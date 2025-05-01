import pytest
import os
import shutil
import json
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

class TestAcWorkspace:
    def test_workspace_creation(self, temp_workspace):
        assert os.path.exists(os.path.join(temp_workspace.path, AC_DIRECTORY_NAME))

    def test_create_project(self, temp_workspace):
        class Args:
            version = "7.6"
            organization = "archesproject"
            branch = "main"

        project = temp_workspace.create_project("test_project", Args())
        assert os.path.exists(os.path.join(temp_workspace._get_ac_directory_path(), "test_project"))
        assert project["arches_repo_organization"] == "archesproject"
        assert project["arches_repo_branch"] == "main"

    def test_list_projects(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        projects = workspace.list_projects()
        assert project_name in projects

    def test_delete_project(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        workspace.delete_project(project_name)
        assert project_name not in workspace.list_projects()

    def test_get_project(self, workspace_with_project):
        workspace, project_name = workspace_with_project
        project = workspace.get_project(project_name)
        assert isinstance(project, AcProject)
        assert project.project_name == project_name

    def test_export_project(self, workspace_with_project, tmp_path):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        workspace.export_project(project_name, str(repo_path))
        assert os.path.exists(os.path.join(repo_path, f".ac_{project_name}"))

    def test_import_project(self, workspace_with_project, tmp_path):
        workspace, project_name = workspace_with_project
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # First export the project
        workspace.export_project(project_name, str(repo_path))
        
        # Delete original project
        workspace.delete_project(project_name)
        
        # Import project back
        workspace.import_project(project_name, str(repo_path))
        assert project_name in workspace.list_projects()

class TestAcSettings:
    def test_settings_creation(self, temp_workspace):
        settings = temp_workspace.get_settings()
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
