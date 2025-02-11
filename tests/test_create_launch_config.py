import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from arches_containers.utils.create_launch_config import create_launch_config

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

def test_create_launch_config_no_vscode_dir(mock_workspace, mock_os_path_exists, mock_os_makedirs, mock_open_file, mock_input):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = os.path.join("fake", "workspace_a")
    mock_os_path_exists.side_effect = lambda path: path != os.path.join("fake", "workspace_a", ".vscode")
    mock_input.return_value = 'y'

    # Act
    create_launch_config()

    # Assert
    mock_os_makedirs.assert_called_once_with(os.path.join("fake", "workspace_a", ".vscode"))
    mock_open_file.assert_called_once_with(os.path.join("fake", "workspace_a", ".vscode", "launch.json"), "w")
    mock_open_file().write.assert_called()
    assert mock_open_file().write.call_count > 1

def test_create_launch_config_launch_json_exists_no_override(mock_workspace, mock_os_path_exists, mock_input, mock_open_file):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = os.path.join("fake", "workspace_b")
    mock_os_path_exists.side_effect = lambda path: path in [os.path.join("fake", "workspace_b", ".vscode"), os.path.join("fake", "workspace_b", ".vscode", "launch.json")]
    mock_input.return_value = 'n'

    # Act
    create_launch_config()

    # Assert
    mock_input.assert_called_once_with("launch.json already exists. Do you want to override it? (y/n): ")
    mock_open_file.assert_not_called()

def test_create_launch_config_launch_json_exists_override(mock_workspace, mock_os_path_exists, mock_input, mock_open_file):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = os.path.join("fake", "workspace_c")
    mock_os_path_exists.side_effect = lambda path: path in [os.path.join("fake", "workspace_c", ".vscode"), os.path.join("fake", "workspace_c", ".vscode", "launch.json")]
    mock_input.return_value = 'y'

    # Act
    create_launch_config()

    # Assert
    mock_input.assert_called_once_with("launch.json already exists. Do you want to override it? (y/n): ")
    mock_open_file.assert_called_once_with(os.path.join("fake", "workspace_c", ".vscode", "launch.json"), "w")
    assert mock_open_file().write.call_count > 1

def test_create_launch_config_no_launch_json(mock_workspace, mock_os_path_exists, mock_os_makedirs, mock_open_file):
    # Arrange
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = os.path.join("fake", "workspace1")
    mock_os_path_exists.side_effect = lambda path: path in [
        os.path.join("fake", "workspace2", ".vscode")
    ]

    # Act
    create_launch_config()

    # Assert
    mock_os_makedirs.assert_called_once_with(os.path.join("fake", "workspace1", ".vscode"))
    mock_open_file.assert_called_once_with(os.path.join("fake", "workspace1", ".vscode", "launch.json"), "w")
    assert mock_open_file().write.call_count > 1

def test_create_launch_config_vscode_dir_exists(mock_workspace, mock_os_path_exists, mock_os_makedirs, mock_open_file, mock_input):
    mock_workspace_instance = mock_workspace.return_value
    mock_workspace_instance.path = os.path.join("fake", "workspace2")

    # First scenario: only .vscode folder exists
    mock_os_path_exists.side_effect = lambda path: path == os.path.join("fake", "workspace2", ".vscode")

    # Provide two inputs in sequence (one for each create_launch_config call)
    mock_input.side_effect = ['n', 'y']

    # First call: should skip overriding
    create_launch_config()
    mock_open_file.assert_called_once_with(os.path.join("fake", "workspace2", ".vscode", "launch.json"), "w")

    # Now pretend the launch.json also exists
    mock_workspace_instance.path = os.path.join("fake", "workspace2")
    mock_os_path_exists.side_effect = lambda path: path in [
        os.path.join("fake", "workspace2", ".vscode"),
        os.path.join("fake", "workspace2", ".vscode", "launch.json"),
    ]
    
    # Second call: should override
    create_launch_config()
    mock_open_file().write.assert_called()
    assert mock_open_file().write.call_count > 1