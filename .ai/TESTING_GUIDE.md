# Testing Guide

## Overview

PTSD Agent has two testing concerns:
1. **Testing PTSD Agent itself** - Unit and integration tests for the product
2. **Testing target projects** - How PTSD Agent runs tests in projects like RAGE

## Testing PTSD Agent Itself

### Test Structure

```
tests/
├── unit/              # Fast, isolated tests
│   ├── discovery/
│   ├── execution/
│   ├── metrics/
│   ├── diagnostics/
│   ├── ui/
│   └── storage/
├── integration/       # Component integration tests
│   ├── test_full_run.py
│   ├── test_mcp_server.py
│   └── test_parallel_execution.py
└── fixtures/          # Test data
    ├── sample_projects/
    │   ├── pytest_project/
    │   ├── jest_project/
    │   └── mixed_project/
    └── expected_outputs/
```

### Running Tests

```bash
# All tests
pytest

# Just unit tests (fast)
pytest tests/unit/

# With coverage
pytest --cov=src/ptsd_agent --cov-report=html

# Specific test
pytest tests/unit/discovery/test_pytest.py::test_discover_files -v

# Watch mode for TDD
pytest-watch tests/unit/
```

### Writing Unit Tests

**Example: Testing Discovery**

```python
# tests/unit/discovery/test_pytest_discoverer.py
import pytest
from pathlib import Path
from ptsd_agent.discovery.pytest import PytestDiscoverer
from ptsd_agent.core.types import TestFile

class TestPytestDiscoverer:
    """Test suite for pytest discoverer."""
    
    @pytest.fixture
    def discoverer(self):
        return PytestDiscoverer()
    
    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample pytest project."""
        # Create test files
        (tmp_path / "test_foo.py").write_text(
            "def test_one(): pass\n"
            "def test_two(): pass\n"
        )
        (tmp_path / "test_bar.py").write_text(
            "def test_three(): pass\n"
        )
        return tmp_path
    
    @pytest.mark.asyncio
    async def test_discover_files(self, discoverer, sample_project):
        """Test file discovery with patterns."""
        files = [
            f async for f in discoverer.discover_files(
                sample_project,
                patterns=["test_*.py"]
            )
        ]
        
        assert len(files) == 2
        assert all(isinstance(f, TestFile) for f in files)
        assert all(f.framework == "pytest" for f in files)
    
    def test_estimate_test_count(self, discoverer, sample_project):
        """Test fast estimation without running pytest."""
        test_file = TestFile(
            path=sample_project / "test_foo.py",
            framework="pytest"
        )
        
        count = discoverer.estimate_test_count(test_file)
        
        assert count == 2  # Two test functions
    
    @pytest.mark.asyncio
    async def test_collect_accurate(self, discoverer, sample_project):
        """Test accurate collection via pytest."""
        test_file = TestFile(
            path=sample_project / "test_foo.py",
            framework="pytest"
        )
        
        units = await discoverer.collect_accurate(test_file)
        
        assert len(units) == 2
        assert units[0].name.endswith("::test_one")
        assert units[1].name.endswith("::test_two")
```

### Integration Tests

**Example: Full Run Test**

```python
# tests/integration/test_full_run.py
import pytest
from pathlib import Path
from ptsd_agent.cli.main import run_tests
from ptsd_agent.core.types import ExecutionConfig

@pytest.mark.integration
class TestFullRun:
    """Integration tests for full test runs."""
    
    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a complete sample project."""
        # Create project structure
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        (tests_dir / "test_passing.py").write_text(
            "def test_pass(): assert True\n"
        )
        (tests_dir / "test_failing.py").write_text(
            "def test_fail(): assert False\n"
        )
        
        # Create .ptsd.yaml config
        (tmp_path / ".ptsd.yaml").write_text("""
project:
  name: Sample Project
  root: .

discovery:
  patterns:
    - "test_*.py"

execution:
  framework: pytest
  parallel_workers: 1
""")
        return tmp_path
    
    def test_run_with_failures(self, sample_project):
        """Test that PTSD Agent handles failures correctly."""
        config = ExecutionConfig(project_root=sample_project)
        result = run_tests(config)
        
        assert result.total_tests == 2
        assert result.passed == 1
        assert result.failed == 1
        assert len(result.diagnostics.failures) == 1
        assert result.exit_code == 1  # Non-zero for failures
```

## Testing Target Projects (RAGE, etc.)

### VirtualEnv Detection

PTSD Agent auto-detects project-specific virtualenvs:

```python
# In execution/pytest.py
def detect_venv(project_root: Path) -> Path | None:
    """Detect virtualenv in target project."""
    candidates = [
        project_root / "venv",
        project_root / ".venv",
        project_root / "env",
    ]
    for venv_path in candidates:
        python_exe = venv_path / "bin" / "python"
        if python_exe.exists():
            return venv_path
    return None

def get_python_command(project_root: Path) -> str:
    """Get Python executable for target project."""
    venv = detect_venv(project_root)
    if venv:
        return str(venv / "bin" / "python")
    return sys.executable  # Fall back to PTSD Agent's Python
```

### Custom Test Commands

Via `.ptsd.yaml` in target project:

```yaml
execution:
  framework: pytest
  custom_command: "{python} -m pytest {args}"
  venv_detection: true
  
  pytest:
    args:
      - "-v"
      - "--tb=short"
      - "-ra"
```

Supported placeholders:
- `{python}` - Python executable (from venv if detected)
- `{args}` - Additional pytest arguments
- `{tests}` - Test file/directory paths

### Testing Non-Python Projects (Future)

PTSD Agent is designed to support any test framework:

```yaml
# For Jest project
execution:
  framework: jest
  custom_command: "npm test -- {args}"
  requires: ["package.json"]
  venv_detection: false

# For Go project
execution:
  framework: go-test
  custom_command: "go test {args} ./..."
  requires: ["go.mod"]
```

## Test Fixtures

### Creating Fixture Projects

```python
# tests/fixtures/sample_projects/pytest_project/
tests/
├── conftest.py       # Shared fixtures
├── unit/
│   ├── test_core.py
│   └── test_utils.py
└── integration/
    └── test_api.py

# conftest.py
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value"}
```

### Expected Outputs

Store expected outputs for regression testing:

```python
# tests/fixtures/expected_outputs/pytest_summary.txt
=== 5 passed, 1 warning in 0.42s ===

# In test
def test_summary_format():
    expected = Path("tests/fixtures/expected_outputs/pytest_summary.txt").read_text()
    actual = generate_summary(results)
    assert actual.strip() == expected.strip()
```

## Continuous Testing

### Watch Mode

```bash
# Auto-run tests on file changes
ptx tests/unit/

# With pytest-watch
pytest-watch tests/
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/unit/ || exit 1
mypy src/ || exit 1
```

## Performance Testing

### Profiling

```bash
# Profile discovery phase
pytest --profile tests/unit/discovery/

# Profile with cProfile
python -m cProfile -o profile.out -m pytest tests/

# Analyze profile
python -m pstats profile.out
```

### Benchmarking

```python
import pytest

@pytest.mark.benchmark
def test_discovery_performance(benchmark, sample_large_project):
    """Benchmark discovery performance on large project."""
    discoverer = PytestDiscoverer()
    
    result = benchmark(
        lambda: list(discoverer.discover_files(sample_large_project, ["test_*.py"]))
    )
    
    # Assert < 1 second for 1000 files
    assert result.stats.mean < 1.0
```

## Meta-Testing

PTSD Agent can test itself:

```bash
# Run PTSD Agent on itself
cd /Users/vx/github/ptsd_agent
ptsd_agent --run-tests --phase 1

# Expected output:
# ✓ Discovery: ~150 tests
# ✓ Component: ptsd_agent | 150 passed | 0 failed
# ✓ Coverage: 95%
```

## Coverage Goals

- **Core modules**: 100% coverage
- **Discovery/Execution**: 95%+ coverage
- **UI/CLI**: 80%+ coverage
- **Overall**: 90%+ coverage

```bash
# Generate HTML coverage report
pytest --cov=src/ptsd_agent --cov-report=html

# Open report
open htmlcov/index.html
```
