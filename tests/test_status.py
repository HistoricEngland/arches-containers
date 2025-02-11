import pytest, json
from unittest.mock import patch, MagicMock
from arches_containers.utils.status import get_running_containers

@pytest.fixture
def mock_subprocess_run():
    with patch('arches_containers.utils.status.subprocess.run') as mock_run:
        yield mock_run

@pytest.fixture
def mock_ac_output_manager():
    with patch('arches_containers.utils.status.AcOutputManager') as mock_manager:
        yield mock_manager

def test_get_running_containers_no_containers(mock_subprocess_run, mock_ac_output_manager):
    # Arrange
    mock_subprocess_run.return_value.stdout = json.dumps({
        "Names": "fake_project_container",
        "Status": "Up 5 minutes"
    }) + "\n"
    project_name = "test_project"
    project_name_urlsafe = "test_project"

    # Act
    get_running_containers(project_name, project_name_urlsafe)

    # Assert
    mock_ac_output_manager.complete_step.assert_called_once_with(f"No {project_name} containers running.")

def test_get_running_containers_with_project_containers(mock_subprocess_run, mock_ac_output_manager):
    # Arrange
    mock_subprocess_run.return_value.stdout = json.dumps({
        "Names": "test_project_container",
        "Status": "Up 5 minutes"
    }) + "\n"
    project_name = "test_project"
    project_name_urlsafe = "test_project"

    # Act
    get_running_containers(project_name, project_name_urlsafe)

    # Assert
    mock_ac_output_manager.write.assert_called_once()
    assert "🟢 Running" in mock_ac_output_manager.write.call_args[0][0].get_string()

def test_get_running_containers_without_project_containers(mock_subprocess_run, mock_ac_output_manager):
    # Arrange
    mock_subprocess_run.return_value.stdout = json.dumps({
        "Names": "other_project_container",
        "Status": "Up 5 minutes"
    }) + "\n"
    project_name = "test_project"
    project_name_urlsafe = "test_project"

    # Act
    get_running_containers(project_name, project_name_urlsafe)

    # Assert
    mock_ac_output_manager.complete_step.assert_called_once_with(f"No {project_name} containers running.")

def test_get_running_containers_exception_handling(mock_subprocess_run, mock_ac_output_manager):
    # Arrange
    mock_subprocess_run.side_effect = Exception("Test exception")
    project_name = "test_project"
    project_name_urlsafe = "test_project"

    # Act
    get_running_containers(project_name, project_name_urlsafe)

    # Assert
    mock_ac_output_manager.fail.assert_called_once_with("An error occurred fetching status: Test exception")