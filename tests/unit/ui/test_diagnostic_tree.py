"""Unit tests for diagnostic tree structures."""

import pytest
from ptsd_agent.ui.diagnostic_tree import DiagnosticNode, DiagnosticTreeBuilder, DiagnosticTreeRenderer
from ptsd_agent.metrics.legacy_collector import MetricsCollector, ComponentMetrics


class TestDiagnosticNode:
    """Test DiagnosticNode dataclass."""
    
    def test_node_creation(self):
        """Test basic node creation."""
        node = DiagnosticNode(level='phase', name='Phase 1')
        assert node.level == 'phase'
        assert node.name == 'Phase 1'
        assert node.children == []
        assert node.expanded is True
    
    def test_has_issues(self):
        """Test has_issues() method."""
        node = DiagnosticNode(level='component', name='acl')
        assert not node.has_issues()
        
        node.counts['warnings'] = 5
        assert node.has_issues()
    
    def test_should_display(self):
        """Test should_display() filtering."""
        node = DiagnosticNode(level='component', name='clean_component')
        
        # Without issues, not displayed unless show_all
        assert not node.should_display(show_all=False)
        assert node.should_display(show_all=True)
        
        # With issues, always displayed
        node.counts['failures'] = 1
        assert node.should_display(show_all=False)
        assert node.should_display(show_all=True)
    
    def test_total_count(self):
        """Test total_count() calculation."""
        node = DiagnosticNode(level='phase', name='Phase 1')
        assert node.total_count() == 0
        
        node.counts = {
            'warnings': 5,
            'skipped': 2,
            'failures': 1,
            'errors': 0
        }
        assert node.total_count() == 8


class TestDiagnosticTreeBuilder:
    """Test DiagnosticTreeBuilder."""
    
    def test_group_by_file(self):
        """Test file grouping logic."""
        builder = DiagnosticTreeBuilder()
        
        diagnostics = [
            {'location': 'tests/test_a.py:10', 'message': 'Warning 1'},
            {'location': 'tests/test_a.py:20', 'message': 'Warning 2'},
            {'location': 'tests/test_b.py:15', 'message': 'Warning 3'},
        ]
        
        grouped = builder._group_by_file(diagnostics)
        
        assert len(grouped) == 2
        assert len(grouped['tests/test_a.py']) == 2
        assert len(grouped['tests/test_b.py']) == 1
    
    def test_build_tree_empty(self):
        """Test building tree with no diagnostics."""
        builder = DiagnosticTreeBuilder()
        collector = MetricsCollector()
        state = {'phases': {}}
        
        root = builder.build_tree(collector, state, [])
        
        assert root.level == 'root'
        assert len(root.children) == 0
        assert root.total_count() == 0
    
    def test_build_tree_with_warnings(self):
        """Test building tree with warnings."""
        builder = DiagnosticTreeBuilder()
        collector = MetricsCollector()
        
        # Add component with warnings
        comp = collector.get_component('test_comp')
        comp.warning_details = [
            {
                'category': 'DeprecationWarning',
                'message': 'Test warning',
                'location': 'tests/test_file.py:10'
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
        
        root = builder.build_tree(collector, state, [1])
        
        assert len(root.children) == 1  # 1 phase
        phase_node = root.children[0]
        assert phase_node.level == 'phase'
        assert phase_node.name == 'Phase 1'
        assert len(phase_node.children) == 1  # 1 component
        
        comp_node = phase_node.children[0]
        assert comp_node.level == 'component'
        assert comp_node.name == 'test_comp'
        assert len(comp_node.children) == 1  # 1 type (warnings)
        
        type_node = comp_node.children[0]
        assert type_node.level == 'type'
        assert 'Warnings' in type_node.name
    
    def test_count_propagation(self):
        """Test that counts propagate up the tree."""
        builder = DiagnosticTreeBuilder()
        collector = MetricsCollector()
        
        # Add component with mixed diagnostics
        comp = collector.get_component('test_comp')
        comp.warning_details = [
            {'category': 'Warning1', 'message': 'msg', 'location': 'test.py:1'},
            {'category': 'Warning2', 'message': 'msg', 'location': 'test.py:2'}
        ]
        comp.skipped_tests = [
            {'test_name': 'test_1', 'reason': 'skipped', 'marker': 'skip', 'location': 'test.py:3'}
        ]
        
        state = {
            'phases': {
                1: {
                    'name': 'Phase 1',
                    'components': {'test_comp': {}}
                }
            }
        }
        
        root = builder.build_tree(collector, state, [1])
        
        # Check root counts
        assert root.counts['warnings'] == 2
        assert root.counts['skipped'] == 1
        assert root.total_count() == 3
        
        # Check phase counts
        phase_node = root.children[0]
        assert phase_node.counts['warnings'] == 2
        assert phase_node.counts['skipped'] == 1


class TestDiagnosticTreeRenderer:
    """Test DiagnosticTreeRenderer."""
    
    def test_render_empty_tree(self):
        """Test rendering empty tree."""
        renderer = DiagnosticTreeRenderer(term_width=80)
        root = DiagnosticNode(level='root', name='Diagnostics')
        
        lines = renderer.render(root)
        
        assert len(lines) == 0  # No output for empty tree
    
    def test_render_single_phase(self):
        """Test rendering tree with single phase."""
        renderer = DiagnosticTreeRenderer(term_width=80)
        
        root = DiagnosticNode(level='root', name='Diagnostics')
        root.counts['warnings'] = 3
        
        phase = DiagnosticNode(level='phase', name='Phase 1')
        phase.counts['warnings'] = 3
        root.children.append(phase)
        
        lines = renderer.render(root)
        
        assert len(lines) > 0
        assert 'Phase 1' in lines[2]  # After header and blank line
    
    def test_format_counts(self):
        """Test count formatting."""
        renderer = DiagnosticTreeRenderer()
        
        # Empty counts
        counts = {'warnings': 0, 'skipped': 0, 'failures': 0, 'errors': 0}
        assert renderer._format_counts(counts) == ""
        
        # Single type
        counts = {'warnings': 5, 'skipped': 0, 'failures': 0, 'errors': 0}
        assert renderer._format_counts(counts) == "[5 wr]"
        
        # Multiple types
        counts = {'warnings': 3, 'skipped': 2, 'failures': 1, 'errors': 0}
        result = renderer._format_counts(counts)
        assert "3 wr" in result
        assert "2 sk" in result
        assert "1 fl" in result
    
    def test_expansion_indicators(self):
        """Test expansion indicators in output."""
        renderer = DiagnosticTreeRenderer()
        
        root = DiagnosticNode(level='root', name='Diagnostics')
        root.counts['warnings'] = 1
        
        phase = DiagnosticNode(level='phase', name='Phase 1', expanded=True)
        phase.counts['warnings'] = 1
        root.children.append(phase)
        
        lines = renderer.render(root)
        output = '\n'.join(lines)
        
        # Expanded nodes should have ▼
        assert '▼' in output
    
    def test_filtering_clean_nodes(self):
        """Test that clean nodes are filtered out."""
        renderer = DiagnosticTreeRenderer()
        
        root = DiagnosticNode(level='root', name='Diagnostics')
        root.counts['warnings'] = 1
        
        # Phase with issues
        phase1 = DiagnosticNode(level='phase', name='Phase 1 (with issues)')
        phase1.counts['warnings'] = 1
        
        # Phase without issues
        phase2 = DiagnosticNode(level='phase', name='Phase 2 (clean)')
        # No counts set
        
        root.children = [phase1, phase2]
        
        lines = renderer.render(root, show_all=False)
        output = '\n'.join(lines)
        
        # Phase 1 should be shown
        assert 'Phase 1' in output
        
        # Phase 2 should NOT be shown
        assert 'Phase 2' not in output
    
    def test_show_all_flag(self):
        """Test show_all flag includes clean nodes."""
        renderer = DiagnosticTreeRenderer()
        
        root = DiagnosticNode(level='root', name='Diagnostics')
        # No counts - clean tree
        
        phase = DiagnosticNode(level='phase', name='Clean Phase')
        root.children.append(phase)
        
        # Without show_all, nothing rendered
        lines = renderer.render(root, show_all=False)
        assert len(lines) == 0
        
        # With show_all, phase is rendered
        lines = renderer.render(root, show_all=True)
        assert len(lines) > 0
