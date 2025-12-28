"""Skip history display component.

Shows historical skip data in compact tree format:
Phase → Component → Tests (with pagination)
"""

from typing import List, Dict
from pathlib import Path


class SkipHistorySection:
    """Display skip history in compact tree format."""
    
    def __init__(self, history_store, show_all: bool = False, 
                 phase_filter: int = None, component_filter: str = None,
                 term_width: int = 120):
        """Initialize skip history section.
        
        Args:
            history_store: HistoryStore instance for querying
            show_all: If True, show all details. If False, show summary with pagination
            phase_filter: Optional phase ID filter
            component_filter: Optional component name filter
            term_width: Terminal width
        """
        self.history = history_store
        self.show_all = show_all
        self.phase_filter = phase_filter
        self.component_filter = component_filter
        self.term_width = term_width
        
        from ptsd_agent.ui.theme import GRAY, DIM, BOLD, YELLOW, RESET
        self.GRAY = GRAY
        self.DIM = DIM
        self.BOLD = BOLD
        self.YELLOW = YELLOW
        self.RESET = RESET
    
    def build(self) -> List[str]:
        """Build skip history display lines."""
        lines = []
        
        # Get skip history
        skip_data = self.history.get_skip_history(
            component=self.component_filter,
            limit=100
        )
        
        if not skip_data:
            lines.append(f"{self.DIM}No skip history found{self.RESET}")
            return lines
        
        # Group by phase → component
        grouped = self._group_by_phase_component(skip_data)
        
        # Build display
        lines.append(f"{self.BOLD}Skip History{self.RESET}")
        lines.append("─" * min(self.term_width, 80))
        lines.append("")
        
        for phase_id, components in sorted(grouped.items()):
            if self.phase_filter and phase_id != self.phase_filter:
                continue
            
            phase_lines = self._build_phase_section(phase_id, components)
            lines.extend(phase_lines)
        
        return lines
    
    def _group_by_phase_component(self, skip_data: List[Dict]) -> Dict[int, Dict[str, List[Dict]]]:
        """Group skip events by phase and component."""
        grouped = {}
        
        for event in skip_data:
            # Use component as phase grouping for now
            # TODO: Get actual phase_id from event or config
            phase_id = 1  # Default phase
            component = event.get('component', 'unknown')
            
            if phase_id not in grouped:
                grouped[phase_id] = {}
            if component not in grouped[phase_id]:
                grouped[phase_id][component] = []
            
            grouped[phase_id][component].append(event)
        
        return grouped
    
    def _build_phase_section(self, phase_id: int, components: Dict[str, List[Dict]]) -> List[str]:
        """Build phase section with components."""
        lines = []
        
        # Calculate total skips for phase
        total_skips = sum(len(tests) for tests in components.values())
        
        # Phase header
        lines.append(f"{self.BOLD}Phase {phase_id}{self.RESET} ({total_skips} skip pattern{'s' if total_skips != 1 else ''})")
        
        # Components
        for comp_name, tests in sorted(components.items()):
            comp_lines = self._build_component_section(comp_name, tests)
            lines.extend(comp_lines)
        
        lines.append("")  # Blank line after phase
        return lines
    
    def _build_component_section(self, component: str, tests: List[Dict]) -> List[str]:
        """Build component section with test list."""
        lines = []
        
        # Component header with compact summary
        avg_frequency = sum(t.get('skip_count', 0) for t in tests) / len(tests) if tests else 0
        
        if self.show_all:
            # Show all tests
            lines.append(f"  └─ {component}")
            for test in tests[:10]:  # Limit even in show_all
                test_line = self._format_test_compact(test)
                lines.append(f"      {test_line}")
            
            if len(tests) > 10:
                lines.append(f"      {self.DIM}... and {len(tests) - 10} more{self.RESET}")
        else:
            # Compact: show count + top issue
            lines.append(f"  └─ {component}: {len(tests)} test{'s' if len(tests) != 1 else ''} (avg {avg_frequency:.0f}/10 runs)")
            
            # Show top 2 only
            for test in tests[:2]:
                test_line = self._format_test_compact(test)
                lines.append(f"      {test_line}")
            
            if len(tests) > 2:
                lines.append(f"      {self.DIM}... and {len(tests) - 2} more (use --show-all){self.RESET}")
        
        return lines
    
    def _format_test_compact(self, test: Dict) -> str:
        """Format a single test entry compactly."""
        name = test.get('test_name', 'unknown')
        skip_count = test.get('skip_count', 0)
        marker = test.get('marker', 'skip')
        reason = test.get('reason', '')
        
        # Truncate long reasons
        if len(reason) > 50:
            reason = reason[:47] + '...'
        
        if self.show_all:
            return f"{name} ({skip_count}/10 runs, {marker}): {reason}"
        else:
            return f"{name} ({skip_count}/10 runs)"
