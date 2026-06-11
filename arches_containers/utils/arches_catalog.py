"""Utilities for browsing package metadata from archesproject/arches-catalog."""

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from slugify import slugify

CATALOG_REPO = "archesproject/arches-catalog"
CATALOG_BRANCH = "main"
CACHE_FILENAME = "arches_catalog_cache.json"
CACHE_TTL = 3600


def _github_api_headers():
    return {"Accept": "application/vnd.github+json"}


def _github_api_get(url):
    req = urllib.request.Request(url, headers=_github_api_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise RuntimeError(
                f"GitHub API rate limit exceeded (HTTP {exc.code}). Please try again later."
            ) from exc
        raise RuntimeError(f"GitHub API request failed (HTTP {exc.code}): {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Unable to reach GitHub. Check your internet connection. ({exc.reason})"
        ) from exc


def _fetch_tree_paths():
    url = (
        f"https://api.github.com/repos/{CATALOG_REPO}/git/trees/{CATALOG_BRANCH}"
        "?recursive=1"
    )
    data = _github_api_get(url)
    if data.get("truncated"):
        raise RuntimeError(
            "Catalog repository tree was truncated by the GitHub API. Contact maintainers."
        )
    return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]


def _fetch_yaml_manifest(path):
    url = f"https://api.github.com/repos/{CATALOG_REPO}/contents/{path}?ref={CATALOG_BRANCH}"
    data = _github_api_get(url)
    content = base64.b64decode(data["content"]).decode("utf-8")
    parsed = yaml.safe_load(content)
    return parsed if isinstance(parsed, dict) else {}


def _normalize_project_name(package_name):
    return slugify(text=package_name, separator="_")


def _build_catalog_packages(all_paths, allowed_kinds):
    pattern = re.compile(r"^packages/[^/]+\.ya?ml$")
    paths = sorted([p for p in all_paths if pattern.match(p)], key=str.lower)
    packages = []
    for manifest_path in paths:
        manifest = _fetch_yaml_manifest(manifest_path)
        name = (manifest.get("name") or "").strip()
        kind = (manifest.get("kind") or "").strip()
        repository = (manifest.get("repository") or "").strip()
        arches_versions = (manifest.get("arches_versions") or "").strip()
        if not name or not kind or not repository or not arches_versions:
            continue
        if allowed_kinds and kind not in allowed_kinds:
            continue

        packages.append(
            {
                "name": name,
                "project_name": _normalize_project_name(name),
                "kind": kind,
                "repository": repository,
                "arches_versions": arches_versions,
                "summary": (manifest.get("summary") or "").strip(),
                "status": (manifest.get("status") or "").strip(),
                "display_name": f"{name}  ({kind} · Arches {arches_versions})",
            }
        )

    return sorted(packages, key=lambda item: item["name"].lower())


def _load_cache(cache_path):
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "timestamp" not in data or "packages" not in data:
            return None
        return data
    except (OSError, ValueError, KeyError):
        return None


def _save_cache(cache_path, packages):
    data = {"timestamp": time.time(), "packages": packages}
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def fetch_arches_catalog_packages(cache_dir=None, allowed_kinds=None):
    if allowed_kinds is None:
        allowed_kinds = {"application", "extension"}

    cache_path = None
    if cache_dir is not None:
        cache_path = os.path.join(cache_dir, CACHE_FILENAME)
        cached = _load_cache(cache_path)
        if cached and (time.time() - cached["timestamp"]) < CACHE_TTL:
            return [pkg for pkg in cached["packages"] if pkg.get("kind") in allowed_kinds]

    all_paths = _fetch_tree_paths()
    packages = _build_catalog_packages(all_paths, allowed_kinds)

    if cache_path and os.path.isdir(cache_dir):
        _save_cache(cache_path, packages)

    return packages


def get_compatible_template_versions(arches_versions, template_versions):
    try:
        specifier = SpecifierSet(arches_versions)
    except InvalidSpecifier as exc:
        raise RuntimeError(f"Invalid arches_versions specifier: '{arches_versions}'") from exc

    compatible = []
    for item in template_versions:
        raw_version = item.get("version", "")
        try:
            if specifier.contains(Version(raw_version), prereleases=True):
                compatible.append(item)
        except InvalidVersion:
            continue

    return compatible