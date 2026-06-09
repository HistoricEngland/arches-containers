"""
Remote catalog utilities for fetching and downloading Arches Container
configurations from a centrally managed GitHub repository.
"""

import base64
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request

CATALOG_REPO = "HistoricEngland/act-configs"
CATALOG_BRANCH = "main"
CACHE_FILENAME = "catalog_cache.json"
CACHE_TTL = 3600  # seconds


def _github_api_headers():
    """Return headers for GitHub API requests."""
    return {"Accept": "application/vnd.github+json"}


def _github_api_get(url):
    """Perform a GET request against the GitHub API and return parsed JSON."""
    req = urllib.request.Request(url, headers=_github_api_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise RuntimeError(
                f"GitHub API rate limit exceeded (HTTP {exc.code}). "
                "Please try again later."
            ) from exc
        raise RuntimeError(
            f"GitHub API request failed (HTTP {exc.code}): {url}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Unable to reach GitHub. Check your internet connection. ({exc.reason})"
        ) from exc


def _fetch_tree():
    """Fetch the full recursive file tree from the catalog repository."""
    url = (
        f"https://api.github.com/repos/{CATALOG_REPO}/git/trees/{CATALOG_BRANCH}"
        "?recursive=1"
    )
    data = _github_api_get(url)
    if data.get("truncated"):
        raise RuntimeError(
            "Catalog repository tree was truncated by the GitHub API. "
            "Contact the maintainers."
        )
    return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]


def _fetch_config_json(path):
    """Fetch and decode a config.json file from the catalog via the GitHub Contents API."""
    url = (
        f"https://api.github.com/repos/{CATALOG_REPO}/contents/{path}"
        f"?ref={CATALOG_BRANCH}"
    )
    data = _github_api_get(url)
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content)


def _build_catalog_entries(all_paths):
    """
    Given the full list of file paths in the repo tree, find all config.json
    files that match the pattern:
        <display-name>/<catalog-version>/.ac_<project>/config.json

    Fetches each config.json and returns a list of catalog entry dicts.
    """
    pattern = re.compile(r"^([^/]+)/([^/]+)/(\.[^/]+)/config\.json$")
    entries = []
    for path in all_paths:
        m = pattern.match(path)
        if not m:
            continue
        catalog_display, catalog_version, ac_folder = m.groups()
        if not ac_folder.startswith(".ac_"):
            continue

        config = _fetch_config_json(path)
        project_name = config.get("project_name", "")
        arches_version = config.get("arches_version", "")
        if not project_name:
            continue

        remote_folder = f"{catalog_display}/{catalog_version}/{ac_folder}"
        folder_files = [p for p in all_paths if p.startswith(remote_folder + "/")]
        display_name = f"{project_name}  (v{catalog_version} · Arches {arches_version})"
        entries.append(
            {
                "project_name": project_name,
                "arches_version": arches_version,
                "catalog_version": catalog_version,
                "display_name": display_name,
                "remote_folder": remote_folder,
                "all_files": folder_files,
            }
        )

    entries.sort(key=lambda e: e["display_name"].lower())
    return entries


def _load_cache(cache_path):
    """Load cache from disk. Returns None if missing, empty, or corrupt."""
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "timestamp" not in data or "configs" not in data:
            return None
        return data
    except (OSError, ValueError, KeyError):
        return None


def _save_cache(cache_path, configs):
    """Save configs list and current timestamp to cache. Failure is non-fatal."""
    data = {"timestamp": time.time(), "configs": configs}
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def fetch_remote_catalog(cache_dir):
    """
    Return the list of available configs from the remote catalog.

    Uses a local cache in cache_dir with a TTL of CACHE_TTL seconds. Pass
    cache_dir=None to skip caching entirely.

    Each entry in the returned list is a dict with:
        project_name     str  - e.g. "arches_her"
        arches_version   str  - e.g. "7.6"
        catalog_version  str  - e.g. "1.1"
        display_name     str  - e.g. "arches_her  (v1.1 · Arches 7.6)"
        remote_folder    str  - path in the catalog repo, e.g. "arches-her/1.1/.ac_arches_her"
        all_files        list - repo-relative paths of every file inside remote_folder
    """
    if cache_dir is not None:
        cache_path = os.path.join(cache_dir, CACHE_FILENAME)
        cached = _load_cache(cache_path)
        if cached and (time.time() - cached["timestamp"]) < CACHE_TTL:
            return cached["configs"]

    all_paths = _fetch_tree()
    configs = _build_catalog_entries(all_paths)

    if cache_dir is not None and os.path.isdir(cache_dir):
        _save_cache(cache_path, configs)

    return configs


def download_config_to_tempdir(catalog_entry):
    """
    Download all files for a catalog entry from the remote repository into a
    temporary directory structured as:

        <tmpdir>/
          <catalog_version>/          ← matches the version dir in act-configs
            .ac_<project_name>/
              config.json
              Dockerfile
              docker/
                ...

    The inner path ``<tmpdir>/<catalog_version>`` is returned alongside the
    root tmpdir so that ``import_project()``'s path-rewriting logic resolves
    the correct ``repo_dir_name`` (= ``catalog_version``) when replacing
    compose-file references like ``./1.1/.ac_<project>/`` with
    ``/.arches_containers/<project>/``.

    Returns a tuple ``(tmpdir, import_path)`` where ``import_path`` is the
    directory to pass to ``import_project()`` and ``tmpdir`` is the root to
    clean up afterwards.
    """
    project_name = catalog_entry["project_name"]
    remote_folder = catalog_entry["remote_folder"]
    all_files = catalog_entry["all_files"]
    catalog_version = catalog_entry["catalog_version"]

    tmpdir = tempfile.mkdtemp(prefix="act_catalog_")
    try:
        inner_path = os.path.join(tmpdir, catalog_version)
        ac_folder_name = f".ac_{project_name}"
        ac_folder_path = os.path.join(inner_path, ac_folder_name)
        os.makedirs(ac_folder_path, exist_ok=True)

        headers = _github_api_headers()
        for file_path in all_files:
            rel = os.path.relpath(file_path, remote_folder)
            dest_path = os.path.join(ac_folder_path, rel)
            dest_dir = os.path.dirname(dest_path)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)

            raw_url = (
                f"https://raw.githubusercontent.com/{CATALOG_REPO}"
                f"/{CATALOG_BRANCH}/{file_path}"
            )
            req = urllib.request.Request(raw_url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    with open(dest_path, "wb") as out:
                        out.write(resp.read())
            except urllib.error.HTTPError as exc:
                raise RuntimeError(
                    f"Failed to download remote file '{file_path}' (HTTP {exc.code})."
                ) from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(
                    f"Unable to download '{file_path}'. "
                    f"Check your internet connection. ({exc.reason})"
                ) from exc
    except Exception:
        import shutil as _shutil
        _shutil.rmtree(tmpdir, ignore_errors=True)
        raise

    return tmpdir, inner_path
