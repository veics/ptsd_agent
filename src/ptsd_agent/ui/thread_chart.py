"""Stacked horizontal colored blocks showing parallel operations.

Each block colored by its own operation type - multiple operations
stack vertically with different colors.
"""

import time
from typing import List, Dict
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
    """Renders chart with horizontally colored stacked blocks."""
    
    # Very sparse patterns (1-3 dots) for curve line
    SPARSE_CURVE = ['⠀', '⠁', '⠂', '⠃', '⠄', '⠅', '⠆', '⠇']
    
    # Dense block
    DENSE_BLOCK = '⣿'
    
    # Foreground colors
    FG_COLORS = {
        OperationType.DISCOVERY: '\033[38;5;110m',
        OperationType.EXECUTION: '\033[38;5;108m',
        OperationType.AI_ANALYSIS: '\033[38;5;180m',
        OperationType.AUTO_FIX: '\033[38;5;174m',
        OperationType.CACHE: '\033[38;5;109m',
    }
    
    RESET = '\033[0m'
    GRAY = '\033[38;5;240m'
    
    def __init__(self, max_threads: int = 12, terminal_width: int = 80, height: int = 5):
        """Initialize chart renderer."""
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        self.chart_width = terminal_width - 8
        
        self.timeline_data: List[DataPoint] = []
        self.start_time = time.time()
    
    def add_data_point(self, operations: Dict[OperationType, int]):
        """Add data point."""
        point = DataPoint(
            timestamp=time.time(),
            operations=operations
        )
        self.timeline_data.append(point)
    
    def _get_sparse_curve_char(self, value: float) -> str:
        """Get sparse curve character."""
        if value <= 0:
            return self.SPARSE_CURVE[0]
        
        ratio = min(value / self.max_threads, 1.0)
        idx = int(ratio * (len(self.SPARSE_CURVE) - 1))
        return self.SPARSE_CURVE[idx]
    
    def _is_curve_level(self, level_idx: int, total_levels: int, point_value: float) -> bool:
        """Check if curve should be drawn at this level."""
        threads_per_level = self.max_threads / total_levels
        level_max = (level_idx + 1) * threads_per_level  
        level_min = level_idx * threads_per_level
        
        return level_min <= point_value < level_max
    
    def render(self) -> str:
        """Render sparse curve with horizontally colored stacked blocks."""
        if not self.timeline_data:
            return ""
        
        downsampled = self._downsample_data(self.timeline_data, self.chart_width)
        
        lines = []
        threads_per_level = self.max_threads / self.height
        
        # Render from top to bottom
        for level_idx in range(self.height - 1, -1, -1):
            level_max = (level_idx + 1) * threads_per_level
            level_min = level_idx * threads_per_level
            
            # Y-axis label
            if level_idx == self.height - 1:
                label = f"{self.GRAY}{int(self.max_threads):3d} ┃{self.RESET}"
            elif level_idx == 0:
                label = f"{self.GRAY}0.0 ┃{self.RESET}"
            else:
                label = f"{self.GRAY} {int(level_max):2d} ┃{self.RESET}"
            
            line = label + " "
            
            for point in downsampled:
                # Check if sparse curve should be drawn here
                if self._is_curve_level(level_idx, self.height, point.total_threads):
                    # Draw sparse curve dot
                    dot = self._get_sparse_curve_char(point.total_threads)
                    if point.operations:
                        dominant_op = max(point.operations.items(), key=lambda x: x[1])[0]
                        color = self.FG_COLORS.get(dominant_op, '')
                        line += color + dot + self.RESET
                    else:
                        line += dot
                else:
                    # Find which operation(s) contribute to this level
                    # Sort by thread count to stack properly
                    drawn = False
                    cumulative_threads = 0
                    
                    for op_type, thread_count in sorted(point.operations.items(), 
                                                       key=lambda x: x[1], reverse=True):
                        op_starts = cumulative_threads
                        op_ends = cumulative_threads + thread_count
                        cumulative_threads = op_ends
                        
                        # Check if this operation occupies this level
                        if op_starts < level_max and op_ends > level_min:
                            # This operation's block is at this level - color it!
                            color = self.FG_COLORS.get(op_type, '')
                            line += color + self.DENSE_BLOCK + self.RESET
                            drawn = True
                            break
                    
                    if not drawn:
                        line += ' '
            
            lines.append(line)
        
        # Timeline axis
        timeline_line = f"{self.GRAY}    ┗━━{self.RESET}"
        
        for point in downsampled:
            if point.operations:
                dominant_op = max(point.operations.items(), key=lambda x: x[1])[0]
                color = self.FG_COLORS.get(dominant_op, '')
                timeline_line += color + "⠒" + self.RESET
            else:
                timeline_line += " "
        
        timeline_line += self.GRAY + "┛" + self.RESET
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
