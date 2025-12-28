"""Core type definitions for PTSD Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


class TestStatus(str, Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class DiagnosticType(str, Enum):
    """Type of diagnostic message."""
    WARNING = "warning"
    FAILURE = "failure"
    ERROR = "error"
    SKIP = "skip"


class DiagnosticCategory(str, Enum):
    """Category of diagnostic for classification."""
    IMPORT_ERROR = "import_error"
    ASSERTION_FAILURE = "assertion_failure"
    TIMEOUT = "timeout"
    FIXTURE_ERROR = "fixture_error"
    COVERAGE_WARNING = "coverage_warning"
    DEPRECATION_WARNING = "deprecation_warning"
    RUNTIME_WARNING = "runtime_warning"
    ENVIRONMENT_DEPENDENCY = "environment_dependency"
    API_NOT_IMPLEMENTED = "api_not_implemented"
    UNKNOWN = "unknown"


@dataclass
class TestFile:
    """Represents a discovered test file."""
    path: Path
    framework: str  # "pytest", "jest", etc.
    estimated_tests: Optional[int] = None  # From fast scan
    actual_tests: Optional[int] = None  # From accurate collection


@dataclass
class TestUnit:
    """Represents an individual test."""
    file: TestFile
    name: str  # Full test name (e.g., "tests/test_foo.py::TestClass::test_method")
    line_number: Optional[int] = None


@dataclass
class ProgressUpdate:
    """Progress update from test executor.
    
    Sent after each test completes to enable accurate progress bars.
    """
    test_name: str
    status: TestStatus
    completed_count: int  # Number of tests completed so far
    total_count: int  # Total tests to execute
    duration: float  # Test duration in seconds
    

@dataclass
class Warning:
    """Diagnostic warning."""
    category: str  # e.g., "DeprecationWarning"
    message: str
    location: str  # "file:line"
    source_component: Optional[str] = None  # Component that produced it
    source_test: Optional[str] = None  # Test that produced it
    is_known: bool = False


@dataclass
class Failure:
    """Test failure."""
    test_name: str
    message: str
    traceback: str
    location: str
    category: DiagnosticCategory = DiagnosticCategory.ASSERTION_FAILURE
    is_known: bool = False


@dataclass
class Error:
    """Test error."""
    test_name: str
    message: str
    traceback: str
    location: str
    category: DiagnosticCategory = DiagnosticCategory.UNKNOWN
    is_known: bool = False


@dataclass
class SkippedTest:
    """Skipped test."""
    test_name: str
    reason: str
    location: str
    blocking_component: Optional[str] = None  # Component it's waiting for
    is_known: bool = False


@dataclass
class Diagnostics:
    """Collection of diagnostics from a test run."""
    warnings: List[Warning] = field(default_factory=list)
    failures: List[Failure] = field(default_factory=list)
    errors: List[Error] = field(default_factory=list)
    skipped: List[SkippedTest] = field(default_factory=list)
    
    def group_by_file(self) -> Dict[Path, List[Any]]:
        """Group all diagnostics by source file for tree view."""
        grouped: Dict[Path, List[Any]] = {}
        
        # Group all diagnostic types
        for items in [self.warnings, self.failures, self.errors, self.skipped]:
            for item in items:
                # Extract file path from location or test name
                file_path = self._extract_file_path(item)
                if file_path:
                    if file_path not in grouped:
                        grouped[file_path] = []
                    grouped[file_path].append(item)
        
        return grouped
    
    def _extract_file_path(self, item: Any) -> Optional[Path]:
        """Extract file path from diagnostic item."""
        if hasattr(item, 'location'):
            location_parts = item.location.split(':')
            if location_parts:
                return Path(location_parts[0])
        if hasattr(item, 'test_name'):
            test_parts = item.test_name.split('::')
            if test_parts:
                return Path(test_parts[0])
        return None


@dataclass
class TestResult:
    """Results from executing tests."""
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float  # seconds
    diagnostics: Diagnostics
    output: str  # Raw output


@dataclass
class ComponentMetrics:
    """Metrics for a single component."""
    name: str
    phase: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    warnings: int = 0
    coverage: Optional[float] = None  # 0.0-100.0
    pass_rate: Optional[float] = None  # 0.0-100.0
    duration: float = 0.0
    diagnostics: Diagnostics = field(default_factory=Diagnostics)


@dataclass
class PhaseMetrics:
    """Aggregated metrics for a phase."""
    id: int
    name: str
    components: List[ComponentMetrics] = field(default_factory=list)
    
    @property
    def total_tests(self) -> int:
        return sum(c.total_tests for c in self.components)
    
    @property
    def passed(self) -> int:
        return sum(c.passed for c in self.components)
    
    @property
    def failed(self) -> int:
        return sum(c.failed for c in self.components)
    
    @property
    def errors(self) -> int:
        return sum(c.errors for c in self.components)
    
    @property
    def skipped(self) -> int:
        return sum(c.skipped for c in self.components)
    
    @property
    def warnings(self) -> int:
        return sum(c.warnings for c in self.components)
    
    @property
    def coverage(self) -> Optional[float]:
        coverages = [c.coverage for c in self.components if c.coverage is not None]
        return sum(coverages) / len(coverages) if coverages else None
    
    @property
    def pass_rate(self) -> Optional[float]:
        if self.total_tests == 0:
            return None
        return (self.passed / self.total_tests) * 100.0


@dataclass
class TestRunSummary:
    """Overall test run summary."""
    run_id: str
    timestamp: datetime
    project_root: Path
    phases: List[PhaseMetrics] = field(default_factory=list)
    duration: float = 0.0
    
    @property
    def total_tests(self) -> int:
        return sum(p.total_tests for p in self.phases)
    
    @property
    def passed(self) -> int:
        return sum(p.passed for p in self.phases)
    
    @property
    def failed(self) -> int:
        return sum(p.failed for p in self.phases)
    
    @property
    def errors(self) -> int:
        return sum(p.errors for p in self.phases)
    
    @property
    def skipped(self) -> int:
        return sum(p.skipped for p in self.phases)
    
    @property
    def warnings(self) -> int:
        return sum(p.warnings for p in self.phases)
    
    @property
    def coverage(self) -> Optional[float]:
        coverages = [p.coverage for p in self.phases if p.coverage is not None]
        return sum(coverages) / len(coverages) if coverages else None
    
    @property
    def pass_rate(self) -> Optional[float]:
        if self.total_tests == 0:
            return None
        return (self.passed / self.total_tests) * 100.0


@dataclass
class ExecutionConfig:
    """Configuration for test execution."""
    project_root: Path
    parallel_workers: int = 1
    framework: str = "pytest"
    venv_path: Optional[Path] = None
    custom_command: Optional[str] = None
    pytest_args: List[str] = field(default_factory=list)
    use_xdist: bool = False
    xdist_workers: int = 0
