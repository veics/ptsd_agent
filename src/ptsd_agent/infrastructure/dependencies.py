"""Dependency Installer for PTSD Agent.

Automatically installs Python dependencies from requirements.txt or pyproject.toml
before running tests.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class InstallResult:
    """Result of a dependency installation attempt."""
    success: bool
    packages_installed: int = 0
    packages_failed: int = 0
    error_message: Optional[str] = None
    details: List[str] = field(default_factory=list)


class DependencyInstaller:
    """Installs Python dependencies for test environments.
    
    Supports:
    - requirements.txt files
    - Service-specific virtual environments
    - Progress callbacks for UI updates
    """
    
    def __init__(
        self,
        project_root: str,
        timeout: int = 300,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """Initialize the dependency installer.
        
        Args:
            project_root: Root directory of the project
            timeout: Maximum time in seconds for pip install
            progress_callback: Optional callback(message, progress_pct) for UI updates
        """
        self.project_root = Path(project_root)
        self.timeout = timeout
        self.progress_callback = progress_callback
    
    def _emit_progress(self, message: str, progress: float = 0.0):
        """Emit progress update to callback if registered."""
        if self.progress_callback:
            self.progress_callback(message, progress)
        logger.debug(f"[DependencyInstaller] {message} ({progress:.0%})")
    
    def find_requirements_files(self, service_path: Optional[str] = None) -> List[Path]:
        """Find all requirements files in a path.
        
        Args:
            service_path: Optional specific service directory to search
            
        Returns:
            List of Path objects to requirements files
        """
        search_path = Path(service_path) if service_path else self.project_root
        
        requirements_files = []
        
        # Priority order for requirements files
        patterns = [
            "requirements.txt",
            "requirements-test.txt",
            "requirements-dev.txt",
            "test-requirements.txt",
        ]
        
        for pattern in patterns:
            req_file = search_path / pattern
            if req_file.exists():
                requirements_files.append(req_file)
        
        return requirements_files
    
    def get_python_executable(self, service_path: Optional[str] = None) -> str:
        """Get the Python executable for a service.
        
        Checks for service-specific venv first, then project venv, then system Python.
        
        Args:
            service_path: Optional service directory with its own venv
            
        Returns:
            Path to Python executable
        """
        if service_path:
            service_path = Path(service_path)
            # Check for service-specific venv
            for venv_name in [".venv", "venv"]:
                venv_python = service_path / venv_name / "bin" / "python"
                if venv_python.exists():
                    return str(venv_python)
        
        # Check for project-level venv
        for venv_name in [".venv", "venv"]:
            venv_python = self.project_root / venv_name / "bin" / "python"
            if venv_python.exists():
                return str(venv_python)
        
        # Fallback to current Python
        return sys.executable
    
    def install_from_requirements(
        self,
        requirements_file: Path,
        python_executable: Optional[str] = None,
        quiet: bool = True
    ) -> InstallResult:
        """Install dependencies from a requirements.txt file.
        
        Args:
            requirements_file: Path to requirements.txt
            python_executable: Python to use for pip (default: auto-detect)
            quiet: Suppress pip output
            
        Returns:
            InstallResult with installation status
        """
        if not requirements_file.exists():
            return InstallResult(
                success=False,
                error_message=f"Requirements file not found: {requirements_file}"
            )
        
        python_exe = python_executable or self.get_python_executable()
        
        # Count packages to install
        with open(requirements_file) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('#') and not l.startswith('-')]
            package_count = len(lines)
        
        self._emit_progress(f"Installing {package_count} packages from {requirements_file.name}", 0.1)
        
        # Build pip install command
        cmd = [
            python_exe, "-m", "pip", "install",
            "-r", str(requirements_file),
            "--upgrade",
        ]
        
        if quiet:
            cmd.append("-q")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.project_root)
            )
            
            if result.returncode == 0:
                self._emit_progress(f"Installed {package_count} packages", 1.0)
                return InstallResult(
                    success=True,
                    packages_installed=package_count,
                    details=[f"Installed from {requirements_file.name}"]
                )
            else:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                return InstallResult(
                    success=False,
                    error_message=f"pip install failed: {error_msg}",
                    details=[result.stderr]
                )
                
        except subprocess.TimeoutExpired:
            return InstallResult(
                success=False,
                error_message=f"Installation timed out after {self.timeout}s"
            )
        except Exception as e:
            return InstallResult(
                success=False,
                error_message=str(e)
            )
    
    def install_for_service(self, service_path: str) -> InstallResult:
        """Install all dependencies for a specific service.
        
        Args:
            service_path: Path to the service directory
            
        Returns:
            InstallResult with aggregated installation status
        """
        service_path = Path(service_path)
        python_exe = self.get_python_executable(str(service_path))
        
        requirements_files = self.find_requirements_files(str(service_path))
        
        if not requirements_files:
            logger.debug(f"[DependencyInstaller] No requirements files found in {service_path}")
            return InstallResult(success=True, details=["No requirements files found"])
        
        total_installed = 0
        total_failed = 0
        all_details = []
        
        for i, req_file in enumerate(requirements_files):
            progress = (i + 1) / len(requirements_files)
            self._emit_progress(f"Installing {req_file.name}", progress * 0.8)
            
            result = self.install_from_requirements(req_file, python_exe)
            
            if result.success:
                total_installed += result.packages_installed
                all_details.extend(result.details)
            else:
                total_failed += 1
                all_details.append(f"Failed: {req_file.name} - {result.error_message}")
        
        self._emit_progress("Dependencies installed", 1.0)
        
        return InstallResult(
            success=total_failed == 0,
            packages_installed=total_installed,
            packages_failed=total_failed,
            details=all_details
        )
    
    def install_all(self, service_paths: Optional[List[str]] = None) -> InstallResult:
        """Install dependencies for all services or specified paths.
        
        Args:
            service_paths: Optional list of service directories
            
        Returns:
            InstallResult with aggregated installation status
        """
        if service_paths:
            paths = [Path(p) for p in service_paths]
        else:
            # Auto-discover services with requirements files
            paths = [self.project_root]
            services_dir = self.project_root / "services"
            if services_dir.exists():
                paths.extend(p for p in services_dir.iterdir() if p.is_dir())
        
        total_installed = 0
        total_failed = 0
        all_details = []
        
        for i, path in enumerate(paths):
            if path.is_dir():
                progress = (i + 1) / len(paths)
                self._emit_progress(f"Processing {path.name}", progress * 0.5)
                
                result = self.install_for_service(str(path))
                total_installed += result.packages_installed
                total_failed += result.packages_failed
                all_details.extend(result.details)
        
        return InstallResult(
            success=total_failed == 0,
            packages_installed=total_installed,
            packages_failed=total_failed,
            details=all_details
        )
