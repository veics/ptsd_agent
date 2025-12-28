"""Test file discovery module for ptsd_agent.

Scans project directories to find all test files and categorize them.
"""
import os
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class TestFile:
    """Represents a discovered test file"""
    path: Path
    relative_path: str
    service: str = ""
    phase: int = 0
    component: str = ""
    

class TestFinder:
    """Finds test files in a project directory"""
    
    def __init__(self, root_dir: str, phase_config: Dict = None):
        self.root_dir = Path(root_dir)
        self.ignored_dirs = {'.venv', 'venv', 'node_modules', '__pycache__', '.git', 'dist', 'build'}
        # Build test_path -> [components] mapping from config (supports shared paths)
        self.test_path_to_components = {}
        if phase_config:
            for phase_id, phase_data in phase_config.items():
                for comp in phase_data.get('components', []):
                    test_path = comp.get('test_path', '')
                    if test_path:
                        # Normalize path for matching
                        normalized = test_path.rstrip('/')
                        if normalized not in self.test_path_to_components:
                            self.test_path_to_components[normalized] = []
                        self.test_path_to_components[normalized].append(comp.get('name', ''))
        
    def scan_directory(self, start_path: str = None) -> List[TestFile]:
        """Recursively scan directory for test files
        
        Args:
            start_path: Directory to start scanning from (default: root_dir)
            
        Returns:
            List of discovered TestFile objects
        """
        scan_root = Path(start_path) if start_path else self.root_dir
        test_files = []
        
        for root, dirs, files in os.walk(scan_root):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            
            # Find test files
            for file in files:
                if self._is_test_file(file):
                    file_path = Path(root) / file
                    relative = file_path.relative_to(self.root_dir)
                    
                    # Get all matching components (handles shared test_paths)
                    components = self._extract_all_components(file_path)
                    if not components:
                        components = [self._extract_service(file_path)]
                    
                    # Create a TestFile entry for EACH matching component
                    for component in components:
                        test_file = TestFile(
                            path=file_path,
                            relative_path=str(relative),
                            service=self._extract_service(file_path),
                            component=component
                        )
                        test_files.append(test_file)
                    
        return test_files
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if filename is a test file"""
        return (
            filename.startswith('test_') and filename.endswith('.py') or
            filename.endswith('_test.py')
        ) and filename != 'conftest.py'
    
    def _extract_service(self, file_path: Path) -> str:
        """Extract service name from file path
        
        Examples:
            services/acl/tests/test_foo.py -> acl
            services/rag_core/tests/unit/test_bar.py -> rag_core
        """
        parts = file_path.parts
        try:
            if 'services' in parts:
                idx = parts.index('services')
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except (ValueError, IndexError):
            pass
        return ""
    
    def _extract_all_components(self, file_path: Path) -> List[str]:
        """Extract ALL component names that match a file path.
        
        Handles shared test_paths where multiple components use the same directory.
        Returns list of component names, or empty list if no config match.
        """
        components = []
        if self.test_path_to_components:
            try:
                relative_path = file_path.relative_to(self.root_dir)
                # Check each configured test_path to see if this file is under it
                for test_path, comp_list in self.test_path_to_components.items():
                    # Check if the file's parent path starts with the test_path
                    if str(relative_path).startswith(test_path) or str(relative_path.parent).startswith(test_path.rstrip('/')):
                        components.extend(comp_list)  # Add ALL components for this path
            except ValueError:
                pass
        return components
    
    def _extract_component(self, file_path: Path) -> str:
        """Extract component name from file path (returns first match).
        
        First checks config-based test_path mapping, then falls back to service name.
        """
        components = self._extract_all_components(file_path)
        if components:
            return components[0]
        # Fall back to service-based extraction
        return self._extract_service(file_path)
    
    def get_statistics(self, test_files: List[TestFile]) -> Dict:
        """Get statistics about discovered tests
        
        Returns:
            Dictionary with counts by service, totals, etc.
        """
        stats = {
            'total_files': len(test_files),
            'by_service': {},
            'by_directory': {}
        }
        
        for tf in test_files:
            # Count by service
            if tf.service:
                stats['by_service'][tf.service] = stats['by_service'].get(tf.service, 0) + 1
            
            # Count by directory
            dir_name = str(tf.path.parent.relative_to(self.root_dir))
            stats['by_directory'][dir_name] = stats['by_directory'].get(dir_name, 0) + 1
        
        return stats
    
    def scan_services_directory(self) -> List[TestFile]:
        """Convenience method to scan services/ and tests/ directories
        
        Returns:
            All test files found in services/ and tests/
        """
        all_tests = []
        
        # Scan services directory
        services_dir = self.root_dir / 'services'
        if services_dir.exists():
            all_tests.extend(self.scan_directory(str(services_dir)))
        
        # Also scan root tests directory
        tests_dir = self.root_dir / 'tests'
        if tests_dir.exists():
            all_tests.extend(self.scan_directory(str(tests_dir)))
        
        return all_tests
    
    def find_orphaned_tests(self, all_tests: List[TestFile], categorized_tests: Set[str]) -> List[TestFile]:
        """Find tests that haven't been categorized
        
        Args:
            all_tests: All discovered tests
            categorized_tests: Set of relative paths that have been categorized
            
        Returns:
            List of TestFile objects not in categorized set
        """
        orphaned = []
        for test in all_tests:
            if test.relative_path not in categorized_tests:
                orphaned.append(test)
        return orphaned
