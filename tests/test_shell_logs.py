import pytest
from unittest.mock import patch, MagicMock, call
from arches_containers.manage import shell_container, logs_container


@pytest.fixture
def mock_project():
    project = MagicMock()
    project.__getitem__ = MagicMock(side_effect=lambda key: "my-project" if key == "project_name_url_safe" else None)
    project.get_project_hash.return_value = "a1b2c"
    return project


@pytest.fixture
def mock_workspace(mock_project):
    with patch("arches_containers.manage.AcWorkspace") as mock_ws_cls:
        mock_ws = MagicMock()
        mock_ws.get_project.return_value = mock_project
        mock_ws_cls.return_value = mock_ws
        yield mock_ws_cls


def _make_subprocess_side_effect(inspect_running: bool | None, exec_returncode: int = 0):
    """
    Returns a side_effect function for subprocess.run that:
    - Responds to 'docker inspect' calls based on inspect_running
      (None → returncode=1 meaning not found, True/False → returncode=0 with stdout 'true'/'false')
    - Returns returncode=exec_returncode for all other docker commands
    """
    def side_effect(command, **kwargs):
        result = MagicMock()
        if "inspect" in command:
            if inspect_running is None:
                result.returncode = 1
                result.stdout = ""
            else:
                result.returncode = 0
                result.stdout = "true\n" if inspect_running else "false\n"
        else:
            result.returncode = exec_returncode
        return result
    return side_effect


@pytest.fixture
def mock_subprocess_running():
    """subprocess.run where the container is running."""
    with patch("arches_containers.manage.subprocess.run") as mock_run:
        mock_run.side_effect = _make_subprocess_side_effect(inspect_running=True)
        yield mock_run


# ── shell_container ──────────────────────────────────────────────────────────

class TestShellContainer:
    def test_default_container_opens_interactive_bash(self, mock_subprocess_running, mock_workspace):
        shell_container("my_project")
        mock_subprocess_running.assert_called_with(
            ["docker", "exec", "-it", "my-project-a1b2c", "/bin/bash"]
        )

    def test_explicit_container_name_is_used(self, mock_subprocess_running, mock_workspace):
        shell_container("my_project", container="custom-container")
        mock_subprocess_running.assert_called_with(
            ["docker", "exec", "-it", "custom-container", "/bin/bash"]
        )

    def test_exec_cmd_produces_non_interactive_call(self, mock_subprocess_running, mock_workspace):
        shell_container("my_project", exec_cmd="python manage.py show_graphs")
        mock_subprocess_running.assert_called_with(
            ["docker", "exec", "my-project-a1b2c", "sh", "-c", "python manage.py show_graphs"]
        )

    def test_exec_cmd_with_explicit_container(self, mock_subprocess_running, mock_workspace):
        shell_container("my_project", container="custom-container", exec_cmd="ls /app")
        mock_subprocess_running.assert_called_with(
            ["docker", "exec", "custom-container", "sh", "-c", "ls /app"]
        )

    def test_returns_returncode(self, mock_workspace):
        with patch("arches_containers.manage.subprocess.run") as mock_run:
            mock_run.side_effect = _make_subprocess_side_effect(inspect_running=True, exec_returncode=1)
            result = shell_container("my_project")
        assert result == 1

    def test_default_container_without_hash(self, mock_subprocess_running, mock_workspace, mock_project):
        mock_project.get_project_hash.return_value = ""
        result = shell_container("my_project")
        mock_subprocess_running.assert_called_with(
            ["docker", "exec", "-it", "my-project", "/bin/bash"]
        )
        assert result == 0

    def test_fails_when_container_not_found(self, mock_workspace):
        with patch("arches_containers.manage.subprocess.run") as mock_run, \
             patch("arches_containers.manage.AcOutputManager") as mock_output:
            mock_run.side_effect = _make_subprocess_side_effect(inspect_running=None)
            shell_container("my_project")
            mock_output.fail.assert_called_once()
            assert "not found" in mock_output.fail.call_args[0][0]

    def test_fails_when_container_stopped(self, mock_workspace):
        with patch("arches_containers.manage.subprocess.run") as mock_run, \
             patch("arches_containers.manage.AcOutputManager") as mock_output:
            mock_run.side_effect = _make_subprocess_side_effect(inspect_running=False)
            shell_container("my_project")
            mock_output.fail.assert_called_once()
            assert "not running" in mock_output.fail.call_args[0][0]


# ── logs_container ───────────────────────────────────────────────────────────

class TestLogsContainer:
    def test_default_container_shows_logs(self, mock_subprocess_running, mock_workspace):
        logs_container("my_project")
        mock_subprocess_running.assert_called_with(
            ["docker", "logs", "my-project-a1b2c"]
        )

    def test_follow_adds_flag(self, mock_subprocess_running, mock_workspace):
        logs_container("my_project", follow=True)
        mock_subprocess_running.assert_called_with(
            ["docker", "logs", "my-project-a1b2c", "-f"]
        )

    def test_explicit_container_name_is_used(self, mock_subprocess_running, mock_workspace):
        logs_container("my_project", container="custom-container")
        mock_subprocess_running.assert_called_with(
            ["docker", "logs", "custom-container"]
        )

    def test_explicit_container_with_follow(self, mock_subprocess_running, mock_workspace):
        logs_container("my_project", container="custom-container", follow=True)
        mock_subprocess_running.assert_called_with(
            ["docker", "logs", "custom-container", "-f"]
        )

    def test_returns_returncode(self, mock_workspace):
        with patch("arches_containers.manage.subprocess.run") as mock_run:
            mock_run.side_effect = _make_subprocess_side_effect(inspect_running=True, exec_returncode=1)
            result = logs_container("my_project")
        assert result == 1

    def test_default_container_without_hash(self, mock_subprocess_running, mock_workspace, mock_project):
        mock_project.get_project_hash.return_value = ""
        result = logs_container("my_project")
        mock_subprocess_running.assert_called_with(
            ["docker", "logs", "my-project"]
        )
        assert result == 0

    def test_fails_when_container_not_found(self, mock_workspace):
        with patch("arches_containers.manage.subprocess.run") as mock_run, \
             patch("arches_containers.manage.AcOutputManager") as mock_output:
            mock_run.side_effect = _make_subprocess_side_effect(inspect_running=None)
            logs_container("my_project")
            mock_output.fail.assert_called_once()
            assert "not found" in mock_output.fail.call_args[0][0]

    def test_fails_when_container_stopped_and_following(self, mock_workspace):
        with patch("arches_containers.manage.subprocess.run") as mock_run, \
             patch("arches_containers.manage.AcOutputManager") as mock_output:
            mock_run.side_effect = _make_subprocess_side_effect(inspect_running=False)
            logs_container("my_project", follow=True)
            mock_output.fail.assert_called_once()
            assert "not running" in mock_output.fail.call_args[0][0]

    def test_warns_and_proceeds_when_container_stopped(self, mock_workspace):
        with patch("arches_containers.manage.subprocess.run") as mock_run, \
             patch("arches_containers.manage.AcOutputManager") as mock_output:
            mock_run.side_effect = _make_subprocess_side_effect(inspect_running=False)
            logs_container("my_project")
        mock_output.warn.assert_called_once()
        assert "not running" in mock_output.warn.call_args[0][0]
        mock_run.assert_called_with(["docker", "logs", "my-project-a1b2c"])
