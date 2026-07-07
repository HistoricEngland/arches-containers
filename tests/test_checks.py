"""
Unit tests for system checks module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
from arches_containers.utils.checks import (
    CheckStatus,
    CheckResult,
    AggregatedCheckResult,
    SystemCheck,
    DockerInstalled,
    DockerDaemonRunning,
    DockerComposeInstalled,
    GitInstalled,
    DiskSpaceAvailable,
    PortAvailable,
    DependenciesCheck,
    WorkspaceCheck,
    ConfigurationCheck,
)


class TestCheckStatus:
    """Test CheckStatus enum."""
    
    def test_check_status_values(self):
        """Verify CheckStatus enum has expected values."""
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.WARN.value == "warn"
        assert CheckStatus.FAIL.value == "fail"


class TestCheckResult:
    """Test CheckResult dataclass."""
    
    def test_check_result_creation(self):
        """Test creating a CheckResult."""
        result = CheckResult(
            status=CheckStatus.PASS,
            title="Test Check",
            message="Test passed"
        )
        assert result.status == CheckStatus.PASS
        assert result.title == "Test Check"
        assert result.message == "Test passed"
        assert result.details == []
        assert result.remediation is None
    
    def test_check_result_with_details(self):
        """Test CheckResult with details."""
        result = CheckResult(
            status=CheckStatus.WARN,
            title="Test Warning",
            message="Warning message",
            details=["Detail 1", "Detail 2"]
        )
        assert len(result.details) == 2


class TestAggregatedCheckResult:
    """Test AggregatedCheckResult."""
    
    def test_all_pass(self):
        """Test all_pass property."""
        results = [
            CheckResult(CheckStatus.PASS, "Check 1", "Passed"),
            CheckResult(CheckStatus.PASS, "Check 2", "Passed"),
        ]
        agg = AggregatedCheckResult(results)
        assert agg.all_pass is True
        assert agg.has_failures is False
        assert agg.has_warnings is False
    
    def test_has_failures(self):
        """Test has_failures property."""
        results = [
            CheckResult(CheckStatus.PASS, "Check 1", "Passed"),
            CheckResult(CheckStatus.FAIL, "Check 2", "Failed"),
        ]
        agg = AggregatedCheckResult(results)
        assert agg.has_failures is True
    
    def test_has_warnings(self):
        """Test has_warnings property."""
        results = [
            CheckResult(CheckStatus.PASS, "Check 1", "Passed"),
            CheckResult(CheckStatus.WARN, "Check 2", "Warning"),
        ]
        agg = AggregatedCheckResult(results)
        assert agg.has_warnings is True
    
    def test_exit_code_pass(self):
        """Test exit code for all passing."""
        results = [CheckResult(CheckStatus.PASS, "Check", "Passed")]
        agg = AggregatedCheckResult(results)
        assert agg.exit_code() == 0
    
    def test_exit_code_fail(self):
        """Test exit code for failure."""
        results = [CheckResult(CheckStatus.FAIL, "Check", "Failed")]
        agg = AggregatedCheckResult(results)
        assert agg.exit_code() == 1
    
    def test_exit_code_warn(self):
        """Test exit code for warnings."""
        results = [
            CheckResult(CheckStatus.PASS, "Check 1", "Passed"),
            CheckResult(CheckStatus.WARN, "Check 2", "Warning"),
        ]
        agg = AggregatedCheckResult(results)
        assert agg.exit_code() == 2


class TestSystemCheck:
    """Test SystemCheck base class utilities."""
    
    def test_is_port_available_true(self):
        """Test port availability check when port is free."""
        # Use a high port number unlikely to be in use
        assert SystemCheck._is_port_available(19999) is True
    
    def test_is_command_available_git(self):
        """Test command availability - git should be available."""
        assert SystemCheck._is_command_available("git") is True
    
    def test_is_command_available_nonexistent(self):
        """Test command availability for nonexistent command."""
        assert SystemCheck._is_command_available("nonexistent_cmd_xyz") is False
    
    def test_get_disk_free_gb(self):
        """Test disk space check returns positive value."""
        free_gb = SystemCheck._get_disk_free_gb("/")
        assert free_gb > 0


class TestDockerChecks:
    """Test Docker-related checks."""
    
    @patch('arches_containers.utils.checks.SystemCheck._run_command')
    def test_docker_installed_pass(self, mock_run):
        """Test Docker installed check when Docker is available."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker version 20.10.0")
        check = DockerInstalled()
        result = check.run()
        assert result.status == CheckStatus.PASS
        assert "Docker installed" in result.title
    
    @patch('arches_containers.utils.checks.SystemCheck._run_command')
    def test_docker_installed_fail(self, mock_run):
        """Test Docker installed check when Docker is not available."""
        mock_run.side_effect = RuntimeError("Docker not found")
        check = DockerInstalled()
        result = check.run()
        assert result.status == CheckStatus.FAIL
        assert result.remediation is not None


class TestGitCheck:
    """Test Git checks."""
    
    @patch('arches_containers.utils.checks.SystemCheck._run_command')
    def test_git_installed_pass(self, mock_run):
        """Test Git installed check when Git is available."""
        mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.32.0")
        check = GitInstalled()
        result = check.run()
        assert result.status == CheckStatus.PASS


class TestDiskSpaceCheck:
    """Test disk space checks."""
    
    def test_disk_space_sufficient(self):
        """Test disk space check when sufficient space available."""
        check = DiskSpaceAvailable(min_gb=1.0)
        result = check.run()
        # Should pass since we have more than 1GB
        assert result.status in [CheckStatus.PASS, CheckStatus.WARN]


class TestDependenciesCheck:
    """Test comprehensive dependencies check."""
    
    def test_dependencies_check_structure(self):
        """Test DependenciesCheck runs all sub-checks."""
        check = DependenciesCheck()
        result = check.run()
        
        # Should have aggregated result
        assert result.status in [CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL]
        assert result.title is not None
        assert result.message is not None
        assert len(result.details) > 0


class TestWorkspaceCheck:
    """Test workspace integrity checks."""
    
    def test_workspace_check_structure(self):
        """Test WorkspaceCheck basic structure."""
        check = WorkspaceCheck()
        result = check.run()
        
        # Should complete without error
        assert result.status in [CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL]
        assert result.title is not None
        assert result.message is not None
    
    def test_find_all_workspaces(self):
        """Test finding all workspaces in directory tree."""
        workspaces = WorkspaceCheck._find_all_workspaces()
        # Should return a list (possibly empty if no workspaces exist)
        assert isinstance(workspaces, list)

    def test_workspace_warns_when_active_workspace_outside_cwd(self, monkeypatch):
        """Warn when active workspace path is outside the current directory path."""
        monkeypatch.setattr("arches_containers.utils.checks.os.getcwd", lambda: "/Users/test/workspace")
        monkeypatch.setattr(WorkspaceCheck, "_find_all_workspaces", staticmethod(lambda: ["/opt/other-workspace"]))
        monkeypatch.setattr(WorkspaceCheck, "_determine_active_workspace", staticmethod(lambda _ws: "/opt/other-workspace"))

        check = WorkspaceCheck()
        result = check.run()

        assert result.status == CheckStatus.WARN
        assert "outside the current directory path" in result.message

    def test_workspace_no_warning_when_active_workspace_is_ancestor(self, monkeypatch):
        """Do not warn when active workspace is an ancestor of the current directory."""
        monkeypatch.setattr("arches_containers.utils.checks.os.getcwd", lambda: "/Users/test/workspace/project")
        monkeypatch.setattr(WorkspaceCheck, "_find_all_workspaces", staticmethod(lambda: ["/Users/test/workspace"]))
        monkeypatch.setattr(WorkspaceCheck, "_determine_active_workspace", staticmethod(lambda _ws: "/Users/test/workspace"))

        check = WorkspaceCheck()
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert "outside current directory" not in result.message

    def test_format_workspace_tree_labels(self, monkeypatch):
        """Workspace tree should label entries as active/parent instead of current."""
        monkeypatch.setattr("arches_containers.utils.checks.os.getcwd", lambda: "/tmp/ws/project")
        monkeypatch.setattr("arches_containers.utils.checks.Path.home", lambda: Path("/tmp"))
        monkeypatch.setattr(WorkspaceCheck, "_count_projects", staticmethod(lambda _path: 0))

        lines = WorkspaceCheck._format_workspace_tree(
            ["/tmp/ws/project", "/tmp", "/tmp/ws"],
            "/tmp/ws/project",
        )

        joined = "\n".join(lines)
        assert "(active)" in joined
        assert "(home workspace)" in joined
        assert "(ancestor workspace)" in joined
        assert "(current)" not in joined


class TestConfigurationCheck:
    """Test project configuration checks."""

    def test_aggregate_config_remediation_failed_only(self):
        """Configuration remediation should only aggregate failed checks and label them."""
        results = [
            CheckResult(
                status=CheckStatus.WARN,
                title="Project 'warn_project'",
                message="Port in use",
                remediation="\n🔧 Warning remediation"
            ),
            CheckResult(
                status=CheckStatus.FAIL,
                title="Project 'failed_project'",
                message="Repo missing",
                remediation="\n🔧 Fix failed project"
            ),
        ]

        remediation = ConfigurationCheck._aggregate_config_remediation(results)

        assert remediation is not None
        assert "failed checks only" in remediation.lower()
        assert "Failed check: Project 'failed_project'" in remediation
        assert "Warning remediation" not in remediation

    def test_port_available_high_port(self):
        """Test port check utility used by configuration checks."""
        check = PortAvailable(19999, "Test Service")
        result = check.run()
        assert result.status == CheckStatus.PASS
    
    def test_is_valid_hash_valid(self):
        """Test hash validation for valid hash."""
        assert ConfigurationCheck._is_valid_hash("a1b2c") is True
        assert ConfigurationCheck._is_valid_hash("00000") is True
    
    def test_is_valid_hash_invalid_length(self):
        """Test hash validation for invalid length."""
        assert ConfigurationCheck._is_valid_hash("a1b2") is False
        assert ConfigurationCheck._is_valid_hash("a1b2cd") is False
    
    def test_is_valid_hash_invalid_chars(self):
        """Test hash validation for invalid characters."""
        assert ConfigurationCheck._is_valid_hash("ZZZZZ") is False
        assert ConfigurationCheck._is_valid_hash("G1B2C") is False
    
    def test_is_version_old_old(self):
        """Test version check for old version."""
        assert ConfigurationCheck._is_version_old("6.2") is True
        assert ConfigurationCheck._is_version_old("7.5") is True
    
    def test_is_version_old_new(self):
        """Test version check for supported version."""
        assert ConfigurationCheck._is_version_old("7.6") is False
        assert ConfigurationCheck._is_version_old("8.0") is False
    
    def test_check_repo_directory_found_with_expected_name(self, tmp_path):
        """Test repo directory check when found with expected project_repo_directory."""
        # Setup temporary workspace with repo
        repo_dir = tmp_path / "my-custom-repo"
        repo_dir.mkdir()
        (repo_dir / "manage.py").touch()
        
        config = {
            "project_repo_directory": "my-custom-repo",
            "project_name": "test_project"
        }
        
        check = ConfigurationCheck({})
        result = check._check_repo_directory(str(tmp_path), "test_project", config)
        
        assert result.status == CheckStatus.PASS
        assert "exists" in result.message.lower()
    
    def test_check_repo_directory_found_with_project_name_only_old_config(self, tmp_path):
        """Test repo directory check when found with project_name (old config without project_repo_directory)."""
        # Setup temporary workspace with repo matching project_name
        repo_dir = tmp_path / "test_project"
        repo_dir.mkdir()
        (repo_dir / "manage.py").touch()
        
        # Old config without project_repo_directory field
        config = {
            "project_name": "test_project"
        }
        
        check = ConfigurationCheck({})
        result = check._check_repo_directory(str(tmp_path), "test_project", config)
        
        # Should pass for old configs with matching project_name
        assert result.status == CheckStatus.PASS
        assert "exists" in result.message.lower()
    
    def test_check_repo_directory_found_with_different_name_new_config(self, tmp_path):
        """Test repo directory check when found with different name (new config with project_repo_directory)."""
        # Setup temporary workspace with repo matching project_name, not config expectation
        repo_dir = tmp_path / "test_project"
        repo_dir.mkdir()
        (repo_dir / "manage.py").touch()
        
        # New config with explicit project_repo_directory that doesn't match
        config = {
            "project_repo_directory": "expected-repo",
            "project_name": "test_project"
        }
        
        check = ConfigurationCheck({})
        result = check._check_repo_directory(str(tmp_path), "test_project", config)
        
        # Should warn when config has project_repo_directory and we find different
        assert result.status == CheckStatus.WARN
        assert "naming" in result.message.lower() or "found" in result.message.lower()
        assert result.remediation is not None
    
    def test_check_repo_directory_not_found_old_config(self, tmp_path):
        """Test repo directory check when repo not found (old config)."""
        # Setup temporary workspace with no repo
        config = {
            "project_name": "test_project"
        }
        
        check = ConfigurationCheck({})
        result = check._check_repo_directory(str(tmp_path), "test_project", config)
        
        assert result.status == CheckStatus.FAIL
        assert "not found" in result.message.lower()
        assert result.remediation is not None
    
    def test_check_repo_directory_infer_from_project_name_hyphen_variant(self, tmp_path):
        """Test repo directory inference with hyphen/underscore variants."""
        # Setup with hyphenated version of project_name
        repo_dir = tmp_path / "test-project"
        repo_dir.mkdir()
        (repo_dir / "manage.py").touch()
        
        # Old config missing project_repo_directory
        config = {
            "project_name": "test_project"
        }
        
        check = ConfigurationCheck({})
        result = check._check_repo_directory(str(tmp_path), "test_project", config)
        
        # Should find it with variant naming and pass (old config behavior)
        assert result.status == CheckStatus.PASS

    def test_extract_project_ports_from_compose_and_config(self, tmp_path):
        """Test extracting ports from docker compose files and config values."""
        repo_dir = tmp_path / "test_project"
        repo_dir.mkdir()
        (repo_dir / "manage.py").touch()
        (repo_dir / "docker-compose.yml").write_text(
            "services:\n"
            "  app:\n"
            "    ports:\n"
            "      - '8123:8000'\n"
            "  search:\n"
            "    ports:\n"
            "      - \"${ELASTIC_PORT:-9201}:9200\"\n",
            encoding="utf-8",
        )

        config = {
            "project_name": "test_project",
            "custom_port": "9001",
        }

        ports = ConfigurationCheck._extract_project_ports(repo_dir, config)
        assert 8123 in ports
        assert 9201 in ports
        assert 9001 in ports

    def test_format_config_results_includes_all_project_findings(self):
        """Configuration output should include all per-project warning/failure details."""
        result = CheckResult(
            status=CheckStatus.FAIL,
            title="Project 'example'",
            message="❌ 1 failure(s), 2 warning(s)",
            details=[
                "[FAIL] Repository directory missing",
                "[WARN] Port 5433 is already in use",
                "[WARN] Arches version 6.2 is old (< 7.6)",
            ],
        )

        lines = ConfigurationCheck._format_config_results([result])

        assert any("Project 'example': 1 failure(s), 2 warning(s)" in line for line in lines)
        assert any("Repository directory missing" in line for line in lines)
        assert any("Port 5433 is already in use" in line for line in lines)
        assert any("Arches version 6.2 is old" in line for line in lines)

    def test_check_project_mismatched_config_project_name_is_failure(self, tmp_path):
        """Mismatched config project_name should fail while preserving warnings."""
        project_name = "warden"
        project_dir = tmp_path / ".arches_containers" / project_name
        project_dir.mkdir(parents=True)

        config = {
            "project_name": "wardenx",
            "project_name_url_safe": "warden",
            "arches_version": "6.2",
        }
        with open(project_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f)

        class FakeProject:
            def get_project_path(self):
                return str(project_dir)

        class FakeWorkspace:
            path = str(tmp_path)

            def get_project(self, _name):
                return FakeProject()

        check = ConfigurationCheck(project_name=project_name)

        with patch.object(ConfigurationCheck, "_check_repo_directory", return_value=CheckResult(
            status=CheckStatus.PASS,
            title="Repository directory found",
            message="✅ Repository directory exists"
        )), patch.object(ConfigurationCheck, "_extract_project_ports", return_value=[]):
            result = check._check_project(FakeWorkspace(), project_name)

        assert result.status == CheckStatus.FAIL
        assert "1 failure(s), 1 warning(s)" in result.message
        assert any("does not match workspace project" in d for d in result.details)
        assert any("Arches version 6.2 is old" in d for d in result.details)




class TestCheckResultFormatting:
    """Test output formatting for check results."""
    
    def test_remediation_formatting(self):
        """Test remediation step formatting."""
        title = "Install Docker"
        steps = ["Visit https://docker.com", "Download Docker Desktop", "Install"]
        formatted = SystemCheck._format_remediation(title, steps)
        
        assert "Install Docker" in formatted
        assert "- Visit" in formatted
        assert "- Download" in formatted
        assert "- Install" in formatted
    
    def test_dependencies_message_aggregation(self):
        """Test message aggregation for dependencies check."""
        results = [
            CheckResult(CheckStatus.PASS, "Check 1", "Passed"),
            CheckResult(CheckStatus.FAIL, "Check 2", "Failed"),
        ]
        message = DependenciesCheck._aggregate_message(results)
        assert "critical issue" in message or "failed" in message.lower()
    
    def test_sub_results_formatting(self):
        """Test formatting of sub-check results."""
        results = [
            CheckResult(CheckStatus.PASS, "Git", "✅ Passed"),
            CheckResult(CheckStatus.WARN, "Docker", "⚠️  Warning"),
        ]
        formatted = DependenciesCheck._format_sub_results(results)
        
        assert len(formatted) == 2
        assert "✅" in formatted[0]
        assert "⚠️" in formatted[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
