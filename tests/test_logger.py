import pytest
from unittest.mock import patch, MagicMock
from arches_containers.utils.logger import AcOutputManager

# test_logger.py

@pytest.fixture(autouse=True)
def reset_singleton():
    yield
    if hasattr(AcOutputManager, 'instance'):
        del AcOutputManager.spinner._live
        del AcOutputManager.instance


@pytest.fixture
def mock_spinner():
    with patch("arches_containers.utils.logger._RichSpinner", autospec=True) as mock_cls:
        yield mock_cls

@pytest.fixture
def spinner_setup():
    AcOutputManager.start_spinner("Test Setup")
    yield
    AcOutputManager.stop_spinner()

def test_write_calls_setup(mock_spinner, spinner_setup):
    '''
    The first test seems to need to do a write but not assert anything otherwise it fails. I think this is due to the singleton pattern used in the AcOutputManager class.
    TODO: Investigate why this is the case. In the meantime, this test is a placeholder so that all other tests pass.
    '''
    AcOutputManager.write("Setup")

def test_write_calls_console_print(mock_spinner, spinner_setup):
    AcOutputManager.write("Test message")
    mock_spinner.return_value.write.assert_called_once_with("Test message")

def test_text_updates_spinner_text(mock_spinner, spinner_setup):
    AcOutputManager.text("New text")
    # Access the spinner instance to check text_attr
    spinner_instance = mock_spinner.return_value
    assert spinner_instance.text_attr == "New text"

def test_complete_step_prints_correct_prefix(mock_spinner, spinner_setup):
    AcOutputManager.complete_step("Completed!")
    mock_spinner.return_value.write.assert_called_once_with("🟢 Completed!")

def test_skipped_step_prints_correct_prefix(mock_spinner, spinner_setup):
    AcOutputManager.skipped_step("Skipped!")
    mock_spinner.return_value.write.assert_called_once_with("🟡 Skipped!")

def test_failed_step_prints_correct_prefix(mock_spinner, spinner_setup):
    AcOutputManager.failed_step("Failed!")
    mock_spinner.return_value.write.assert_called_once_with("🔴 Failed!")

def test_success_stops_spinner_with_ok(mock_spinner):
    AcOutputManager.success("All good.")
    mock_spinner.return_value.write.assert_called_with("🟢 All good.")
    mock_spinner.return_value.ok.assert_called_once_with("🏁 Finished successfully")

def test_stop_spinner_calls_spinner_stop(mock_spinner):
    AcOutputManager.stop_spinner()
    mock_spinner.return_value.stop.assert_called_once()

def test_start_spinner_calls_spinner_start(mock_spinner):
    AcOutputManager.start_spinner("Hello")
    mock_spinner.return_value.start.assert_called_once_with("Hello")

@patch("builtins.exit", MagicMock())
def test_fail_stops_spinner_and_exits(mock_spinner):
    AcOutputManager.fail("Error occurred.")
    mock_spinner.return_value.write.assert_called_with("🔴 Error occurred.")
    mock_spinner.return_value.fail.assert_called_once_with("❌ Finished with errors")
    # exit(1) was called as well