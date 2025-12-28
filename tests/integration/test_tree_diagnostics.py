"""Integration tests for tree-view diagnostics display."""

import pytest
from ptsd_agent.ui.diagnostic_tree import DiagnosticTreeBuilder, DiagnosticTreeRenderer
from ptsd_agent.ui.legacy_components import DiagnosticsSection
from ptsd_agent.metrics.legacy_collector import MetricsCollector


class TestTreeViewIntegration:
    """Integration tests for complete tree view workflow."""
    
    def test_full_tree_workflow(self):
        """Test complete workflow: collector → builder → renderer."""
        # Setup collector with mixed diagnostics
        collector = MetricsCollector()
        
        comp1 = collector.get_component('acl')
        comp1.warning_details = [
            {
                'category': 'DeprecationWarning',
                'message': 'Old API deprecated',
                'location': 'tests/acl/test_auth.py:10'
            },
            {
                'category': 'UserWarning',
                'message': 'Missing config',
                'location': 'tests/acl/test_auth.py:25'
            }
        ]
        comp1.skipped_tests = [
            {
                'test_name': 'test_oauth',
                'reason': 'OAuth not configured',
                'marker': 'skipif',
                'location': 'tests/acl/test_oauth.py:15'
            }
        ]
        
        comp2 = collector.get_component('architecture')
        comp2.failures = [
            {
                'test_name': 'test_schema_validation',
                'reason': 'AssertionError: Schema mismatch',
                'location': 'tests/architecture/test_schema.py:45'
            }
        ]
        
        state = {
            'phases': {
                1: {
                    'name': 'Phase 1: Core',
                    'components': {
                        'acl': {},
                        'architecture': {}
                    }
                }
            }
        }
        
        # Build tree
        builder = DiagnosticTreeBuilder()
        root = builder.build_tree(collector, state, [1])
        
        # Verify tree structure
        assert len(root.children) == 1  # 1 phase
        phase = root.children[0]
        assert phase.name == 'Phase 1: Core'
        assert len(phase.children) == 2  # 2 components
        
        # Verify counts propagated
        assert root.counts['warnings'] == 2
        assert root.counts['skipped'] == 1
        assert root.counts['failures'] == 1
        assert root.total_count() == 4
        
        # Render tree
        renderer = DiagnosticTreeRenderer(term_width=120)
        lines = renderer.render(root)
        
        # Verify output
        assert len(lines) > 0
        output = '\n'.join(lines)
        assert 'Phase 1: Core' in output
        assert 'acl' in output
        assert 'architecture' in output
        assert 'Warnings' in output
        assert 'Skipped Tests' in output
        assert 'Test Failures' in output
    
    def test_diagnostics_section_tree_vs_flat(self):
        """Test that tree and flat views show same data."""
        collector = MetricsCollector()
        
        comp = collector.get_component('test_comp')
        comp.warning_details = [
            {
                'category': 'Warning1',
                'message': 'Msg1',
                'location': 'file1.py:1'
            },
            {
                'category': 'Warning2',
                'message': 'Msg2',
                'location': 'file2.py:2'
            }
        ]
        comp.skipped_tests = [
            {
                'test_name': 'test_skip',
                'reason': 'Skipped',
                'marker': 'skip',
                'location': 'file3.py:3'
            }
        ]
        
        state = {
            'phases': {
                1: {
                    'name': 'Phase 1',
                    'components': {'test_comp': {}}
                }
            }
        }
        
        # Flat view
        diag_flat = DiagnosticsSection(
            collector=collector,
            show_diagnostics=True,
            use_tree_view=False
        )
        flat_lines = diag_flat.build()
        flat_output = '\n'.join(flat_lines)
        
        # Tree view
        diag_tree = DiagnosticsSection(
            collector=collector,
            show_diagnostics=True,
            use_tree_view=True,
            state=state,
            active_phases=[1]
        )
        tree_lines = diag_tree.build()
        tree_output = '\n'.join(tree_lines)
        
        # Both should mention the diagnostics
        assert '2 wr' in flat_output
        assert '1 sk' in flat_output
        assert '2 wr' in tree_output
        assert '1 sk' in tree_output
        
        # Flat should have numbered list
        assert '[1]' in flat_output
        assert '[2]' in flat_output
        
        # Tree should have hierarchy
        assert 'Phase 1' in tree_output
        assert 'test_comp' in tree_output
        assert '▼' in tree_output or '►' in tree_output
    
    def test_empty_diagnostics(self):
        """Test that empty diagnostics return empty output."""
        collector = MetricsCollector()
        # No diagnostics added
        
        state = {
            'phases': {
                1: {
                    'name': 'Phase 1',
                    'components': {}
                }
            }
        }
        
        # Flat view
        diag_flat = DiagnosticsSection(
            collector=collector,
            show_diagnostics=True
        )
        assert len(diag_flat.build()) == 0
        
        # Tree view
        diag_tree = DiagnosticsSection(
            collector=collector,
            show_diagnostics=True,
            use_tree_view=True,
            state=state,
            active_phases=[1]
        )
        assert len(diag_tree.build()) == 0
    
    def test_tree_filtering(self):
        """Test that clean components are filtered out."""
        collector = MetricsCollector()
        
        # Component with issues
        comp1 = collector.get_component('comp_with_issues')
        comp1.warning_details = [
            {
                'category': 'Warning',
                'message': 'Issue',
                'location': 'file.py:1'
            }
        ]
        
        # Clean component (no diagnostics)
        comp2 = collector.get_component('clean_comp')
        # No diagnostics added
        
        state = {
            'phases': {
                1: {
                    'name': 'Phase 1',
                    'components': {
                        'comp_with_issues': {},
                        'clean_comp': {}
                    }
                }
            }
        }
        
        # Build tree
        builder = DiagnosticTreeBuilder()
        root = builder.build_tree(collector, state, [1])
        
        # Verify clean component filtered out
        phase = root.children[0]
        assert len(phase.children) == 1  # Only comp_with_issues
        assert phase.children[0].name == 'comp_with_issues'
    
    def test_file_grouping(self):
        """Test that diagnostics are grouped by file."""
        collector = MetricsCollector()
        
        comp = collector.get_component('test_comp')
        comp.warning_details = [
            {'category': 'W1', 'message': 'M1', 'location': 'file1.py:10'},
            {'category': 'W2', 'message': 'M2', 'location': 'file1.py:20'},
            {'category': 'W3', 'message': 'M3', 'location': 'file2.py:15'},
        ]
        
        state = {
            'phases': {
                1: {
                    'name': 'Phase 1',
                    'components': {'test_comp': {}}
                }
            }
        }
        
        # Build tree
        builder = DiagnosticTreeBuilder()
        root = builder.build_tree(collector, state, [1])
        
        # Navigate to warnings type node
        phase = root.children[0]
        comp = phase.children[0]
        warnings_type = comp.children[0]
        
        # Should have 2 file nodes
        assert len(warnings_type.children) == 2
        
        # Verify file grouping
        file_names = [node.metadata['file'] for node in warnings_type.children]
        assert 'file1.py' in file_names
        assert 'file2.py' in file_names
        
        # file1.py should have 2 warnings
        file1_node = [n for n in warnings_type.children if n.metadata['file'] == 'file1.py'][0]
        assert len(file1_node.children) == 2
