import sys
from unittest.mock import patch, call
from arches_containers.main import main


def run_cli(args):
    sys.argv = ["arches-containers"] + args
    try:
        main()
    except SystemExit:
        pass


def test_activate_blocked_when_different_project_running():
    """Issue #99: activating a different project should fail when containers are running."""
    with patch("arches_containers.main.arches_repo_helper.clone_and_checkout_repo"), \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager") as mock_output:
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "project_a"
        mock_settings.get_active_project_name.return_value = "project_a"
        mock_workspace.return_value.is_active_project_running.return_value = True
        mock_workspace.return_value.get_project.return_value._config = {}
        mock_output.fail.side_effect = SystemExit(1)

        run_cli(["activate", "-p", "project_b"])

        mock_output.fail.assert_called_once()
        assert "project_a" in mock_output.fail.call_args[0][0]
        mock_settings.set_active_project.assert_not_called()


def test_activate_allowed_when_activating_same_project():
    """Issue #99: activating the already-active project should not be blocked even if containers are up."""
    with patch("arches_containers.main.arches_repo_helper.clone_and_checkout_repo"), \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager") as mock_output:
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "project_a"
        mock_settings.get_active_project_name.return_value = "project_a"
        mock_workspace.return_value.is_active_project_running.return_value = True
        mock_workspace.return_value.get_project.return_value._config = {}

        run_cli(["activate", "-p", "project_a"])

        mock_output.fail.assert_not_called()
        mock_settings.set_active_project.assert_called_once_with("project_a")


def test_activate_allowed_when_no_containers_running():
    """Issue #99: activating a different project should succeed when no containers are running."""
    with patch("arches_containers.main.arches_repo_helper.clone_and_checkout_repo"), \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager") as mock_output:
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "project_a"
        mock_settings.get_active_project_name.return_value = "project_a"
        mock_workspace.return_value.is_active_project_running.return_value = False
        mock_workspace.return_value.get_project.return_value._config = {}

        run_cli(["activate", "-p", "project_b"])

        mock_output.fail.assert_not_called()
        mock_settings.set_active_project.assert_called_once_with("project_b")
