"""Beautiful Unicode Braille chart for thread utilization visualization.

Displays two charts:
1. Real-time: Last 60 seconds (sliding window)
2. Full timeline: Entire execution from start to finish
"""

import time
from collections import deque
from typing import Dict, List, Literal
from dataclasses import dataclass
from enum import Enum


class OperationType(Enum):
    """Types of operations that consume threads."""
    DISCOVERY = "discovery"
    EXECUTION = "execution"
    AI_ANALYSIS = "ai"
    AUTO_FIX = "fix"
    CACHE = "cache"


@dataclass
class DataPoint:
    """Single data point for thread utilization."""
    timestamp: float
    active_threads: int
    operation_type: OperationType


class ThreadChartRenderer:
    """Renders beautiful Unicode Braille charts for thread utilization."""
    
    # Braille Unicode patterns for smooth curves (8 levels of intensity)
    BRAILLE_CHARS = [
        ' ', '⠁', '⠃', '⠇', '⠏', '⠟', '⠿', '⣿'
    ]
    
    # ANSI color codes
    COLORS = {
        OperationType.DISCOVERY: '\033[34m',    # Blue
        OperationType.EXECUTION: '\033[32m',    # Green
        OperationType.AI_ANALYSIS: '\033[33m',  # Yellow
        OperationType.AUTO_FIX: '\033[38;5;208m',  # Orange
        OperationType.CACHE: '\033[36m',        # Cyan
    }
    RESET = '\033[0m'
    
    def __init__(self, max_threads: int = 12, terminal_width: int = 80):
        """Initialize chart renderer.
        
        Args:
            max_threads: Maximum number of threads
            terminal_width: Width of terminal in characters
        """
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.chart_width = terminal_width - 20  # Leave space for borders/labels
        
        # Real-time data (60 second window)
        self.realtime_data = deque(maxlen=self.chart_width)
        
        # Full timeline data (entire execution)
        self.full_timeline_data: List[DataPoint] = []
        
        self.start_time = time.time()
    
    def add_data_point(self, active_threads: int, operation_type: OperationType):
        """Add a data point to both charts.
        
        Args:
            active_threads: Number of threads currently active
            operation_type: Type of operation being performed
        """
        point = DataPoint(
            timestamp=time.time(),
            active_threads=active_threads,
            operation_type=operation_type
        )
        
        # Add to real-time (auto-truncates to maxlen)
        self.realtime_data.append(point)
        
        # Add to full timeline
        self.full_timeline_data.append(point)
    
    def _get_braille_char(self, value: float, max_value: float) -> str:
        """Convert value to Braille character for smooth visualization.
        
        Args:
            value: Current value
            max_value: Maximum value for normalization
        
        Returns:
            Unicode Braille character
        """
        if value <= 0:
            return ' '
        
        ratio = min(value / max_value, 1.0)
        index = int(ratio * (len(self.BRAILLE_CHARS) - 1))
        return self.BRAILLE_CHARS[index]
    
    def render_realtime_chart(self) -> str:
        """Render real-time 60-second chart.
        
        Returns:
            Formatted chart string with ANSI colors
        """
        lines = []
        
        # Header
        lines.append("╭─ Thread Utilization (Real-time) " + "─" * (self.chart_width - 15) + "╮")
        lines.append("│" + " " * 20 + "<<<    Last 60 seconds    >>>" + " " * (self.chart_width - 30) + "│")
        lines.append("│" + " " * self.terminal_width + "│")
        
        # Chart data (12 rows for thread levels)
        for thread_level in range(self.max_threads, 0, -2):
            line = f"│ {thread_level:2d} ┃"
            
            for point in self.realtime_data:
                char = self._get_braille_char(point.active_threads, self.max_threads)
                color = self.COLORS.get(point.operation_type, self.RESET)
                line += color + char + self.RESET
            
            # Pad if not enough data yet
            padding = self.chart_width - len(self.realtime_data)
            line += " " * padding + "┃ │"
            lines.append(line)
        
        # X-axis with time markers
        elapsed = time.time() - self.start_time
        time_markers = "│      ┗━━"
        for i in range(0, 61, 5):
            time_markers += f"┳{'━' * 4}"
        time_markers += "┳━━┛ │"
        lines.append(time_markers)
        
        # Time labels
        time_labels = "│         "
        for i in range(0, 61, 5):
            time_labels += f"{i:2d}s  "
        lines.append(time_labels + "    │")
        
        # Legend
        avg_threads = sum(p.active_threads for p in self.realtime_data) / max(len(self.realtime_data), 1)
        legend = (
            "│      "
            f"{self.COLORS[OperationType.DISCOVERY]}Discovery{self.RESET}  "
            f"{self.COLORS[OperationType.EXECUTION]}Execution{self.RESET}  "
            f"{self.COLORS[OperationType.AI_ANALYSIS]}AI Analysis{self.RESET}  "
            f"{self.COLORS[OperationType.AUTO_FIX]}Auto-Fix{self.RESET}      "
            f"[Avg: {avg_threads:.1f} threads]   │"
        )
        lines.append(legend)
        
        # Footer
        lines.append("╰" + "─" * (self.terminal_width - 2) + "╯")
        
        return '\n'.join(lines)
    
    def render_full_timeline_chart(self) -> str:
        """Render full execution timeline chart.
        
        Returns:
            Formatted chart string showing entire test run
        """
        if not self.full_timeline_data:
            return ""
        
        lines = []
        
        # Downsample data to fit chart width
        downsampled = self._downsample_data(self.full_timeline_data, self.chart_width)
        
        # Header
        total_time = time.time() - self.start_time
        lines.append("╭─ Thread Utilization (Full Timeline) " + "─" * (self.chart_width - 20) + "╮")
        lines.append(f"│{' ' * 20}<<<    Total: {total_time:.1f}s    >>>" + " " * (self.chart_width - 30) + "│")
        lines.append("│" + " " * self.terminal_width + "│")
        
        # Chart data
        for thread_level in range(self.max_threads, 0, -2):
            line = f"│ {thread_level:2d} ┃"
            
            for point in downsampled:
                char = self._get_braille_char(point.active_threads, self.max_threads)
                color = self.COLORS.get(point.operation_type, self.RESET)
                line += color + char + self.RESET
            
            line += "┃ │"
            lines.append(line)
        
        # X-axis
        lines.append("│      ┗━━" + "┳━━━━" * 12 + "┳━━┛ │")
        
        # Time labels (evenly distributed)
        time_labels = "│         "
        for i in range(0, int(total_time) + 1, max(int(total_time) // 12, 1)):
            time_labels += f"{i:3d}s "
        lines.append(time_labels + "     │")
        
        # Footer
        lines.append("╰" + "─" * (self.terminal_width - 2) + "╯")
        
        return '\n'.join(lines)
    
    def _downsample_data(self, data: List[DataPoint], target_width: int) -> List[DataPoint]:
        """Downsample data to fit target width.
        
        Args:
            data: Full data list
            target_width: Target number of points
        
        Returns:
            Downsampled data
        """
        if len(data) <= target_width:
            return data
        
        # Simple averaging downsampling
        step = len(data) / target_width
        downsampled = []
        
        for i in range(target_width):
            start_idx = int(i * step)
            end_idx = int((i + 1) * step)
            chunk = data[start_idx:end_idx]
            
            if chunk:
                # Average active threads, take most common operation type
                avg_threads = sum(p.active_threads for p in chunk) // len(chunk)
                most_common_op = max(set(p.operation_type for p in chunk), 
                                   key=lambda x: sum(1 for p in chunk if p.operation_type == x))
                
                downsampled.append(DataPoint(
                    timestamp=chunk[0].timestamp,
                    active_threads=avg_threads,
                    operation_type=most_common_op
                ))
        
        return downsampled
    
    def render_both_charts(self) -> str:
        """Render both charts stacked vertically.
        
        Returns:
            Both charts separated by newline
        """
        return self.render_realtime_chart() + "\n\n" + self.render_full_timeline_chart()
