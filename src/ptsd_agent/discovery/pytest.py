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
            content = file.path.read_text()
            tree = ast.parse(content)
            
            count = 0
            for node in tree.body:
                # Count test functions
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        count += 1
                # Count test methods in classes
                elif isinstance(node, ast.ClassDef):
                    if node.name.startswith('Test'):
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                                count += 1
            
            return count
        except Exception:
            # Fallback to regex if AST fails
            content = file.path.read_text()
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
