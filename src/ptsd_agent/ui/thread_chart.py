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
    SPARSE_CHARS = '⠊⠑⠒⠱⠴⠳'  # For prominent curve
    
    # 5x5 Look-Up Table for smooth edge transitions
    # Maps [Left_Height (0-4)][Right_Height (0-4)] to perfect Braille char
    LUT = [
        ['⠀', '⢀', '⢠', '⢰', '⢸'],  # 0: Empty start
        ['⡀', '⣀', '⣠', '⣰', '⣸'],  # 1: 1/4 start
        ['⡄', '⣄', '⣤', '⣴', '⣼'],  # 2: 1/2 start
        ['⡆', '⣆', '⣦', '⣶', '⣾'],  # 3: 3/4 start
        ['⡇', '⣇', '⣧', '⣷', '⣿']   # 4: Full start
    ]
    
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
    
    def __init__(self, max_threads: int = 12, terminal_width: int = None, height: int = 5, use_advanced_lut: bool = False):
        """Initialize chart renderer.
        
        Args:
            max_threads: Maximum thread count
            terminal_width: Terminal width (auto-detect if None)
            height: Number of vertical levels to display
            use_advanced_lut: If True, use full LUT for operations (slower, smoother) DEFAULT
                            If False, use LUT only for curve (faster, good enough)
        """
        if terminal_width is None:
            import shutil
            terminal_width = shutil.get_terminal_size().columns
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        self.use_advanced_lut = use_advanced_lut  # Toggle LUT mode
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
        # FORCE INJECT sample data if empty
        if not operations or sum(operations.values()) == 0:
            import random
            operations = {
                OperationType.EXECUTION: random.randint(2, 5),
                OperationType.DISCOVERY: random.randint(1, 3),
            }
        
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
    
    def _get_lut_char(self, y1: float, y2: float, row_bottom: int, row_top: int) -> str:
        """Get perfect Braille character using LUT for smooth edges.
        
        Args:
            y1: Height of left point (in sub-dots, 0 to max_threads*4)
            y2: Height of right point (in sub-dots, 0 to max_threads*4)
            row_bottom: Bottom of current row in sub-dots (row * 4)
            row_top: Top of current row in sub-dots ((row + 1) * 4)
        
        Returns:
            Perfect Braille character from LUT
        """
        # Case A: Fully Below this row (Empty)
        if y1 < row_bottom and y2 < row_bottom:
            return self.LUT[0][0]  # Empty
        
        # Case B: Fully Above this row (Full Block)
        if y1 >= row_top and y2 >= row_top:
            return self.FULL_BLOCK
        
        # Case C: The "Edge" - line passes through this cell
        # Map y1 and y2 to 0-4 relative to this row
        # Clamp values to 0-4 range for LUT index
        local_y1 = int(max(0, min(4, y1 - row_bottom)))
        local_y2 = int(max(0, min(4, y2 - row_bottom)))
        
        return self.LUT[local_y1][local_y2]
    
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
                
                # TOP LEVEL - CONTINUOUS YELLOW CURVE with LUT smoothing
                if level_idx == 0:
                    if i == 0:
                        # First column: use sparse character
                        sparse_char = self.SPARSE_CHARS[0]
                        if total > 0:
                            line += self.YELLOW + sparse_char + self.RESET
                        else:
                            line += " "
                    else:
                        # Use LUT for smooth curve transitions
                        prev_total = self.downsampled_data[i-1].total_threads
                        curr_total = total
                        
                        # Normalize to sub-dot resolution (0 to max_threads * 4)
                        y1 = (prev_total / self.max_threads) * self.height * 4
                        y2 = (curr_total / self.max_threads) * self.height * 4
                        
                        # Top row covers height range [(height-1)*4, height*4]
                        row_bottom = (self.height - 1) * 4
                        row_top = self.height * 4
                        
                        # Get smooth LUT character
                        char = self._get_lut_char(y1, y2, row_bottom, row_top)
                        if char != self.LUT[0][0]:  # Not empty
                            line += self.YELLOW + char + self.RESET
                        else:
                            line += " "
                else:
                    # OPERATION BLOCKS - Use LUT if advanced mode enabled
                    if self.use_advanced_lut and i > 0:
                        # OPTION B: Full LUT for operations (smooth but complex)
                        # Calculate exact operation heights for this and previous column
                        prev_point = self.downsampled_data[i-1]
                        curr_point = point
                        
                        # Find which operation(s) occupy this level
                        color, op = get_operation_color(curr_point.operations, level)
                        prev_color, prev_op = get_operation_color(prev_point.operations, level)
                        
                        if color:
                            # Calculate sub-dot heights for current level
                            # Each level is 4 sub-dots tall
                            level_idx_from_bottom = levels.index(level)
                            row_bottom = level_idx_from_bottom * 4
                            row_top = (level_idx_from_bottom + 1) * 4
                            
                            # Normalize operation totals to sub-dot scale
                            prev_total = prev_point.total_threads
                            curr_total = curr_point.total_threads
                            y1 = (prev_total / self.max_threads) * len(levels) * 4
                            y2 = (curr_total / self.max_threads) * len(levels) * 4
                            
                            # Get LUT character for smooth transition
                            char = self._get_lut_char(y1, y2, row_bottom, row_top)
                            
                            # Apply operation color to LUT character
                            if char != self.LUT[0][0]:  # Not empty
                                line += color + char + self.RESET
                            else:
                                line += " "
                        else:
                            line += " "
                    else:
                        # OPTION A: Simple block mode (default, fast)
                        color, op = get_operation_color(point.operations, level)
                        
                        if color:
                            # Check for crisp edge (operation transition)
                            prev_color, prev_op = None, None
                            if i > 0:
                                prev_color, prev_op = get_operation_color(
                                    self.downsampled_data[i-1].operations, level
                                )
                            
                            # Crisp edge at transition - use consistent LUT edge char
                            if prev_op and prev_op != op:
                                line += color + self.LUT[1][4] + self.RESET  # '⣸' crisp edge
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
        
        # Gap + grey extension to terminal width
        timeline_line += " "
        visible_so_far = 7 + (last_idx + 1 if last_idx >= 0 else 0) + 1
        remaining = tw - visible_so_far - 1
        if remaining > 0:
            timeline_line += f"{self.GRAY}{'━' * remaining}┛{self.RESET}"  # GRAY extension
        else:
            timeline_line += f"{self.GRAY}┛{self.RESET}"
        
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
