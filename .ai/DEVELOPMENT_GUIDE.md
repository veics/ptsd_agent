# Development Guide

## Setup

```bash
# Clone repository
git clone https://github.com/yourusername/ptsd_agent.git
cd ptsd_agent

# Create virtualenv with Python 3.14
python3.14 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
ptsd_agent --version
mypy --version
pytest --version
```

## Code Organization Principles

### 1. Zero Duplication Rule

**❌ Bad - Duplicated Logic**:
```python
# In discovery/pytest.py
def parse_test_name(output: str) -> str:
    match = re.search(r'test_\w+', output)
    return match.group(0) if match else ""

# In execution/pytest.py  
def parse_test_name(output: str) -> str:
    match = re.search(r'test_\w+', output)
    return match.group(0) if match else ""
```

**✅ Good - Shared Utility**:
```python
# In core/utils.py
def parse_pytest_test_name(output: str) -> str:
    """Extract test name from pytest output."""
    match = re.search(r'test_\w+', output)
    return match.group(0) if match else ""

# In discovery/pytest.py and execution/pytest.py
from ptsd_agent.core.utils import parse_pytest_test_name
```

### 2. Contracts First

**Always define the interface before implementing:**

```python
# Step 1: Define protocol in core/interfaces.py
@runtime_checkable
class MyComponent(Protocol):
    def do_something(self, param: str) -> int:
        ...

# Step 2: Implement in specific module
# my_module/impl.py
from ptsd_agent.core.interfaces import MyComponent

class MyImplementation:
    def do_something(self, param: str) -> int:
        return len(param)

# Step 3: Verify type compliance
assert isinstance(MyImplementation(), MyComponent)
```

### 3. Type Safety

**All code must pass mypy strict mode:**

```python
# Good - Full type annotations
def process_results(
    results: List[TestResult],
    filter_fn: Callable[[TestResult], bool]
) -> Dict[str, TestMetrics]:
    filtered = [r for r in results if filter_fn(r)]
    return aggregate_metrics(filtered)

# Bad - No types
def process_results(results, filter_fn):
    filtered = [r for r in results if filter_fn(r)]
    return aggregate_metrics(filtered)
```

## Common Development Tasks

### Adding a New UI Section

**1. Define Contract** (`core/interfaces.py`):
```python
@runtime_checkable
class UISection(Protocol):
    """Protocol for UI sections."""
    
    def render(self, data: Any, width: int) -> str:
        """Render section to string."""
        ...
    
    def should_display(self, data: Any) -> bool:
        """Check if section has data to display."""
        ...
```

**2. Implement** (`ui/sections/my_section.py`):
```python
from ptsd_agent.core.interfaces import UISection
from ptsd_agent.ui.tree import TreeRenderer

class TestCoverageSection:
    """Display test coverage by component."""
    
    def __init__(self):
        self.tree_renderer = TreeRenderer()
    
    def render(self, data: TestRunSummary, width: int) -> str:
        if not self.should_display(data):
            return ""
        
        lines = ["Test Coverage"]
        for component in data.components:
            lines.append(f"  ├─ {component.name}: {component.coverage}%")
        
        return "\n".join(lines)
    
    def should_display(self, data: TestRunSummary) -> bool:
        return any(c.coverage is not None for c in data.components)
```

**3. Register** (`ui/renderer.py`):
```python
from ptsd_agent.ui.sections.my_section import TestCoverageSection

class UIRenderer:
    def __init__(self):
        self.sections = [
            DiscoverySection(),
            ExecutionSection(),
            TestCoverageSection(),  # Add here
            DiagnosticsSection(),
        ]
```

**4. Test** (`tests/unit/ui/test_coverage_section.py`):
```python
import pytest
from ptsd_agent.ui.sections.my_section import TestCoverageSection
from ptsd_agent.core.types import TestRunSummary, ComponentMetrics

def test_coverage_section_renders():
    section = TestCoverageSection()
    summary = TestRunSummary(components=[
        ComponentMetrics(name="core", coverage=95.5),
        ComponentMetrics(name="api", coverage=87.2),
    ])
    
    output = section.render(summary, width=80)
    
    assert "Test Coverage" in output
    assert "core: 95.5%" in output
    assert "api: 87.2%" in output

def test_coverage_section_hidden_when_no_data():
    section = TestCoverageSection()
    summary = TestRunSummary(components=[
        ComponentMetrics(name="core", coverage=None),
    ])
    
    assert not section.should_display(summary)
```

### Adding Framework Support

**Example: Adding Jest Support**

**1. Implement Discoverer** (`discovery/jest.py`):
```python
from pathlib import Path
from typing import AsyncIterator, List
from ptsd_agent.core.interfaces import TestDiscoverer
from ptsd_agent.core.types import TestFile, TestUnit

class JestDiscoverer:
    """Test discoverer for Jest framework."""
    
    async def discover_files(
        self,
        root: Path,
        patterns: List[str],
        exclude: List[str] | None = None
    ) -> AsyncIterator[TestFile]:
        """Find *.test.js and *.spec.js files."""
        # Implementation
        ...
    
    def estimate_test_count(self, file: TestFile) -> int:
        """Count describe/it blocks via regex."""
        content = file.path.read_text()
        # Count 'it(' and 'test(' occurrences
        count = content.count('it(') + content.count('test(')
        return count
    
    async def collect_accurate(
        self,
        file: TestFile,
        venv: Path | None = None
    ) -> List[TestUnit]:
        """Run jest --listTests for accurate count."""
        # Run jest --listTests --json
        ...
```

**2. Implement Executor** (`execution/jest.py`):
```python
from ptsd_agent.core.interfaces import TestExecutor
from ptsd_agent.core.types import TestResult, Diagnostics

class JestExecutor:
    """Test executor for Jest framework."""
    
    async def execute(
        self,
        tests: List[TestUnit],
        config: ExecutionConfig,
        progress_callback: Callable[[ProgressUpdate], None] | None = None
    ) -> TestResult:
        """Run jest with --json output."""
        # Implementation
        ...
    
    def parse_diagnostics(self, output: str) -> Diagnostics:
        """Parse Jest JSON output for failures/errors."""
        # Implementation
        ...
```

**3. Add Tests** (`tests/unit/discovery/test_jest.py`):
```python
import pytest
from ptsd_agent.discovery.jest import JestDiscoverer

@pytest.mark.asyncio
async def test_jest_discover_files(tmp_path):
    # Create fixture files
    (tmp_path / "foo.test.js").write_text("test('foo', () => {})")
    (tmp_path / "bar.spec.js").write_text("it('bar', () => {})")
    
    discoverer = JestDiscoverer()
    files = [f async for f in discoverer.discover_files(
        tmp_path,
        patterns=["*.test.js", "*.spec.js"]
    )]
    
    assert len(files) == 2
```

## Code Quality Standards

### Pre-commit Checks

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Run tests
pytest
```

### CI Pipeline

All PRs must pass:
- ✅ Black formatting
- ✅ Ruff linting
- ✅ Mypy type checking
- ✅ Pytest (100% pass rate)
- ✅ Coverage (>80%)

## Debugging Tips

### Enable Debug Logging

```python
# In your module
import logging
logger = logging.getLogger(__name__)

# In CLI
ptsd_agent --run-tests --log-level DEBUG
```

### Test Specific Module

```bash
# Test only discovery
pytest tests/unit/discovery/

# Test with verbose output
pytest -vv tests/unit/discovery/test_pytest.py::test_discover_files

# Debug with pdb
pytest --pdb tests/unit/
```

### Profile Performance

```bash
# Profile test execution
pytest --profile tests/

# Profile specific function
python -m cProfile -s cumtime -m ptsd_agent.main --run-tests
```

## Release Process

1. Update `CHANGELOG.md`
2. Bump version in `pyproject.toml`
3. Create git tag: `git tag v1.0.0-beta.2`
4. Push: `git push --tags`
5. CI builds and publishes to PyPI

## Getting Help

- Architecture questions → `.ai/ARCHITECTURE.md`
- Contract definitions → `.ai/CONTRACTS.md`
- Testing patterns → `.ai/TESTING_GUIDE.md`
- Examples → `.ai/examples/`
