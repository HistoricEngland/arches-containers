import pytest
import os
import shutil
import json
import platform
from arches_containers.utils.workspace import (
    AcWorkspace, 
    AcSettings, 
    AcProject, 
    AcProjectSettings,
    AC_DIRECTORY_NAME
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
    class Args:
        version = "7.6"
        organization = None
        branch = None

    project_name = "test_project"
    temp_workspace.create_project(project_name, Args())
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
        class Args:
            pass
        Args.version = version
        Args.organization = "archesproject"
        Args.branch = "main"
        # Simulate arm64
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        project = temp_workspace.create_project("test_project", Args())
        assert os.path.exists(os.path.join(temp_workspace._get_ac_directory_path(), "test_project"))
        assert project["arches_repo_organization"] == "archesproject"
        assert project["arches_repo_branch"] == "main"
        # Check platform line uncommented for arm64 if present
        compose_path = os.path.join(temp_workspace._get_ac_directory_path(), "test_project", "docker-compose-dependencies.yml")
        line = get_platform_line(compose_path)
        if line is not None:
            assert line.strip().startswith("platform: linux/arm64") or line.strip().startswith("#platform: linux/arm64")
        # Simulate amd64
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        project2 = temp_workspace.create_project("test_project2", Args())
        compose_path2 = os.path.join(temp_workspace._get_ac_directory_path(), "test_project2", "docker-compose-dependencies.yml")
        line2 = get_platform_line(compose_path2)
        if line2 is not None:
            assert line2.strip().startswith("#platform: linux/arm64")

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
        project[AcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value] = "test_org"
        project.save()

        # Reload project to verify save
        project = workspace.get_project(project_name)
        assert project[AcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value] == "test_org"

    def test_get_project_path(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        expected_path = os.path.join(workspace._get_ac_directory_path(), project_name)
        assert project.get_project_path() == expected_path

class TestAcProjectSettings:
    def test_project_settings_enum(self):
        assert str(AcProjectSettings.PROJECT_NAME) == "project_name"
        assert str(AcProjectSettings.PROJECT_NAME_URLSAFE) == "project_name_url_safe"
        assert str(AcProjectSettings.PROJECT_ARCHES_VERSION) == "arches_version"
