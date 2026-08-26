import os
import pytest
from unittest.mock import patch, MagicMock
from arches_containers.utils.arches_repo_helper import _get_repo_info, derive_repo_directory_name, clone_repository

@pytest.fixture
def mock_workspace():
    with patch('arches_containers.utils.arches_repo_helper.AcWorkspace') as MockAcWorkspace:
        yield MockAcWorkspace

@pytest.fixture
def mock_project_settings():
    with patch('arches_containers.utils.arches_repo_helper.AcProjectAttributes') as MockAcProjectAttributes:
        yield MockAcProjectAttributes

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
    @patch('arches_containers.utils.arches_repo_helper.AcProjectAttributes')
    def test_get_repo_info(self, MockAcProjectAttributes, MockAcWorkspace):
        # Arrange
        project_name = "test_project"
        mock_workspace = MockAcWorkspace.return_value
        mock_config = {
            MockAcProjectAttributes.PROJECT_ARCHES_REPO_BRANCH.value: "main",
            MockAcProjectAttributes.PROJECT_ARCHES_REPO_ORGANIZATION.value: "test_org"
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


def test_derive_repo_directory_name_handles_git_suffix():
    assert derive_repo_directory_name("https://github.com/archesproject/arches-lingo.git") == "arches-lingo"


def test_clone_repository_returns_false_if_target_exists(tmp_path):
    existing = tmp_path / "existing-repo"
    existing.mkdir()

    result = clone_repository("https://github.com/archesproject/arches-lingo.git", str(existing))

    assert result is False


def test_clone_repository_returns_true_on_success(tmp_path):
    target = tmp_path / "new-repo"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = clone_repository(
            "https://github.com/archesproject/arches-lingo.git",
            str(target),
        )

    assert result is True