# API Contracts

All contracts are defined as Python Protocols in `src/ptsd_agent/core/interfaces.py`.

## Core Principle

**Interfaces before implementation.** Every major component implements a protocol.

## Core Protocols

### 1. TestDiscoverer

Discovers test files and estimates/collects test counts.

```python
@runtime_checkable
class TestDiscoverer(Protocol):
    """Contract for test discovery engines."""
    
    async def discover_files(
        self, 
        root: Path, 
        patterns: List[str],
        exclude: List[str] | None = None
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
        
        Returns:
            Approximate number of tests in file
        """
        ...
    
    async def collect_accurate(self, file: TestFile, venv: Path | None = None) -> List[TestUnit]:
        """Accurate collection via pytest --collect-only.
        
        Args:
            file: Test file to collect from
            venv: Optional virtualenv path for project-specific dependencies
            
        Returns:
            List of TestUnit objects with exact test names
        """
        ...
```

### 2. TestExecutor

Executes tests and parses results.

```python
@runtime_checkable  
class TestExecutor(Protocol):
    """Contract for test execution engines."""
    
    async def execute(
        self,
        tests: List[TestUnit],
        config: ExecutionConfig,
        progress_callback: Callable[[ProgressUpdate], None] | None = None
    ) -> TestResult:
        """Execute tests and return results.
        
        Args:
            tests: Tests to execute
            config: Execution configuration (venv, args, parallel workers)
            progress_callback: Called for each test completion for accurate progress
            
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
```

### 3. MetricsCollector

Collects and aggregates test metrics.

```python
@runtime_checkable
class MetricsCollector(Protocol):
    """Contract for metrics collection."""
    
    def record_test_result(self, component: str, result: TestResult) -> None:
        """Record results for a component."""
        ...
    
    def get_component_metrics(self, component: str) -> ComponentMetrics:
        """Get aggregated metrics for component."""
        ...
    
    def get_phase_metrics(self, phase_id: int) -> PhaseMetrics:
        """Get aggregated metrics for phase."""
        ...
    
    def get_summary(self) -> TestRunSummary:
        """Get overall run summary."""
        ...
```

### 4. UIRenderer

Renders terminal UI sections.

```python
@runtime_checkable
class UIRenderer(Protocol):
    """Contract for UI rendering."""
    
    def render_discovery(self, progress: DiscoveryProgress) -> str:
        """Render discovery phase UI."""
        ...
    
    def render_execution(self, progress: ExecutionProgress) -> str:
        """Render test execution UI with progress bars."""
        ...
    
    def render_diagnostics(self, diagnostics: Diagnostics, tree_view: bool = True) -> str:
        """Render diagnostics section."""
        ...
    
    def render_summary(self, summary: TestRunSummary) -> str:
        """Render final summary."""
        ...
```

### 5. ProgressUpdate

For accurate progress tracking during execution.

```python
@dataclass
class ProgressUpdate:
    """Progress update from test executor.
    
    Sent after each test completes to enable accurate progress bars.
    """
    test_name: str
    status: TestStatus  # passed | failed | error | skipped
    completed_count: int  # Number of tests completed so far
    total_count: int  # Total tests to execute
    duration: float  # Test duration in seconds
```

## Data Models

### TestFile
```python
@dataclass
class TestFile:
    path: Path
    framework: str  # "pytest", "jest", etc.
    estimated_tests: int | None = None  # From fast scan
    actual_tests: int | None = None  # From precise collection
```

### TestUnit
```python
@dataclass
class TestUnit:
    file: TestFile
    name: str  # Full test name (e.g., "tests/test_foo.py::TestClass::test_method")
    line_number: int | None = None
```

### Diagnostics
```python
@dataclass
class Diagnostics:
    warnings: List[Warning]
    failures: List[Failure]
    errors: List[Error]
    skipped: List[SkippedTest]
    
    def group_by_file(self) -> Dict[Path, List[Issue]]:
        """Group diagnostics by source file for tree view."""
        ...
```

## Adding New Framework Support

### Step 1: Implement TestDiscoverer

```python
# src/ptsd_agent/discovery/jest.py
from ptsd_agent.core.interfaces import TestDiscoverer

class JestDiscoverer:
    """Jest test discoverer."""
    
    async def discover_files(self, root, patterns, exclude=None):
        # Find *.test.js, *.spec.js files
        ...
    
    def estimate_test_count(self, file):
        # Count describe/it blocks via regex
        ...
    
    async def collect_accurate(self, file, venv=None):
        # Run jest --listTests
        ...
```

### Step 2: Implement TestExecutor

```python
# src/ptsd_agent/execution/jest.py
from ptsd_agent.core.interfaces import TestExecutor

class JestExecutor:
    """Jest test executor."""
    
    async def execute(self, tests, config, progress_callback=None):
        # Run jest with --json output
        # Parse results
        # Call progress_callback after each test for accurate progress
        ...
    
    def parse_diagnostics(self, output):
        # Parse Jest JSON output
        ...
```

### Step 3: Register

```yaml
# .ptsd.yaml
frameworks:
  - name: jest
    discoverer: ptsd_agent.discovery.jest.JestDiscoverer
    executor: ptsd_agent.execution.jest.JestExecutor
    file_patterns: ["*.test.js", "*.spec.js"]
```

## Contract Compliance

All implementations must:
1. **Match the signature** - Same parameters and return types
2. **Pass type checking** - `mypy --strict` must pass
3. **Have tests** - Unit tests verifying contract compliance
4. **Handle errors** - Graceful degradation with clear error messages

## Testing Contracts

```python
# tests/unit/test_contracts.py
import pytest
from ptsd_agent.core.interfaces import TestDiscoverer
from ptsd_agent.discovery.pytest import PytestDiscoverer

def test_pytest_discoverer_implements_contract():
    """Verify PytestDiscoverer implements TestDiscoverer protocol."""
    assert isinstance(PytestDiscoverer(), TestDiscoverer)

def test_discover_files_signature():
    """Verify discover_files has correct signature."""
    discoverer = PytestDiscoverer()
    # Test actual method call
    files = await discoverer.discover_files(Path("."), ["test_*.py"])
    assert all(isinstance(f, TestFile) for f in files)
```
