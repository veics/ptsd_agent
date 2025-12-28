import subprocess
import time
import re
import sys
import os
import shutil
import logging
import ast
from typing import Dict, List, Optional
from pathlib import Path
from ptsd_agent.metrics.legacy_collector import MetricsCollector, TestResult
from ..discovery.fast_counter import FastTestCounter  # NEW: Phase 2
from ..core.thread_pool import OperationType, OperationPriority  # NEW: Phase 5

logger = logging.getLogger(__name__)


# Mapping of test paths to their source service directories
# This allows tests to import from app.* etc.
SERVICE_PATH_MAP = {
    # Direct service paths - tests are in their original locations
    "services/acl/tests/": "services/acl",
    "services/rag_core/tests/": "services/rag_core",
    "services/identity_mapping/tests/": "services/identity_mapping",
    "services/profile/tests/": "services/profile",
    "services/dataset_builder/tests/": "services/dataset_builder",
    "services/training_orchestrator/tests/": "services/training_orchestrator",
    "services/cdn/tests/": "services/cdn",
    "services/search_engine/tests/": "services/search_engine",
}


class TestExecutor:
    """Executes tests and streams real-time metrics to the collector"""
    
    def __init__(self, collector: MetricsCollector, coverage_temp_dir: str = None, 
                 coverage_storage_dir: str = None, run_id: str = None, thread_pool=None):
        self.collector = collector
        self.thread_pool = thread_pool  # NEW: Thread pool for operations
        import tempfile
        self.coverage_temp_dir = coverage_temp_dir or tempfile.gettempdir()
        self.coverage_storage_dir = coverage_storage_dir
        self.run_id = run_id
        self._error_buffer: List[str] = []  # Capture error output for debugging
        self._coverage_files: Dict[str, str] = {}  # Track coverage files per component
        self._discovery_cache: Dict[str, Dict] = {}  # NEW: Cache discovery results (Phase 2)
        self._fast_counter = FastTestCounter()  # NEW: Fast test counting (Phase 2)
    
    def get_error_buffer(self) -> List[str]:
        """Get captured error output from the last test run."""
        return self._error_buffer.copy()
    
    def get_coverage_files(self) -> Dict[str, str]:
        """Get dictionary of component names to their coverage file paths."""
        return self._coverage_files.copy()

    def _get_service_dir_for_path(self, test_path: str) -> Optional[str]:
        """Get the service directory for a test path"""
        for pattern, service_dir in SERVICE_PATH_MAP.items():
            if test_path.startswith(pattern) or test_path == pattern.rstrip('/'):
                if Path(service_dir).exists():
                    return service_dir
        # Also check if test_path is directly inside a service
        if test_path.startswith("services/"):
            parts = test_path.split("/")
            if len(parts) >= 2:
                service_dir = f"services/{parts[1]}"
                if Path(service_dir).exists():
                    return service_dir
        return None
    
    def _get_coverage_path_for_component(self, component_name: str, test_path: str) -> Optional[str]:
        """Get the coverage path for a component.
        
        Returns the path to measure coverage for, or None if coverage doesn't apply.
        Special handling for phase 1 components:
        - architecture: core/
        - contracts: None (YAML files, no coverage)
        - acl: services/acl/app
        """
        # Special cases for phase 1 components
        if component_name == "architecture":
            core_path = Path("core").absolute()
            if core_path.exists():
                return str(core_path)
        elif component_name == "contracts":
            # Contracts are YAML files - no coverage measurement
            return None
        
        # For service-based components, use the service/app directory
        service_dir = self._get_service_dir_for_path(test_path)
        if service_dir:
            app_path = Path(service_dir) / "app"
            if app_path.exists():
                return str(app_path)
        
        return None
    
    def _get_pytest_executable(self, test_path: str) -> tuple:
        """Get the pytest executable and python for a test path.
        
        Returns:
            Tuple of (pytest_cmd, python_executable)
            - If service has its own venv, use that
            - Otherwise use main venv
        """
        service_dir = self._get_service_dir_for_path(test_path)
        if service_dir:
            # Check for service-specific venv
            service_venv_pytest = Path(service_dir) / "venv" / "bin" / "pytest"
            service_venv_python = Path(service_dir) / "venv" / "bin" / "python"
            if service_venv_pytest.exists():
                return str(service_venv_pytest), str(service_venv_python)
            # Also check .venv
            service_venv_pytest = Path(service_dir) / ".venv" / "bin" / "pytest"
            service_venv_python = Path(service_dir) / ".venv" / "bin" / "python"
            if service_venv_pytest.exists():
                return str(service_venv_pytest), str(service_venv_python)
        
        # Fallback to main venv
        return f"{sys.executable} -m pytest", sys.executable

    def _get_pythonpath_for_test(self, test_path: str) -> Optional[str]:
        """Determine the PYTHONPATH needed for a test path"""
        for pattern, service_dir in SERVICE_PATH_MAP.items():
            if test_path.startswith(pattern) or test_path == pattern.rstrip('/'):
                if Path(service_dir).exists():
                    return str(Path(service_dir).absolute())
        return None

    def run_component(self, phase_id: int, component_name: str, test_path: str = "tests/", simulation: bool = False, callback=None):
        """Run tests for a specific component and parse output
        
        Args:
            phase_id: Phase ID
            component_name: Component name
            test_path: Path to tests
            simulation: Whether to run in simulation mode
            callback: Optional callback function(test_name) called when each test starts
        """
        if simulation:
            return self._simulate_run(phase_id, component_name)
        
        # Get PYTHONPATH for this test
        pythonpath = self._get_pythonpath_for_test(test_path)
        
                # No tests discovered - just return 0
                return 0
            # Store discovered count for accurate progress calculation
            self.collector.set_discovered_total(component_name, len(tests))
        
        # Run pytest with verbose output
        return self._run_pytest(component_name, test_path, pythonpath=pythonpath, callback=callback)

    
    def _discover_tests(self, test_path: str, pythonpath: str = None) -> tuple:
        """Discover test files using pytest collection.
        
        Returns:
            Tuple of (tests_list, error_message). error_message is None if no errors.
        """
        if not Path(test_path).exists():
            return [], f"Path does not exist: {test_path}"
        
        # Build environment with PYTHONPATH if needed
        env = os.environ.copy()
        if pythonpath:
            existing = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = f"{pythonpath}:{existing}" if existing else pythonpath
        
        # Get service-specific pytest if available
        pytest_cmd, python_exe = self._get_pytest_executable(test_path)
        
        try:
            # Build command based on pytest_cmd type
            if " -m pytest" in pytest_cmd:
                cmd = [python_exe, "-m", "pytest", "--collect-only", "-q", test_path]
            else:
                cmd = [pytest_cmd, "--collect-only", "-q", test_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            output = result.stdout + result.stderr
            
            import re
            
            # FIRST: Check for collected tests - prioritize finding tests over errors
            # This handles partial collection where some files error but others succeed
            match = re.search(r'(\d+)\s+tests?\s+collected', output)
            if match:
                count = int(match.group(1))
                if count > 0:
                    return ["test"] * count, None  # Tests found, run them
            
            # Also check for actual test lines (file.py::test_name format)
            lines = result.stdout.split('\n')
            test_lines = [l for l in lines if '::test_' in l or '::Test' in l]
            if test_lines:
                return test_lines, None
            
            # No tests were collected - check for errors to report
            if 'ImportError' in output or 'ModuleNotFoundError' in output:
                error_match = re.search(r'(ModuleNotFoundError|ImportError).*$', output, re.MULTILINE)
                error_msg = error_match.group(0) if error_match else "Import error during test collection"
                return [], error_msg
            
            if 'error' in output.lower() and 'tests collected' not in output.lower():
                error_match = re.search(r'(Error|ERROR).*$', output, re.MULTILINE)
                error_msg = error_match.group(0) if error_match else "Error during test collection"
                return [], error_msg
            
            # No tests found
            if 'no tests collected' in output.lower():
                return [], "No tests found in directory"

            
            return [], None
        except Exception as e:
            return [], str(e)


    
    def _run_pytest(self, component_name: str, test_path: str, pythonpath: str = None, callback=None) -> int:
        """Run pytest with real-time output streaming and coverage"""
        # Build environment with PYTHONPATH if needed
        env = os.environ.copy()
        if pythonpath:
            existing = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = f"{pythonpath}:{existing}" if existing else pythonpath
        
        # Get service-specific pytest if available
        pytest_cmd, python_exe = self._get_pytest_executable(test_path)
        
        # Build pytest command - add -v for test result parsing (required)
        # Add -ra to show short test summary for all outcomes (especially skip reasons)
        # Let pytest.ini control other settings like --tb and warnings
        if " -m pytest" in pytest_cmd:
            cmd = [python_exe, "-m", "pytest", "-v", "-ra", "--continue-on-collection-errors"]
        else:
            cmd = [pytest_cmd, "-v", "-ra", "--continue-on-collection-errors"]
        
        # Add coverage for the service if we have a pythonpath or service dir
        # Coverage percentage is parsed from terminal output and stored in memory (MetricsCollector)
        # Coverage data files use unique IDs to prevent race conditions in parallel runs
        import tempfile
        import uuid
        coverage_temp_dir = getattr(self, 'coverage_temp_dir', tempfile.gettempdir())
        
        # Get coverage path for this component
        cov_path_str = self._get_coverage_path_for_component(component_name, test_path)
        if cov_path_str:
            cov_path = Path(cov_path_str)
            if cov_path.exists():
                # Unique coverage file per subprocess run
                env['COVERAGE_FILE'] = str(Path(coverage_temp_dir) / f".coverage.{uuid.uuid4().hex[:8]}")
                cmd.extend(["--cov", str(cov_path), "--cov-report", "term-missing:skip-covered"])
        
        cmd.append(test_path)
        
        # Log command execution for debugging
        logger.debug(f"[{component_name}] Running pytest: {' '.join(cmd)}")
        logger.debug(f"[{component_name}] PYTHONPATH: {env.get('PYTHONPATH', 'not set')}")
        logger.debug(f"[{component_name}] Coverage path: {cov_path_str if cov_path_str else 'none'}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=None  # Run from project root
            )
            
            # Stream output and parse in real-time
            coverage_pct = None
            warnings_count = None
            self._error_buffer = []  # Initialize error capture buffer
            output_lines = []  # Store all output for post-processing
            tests_parsed = 0  # Track how many tests were successfully parsed
            
            logger.debug(f"[{component_name}] Starting output parsing...")
            
            for line in process.stdout:
                output_lines.append(line)
                # Parse each line and track if we found a test result
                before_count = len(self.collector.get_component(component_name).tests)
                self._parse_line(component_name, line, callback=callback)
                after_count = len(self.collector.get_component(component_name).tests)
                if after_count > before_count:
                    tests_parsed += 1
                
                stripped = line.strip()
                # Parse coverage from output: "TOTAL ... 85%" or "TOTAL                                     1955   1955     0%"
                if stripped.startswith("TOTAL") and "%" in stripped:
                    import re
                    # Match percentage at the end of the line (e.g., "0%", "85%", "100%")
                    # Handle both formats: "TOTAL ... 85%" and "TOTAL                                     1955   1955     0%"
                    match = re.search(r'(\d+(?:\.\d+)?)%', stripped)
                    if match:
                        coverage_pct = float(match.group(1))
                        logger.debug(f"[{component_name}] Parsed coverage: {coverage_pct}%")
                # Parse warnings from summary line: "X passed, 3 warnings in 0.05s"
                if "warning" in stripped.lower():
                    import re
                    match = re.search(r'(\d+)\s+warning', stripped)
                    if match:
                        warnings_count = int(match.group(1))
                        logger.debug(f"[{component_name}] Parsed warnings from summary: {warnings_count}")
            
            # If coverage wasn't found in streaming, try parsing from full output
            if coverage_pct is None:
                full_output = ''.join(output_lines)
                import re
                # Look for TOTAL line in the full output - handle multiple formats:
                # "TOTAL                                     1955   1955     0%"
                # "TOTAL ... 85%"
                # Match any TOTAL line with percentage
                patterns = [
                    r'TOTAL\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%',  # Standard format with numbers
                    r'TOTAL\s+.*?(\d+(?:\.\d+)?)%',  # Any format with percentage
                ]
                for pattern in patterns:
                    total_match = re.search(pattern, full_output, re.MULTILINE)
                    if total_match:
                        coverage_pct = float(total_match.group(1))
                        break
                
            process.wait()
            exit_code = process.returncode
            
            logger.debug(f"[{component_name}] Pytest exited with code: {exit_code}")
            logger.debug(f"[{component_name}] Tests parsed: {tests_parsed}")
            logger.debug(f"[{component_name}] Total output lines: {len(output_lines)}")
            
            # DIAGNOSTIC: Check if tests were parsed
            comp = self.collector.get_component(component_name)
            if comp.discovered_total > 0 and tests_parsed == 0:
                logger.warning(f"[{component_name}] No tests were parsed despite {comp.discovered_total} discovered!")
                logger.warning(f"[{component_name}] Exit code: {exit_code}")
                logger.warning(f"[{component_name}] Command: {' '.join(cmd)}")
                # Log first and last 10 lines of output for debugging
                if len(output_lines) > 0:
                    logger.warning(f"[{component_name}] First 5 output lines: {output_lines[:5]}")
                    logger.warning(f"[{component_name}] Last 5 output lines: {output_lines[-5:]}")
                else:
                    logger.error(f"[{component_name}] NO OUTPUT CAPTURED FROM PYTEST!")
            
            # DIAGNOSTIC EXTRACTION: Parse full output for detailed diagnostics
            # Extract warnings, skip reasons, failures, and errors
            full_output = ''.join(output_lines)
            self._extract_diagnostics(component_name, full_output)
            
            # Store coverage if collected
            if coverage_pct is not None:
                self.collector.set_coverage(component_name, coverage_pct)
                logger.debug(f"[{component_name}] Set coverage to {coverage_pct}%")
            
            # Store warnings - prefer detailed extraction over summary count
            # Count warnings from detailed extraction if summary didn't have any
            if warnings_count is None or warnings_count == 0:
                detailed_warnings = len(comp.warning_details)
                if detailed_warnings > 0:
                    warnings_count = detailed_warnings
                    logger.debug(f"[{component_name}] Using detailed warning count: {warnings_count}")
            
            if warnings_count is not None and warnings_count > 0:
                self.collector.set_warnings(component_name, warnings_count)
                logger.debug(f"[{component_name}] Set warnings to {warnings_count}")
            
            # Preserve coverage file to permanent storage if configured
            if self.coverage_storage_dir and self.run_id and env.get('COVERAGE_FILE'):
                coverage_file = Path(env['COVERAGE_FILE'])
                if coverage_file.exists():
                    dest_dir = Path(self.coverage_storage_dir) / self.run_id
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = dest_dir / f"{component_name}.coverage"
                    try:
                        shutil.copy2(coverage_file, dest_file)
                        self._coverage_files[component_name] = str(dest_file)
                        logger.debug(f"Preserved coverage file for {component_name}: {dest_file}")
                    except Exception as e:
                        logger.warning(f"Failed to preserve coverage file: {e}")
            
            return exit_code
        except Exception as e:
            logger.error(f"[{component_name}] Exception running pytest: {e}")
            logger.exception(e)  # Log full traceback
            print(f"Error running pytest for {component_name}: {e}")
            return 1

    def _extract_diagnostics(self, component_name: str, output: str):
        """Extract detailed diagnostics from pytest output"""
        comp = self.collector.get_component(component_name)
        
        # Extract warning details from pytest warnings summary
        # Format with or without leading spaces: "/path/file.py:123: WarningType: message"
        warning_pattern = r'\s*([/\w.]+\.py):(\d+):\s+(\w+Warning):\s+(.+)'
        for match in re.finditer(warning_pattern, output):
            location, line_no, category, message = match.groups()
            comp.warning_details.append({
                "category": category,
                "message": message.strip()[:200],
                "location": f"{location}:{line_no}"
            })
        
        # Extract skip reasons - NEW APPROACH: Parse test files directly
        # Extract test names from SKIPPED lines first
        skip_pattern = r'([\w/_.]+\.py)::([\w:]+)\s+SKIPPED'
        skipped_test_names = set()
        
        for match in re.finditer(skip_pattern, output):
            file_path, test_id = match.groups()
            test_name = f"{file_path}::{test_id}"
            skipped_test_names.add(test_name)
        
        # Parse test files to extract skip reasons from @pytest.mark.skip decorators
        for test_name in skipped_test_names:
            file_path = test_name.split('::', 1)[0]
            test_method = test_name.split('::')[-1]
            skip_reason = self._extract_skip_reason_from_file(file_path, test_method)
            
            # Determine marker type
            marker = "skip"
            if skip_reason:
                if "skipif" in skip_reason.lower():
                    marker = "skipif"
                elif "xfail" in skip_reason.lower():
                    marker = "xfail"
            
            comp.skipped_tests.append({
                "test_name": test_name,
                "reason": skip_reason or "No reason provided",
                "marker": marker
            })

        
        # Extract failure details - capture test name and assertion error
        # Format: "__ test_name __" followed by "AssertionError: message"  
        failure_section_pattern = r'_{2,}\s+([\w:./]+)\s+_{2,}.*?(?=(_{2,}\s+\w+\s+_{2,}|$))'
        for match in re.finditer(failure_section_pattern, output, re.DOTALL):
            section = match.group(0)
            test_name = match.group(1)
            
            # Extract assertion or error from section
            reason_match = re.search(r'(AssertionError|ValueError|TypeError|.*Error):\s*(.+)', section, re.MULTILINE)
            if reason_match:
                error_type, reason = reason_match.groups()
                # Extract location
                loc_match = re.search(r'([\w/_.]+\.py):(\d+)', section)
                location = f"{loc_match.group(1)}:{loc_match.group(2)}" if loc_match else "unknown"
                
                comp.failures.append({
                    "test_name": test_name,
                    "reason": f"{error_type}: {reason.strip()[:200]}",
                    "location": location
                })
        
        # Extract error details (collection errors, import errors)
        error_pattern = r'ERROR\s+([\w/_.]+\.py)::([\w:]+).*?(?:ImportError|ModuleNotFoundError|.*Error):\s*(.+)'
        for match in re.finditer(error_pattern, output, re.DOTALL):
            file_path, test_id, error_msg = match.groups()
            test_name = f"{file_path}::{test_id}"
            
            # Extract error type
            error_type_match = re.search(r'(ImportError|ModuleNotFoundError|\w+Error)', error_msg)
            error_type = error_type_match.group(1) if error_type_match else "Error"
            
            comp.test_errors.append({
                "test_name": test_name,
                "error_type": error_type,
                "message": error_msg.strip()[:200],
                "location": file_path
            })

    def _parse_line(self, component_name: str, line: str, callback=None):
        """Parse pytest verbose output lines for metrics and error messages"""
        # Pytest verbose format variations:
        # "tests/test_file.py::test_name PASSED        [ 10%]"
        # "tests/test_file.py::TestClass::test_name PASSED [ 10%]"
        # Match: path.py::optional_class::test_method STATUS [percent]
        test_pattern = r"([\w/_.]+\.py)::([\w:]+)\s+(PASSED|FAILED|ERROR|SKIPPED)\s+\["
        match = re.search(test_pattern, line)
        if match:
            file_path, test_id, status = match.groups()
            test_name = f"{file_path}::{test_id}"
            
            # Call callback with test name if provided
            if callback:
                callback(test_name)
            
            # Store the test result
            self.collector.record_test(component_name, TestResult(
                name=test_name,
                status=status.lower(),
                duration=0.05,
                error_message=None  # Will be populated by _capture_errors
            ))
        
        # Capture failure/error details for later matching
        # Store lines that look like error output for the MCP to access
        if hasattr(self, '_error_buffer'):
            # Check for common error patterns
            if 'FAILED' in line or 'ERROR' in line or 'AssertionError' in line:
                self._error_buffer.append(line.strip())
            elif line.strip().startswith('E '):  # pytest error lines start with 'E '
                self._error_buffer.append(line.strip())
            elif 'Traceback' in line or 'File "' in line:
                self._error_buffer.append(line.strip())

    def _extract_skip_reason_from_file(self, file_path: str, test_method: str) -> Optional[str]:
        """Extract skip reason from @pytest.mark.skip decorator in test file.
        
        Args:
            file_path: Path to the test file
            test_method: Name of the test method (including Test Class prefix if present)
        
        Returns:
            Skip reason string or None if not found
        """
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read(), filename=file_path)
            
            # Handle TestClass::test_method format
            parts = test_method.split('::')
            if len(parts) == 2:
                class_name, method_name = parts
            else:
                class_name = None
                method_name = test_method
            
            # Search for the test method in the AST
            for node in ast.walk(tree):
                # If we need a class, find it first
                if class_name and isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                            return self._extract_decorator_reason(item)
                
                # Function-level test (no class)
                elif not class_name and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
                    return self._extract_decorator_reason(node)
            
            return None
        except Exception as e:
            logger.debug(f"Failed to parse {file_path} for skip reason: {e}")
            return None

    def _extract_decorator_reason(self, func_node) -> Optional[str]:
        """Extract reason from @pytest.mark.skip decorator."""
        for decorator in func_node.decorator_list:
            # Handle @pytest.mark.skip(reason="...")
            if (isinstance(decorator, ast.Call) and
                isinstance(decorator.func, ast.Attribute) and
                decorator.func.attr == 'skip'):
                
                # Look for reason in keyword arguments
                for keyword in decorator.keywords:
                    if keyword.arg == 'reason' and isinstance(keyword.value, ast.Constant):
                        return keyword.value.value
        
        return None

    def _simulate_run(self, phase_id: int, component_name: str):
        """Simulated run for demo purposes"""
        tests = [
            ("test_init", "passed"),
            ("test_config", "passed"),
            ("test_logic", "passed"),
            ("test_edge_case", "passed"),
            ("test_failure", "error" if "engine" in component_name else "passed")
        ]
        
        for name, status in tests:
            time.sleep(0.05)
            self.collector.record_test(component_name, TestResult(
                name=f"{component_name}::{name}",
                status=status,
                duration=0.05
            ))
        return 0
