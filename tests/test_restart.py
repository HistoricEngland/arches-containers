import pytest
from unittest.mock import patch
from arches_containers.main import main
import sys

# Helper to simulate CLI arguments
def run_cli(args):
    sys.argv = ["arches-containers"] + args
    try:
        main()
    except SystemExit:
        pass

def test_restart_runs_down_and_up():
    with patch("arches_containers.main.compose_project") as mock_compose, \
         patch("arches_containers.main.arches_repo_helper.change_arches_branch") as mock_branch, \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager"):
        # Simulate active project
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "demo"
        run_cli(["restart", "-p", "demo"])
        # Should call down then up
        assert mock_compose.call_count == 2
        assert mock_compose.call_args_list[0][0][1] == "down"
        assert mock_compose.call_args_list[1][0][1] == "up"

def test_restart_with_build_and_verbose():
    with patch("arches_containers.main.compose_project") as mock_compose, \
         patch("arches_containers.main.arches_repo_helper.change_arches_branch") as mock_branch, \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager"):
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "demo"
        run_cli(["restart", "-p", "demo", "-b", "-vb"])
        # Should call down (no build), then up (with build)
        assert mock_compose.call_count == 2
        assert mock_compose.call_args_list[0][0][2] is False  # build for down
        assert mock_compose.call_args_list[1][0][2] is True   # build for up
