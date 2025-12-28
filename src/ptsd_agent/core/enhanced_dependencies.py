"""Enhanced dependency system with external library support.

Supports both internal component dependencies and external library dependencies.
Automatically checks library versions to detect when blockers are resolved.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from packaging import version
import subprocess
import importlib.metadata
import logging

logger = logging.getLogger(__name__)


@dataclass
class InternalDependency:
    """Internal component/phase dependency."""
    phase_id: int
    component: str
    required: bool = True  # If False, soft dependency (warn but don't block)
    
    def __str__(self) -> str:
        prefix = "requires" if self.required else "suggests"
        return f"{prefix} Phase {self.phase_id}:{self.component}"


@dataclass
class ExternalDependency:
    """External library dependency."""
    package: str
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    reason: str = ""
    ticket_url: Optional[str] = None
    
    def __str__(self) -> str:
        ver_str = ""
        if self.min_version:
            ver_str = f">={self.min_version}"
        if self.max_version:
            ver_str += f",<{self.max_version}" if ver_str else f"<{self.max_version}"
        
        pkg_str = f"{self.package}{ver_str}" if ver_str else self.package
        return f"requires {pkg_str}"
    
    def is_satisfied(self) -> bool:
        """Check if this dependency is satisfied.
        
        Returns:
            True if package is installed and meets version requirements
        """
        try:
            installed_version = importlib.metadata.version(self.package)
            
            if self.min_version:
                if version.parse(installed_version) < version.parse(self.min_version):
                    logger.debug(f"{self.package} {installed_version} < required {self.min_version}")
                    return False
            
            if self.max_version:
                if version.parse(installed_version) >= version.parse(self.max_version):
                    logger.debug(f"{self.package} {installed_version} >= max {self.max_version}")
                    return False
            
            logger.debug(f"{self.package} {installed_version} satisfies requirements")
            return True
            
        except importlib.metadata.PackageNotFoundError:
            logger.debug(f"{self.package} not installed")
            return False
        except Exception as e:
            logger.warning(f"Error checking {self.package}: {e}")
            return False
    
    def check_for_updates(self) -> Optional[str]:
        """Check if a newer version is available on PyPI.
        
        Returns:
            Latest version string if available, None if up-to-date or error
        """
        try:
            import urllib.request
            import json
            
            url = f"https://pypi.org/pypi/{self.package}/json"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                latest_version = data['info']['version']
                
                # Check if latest satisfies our requirements
                if self.min_version:
                    if version.parse(latest_version) >= version.parse(self.min_version):
                        # Check current installation
                        try:
                            current = importlib.metadata.version(self.package)
                            if version.parse(latest_version) > version.parse(current):
                                return latest_version
                        except importlib.metadata.PackageNotFoundError:
                            return latest_version  # Not installed, latest available
                
                return None
                
        except Exception as e:
            logger.debug(f"Could not check updates for {self.package}: {e}")
            return None
    
    def get_update_command(self) -> str:
        """Get pip command to update this dependency.
        
        Returns:
            pip install command string
        """
        if self.min_version:
            return f"pip install '{self.package}>={self.min_version}'"
        return f"pip install --upgrade {self.package}"


@dataclass
class DependencySpec:
    """Complete dependency specification for a component."""
    phase_id: int
    component: str
    internal_deps: List[InternalDependency] = field(default_factory=list)
    external_deps: List[ExternalDependency] = field(default_factory=list)
    
    def get_internal_blockers(self, failed_components: Set[str]) -> List[InternalDependency]:
        """Get internal dependencies that are blocking.
        
        Args:
            failed_components: Set of component identifiers that have failed
                              Format: "phase_id:component_name"
        
        Returns:
            List of dependencies that are blocking
        """
        blockers = []
        for dep in self.internal_deps:
            if not dep.required:
                continue  # Soft dependencies don't block
            
            dep_id = f"{dep.phase_id}:{dep.component}"
            if dep_id in failed_components:
                blockers.append(dep)
        
        return blockers
    
    def get_external_blockers(self) -> List[ExternalDependency]:
        """Get external dependencies that are blocking.
        
        Returns:
            List of external dependencies not satisfied
        """
        return [dep for dep in self.external_deps if not dep.is_satisfied()]
    
    def is_blocked(self, failed_components: Set[str]) -> bool:
        """Check if component is blocked by dependencies.
        
        Args:
            failed_components: Set of failed component identifiers
        
        Returns:
            True if blocked by any dependency
        """
        return bool(self.get_internal_blockers(failed_components) or 
                   self.get_external_blockers())


class DependencyManager:
    """Manages all component dependencies."""
    
    def __init__(self):
        """Initialize dependency manager."""
        self.specs: Dict[str, DependencySpec] = {}
        self.failed_components: Set[str] = set()
    
    def add_spec(self, spec: DependencySpec):
        """Add a dependency specification.
        
        Args:
            spec: DependencySpec to add
        """
        key = f"{spec.phase_id}:{spec.component}"
        self.specs[key] = spec
    
    def load_from_config(self, config: Dict[str, Any]):
        """Load dependency specs from .ptsd.yaml config.
        
        Args:
            config: Parsed .ptsd.yaml configuration
        """
        components = config.get('components', {})
        
        for comp_name, comp_config in components.items():
            phase_id = comp_config.get('phase', 1)
            
            spec = DependencySpec(phase_id=phase_id, component=comp_name)
            
            # Load internal dependencies
            internal_deps = comp_config.get('depends_on', [])
            for dep in internal_deps:
                if isinstance(dep, str):
                    # Simple format: "component_name" (same phase)
                    spec.internal_deps.append(
                        InternalDependency(phase_id=phase_id, component=dep)
                    )
                elif isinstance(dep, dict):
                    # Detailed format: {phase: 1, component: "name", required: true}
                    spec.internal_deps.append(
                        InternalDependency(
                            phase_id=dep.get('phase', phase_id),
                            component=dep['component'],
                            required=dep.get('required', True)
                        )
                    )
            
            # Load external dependencies
            external_deps = comp_config.get('external_deps', [])
            for dep in external_deps:
                if isinstance(dep, str):
                    # Simple format: "package>=1.0.0"
                    spec.external_deps.append(self._parse_external_dep(dep))
                elif isinstance(dep, dict):
                    # Detailed format with reason/ticket
                    spec.external_deps.append(
                        ExternalDependency(
                            package=dep['package'],
                            min_version=dep.get('min_version'),
                            max_version=dep.get('max_version'),
                            reason=dep.get('reason', ''),
                            ticket_url=dep.get('ticket_url')
                        )
                    )
            
            if spec.internal_deps or spec.external_deps:
                self.add_spec(spec)
    
    def _parse_external_dep(self, dep_str: str) -> ExternalDependency:
        """Parse external dependency from string like 'package>=1.0.0'."""
        # Simple parser, can be enhanced
        if '>=' in dep_str:
            package, min_ver = dep_str.split('>=')
            return ExternalDependency(package=package.strip(), min_version=min_ver.strip())
        elif '>' in dep_str:
            package, min_ver = dep_str.split('>')
            return ExternalDependency(package=package.strip(), min_version=min_ver.strip())
        elif '<' in dep_str:
            package, max_ver = dep_str.split('<')
            return ExternalDependency(package=package.strip(), max_version=max_ver.strip())
        else:
            return ExternalDependency(package=dep_str.strip())
    
    def mark_failed(self, phase_id: int, component: str):
        """Mark a component as failed.
        
        Args:
            phase_id: Phase ID
            component: Component name
        """
        self.failed_components.add(f"{phase_id}:{component}")
    
    def mark_passed(self, phase_id: int, component: str):
        """Mark a component as passed (clear failed status).
        
        Args:
            phase_id: Phase ID
            component: Component name
        """
        key = f"{phase_id}:{component}"
        self.failed_components.discard(key)
    
    def is_blocked(self, phase_id: int, component: str) -> bool:
        """Check if component is blocked.
        
        Args:
            phase_id: Phase ID
            component: Component name
        
        Returns:
            True if blocked
        """
        key = f"{phase_id}:{component}"
        spec = self.specs.get(key)
        
        if not spec:
            return False  # No dependencies = not blocked
        
        return spec.is_blocked(self.failed_components)
    
    def get_blocker_summary(self, phase_id: int, component: str) -> Dict[str, Any]:
        """Get summary of what's blocking a component.
        
        Args:
            phase_id: Phase ID
            component: Component name
        
        Returns:
            Dictionary with internal and external blocker details
        """
        key = f"{phase_id}:{component}"
        spec = self.specs.get(key)
        
        if not spec:
            return {'blocked': False}
        
        internal = spec.get_internal_blockers(self.failed_components)
        external = spec.get_external_blockers()
        
        return {
            'blocked': bool(internal or external),
            'internal_blockers': [str(d) for d in internal],
            'external_blockers': [str(d) for d in external],
            'can_auto_retest': not external  # Can retest if only internal blockers
        }
    
    def check_external_updates(self) -> Dict[str, Any]:
        """Check all external dependencies for available updates.
        
        Returns:
            Dictionary with update information for each blocked dependency
        """
        updates = {
            'available': [],
            'blockers_resolved': [],
            'commands': []
        }
        
        for spec in self.specs.values():
            for ext_dep in spec.external_deps:
                if not ext_dep.is_satisfied():
                    # Check for updates
                    latest = ext_dep.check_for_updates()
                    
                    if latest:
                        updates['available'].append({
                            'package': ext_dep.package,
                            'latest': latest,
                            'required': ext_dep.min_version,
                            'component': spec.component,
                            'phase': spec.phase_id,
                            'reason': ext_dep.reason
                        })
                        
                        # If latest satisfies requirement, blocker is resolved
                        if ext_dep.min_version:
                            if version.parse(latest) >= version.parse(ext_dep.min_version):
                                updates['blockers_resolved'].append({
                                    'package': ext_dep.package,
                                    'version': latest,
                                    'component': f"Phase {spec.phase_id}:{spec.component}"
                                })
                                updates['commands'].append(ext_dep.get_update_command())
        
        return updates
    
    def auto_update_check(self) -> str:
        """Run update check and generate human-readable report.
        
        Returns:
            Formatted string with update information
        """
        updates = self.check_external_updates()
        
        if not updates['available']:
            return "✓ All external dependencies up-to-date or no updates available"
        
        lines = ["External Dependency Updates Available:\n"]
        
        if updates['blockers_resolved']:
            lines.append("🎉 BLOCKERS RESOLVED:")
            for blocker in updates['blockers_resolved']:
                lines.append(f"  ✓ {blocker['package']} {blocker['version']} now available")
                lines.append(f"    → Unblocks: {blocker['component']}")
            lines.append("")
        
        if updates['available']:
            lines.append("📦 Updates available:")
            for upd in updates['available']:
                lines.append(f"  • {upd['package']}: {upd['latest']} (requires >={upd['required']})")
                lines.append(f"    Component: Phase {upd['phase']}:{upd['component']}")
                if upd['reason']:
                    lines.append(f"    Reason: {upd['reason']}")
        
        if updates['commands']:
            lines.append("\n💡 Run these commands to resolve blockers:")
            for cmd in updates['commands']:
                lines.append(f"  {cmd}")
        
        return "\n".join(lines)
