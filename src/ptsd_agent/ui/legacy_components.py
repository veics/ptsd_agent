"""
PTSD Agent UI Components
Reusable UI components: ProgressBar, Spinner, ForwardAnimation, MetricsBlock
All components use shared theme for consistent styling.
"""

import time
import shutil
from typing import Optional, Dict, List
from .theme import (
    RESET, DIM, GRAY, CYAN, GREEN, ORANGE, YELLOW,
    CYAN_WASHED, ORANGE_WASHED, RED_WASHED,
    PINK_LIGHT, RED_BRIGHT, PINK_LIGHT_WASHED, RED_BRIGHT_WASHED,
    get_color, get_color_for_value, get_washed_color_for_value,
    get_status_color_name
)


# =============================================================================
# Right Alignment Utility
# =============================================================================

def get_terminal_width() -> int:
    """Get current terminal width."""
    return shutil.get_terminal_size().columns


def right_align_text(left_content: str, right_content: str, 
                     term_width: int = None, trailing_space: int = 1) -> str:
    """
    Align text with left and right portions, padding between them.
    
    Args:
        left_content: Content for left side (may contain ANSI codes)
        right_content: Content for right side (may contain ANSI codes)
        term_width: Terminal width (auto-detected if None)
        trailing_space: Number of trailing spaces after right content
    
    Returns:
        Formatted line with proper spacing and trailing space
    """
    import re
    
    # Strip ANSI codes for length calculation
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    left_visible = ansi_pattern.sub('', left_content)
    right_visible = ansi_pattern.sub('', right_content)
    
    width = term_width or get_terminal_width()
    padding = width - len(left_visible) - len(right_visible) - trailing_space
    
    if padding < 1:
        padding = 1
    
    return f"{left_content}{' ' * padding}{right_content}{' ' * trailing_space}"


def format_line_right_aligned(left: str, middle: str, right: str,
                               term_width: int = None, trailing_space: int = 1) -> str:
    """
    Format a line with left, middle (optional), and right-aligned portions.
    
    Args:
        left: Left-aligned content
        middle: Middle content (will be truncated if needed)
        right: Right-aligned content
        term_width: Terminal width
        trailing_space: Trailing spaces
    """
    import re
    
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    left_vis = ansi_pattern.sub('', left)
    right_vis = ansi_pattern.sub('', right)
    middle_vis = ansi_pattern.sub('', middle)
    
    width = term_width or get_terminal_width()
    available_middle = width - len(left_vis) - len(right_vis) - trailing_space - 2
    
    if len(middle_vis) > available_middle and available_middle > 3:
        # Truncate middle with ellipsis
        middle = "..." + middle[-(available_middle - 3):]
        middle_vis = "..." + middle_vis[-(available_middle - 3):]
    
    padding = width - len(left_vis) - len(middle_vis) - len(right_vis) - trailing_space
    if padding < 1:
        padding = 1
    
    left_pad = 1
    right_pad = padding - left_pad
    if right_pad < 0:
        right_pad = 0
    
    return f"{left}{' ' * left_pad}{middle}{' ' * right_pad}{right}{' ' * trailing_space}"


# =============================================================================
# Spinner Component
# =============================================================================

class Spinner:
    """Time-based braille spinner for consistent animation speed."""
    
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, interval: float = 0.08):
        self.interval = interval
        self._start_time = time.time()
    
    def get_frame(self) -> str:
        """Get current spinner frame based on elapsed time."""
        elapsed = time.time() - self._start_time
        idx = int(elapsed / self.interval) % len(self.FRAMES)
        return self.FRAMES[idx]
    
    def render(self, color: str = None, status: str = "in_progress") -> str:
        """
        Render spinner with color from status or override.
        
        Args:
            color: Override color (ANSI code)
            status: Status name for theme color (in_progress, error, failure, warning)
        """
        frame = self.get_frame()
        if color:
            return f"{color}{frame}{RESET}"
        # Get color from theme by status name
        color_name = get_status_color_name(status)
        color_code = get_color(color_name)
        return f"{color_code}{frame}{RESET}"


# =============================================================================
# Status Indicator Component
# =============================================================================

class StatusIndicator:
    """
    Unified status indicator for components, phases, and projects.
    
    States:
    - not_started: ○ grey/dim
    - initializing: ○ blinking cyan
    - queued: ○ normal color (cyan)
    - running: ⠙ spinner (yellow, escalates on errors)
    - completed: ✓ green (default)
    """
    
    CIRCLE = "○"
    CHECK = "✓"
    
    def __init__(self):
        self._spinner = Spinner()
        self._blink_state = True
        self._last_blink = time.time()
        self._blink_interval = 0.3
    
    def _get_blink_state(self) -> bool:
        """Update and return current blink state."""
        now = time.time()
        if now - self._last_blink >= self._blink_interval:
            self._blink_state = not self._blink_state
            self._last_blink = now
        return self._blink_state
    
    def render(self, state: str, status: str = "success", color_override: str = None) -> str:
        """
        Render status indicator based on state.
        
        Args:
            state: One of 'not_started', 'initializing', 'queued', 'running', 'completed'
            status: For running state, the status level (in_progress, warning, failure, error)
            color_override: Override color for the indicator
        
        Returns:
            Formatted status indicator with ANSI colors
        """
        if state == "not_started":
            return f"{DIM}{self.CIRCLE}{RESET}"
        
        elif state == "initializing":
            # Blinking cyan
            if self._get_blink_state():
                return f"{CYAN}{self.CIRCLE}{RESET}"
            else:
                return f"{DIM}{self.CIRCLE}{RESET}"
        
        elif state == "queued":
            return f"{CYAN}{self.CIRCLE}{RESET}"
        
        elif state == "running":
            return self._spinner.render(color=color_override, status=status)
        
        elif state == "completed":
            color = color_override or GREEN
            return f"{color}{self.CHECK}{RESET}"
        
        else:
            # Default to dim circle
            return f"{DIM}{self.CIRCLE}{RESET}"
    
    @staticmethod
    def get_worst_status(*statuses) -> str:
        """
        Get the worst (highest priority) status from multiple statuses.
        Used for inheritance: component → phase → project.
        
        Priority: error > failure > warning > in_progress > success
        """
        priority = ["success", "in_progress", "warning", "failure", "error"]
        worst_idx = 0
        for s in statuses:
            if s in priority:
                idx = priority.index(s)
                if idx > worst_idx:
                    worst_idx = idx
        return priority[worst_idx]


# =============================================================================
# Forward Animation Component
# =============================================================================

class ForwardAnimation:
    """Forward arrow animation for headers."""
    
    FRAMES = ["▹▹▹▹▸", "▹▹▹▸▹", "▹▹▸▹▹", "▹▸▹▹▹", "▸▹▹▹▹"]
    COMPLETED = "▸▸▸▸▸"
    
    def __init__(self, interval: float = 0.15):
        self.interval = interval
        self._start_time = time.time()
    
    def get_frame(self, mode: str = "running") -> str:
        if mode == "completed":
            return self.COMPLETED
        elapsed = time.time() - self._start_time
        idx = int(elapsed / self.interval) % len(self.FRAMES)
        return self.FRAMES[idx]


# =============================================================================
# Progress Bar Component (Shared)
# =============================================================================

class ProgressBar:
    """
    Unified progress bar component.
    
    Features:
    - Configurable via .ptsd.yaml progress_bar section
    - Brackets [] enclosing the bar
    - Blinking blocks for parallel execution (count = active processes)
    - Color from config or overridable
    - hide_at_100: replace bar with summary at 100%
    """
    
    def __init__(self, width: int = 20, filled: str = None, empty: str = None):
        from .theme import get_progress_bar_config
        config = get_progress_bar_config()
        
        self.width = width
        self.filled = filled or config['filled_char']
        self.empty = empty or config['empty_char']
        self._config = config
        self._blink_state = True
        self._last_blink = time.time()
        self._blink_interval = 0.3
    
    def _get_blink_state(self) -> bool:
        """Update and return current blink state."""
        now = time.time()
        if now - self._last_blink >= self._blink_interval:
            self._blink_state = not self._blink_state
            self._last_blink = now
        return self._blink_state
    
    def render(
        self, 
        pct: float, 
        color: str = None,
        empty_color: str = None,
        active_count: int = 0,
        blink_color: str = None,
        brackets: bool = None
    ) -> str:
        """
        Render progress bar with config-based or override colors.
        
        Args:
            pct: Progress percentage (0-100)
            color: Override color for filled portion
            empty_color: Override color for empty portion
            active_count: Number of active processes (blinking blocks)
            blink_color: Override color for blinking blocks
            brackets: Override whether to wrap in [] (default from config)
        
        Returns:
            Formatted progress bar string like "[▰▰▰▰▰▱▱▱▱▱]"
        """
        from .theme import get_color
        
        pct = max(0, min(100, pct))
        filled_count = int((pct / 100) * self.width)
        empty_count = self.width - filled_count
        
        # Get colors from config or overrides
        filled_clr = color or get_color(self._config['filled_color'])
        empty_clr = empty_color or get_color(self._config['empty_color'])
        blink_clr = blink_color or get_color(self._config['blink_color'])
        
        # Determine blink count from config or active_count
        blink_cfg = self._config['blink_count']
        if blink_cfg == "auto":
            effective_blink_count = active_count
        else:
            effective_blink_count = min(int(blink_cfg), active_count) if active_count > 0 else 0
        
        blink_on = self._get_blink_state()
        use_brackets = brackets if brackets is not None else self._config['show_brackets']
        
        # At 100%, use dimmed/washed color and NO blinking
        if pct >= 100:
            filled_str = f"{DIM}{filled_clr}{self.filled * filled_count}{RESET}"
            bar = filled_str  # No empty blocks at 100%
            if use_brackets:
                return f"[{bar}]"
            return bar
        
        # Build filled portion (not at 100%)
        filled_str = f"{filled_clr}{self.filled * filled_count}{RESET}"
        
        # Build empty portion with blinking blocks for active processes
        if effective_blink_count > 0 and empty_count > 0:
            blink_count = min(effective_blink_count, empty_count)
            regular_empty = empty_count - blink_count
            
            if blink_on:
                # Blink ON: use filled char with dimmed/washed color
                blink_str = f"{DIM}{filled_clr}{self.filled * blink_count}{RESET}"
            else:
                # Blink OFF: use empty char with empty color
                blink_str = f"{empty_clr}{self.empty * blink_count}{RESET}"
            
            empty_str = blink_str + f"{empty_clr}{self.empty * regular_empty}{RESET}"
        else:
            empty_str = f"{empty_clr}{self.empty * empty_count}{RESET}"
        
        # Combine
        bar = f"{filled_str}{empty_str}"
        if use_brackets:
            return f"[{bar}]"
        return bar
    
    def render_or_summary(
        self, 
        pct: float, 
        summary: str = "",
        **kwargs
    ) -> str:
        """
        Render bar or summary based on hide_at_100 config.
        
        If pct >= 100 and hide_at_100 is True, returns summary instead of bar.
        """
        if pct >= 100 and self._config.get('hide_at_100', True):
            return summary
        return self.render(pct, **kwargs)
    
    def render_full_width(
        self, 
        pct: float, 
        term_width: int, 
        color: str = None,
        empty_color: str = None,
        active_count: int = 1
    ) -> str:
        """
        Render full-width progress bar (delimiter bar) with blinking blocks.
        
        Args:
            pct: Progress percentage (0-100)
            term_width: Terminal width
            color: Override color for filled portion
            empty_color: Override color for empty portion
            active_count: Number of blinking blocks
        """
        from .theme import GRAY_WASHED
        
        # Use full term_width for complete line coverage
        bar_width = term_width
        
        pct = max(0, min(100, pct))
        filled_count = int((pct / 100) * bar_width)
        empty_count = bar_width - filled_count
        
        filled_color = color or get_color_for_value("progress", pct)
        empty_clr = empty_color or GRAY
        
        # Blink state for active processes
        blink_on = self._get_blink_state()
        
        # At 100%, use washed version of the color (gray washed for gray, cyan washed for others)
        if pct >= 100:
            if filled_color == GRAY:
                return f"{GRAY_WASHED}{self.filled * term_width}{RESET}"
            else:
                return f"{CYAN_WASHED}{self.filled * term_width}{RESET}"
        
        # Build filled portion
        filled_str = f"{filled_color}{self.filled * filled_count}{RESET}"
        
        # Build empty portion with blinking blocks
        if active_count > 0 and empty_count > 0:
            blink_count = min(active_count, empty_count)
            regular_empty = empty_count - blink_count
            
            if blink_on:
                # Blink ON: use WASHED version of the filled color (gray washed for gray, cyan washed for others)
                if filled_color == GRAY:
                    blink_str = f"{GRAY_WASHED}{self.filled * blink_count}{RESET}"
                else:
                    blink_str = f"{CYAN_WASHED}{self.filled * blink_count}{RESET}"
            else:
                # Blink OFF: use empty color and character
                blink_str = f"{empty_clr}{self.empty * blink_count}{RESET}"
            
            empty_str = blink_str + f"{empty_clr}{self.empty * regular_empty}{RESET}"
        else:
            empty_str = f"{empty_clr}{self.empty * empty_count}{RESET}"
        
        return f"{filled_str}{empty_str}"
    
    @staticmethod
    def format_percentage(pct: float, completed: bool = False) -> str:
        """
        Format percentage with appropriate color.
        
        Args:
            pct: Percentage value
            completed: If True, use DIM/grey color
        """
        if completed:
            return f"{DIM}{int(pct):3d}%{RESET}"
        else:
            color = get_color_for_value("progress", pct)
            return f"{color}{int(pct):3d}%{RESET}"


# =============================================================================
# Metrics Block Component
# =============================================================================

class MetricsBlock:
    """
    Standardized metrics display: [ N wr | N fl | N er | N sk | N% cv | N% ]
    Uses theme thresholds for automatic coloring.
    Compact format: numbers always fit, labels truncate as needed.
    """
    
    # Target total width: ~43 chars for metrics content (excluding brackets)
    # Format: war, fail, err, skip, cov%, pass%
    
    def _format_metric(self, value: int, label: str, width: int) -> str:
        """Format metric with strict fixed width, truncating label if needed."""
        val_str = str(value)
        # Calculate space available for " " + label
        # We need at least 1 char for the number.
        # Construct ideal string: "123 label"
        # If len > width, trim right char by char.
        
        # Start with full label
        suffix = f" {label}"
        
        # Calculate how much space we have for the suffix
        avail = width - len(val_str)
        
        if avail <= 0:
            # Number takes whole width (or more), return number
            return val_str
            
        # Truncate suffix to available space
        if len(suffix) > avail:
            suffix = suffix[:avail]
            
        return f"{val_str}{suffix}".rjust(width)

    def render(
        self,
        cov: int = 0,
        war: int = 0,
        fail: int = 0,
        err: int = 0,
        skip: int = 0,  # Skipped tests (known issues)
        total: int = 0,
        pass_rate: float = 0
    ) -> str:
        """Render metrics block with STRICT FIXED column widths."""
        cov_color = get_washed_color_for_value("coverage", cov)
        war_color = get_washed_color_for_value("warnings", war)
        fail_color = RED_WASHED if fail > 0 else DIM
        err_color = RED_BRIGHT if err > 0 else DIM
        skip_color = GRAY
        total_color = DIM
        pass_color = get_washed_color_for_value("pass_rate", pass_rate)
        
        # Columns widths chosen to fit typical values + short labels
        # Standardized to 6 chars for consistency: "123 ab"
        # labels: cv, wr, fl, er, sk
        
        # Coverage special case for %
        if cov < 0:  # -1 = n/a (not applicable)
            cov_str = "   n/a"
        else:
            cov_val_str = f"{cov}%"
            # Manual format for cov:
            c_suffix = " cv"
            c_avail = 6 - len(cov_val_str)
            if len(c_suffix) > c_avail:
                c_suffix = c_suffix[:c_avail]
            cov_str = f"{cov_val_str}{c_suffix}".rjust(6)

        
        war_str = self._format_metric(war, "wr", 6)
        fail_str = self._format_metric(fail, "fl", 6)
        err_str = self._format_metric(err, "er", 6)
        skip_str = self._format_metric(skip, "sk", 6)
        
        # Pass rate - use round() for proper .5 handling
        if pass_rate == 100 or pass_rate == 0:
            p_val = f"{int(pass_rate)}%"
        else:
            p_val = f"{round(pass_rate)}%"
        pass_str = p_val.rjust(6)
        
        parts = [
            f"{war_color}{war_str}{RESET}",
            f"{fail_color}{fail_str}{RESET}",
            f"{err_color}{err_str}{RESET}",
            f"{skip_color}{skip_str}{RESET}",
            f"{cov_color}{cov_str}{RESET}",
            f"{pass_color}{pass_str}{RESET}",
        ]
        
        separator = f"{DIM}|{RESET}" # 1 char separator
        
        inner = separator.join(parts)
        return f"{DIM}[{RESET}{inner}{DIM}]{RESET}"
    
    @property
    def width(self) -> int:
        # [6wr|6fl|6er|6sk|6cv|6pct] = 2 brackets + 5 separators + 36 chars = 43
        return 43


# =============================================================================
# Full-width Bottom Bar (uses shared ProgressBar)
# =============================================================================

class BottomBar:
    """Full-width progress bar that spans terminal width (uses shared ProgressBar logic)."""
    
    def __init__(self, filled: str = "▰", empty: str = "▱"):
        self._bar = ProgressBar(width=1, filled=filled, empty=empty)
        self.filled = filled
        self.empty = empty
    
    def render(self, pct: float, term_width: int, color: str = None, empty_color: str = None, active_count: int = 1) -> str:
        """Render full-width progress bar with blinking blocks."""
        return self._bar.render_full_width(pct, term_width, color=color, empty_color=empty_color, active_count=active_count)


# =============================================================================
# Diagnostics Section Component
# =============================================================================

class DiagnosticsSection:
    """Display detailed test diagnostics: failures, errors, warnings, skipped tests
    
    Supports two display modes:
    - tree: Hierarchical tree view (Phase → Component → Type → File → Test)
    - flat: Traditional flat list view (default for backward compatibility)
    """
    
    def __init__(self, collector, term_width: int = None, show_diagnostics: bool = False,
                 use_tree_view: bool = False, state: Dict = None, active_phases: List = None,
                 hide_known_issues: bool = False):
        """Initialize diagnostics section.
        
        Args:
            collector: MetricsCollector with component data
            term_width: Terminal width for formatting
            show_diagnostics: Whether to show diagnostics
            use_tree_view: If True, use tree view. If False, use flat view.
            state: Global state dict (required for tree view)
            active_phases: List of active phase IDs (required for tree view)
            hide_known_issues: If True, filter out known issues from display
        """
        self.collector = collector
        self.term_width = term_width or get_terminal_width()
        self.show_diagnostics = show_diagnostics
        self.use_tree_view = use_tree_view
        self.state = state
        self.active_phases = active_phases or []
        self.hide_known_issues = hide_known_issues
        
        # Load known issues registry if it exists
        self.known_issues = None
        try:
            from ptsd_agent.core.known_issues import KnownIssuesRegistry
            self.known_issues = KnownIssuesRegistry()
        except Exception:
            pass  # No registry file or import error, continue without it
    
    def build(self) -> List[str]:
        """Build diagnostics section lines"""
        if not self.show_diagnostics:
            return []
        
        # Use tree view if enabled and state is available
        if self.use_tree_view and self.state is not None:
            return self._build_tree_view()
        else:
            return self._build_flat_view()
    
    def _build_tree_view(self) -> List[str]:
        """Build hierarchical tree view of diagnostics."""
        from ptsd_agent.ui.diagnostic_tree import DiagnosticTreeBuilder, DiagnosticTreeRenderer
        
        # Build tree structure
        builder = DiagnosticTreeBuilder(
            known_issues_registry=self.known_issues,
            hide_known=self.hide_known_issues
        )
        root = builder.build_tree(self.collector, self.state, self.active_phases)
        
        # Render tree with known counts
        renderer = DiagnosticTreeRenderer(term_width=self.term_width)
        renderer.known_counts = builder.get_known_counts()  # Pass known counts for display
        lines = renderer.render(root, show_all=False)
        
        return lines
    
    def _build_flat_view(self) -> List[str]:
        """Build traditional flat list view of diagnostics (legacy format)."""
        lines = []
        
        # Aggregate diagnostics from all components
        all_warnings = []
        all_skipped = []
        all_failures = []
        all_errors = []
        
        for comp_name, comp in self.collector.components.items():
            for w in comp.warning_details:
                all_warnings.append({**w, "component": comp_name})
            for s in comp.skipped_tests:
                all_skipped.append({**s, "component": comp_name})
            for f in comp.failures:
                all_failures.append({**f, "component": comp_name})
            for e in comp.test_errors:
                all_errors.append({**e, "component": comp_name})
        
        # Header with count summary
        total_diag = len(all_warnings) + len(all_skipped) + len(all_failures) + len(all_errors)
        if total_diag == 0:
            return []  # No diagnostics to show
        
        summary = f"{len(all_warnings)} wr | {len(all_skipped)} sk"
        if all_failures:
            summary += f" | {len(all_failures)} fl"
        if all_errors:
            summary += f" | {len(all_errors)} er"
        
        header = right_align_text(f"  {GRAY}Diagnostics ({summary}){RESET}", f"{DIM}▼{RESET}", self.term_width)
        lines.append(header)
        lines.append("")  # Blank line
        
        # Warnings section
        if all_warnings:
            lines.append(f"    {YELLOW}=== Warnings ({len(all_warnings)}) ==={RESET}")
            for i, w in enumerate(all_warnings[:20], 1):  # Show top 20
                lines.append(f"    {DIM}[{i}]{RESET} {w['category']}: {w['message'][:100]}")
                lines.append(f"        {DIM}→ {w['component']}/{w['location']}{RESET}")
            if len(all_warnings) > 20:
                lines.append(f"    {DIM}... ({len(all_warnings) - 20} more){RESET}")
            lines.append("")
        
        # Skipped Tests section
        if all_skipped:
            lines.append(f"    {CYAN}=== Skipped Tests ({len(all_skipped)}) ==={RESET}")
            for i, s in enumerate(all_skipped[:20], 1):
                marker_label = s.get('marker', 'skip').upper()
                lines.append(f"    {DIM}[{i}]{RESET} {s['component']}::{s['test_name']}")
                lines.append(f"        {DIM}→ Reason: {s['reason']} ({marker_label}){RESET}")
            if len(all_skipped) > 20:
                lines.append(f"    {DIM}... ({len(all_skipped) - 20} more){RESET}")
            lines.append("")
        
        # Failures section
        if all_failures:
            lines.append(f"    {RED_BRIGHT}=== Test Failures ({len(all_failures)}) ==={RESET}")
            for i, f in enumerate(all_failures[:10], 1):
                lines.append(f"    {DIM}[{i}]{RESET} {f['component']}::{f['test_name']}")
                lines.append(f"        {DIM}→ {f['reason']}{RESET}")
                lines.append(f"        {DIM}→ {f['location']}{RESET}")
            if len(all_failures) > 10:
                lines.append(f"    {DIM}... ({len(all_failures) - 10} more){RESET}")
            lines.append("")
        
        # Errors section
        if all_errors:
            lines.append(f"    {RED_BRIGHT}=== Errors ({len(all_errors)}) ==={RESET}")
            for i, e in enumerate(all_errors[:10], 1):
                lines.append(f"    {DIM}[{i}]{RESET} {e['component']}::{e['test_name']}")
                lines.append(f"        {DIM}→ {e['error_type']}: {e['message']}{RESET}")
                lines.append(f"        {DIM}→ {e['location']}{RESET}")
            if len(all_errors) > 10:
                lines.append(f"    {DIM}... ({len(all_errors) - 10} more){RESET}")
        
        return lines
