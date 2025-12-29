"""Configuration loader for ptsd_agent.

Loads project configuration from:
1. .ptsd.yaml file (if exists)
2. Environment variables (overrides)
3. Auto-discovery (fallback)
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class ProjectConfig:
    """Configuration for test project structure and execution"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict
        self.project_name = self._config.get('project', {}).get('name', 'Unknown Project')
        self.phases = self._config.get('phases', [])
        self.experimental = self._config.get('experimental', {})
        self.include_dev_tests = self.experimental.get('include_dev_tests', False)
        self._diagnostics_config = self._load_diagnostics_config()
    
    def _load_diagnostics_config(self) -> Dict:
        """Load diagnostics configuration from ptsd_agent.config.json"""
        import json
        from pathlib import Path
        
        # Default diagnostics config
        defaults = {
            "show_diagnostics": False,
            "use_tree_view": False,  # Use hierarchical tree view for diagnostics
            "show_all_diagnostics": False,  # Show all items, not just first 2 per category
            "diagnostics_limits": {
                "max_failures": 10,
                "max_errors": 10,
                "max_warnings": 20,
                "max_skipped": 50
            }
        }
        
        # Try to load from config file
        config_path = Path("ptsd_agent.config.json")
        if config_path.exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    if "diagnostics" in user_config:
                        diag_conf = user_config["diagnostics"]
                        if "show_diagnostics" in diag_conf:
                            defaults["show_diagnostics"] = diag_conf["show_diagnostics"]
                        if "use_tree_view" in diag_conf:
                            defaults["use_tree_view"] = diag_conf["use_tree_view"]
                        if "show_all_diagnostics" in diag_conf:
                            defaults["show_all_diagnostics"] = diag_conf["show_all_diagnostics"]
                        if "diagnostics_limits" in diag_conf:
                            defaults["diagnostics_limits"].update(diag_conf["diagnostics_limits"])
            except Exception as e:
                import logging
                logging.warning(f"Failed to load diagnostics config: {e}")
        
        return defaults
    
    def get_diagnostics_config(self) -> Dict[str, Any]:
        """Get diagnostics display configuration"""
        # Return the diagnostics config loaded during initialization
        # This includes both show_diagnostics and diagnostics_limits from config file or defaults
        return self._diagnostics_config
    
    def get_parallel_config(self) -> Dict[str, Any]:
        """Get parallel execution configuration
        
        Returns:
            Dict with 'max_workers' key (0=auto, >0=specific count)
        """
        parallel = self._config.get('parallel', {})
        return {
            'max_workers': parallel.get('max_workers', 0)  # 0 = auto-detect
        }
    
    def get_chart_config(self) -> Dict[str, Any]:
        """Get chart display configuration
        
        Config keys:
            height: Number of rows (default: 6)
            width: Fixed columns or percentage string like '100%' (default: '100%')
            enabled: Whether chart is enabled (default: True)
            colors:
                axis: ANSI color code for Y/X axis (default: 172 - dimmed orange)
                empty: ANSI color code for unprogressed bar (default: 236 - grey)
                blink: ANSI color code for blinking progress edge (default: 214 - orange)
                blink_chars: Number of chars to blink (default: 2)
        
        Returns:
            Dict with chart configuration
        """
        chart = self._config.get('chart', {})
        colors = chart.get('colors', {})
        return {
            'height': chart.get('height', 6),
            'width': chart.get('width', '100%'),
            'enabled': chart.get('enabled', True),
            'colors': {
                'axis': colors.get('axis', 94),
                'empty': colors.get('empty', 236),
                'blink': colors.get('blink', 214),
                'blink_chars': colors.get('blink_chars', 2)
            }
        }
    
    def get_phase_config(self, phase_id: int) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific phase"""
        for phase in self.phases:
            if phase.get('id') == phase_id:
                return phase
        return None
    
    def get_component_test_path(self, phase_id: int, component_name: str) -> str:
        """Get test path for a specific component. Returns empty string if not configured."""
        phase = self.get_phase_config(phase_id)
        if not phase:
            return ""
        
        for component in phase.get('components', []):
            if component.get('name') == component_name:
                # Return configured test_path, or empty string if not set
                return component.get('test_path', '')
        
        return ""
    
    def get_all_phases(self) -> List[int]:
        """Get list of all phase IDs"""
        return [p['id'] for p in self.phases]
    
    def get_phase_components(self, phase_id: int) -> List[str]:
        """Get list of component names for a phase"""
        phase = self.get_phase_config(phase_id)
        if not phase:
            return []
        return [c['name'] for c in phase.get('components', [])]


def _print_config_line(source: str):
    """Print config loading line with discovery-style formatting.
    Uses right-aligned percentage and consistent formatting.
    """
    import shutil
    term_width = shutil.get_terminal_size().columns
    
    # Use shared components for consistent alignment
    try:
        from ptsd_agent.ui.components import right_align_text
        from ptsd_agent.ui.theme import GREEN, DIM, RESET
    except ImportError:
        GREEN = "\033[92m"
        DIM = "\033[2m"
        RESET = "\033[0m"
        right_align_text = None
    
    BOLD = "\033[1m"
    
    # Left side: ✓ Loaded configuration from {source}
    left = f"{GREEN}✓{RESET} {DIM}Loaded configuration from{RESET} {BOLD}{source}{RESET}"
    
    # Right side: 100% with 3 trailing spaces to align with Running Tests UI
    right = f"{DIM}100%{RESET}   "
    
    if right_align_text:
        # Use shared alignment function with no trailing space
        line = right_align_text(left, right, term_width, trailing_space=0)
        print(line)
    else:
        # Fallback: manual alignment
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        left_visible = len(ansi_escape.sub('', left))
        right_visible = len(ansi_escape.sub('', right))
        padding = term_width - left_visible - right_visible
        print(f"{left}{' ' * max(1, padding)}{right}")


def load_config(project_root: str = ".") -> ProjectConfig:
    """Load project configuration
    
    Priority:
    1. Task Master AI (if available)
    2. .ptsd.yaml file (if exists)
    3. Auto-discovery (fallback)
    
    Args:
        project_root: Path to project root directory
        
    Returns:
        ProjectConfig instance
    """
    import os
    silent = os.environ.get('PTSD_SILENT_CONFIG') == '1'
    
    # Try Task Master AI first
    try:
        from .taskmaster_integration import discover_with_taskmaster
        tm_config = discover_with_taskmaster(project_root)
        if tm_config:
            if not silent:
                _print_config_line("Task Master AI")
            return ProjectConfig(tm_config)
    except ImportError:
        pass  # Task Master integration not available
    
    # Try YAML config file
    config_path = Path(project_root) / ".ptsd.yaml"
    if config_path.exists():
        if not silent:
            _print_config_line(".ptsd.yaml")
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return ProjectConfig(config_dict)
    
    # Fallback to auto-discovery
    if not silent:
        _print_config_line("auto-discovery")
    return auto_discover_project(project_root)


def auto_discover_project(project_root: str = ".") -> ProjectConfig:
    """Auto-discover project structure if no config file exists
    
    Scans for:
    - services/ directory (microservices architecture)
    - tests/ directory (monolithic architecture)
    - Phase organization based on service structure
    
    Args:
        project_root: Path to project root directory
        
    Returns:
        ProjectConfig instance with discovered structure
    """
    root_path = Path(project_root)
    project_name = root_path.name
    
    phases = []
    
    # Strategy 1: Scan services/ directory for microservices
    services_dir = root_path / "services"
    if services_dir.exists() and services_dir.is_dir():
        
        # Get all service directories (filter out invalid names)
        service_dirs = [
            d for d in services_dir.iterdir() 
            if d.is_dir() and not d.name.startswith('.') and d.name != '*'
        ]
        
        if service_dirs:
            # Group services into logical phases
            # You can customize this grouping logic
            components = []
            for service_dir in sorted(service_dirs):
                service_name = service_dir.name
                
                # Look for tests in service directory
                test_path = f"services/{service_name}/tests/"
                if not (service_dir / "tests").exists():
                    # Fallback to root tests/
                    test_path = "tests/"
                
                components.append({
                    'name': service_name,
                    'test_path': test_path
                })
            
            # Create a single phase with all services
            phases.append({
                'id': 1,
                'name': 'Core Services',
                'components': components
            })
            
            print(f"  Discovered {len(components)} services")
    
    # Strategy 2: Fallback to simple tests/ directory
    if not phases:
        test_dir = root_path / "tests"
        if test_dir.exists():
            phases.append({
                'id': 1,
                'name': 'Default Phase',
                'components': [
                    {
                        'name': 'default',
                        'test_path': 'tests/'
                    }
                ]
            })
    
    # Strategy 3: No tests found
    if not phases:
        print(f"  Warning: No tests/ or services/ directory found")
        phases = []
    
    config_dict = {
        'project': {'name': project_name},
        'phases': phases
    }
    
    return ProjectConfig(config_dict)
