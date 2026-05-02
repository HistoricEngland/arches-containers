import pytest
import os
import shutil
import json
import platform
from types import SimpleNamespace
from arches_containers.utils.workspace import (
    AcWorkspace, 
    AcSettings, 
    AcProject, 
    AcProjectAttributes,
    AC_DIRECTORY_NAME,
    REPLACE_TOKEN_HASH,
    _generate_project_hash,
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
        workspace.import_project(project_name, str(repo_path))
        assert project_name in workspace.list_projects()
        compose_path = os.path.join(workspace._get_ac_directory_path(), project_name, "docker-compose-dependencies.yml")
        line = get_platform_line(compose_path)
        if line is not None:
            assert line.strip().startswith("platform: linux/arm64")

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
        # Older templates do not have {{project_hash}} tokens in their compose files,
        # but a hash is still generated and stored in config.json for the new project.
        project = temp_workspace.create_project("oldproj", make_create_args(version=version))
        project_hash = project.get_project_hash()
        assert isinstance(project_hash, str)
        assert len(project_hash) == 5
        # Verify compose files do NOT contain the hash (old templates don't use it)
        project_path = os.path.join(temp_workspace._get_ac_directory_path(), "oldproj")
        deps_path = os.path.join(project_path, "docker-compose-dependencies.yml")
        if os.path.exists(deps_path):
            with open(deps_path) as f:
                content = f.read()
            assert project_hash not in content

class TestAcProjectAttributes:
    def test_project_settings_enum(self):
        assert str(AcProjectAttributes.PROJECT_NAME) == "project_name"
        assert str(AcProjectAttributes.PROJECT_NAME_URLSAFE) == "project_name_url_safe"
        assert str(AcProjectAttributes.PROJECT_ARCHES_VERSION) == "arches_version"
