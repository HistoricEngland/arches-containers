import json
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from arches_containers.main import main
from arches_containers.utils.workspace import AcWorkspace


@pytest.mark.parametrize(
    "repo_directory", ["test-project", "custom-repo", "test_project", "nested/test-project"]
)
@pytest.mark.parametrize("extra_export", [None, ".ac_test_project_20261013000000", ".ac_other_project"])
@pytest.mark.parametrize("project_input", ["test_project", "test-project"])
def test_import_with_project_name_resolves_exported_repo(tmp_path, monkeypatch, repo_directory, extra_export, project_input):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    repo_path = tmp_path / repo_directory
    export_path = repo_path / ".ac_test_project"
    export_path.mkdir(parents=True)
    (export_path / "config.json").write_text(
        json.dumps({"project_name": "test_project"}), encoding="utf-8"
    )
    if extra_export:
        extra_path = repo_path / extra_export
        extra_path.mkdir()
        (extra_path / "config.json").write_text(
            json.dumps({"project_name": "test_project"}), encoding="utf-8"
        )
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", project_input, "--no"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager"), \
         patch("arches_containers.main._interactive_project_select") as select_project, \
         patch.object(workspace, "import_project") as import_project:
        main()

    import_project.assert_called_once_with(
        "test_project", str(repo_path), new_hash=None, target_hash=None, prompt_default=False
    )
    select_project.assert_not_called()


@pytest.mark.parametrize("project_input", ["test_project", "test-project"])
def test_import_with_explicit_repo_path_skips_discovery(tmp_path, monkeypatch, project_input):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    repo_path = str(tmp_path / "custom-repo")
    monkeypatch.setattr(
        sys, "argv",
        ["act", "import", "-p", project_input, "-r", repo_path, "--hash", "abcde", "--yes"],
    )

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager"), \
         patch.object(workspace, "discover_importable_projects") as discover_projects, \
         patch.object(workspace, "import_project") as import_project:
        main()

    import_project.assert_called_once_with(
        "test_project", repo_path, new_hash=None, target_hash="abcde", prompt_default=True
    )
    discover_projects.assert_not_called()


@pytest.mark.parametrize("project_input", ["test_project", "test-project"])
def test_import_with_duplicate_project_names_requires_repo_path(tmp_path, monkeypatch, project_input):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    repo_paths = [tmp_path / "first-repo", tmp_path / "second-repo"]
    for repo_path in repo_paths:
        export_path = repo_path / ".ac_test_project"
        export_path.mkdir(parents=True)
        (export_path / "config.json").write_text(
            json.dumps({"project_name": "test_project"}), encoding="utf-8"
        )
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", project_input, "--no"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager") as output, \
         patch.object(workspace, "import_project") as import_project:
        with pytest.raises(SystemExit) as error:
            main()

    assert error.value.code == 1
    output.fail.assert_called_once()
    message = output.fail.call_args[0][0]
    assert f"Multiple importable projects named '{project_input}'" in message
    assert "--repo_path" in message
    assert "\n\n  Matching exports:\n" in message
    for repo_path in repo_paths:
        assert f"    test_project\n      {repo_path}" in message
    import_project.assert_not_called()


@pytest.mark.parametrize(
    "project_input,repo_alias", [("test_project", "test_project"), ("test-project", "test-project")]
)
def test_import_project_identity_takes_priority_over_repo_alias(tmp_path, monkeypatch, project_input, repo_alias):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    for directory, name in [("project-source", "test_project"), (repo_alias, "other_project")]:
        export_path = tmp_path / directory / f".ac_{name}"
        export_path.mkdir(parents=True)
        (export_path / "config.json").write_text(
            json.dumps({"project_name": name}), encoding="utf-8"
        )
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", project_input, "--no"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager") as output, \
         patch.object(workspace, "import_project") as import_project:
        main()

    import_project.assert_called_once_with(
        "test_project", str(tmp_path / "project-source"),
        new_hash=None, target_hash=None, prompt_default=False,
    )
    if project_input != "test_project":
        output.write.assert_any_call(
            f"Resolved '{project_input}' to project 'test_project' in '{tmp_path / 'project-source'}'."
        )


def test_import_with_duplicate_repo_aliases_requires_project_name_and_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    for name in ["first_project", "second_project"]:
        export_path = tmp_path / name / "custom-repo" / f".ac_{name}"
        export_path.mkdir(parents=True)
        (export_path / "config.json").write_text(
            json.dumps({"project_name": name}), encoding="utf-8"
        )
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", "custom-repo", "--no"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager") as output, \
         patch.object(workspace, "import_project") as import_project:
        with pytest.raises(SystemExit) as error:
            main()

    assert error.value.code == 1
    message = output.fail.call_args[0][0]
    assert "first_project" in message
    assert "second_project" in message
    assert "--repo_path" in message
    import_project.assert_not_called()


def test_import_with_typo_suggests_project_without_importing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    for directory in ["first-repo", "second-repo"]:
        export_path = tmp_path / directory / ".ac_test_project"
        export_path.mkdir(parents=True)
        (export_path / "config.json").write_text(
            json.dumps({"project_name": "test_project"}), encoding="utf-8"
        )
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", "test_projet", "--yes"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager") as output, \
         patch.object(workspace, "import_project") as import_project:
        with pytest.raises(SystemExit) as error:
            main()

    assert error.value.code == 1
    message = output.fail.call_args[0][0]
    assert "No exported config matches 'test_projet'" in message
    assert "\n\n  Did you mean?\n    act import -p test_project" in message
    assert "\n\n  Checked path:\n    " in message
    assert "\n\n  Select from available projects:\n    act import" in message
    assert "\n\n  Or specify the project and repository:\n    act import -p <project_name> --repo_path <path>" in message
    assert message.count("-p test_project") == 1
    import_project.assert_not_called()


def test_import_with_explicit_repo_path_preserves_literal_export_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    repo_path = tmp_path / "custom-repo"
    (repo_path / ".ac_test-project").mkdir(parents=True)
    monkeypatch.setattr(
        sys, "argv", ["act", "import", "-p", "test-project", "-r", str(repo_path), "--no"]
    )

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager"), \
         patch.object(workspace, "discover_importable_projects") as discover_projects, \
         patch.object(workspace, "import_project") as import_project:
        main()

    import_project.assert_called_once_with(
        "test-project", str(repo_path), new_hash=None, target_hash=None, prompt_default=False
    )
    discover_projects.assert_not_called()


def test_import_preserves_direct_path_for_config_without_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    export_path = tmp_path / "test_project" / ".ac_test_project"
    export_path.mkdir(parents=True)
    (export_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", "test_project", "--no"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager"), \
         patch.object(workspace, "import_project") as import_project:
        main()

    import_project.assert_called_once_with(
        "test_project", str(tmp_path / "test_project"),
        new_hash=None, target_hash=None, prompt_default=False,
    )


@pytest.mark.parametrize("mismatched_export", [False, True])
def test_import_without_matching_export_reports_missing_config(tmp_path, monkeypatch, mismatched_export):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    if mismatched_export:
        export_path = tmp_path / "custom-repo" / ".ac_other_project"
        export_path.mkdir(parents=True)
        (export_path / "config.json").write_text(
            json.dumps({"project_name": "test_project"}), encoding="utf-8"
        )
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", "test_project", "--no"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager") as output, \
         patch.object(workspace, "import_project") as import_project:
        with pytest.raises(SystemExit) as error:
            main()

    assert error.value.code == 1
    output.fail.assert_called_once()
    message = output.fail.call_args[0][0]
    assert "No exported config matches 'test_project'" in message
    assert "config.json" in message
    assert "--repo_path" in message
    import_project.assert_not_called()


@pytest.mark.parametrize("project_input", ["test_project", "test-project", "custom-repo"])
@pytest.mark.parametrize("legacy_config", [False, True])
def test_import_with_project_name_round_trip(tmp_path, monkeypatch, project_input, legacy_config):
    monkeypatch.chdir(tmp_path)
    workspace = AcWorkspace()
    workspace.create_project(
        "test_project",
        SimpleNamespace(version="7.6", organization=None, branch=None, repo_name=None),
    )
    repo_directory = "custom-repo" if project_input == "custom-repo" else "test-project"
    repo_path = tmp_path / repo_directory
    repo_path.mkdir()
    workspace.export_project("test_project", str(repo_path), prompt_default=False)
    if legacy_config:
        config_path = repo_path / ".ac_test_project" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config.pop("project_repo_directory", None)
        config_path.write_text(json.dumps(config), encoding="utf-8")
    workspace.delete_project("test_project")
    monkeypatch.setattr(sys, "argv", ["act", "import", "-p", project_input, "--no"])

    with patch("arches_containers.main.AcWorkspace", return_value=workspace), \
         patch("arches_containers.main.AcOutputManager"):
        main()

    assert "test_project" in workspace.list_projects()
    project = workspace.get_project("test_project")
    assert project.project_name == "test_project"
    if not legacy_config:
        assert project["project_repo_directory"] == "test-project"
    compose_path = tmp_path / ".arches_containers" / "test_project" / "docker-compose.yml"
    compose = compose_path.read_text(encoding="utf-8")
    assert "/.arches_containers/test_project" in compose
    assert f"/{repo_directory}/.ac_test_project" not in compose