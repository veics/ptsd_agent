"""Pytest test discoverer implementation."""

import ast
import re
from pathlib import Path
from typing import AsyncIterator, List, Optional

from ptsd_agent.core.interfaces import TestDiscoverer
from ptsd_agent.core.types import TestFile, TestUnit


class PytestDiscoverer:
    """Test discoverer for pytest framework."""
    
    async def discover_files(
        self,
        root: Path,
        patterns: List[str],
        exclude: Optional[List[str]] = None
    ) -> AsyncIterator[TestFile]:
        """Discover pytest test files."""
        exclude = exclude or []
        
        for pattern in patterns:
            for file_path in root.rglob(pattern):
                # Check if should exclude
                if any(excl in str(file_path) for excl in exclude):
                    continue
                
                if file_path.is_file() and file_path.suffix == '.py':
                    yield TestFile(
                        path=file_path,
                        framework="pytest"
                    )
    
    def estimate_test_count(self, file: TestFile) -> int:
        """Fast AST-based estimation."""
        try:
            # Try UTF-8 first, fallback to latin-1 for non-UTF-8 files
            try:
                content = file.path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = file.path.read_text(encoding='latin-1', errors='ignore')
            
            tree = ast.parse(content)
            
            count = 0
            
            # Only examine module-level nodes (not nested via ast.walk)
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    # Module-level test function
                    count += 1
                elif isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                    # Test class - skip if it has __init__ (dataclasses)
                    has_init = any(
                        isinstance(item, ast.FunctionDef) and item.name == '__init__'
                        for item in node.body
                    )
                    if not has_init:
                        # Count test methods in actual test classes
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                                count += 1
            
            return count
        except Exception:
            # Fallback to regex if AST fails
            try:
                content = file.path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = file.path.read_text(encoding='latin-1', errors='ignore')
            return len(re.findall(r'^\s*def test_\w+', content, re.MULTILINE))
    
    async def collect_accurate(
        self,
        file: TestFile,
        venv: Optional[Path] = None
    ) -> List[TestUnit]:
        """Accurate collection via pytest --collect-only."""
        # TODO: Implement with subprocess calling pytest
        # For now, return empty list
        return []


# Verify it implements the protocol
if __name__ == "__main__":
    from ptsd_agent.core.interfaces import TestDiscoverer
    discoverer = PytestDiscoverer()
    assert isinstance(discoverer, TestDiscoverer)
    print("✓ PytestDiscoverer implements TestDiscoverer protocol")
