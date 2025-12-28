"""
Automatic dependency installer for PTSD Agent.

Scans service-specific requirements.txt files and installs missing dependencies
before test discovery to prevent import errors.
"""

import subprocess
import sys
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """Represents a Python package requirement."""
    name: str
    version: Optional[str] = None
    specifier: Optional[str] = None  # e.g., "==", ">=", "~="
    
    def __str__(self):
        if self.version and self.specifier:
            return f"{self.name}{self.specifier}{self.version}"
        return self.name
    
    @property
    def package_name(self) -> str:
        """Get the base package name without version."""
        return self.name.lower().replace('_', '-')


@dataclass
class InstallResult:
    """Results from dependency installation."""
    installed: List[Requirement]
    skipped: List[Tuple[Requirement, str]]  # (requirement, reason)
    failed: List[Tuple[Requirement, str]]   # (requirement, error)
    
    @property
    def total(self) -> int:
        return len(self.installed) + len(self.skipped) + len(self.failed)
    
    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return (len(self.installed) + len(self.skipped)) / self.total * 100


class DependencyInstaller:
    """Manages automatic dependency installation for test discovery."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "services"
        
    def collect_service_requirements(self, skip_dev: bool = False) -> List[Requirement]:
        """
        Collect all requirements from service-specific requirements files.
        
        Args:
            skip_dev: If True, skip requirements-dev.txt files
            
        Returns:
            List of unique requirements
        """
        requirements = {}  # Use dict to dedupe by package name
        
        if not self.services_dir.exists():
            logger.debug("No services directory found")
            return []
        
        # Find all requirements files
        patterns = ["requirements.txt"]
        if not skip_dev:
            patterns.append("requirements-dev.txt")
        
        for service_dir in self.services_dir.iterdir():
            if not service_dir.is_dir():
                continue
                
            for pattern in patterns:
                req_file = service_dir / pattern
                if req_file.exists():
                    parsed = self._parse_requirements_file(req_file)
                    for req in parsed:
                        # Keep the requirement with the most specific version
                        if req.package_name not in requirements or req.version:
                            requirements[req.package_name] = req
        
        return list(requirements.values())
    
    def _parse_requirements_file(self, file_path: Path) -> List[Requirement]:
        """Parse a requirements.txt file and extract requirements."""
        requirements = []
        
        try:
            with open(file_path) as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Skip flags (like -r, -e, --index-url, etc.)
                    if line.startswith('-'):
                        logger.debug(f"Skipping requirements file flag: {line}")
                        continue
                    
                    # Skip git URLs
                    if line.startswith('git+') or line.startswith('http'):
                        continue
                    
                    # Parse requirement
                    req = self._parse_requirement_line(line)
                    if req:
                        requirements.append(req)
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
        
        return requirements
    
    def _parse_requirement_line(self, line: str) -> Optional[Requirement]:
        """Parse a single requirement line."""
        # Match patterns like: package==1.0.0, package>=1.0, package~=1.0
        pattern = r'^([a-zA-Z0-9_\-\.]+)\s*([>=<~!]+)\s*([0-9\.]+.*?)(?:\s|$|;)'
        match = re.match(pattern, line)
        
        if match:
            name, specifier, version = match.groups()
            return Requirement(name=name, version=version.strip(), specifier=specifier)
        
        # Simple package name without version
        simple_pattern = r'^([a-zA-Z0-9_\-\.]+)(?:\s|$|;)'
        simple_match = re.match(simple_pattern, line)
        if simple_match:
            return Requirement(name=simple_match.group(1))
        
        return None
    
    def filter_missing_packages(self, requirements: List[Requirement]) -> List[Requirement]:
        """
        Filter out already-installed packages.
        
        Returns:
            List of requirements that need to be installed
        """
        missing = []
        
        for req in requirements:
            if not self._is_package_installed(req):
                missing.append(req)
        
        return missing
    
    def _is_package_installed(self, req: Requirement) -> bool:
        """Check if a package is already installed."""
        try:
            import importlib.metadata
            # Check if package exists
            importlib.metadata.distribution(req.package_name)
            return True
        except importlib.metadata.PackageNotFoundError:
            return False
        except Exception:
            # If we can't check, assume it's not installed
            return False
    
    def _check_python_compatibility(self, req: Requirement) -> Tuple[bool, Optional[str]]:
        """Check if requirement is compatible with current Python version.
        
        Returns:
            (is_compatible, suggested_version)
        """
        import sys
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        # Packages requiring build tools (cmake, ninja, etc.)
        build_tool_packages = {
            'pyarrow': 'cmake (install via Homebrew: brew install cmake)',
            'lightgbm': 'cmake (install via Homebrew: brew install cmake)',
            'lxml': 'libxml2 (install via Homebrew: brew install libxml2)',
            'grpcio': 'system build tools',
        }
        
        # Check if package requires build tools
        if req.package_name in build_tool_packages:
            tool_name = build_tool_packages[req.package_name]
            logger.warning(f"Skipping {req}: requires {tool_name}")
            return (False, None)
        
        # Known Python version compatibility issues
        compatibility_fixes = {
            'qdrant-client': {
                '1.7.0': ('3.14', '1.11.3'),
                '1.7.1': ('3.14', '1.11.3'),
                '1.7.2': ('3.14', '1.11.3'),
            },
            'scikit-learn': {
                '1.3.0': ('3.14', '1.5.0'),
                '1.3.1': ('3.14', '1.5.0'),
                '1.3.2': ('3.14', '1.5.0'),
                '1.4.0': ('3.14', '1.5.0'),
            },
        }
        
        pkg_fixes = compatibility_fixes.get(req.package_name, {})
        if not pkg_fixes:
            return (True, None)
        
        # Check specific version
        version_fix = pkg_fixes.get(req.version or '*')
        if version_fix:
            incompatible_py, suggested = version_fix
            if py_version >= incompatible_py:
                return (False, suggested)
        
        return (True, None)
    
    def install_packages(
        self, 
        packages: List[Requirement],
        progress_callback=None,
        timeout: int = 300
    ) -> InstallResult:
        """
        Install missing packages.
        
        Args:
            packages: List of requirements to install
            progress_callback: Optional callback(package, status) for progress updates
            timeout: Installation timeout in seconds
            
        Returns:
            InstallResult with installation summary
        """
        installed = []
        skipped = []
        failed = []
        
        if not packages:
            return InstallResult(installed=[], skipped=[], failed=[])
        
        # Get pip executable from current venv
        pip_path = sys.executable.replace('python', 'pip')
        if not Path(pip_path).exists():
            pip_path = sys.executable
            pip_args = [pip_path, '-m', 'pip']
        else:
            pip_args = [pip_path]
        
        for req in packages:
            # Check Python version compatibility first
            is_compatible, suggested_version = self._check_python_compatibility(req)
            if not is_compatible:
                if suggested_version:
                    skip_msg = f"Python {sys.version_info.major}.{sys.version_info.minor} incompatible, use {suggested_version} instead"
                    skipped.append((req, skip_msg))
                    logger.warning(f"Skipping {req}: {skip_msg}")
                else:
                    skip_msg = f"Python {sys.version_info.major}.{sys.version_info.minor} incompatible, no compatible version found"
                    skipped.append((req, skip_msg))
                    logger.warning(f"Skipping {req}: {skip_msg}")
                
                if progress_callback:
                    progress_callback(req, 'skipped')
                continue
            
            if progress_callback:
                progress_callback(req, 'installing')
            
            try:
                # Build pip install command correctly
                install_cmd = pip_args + ['install', '--quiet', str(req)]
                
                result = subprocess.run(
                    install_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                if result.returncode == 0:
                    installed.append(req)
                    if progress_callback:
                        progress_callback(req, 'installed')
                else:
                    error_msg = result.stderr.strip() or "Unknown error"
                    # Check for common skippable errors
                    if 'already satisfied' in error_msg.lower():
                        skipped.append((req, "already installed"))
                        if progress_callback:
                            progress_callback(req, 'skipped')
                    else:
                        failed.append((req, error_msg))
                        if progress_callback:
                            progress_callback(req, 'failed')
                        logger.error(f"Failed to install {req}: {error_msg}")
            
            except subprocess.TimeoutExpired:
                failed.append((req, f"Installation timeout ({timeout}s)"))
                if progress_callback:
                    progress_callback(req, 'failed')
            except Exception as e:
                failed.append((req, str(e)))
                if progress_callback:
                    progress_callback(req, 'failed')
                logger.error(f"Error installing {req}: {e}")
        
        return InstallResult(
            installed=installed,
            skipped=skipped,
            failed=failed
        )
    
    def get_installation_summary(self, result: InstallResult) -> Dict:
        """Get human-readable installation summary."""
        return {
            'total': result.total,
            'installed': len(result.installed),
            'skipped': len(result.skipped),
            'failed': len(result.failed),
            'success_rate': result.success_rate,
            'installed_packages': [str(r) for r in result.installed],
            'failed_packages': [(str(r), err) for r, err in result.failed]
        }


def get_dependency_installer(project_root: str = ".") -> DependencyInstaller:
    """Get a DependencyInstaller instance."""
    return DependencyInstaller(project_root)
