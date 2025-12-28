"""Unit tests for pytest discoverer."""

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
    def sample_file(self, tmp_path):
        """Create a sample test file."""
        file = tmp_path / "test_example.py"
        file.write_text("""
def test_one():
    assert True

def test_two():
    assert True

class TestClass:
    def test_three(self):
        assert True
""")
        return file
    
    def test_estimate_test_count(self, discoverer, sample_file):
        """Test fast estimation."""
        test_file = TestFile(path=sample_file, framework="pytest")
        count = discoverer.estimate_test_count(test_file)
        
        assert count == 3  # test_one, test_two, test_three
    
    @pytest.mark.asyncio
    async def test_discover_files(self, discoverer, tmp_path):
        """Test file discovery."""
        # Create test files
        (tmp_path / "test_foo.py").write_text("def test_foo(): pass")
        (tmp_path / "test_bar.py").write_text("def test_bar(): pass")
        (tmp_path / "not_a_test.py").write_text("def helper(): pass")
        
        files = [f async for f in discoverer.discover_files(
            tmp_path,
            patterns=["test_*.py"]
        )]
        
        assert len(files) == 2
        assert all(f.framework == "pytest" for f in files)
