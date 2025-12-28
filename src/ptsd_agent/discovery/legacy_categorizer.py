"""Test categorization module for ptsd_agent.

Assigns discovered test files to project phases and components.
"""
from typing import List, Dict, Set
from pathlib import Path
from .test_finder import TestFile


class PhaseCategorizer:
    """Categorizes test files into project phases"""
    
    def __init__(self, phase_config: Dict):
        """Initialize with phase configuration from ProjectConfig
        
        Args:
            phase_config: Dict mapping phase_id -> {components: [names]}
        """
        self.phase_config = phase_config
        self._build_component_to_phase_map()
        
    def _build_component_to_phase_map(self):
        """Build reverse mapping: component_name -> phase_id"""
        self.component_to_phase = {}
        
        for phase_id, phase_data in self.phase_config.items():
            components = phase_data.get('components', [])
            for component in components:
                comp_name = component.get('name', '')
                if comp_name:
                    self.component_to_phase[comp_name] = phase_id
    
    def categorize_tests(self, test_files: List[TestFile]) -> Dict[int, Dict[str, List[TestFile]]]:
        """Categorize test files by phase and component
        
        Args:
            test_files: List of discovered TestFile objects
            
        Returns:
            Nested dict: {phase_id: {component_name: [TestFile, ...]}}
        """
        categorized = {}
        
        for test_file in test_files:
            # Determine phase from component
            if test_file.component in self.component_to_phase:
                phase_id = self.component_to_phase[test_file.component]
                
                # Initialize phase dict if needed
                if phase_id not in categorized:
                    categorized[phase_id] = {}
                
                # Initialize component list if needed
                if test_file.component not in categorized[phase_id]:
                    categorized[phase_id][test_file.component] = []
                
                # Add test file
                categorized[phase_id][test_file.component].append(test_file)
                
                # Update test_file phase
                test_file.phase = phase_id
        
        return categorized
    
    def get_categorized_paths(self, categorized: Dict) -> Set[str]:
        """Get set of all categorized test file paths
        
        Args:
            categorized: Output from categorize_tests()
            
        Returns:
            Set of relative paths that have been categorized
        """
        paths = set()
        for phase_data in categorized.values():
            for component_tests in phase_data.values():
                for test_file in component_tests:
                    paths.add(test_file.relative_path)
        return paths
    
    def get_summary(self, categorized: Dict) -> Dict:
        """Get summary statistics of categorization
        
        Returns:
            Dictionary with counts per phase and component
        """
        summary = {
            'total_categorized': 0,
            'by_phase': {}
        }
        
        for phase_id, phase_data in categorized.items():
            phase_total = 0
            components = {}
            
            for component, test_files in phase_data.items():
                count = len(test_files)
                components[component] = count
                phase_total += count
            
            summary['by_phase'][phase_id] = {
                'total': phase_total,
                'components': components
            }
            summary['total_categorized'] += phase_total
        
        return summary
    
    def detect_orphaned_tests(self, all_tests: List[TestFile], categorized: Dict) -> List[TestFile]:
        """Find tests that couldn't be categorized
        
        Args:
            all_tests: All discovered test files
            categorized: Output from categorize_tests()
            
        Returns:
            List of uncategorized TestFile objects
        """
        categorized_paths = self.get_categorized_paths(categorized)
        orphaned = []
        
        for test in all_tests:
            if test.relative_path not in categorized_paths:
                orphaned.append(test)
        
        return orphaned
    
    def suggest_migration_plan(self, categorized: Dict) -> List[Dict]:
        """Generate migration plan for moving tests to centralized structure
        
        Returns:
            List of migration steps with source/dest paths
        """
        migration_plan = []
        
        for phase_id, phase_data in sorted(categorized.items()):
            for component, test_files in sorted(phase_data.items()):
                # Group by directory
                source_dirs = set()
                for tf in test_files:
                    source_dirs.add(tf.path.parent)
                
                for source_dir in sorted(source_dirs):
                    # Destination: tests/phase{N}/{component}/
                    dest_dir = Path(f"tests/phase{phase_id}/{component}")
                    
                    # Get test files from this source directory
                    files_to_move = [tf for tf in test_files if tf.path.parent == source_dir]
                    
                    migration_plan.append({
                        'phase': phase_id,
                        'component': component,
                        'source': str(source_dir),
                        'destination': str(dest_dir),
                        'file_count': len(files_to_move),
                        'files': [str(tf.path) for tf in files_to_move]
                    })
        
        return migration_plan
