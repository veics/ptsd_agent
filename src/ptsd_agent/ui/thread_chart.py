"""Thread chart with Braille-based visualization.

Version 1: Curve with spacing above bands for clarity.
Clear separation between curve line and colored bands.
"""

import time
import math
from typing import List, Dict, Optional
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
    """Single data point with multiple parallel operations."""
    timestamp: float
    operations: Dict[OperationType, int]
    
    @property
    def total_threads(self) -> int:
        return sum(self.operations.values())


class ThreadChartRenderer:
    """Version 1: Spaced curve above bands."""
    
    # Braille characters
    FULL_BLOCK = '⣿'  # Dense 8-dot block
    EDGE_CHAR = '⣸'  # Crisp edge (partial dots)
    SPARSE_CHARS = '⠊⠑⠒⠱⠴⠳'  # For prominent curve
    
    # Colors
    YELLOW = '\033[38;5;180m'  # Prominent curve color
    GREEN = '\033[38;5;108m'   # Timeline progress
    FADED_GREEN = '\033[38;5;65m'  # Blinking timeline
    FG_COLORS = {
        OperationType.DISCOVERY: '\033[38;5;110m',    # Blue
        OperationType.EXECUTION: '\033[38;5;108m',    # Green  
        OperationType.AI_ANALYSIS: '\033[38;5;180m',  # Yellow
        OperationType.AUTO_FIX: '\033[38;5;174m',     # Red
        OperationType.CACHE: '\033[38;5;109m',        # Cyan
    }
    
    RESET = '\033[0m'
    GRAY = '\033[38;5;240m'
    
    # Curve spacing removed - not needed for new design
    
    def __init__(self, max_threads: int = 12, terminal_width: int = None, height: int = 5):
        """Initialize chart renderer."""
        if terminal_width is None:
            import shutil
            terminal_width = shutil.get_terminal_size().columns
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        # Y-axis: "  12 ┃" = 5 chars
        self.chart_width = terminal_width - 5
        
        self.timeline_data: List[DataPoint] = []
        self.start_time = time.time()
        self.downsampled_data: List[DataPoint] = []
        self.frame_count = 0  # For blinking timeline
        
        # No initial empty data point - let it build naturally
    
    def _log_scale(self, value: float) -> float:
        """Convert thread count to logarithmic scale.
        
        Uses log2(value + 1) to handle 0 gracefully and make
        small values (1-4) more visible.
        """
        if value <= 0:
            return 0
        return math.log2(value + 1)
    
    def _inverse_log_scale(self, log_value: float) -> float:
        """Convert logarithmic scale back to thread count."""
        if log_value <= 0:
            return 0
        return (2 ** log_value) - 1
    
    def add_data_point(self, operations: Dict[OperationType, int]):
        """Add data point."""
        point = DataPoint(
            timestamp=time.time(),
            operations=operations
        )
        self.timeline_data.append(point)
    
    def _get_prominent_curve_char(self, value: float) -> str:
        """Get prominent curve character."""
        if value <= 0:
            return self.PROMINENT_CURVE[0]
        
        ratio = min(value / self.max_threads, 1.0)
        idx = int(ratio * (len(self.PROMINENT_CURVE) - 1))
        return self.PROMINENT_CURVE[idx]
    
    def _get_curve_level(self, point_value: float) -> int:
        """Get which level the curve is at (using logarithmic scale)."""
        if point_value <= 0:
            return -1
        
        max_log = self._log_scale(self.max_threads)
        value_log = self._log_scale(point_value)
        
        log_per_level = max_log / self.height
        level = int(value_log / log_per_level)
        return min(level, self.height - 1)
    
    def _get_band_max_level(self, point_value: float) -> float:
        """Get maximum level for bands (with spacing below curve) using log scale."""
        if point_value <= 0:
            return 0
        
        # Subtract spacing in thread count, then convert to log
        adjusted_value = max(0, point_value - self.CURVE_SPACING)
        return self._log_scale(adjusted_value)
    
    def _is_connecting_line(self, level_idx: int, col_idx: int) -> Optional[str]:
        """Check if we should draw a connecting line."""
        if col_idx >= len(self.downsampled_data):
            return None
        
        curr_point = self.downsampled_data[col_idx]
        curr_level = self._get_curve_level(curr_point.total_threads)
        
        if col_idx > 0:
            prev_point = self.downsampled_data[col_idx - 1]
            prev_level = self._get_curve_level(prev_point.total_threads)
            
            if prev_level == curr_level == level_idx:
                if curr_point.operations:
                    dominant_op = max(curr_point.operations.items(), key=lambda x: x[1])[0]
                    return self.FG_COLORS.get(dominant_op, '') + self.CONNECTIONS[0] + self.RESET
        
        return None
    
    
    def render(self) -> str:
        """Render chart with finalized design: yellow curve, colored blocks, crisp edges."""
        if not self.timeline_data:
            return ""
        
        # Downsample to fit chart width
        self.downsampled_data = self._downsample_data(self.timeline_data, self.chart_width)
        
        if not self.downsampled_data:
            return ""
        
        self.frame_count += 1  # For blinking effect
        
        lines = []
        
        # Define 5 levels
        levels = [12, 9, 6, 3, 1]
        
        # Helper function to get operation color at specific level
        def get_operation_color(operations: Dict[OperationType, int], level: int):
            """Get color for operation at this level (stacked bottom-up)."""
            cumulative = 0
            for op_type in [OperationType.DISCOVERY, OperationType.EXECUTION,
                           OperationType.AI_ANALYSIS, OperationType.AUTO_FIX, OperationType.CACHE]:
                if op_type not in operations:
                    continue
                count = operations[op_type]
                bottom = cumulative
                top = cumulative + count
                cumulative += count
                
                # Level within this operation's range?
                if level <= top and level > bottom:
                    return self.FG_COLORS.get(op_type, ''), op_type
            return None, None
        
        # Render each level (top to bottom)
        for level_idx, level in enumerate(levels):
            # Y-axis label (numbers GRAY, border GREEN)
            if level >= 10:
                label = f"{self.GRAY}{level:3d} {self.GREEN}┃{self.RESET}"
            else:
                label = f"{self.GRAY}  {level} {self.GREEN}┃{self.RESET}"
            line = label
            
            # Render each column
            for i, point in enumerate(self.downsampled_data):
                total = point.total_threads
                
                if total == 0:
                    line += " "
                    continue
                
                # TOP LEVEL - CONTINUOUS YELLOW CURVE
                if level_idx == 0:
                    sparse_char = self.SPARSE_CHARS[i % len(self.SPARSE_CHARS)]
                    if total > 0:
                        line += self.YELLOW + sparse_char + self.RESET
                    else:
                        line += " "
                else:
                    # Get color for this level
                    color, op = get_operation_color(point.operations, level)
                    
                    if color:
                        # Check for crisp edge (operation transition)
                        prev_color, prev_op = None, None
                        if i > 0:
                            prev_color, prev_op = get_operation_color(
                                self.downsampled_data[i-1].operations, level
                            )
                        
                        # Crisp edge at transition
                        if prev_op and prev_op != op:
                            line += color + self.EDGE_CHAR + self.RESET
                        else:
                            # Full block
                            line += color + self.FULL_BLOCK + self.RESET
                    else:
                        line += " "
            
            lines.append(line)
        
        # GREEN TIMELINE with BLINKING
        import shutil
        tw = shutil.get_terminal_size().columns
        
        # Find lust data point
        last_idx = -1
        for i in range(len(self.downsampled_data) - 1, -1, -1):
            if self.downsampled_data[i].total_threads > 0:
                last_idx = i
                break
        
        timeline_line = f"{self.GRAY}    {self.GREEN}┗━━{self.RESET}"
        
        # GREEN progress
        for i in range(len(self.downsampled_data)):
            if i < last_idx:
                # Solid green
                timeline_line += f"{self.GREEN}━{self.RESET}"
            elif i == last_idx:
                # BLINK: washed green ↔ grey (slower: every 4 frames)
                if self.frame_count % 4 < 2:
                    timeline_line += f"{self.FADED_GREEN}━{self.RESET}"
                else:
                    timeline_line += f"{self.GRAY}━{self.RESET}"
        
        # Gap + grey to terminal width
        timeline_line += " "
        visible_so_far = 7 + (last_idx + 1 if last_idx >= 0 else 0) + 1
        remaining = tw - visible_so_far - 1
        if remaining > 0:
            timeline_line += f"{self.GREEN}{'━' * remaining}┛{self.RESET}"
        else:
            timeline_line += f"{self.GREEN}┛{self.RESET}"
        
        lines.append(timeline_line)
        
        # Time labels
        total_time = time.time() - self.start_time
        tick_interval = max(int(self.chart_width / 8), 8)
        
        time_labels = "      "
        for i in range(0, self.chart_width, tick_interval):
            time_sec = int((i / self.chart_width) * total_time)
            time_labels += f"{self.GRAY}{time_sec:02d}     {self.RESET}"
        
        lines.append(time_labels)
        
        return '\n'.join(lines)
    
    def render_realtime_chart(self) -> str:
        return self.render()
    
    def _downsample_data(self, data: List[DataPoint], target_width: int) -> List[DataPoint]:
        """Downsample data."""
        if len(data) <= target_width:
            padding = target_width - len(data)
            return list(data) + [DataPoint(0, {}) for _ in range(padding)]
        
        step = len(data) / target_width
        downsampled = []
        
        for i in range(target_width):
            start_idx = int(i * step)
            end_idx = int((i + 1) * step)
            chunk = data[start_idx:end_idx]
            
            if chunk:
                agg_ops: Dict[OperationType, int] = {}
                for point in chunk:
                    for op_type, threads in point.operations.items():
                        agg_ops[op_type] = agg_ops.get(op_type, 0) + threads
                
                for op_type in agg_ops:
                    agg_ops[op_type] //= len(chunk)
                
                downsampled.append(DataPoint(
                    timestamp=chunk[0].timestamp,
                    operations=agg_ops
                ))
        
        return downsampled
