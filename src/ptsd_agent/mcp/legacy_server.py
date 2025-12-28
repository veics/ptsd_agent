"""
PTSD Agent MCP Server

Minimal, powerful MCP server for debugging and troubleshooting test runs.
Provides 2 consolidated tools for maximum debugging capability with minimum complexity.

Tools:
- diagnose: Retrieve any diagnostic information for debugging
- run_tests: Execute tests with flexible targeting

Resources:
- ptsd://status: Quick project status overview
"""

from mcp.server.fastmcp import FastMCP
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import os
import sys
from contextlib import contextmanager

# Context manager to temporarily suppress .env file access errors
@contextmanager
def _suppress_env_access():
    """Temporarily suppress .env file access errors during FastMCP initialization."""
    import builtins
    original_open = builtins.open
    
    def safe_open(file, *args, **kwargs):
        """Open file but skip .env files if permission denied."""
        if isinstance(file, (str, Path)) and str(file).endswith('.env'):
            try:
                return original_open(file, *args, **kwargs)
            except (PermissionError, OSError):
                # Return a dummy file-like object that reads nothing
                from io import StringIO
                return StringIO('')
        return original_open(file, *args, **kwargs)
    
    # Temporarily replace open() function
    builtins.open = safe_open
    try:
        yield
    finally:
        # Restore original open()
        builtins.open = original_open

# Initialize FastMCP server
# FastMCP uses pydantic-settings which tries to load .env files
# We suppress .env access errors since we don't need .env for MCP server operation
try:
    with _suppress_env_access():
        mcp = FastMCP("ptsd-agent")
except Exception as e:
    # If suppression didn't work, try a different approach
    # Create a minimal FastMCP instance without settings
    import warnings
    warnings.warn(f"FastMCP initialization had issues (continuing anyway): {e}", UserWarning)
    # Try one more time with environment variable to skip .env
    os.environ["_SKIP_ENV_FILE"] = "1"
    try:
        mcp = FastMCP("ptsd-agent")
    except Exception:
        # Last resort: create FastMCP with minimal config
        # This should work even if .env access fails
        mcp = FastMCP("ptsd-agent", debug=False)

# Global state
_initialized = False
_project_root: Optional[Path] = None
_config = None
_collector = None
_executor = None
_history = None


def _find_project_root() -> Path:
    """Find the project root by looking for .ptsd.yaml or .ptsd/."""
    # Check environment variable first
    if "PTSD_PROJECT_ROOT" in os.environ:
        return Path(os.environ["PTSD_PROJECT_ROOT"])
    
    # Check current directory and parents
    current = Path.cwd()
    for path in [current] + list(current.parents):
        if (path / ".ptsd.yaml").exists() or (path / ".ptsd").exists():
            return path
    
    # Fallback to script location (for wrapper script usage)
    script_dir = Path(__file__).parent.parent
    if (script_dir / ".ptsd.yaml").exists():
        return script_dir
    
    return current


def _init_server() -> bool:
    """Initialize server state on first use. Returns True if successful."""
    global _initialized, _project_root, _config, _collector, _executor, _history
    
    if _initialized:
        return True
    
    try:
        # Find and change to project root
        _project_root = _find_project_root()
        os.chdir(_project_root)
        
        # Add project root to Python path if needed
        root_str = str(_project_root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        
        # Import after path setup
        from ptsd_agent.config import load_config
        from ptsd_agent.metrics.collector import MetricsCollector
        from ptsd_agent.executor import TestExecutor
        from ptsd_agent.history import get_history_store
        
        _config = load_config(str(_project_root))
        _collector = MetricsCollector()
        _executor = TestExecutor(_collector)
        _history = get_history_store(str(_project_root / ".ptsd"))
        
        _initialized = True
        return True
        
    except Exception as e:
        # Return error info instead of crashing
        return False


def _ensure_initialized() -> Dict[str, Any]:
    """Ensure server is initialized, return error dict if not."""
    if not _init_server():
        return {
            "error": "Failed to initialize server",
            "hint": "Set PTSD_PROJECT_ROOT environment variable or run from project directory"
        }
    return {}


def _parse_scope(scope: str) -> Dict[str, Any]:
    """Parse scope string into structured target.
    
    Formats:
    - "project" -> all phases
    - "phase:N" -> specific phase
    - "component:name" -> specific component
    - "test:pattern" -> tests matching pattern
    """
    if scope == "project" or not scope:
        return {"type": "project"}
    
    if scope.startswith("phase:"):
        try:
            phase_id = int(scope.split(":")[1])
            return {"type": "phase", "id": phase_id}
        except (ValueError, IndexError):
            return {"type": "project"}
    
    if scope.startswith("component:"):
        comp_name = scope.split(":", 1)[1]
        return {"type": "component", "name": comp_name}
    
    if scope.startswith("test:"):
        pattern = scope.split(":", 1)[1]
        return {"type": "test", "pattern": pattern}
    
    return {"type": "project"}


def _get_summary() -> Dict[str, Any]:
    """Get project summary from latest run or current state."""
    err = _ensure_initialized()
    if err:
        return err
    
    # Try historical data first
    try:
        latest_run = _history.get_latest_run()
        if latest_run:
            overall = latest_run.get("overall", {})
            return {
                "run_id": latest_run.get("run_id"),
                "timestamp": latest_run.get("timestamp"),
                "pass_rate": overall.get("pass_rate", 0),
                "coverage": overall.get("coverage", 0),
                "total_tests": overall.get("total_tests", 0),
                "failures": overall.get("failures", 0),
                "errors": overall.get("errors", 0),
                "warnings": overall.get("warnings", 0),
                "skipped": overall.get("skipped", 0),
            }
    except Exception:
        pass
    
    # Fallback: no historical data
    return {
        "message": "No historical run data. Run tests first.",
        "pass_rate": 0,
        "coverage": 0,
        "total_tests": 0
    }


def _get_metrics(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Get metrics for specified scope."""
    err = _ensure_initialized()
    if err:
        return err
    
    try:
        latest_run = _history.get_latest_run()
    except Exception:
        latest_run = None
    
    if not latest_run:
        return {"error": "No historical run data available. Run tests first via CLI."}
    
    phases_data = latest_run.get("phases", {})
    
    if scope["type"] == "project":
        return {
            "by_phase": {
                pid: {
                    "name": pdata.get("name"),
                    "metrics": pdata.get("metrics", {}),
                    "component_count": len(pdata.get("components", {}))
                }
                for pid, pdata in phases_data.items()
            }
        }
    
    elif scope["type"] == "phase":
        phase_id = str(scope["id"])
        if phase_id in phases_data:
            pdata = phases_data[phase_id]
            return {
                "phase": phase_id,
                "name": pdata.get("name"),
                "metrics": pdata.get("metrics", {}),
                "components": pdata.get("components", {})
            }
        return {"error": f"Phase {phase_id} not found"}
    
    elif scope["type"] == "component":
        comp_name = scope["name"]
        for pid, pdata in phases_data.items():
            if comp_name in pdata.get("components", {}):
                return {
                    "phase": pid,
                    "component": comp_name,
                    "metrics": pdata["components"][comp_name]
                }
        return {"error": f"Component {comp_name} not found"}
    
    return {}


def _get_tests(scope: Dict[str, Any], filter_type: str) -> List[Dict[str, Any]]:
    """Get test results for specified scope and filter."""
    err = _ensure_initialized()
    if err:
        return []
    
    all_tests = []
    
    # Get from collector (current run)
    try:
        for comp_name, comp_metrics in _collector.components.items():
            for test in getattr(comp_metrics, 'tests', []):
                all_tests.append({
                    "component": comp_name,
                    "name": getattr(test, 'name', 'unknown'),
                    "status": getattr(test, 'status', 'unknown'),
                    "duration": getattr(test, 'duration', 0),
                    "error_message": getattr(test, 'error_message', None)
                })
    except Exception:
        pass
    
    # Apply filter
    if filter_type == "failures":
        all_tests = [t for t in all_tests if t["status"] == "failed"]
    elif filter_type == "errors":
        all_tests = [t for t in all_tests if t["status"] == "error"]
    elif filter_type == "slow":
        all_tests = sorted(all_tests, key=lambda t: t.get("duration", 0), reverse=True)[:20]
    
    # Apply scope filter
    if scope["type"] == "component":
        all_tests = [t for t in all_tests if t["component"] == scope.get("name")]
    elif scope["type"] == "test":
        pattern = scope.get("pattern", "").lower()
        all_tests = [t for t in all_tests if pattern in t.get("name", "").lower()]
    
    return all_tests


def _analyze_coverage_gaps(scope: Dict[str, Any], low_threshold: bool = False) -> Dict[str, Any]:
    """Analyze coverage gaps for the specified scope."""
    err = _ensure_initialized()
    if err:
        return {}
    
    try:
        latest_run = _history.get_latest_run()
    except Exception:
        latest_run = None
    
    if not latest_run:
        return {"error": "No historical run data available"}
    
    threshold = 80 if low_threshold else 100
    gaps = []
    
    phases_data = latest_run.get("phases", {})
    
    if scope["type"] == "project":
        for pid, pdata in phases_data.items():
            for comp_name, comp_data in pdata.get("components", {}).items():
                coverage = comp_data.get("coverage", 0)
                if coverage < threshold:
                    gaps.append({
                        "phase": pid,
                        "component": comp_name,
                        "coverage": coverage,
                        "target": threshold,
                        "gap": threshold - coverage
                    })
    elif scope["type"] == "phase":
        phase_id = str(scope["id"])
        if phase_id in phases_data:
            pdata = phases_data[phase_id]
            for comp_name, comp_data in pdata.get("components", {}).items():
                coverage = comp_data.get("coverage", 0)
                if coverage < threshold:
                    gaps.append({
                        "component": comp_name,
                        "coverage": coverage,
                        "target": threshold,
                        "gap": threshold - coverage
                    })
    elif scope["type"] == "component":
        comp_name = scope["name"]
        for pid, pdata in phases_data.items():
            if comp_name in pdata.get("components", {}):
                comp_data = pdata["components"][comp_name]
                coverage = comp_data.get("coverage", 0)
                if coverage < threshold:
                    gaps.append({
                        "phase": pid,
                        "component": comp_name,
                        "coverage": coverage,
                        "target": threshold,
                        "gap": threshold - coverage
                    })
    
    return {
        "threshold": threshold,
        "gaps": sorted(gaps, key=lambda x: x["gap"], reverse=True),
        "total_gaps": len(gaps)
    }


def _get_warnings(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Get warnings for the specified scope."""
    err = _ensure_initialized()
    if err:
        return {}
    
    try:
        latest_run = _history.get_latest_run()
    except Exception:
        latest_run = None
    
    if not latest_run:
        return {"error": "No historical run data available"}
    
    warnings_data = []
    phases_data = latest_run.get("phases", {})
    
    if scope["type"] == "project":
        for pid, pdata in phases_data.items():
            for comp_name, comp_data in pdata.get("components", {}).items():
                warnings_count = comp_data.get("warnings", 0)
                if warnings_count > 0:
                    warnings_data.append({
                        "phase": pid,
                        "component": comp_name,
                        "count": warnings_count
                    })
    elif scope["type"] == "phase":
        phase_id = str(scope["id"])
        if phase_id in phases_data:
            pdata = phases_data[phase_id]
            for comp_name, comp_data in pdata.get("components", {}).items():
                warnings_count = comp_data.get("warnings", 0)
                if warnings_count > 0:
                    warnings_data.append({
                        "component": comp_name,
                        "count": warnings_count
                    })
    elif scope["type"] == "component":
        comp_name = scope["name"]
        for pid, pdata in phases_data.items():
            if comp_name in pdata.get("components", {}):
                comp_data = pdata["components"][comp_name]
                warnings_count = comp_data.get("warnings", 0)
                if warnings_count > 0:
                    warnings_data.append({
                        "phase": pid,
                        "component": comp_name,
                        "count": warnings_count
                    })
    
    return {
        "total": sum(w.get("count", 0) for w in warnings_data),
        "by_component": warnings_data
    }


def _get_logs(lines: int = 50) -> List[Dict[str, Any]]:
    """Get recent log entries."""
    err = _ensure_initialized()
    if err:
        return []
    
    try:
        from ptsd_agent.report_logging import get_log_manager
        log_manager = get_log_manager()
        recent_entries = log_manager.entries[-lines:]
        
        return [
            {
                "timestamp": getattr(entry, 'timestamp', ''),
                "level": getattr(entry, 'level', ''),
                "phase": getattr(entry, 'phase', ''),
                "component": getattr(entry, 'component', ''),
                "message": getattr(entry, 'message', '')
            }
            for entry in recent_entries
        ]
    except Exception:
        return []


def _get_history() -> Dict[str, Any]:
    """Get recent run history."""
    err = _ensure_initialized()
    if err:
        return err
    
    try:
        runs = _history.list_runs(limit=5)
        latest_logs = _history.get_latest_logs()
        return {
            "recent_runs": runs,
            "latest_logs": latest_logs
        }
    except Exception as e:
        return {"error": str(e)}


def _get_config() -> Dict[str, Any]:
    """Get project configuration."""
    err = _ensure_initialized()
    if err:
        return err
    
    try:
        phases = []
        for phase_id in _config.get_all_phases():
            phase_cfg = _config.get_phase_config(phase_id)
            components = _config.get_phase_components(phase_id)
            phases.append({
                "id": phase_id,
                "name": phase_cfg.get("name", f"Phase {phase_id}"),
                "components": components
            })
        
        # Add Task Master summary
        from ptsd_agent.taskmaster import TaskMasterLoader
        tm_loader = TaskMasterLoader(str(_project_root))
        tm_summary = tm_loader.load()
        
        return {
            "project_name": _config.project_name,
            "project_root": str(_project_root),
            "phases": phases,
            "taskmaster": {
                "total_tasks": tm_summary.total_tasks if tm_summary else 0,
                "done_tasks": tm_summary.done_tasks if tm_summary else 0,
                "completion_pct": tm_summary.completion_pct if tm_summary else 0
            } if tm_summary else None
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def diagnose(
    scope: str = "project",
    filter: str = "all",
    include: Optional[List[str]] = None
) -> str:
    """Retrieve diagnostic information for debugging and troubleshooting.
    
    This is the primary tool for understanding test failures, errors, and project status.
    
    Args:
        scope: What to diagnose. Options:
            - "project" (default): Full project overview
            - "phase:N": Specific phase (e.g., "phase:2")
            - "component:name": Specific component (e.g., "component:acl")
            - "test:pattern": Tests matching pattern (e.g., "test:auth")
        
        filter: Filter results. Options:
            - "all" (default): All results
            - "failures": Only failed tests
            - "errors": Only tests with errors
            - "warnings": Components with warnings
            - "slow": Slowest tests
            - "coverage_gaps": Components with coverage < 100%
            - "low_coverage": Components with coverage < 80%
        
        include: Sections to include in response. Options:
            - "summary": Pass rate, coverage, totals
            - "metrics": Detailed per-phase/component metrics
            - "tests": Individual test results
            - "warnings": Warning counts by component
            - "logs": Recent log entries
            - "history": Historical run data
            - "config": Project configuration
            Default: ["summary", "metrics", "tests"]
    
    Returns:
        JSON string with requested diagnostic information.
    
    Examples:
        diagnose()  # Full project summary
        diagnose(scope="component:acl", filter="failures")  # Failed tests in acl
        diagnose(include=["logs", "history"])  # Logs and history only
    """
    # Default includes
    if include is None:
        include = ["summary", "metrics", "tests"]
    
    parsed_scope = _parse_scope(scope)
    result = {"scope": scope, "filter": filter}
    
    try:
        if "summary" in include:
            result["summary"] = _get_summary()
        
        if "metrics" in include:
            metrics_data = _get_metrics(parsed_scope)
            result["metrics"] = metrics_data
            
            # Add coverage gap analysis if requested
            if filter in ["coverage_gaps", "low_coverage"]:
                result["coverage_gaps"] = _analyze_coverage_gaps(parsed_scope, filter == "low_coverage")
        
        if "tests" in include:
            result["tests"] = _get_tests(parsed_scope, filter)
        
        if "warnings" in include:
            result["warnings"] = _get_warnings(parsed_scope)
        
        if "logs" in include:
            result["logs"] = _get_logs()
        
        if "history" in include:
            result["history"] = _get_history()
        
        if "config" in include:
            result["config"] = _get_config()
    
    except Exception as e:
        result["error"] = str(e)
    
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def run_tests(
    target: str = "all",
    options: Optional[Dict[str, Any]] = None
) -> str:
    """Execute tests with flexible targeting.
    
    Args:
        target: What to test. Options:
            - "all": Run all tests
            - "phase:N": Run tests for specific phase
            - "component:name": Run tests for specific component
        
        options: Execution options (optional):
            - parallel: Run in parallel (default: True)
            - fail_fast: Stop on first failure (default: False)
    
    Returns:
        JSON string with test execution results.
    
    Examples:
        run_tests()  # Run all tests
        run_tests(target="phase:2")  # Run Phase 2 tests
        run_tests(target="component:acl", options={"parallel": False})
    """
    err = _ensure_initialized()
    if err:
        return json.dumps(err, indent=2)
    
    try:
        # Parse options
        opts = options or {}
        parallel = opts.get("parallel", True)
        
        parsed = _parse_scope(target)
        components_to_test = []
        
        if parsed["type"] == "project" or target == "all":
            # Test all components
            for phase_id in _config.get_all_phases():
                for comp in _config.get_phase_components(phase_id):
                    test_path = _config.get_component_test_path(phase_id, comp)
                    if test_path and test_path != "tests/":
                        components_to_test.append((phase_id, comp, test_path))
        
        elif parsed["type"] == "phase":
            phase_id = parsed["id"]
            for comp in _config.get_phase_components(phase_id):
                test_path = _config.get_component_test_path(phase_id, comp)
                if test_path and test_path != "tests/":
                    components_to_test.append((phase_id, comp, test_path))
        
        elif parsed["type"] == "component":
            comp_name = parsed["name"]
            for phase_id in _config.get_all_phases():
                if comp_name in _config.get_phase_components(phase_id):
                    test_path = _config.get_component_test_path(phase_id, comp_name)
                    components_to_test.append((phase_id, comp_name, test_path))
                    break
        
        if not components_to_test:
            return json.dumps({"error": "No components found to test", "target": target})
        
        # Run tests
        results = []
        for pid, comp, test_path in components_to_test:
            _executor.run_component(pid, comp, test_path)
            comp_metrics = _collector.get_component(comp)
            
            results.append({
                "phase": pid,
                "component": comp,
                "passed": comp_metrics.passed,
                "failed": comp_metrics.failed,
                "errors": comp_metrics.errors,
                "skipped": comp_metrics.skipped,
                "coverage": comp_metrics.coverage,
                "pass_rate": comp_metrics.pass_rate
            })
        
        summary = _collector.get_summary()
        
        # Get failed tests for debugging
        failed_tests = _get_tests({"type": "project"}, "failures")
        
        # Get verbose error output if any failures
        error_output = []
        if _executor and hasattr(_executor, 'get_error_buffer'):
            error_output = _executor.get_error_buffer()
        
        return json.dumps({
            "target": target,
            "summary": summary,
            "components": results,
            "failed_tests": failed_tests[:10],  # Top 10 failures for quick debugging
            "verbose_errors": error_output[:50] if error_output else []  # Last 50 error lines
        }, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e), "target": target}, indent=2)


@mcp.resource("ptsd://status")
def get_status() -> str:
    """Get quick project status overview.
    
    Returns combined summary of project configuration, latest run metrics,
    and Task Master status for a complete project health picture.
    """
    try:
        summary = _get_summary()
        config = _get_config()
        
        return json.dumps({
            "project": config.get("project_name"),
            "project_root": config.get("project_root"),
            "phases": len(config.get("phases", [])),
            "latest_run": summary,
            "taskmaster": config.get("taskmaster")
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    mcp.run()
