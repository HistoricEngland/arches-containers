import pytest
import os
import shutil
import json
import platform
from types import SimpleNamespace
from unittest.mock import patch
from arches_containers.utils.workspace import (
    AcWorkspace, 
    AcSettings, 
    AcProject, 
    AcProjectAttributes,
    AC_DIRECTORY_NAME,
    REPLACE_TOKEN_HASH,
    _generate_project_hash,
    _version_supports_project_hash,
    _is_version_supported,
)


def make_create_args(version="7.6", organization=None, branch=None, repo_name=None):
    return SimpleNamespace(
        version=version,
        organization=organization,
        branch=branch,
        repo_name=repo_name,
    )

@pytest.fixture
def temp_workspace(tmp_path):
    """Creates a temporary workspace directory"""
    os.chdir(tmp_path)
    workspace = AcWorkspace()
    yield workspace
    os.chdir("/")

@pytest.fixture
def workspace_with_project(temp_workspace):
    """Creates a workspace with a test project"""
    project_name = "test_project"
    temp_workspace.create_project(project_name, make_create_args())
    return temp_workspace, project_name

def get_platform_line(yaml_path):
    if not os.path.exists(yaml_path):
        return None
    with open(yaml_path) as f:
        for line in f:
            if 'platform:' in line:
                return line.rstrip('\n')
    return None

class TestAcWorkspace:
    def test_workspace_creation(self, temp_workspace):
        assert os.path.exists(os.path.join(temp_workspace.path, AC_DIRECTORY_NAME))

    @pytest.mark.parametrize("version", ["7.6", "8.0"])
    def test_create_project(self, temp_workspace, monkeypatch, version):
        args = make_create_args(version=version, organization="archesproject", branch="main")
        # Simulate arm64
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        project = temp_workspace.create_project("test_project", args)
        assert os.path.exists(os.path.join(temp_workspace._get_ac_directory_path(), "test_project"))
        assert project["arches_repo_organization"] == "archesproject"
        assert project["arches_repo_branch"] == "main"
        assert project[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value] == "test-project"
        # Check platform line uncommented for arm64 if present
        compose_path = os.path.join(temp_workspace._get_ac_directory_path(), "test_project", "docker-compose-dependencies.yml")
        line = get_platform_line(compose_path)
        if line is not None:
            assert line.strip().startswith("platform: linux/arm64") or line.strip().startswith("#platform: linux/arm64")
        # Simulate amd64
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        project2 = temp_workspace.create_project("test_project2", args)
        assert project2[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value] == "test-project2"
        compose_path2 = os.path.join(temp_workspace._get_ac_directory_path(), "test_project2", "docker-compose-dependencies.yml")
        line2 = get_platform_line(compose_path2)
        if line2 is not None:
            assert line2.strip().startswith("#platform: linux/arm64")

    @pytest.mark.parametrize("version", ["7.6", "8.0"])
    def test_create_project_with_custom_repo_name(self, temp_workspace, version):
        project = temp_workspace.create_project(
            "test_project",
            make_create_args(version=version, repo_name="custom-repo"),
        )

        assert project[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value] == "custom-repo"

    @pytest.mark.parametrize("version", ["7.6", "8.0"])
    def test_export_project(self, workspace_with_project, tmp_path, monkeypatch, version):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        # Simulate arm64
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        workspace.export_project(project_name, str(repo_path))
        exported_compose = os.path.join(repo_path, f".ac_{project_name}", "docker-compose-dependencies.yml")
        line = get_platform_line(exported_compose)
        if line is not None:
            assert line.strip().startswith("#platform: linux/arm64")

    @pytest.mark.parametrize("version", ["7.6", "8.0"])
    def test_import_project(self, workspace_with_project, tmp_path, monkeypatch, version):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        # First export the project
        workspace.export_project(project_name, str(repo_path))
        # Delete original project
        workspace.delete_project(project_name)
        # Simulate arm64
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        # Import project back
        workspace.import_project(project_name, str(repo_path), new_hash=False)
        assert project_name in workspace.list_projects()
        compose_path = os.path.join(workspace._get_ac_directory_path(), project_name, "docker-compose-dependencies.yml")
        line = get_platform_line(compose_path)
        if line is not None:
            assert line.strip().startswith("platform: linux/arm64")

    def test_import_project_with_explicit_hash(self, workspace_with_project, tmp_path):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo_explicit_hash"
        repo_path.mkdir()

        workspace.export_project(project_name, str(repo_path))
        workspace.delete_project(project_name)

        workspace.import_project(project_name, str(repo_path), target_hash="abcde")
        imported_project = workspace.get_project(project_name)
        assert imported_project.get_project_hash() == "abcde"

        compose_path = os.path.join(workspace._get_ac_directory_path(), project_name, "docker-compose-dependencies.yml")
        with open(compose_path) as f:
            content = f.read()
        assert "abcde" in content

    def test_import_project_prompts_for_new_hash_when_flag_omitted(self, workspace_with_project, tmp_path, monkeypatch):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo_prompt_hash"
        repo_path.mkdir()

        original_hash = workspace.get_project(project_name).get_project_hash()
        workspace.export_project(project_name, str(repo_path))
        workspace.delete_project(project_name)

        monkeypatch.setattr("builtins.input", lambda _: "y")
        workspace.import_project(project_name, str(repo_path))

        imported_hash = workspace.get_project(project_name).get_project_hash()
        assert imported_hash != original_hash

    def test_import_project_does_not_prompt_when_config_has_no_hash_key(self, temp_workspace, tmp_path, monkeypatch):
        """Importing a config without a project_hash key should not prompt for a new hash."""
        project_name = "test_project"
        temp_workspace.create_project(project_name, make_create_args())
        repo_path = tmp_path / "test_repo_no_hash_key"
        repo_path.mkdir()

        temp_workspace.export_project(project_name, str(repo_path))
        temp_workspace.delete_project(project_name)

        # Remove the project_hash key from the exported config to simulate a legacy config
        ac_repo_path = os.path.join(repo_path, f".ac_{project_name}")
        config_path = os.path.join(ac_repo_path, "config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        config.pop(AcProjectAttributes.PROJECT_HASH.value, None)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(AssertionError("input() should not be called for configs without a project_hash key")))
        temp_workspace.import_project(project_name, str(repo_path))

    def test_export_project_keeps_existing_repo_hash(self, workspace_with_project, tmp_path, monkeypatch):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo_keep_hash"
        repo_path.mkdir()

        workspace.export_project(project_name, str(repo_path))

        ac_repo_path = os.path.join(repo_path, f".ac_{project_name}")
        config_path = os.path.join(ac_repo_path, "config.json")
        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        config[AcProjectAttributes.PROJECT_HASH.value] = "abcde"
        with open(config_path, "w") as config_file:
            json.dump(config, config_file, indent=4)

        monkeypatch.setattr("builtins.input", lambda _: "y")
        workspace.export_project(project_name, str(repo_path), keep_repo_hash=True)

        with open(config_path, "r") as config_file:
            exported_config = json.load(config_file)
        assert exported_config[AcProjectAttributes.PROJECT_HASH.value] == "abcde"

        compose_path = os.path.join(ac_repo_path, "docker-compose-dependencies.yml")
        with open(compose_path) as f:
            content = f.read()
        assert "abcde" in content

    def test_rehash_project_with_explicit_hash(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        workspace.rehash_project(project_name, target_hash="abcde")

        reloaded = workspace.get_project(project_name)
        assert reloaded.get_project_hash() == "abcde"

    def test_rehash_project_fails_when_containers_running(self, workspace_with_project, monkeypatch):
        workspace, project_name = workspace_with_project

        monkeypatch.setattr(
            "arches_containers.utils.workspace.has_running_project_containers",
            lambda project_name, project_name_urlsafe: True,
        )

        with pytest.raises(SystemExit):
            workspace.rehash_project(project_name)

    def test_import_project_rejects_invalid_hash(self, workspace_with_project, tmp_path):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo_invalid_hash"
        repo_path.mkdir()

        workspace.export_project(project_name, str(repo_path))
        workspace.delete_project(project_name)

        with pytest.raises(ValueError):
            workspace.import_project(project_name, str(repo_path), target_hash="invalid")

    def test_import_project_prompt_default_yes_is_non_interactive(self, workspace_with_project, tmp_path, monkeypatch):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo_prompt_default_yes"
        repo_path.mkdir()

        original_hash = workspace.get_project(project_name).get_project_hash()
        workspace.export_project(project_name, str(repo_path))
        workspace.delete_project(project_name)

        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(AssertionError("input should not be called")))
        workspace.import_project(project_name, str(repo_path), prompt_default=True)

        imported_hash = workspace.get_project(project_name).get_project_hash()
        assert imported_hash != original_hash

    def test_export_project_prompt_default_no_is_non_interactive(self, workspace_with_project, tmp_path, monkeypatch):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo_prompt_default_no"
        repo_path.mkdir()

        workspace.export_project(project_name, str(repo_path))

        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(AssertionError("input should not be called")))
        workspace.export_project(project_name, str(repo_path), prompt_default=False)

        backup_candidates = [
            name for name in os.listdir(repo_path)
            if name.startswith(f".ac_{project_name}_")
        ]
        # Export should be cancelled without prompting, so no timestamp backup should be created.
        assert backup_candidates == []

class TestAcWorkspaceIsActiveProjectRunning:
    def test_returns_true_when_containers_running(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        workspace.get_settings().set_active_project(project_name)
        with patch("arches_containers.utils.workspace.has_running_project_containers", return_value=True):
            assert workspace.is_active_project_running() is True

    def test_returns_false_when_no_containers_running(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        workspace.get_settings().set_active_project(project_name)
        with patch("arches_containers.utils.workspace.has_running_project_containers", return_value=False):
            assert workspace.is_active_project_running() is False

    def test_returns_false_when_no_active_project(self, temp_workspace):
        temp_workspace.get_settings().clear_active_project()
        with patch("arches_containers.utils.workspace.has_running_project_containers") as mock_check:
            result = temp_workspace.is_active_project_running()
        assert result is False
        mock_check.assert_not_called()


class TestAcSettings:
    def test_settings_creation(self, temp_workspace):
        settings = temp_workspace.get_settings()
        settings.clear_active_project()
        assert settings.settings["active_project"] == ""
        assert settings.settings["host"] == "localhost"
        assert settings.settings["port"] == 8002

    def test_set_active_project(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        settings = workspace.get_settings()
        settings.set_active_project(project_name)
        assert settings.get_active_project_name() == project_name

    def test_clear_active_project(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        settings = workspace.get_settings()
        settings.set_active_project(project_name)
        settings.clear_active_project()
        assert settings.settings["active_project"] == ""

class TestAcProject:
    def test_project_creation(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        assert project.project_name == project_name

    def test_project_config_modification(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        project[AcProjectAttributes.PROJECT_ARCHES_REPO_ORGANIZATION.value] = "test_org"
        project.save()

        # Reload project to verify save
        project = workspace.get_project(project_name)
        assert project[AcProjectAttributes.PROJECT_ARCHES_REPO_ORGANIZATION.value] == "test_org"

    def test_get_project_path(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        expected_path = os.path.join(workspace._get_ac_directory_path(), project_name)
        assert project.get_project_path() == expected_path

    def test_get_project_hash_returns_hash(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        project_hash = project.get_project_hash()
        assert isinstance(project_hash, str)
        assert len(project_hash) == 5

    def test_get_project_hash_fallback_for_legacy_config(self, temp_workspace):
        # Simulate a legacy config without project_hash
        project_name = "legacy_project"
        temp_workspace.create_project(project_name, make_create_args())
        project = temp_workspace.get_project(project_name)
        # Remove the project_hash key to simulate legacy config
        del project._config[AcProjectAttributes.PROJECT_HASH.value]
        assert project.get_project_hash() == ""

    def test_get_project_hash_ignored_for_pre_7_6_even_if_present(self, temp_workspace):
        project_name = "legacy_old_version"
        temp_workspace.create_project(project_name, make_create_args(version="7.5"))
        project = temp_workspace.get_project(project_name)
        project[AcProjectAttributes.PROJECT_HASH.value] = "abcde"
        project.save()

        reloaded = temp_workspace.get_project(project_name)
        assert reloaded.get_project_hash() == ""

    def test_is_initialised_returns_false_when_repo_dir_missing(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        # repo_dir does not exist in workspace root, so is_initialised() should return False
        assert project.is_initialised() is False

    def test_is_initialised_returns_true_when_repo_dir_exists(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        repo_dir = os.path.join(workspace.path, project[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value])
        os.makedirs(repo_dir, exist_ok=True)
        assert project.is_initialised() is True

class TestGenerateProjectHash:
    def test_hash_is_five_chars(self):
        h = _generate_project_hash("/some/path/to/project")
        assert len(h) == 5

    def test_hash_is_hex(self):
        h = _generate_project_hash("/some/path/to/project")
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self):
        path = "/some/path/to/project"
        assert _generate_project_hash(path) == _generate_project_hash(path)

    def test_different_paths_produce_different_hashes(self):
        h1 = _generate_project_hash("/path/one")
        h2 = _generate_project_hash("/path/two")
        assert h1 != h2

class TestProjectHashInTemplates:
    @pytest.mark.parametrize("version", ["7.6", "8.0"])
    def test_project_hash_in_config(self, temp_workspace, version):
        project = temp_workspace.create_project("hash_test", make_create_args(version=version))
        project_hash = project.get_project_hash()
        assert len(project_hash) == 5

    @pytest.mark.parametrize("version", ["7.5", "7.4"])
    def test_pre_7_6_project_hash_is_ignored(self, temp_workspace, version):
        project = temp_workspace.create_project("legacy_hash_test", make_create_args(version=version))
        assert _version_supports_project_hash(version) is False
        assert project.get_project_hash() == ""

    @pytest.mark.parametrize("version", ["7.6", "8.0"])
    def test_no_hash_token_remains_in_files(self, temp_workspace, version):
        temp_workspace.create_project("myhashproj", make_create_args(version=version))
        project_path = os.path.join(temp_workspace._get_ac_directory_path(), "myhashproj")
        for root, dirs, files in os.walk(project_path):
            for fname in files:
                with open(os.path.join(root, fname)) as f:
                    content = f.read()
                assert REPLACE_TOKEN_HASH not in content, f"Token {REPLACE_TOKEN_HASH} still present in {fname}"

    @pytest.mark.parametrize("version", ["7.6", "8.0"])
    def test_hash_present_in_compose_files(self, temp_workspace, version):
        project = temp_workspace.create_project("hashcomp", make_create_args(version=version))
        project_hash = project.get_project_hash()
        project_path = os.path.join(temp_workspace._get_ac_directory_path(), "hashcomp")
        deps_path = os.path.join(project_path, "docker-compose-dependencies.yml")
        with open(deps_path) as f:
            content = f.read()
        assert project_hash in content

    @pytest.mark.parametrize("version", ["7.5", "7.4"])
    def test_older_templates_unaffected(self, temp_workspace, version):
        # Older templates do not have {{project_hash}} tokens and should ignore hash usage.
        project = temp_workspace.create_project("oldproj", make_create_args(version=version))
        project_hash = project.get_project_hash()
        assert project_hash == ""
        # Verify config remains backward compatible for old templates.
        reloaded = temp_workspace.get_project("oldproj")
        assert reloaded.get_project_hash() == ""
        assert AcProjectAttributes.PROJECT_HASH.value not in reloaded._config
        # Verify compose files do NOT contain the hash (old templates don't use it)
        project_path = os.path.join(temp_workspace._get_ac_directory_path(), "oldproj")
        deps_path = os.path.join(project_path, "docker-compose-dependencies.yml")
        if os.path.exists(deps_path):
            with open(deps_path) as f:
                content = f.read()
            assert REPLACE_TOKEN_HASH not in content

class TestAcProjectAttributes:
    def test_project_settings_enum(self):
        assert str(AcProjectAttributes.PROJECT_NAME) == "project_name"
        assert str(AcProjectAttributes.PROJECT_NAME_URLSAFE) == "project_name_url_safe"
        assert str(AcProjectAttributes.PROJECT_ARCHES_VERSION) == "arches_version"


class TestIsVersionSupported:
    @pytest.mark.parametrize("version", ["7.6", "7.7", "8.0", "9.0"])
    def test_supported_versions(self, version):
        assert _is_version_supported(version) is True

    @pytest.mark.parametrize("version", ["6.1", "6.2", "7.0", "7.1", "7.2", "7.3", "7.4", "7.5"])
    def test_unsupported_versions(self, version):
        assert _is_version_supported(version) is False

    def test_invalid_version_returns_false(self):
        assert _is_version_supported("invalid") is False
        assert _is_version_supported("") is False
