import os
import pytest
from unittest.mock import patch, MagicMock
from arches_containers.utils.arches_repo_helper import _get_repo_info

@pytest.fixture
def mock_workspace():
    with patch('arches_containers.utils.arches_repo_helper.AcWorkspace') as MockAcWorkspace:
        yield MockAcWorkspace

@pytest.fixture
def mock_project_settings():
    with patch('arches_containers.utils.arches_repo_helper.AcProjectSettings') as MockAcProjectSettings:
        yield MockAcProjectSettings

def test_get_repo_info(mock_workspace, mock_project_settings):
    # Arrange
    project_name = "test_project"
    mock_workspace_instance = mock_workspace.return_value
    mock_config = {
        mock_project_settings.PROJECT_ARCHES_REPO_BRANCH.value: "main",
        mock_project_settings.PROJECT_ARCHES_REPO_ORGANIZATION.value: "test_org"
    }
    mock_workspace_instance.get_project.return_value = mock_config

    # Act
    config, repo_url, clone_dir, branch = _get_repo_info(project_name)

    # Assert
    assert config == mock_config
    assert repo_url == "https://github.com/test_org/arches.git"
    assert clone_dir == os.path.join(mock_workspace_instance.path, "arches")
    assert branch == "main"
    
import unittest
from unittest.mock import patch, MagicMock
from arches_containers.utils.arches_repo_helper import _get_repo_info

class TestArchesRepoHelper(unittest.TestCase):

    @patch('arches_containers.utils.arches_repo_helper.AcWorkspace')
    @patch('arches_containers.utils.arches_repo_helper.AcProjectSettings')
    def test_get_repo_info(self, MockAcProjectSettings, MockAcWorkspace):
        # Arrange
        project_name = "test_project"
        mock_workspace = MockAcWorkspace.return_value
        mock_config = {
            MockAcProjectSettings.PROJECT_ARCHES_REPO_BRANCH.value: "main",
            MockAcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value: "test_org"
        }
        mock_workspace.get_project.return_value = mock_config

        # Act
        config, repo_url, clone_dir, branch = _get_repo_info(project_name)

        # Assert
        self.assertEqual(config, mock_config)
        self.assertEqual(repo_url, "https://github.com/test_org/arches.git")
        self.assertEqual(clone_dir, os.path.join(mock_workspace.path, "arches"))
        self.assertEqual(branch, "main")

if __name__ == '__main__': 
    unittest.main()