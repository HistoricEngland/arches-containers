import json
import os
import time
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, call, patch

import pytest

from arches_containers.utils.remote_catalog import (
    CACHE_FILENAME,
    CACHE_TTL,
    CATALOG_BRANCH,
    CATALOG_REPO,
    _build_catalog_entries,
    _fetch_config_json,
    _fetch_tree,
    _github_api_headers,
    _load_cache,
    _save_cache,
    download_config_to_tempdir,
    fetch_remote_catalog,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TREE_PATHS = [
    "arches-her/1.1/.ac_arches_her/config.json",
    "arches-her/1.1/.ac_arches_her/Dockerfile",
    "arches-her/1.1/.ac_arches_her/docker-compose.yml",
    "arches-her/1.1/.ac_arches_her/docker/entrypoint.sh",
    "arches-lingo/1.0/.ac_arches_lingo/config.json",
    "arches-lingo/1.0/.ac_arches_lingo/Dockerfile",
    "README.md",
]

SAMPLE_CONFIGS = {
    "arches-her/1.1/.ac_arches_her/config.json": {
        "project_name": "arches_her",
        "project_name_url_safe": "arches-her",
        "project_repo_directory": "arches-her",
        "project_hash": "c0d8d",
        "arches_version": "7.6",
        "arches_repo_organization": "archesproject",
        "arches_repo_branch": "stable/7.6.22",
    },
    "arches-lingo/1.0/.ac_arches_lingo/config.json": {
        "project_name": "arches_lingo",
        "project_name_url_safe": "arches-lingo",
        "project_repo_directory": "arches-lingo",
        "project_hash": "ed22d",
        "arches_version": "8.1",
        "arches_repo_organization": "archesproject",
        "arches_repo_branch": "stable/8.1.2",
    },
}


def _make_api_response(data):
    """Return a mock urllib response yielding JSON-encoded data."""
    body = json.dumps(data).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_contents_response(data):
    """Return a GitHub Contents API mock response (base64 encoded content)."""
    import base64

    raw = json.dumps(data).encode()
    encoded = base64.b64encode(raw).decode()
    return _make_api_response({"content": encoded + "\n"})


# ---------------------------------------------------------------------------
# _github_api_headers
# ---------------------------------------------------------------------------


def test_headers_accept_set():
    headers = _github_api_headers()
    assert headers == {"Accept": "application/vnd.github+json"}


# ---------------------------------------------------------------------------
# _fetch_tree
# ---------------------------------------------------------------------------


def test_fetch_tree_returns_blob_paths():
    tree_data = {
        "truncated": False,
        "tree": [
            {"path": "arches-her/1.1/.ac_arches_her/config.json", "type": "blob"},
            {"path": "arches-her/1.1/.ac_arches_her", "type": "tree"},
            {"path": "README.md", "type": "blob"},
        ],
    }
    with patch("urllib.request.urlopen", return_value=_make_api_response(tree_data)):
        paths = _fetch_tree()
    assert "arches-her/1.1/.ac_arches_her/config.json" in paths
    assert "README.md" in paths
    # tree entries (directories) should be excluded
    assert "arches-her/1.1/.ac_arches_her" not in paths


def test_fetch_tree_raises_on_truncation():
    tree_data = {"truncated": True, "tree": []}
    with patch("urllib.request.urlopen", return_value=_make_api_response(tree_data)):
        with pytest.raises(RuntimeError, match="truncated"):
            _fetch_tree()


def test_fetch_tree_raises_on_rate_limit():
    exc = urllib.error.HTTPError(url="", code=403, msg="Forbidden", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=exc):
        with pytest.raises(RuntimeError, match="rate limit"):
            _fetch_tree()


def test_fetch_tree_raises_on_network_error():
    exc = urllib.error.URLError(reason="Name or service not known")
    with patch("urllib.request.urlopen", side_effect=exc):
        with pytest.raises(RuntimeError, match="internet connection"):
            _fetch_tree()


# ---------------------------------------------------------------------------
# _build_catalog_entries
# ---------------------------------------------------------------------------


def test_build_catalog_entries():
    def fake_fetch_config(path):
        return SAMPLE_CONFIGS[path]

    with patch(
        "arches_containers.utils.remote_catalog._fetch_config_json",
        side_effect=fake_fetch_config,
    ):
        entries = _build_catalog_entries(SAMPLE_TREE_PATHS)

    assert len(entries) == 2
    names = [e["project_name"] for e in entries]
    assert "arches_her" in names
    assert "arches_lingo" in names


def test_build_catalog_entries_display_name_format():
    def fake_fetch_config(path):
        return SAMPLE_CONFIGS[path]

    with patch(
        "arches_containers.utils.remote_catalog._fetch_config_json",
        side_effect=fake_fetch_config,
    ):
        entries = _build_catalog_entries(SAMPLE_TREE_PATHS)

    her = next(e for e in entries if e["project_name"] == "arches_her")
    assert her["display_name"] == "arches_her  (v1.1 · Arches 7.6)"
    assert her["catalog_version"] == "1.1"
    assert her["arches_version"] == "7.6"
    assert her["remote_folder"] == "arches-her/1.1/.ac_arches_her"


def test_build_catalog_entries_all_files_populated():
    def fake_fetch_config(path):
        return SAMPLE_CONFIGS[path]

    with patch(
        "arches_containers.utils.remote_catalog._fetch_config_json",
        side_effect=fake_fetch_config,
    ):
        entries = _build_catalog_entries(SAMPLE_TREE_PATHS)

    her = next(e for e in entries if e["project_name"] == "arches_her")
    # config.json itself is not in all_files (it starts with remote_folder + "/")
    assert "arches-her/1.1/.ac_arches_her/Dockerfile" in her["all_files"]
    assert "arches-her/1.1/.ac_arches_her/docker/entrypoint.sh" in her["all_files"]
    # README.md at root should not be included
    assert "README.md" not in her["all_files"]


def test_build_catalog_entries_skips_non_ac_folders():
    paths = ["arches-her/1.1/.other_folder/config.json"]
    entries = _build_catalog_entries(paths)
    assert entries == []


def test_build_catalog_entries_skips_missing_project_name():
    def fake_fetch_config(path):
        return {"arches_version": "7.6"}  # no project_name

    paths = ["arches-her/1.1/.ac_arches_her/config.json"]
    with patch(
        "arches_containers.utils.remote_catalog._fetch_config_json",
        side_effect=fake_fetch_config,
    ):
        entries = _build_catalog_entries(paths)
    assert entries == []


def test_build_catalog_entries_sorted_alphabetically():
    def fake_fetch_config(path):
        return SAMPLE_CONFIGS[path]

    with patch(
        "arches_containers.utils.remote_catalog._fetch_config_json",
        side_effect=fake_fetch_config,
    ):
        entries = _build_catalog_entries(SAMPLE_TREE_PATHS)

    display_names = [e["display_name"] for e in entries]
    assert display_names == sorted(display_names, key=str.lower)


# ---------------------------------------------------------------------------
# _load_cache / _save_cache
# ---------------------------------------------------------------------------


def test_save_and_load_cache(tmp_path):
    configs = [{"project_name": "arches_her", "display_name": "arches_her  (v1.1 · Arches 7.6)"}]
    cache_path = str(tmp_path / CACHE_FILENAME)
    _save_cache(cache_path, configs)
    loaded = _load_cache(cache_path)
    assert loaded is not None
    assert loaded["configs"] == configs
    assert "timestamp" in loaded


def test_load_cache_returns_none_for_missing_file(tmp_path):
    cache_path = str(tmp_path / "nonexistent.json")
    assert _load_cache(cache_path) is None


def test_load_cache_returns_none_for_corrupt_json(tmp_path):
    cache_path = tmp_path / CACHE_FILENAME
    cache_path.write_text("not valid json")
    assert _load_cache(str(cache_path)) is None


def test_load_cache_returns_none_for_missing_keys(tmp_path):
    cache_path = tmp_path / CACHE_FILENAME
    cache_path.write_text(json.dumps({"only_timestamp": 0}))
    assert _load_cache(str(cache_path)) is None


def test_save_cache_is_non_fatal_on_write_error(tmp_path):
    # Passing a path inside a non-existent directory should not raise
    cache_path = str(tmp_path / "nonexistent_dir" / CACHE_FILENAME)
    _save_cache(cache_path, [])  # should not raise


# ---------------------------------------------------------------------------
# fetch_remote_catalog — cache behaviour
# ---------------------------------------------------------------------------


def test_fetch_remote_catalog_uses_cache_when_fresh(tmp_path):
    configs = [{"project_name": "arches_her"}]
    cache_data = {"timestamp": time.time(), "configs": configs}
    cache_path = tmp_path / CACHE_FILENAME
    cache_path.write_text(json.dumps(cache_data))

    with patch("urllib.request.urlopen") as mock_urlopen:
        result = fetch_remote_catalog(str(tmp_path))

    mock_urlopen.assert_not_called()
    assert result == configs


def test_fetch_remote_catalog_refetches_stale_cache(tmp_path):
    configs = [{"project_name": "arches_her"}]
    stale_timestamp = time.time() - CACHE_TTL - 60
    cache_data = {"timestamp": stale_timestamp, "configs": configs}
    (tmp_path / CACHE_FILENAME).write_text(json.dumps(cache_data))

    def fake_fetch_config(path):
        return SAMPLE_CONFIGS[path]

    tree_data = {
        "truncated": False,
        "tree": [{"path": p, "type": "blob"} for p in SAMPLE_TREE_PATHS],
    }
    with patch("urllib.request.urlopen", return_value=_make_api_response(tree_data)):
        with patch(
            "arches_containers.utils.remote_catalog._fetch_config_json",
            side_effect=fake_fetch_config,
        ):
            result = fetch_remote_catalog(str(tmp_path))

    assert len(result) == 2


def test_fetch_remote_catalog_skips_cache_when_none():
    def fake_fetch_config(path):
        return SAMPLE_CONFIGS[path]

    tree_data = {
        "truncated": False,
        "tree": [{"path": p, "type": "blob"} for p in SAMPLE_TREE_PATHS],
    }
    with patch("urllib.request.urlopen", return_value=_make_api_response(tree_data)) as mock_urlopen:
        with patch(
            "arches_containers.utils.remote_catalog._fetch_config_json",
            side_effect=fake_fetch_config,
        ):
            result = fetch_remote_catalog(cache_dir=None)

    assert len(result) == 2
    # No cache file written (would have required a real dir)


# ---------------------------------------------------------------------------
# download_config_to_tempdir
# ---------------------------------------------------------------------------


def test_download_config_to_tempdir_creates_ac_folder(tmp_path, monkeypatch):
    entry = {
        "project_name": "arches_her",
        "remote_folder": "arches-her/1.1/.ac_arches_her",
        "all_files": [
            "arches-her/1.1/.ac_arches_her/config.json",
            "arches-her/1.1/.ac_arches_her/docker/entrypoint.sh",
        ],
    }

    file_counter = [0]

    def fake_urlopen(req, timeout=15):
        file_counter[0] += 1
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"file content"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    import tempfile

    original_mkdtemp = tempfile.mkdtemp

    def controlled_mkdtemp(**kwargs):
        return str(tmp_path / "act_catalog_test")

    monkeypatch.setattr(tempfile, "mkdtemp", controlled_mkdtemp)

    tmpdir = download_config_to_tempdir(entry)

    assert os.path.isdir(os.path.join(tmpdir, ".ac_arches_her"))
    assert os.path.isfile(os.path.join(tmpdir, ".ac_arches_her", "config.json"))
    assert os.path.isfile(os.path.join(tmpdir, ".ac_arches_her", "docker", "entrypoint.sh"))
    assert file_counter[0] == 2


def test_download_config_to_tempdir_raises_on_http_error(monkeypatch):
    entry = {
        "project_name": "arches_her",
        "remote_folder": "arches-her/1.1/.ac_arches_her",
        "all_files": ["arches-her/1.1/.ac_arches_her/config.json"],
    }

    exc = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=15: (_ for _ in ()).throw(exc))

    with pytest.raises(RuntimeError, match="HTTP 404"):
        download_config_to_tempdir(entry)


def test_download_config_to_tempdir_raises_on_network_error(monkeypatch):
    entry = {
        "project_name": "arches_her",
        "remote_folder": "arches-her/1.1/.ac_arches_her",
        "all_files": ["arches-her/1.1/.ac_arches_her/config.json"],
    }

    exc = urllib.error.URLError(reason="Connection refused")
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=15: (_ for _ in ()).throw(exc))

    with pytest.raises(RuntimeError, match="internet connection"):
        download_config_to_tempdir(entry)
