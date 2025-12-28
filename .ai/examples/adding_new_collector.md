# Example: Adding New Test Collector

This example shows how to add a new collector type while following contracts-first development.

## Step 1: Define the Contract

```python
# src/ptsd_agent/core/interfaces.py
from typing import Protocol, runtime_checkable, List
from pathlib import Path

@runtime_checkable
class TestCollector(Protocol):
    """Protocol for test collection strategies."""
    
    def collect_from_file(self, file_path: Path) -> List[str]:
        """Collect test names from a single file.
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of fully qualified test names
        """
        ...
```

## Step 2: Implement the Contract

```python
# src/ptsd_agent/discovery/regex_collector.py  
from pathlib import Path
from typing import List
import re

from ptsd_agent.core.interfaces import TestCollector

class RegexCollector:
    """Collect tests using regex patterns."""
    
    def __init__(self, pattern: str = r"def (test_\w+)"):
        self.pattern = re.compile(pattern)
    
    def collect_from_file(self, file_path: Path) -> List[str]:
        """Collect test names via regex matching."""
        content = file_path.read_text()
        matches = self.pattern.findall(content)
        
        # Return fully qualified names
        return [f"{file_path.name}::{name}" for name in matches]
```

## Step 3: Verify Type Compliance

```python
# Verify it implements the protocol
from ptsd_agent.core.interfaces import TestCollector
from ptsd_agent.discovery.regex_collector import RegexCollector

collector = RegexCollector()
assert isinstance(collector, TestCollector)  # ✅ Type check passes
```

## Step 4: Write Tests

```python
# tests/unit/discovery/test_regex_collector.py
import pytest
from pathlib import Path
from ptsd_agent.discovery.regex_collector import RegexCollector

class TestRegexCollector:
    @pytest.fixture
    def sample_file(self, tmp_path):
        file = tmp_path / "test_example.py"
        file.write_text("""
def test_one():
    assert True

def test_two():
    assert True

def helper():
    pass
""")
        return file
    
    def test_collects_test_functions(self, sample_file):
        collector = RegexCollector()
        tests = collector.collect_from_file(sample_file)
        
        assert len(tests) == 2
        assert "test_example.py::test_one" in tests
        assert "test_example.py::test_two" in tests
        assert "test_example.py::helper" not in tests
```

## Step 5: Integrate

```python
# src/ptsd_agent/discovery/pytest.py
from ptsd_agent.discovery.regex_collector import RegexCollector

class PytestDiscoverer:
    def __init__(self):
        # Use regex collector for fast estimation
        self.fast_collector = RegexCollector(pattern=r"def (test_\w+)")
    
    def estimate_test_count(self, file: TestFile) -> int:
        tests = self.fast_collector.collect_from_file(file.path)
        return len(tests)
```

## Benefits of This Approach

1. **Contract defines behavior** - Clear expectations
2. **Type safety** - Mypy validates compliance
3. **Testability** - Easy to write unit tests
4. **Pluggability** - Swap implementations easily
5. **YOLO-friendly** - AI agents can implement without ambiguity
