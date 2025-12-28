"""Protocol definitions for PTSD Agent.

All major components implement these protocols for type safety and pluggability.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable, List, AsyncIterator, Callable, Optional

from ptsd_agent.core.types import (
    TestFile,
    TestUnit,
    TestResult,
    Diagnostics,
    ExecutionConfig,
    ProgressUpdate,
    ComponentMetrics,
    PhaseMetrics,
    TestRunSummary,
)


@runtime_checkable
class TestDiscoverer(Protocol):
    """Protocol for test discovery engines."""
    
    async def discover_files(
        self, 
        root: Path, 
        patterns: List[str],
        exclude: Optional[List[str]] = None
    ) -> AsyncIterator[TestFile]:
        """Discover test files matching patterns.
        
        Args:
            root: Project root directory
            patterns: Glob patterns (e.g., ["test_*.py", "*_test.py"])
            exclude: Patterns to exclude
            
        Yields:
            TestFile objects with metadata
        """
        ...
    
    def estimate_test_count(self, file: TestFile) -> int:
        """Fast estimation without running pytest.
        
        Uses AST parsing or simple heuristics to count tests.
        Prefixed with ~ in UI to indicate approximation.
        
        Args:
            file: Test file to analyze
            
        Returns:
            Approximate number of tests in file
        """
        ...
    
    async def collect_accurate(
        self,
        file: TestFile,
        venv: Optional[Path] = None
    ) -> List[TestUnit]:
        """Accurate collection via pytest --collect-only.
        
        Args:
            file: Test file to collect from
            venv: Optional virtualenv path for project-specific dependencies
            
        Returns:
            List of TestUnit objects with exact test names
        """
        ...


@runtime_checkable  
class TestExecutor(Protocol):
    """Protocol for test execution engines."""
    
    async def execute(
        self,
        tests: List[TestUnit],
        config: ExecutionConfig,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> TestResult:
        """Execute tests and return results.
        
        Args:
            tests: Tests to execute
            config: Execution configuration (venv, args, parallel workers)
            progress_callback: Called after EACH test completion for accurate progress
            
        Returns:
            TestResult with metrics and diagnostics
        """
        ...
    
    def parse_diagnostics(self, output: str) -> Diagnostics:
        """Parse test output for failures/warnings/skips.
        
        Args:
            output: Raw pytest output
            
        Returns:
            Diagnostics object with categorized issues
        """
        ...


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol for metrics collection."""
    
    def record_test_result(self, component: str, result: TestResult) -> None:
        """Record results for a component.
        
        Args:
            component: Component name
            result: Test execution results
        """
        ...
    
    def get_component_metrics(self, component: str) -> ComponentMetrics:
        """Get aggregated metrics for component.
        
        Args:
            component: Component name
            
        Returns:
            ComponentMetrics with aggregated data
        """
        ...
    
    def get_phase_metrics(self, phase_id: int) -> PhaseMetrics:
        """Get aggregated metrics for phase.
        
        Args:
            phase_id: Phase identifier
            
        Returns:
            PhaseMetrics with all components
        """
        ...
    
    def get_summary(self) -> TestRunSummary:
        """Get overall run summary.
        
        Returns:
            TestRunSummary with all phases and components
        """
        ...


@runtime_checkable
class UIRenderer(Protocol):
    """Protocol for UI rendering."""
    
    def render_discovery(self, file_count: int, estimated_tests: int) -> str:
        """Render discovery phase UI.
        
        Args:
            file_count: Number of test files discovered
            estimated_tests: Estimated test count (~N notation)
            
        Returns:
            Formatted UI string
        """
        ...
    
    def render_execution(
        self,
        component: str,
        current_test: str,
        completed: int,
        total: int,
        progress_pct: float
    ) -> str:
        """Render test execution UI with progress bars.
        
        Args:
            component: Component name
            current_test: Currently executing test
            completed: Tests completed
            total: Total tests
            progress_pct: Progress percentage
            
        Returns:
            Formatted UI string with progress bar
        """
        ...
    
    def render_diagnostics(
        self,
        diagnostics: Diagnostics,
        tree_view: bool = True
    ) -> str:
        """Render diagnostics section.
        
        Args:
            diagnostics: Diagnostic data
            tree_view: Use hierarchical tree view
            
        Returns:
            Formatted diagnostics display
        """
        ...
    
    def render_summary(self, summary: TestRunSummary) -> str:
        """Render final summary.
        
        Args:
            summary: Test run summary
            
        Returns:
            Formatted summary string
        """
        ...


@runtime_checkable
class HistoryStore(Protocol):
    """Protocol for test run history storage."""
    
    def save_run(self, summary: TestRunSummary) -> str:
        """Save test run to history.
        
        Args:
            summary: Test run summary to persist
            
        Returns:
            Run ID
        """
        ...
    
    def get_run(self, run_id: str) -> Optional[TestRunSummary]:
        """Retrieve test run by ID.
        
        Args:
            run_id: Run identifier
            
        Returns:
            TestRunSummary if found, None otherwise
        """
        ...
    
    def list_runs(self, limit: int = 10) -> List[TestRunSummary]:
        """List recent test runs.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of recent TestRunSummary objects
        """
        ...
