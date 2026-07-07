"""
System checks for arches-containers pre-flight validation.

Provides a framework for checking system readiness before running arches-containers,
including dependency verification, workspace integrity, and configuration validation.
"""

import os
import re
import socket
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class CheckStatus(Enum):
    """Status of a system check."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    """Result of a single system check or sub-check."""
    status: CheckStatus
    title: str
    message: str
    details: Optional[List[str]] = field(default_factory=list)
    remediation: Optional[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = []


@dataclass
class AggregatedCheckResult:
    """Aggregated results from multiple checks."""
    checks: List[CheckResult]
    
    @property
    def all_pass(self) -> bool:
        """True if all checks passed."""
        return all(c.status == CheckStatus.PASS for c in self.checks)
    
    @property
    def has_failures(self) -> bool:
        """True if any check failed."""
        return any(c.status == CheckStatus.FAIL for c in self.checks)
    
    @property
    def has_warnings(self) -> bool:
        """True if any check has warnings (excluding failures)."""
        return any(c.status == CheckStatus.WARN for c in self.checks)
    
    def exit_code(self) -> int:
        """Return appropriate exit code: 0=pass, 1=fail, 2=warnings."""
        if self.has_failures:
            return 1
        if self.has_warnings:
            return 2
        return 0
    
    def summary(self) -> str:
        """Return summary string."""
        pass_count = sum(1 for c in self.checks if c.status == CheckStatus.PASS)
        warn_count = sum(1 for c in self.checks if c.status == CheckStatus.WARN)
        fail_count = sum(1 for c in self.checks if c.status == CheckStatus.FAIL)
        
        if self.has_failures:
            return f"❌ Top-level checks: {pass_count} passed, {warn_count} warnings, {fail_count} failed"
        elif self.has_warnings:
            return f"⚠️  Top-level checks: {pass_count} passed, {warn_count} warnings"
        else:
            return f"✅ Top-level checks: {pass_count} passed"


class SystemCheck(ABC):
    """Abstract base class for system checks."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    @abstractmethod
    def run(self) -> CheckResult:
        """Run the check and return a CheckResult."""
        pass
    
    @staticmethod
    def _run_command(
        cmd: List[str],
        capture_output: bool = True,
        text: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command safely.
        
        Args:
            cmd: Command as list of strings
            capture_output: Whether to capture stdout/stderr
            text: Whether to decode output as text
            
        Returns:
            CompletedProcess result
        """
        try:
            return subprocess.run(
                cmd,
                capture_output=capture_output,
                text=text,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            raise RuntimeError(f"Command not found: {cmd[0]}")
    
    @staticmethod
    def _is_command_available(cmd: str) -> bool:
        """Check if a command is available in PATH."""
        result = subprocess.run(
            ["which", cmd],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    
    @staticmethod
    def _is_port_available(port: int) -> bool:
        """Check if a port is available (not in use)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return True
        except OSError:
            return False
    
    @staticmethod
    def _get_disk_free_gb(path: str = "/") -> float:
        """Get free disk space in GB."""
        try:
            stat = shutil.disk_usage(path)
            return stat.free / (1024 ** 3)
        except Exception:
            return -1.0
    
    @staticmethod
    def _format_remediation(title: str, steps: List[str]) -> str:
        """Format remediation steps for display."""
        lines = [f"\n   {title}:"]
        for step in steps:
            if step.strip():
                lines.append(f"   - {step}")
            else:
                lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _strip_status_prefix(message: str) -> str:
        """Remove leading status icon prefixes from a message string."""
        if not isinstance(message, str):
            return message

        prefixes = ["✅ ", "⚠️  ", "⚠️ ", "❌ "]
        cleaned = message

        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].lstrip()
                    changed = True

        return cleaned


# ============================================================================
# Reusable Basic Checks
# ============================================================================

class DockerInstalled(SystemCheck):
    """Check if Docker is installed."""
    
    def run(self) -> CheckResult:
        try:
            result = self._run_command(["docker", "--version"])
            if result.returncode == 0:
                version = result.stdout.strip()
                return CheckResult(
                    status=CheckStatus.PASS,
                    title="Docker installed",
                    message=f"✅ {version}"
                )
        except Exception:
            pass
        
        return CheckResult(
            status=CheckStatus.FAIL,
            title="Docker not found",
            message="❌ Docker is not installed or not in PATH",
            remediation=self._format_remediation(
                "Install Docker",
                [
                    "Visit https://www.docker.com/products/docker-desktop",
                    "Download Docker Desktop for your OS",
                    "Install and restart your terminal"
                ]
            )
        )


class DockerDaemonRunning(SystemCheck):
    """Check if Docker daemon is running."""
    
    def run(self) -> CheckResult:
        try:
            result = self._run_command(["docker", "ps"], capture_output=True)
            if result.returncode == 0:
                return CheckResult(
                    status=CheckStatus.PASS,
                    title="Docker daemon running",
                    message="✅ Docker daemon is accessible"
                )
        except Exception:
            pass
        
        return CheckResult(
            status=CheckStatus.FAIL,
            title="Docker daemon not running",
            message="❌ Cannot connect to Docker daemon",
            remediation=self._format_remediation(
                "Start Docker daemon",
                [
                    "Open Docker Desktop application",
                    "Or run: open /Applications/Docker.app (macOS)",
                    "Wait for Docker icon to appear in menu bar"
                ]
            )
        )


class DockerComposeInstalled(SystemCheck):
    """Check if Docker Compose is installed."""
    
    def run(self) -> CheckResult:
        try:
            result = self._run_command(["docker", "compose", "version"])
            if result.returncode == 0:
                version = result.stdout.strip()
                return CheckResult(
                    status=CheckStatus.PASS,
                    title="Docker Compose installed",
                    message=f"✅ {version}"
                )
        except Exception:
            pass
        
        return CheckResult(
            status=CheckStatus.FAIL,
            title="Docker Compose not found",
            message="❌ Docker Compose is not installed or not in PATH",
            remediation=self._format_remediation(
                "Install Docker Compose",
                [
                    "Docker Compose is typically included with Docker Desktop",
                    "Reinstall Docker Desktop from https://www.docker.com/products/docker-desktop",
                    "Verify with: docker compose version"
                ]
            )
        )


class GitInstalled(SystemCheck):
    """Check if Git is installed."""
    
    def run(self) -> CheckResult:
        try:
            result = self._run_command(["git", "--version"])
            if result.returncode == 0:
                version = result.stdout.strip()
                return CheckResult(
                    status=CheckStatus.PASS,
                    title="Git installed",
                    message=f"✅ {version}"
                )
        except Exception:
            pass
        
        return CheckResult(
            status=CheckStatus.FAIL,
            title="Git not found",
            message="❌ Git is not installed or not in PATH",
            remediation=self._format_remediation(
                "Install Git",
                [
                    "Visit https://git-scm.com/download",
                    "Download and install Git for your OS",
                    "Restart your terminal and verify with: git --version"
                ]
            )
        )


class DiskSpaceAvailable(SystemCheck):
    """Check if sufficient disk space is available."""
    
    def __init__(self, min_gb: float = 5.0, check_path: str = "/", verbose: bool = False):
        super().__init__(verbose)
        self.min_gb = min_gb
        self.check_path = check_path
    
    def run(self) -> CheckResult:
        free_gb = self._get_disk_free_gb(self.check_path)
        
        if free_gb < 0:
            return CheckResult(
                status=CheckStatus.WARN,
                title="Disk space check",
                message="⚠️  Could not determine available disk space"
            )
        
        if free_gb < self.min_gb:
            return CheckResult(
                status=CheckStatus.WARN,
                title=f"Low disk space ({free_gb:.1f}GB free)",
                message=f"⚠️  Less than {self.min_gb}GB available",
                remediation=self._format_remediation(
                    "Free up disk space",
                    [
                        f"Current available space: {free_gb:.1f}GB",
                        f"Recommended minimum: {self.min_gb}GB",
                        "Delete unused files, containers, or images",
                        "Run: docker system prune (warning: removes stopped containers)"
                    ]
                )
            )
        
        return CheckResult(
            status=CheckStatus.PASS,
            title=f"Disk space sufficient ({free_gb:.1f}GB free)",
            message=f"✅ {free_gb:.1f}GB available (minimum {self.min_gb}GB required)"
        )


class PortAvailable(SystemCheck):
    """Check if a port is available."""
    
    def __init__(self, port: int, service_name: str = "", verbose: bool = False):
        super().__init__(verbose)
        self.port = port
        self.service_name = service_name
    
    def run(self) -> CheckResult:
        available = self._is_port_available(self.port)
        
        service_label = f" ({self.service_name})" if self.service_name else ""
        
        if available:
            return CheckResult(
                status=CheckStatus.PASS,
                title=f"Port {self.port} available{service_label}",
                message=f"✅ Port {self.port} is available"
            )
        
        return CheckResult(
            status=CheckStatus.WARN,
            title=f"Port {self.port} in use{service_label}",
            message=f"⚠️  Port {self.port} is already in use",
            remediation=self._format_remediation(
                f"Free up port {self.port}",
                [
                    f"Another service is using port {self.port}",
                    f"Find process: lsof -i :{self.port} (macOS/Linux)",
                    "Stop or restart the conflicting service",
                    "Or use a different port in your configuration"
                ]
            )
        )


# ============================================================================
# Composite Checks
# ============================================================================

class DependenciesCheck(SystemCheck):
    """Check all system dependencies required for arches-containers."""
    
    def __init__(self, verbose: bool = False):
        super().__init__(verbose)
    
    def run(self) -> CheckResult:
        """Run all dependency checks and aggregate results."""
        checks = [
            GitInstalled(self.verbose),
            DockerInstalled(self.verbose),
            DockerDaemonRunning(self.verbose),
            DockerComposeInstalled(self.verbose),
            DiskSpaceAvailable(min_gb=5.0, verbose=self.verbose),
        ]
        
        results = [check.run() for check in checks]
        
        # Aggregate results
        has_failures = any(r.status == CheckStatus.FAIL for r in results)
        has_warnings = any(r.status == CheckStatus.WARN for r in results)
        
        if has_failures:
            status = CheckStatus.FAIL
            title = "Dependencies check failed"
        elif has_warnings:
            status = CheckStatus.WARN
            title = "Dependencies check completed with warnings"
        else:
            status = CheckStatus.PASS
            title = "All dependencies available"
        
        return CheckResult(
            status=status,
            title=title,
            message=self._aggregate_message(results),
            details=self._format_sub_results(results),
            remediation=self._aggregate_remediation(results)
        )
    
    @staticmethod
    def _aggregate_message(results: List[CheckResult]) -> str:
        """Create aggregate message from sub-check results."""
        fail_count = sum(1 for r in results if r.status == CheckStatus.FAIL)
        warn_count = sum(1 for r in results if r.status == CheckStatus.WARN)
        
        if fail_count > 0:
            return f"❌ {fail_count} critical issue(s) found"
        if warn_count > 0:
            return f"⚠️  {warn_count} warning(s) found"
        return "✅ All dependencies check passed"
    
    @staticmethod
    def _format_sub_results(results: List[CheckResult]) -> List[str]:
        """Format sub-check results as detail lines."""
        lines = []
        for result in results:
            status_icon = {
                CheckStatus.PASS: "✅",
                CheckStatus.WARN: "⚠️ ",
                CheckStatus.FAIL: "❌"
            }[result.status]
            clean_message = SystemCheck._strip_status_prefix(result.message)
            lines.append(f"{status_icon} {result.title}: {clean_message}")
        return lines
    
    @staticmethod
    def _aggregate_remediation(results: List[CheckResult]) -> Optional[str]:
        """Aggregate remediation steps from failed checks."""
        failed = [r for r in results if r.status == CheckStatus.FAIL and r.remediation]
        if not failed:
            return None
        
        lines = ["\n🔧 Remediation steps:"]
        for result in failed:
            lines.append(f"\n{result.title}:")
            lines.append(result.remediation)
        return "\n".join(lines)


class WorkspaceCheck(SystemCheck):
    """Check workspace integrity and configuration."""
    
    def run(self) -> CheckResult:
        """Check for workspace issues like hidden workspaces or misconfiguration."""
        workspaces = self._find_all_workspaces()
        active_workspace = self._determine_active_workspace(workspaces)
        
        issues = []
        warnings = []
        
        cwd = os.getcwd()

        # Flag when active workspace is not the current directory or an ancestor.
        # This often indicates an unexpected workspace selection.
        if active_workspace and not self._is_workspace_under_cwd(active_workspace, cwd):
            warnings.append("Active workspace is outside the current directory path")

        # Check for multiple workspaces
        if len(workspaces) > 1:
            warnings.append(f"Multiple workspaces found: {len(workspaces)}")
        
        # Determine status
        if issues:
            status = CheckStatus.FAIL
            title = "Workspace integrity check failed"
            message = "❌ " + issues[0]
            remediation = self._format_workspace_remediation(workspaces, active_workspace, cwd)
        elif warnings:
            status = CheckStatus.WARN
            title = "Workspace check completed with warnings"
            message = f"⚠️  {warnings[0]}"
            remediation = self._format_workspace_remediation(workspaces, active_workspace, cwd)
        else:
            status = CheckStatus.PASS
            title = "Workspace configuration valid"
            message = f"✅ Single workspace at {active_workspace}"
            remediation = None

        details = []
        if warnings:
            details.extend([f"⚠️  {warning}" for warning in warnings[1:]])

        if active_workspace and not self._is_workspace_under_cwd(active_workspace, cwd):
            details.append(f"Active workspace: {active_workspace}")
            details.append(f"Current directory: {cwd}")

        details.extend(self._format_workspace_tree(workspaces, active_workspace))
        
        return CheckResult(
            status=status,
            title=title,
            message=message,
            details=details,
            remediation=remediation
        )
    
    @staticmethod
    def _find_all_workspaces() -> List[str]:
        """Find all .arches_containers directories up the directory tree."""
        workspaces = []
        cwd = os.getcwd()
        
        # Walk up from current directory
        current = Path(cwd)
        home = Path.home()
        
        while current != current.parent:
            ac_dir = current / ".arches_containers"
            if ac_dir.exists() and ac_dir.is_dir():
                workspaces.append(str(ac_dir.parent))
            
            # Stop at home directory but include it
            if current == home:
                ac_dir = current / ".arches_containers"
                if ac_dir.exists() and ac_dir.is_dir() and str(current) not in workspaces:
                    workspaces.append(str(current))
                break
            
            current = current.parent
        
        return workspaces
    
    @staticmethod
    def _determine_active_workspace(workspaces: List[str]) -> Optional[str]:
        """Determine which workspace is active (prioritize cwd, then closest parent)."""
        if not workspaces:
            return None
        
        cwd = os.getcwd()
        
        # Prefer workspace in or closest to cwd
        for workspace in workspaces:
            if cwd.startswith(workspace):
                return workspace
        
        # Fallback to first (closest to cwd due to traversal order)
        return workspaces[0]
    
    @staticmethod
    def _is_workspace_in_cwd(workspace: str, cwd: str) -> bool:
        """Check if workspace is within the current working directory."""
        return cwd.startswith(workspace)

    @staticmethod
    def _is_workspace_under_cwd(workspace: str, cwd: str) -> bool:
        """Check if workspace path is the current directory or one of its ancestors."""
        workspace_path = Path(workspace).resolve()
        cwd_path = Path(cwd).resolve()
        return cwd_path == workspace_path or str(cwd_path).startswith(str(workspace_path) + os.sep)
    
    @staticmethod
    def _format_workspace_tree(workspaces: List[str], active: Optional[str]) -> List[str]:
        """Format workspaces as tree display."""
        lines = []
        cwd = os.getcwd()
        home = str(Path.home())
        
        for workspace in workspaces:
            projects = WorkspaceCheck._count_projects(workspace)
            project_label = f"{projects} project(s)"
            
            is_active = workspace == active
            
            indicator = "👉" if is_active else "  "
            if is_active:
                location = "(active)"
            elif workspace == home:
                location = "(home workspace)"
            elif cwd.startswith(workspace):
                location = "(ancestor workspace)"
            else:
                location = "(other)"
            
            line = f"{indicator} {workspace} {location} - {project_label}"
            lines.append(line)
        
        return lines
    
    @staticmethod
    def _count_projects(workspace_path: str) -> int:
        """Count number of projects in workspace."""
        try:
            ac_dir = Path(workspace_path) / ".arches_containers"
            if ac_dir.exists():
                # Count directories that contain config.json
                projects = [d for d in ac_dir.iterdir() 
                           if d.is_dir() and (d / "config.json").exists()]
                return len(projects)
        except Exception:
            pass
        return 0
    
    @staticmethod
    def _format_workspace_remediation(workspaces: List[str], active: Optional[str], 
                                      cwd: str) -> Optional[str]:
        """Generate remediation guidance for workspace issues."""
        if not workspaces:
            return None
        
        lines = ["\n   🔧 Workspace guidance:"]
        
        if len(workspaces) > 1:
            lines.append(f"\n   Multiple workspaces found:")
            for ws in workspaces:
                is_active = ws == active
                marker = "→" if is_active else " "
                lines.append(f"   {marker} {ws}")
            
            lines.append(f"\n   Active workspace: {active}")
            lines.append(f"   This is where 'act' will look for projects.")
            
            hidden_workspaces = [w for w in workspaces 
                                if w.startswith(str(Path.home())) and not cwd.startswith(w)]
            if hidden_workspaces:
                lines.append(f"\n   Hidden workspaces (in home directory) can interfere with project discovery.")
                lines.append(f"   Consider removing or consolidating workspaces.")
        
        return "\n".join(lines)


class ConfigurationCheck(SystemCheck):
    """Check configuration integrity for projects in the active workspace."""
    
    def __init__(self, project_name: Optional[str] = None, verbose: bool = False):
        super().__init__(verbose)
        self.project_name = project_name
    
    def run(self) -> CheckResult:
        """Check configuration for one or all projects."""
        from arches_containers.utils.workspace import AcWorkspace
        
        try:
            workspace = AcWorkspace()
        except Exception as e:
            return CheckResult(
                status=CheckStatus.FAIL,
                title="Configuration check failed",
                message=f"❌ Could not initialize workspace: {str(e)}",
                remediation=self._format_remediation(
                    "Initialize workspace",
                    ["Run: act status", "Or: act up to create a new project"]
                )
            )
        
        # Get projects to check
        if self.project_name:
            projects_to_check = [self.project_name]
        else:
            projects_to_check = workspace.list_projects()
        
        if not projects_to_check:
            return CheckResult(
                status=CheckStatus.PASS,
                title="No projects to check",
                message="✅ No projects in active workspace"
            )
        
        # Run checks for each project
        all_results = []
        for project in projects_to_check:
            result = self._check_project(workspace, project)
            all_results.append(result)
        
        # Aggregate
        has_failures = any(r.status == CheckStatus.FAIL for r in all_results)
        has_warnings = any(r.status == CheckStatus.WARN for r in all_results)
        
        if has_failures:
            status = CheckStatus.FAIL
            title = "Configuration issues found"
        elif has_warnings:
            status = CheckStatus.WARN
            title = "Configuration warnings"
        else:
            status = CheckStatus.PASS
            title = "All configurations valid"
        
        return CheckResult(
            status=status,
            title=title,
            message=self._aggregate_config_message(all_results),
            details=self._format_config_results(all_results),
            remediation=self._aggregate_config_remediation(all_results)
        )
    
    def _check_project(self, workspace, project_name: str) -> CheckResult:
        """Check a single project's configuration."""
        try:
            from arches_containers.utils.workspace import AcProjectAttributes
            import json
            
            project = workspace.get_project(project_name)
            config_path = Path(project.get_project_path()) / "config.json"
            
            if not config_path.exists():
                return CheckResult(
                    status=CheckStatus.FAIL,
                    title=f"{project_name}: config.json missing",
                    message=f"❌ Config file not found at {config_path}",
                    remediation=self._format_remediation(
                        "Create project",
                        [f"Run: act create -p {project_name}",
                         f"(select the version from the presented list)"]
                    )
                )
            
            with open(config_path) as f:
                config = json.load(f)
            
            issues = []
            warnings = []
            repo_check_remediation = None
            
            # Check for project_repo_directory (backward compatibility check)
            repo_check = self._check_repo_directory(
                workspace.path,
                project_name,
                config
            )
            if repo_check.status == CheckStatus.FAIL:
                issues.append(repo_check.message)
                repo_check_remediation = repo_check.remediation
            elif repo_check.status == CheckStatus.WARN:
                warnings.append(repo_check.message)

            # Check config identity consistency
            config_project_name = config.get(AcProjectAttributes.PROJECT_NAME.value)
            if config_project_name and config_project_name != project_name:
                issues.append(
                    f"Config project_name '{config_project_name}' does not match workspace project '{project_name}'"
                )

            # Check ports declared in config.json and project docker-compose files.
            project_ports = self._extract_project_ports(config_path.parent, config)
            for port in project_ports:
                if not self._is_port_available(port):
                    port_name = self._get_port_name(port)
                    port_label = f" ({port_name})" if port_name else ""
                    warnings.append(f"Port {port} is already in use{port_label}")
            
            # Check hash format
            project_hash = config.get(AcProjectAttributes.PROJECT_HASH.value)
            if project_hash and not self._is_valid_hash(project_hash):
                warnings.append(f"Invalid project hash format: {project_hash}")
            
            # Check version
            version = config.get(AcProjectAttributes.PROJECT_ARCHES_VERSION.value)
            if version and self._is_version_old(version):
                warnings.append(f"Arches version {version} is old (< 7.6)")
            
            # Determine status
            if issues:
                status = CheckStatus.FAIL
                issue_count = len(issues)
                warn_count = len(warnings)
                message = f"❌ {issue_count} failure(s)"
                if warn_count:
                    message += f", {warn_count} warning(s)"
                # Use repo check remediation if available, otherwise use general remediation
                remediation = repo_check_remediation if repo_check_remediation else self._format_project_remediation(project_name, config, issues)
            elif warnings:
                status = CheckStatus.WARN
                message = f"⚠️  {len(warnings)} warning(s)"
                remediation = None
            else:
                status = CheckStatus.PASS
                message = f"✅ Configuration valid"
                remediation = None

            finding_details: List[str] = []
            finding_details.extend([f"[FAIL] {issue}" for issue in issues])
            finding_details.extend([f"[WARN] {warning}" for warning in warnings])
            
            return CheckResult(
                status=status,
                title=f"Project '{project_name}'",
                message=message,
                details=finding_details,
                remediation=remediation
            )
        
        except Exception as e:
            return CheckResult(
                status=CheckStatus.FAIL,
                title=f"Project '{project_name}': check error",
                message=f"❌ {str(e)}",
                remediation=self._format_remediation(
                    "Debug",
                    ["Run with --verbose for more details"]
                )
            )
    
    def _check_repo_directory(self, workspace_path: str, project_name: str, 
                             config: Dict[str, Any]) -> CheckResult:
        """
        Check repository directory existence with backward compatibility.
        
        Logic:
        - If project_repo_directory is set in config:
          1. Check for that specific directory → pass if found
          2. If not found, check for directory matching project_name
          3. If found with project_name, warn about naming mismatch
          4. If neither found, fail
        - If project_repo_directory is NOT set (old config):
          1. Check for directory matching project_name → pass if found
          2. If not found, fail
        
        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            config: Project configuration dict
            
        Returns:
            CheckResult with PASS/WARN/FAIL status
        """
        from arches_containers.utils.workspace import AcProjectAttributes
        
        workspace = Path(workspace_path)
        repo_dir_config = config.get(AcProjectAttributes.PROJECT_REPO_DIRECTORY.value)
        
        # Case 1: project_repo_directory is specified in config
        if repo_dir_config:
            repo_path = workspace / repo_dir_config
            if repo_path.exists() and (repo_path / "manage.py").exists():
                return CheckResult(
                    status=CheckStatus.PASS,
                    title="Repository/directory found",
                    message=f"✅ Repository/directory '{repo_dir_config}' exists"
                )
            
            # Not found with config name, check for project_name variant
            inferred_repo = self._find_repo_for_project(workspace_path, project_name, config)
            
            if inferred_repo:
                # Found with different name, warn about naming mismatch
                inferred_name = Path(inferred_repo).name
                
                return CheckResult(
                    status=CheckStatus.WARN,
                    title="Repository found with different naming",
                    message=f"⚠️  Repository found as '{inferred_name}' but config expects '{repo_dir_config}'",
                    remediation=self._format_remediation(
                        "Update repository directory reference",
                        [
                            f"The project config specifies: {repo_dir_config}",
                            f"But the repository folder is named: {inferred_name}",
                            f"",
                            f"Option 1: Rename repository folder (recommended for consistency)",
                            f"  run: mv {inferred_name} {repo_dir_config}",
                            f"",
                            f"Option 2: Update project configuration",
                            f"  Edit .arches_containers/{project_name}/config.json",
                            f"  Change 'project_repo_directory' to: {inferred_name}",
                            f"  Then run: act up"
                        ]
                    )
                )
            
            # Neither directory found, fail
            return CheckResult(
                status=CheckStatus.FAIL,
                title="Repository directory not found",
                message=f"❌ Repository/directory '{repo_dir_config}' not found in workspace",
                remediation=self._format_remediation(
                    "Set up the repository",
                    [
                        f"The project expects a repository named: {repo_dir_config}",
                        f"",
                        f"Option 1: Clone the repository (recommended)",
                        f"  run: git clone <repo-url> {repo_dir_config}",
                        f"  run: act up",
                        f"",
                        f"Option 2: Create project using the configuration",
                        f"  run: act activate -p {project_name}",
                        f"  run: act up",
                        f"  (This will create the Arches application/extension project)"
                    ]
                )
            )
        
        # Case 2: project_repo_directory is NOT set (old config without this field)
        else:
            inferred_repo = self._find_repo_for_project(workspace_path, project_name, config)
            
            if inferred_repo:
                # Found with project_name, pass (backward compatibility with old configs)
                found_name = Path(inferred_repo).name
                return CheckResult(
                    status=CheckStatus.PASS,
                    title="Repository directory found",
                    message=f"✅ Repository/directory '{found_name}' exists (using project_name)"
                )
            
            # Not found, fail
            return CheckResult(
                status=CheckStatus.FAIL,
                title="Repository directory not found",
                message=f"❌ Repository/directory '{project_name}' not found in workspace",
                remediation=self._format_remediation(
                    "Add the repository/directory for the project",
                    [
                        f"The project looks for a repository named: {project_name}",
                        f"",
                        f"Option 1: Clone the repository (recommended)",
                        f"  run: git clone <repo-url> {project_name}",
                        f"  run: act up",
                        f"",
                        f"Option 2: Create project using up command",
                        f"  run: act activate {project_name}",
                        f"  run: act up"
                    ]
                )
            )
    
    @staticmethod
    def _find_repo_for_project(workspace_path: str, project_name: str, config: Dict[str, Any]) -> Optional[str]:
        """Try to find the repository folder for a project."""
        project_name_underscore = project_name.replace("-", "_")
        project_name_hyphen = project_name.replace("_", "-")
        
        # Check parent directory for folders matching project name variants
        workspace = Path(workspace_path)
        for variant in [project_name, project_name_underscore, project_name_hyphen]:
            candidate = workspace / variant
            if candidate.exists() and (candidate / "manage.py").exists():
                return str(candidate)
        
        return None

    @staticmethod
    def _extract_project_ports(project_path: Path, config: Dict[str, Any]) -> List[int]:
        """
        Extract host ports used by a project from config values and project docker compose files.

        Returns a sorted, de-duplicated list of ports.
        """
        ports = set()

        # Extract numeric ports from config values with "port" in the key name.
        for key, value in config.items():
            if "port" not in str(key).lower():
                continue

            port = ConfigurationCheck._parse_port_value(value)
            if port:
                ports.add(port)

        # Extract host ports from docker-compose files in the project directory.
        compose_files = list(project_path.glob("docker-compose*.yml")) + list(project_path.glob("docker-compose*.yaml"))
        direct_mapping = re.compile(r"-\s*['\"]?(\d{2,5})\s*:\s*\d{2,5}")
        env_default_mapping = re.compile(r"\$\{[^}:]+:-?(\d{2,5})\}\s*:\s*\d{2,5}")

        for compose_file in compose_files:
            try:
                with open(compose_file, encoding="utf-8") as f:
                    for raw_line in f:
                        line = raw_line.strip()
                        if not line or line.startswith("#"):
                            continue

                        direct_match = direct_mapping.search(line)
                        if direct_match:
                            ports.add(int(direct_match.group(1)))
                            continue

                        env_default_match = env_default_mapping.search(line)
                        if env_default_match:
                            ports.add(int(env_default_match.group(1)))
            except OSError:
                continue

        return sorted(ports)

    @staticmethod
    def _parse_port_value(value: Any) -> Optional[int]:
        """Parse a port value from int or numeric string config values."""
        if isinstance(value, int) and 0 < value <= 65535:
            return value

        if isinstance(value, str) and value.isdigit():
            parsed = int(value)
            if 0 < parsed <= 65535:
                return parsed

        return None

    @staticmethod
    def _get_port_name(port: int) -> str:
        """Get a friendly label for known Arches-related ports."""
        port_names = {
            8000: "Arches API",
            8001: "Elasticsearch",
            8002: "Application",
        }
        return port_names.get(port, "")
    
    @staticmethod
    def _is_valid_hash(hash_str: str) -> bool:
        """Check if hash matches expected format (5-char lowercase hex)."""
        if not isinstance(hash_str, str) or len(hash_str) != 5:
            return False
        try:
            int(hash_str, 16)
            # Check that all letters (if any) are lowercase
            return hash_str == hash_str.lower()
        except ValueError:
            return False
    
    @staticmethod
    def _is_version_old(version_str: str) -> bool:
        """Check if version is < 7.6."""
        try:
            parts = version_str.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            return (major, minor) < (7, 6)
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def _format_project_remediation(project_name: str, config: Dict[str, Any], 
                                   issues: List[str]) -> Optional[str]:
        """Generate remediation for project configuration issues."""
        if not issues:
            return None
        
        lines = [f"\n   🔧 Fix configuration for '{project_name}':"]

        if any("does not match workspace project" in issue for issue in issues):
            current_name = config.get("project_name", "<missing>")
            lines.append(f"\n   The act config project (directory) name does not match the config.json project_name.")
            lines.append(f"   Current config value: {current_name}")
            lines.append(f"   Expected value: {project_name}")
            lines.append(f"\n   Option 1: Update config.json (recommended)")
            lines.append(f"      Edit .arches_containers/{project_name}/config.json")
            lines.append(f"      Set 'project_name' to: {project_name}")
            lines.append(f"\n   Option 2: Recreate the project entry")
            lines.append(f"      run: act delete -p {project_name}")
            lines.append(f"      run: act create -p {project_name}")
            lines.append(f"      (Select the version from the presented list)")
            lines.append(f"      run: act activate -p {project_name}")
            lines.append(f"      run: act up")
        
        if "project_repo_directory" in issues[0]:
            project_url_safe = config.get("project_name_url_safe", project_name)
            lines.append(f"\n   The config is missing the repository directory reference.")
            lines.append(f"\n   Option 1: Recreate the project")
            lines.append(f"      run: act delete {project_name}")
            lines.append(f"      run: act up --app {project_name}")
            lines.append(f"\n   Option 2: Ensure repository folder exists and matches project name:")
            lines.append(f"      Expected folder name: {project_url_safe} or {project_name}")
            lines.append(f"      Check that the repo is in: {Path.cwd()}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _aggregate_config_message(results: List[CheckResult]) -> str:
        """Create aggregate message from project check results."""
        fail_count = sum(1 for r in results if r.status == CheckStatus.FAIL)
        warn_count = sum(1 for r in results if r.status == CheckStatus.WARN)
        pass_count = sum(1 for r in results if r.status == CheckStatus.PASS)
        
        if fail_count > 0:
            return f"❌ {fail_count} project(s) with configuration issues"
        if warn_count > 0:
            return f"⚠️  {warn_count} project(s) with warnings"
        return f"✅ {pass_count} project(s) configured correctly"
    
    @staticmethod
    def _format_config_results(results: List[CheckResult]) -> List[str]:
        """Format project configuration results as detail lines."""
        lines = []
        for result in results:
            status_icon = {
                CheckStatus.PASS: "✅",
                CheckStatus.WARN: "⚠️ ",
                CheckStatus.FAIL: "❌"
            }[result.status]
            clean_message = SystemCheck._strip_status_prefix(result.message)
            lines.append(f"{status_icon} {result.title}: {clean_message}")
            for detail in result.details or []:
                clean_detail = SystemCheck._strip_status_prefix(detail)
                lines.append(f"   - {clean_detail}")
        return lines
    
    @staticmethod
    def _aggregate_config_remediation(results: List[CheckResult]) -> Optional[str]:
        """Aggregate remediation from failed project checks."""
        failed_with_remediation = [
            r for r in results
            if r.status == CheckStatus.FAIL and r.remediation
        ]
        if not failed_with_remediation:
            return None
        
        lines = ["\n🔧 Remediation for failed checks only:"]
        for result in failed_with_remediation:
            lines.append(f"\n   🔴 Failed check: {result.title}")
            lines.append(result.remediation)
        return "\n".join(lines)
