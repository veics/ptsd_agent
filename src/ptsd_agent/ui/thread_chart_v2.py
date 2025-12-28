"""Version 2: Sparse dot line floating on top.

Simple sparse Braille dots forming a line above colored bands.
"""

import time
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


class ThreadChartRendererV2:
    """Version 2: Sparse dot line on top."""
    
    # Very sparse dots for line
    SPARSE_DOTS = ['⠀', '⠁', '⠂', '⠃', '⠄', '⠅', '⠆', '⠇']
    
    # Connection line
    CONNECTION = '⠤'
    
    # Dense block
    DENSE_BLOCK = '⣿'
    
    # Gray for baseline
    GRAY_FILLED = '\033[38;5;240m'
    
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
        self.downsampled_data: List[DataPoint] = []
    
    def add_data_point(self, operations: Dict[OperationType, int]):
        """Add data point."""
        point = DataPoint(
            timestamp=time.time(),
            operations=operations
        )
        self.timeline_data.append(point)
    
    def _get_sparse_dot(self, value: float) -> str:
        """Get sparse dot."""
        if value <= 0:
            return self.SPARSE_DOTS[0]
        
        ratio = min(value / self.max_threads, 1.0)
        idx = int(ratio * (len(self.SPARSE_DOTS) - 1))
        return self.SPARSE_DOTS[idx]
    
    def _get_curve_level(self, point_value: float) -> int:
        """Get which level the curve is at."""
        if point_value <= 0:
            return -1
        
        threads_per_level = self.max_threads / self.height
        level = int(point_value / threads_per_level)
        return min(level, self.height - 1)
    
    def _is_connecting_line(self, level_idx: int, col_idx: int) -> bool:
        """Check if connecting line between dots."""
        if col_idx >= len(self.downsampled_data) or col_idx == 0:
            return False
        
        curr_level = self._get_curve_level(self.downsampled_data[col_idx].total_threads)
        prev_level = self._get_curve_level(self.downsampled_data[col_idx - 1].total_threads)
        
        return prev_level == curr_level == level_idx
    
    def render(self) -> str:
        """Render chart with sparse dot line."""
        if not self.timeline_data:
            return ""
        
        self.downsampled_data = self._downsample_data(self.timeline_data, self.chart_width)
        
        lines = []
        threads_per_level = self.max_threads / self.height
        
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
            
            for col_idx, point in enumerate(self.downsampled_data):
                curve_level = self._get_curve_level(point.total_threads)
                
                # Check if sparse dot should be drawn
                if curve_level == level_idx:
                    dot = self._get_sparse_dot(point.total_threads)
                    if point.operations:
                        dominant_op = max(point.operations.items(), key=lambda x: x[1])[0]
                        color = self.FG_COLORS.get(dominant_op, '')
                        line += color + dot + self.RESET
                    else:
                        line += dot
                elif self._is_connecting_line(level_idx, col_idx):
                    # Draw connection
                    if point.operations:
                        dominant_op = max(point.operations.items(), key=lambda x: x[1])[0]
                        color = self.FG_COLORS.get(dominant_op, '')
                        line += color + self.CONNECTION + self.RESET
                    else:
                        line += self.CONNECTION
                else:
                    # Draw colored bands
                    cumulative = 0
                    drawn = False
                    
                    for op_type in [OperationType.DISCOVERY, OperationType.EXECUTION, 
                                   OperationType.AI_ANALYSIS, OperationType.AUTO_FIX, 
                                   OperationType.CACHE]:
                        if op_type not in point.operations:
                            continue
                        
                        thread_count = point.operations[op_type]
                        op_bottom = cumulative
                        op_top = cumulative + thread_count
                        cumulative = op_top
                        
                        if op_bottom < level_max and op_top > level_min:
                            color = self.FG_COLORS.get(op_type, '')
                            line +=color + self.DENSE_BLOCK + self.RESET
                            drawn = True
                            break
                    
                    if not drawn:
                        if level_idx == 0:
                            line += self.GRAY_FILLED + self.DENSE_BLOCK + self.RESET
                        else:
                            line += ' '
            
            lines.append(line)
        
        # Timeline axis
        timeline_line = f"{self.GRAY}    ┗━━{self.RESET}"
        for _ in self.downsampled_data:
            timeline_line += self.GRAY_FILLED + "━" + self.RESET
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
