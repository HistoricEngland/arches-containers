import subprocess
import sys
import os
from unittest.mock import patch
from arches_containers.main import main

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

def test_restart_with_app_flag():
    with patch("arches_containers.main.compose_project") as mock_compose, \
         patch("arches_containers.main.arches_repo_helper.change_arches_branch") as mock_branch, \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager"):
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "demo"
        run_cli(["restart", "-p", "demo", "--app"])
        # Should call down then up with app container type
        assert mock_compose.call_count == 2
        assert mock_compose.call_args_list[0][0][4] == "app"  # container_type for down
        assert mock_compose.call_args_list[1][0][4] == "app"  # container_type for up

def test_restart_with_dep_flag():
    with patch("arches_containers.main.compose_project") as mock_compose, \
         patch("arches_containers.main.arches_repo_helper.change_arches_branch") as mock_branch, \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager"):
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "demo"
        run_cli(["restart", "-p", "demo", "--dep"])
        # Should call down then up with dep container type
        assert mock_compose.call_count == 2
        assert mock_compose.call_args_list[0][0][4] == "dep"  # container_type for down
        assert mock_compose.call_args_list[1][0][4] == "dep"  # container_type for up

def test_up_with_app_flag():
    with patch("arches_containers.main.compose_project") as mock_compose, \
         patch("arches_containers.main.arches_repo_helper.change_arches_branch") as mock_branch, \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager"):
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "demo"
        run_cli(["up", "-p", "demo", "--app"])
        # Should call up with app container type
        assert mock_compose.call_count == 1
        assert mock_compose.call_args_list[0][0][4] == "app"  # container_type

def test_down_with_dep_flag():
    with patch("arches_containers.main.compose_project") as mock_compose, \
         patch("arches_containers.main.arches_repo_helper.change_arches_branch") as mock_branch, \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager"):
        mock_settings = mock_workspace.return_value.get_settings.return_value
        mock_settings.get_active_project.return_value.project_name = "demo"
        run_cli(["down", "-p", "demo", "--dep"])
        # Should call down with dep container type
        assert mock_compose.call_count == 1
        assert mock_compose.call_args_list[0][0][4] == "dep"  # container_type

def test_app_and_dep_flags_mutually_exclusive():
    """Test that --app and --dep flags cannot be used together"""

    
    # Get the directory containing this test file, then go up one level to the package root
    test_dir = os.path.dirname(os.path.abspath(__file__))
    package_root = os.path.dirname(test_dir)
    
    # Test with restart command
    result = subprocess.run([
        sys.executable, "-m", "arches_containers.main", 
        "restart", "-p", "demo", "--app", "--dep"
    ], capture_output=True, text=True, cwd=package_root)
    
    # Should exit with error code (argparse error)
    assert result.returncode != 0
    assert "not allowed with argument" in result.stderr or "mutually exclusive" in result.stderr
    
    # Test with up command  
    result = subprocess.run([
        sys.executable, "-m", "arches_containers.main",
        "up", "-p", "demo", "--app", "--dep"
    ], capture_output=True, text=True, cwd=package_root)
    
    # Should exit with error code (argparse error)
    assert result.returncode != 0
    assert "not allowed with argument" in result.stderr or "mutually exclusive" in result.stderr
    
    # Test with down command
    result = subprocess.run([
        sys.executable, "-m", "arches_containers.main",
        "down", "-p", "demo", "--app", "--dep"  
    ], capture_output=True, text=True, cwd=package_root)
    
    # Should exit with error code (argparse error)
    assert result.returncode != 0
    assert "not allowed with argument" in result.stderr or "mutually exclusive" in result.stderr
