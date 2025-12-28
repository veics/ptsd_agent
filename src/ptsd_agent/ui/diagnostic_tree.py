"""Hierarchical tree view for test diagnostics.

Provides tree-based diagnostic display matching test execution structure:
Phase → Component → Type (Warnings/Skips/Failures/Errors) → File → Test
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict
from pathlib import Path


@dataclass
class DiagnosticNode:
    """Node in the diagnostic tree hierarchy.
    
    Represents a single node which can be:
    - Phase level: Contains components
    - Component level: Contains diagnostic types
    - Type level: Contains files (warnings, skipped, failures, errors)
    - File level: Contains individual tests
    - Test level: Leaf node with actual diagnostic details
    """
    level: str  # 'phase', 'component', 'type', 'file', 'test'
    name: str
    children: List['DiagnosticNode'] = field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=lambda: {
        'warnings': 0,
        'skipped': 0,
        'failures': 0,
        'errors': 0
    })
    expanded: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_issues(self) -> bool:
        """Check if this node or any child has diagnostics."""
        return sum(self.counts.values()) > 0
    
    def should_display(self, show_all: bool = False) -> bool:
        """Determine if node should be displayed.
        
        Args:
            show_all: If True, show all nodes. If False, only show nodes with issues.
        
        Returns:
            True if node should be displayed
        """
        if show_all:
            return True
        return self.has_issues()
    
    def total_count(self) -> int:
        """Get total diagnostic count."""
        return sum(self.counts.values())


class DiagnosticTreeBuilder:
    """Build hierarchical diagnostic tree from flat component data."""
    
    def __init__(self):
        self.diagnostic_type_map = {
            'warning_details': 'warnings',
            'skipped_tests': 'skipped',
            'failures': 'failures',
            'test_errors': 'errors'
        }
    
    def build_tree(self, collector, state: Dict, active_phases: List[int]) -> DiagnosticNode:
        """Build complete diagnostic tree from collector and state.
        
        Args:
            collector: MetricsCollector instance with component data
            state: Global state dict with phase/component structure
            active_phases: List of active phase IDs
        
        Returns:
            Root DiagnosticNode containing entire tree
        """
        root = DiagnosticNode(
            level='root',
            name='Diagnostics',
            expanded=True
        )
        
        # Build tree: Phase → Component → Type → File → Test
        for phase_id in active_phases:
            phase_state = state['phases'].get(phase_id)
            if not phase_state:
                continue
            
            phase_node = self._build_phase_node(phase_id, phase_state, collector)
            
            # Only add phase if it has issues or components
            if phase_node.children:
                root.children.append(phase_node)
                self._propagate_counts(phase_node, root)
        
        return root
    
    def _build_phase_node(self, phase_id: int, phase_state: Dict, collector) -> DiagnosticNode:
        """Build a phase node with its components."""
        phase_node = DiagnosticNode(
            level='phase',
            name=phase_state.get('name', f'Phase {phase_id}'),
            metadata={'phase_id': phase_id}
        )
        
        # Process each component in the phase
        for comp_name in phase_state.get('components', {}).keys():
            comp_data = collector.get_component(comp_name)
            if not comp_data:
                continue
            
            comp_node = self._build_component_node(comp_name, comp_data)
            
            # Only add component if it has issues
            if comp_node.children:
                phase_node.children.append(comp_node)
                self._propagate_counts(comp_node, phase_node)
        
        return phase_node
    
    def _build_component_node(self, comp_name: str, comp_data) -> DiagnosticNode:
        """Build a component node with diagnostic types."""
        comp_node = DiagnosticNode(
            level='component',
            name=comp_name,
            metadata={'component': comp_name}
        )
        
        # Process each diagnostic type (warnings, skipped, failures, errors)
        for attr_name, type_name in self.diagnostic_type_map.items():
            diagnostics = getattr(comp_data, attr_name, [])
            if not diagnostics:
                continue
            
            type_node = self._build_type_node(type_name, diagnostics, comp_name)
            
            if type_node.children or type_node.diagnostics:
                comp_node.children.append(type_node)
                self._propagate_counts(type_node, comp_node)
        
        return comp_node
    
    def _build_type_node(self, type_name: str, diagnostics: List[Dict], comp_name: str) -> DiagnosticNode:
        """Build a diagnostic type node (warnings, skipped, failures, errors)."""
        # Map type name to display name
        display_names = {
            'warnings': 'Warnings',
            'skipped': 'Skipped Tests',
            'failures': 'Test Failures',
            'errors': 'Errors'
        }
        
        type_node = DiagnosticNode(
            level='type',
            name=f"{display_names.get(type_name, type_name)} ({len(diagnostics)})",
            metadata={'type': type_name, 'component': comp_name}
        )
        
        # Set count for this type
        type_node.counts[type_name] = len(diagnostics)
        
        # Group diagnostics by file
        grouped = self._group_by_file(diagnostics)
        
        # Create file nodes
        for file_path, file_diags in grouped.items():
            file_node = self._build_file_node(file_path, file_diags, type_name)
            type_node.children.append(file_node)
        
        return type_node
    
    def _build_file_node(self, file_path: str, diagnostics: List[Dict], type_name: str) -> DiagnosticNode:
        """Build a file node containing test-level diagnostics."""
        # Get just the filename for display
        filename = Path(file_path).name if file_path != 'unknown' else 'unknown'
        
        file_node = DiagnosticNode(
            level='file',
            name=f"{file_path} ({len(diagnostics)})",
            metadata={'file': file_path},
            expanded=False  # Files collapsed by default
        )
        
        # Create test nodes for each diagnostic
        for diag in diagnostics:
            test_node = self._build_test_node(diag, type_name)
            file_node.children.append(test_node)
            file_node.counts[type_name] += 1
        
        return file_node
    
    def _build_test_node(self, diagnostic: Dict, type_name: str) -> DiagnosticNode:
        """Build a test-level node (leaf) with diagnostic details."""
        # Extract test name based on diagnostic type
        if type_name == 'warnings':
            test_name = diagnostic.get('category', 'Unknown')
            details = diagnostic.get('message', '')
        elif type_name == 'skipped':
            test_name = diagnostic.get('test_name', 'Unknown')
            details = f"Reason: {diagnostic.get('reason', 'No reason')} ({diagnostic.get('marker', 'skip').upper()})"
        elif type_name in ('failures', 'errors'):
            test_name = diagnostic.get('test_name', 'Unknown')
            if type_name == 'failures':
                details = diagnostic.get('reason', '')
            else:
                details = f"{diagnostic.get('error_type', 'Error')}: {diagnostic.get('message', '')}"
        else:
            test_name = 'Unknown'
            details = str(diagnostic)
        
        test_node = DiagnosticNode(
            level='test',
            name=test_name,
            diagnostics=[diagnostic],
            metadata={'details': details, 'type': type_name}
        )
        test_node.counts[type_name] = 1
        
        return test_node
    
    def _group_by_file(self, diagnostics: List[Dict]) -> Dict[str, List[Dict]]:
        """Group diagnostics by source file.
        
        Args:
            diagnostics: List of diagnostic dicts
        
        Returns:
            Dict mapping file paths to lists of diagnostics
        """
        grouped = defaultdict(list)
        
        for diag in diagnostics:
            # Extract file path from location field
            location = diag.get('location', 'unknown')
            if isinstance(location, str):
                # Location format: "path/file.py:123" or just "path/file.py"
                file_path = location.split(':')[0]
            else:
                file_path = 'unknown'
            
            grouped[file_path].append(diag)
        
        return dict(grouped)
    
    def _propagate_counts(self, child: DiagnosticNode, parent: DiagnosticNode):
        """Propagate diagnostic counts from child to parent.
        
        Args:
            child: Child node with counts to propagate
            parent: Parent node to receive counts
        """
        for key in parent.counts.keys():
            parent.counts[key] += child.counts.get(key, 0)


class DiagnosticTreeRenderer:
    """Render diagnostic tree with indentation and expand/collapse indicators."""
    
    def __init__(self, term_width: int = 120):
        """Initialize renderer.
        
        Args:
            term_width: Terminal width for line wrapping
        """
        self.term_width = term_width
        
        # Import colors from theme
        from ptsd_agent.ui.theme import (
            RESET, DIM, BOLD, GRAY, RED, GREEN, YELLOW, CYAN,
            RED_BRIGHT, BLUE
        )
        self.RESET = RESET
        self.DIM = DIM
        self.BOLD = BOLD
        self.GRAY = GRAY
        self.RED = RED
        self.GREEN = GREEN
        self.YELLOW = YELLOW
        self.CYAN = CYAN
        self.RED_BRIGHT = RED_BRIGHT
        self.BLUE = BLUE
    
    def render(self, root: DiagnosticNode, show_all: bool = False) -> List[str]:
        """Render tree to list of strings for terminal output.
        
        Args:
            root: Root node of diagnostic tree
            show_all: If True, show all nodes. If False, filter to nodes with issues.
        
        Returns:
            List of formatted strings ready for terminal output
        """
        lines = []
        
        # Header with total counts
        if root.total_count() > 0:
            header = self._format_header(root)
            lines.append(header)
            lines.append("")  # Blank line
        
        # Render children (skip root itself)
        for i, child in enumerate(root.children):
            is_last = (i == len(root.children) - 1)
            self._render_node(child, lines, indent="", is_last=is_last, show_all=show_all)
        
        return lines
    
    def _render_node(self, node: DiagnosticNode, lines: List[str], 
                     indent: str, is_last: bool, show_all: bool):
        """Recursively render node and children.
        
        Args:
            node: Node to render
            lines: Output list to append formatted lines
            indent: Current indentation string
            is_last: Whether this is the last sibling
            show_all: Whether to show nodes without issues
        """
        if not node.should_display(show_all):
            return
        
        # Build tree character prefix
        tree_char = "└─" if is_last else "├─"
        expansion = "▼" if node.expanded else "►"
        
        # Build node line with appropriate coloring
        line = self._format_node_line(node, indent, tree_char, expansion)
        lines.append(line)
        
        # Render children if expanded
        if node.expanded and node.children:
            child_indent = indent + ("   " if is_last else "│  ")
            for i, child in enumerate(node.children):
                is_last_child = (i == len(node.children) - 1)
                self._render_node(child, lines, child_indent, is_last_child, show_all)
    
    def _format_node_line(self, node: DiagnosticNode, indent: str, 
                         tree_char: str, expansion: str) -> str:
        """Format a single node line with colors and counts.
        
        Args:
            node: Node to format
            indent: Current indentation
            tree_char: Tree character (├─ or └─)
            expansion: Expansion indicator (▼ or ►)
        
        Returns:
            Formatted line string
        """
        # Choose color based on level and type
        color = self._get_node_color(node)
        
        # Build count string
        count_str = self._format_counts(node.counts)
        
        # Format based on node level
        if node.level == 'phase':
            # Phase: "✓ Phase 1: Architecture & Foundation [7 wr | 2 sk] ▼"
            status_icon = f"{self.GREEN}✓{self.RESET}"
            line = f"{indent}{status_icon} {self.BOLD}{node.name}{self.RESET}"
            if count_str:
                line += f" {count_str}"
            line += f" {self.DIM}{expansion}{self.RESET}"
        
        elif node.level == 'component':
            # Component: "├─ architecture [7 wr] ▼"
            line = f"{indent}{tree_char} {node.name}"
            if count_str:
                line += f" {count_str}"
            line += f" {self.DIM}{expansion}{self.RESET}"
        
        elif node.level == 'type':
            # Type: "└─ Warnings (7) ▼"
            line = f"{indent}{tree_char} {color}{node.name}{self.RESET}"
            line += f" {self.DIM}{expansion}{self.RESET}"
        
        elif node.level == 'file':
            # File: "├─ test_core.py (3) ►"
            line = f"{indent}{tree_char} {self.GRAY}{node.name}{self.RESET}"
            line += f" {self.DIM}{expansion}{self.RESET}"
        
        elif node.level == 'test':
            # Test: "├─ test_name" (leaf, no expansion)
            details = node.metadata.get('details', '')
            line = f"{indent}{tree_char} {node.name}"
            if details:
                # Add details on next line with extra indentation
                lines_list = [line]
                detail_indent = indent + ("   " if tree_char == "└─" else "│  ")
                lines_list.append(f"{detail_indent}{self.DIM}→ {details}{self.RESET}")
                return "\n".join(lines_list)
        
        else:
            # Default formatting
            line = f"{indent}{tree_char} {node.name}"
            if count_str:
                line += f" {count_str}"
            line += f" {self.DIM}{expansion}{self.RESET}"
        
        return line
    
    def _get_node_color(self, node: DiagnosticNode) -> str:
        """Get color for node based on type.
        
        Args:
            node: Node to get color for
        
        Returns:
            ANSI color code
        """
        if node.level == 'type':
            type_name = node.metadata.get('type', '')
            if type_name == 'warnings':
                return self.YELLOW
            elif type_name == 'skipped':
                return self.CYAN
            elif type_name in ('failures', 'errors'):
                return self.RED_BRIGHT
        
        return ""  # No color
    
    def _format_counts(self, counts: Dict[str, int]) -> str:
        """Format diagnostic counts for display.
        
        Args:
            counts: Dict of diagnostic type counts
        
        Returns:
            Formatted count string like "[3 wr | 2 sk]"
        """
        parts = []
        
        if counts.get('warnings'):
            parts.append(f"{counts['warnings']} wr")
        if counts.get('skipped'):
            parts.append(f"{counts['skipped']} sk")
        if counts.get('failures'):
            parts.append(f"{counts['failures']} fl")
        if counts.get('errors'):
            parts.append(f"{counts['errors']} er")
        
        if not parts:
            return ""
        
        return f"[{' | '.join(parts)}]"
    
    def _format_header(self, root: DiagnosticNode) -> str:
        """Format header line with total counts.
        
        Args:
            root: Root node with aggregated counts
        
        Returns:
            Formatted header string
        """
        total = root.total_count()
        count_str = self._format_counts(root.counts)
        
        header = f"{self.GRAY}Diagnostics ({total} total: {count_str}){self.RESET}"
        # Right-align the expansion indicator
        padding = max(0, self.term_width - len(f"Diagnostics ({total} total: {count_str})") - 5)
        return header + (" " * padding) + f"{self.DIM}▼{self.RESET}"
