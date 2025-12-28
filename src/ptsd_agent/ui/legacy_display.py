#!/usr/bin/env python3.14
"""
Progressive Display v4 - Final layout with perfect alignment and centered metrics
Now uses shared theme.py for colors and components.py for UI elements.
"""

import sys
import time
import shutil
import re

# Import shared theme colors
from .theme import (
    RESET, DIM, GRAY, RED, GREEN, YELLOW, ORANGE, CYAN,
    RED_WASHED, GREEN_WASHED, YELLOW_WASHED, ORANGE_WASHED, CYAN_WASHED,
    BLUE_WASHED, get_color_for_value, get_washed_color_for_value,
    get_status_color_name, get_color,
    TRIANGLE_EXPANDED, TRIANGLE_COLLAPSED
)
# Import shared components
from .legacy_components import Spinner, ForwardAnimation, ProgressBar, MetricsBlock, BottomBar, DiagnosticsSection


class ProgressiveDisplay:
    """Final display implementation with precise layout and centering"""
    
    # Minimum terminal width to prevent errors
    MIN_TERM_WIDTH = 80
    
    def _handle_resize(self, old_size, new_size):
        """Handle terminal resize event atomically.
        
        Args:
            old_size: Previous terminal size (width, height)
            new_size: New terminal size (width, height)
        """
        # Acquire lock to prevent rendering during resize
        with self._resize_lock:
            self._resizing = True
            
            # Update terminal width
            self.term_width = max(self.MIN_TERM_WIDTH, new_size[0])
            
            # Clear the display buffer to prevent corruption
            # The next render() call will draw with the new width
            if self.last_line_count > 0:
                # Move cursor up and clear all previously rendered lines
                sys.stdout.write(f"\033[{self.last_line_count}A")
                for _ in range(self.last_line_count):
                    sys.stdout.write("\033[2K\033[B")
                sys.stdout.write(f"\033[{self.last_line_count}A")
                sys.stdout.flush()
                # Reset line count - next render will update it
                self.last_line_count = 0
            
            self._resizing = False
    
    def get_status_color(self, pct):
        """Color based on progress using theme thresholds."""
        return get_color_for_value("progress", pct)

    def get_washed_status_color(self, pct):
        """Washed color based on progress using theme thresholds."""
        return get_washed_color_for_value("progress", pct)

    def get_bar_color(self, pct):
        """Color for bar/pct using theme thresholds."""
        return get_color_for_value("bar", pct)
    
    def get_status_from_metrics(self, component_names=None, component_name=None) -> str:
        """
        Determine status from metrics (errors/failures) for spinner color inheritance.
        
        Priority: error > failure > warning > in_progress > success
        
        Returns:
            Status name: 'error', 'failure', 'warning', 'in_progress', or 'success'
        """
        errors = 0
        failures = 0
        warnings = 0
        
        if component_names and self.collector:
            for cname in component_names:
                comp = self.collector.get_component(cname)
                if comp:
                    errors += comp.errors
                    failures += comp.failed
                    warnings += comp.warnings
        elif component_name and self.collector:
            comp = self.collector.get_component(component_name)
            if comp:
                errors = comp.errors
                failures = comp.failed
                warnings = comp.warnings
        
        if errors > 0:
            return "error"
        elif failures > 0:
            return "failure"
        elif warnings > 0:
            return "warning"
        else:
            return "in_progress"
    
    def get_inherited_spinner_color(self, component_names=None, component_name=None):
        """Get spinner color based on worst status from children."""
        status = self.get_status_from_metrics(component_names, component_name)
        color_name = get_status_color_name(status)
        return get_color(color_name)

    def __init__(self, project_name="RAGE", collector=None):
        self.project_name = project_name
        self.collector = collector
        self._metrics_block = MetricsBlock()  # Single instance for all metric rendering
        
        # NEW: Terminal manager for resize handling
        from .terminal import TerminalManager
        self.terminal = TerminalManager()
        self.terminal.on_resize(self._handle_resize)
        
        # NEW: Resize lock to prevent output corruption
        import threading
        self._resize_lock = threading.Lock()
        self._resizing = False
        
        # Use terminal manager for width detection
        self.term_width = max(self.MIN_TERM_WIDTH, self.terminal.get_size()[0])
        
        # UI Alignment Constants
        self.BAR_WIDTH = 20
        self.PCT_WIDTH = 7   # " 100% ▲" (exactly 7 columns with leading space)
        self.MARGIN_RIGHT = 10
        
        # Shared progress bar with blinking support
        self._progress_bar = ProgressBar(width=self.BAR_WIDTH)
        self._bottom_bar = BottomBar()
        
        # Track number of lines shown in last render
        self.last_line_count = 0
        
        # Spinner for animations - time-based for consistent speed
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.start_time = time.time()
        self.clear_skip_count = 0  # Skip this many clear_screen calls (set to skip initial clears)
        self.spinner_interval = 0.1  # 100ms per frame
        
        # Forward animation - filled triangle is cyan
        self.forward_chars = [
            f'{CYAN}▸{RESET}▹▹▹▹',
            f'▹{CYAN}▸{RESET}▹▹▹',
            f'▹▹{CYAN}▸{RESET}▹▹',
            f'▹▹▹{CYAN}▸{RESET}▹',
            f'▹▹▹▹{CYAN}▸{RESET}'
        ]
        self.forward_interval = 0.15  # 150ms per frame
        
        self.lines = []
    
    def refresh_width(self):
        """Refresh terminal width before building lines."""
        self.term_width = max(self.MIN_TERM_WIDTH, self.terminal.get_size()[0])
        
    def build_metrics_block(self, component_name=None, component_names=None):
        """Build metrics block using MetricsBlock class - delegates to components.py"""
        # Get metrics from collector
        cov = war = fail = err = skip = total = pass_rate = 0
        
        if component_names:
            # Aggregate from multiple components
            metrics = self._get_aggregated_metrics(component_names)
            cov, war, fail, err, skip, total, pass_rate = (
                metrics["cov"], metrics["war"], metrics["fail"],
                metrics["err"], metrics["skip"], metrics["total"], metrics["pass_rate"]
            )
        elif self.collector and component_name:
            comp = self.collector.get_component(component_name)
            if comp:
                cov = int(comp.coverage) if comp.coverage >= 0 else -1  # Preserve -1 for n/a
                war, fail, err, skip, total = comp.warnings, comp.failed, comp.errors, comp.skipped, comp.total
                pass_rate = comp.pass_rate if comp.total > 0 else 0
        
        # Delegate to MetricsBlock class (single source of truth)
        return self._metrics_block.render(cov=cov, war=war, fail=fail, err=err, skip=skip, total=total, pass_rate=pass_rate)

    def _get_aggregated_metrics(self, component_names):
        """Aggregate metrics from multiple components"""
        if not self.collector or not component_names:
            return {"cov": 0, "war": 0, "fail": 0, "err": 0, "skip": 0, "total": 0, "pass_rate": 0}
        
        total_passed = total_failed = total_errors = total_skipped = total_tests = total_warnings = 0
        total_coverage = coverage_count = 0
        
        for comp_name in component_names:
            comp = self.collector.get_component(comp_name)
            # Only aggregate if component has discovered or executed tests
            # This prevents Task Master components with 0 tests from being counted
            if comp.discovered_total > 0 or (comp.passed + comp.failed + comp.errors + comp.skipped) > 0:
                if comp.total > 0:
                    total_passed += comp.passed
                    total_failed += comp.failed
                    total_errors += comp.errors
                    total_skipped += comp.skipped
                    total_tests += comp.total
                    total_warnings += comp.warnings
                if comp.coverage is not None and comp.coverage >= 0:
                    total_coverage += comp.coverage
                    coverage_count += 1
        
        executed = total_passed + total_failed + total_errors
        pass_rate = (total_passed / executed * 100) if executed > 0 else 0
        avg_coverage = int(total_coverage / coverage_count) if coverage_count > 0 else -1  # -1 = n/a when no coverage data
        
        return {
            "cov": avg_coverage, "war": total_warnings, "fail": total_failed,
            "err": total_errors, "skip": total_skipped, "total": total_tests, "pass_rate": pass_rate
        }

    @property
    def metrics_width(self):
        """Width of metrics block - delegates to MetricsBlock"""
        return self._metrics_block.width

    MIN_TERM_WIDTH = 80

    def _truncate(self, text, max_len):
        """Truncate text to max_len with ellipsis"""
        target_len = max(max_len, 12)
        if len(text) <= target_len:
            return text
        return text[:target_len-1] + "…"
    
    def _build_aligned_row(self, left_text, left_visible_len, right_text, right_width, middle_text=None, middle_width=0, margin_right=10, mode="completed"):
        """Builds a row using anchored columns for perfect vertical alignment"""
        # Mode-specific anchoring:
        # - Complete state: flush right (term_width)
        # - Running state: safe gutter (term_width - 2) to prevent wrap
        if mode == "running":
            target_end_col = self.term_width - 2
        else:
            target_end_col = self.term_width
        
        right_start_col = target_end_col - right_width + 1
        
        if middle_text:
            # Anchor middle block
            middle_start_col = right_start_col - margin_right - middle_width
            
            # Spaces from end of left to start of middle
            p1 = middle_start_col - (left_visible_len + 1)
            # Spaces from end of middle to start of right
            p2 = right_start_col - (middle_start_col + middle_width)
            
            return f"{left_text}{' ' * max(0, p1)}{middle_text}{' ' * max(0, p2)}{right_text}"
        else:
            p = right_start_col - (left_visible_len + 1)
            return f"{left_text}{' ' * max(0, p)}{right_text}"
            
    def _format_pct(self, pct, triangle="expanded"):
        """Standardized percentage formatting: force int and fixed width (7 chars with leading space)"""
        val = int(pct)
        if triangle == "expanded":
            char = TRIANGLE_EXPANDED  # ▼ Down-pointing: content showing below
        elif triangle == "collapsed":
            char = TRIANGLE_COLLAPSED  # ▶ Right-pointing: content collapsed/hidden
        else:
            char = " "
        
        # space (1 char) + val:3% (4 chars) + space (1 char) + char (1 char) = 7 chars
        return f" {val:3}% {char}"

    def _format_right_block(self, pct, mode="running", triangle="expanded", active_count=1):
        """Creates the right-aligned status block (bar + pct)"""
        pct_text = self._format_pct(pct, triangle)
        
        if mode == "running":
            bar = self.make_progress_bar(pct, width=self.BAR_WIDTH, active_count=active_count)
            color = self.get_bar_color(pct)
            # No trailing space - the gutter is sufficient
            return f"{color}{bar}{pct_text}{RESET}", self.BAR_WIDTH + self.PCT_WIDTH
        else:
            # Complete state: just the percentage, no trailing space
            return f"{GRAY}{pct_text}{RESET}", self.PCT_WIDTH

    def _format_activity_block(self, current_test, max_width=None):
        """Standardized activity block: [ test_name ] or [ test1, test2 ]
        
        Args:
            current_test: The test name (string) or list of test names to display
            max_width: Maximum width for the entire block (including brackets). 
                       If None, no truncation is applied.
        """
        if not current_test:
            return "", 0
        
        # Handle list of tests (when collapsed)
        if isinstance(current_test, list):
            if not current_test:
                return "", 0
            # Join test names, truncate list if too many
            if len(current_test) == 1:
                test_str = current_test[0]
            elif len(current_test) <= 3:
                test_str = ", ".join(current_test)
            else:
                # Show first 2 + count
                test_str = f"{current_test[0]}, {current_test[1]}... +{len(current_test) - 2}"
            current_test = test_str
        
        # Calculate available space for test name
        # Block format: [ test_name ] -> 4 chars for brackets and spaces
        bracket_overhead = 4
        if max_width and max_width > bracket_overhead:
            max_test_len = max_width - bracket_overhead
            if len(current_test) > max_test_len:
                # Truncate with ellipsis (…)
                current_test = current_test[:max_test_len - 1] + "…"
        
        # Format based on content
        if "Initializing" in current_test:
            activity_text = f"{GRAY}{current_test}{RESET}"
        else:
            activity_text = f"{BLUE_WASHED}{current_test}{RESET}"
        
        text = f"{DIM}[{RESET} {activity_text} {DIM}]{RESET}"
        # Visible length: [ test ] -> 1 + 1 + len + 1 + 1 = 4 + len
        visible_len = len(current_test) + 4
        return text, visible_len
    
    def _get_physical_lines(self, text):
        """Estimate number of physical lines a string will take up"""
        # We strip ANSI for length calculation
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        lines = text.split('\n')
        count = 0
        effective_width = self.term_width
        for line in lines:
            stripped = ansi_escape.sub('', line)
            line_len = len(stripped)
            if line_len == 0:
                count += 1
            else:
                count += (line_len + effective_width - 1) // effective_width
        return count

    def clear_screen(self):
        """Move cursor up to start of previous block and clear"""
        # Refresh terminal width before building new frame
        old_width = self.term_width
        self.term_width = max(self.MIN_TERM_WIDTH, shutil.get_terminal_size().columns - 1)
        
        # Skip first N clears if requested (preserves discovery output)
        if self.clear_skip_count > 0:
            self.clear_skip_count -= 1
            self.lines = []
            return
        
        # Normal operation: move up and clear
        if self.last_line_count > 0:
            # Fallback to relative movement (original behavior)
            sys.stdout.write(f"\033[{self.last_line_count}F\033[J")
            sys.stdout.flush()
        self.lines = []
    
    def add_line(self, text):
        """Add a line to display"""
        self.lines.append(text.rstrip())
    
    def render(self):
        """Display all lines and track physical line usage"""
        if not self.lines:
            return
        
        # Skip rendering if resize is in progress to prevent corruption
        if self._resizing:
            return
        
        # Acquire lock to prevent resize during render
        with self._resize_lock:
            # Refresh width in case of resize (subtract 1 to prevent edge wrapping)
            self.term_width = max(self.MIN_TERM_WIDTH, self.terminal.get_size()[0] - 1)
            
            # Hide cursor during render
            sys.stdout.write("\033[?25l")
            
            full_output = "\n".join(self.lines) + "\n"
            sys.stdout.write(full_output)
            sys.stdout.flush()
            
            # Calculate physical lines for next clearing
            self.last_line_count = self._get_physical_lines(full_output.rstrip('\n'))
    
    def next_frame(self):
        """No-op: animations are now time-based"""
        pass
    
    def get_spinner(self):
        """Time-based spinner for consistent animation speed"""
        elapsed = time.time() - self.start_time
        idx = int(elapsed / self.spinner_interval) % len(self.spinner_chars)
        return self.spinner_chars[idx]
    
    def get_forward(self):
        """Time-based forward animation for consistent speed"""
        elapsed = time.time() - self.start_time
        idx = int(elapsed / self.forward_interval) % len(self.forward_chars)
        return self.forward_chars[idx]
    
    def make_progress_bar(self, pct, width=20, active_count=1):
        """Create a progress bar string with blinking blocks for active processes."""
        # Use a temporary bar if width is different from internal BAR_WIDTH
        if width != self.BAR_WIDTH:
            return ProgressBar(width=width).render(pct, active_count=active_count)
        # Use the shared ProgressBar component with blinking support
        return self._progress_bar.render(pct, active_count=active_count)
    
    def build_header(self, phase_count=1, mode="running", all_components=None):
        """Header with spinner (running) or checkmark (completed)"""
        if mode == "running":
            icon = self.get_spinner()
            # Inherit color from worst child status
            if all_components:
                color = self.get_inherited_spinner_color(component_names=all_components)
            else:
                color = YELLOW
            text = f"Running {phase_count} phase{'s' if phase_count > 1 else ''}..."
            self.add_line(f"{color}{icon}{RESET} {text}")
        else:
            icon = "✓"
            color = GREEN
            text = f"Completed {phase_count} phase{'s' if phase_count > 1 else ''}..."
            self.add_line(f"{color}{icon}{RESET} {DIM}{text}{RESET}")
    
    def build_project_line(self, active_phases=None, phase_names=None, progress_pct=0, mode="running", triangle="expanded", running_count=0, current_test=None):
        """Project line: ⠋ Project: RAGE | Phase 1, 2 and 5 more [running tests] [bar] 100% ▲"""
        phase_info = ""
        if active_phases:
            p_ids = sorted(active_phases)
            if len(p_ids) == 1:
                phase_info = f" | Phase {p_ids[0]}"
            elif len(p_ids) <= 3:
                phase_info = f" | Phase {', '.join(map(str, p_ids[:-1]))} & {p_ids[-1]}"
            else:
                # Truncate: show first 2 phases + "and N more"
                phase_info = f" | Phase {p_ids[0]}, {p_ids[1]} and {len(p_ids) - 2} more"
        
        display_name = self._truncate(f"Project: {self.project_name}{phase_info}", self.term_width // 3)
        
        # Collect all component names for status inheritance
        all_components = []
        if phase_names:
            for comps in phase_names.values():
                all_components.extend(comps)
        
        if mode == "running":
            icon = self.get_spinner()
            # Inherit color from worst child status (errors/failures)
            color = self.get_inherited_spinner_color(component_names=all_components)
            
            # When collapsed, show running tests in brackets
            if triangle == "collapsed" and current_test:
                # Calculate available width for activity block
                effective_width = self.term_width - 2
                left_visible_len = 1 + 1 + len(display_name)  # icon + sp + name
                right_total = self.BAR_WIDTH + self.PCT_WIDTH
                min_padding = 2
                available_width = effective_width - left_visible_len - right_total - min_padding - self.MARGIN_RIGHT
                available_width = max(available_width, 15)
                
                middle, middle_width = self._format_activity_block(current_test, max_width=available_width)
            else:
                middle, middle_width = None, 0
            
            left = f"{color}{icon}{RESET} {display_name}"
            left_visible = f"{icon} {display_name}"
        else:
            pct = progress_pct if progress_pct > 0 else 100
            # Aggregate metrics from all active components
            all_components = []
            if phase_names:
                for comps in phase_names.values():
                    all_components.extend(comps)
            # Pass component list for aggregated metrics display
            middle = self.build_metrics_block(component_names=all_components)
            middle_width = self.metrics_width
            left = f"{GREEN}✓{RESET} {GRAY}{display_name}{RESET}"
            left_visible = f"✓ {display_name}"
            progress_pct = pct # Use normalized pct for metrics

        # Use running_count for blinking blocks (0 at completion)
        active_for_bar = running_count if mode == "running" else 0
        right, right_width = self._format_right_block(progress_pct, mode=mode, triangle=triangle, active_count=active_for_bar)
        # Use margin=0 for tight alignment of metrics next to percentage
        line = self._build_aligned_row(left, len(left_visible), right, right_width, middle, middle_width, margin_right=0, mode=mode)
        self.add_line(line)
    
    def build_phase_line(self, phase_id, phase_name, progress_pct=0, current_test=None, mode="running", is_last=False, triangle="expanded", components=None, running_count=0):
        """Phase line: aligns with project tree"""
        tree = "└─" if is_last else "├─"
        # Don't add "Phase {id}:" prefix - phase_name already includes it
        display_name = self._truncate(phase_name, self.term_width // 3)
        
        # Get phase components for status inheritance
        phase_components = components if components else []
        
        if mode == "running":
            icon = self.get_spinner()
            # Inherit color from worst child status (errors/failures)
            color = self.get_inherited_spinner_color(component_names=phase_components)
            
            # Calculate available width for activity block
            effective_width = self.term_width - 2  # Safety gutter
            left_visible_len = 1 + 1 + 2 + 1 + len(display_name)  # icon + sp + tree + sp + name
            right_total = self.BAR_WIDTH + self.PCT_WIDTH
            min_padding = 2
            available_width = effective_width - left_visible_len - right_total - min_padding - self.MARGIN_RIGHT
            available_width = max(available_width, 15)
            
            middle, middle_width = self._format_activity_block(current_test, max_width=available_width)
            right_width = self.BAR_WIDTH + self.PCT_WIDTH
            left = f"{color}{icon}{RESET} {tree} {display_name}"
            left_visible = f"{icon} {tree} {display_name}"
        elif mode not in ["running", "completed"]:
            # Phase without active test metrics - show status text
            icon = "○"  # Circle for non-testable phases
            # Use the mode string directly (which now contains "not planned", "in development" etc from main.py)
            status_text = f"[{mode}]"
            middle = f"{GRAY}{status_text}{RESET}"
            middle_width = len(status_text)
            right_width = self.PCT_WIDTH
            left = f"{GRAY}{icon}{RESET} {GRAY}{tree} {display_name}{RESET}"
            left_visible = f"{icon} {tree} {display_name}"
            progress_pct = 0  # Force 0% for status phases
        else:
            pct = progress_pct if progress_pct > 0 else 100
            # Aggregate metrics from components in this phase
            phase_components = components if components else []
            # Pass component list for aggregated metrics display
            middle = self.build_metrics_block(component_names=phase_components)
            middle_width = self.metrics_width
            right_width = self.PCT_WIDTH
            left = f"{GREEN}✓{RESET} {GRAY}{tree} {display_name}{RESET}"
            left_visible = f"✓ {tree} {display_name}"
            progress_pct = pct

        # Use running_count for blinking blocks (0 at completion)
        active_for_bar = running_count if mode == "running" else 0
        right, right_width = self._format_right_block(progress_pct, mode=mode, triangle=triangle, active_count=active_for_bar)
        

        # Use margin=0 for tight alignment of metrics next to percentage
        line = self._build_aligned_row(left, len(left_visible), right, right_width, middle, middle_width, margin_right=0, mode=mode)
        self.add_line(line)
        
        # Separator line removed - underline extends on the phase line itself
    
    def build_component_line(self, comp_name, is_last_comp, progress_pct=0, current_test=None, 
                            mode="running", status="running", is_last_phase=False, 
                            taskmaster_status=None, display_status=None):
        """Component line: leaf node"""
        phase_continue = " " if is_last_phase else "│"
        tree = "└─" if is_last_comp else "├─"
        
        # Get component stats for inline display
        comp = self.collector.get_component(comp_name) if self.collector else None
        file_count = comp.file_count if comp else 0
        test_count = comp.test_file_count or comp.discovered_total if comp else 0
        
        # Build inline stats suffix for component name when running
        stats_suffix = ""
        if mode == "running" and (file_count > 0 or test_count > 0):
            # Add ~ prefix if counts are approximate
            prefix = "~" if (comp and comp.is_approximate) else ""
            parts = []
            if file_count > 0:
                parts.append(f"{prefix}{file_count} file{'s' if file_count != 1 else ''}")
            if test_count > 0:
                parts.append(f"{prefix}{test_count} test{'s' if test_count != 1 else ''}")
            if parts:
                stats_suffix = f": {' '.join(parts)}"
        
        # Combine component name with stats
        display_name_with_stats = f"{comp_name}{stats_suffix}"
        display_name = self._truncate(display_name_with_stats, self.term_width // 3)
        
        # Unified logic: prepare components based on mode
        # Check if we should show a status string instead of metrics
        # This occurs IF:
        # 1. status is 'taskmaster' (Phase 3)
        # 2. OR display_status is explicitly provided (Logic-based status override)
        if status == "taskmaster" or display_status:
            # Component showing status text instead of metrics
            icon = "○"  # Circle for status components
            
            # Use display_status if available (preferred), else fallback to taskmaster_status or 'not planned'
            final_status = display_status or taskmaster_status or "not planned"
            
            middle = f"{GRAY}[{final_status}]{RESET}"
            middle_width = len(f"[{final_status}]")
            left = f"{GRAY}{icon}{RESET} {GRAY}{phase_continue} {tree} {display_name}{RESET}"
            left_visible = f"{icon} {phase_continue} {tree} {display_name}"
            progress_pct = 0  # Force 0% for Task Master components
            right, right_width = self._format_right_block(progress_pct, mode="planned", triangle="none")
        elif mode == "running":
            if status == "running" or status == "complete":
                icon = self.get_spinner() if status == "running" else "✓"
            elif status == "error":
                icon = "✗"
            else:
                icon = "○"
            # Inherit color from component's own metrics (errors/failures)
            color = self.get_inherited_spinner_color(component_name=comp_name)
            
            # Calculate available width for activity block
            # Line structure: left (icon + tree + name) + padding + middle (test) + padding + right (bar + pct)
            # Running mode uses term_width - 2 for safety gutter
            effective_width = self.term_width - 2  # Safety gutter
            left_visible_len = 1 + 1 + 1 + 1 + 2 + 1 + len(display_name)  # icon + sp + │ + sp + ├─ + sp + name
            right_total = self.BAR_WIDTH + self.PCT_WIDTH  # bar (20) + pct (6)
            min_padding = 2  # Minimum 1 space on each side of middle block
            
            # Available = total - left - right - minimum padding on both sides
            available_width = effective_width - left_visible_len - right_total - min_padding - self.MARGIN_RIGHT
            
            # Ensure reasonable minimum
            available_width = max(available_width, 15)
            
            middle, middle_width = self._format_activity_block(current_test, max_width=available_width)
            left = f"{color}{icon}{RESET} {phase_continue} {tree} {display_name}"
            left_visible = f"{icon} {phase_continue} {tree} {display_name}"
            right, right_width = self._format_right_block(progress_pct, mode=mode, triangle="none")
        else:
            pct = progress_pct if progress_pct > 0 else 100
            middle = self.build_metrics_block(component_name=comp_name)
            middle_width = self.metrics_width
            left = f"{GREEN}✓{RESET} {GRAY}{phase_continue} {tree} {display_name}{RESET}"
            left_visible = f"✓ {phase_continue} {tree} {display_name}"
            progress_pct = pct
            right, right_width = self._format_right_block(progress_pct, mode=mode, triangle="none")
        
        # Build aligned row
        # For taskmaster, right block was already created above with right_width set
        if status != "taskmaster":
            right, right_width = self._format_right_block(progress_pct, mode=mode, triangle="none")
        
        # Use margin=0 for tight alignment of metrics next to percentage
        line = self._build_aligned_row(left, len(left_visible), right, right_width, middle, middle_width, margin_right=0, mode=mode if status != "taskmaster" else "planned")
        self.add_line(line)
    
    def build_bottom_bar(self, progress_pct=0, mode="running", active_count=1):
        """Full-width progress bar with blinking blocks for active processes."""
        w = self.term_width
        
        # Use BottomBar component for blinking support
        bar = self._bottom_bar.render(
            progress_pct, 
            w, 
            color=CYAN, 
            active_count=active_count
        )
        self.add_line(bar)


def demo_final_layout():
    """Demo showing the requested layout with real RAGE project data"""
    display = ProgressiveDisplay("RAGE")
    
    # Real data from check_project_status.py
    phase_names = {
        1: "Architecture & Foundation",
        2: "Core Backend Services",
        5: "Enterprise Scale",
        7: "Global Federation"
    }
    active_phases_live = [1, 2, 5, 7]
    
    # Simulate animated progress
    for progress in range(0, 101, 10):
        display.clear_screen()
        display.next_frame()
        
        # Consistent phase count (4 phases)
        display.build_header(phase_count=len(active_phases_live), mode="running")
        
        # Project line correctly shows Phase 1, 2, 5 & 7
        display.build_project_line(active_phases=active_phases_live, progress_pct=progress, mode="running")
        
        # Phase 1 detail (Complete)
        display.build_phase_line(1, phase_names[1], progress_pct=100, mode="running", is_last=False)
        display.build_component_line("acl", False, progress_pct=100, status="complete", is_last_phase=False)
        display.build_component_line("contracts", False, progress_pct=100, status="complete", is_last_phase=False)
        display.build_component_line("observability", True, progress_pct=100, status="complete", is_last_phase=False)
        
        # Phase 2 detail (In Progress)
        display.build_phase_line(2, phase_names[2], progress_pct=progress, mode="running", is_last=False)
        display.build_component_line("rag_core", False, progress_pct=progress, status="running", is_last_phase=False)
        display.build_component_line("search_engine", False, progress_pct=0, status="pending", is_last_phase=False)
        display.build_component_line("identity_mapping", True, progress_pct=0, status="pending", is_last_phase=False)
        
        # Future phases
        display.build_phase_line(5, phase_names[5], progress_pct=0, mode="running", is_last=False)
        display.build_phase_line(7, phase_names[7], progress_pct=0, mode="running", is_last=True)
        
        display.build_bottom_bar(progress, "running")
        display.render()
        time.sleep(0.1)

    time.sleep(0.5)
    
    # Completion state
    display.clear_screen()
    display.build_header(phase_count=len(active_phases_live), mode="completed")
    # Project: 90% (Orange washed)
    display.build_project_line(active_phases=active_phases_live, progress_pct=90, mode="completed")
    
    # Phase 1: 100% (Green washed)
    display.build_phase_line(1, phase_names[1], progress_pct=100, mode="completed", is_last=False)
    display.build_component_line("acl", False, progress_pct=100, mode="completed", is_last_phase=False)
    display.build_component_line("contracts", False, progress_pct=100, mode="completed", is_last_phase=False)
    display.build_component_line("observability", True, progress_pct=100, mode="completed", is_last_phase=False)
    
    # Phase 2: 85% (Orange washed)
    display.build_phase_line(2, phase_names[2], progress_pct=85, mode="completed", is_last=False)
    display.build_component_line("rag_core", False, progress_pct=100, mode="completed", is_last_phase=False)
    display.build_component_line("search_engine", False, progress_pct=80, mode="completed", is_last_phase=False)
    display.build_component_line("identity_mapping", True, progress_pct=75, mode="completed", is_last_phase=False)

    # Future phases: 0% and 100% mix
    display.build_phase_line(5, phase_names[5], progress_pct=0, mode="completed", is_last=False)
    display.build_phase_line(7, phase_names[7], progress_pct=100, mode="completed", is_last=True)
    
    display.build_bottom_bar(mode="completed")
    display.render()


if __name__ == "__main__":
    demo_final_layout()

    def _get_aggregated_metrics(self, component_names):
        """Aggregate metrics from multiple components"""
        if not self.collector or not component_names:
            return {"fail": 0, "err": 0, "total": 0, "pass_rate": 100}
        
        total_passed = 0
        total_failed = 0
        total_errors = 0
        total_tests = 0
        
        for comp_name in component_names:
            comp = self.collector.get_component(comp_name)
            if comp.total > 0:
                total_passed += comp.passed
                total_failed += comp.failed
                total_errors += comp.errors
                total_tests += comp.total
        
        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 100
        
        return {
            "fail": total_failed,
            "err": total_errors,
            "total": total_tests,
            "pass_rate": pass_rate
        }
