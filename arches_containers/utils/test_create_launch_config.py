import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from .create_launch_config import create_launch_config

@pytest.fixture
def mock_workspace():
  with patch('arches_containers.utils.create_launch_config.AcWorkspace') as MockAcWorkspace:
    yield MockAcWorkspace

@pytest.fixture
def mock_os_path_exists():
  with patch('os.path.exists') as mock_exists:
    yield mock_exists

@pytest.fixture
def mock_os_makedirs():
  with patch('os.makedirs') as mock_makedirs:
    yield mock_makedirs

@pytest.fixture
def mock_input():
  with patch('builtins.input') as mock_input:
    yield mock_input

@pytest.fixture
def mock_open_file():
  with patch('builtins.open', mock_open()) as mock_file:
    yield mock_file

def test_create_launch_config_no_vscode_dir(mock_workspace, mock_os_path_exists, mock_os_makedirs, mock_open_file):
  # Arrange
  mock_workspace_instance = mock_workspace.return_value
@pytest.fixture
def mock_workspace():
    with patch('arches_containers.utils.create_launch_config.AcWorkspace') as MockAcWorkspace:
        yield MockAcWorkspace

@pytest.fixture
def mock_os_path_exists():
    with patch('os.path.exists') as mock_exists:
        yield mock_exists

@pytest.fixture
def mock_os_makedirs():
    with patch('os.makedirs') as mock_makedirs:
        yield mock_makedirs

@pytest.fixture
def mock_input():
    with patch('builtins.input') as mock_input:
        yield mock_input

@pytest.fixture
def mock_open_file():
    with patch('builtins.open', mock_open()) as mock_file:
        yield mock_file

def test_create_launch_config_no_vscode_dir(mock_workspace, mock_os_path_exists, mock_os_makedirs, mock_open_file):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = "/fake/workspace"
    mock_os_path_exists.side_effect = lambda path: path != "/fake/workspace/.vscode"

    # Act
    create_launch_config()

    # Assert
    mock_os_makedirs.assert_called_once_with("/fake/workspace/.vscode")
    mock_open_file.assert_called_once_with("/fake/workspace/.vscode/launch.json", "w")
    mock_open_file().write.assert_called_once()

def test_create_launch_config_launch_json_exists_no_override(mock_workspace, mock_os_path_exists, mock_input, mock_open_file):
  # Arrange
  mock_workspace_instance = mock_workspace.return_value
  mock_workspace_instance.path = "/fake/workspace"
  mock_os_path_exists.side_effect = lambda path: path in ["/fake/workspace/.vscode", "/fake/workspace/.vscode/launch.json"]
  mock_input.return_value = 'n'

  # Act
  create_launch_config()

  # Assert
  mock_input.assert_called_once_with("launch.json already exists. Do you want to override it? (y/n): ")
  mock_open_file.assert_not_called()

def test_create_launch_config_launch_json_exists_override(mock_workspace, mock_os_path_exists, mock_input, mock_open_file):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = "/fake/workspace"
    mock_os_path_exists.side_effect = lambda path: path in ["/fake/workspace/.vscode", "/fake/workspace/.vscode/launch.json"]
    mock_input.return_value = 'y'

    # Act
    create_launch_config()

    # Assert
    mock_input.assert_called_once_with("launch.json already exists. Do you want to override it? (y/n): ")
    mock_open_file.assert_called_once_with("/fake/workspace/.vscode/launch.json", "w")
    mock_open_file().write.assert_called_once()

def test_create_launch_config_no_launch_json(mock_workspace, mock_os_path_exists, mock_os_makedirs, mock_open_file):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = "/fake/workspace"
    mock_os_path_exists.side_effect = lambda path: path != "/fake/workspace/.vscode/launch.json"

    # Act
    create_launch_config()

    # Assert
    mock_os_makedirs.assert_called_once_with("/fake/workspace/.vscode")
    mock_open_file.assert_called_once_with("/fake/workspace/.vscode/launch.json", "w")
    mock_open_file().write.assert_called_once()

def test_create_launch_config_vscode_dir_exists(mock_workspace, mock_os_path_exists, mock_os_makedirs, mock_open_file):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = "/fake/workspace"
    mock_os_path_exists.side_effect = lambda path: path == "/fake/workspace/.vscode"

    # Act
    create_launch_config()

    # Assert
    mock_os_makedirs.assert_not_called()
    mock_open_file.assert_called_once_with("/fake/workspace/.vscode/launch.json", "w")
    mock_open_file().write.assert_called_once()
    mock_workspace_instance.path = "/fake/workspace"
    mock_os_path_exists.side_effect = lambda path: path in ["/fake/workspace/.vscode", "/fake/workspace/.vscode/launch.json"]
    mock_input.return_value = 'y'

    # Act
    create_launch_config()

    # Assert
    mock_input.assert_called_once_with("launch.json already exists. Do you want to override it? (y/n): ")
    mock_open_file.assert_called_once_with("/fake/workspace/.vscode/launch.json", "w")
    mock_open_file().write.assert_called_once()