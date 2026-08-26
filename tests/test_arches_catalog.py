import json
import time
from unittest.mock import patch

import pytest

from arches_containers.utils.arches_catalog import (
    CACHE_FILENAME,
    CACHE_TTL,
    _build_catalog_packages,
    fetch_arches_catalog_packages,
    get_compatible_template_versions,
)


SAMPLE_TREE = [
    "packages/arches-her.yaml",
    "packages/arches-lingo.yaml",
    "packages/arches-containers.yaml",
    "README.md",
]


SAMPLE_MANIFESTS = {
    "packages/arches-her.yaml": {
        "name": "arches-her",
        "kind": "application",
        "repository": "https://github.com/archesproject/arches-her",
        "arches_versions": ">=7.6,<8.0",
        "summary": "Arches HER package",
        "status": "stable",
    },
    "packages/arches-lingo.yaml": {
        "name": "arches-lingo",
        "kind": "extension",
        "repository": "https://github.com/archesproject/arches-lingo",
        "arches_versions": ">=8.0,<=8.1",
        "summary": "Arches Lingo package",
        "status": "stable",
    },
    "packages/arches-containers.yaml": {
        "name": "arches-containers",
        "kind": "tool",
        "repository": "https://github.com/HistoricEngland/arches-containers",
        "arches_versions": ">=7.6,<=8.1",
        "summary": "Arches Containers tool",
        "status": "stable",
    },
}


def test_build_catalog_packages_filters_to_application_and_extension():
    def fake_fetch_yaml(path):
        return SAMPLE_MANIFESTS[path]

    with patch(
        "arches_containers.utils.arches_catalog._fetch_yaml_manifest",
        side_effect=fake_fetch_yaml,
    ):
        results = _build_catalog_packages(SAMPLE_TREE, {"application", "extension"})

    assert len(results) == 2
    names = [item["name"] for item in results]
    assert "arches-her" in names
    assert "arches-lingo" in names
    assert "arches-containers" not in names


def test_build_catalog_packages_normalizes_project_name():
    def fake_fetch_yaml(path):
        return SAMPLE_MANIFESTS[path]

    with patch(
        "arches_containers.utils.arches_catalog._fetch_yaml_manifest",
        side_effect=fake_fetch_yaml,
    ):
        results = _build_catalog_packages(["packages/arches-her.yaml"], {"application", "extension"})

    assert results[0]["project_name"] == "arches_her"


def test_get_compatible_template_versions_filters_correctly():
    templates = [
        {"version": "7.6", "display_name": "7.6"},
        {"version": "8.0", "display_name": "8.0"},
        {"version": "8.1", "display_name": "8.1"},
    ]

    compatible = get_compatible_template_versions(">=8.0,<=8.1", templates)

    assert [item["version"] for item in compatible] == ["8.0", "8.1"]


def test_get_compatible_template_versions_raises_for_invalid_specifier():
    templates = [{"version": "8.1", "display_name": "8.1"}]
    with pytest.raises(RuntimeError, match="Invalid arches_versions"):
        get_compatible_template_versions("bad-spec", templates)


def test_fetch_arches_catalog_packages_uses_cache_when_fresh(tmp_path):
    cached_packages = [
        {
            "name": "arches-her",
            "project_name": "arches_her",
            "kind": "application",
            "repository": "https://github.com/archesproject/arches-her",
            "arches_versions": ">=7.6,<8.0",
            "summary": "",
            "status": "stable",
            "display_name": "arches-her  (application · Arches >=7.6,<8.0)",
        }
    ]
    cache_data = {"timestamp": time.time(), "packages": cached_packages}
    (tmp_path / CACHE_FILENAME).write_text(json.dumps(cache_data))

    with patch("arches_containers.utils.arches_catalog._fetch_tree_paths") as mocked:
        results = fetch_arches_catalog_packages(cache_dir=str(tmp_path))

    mocked.assert_not_called()
    assert results == cached_packages


def test_fetch_arches_catalog_packages_refetches_when_stale(tmp_path):
    cache_data = {"timestamp": time.time() - CACHE_TTL - 5, "packages": []}
    (tmp_path / CACHE_FILENAME).write_text(json.dumps(cache_data))

    def fake_fetch_yaml(path):
        return SAMPLE_MANIFESTS[path]

    with patch(
        "arches_containers.utils.arches_catalog._fetch_tree_paths",
        return_value=SAMPLE_TREE,
    ):
        with patch(
            "arches_containers.utils.arches_catalog._fetch_yaml_manifest",
            side_effect=fake_fetch_yaml,
        ):
            results = fetch_arches_catalog_packages(cache_dir=str(tmp_path))

    assert len(results) == 2