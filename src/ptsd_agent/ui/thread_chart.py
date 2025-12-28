"""Final design: Colored bands with sparse curve on top.

Beautiful complete visualization:
- Gray filled baseline
- Colored horizontal bands showing execution types
- Sparse 1-3 dot curve line floating on top
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
    """Renders chart with bands and curve."""
    
    # Sparse curve patterns (1-3 dots)
    SPARSE_CURVE = ['⠀', '⠁', '⠂', '⠃', '⠄', '⠅', '⠆', '⠇']
    
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
    
    def add_data_point(self, operations: Dict[OperationType, int]):
        """Add data point."""
        point = DataPoint(
            timestamp=time.time(),
            operations=operations
        )
        self.timeline_data.append(point)
    
    def _get_sparse_curve_char(self, value: float) -> str:
        """Get sparse curve character (1-3 dots)."""
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
        """Render complete chart with bands and curve."""
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
                # Check if sparse curve should be drawn here (priority)
                if self._is_curve_level(level_idx, self.height, point.total_threads):
                    # Draw sparse curve dot on top
                    dot = self._get_sparse_curve_char(point.total_threads)
                    if point.operations:
                        dominant_op = max(point.operations.items(), key=lambda x: x[1])[0]
                        color = self.FG_COLORS.get(dominant_op, '')
                        line += color + dot + self.RESET
                    else:
                        line += dot
                else:
                    # Draw colored horizontal bands below curve
                    cumulative = 0
                    drawn = False
                    
                    # Stack operations in consistent order
                    for op_type in [OperationType.DISCOVERY, OperationType.EXECUTION, 
                                   OperationType.AI_ANALYSIS, OperationType.AUTO_FIX, 
                                   OperationType.CACHE]:
                        if op_type not in point.operations:
                            continue
                        
                        thread_count = point.operations[op_type]
                        op_bottom = cumulative
                        op_top = cumulative + thread_count
                        cumulative = op_top
                        
                        # Check if this band occupies this level
                        if op_bottom < level_max and op_top > level_min:
                            color = self.FG_COLORS.get(op_type, '')
                            line += color + self.DENSE_BLOCK + self.RESET
                            drawn = True
                            break
                    
                    if not drawn:
                        # Gray filled baseline
                        if level_idx == 0:
                            line += self.GRAY_FILLED + self.DENSE_BLOCK + self.RESET
                        else:
                            line += ' '
            
            lines.append(line)
        
        # Timeline axis
        timeline_line = f"{self.GRAY}    ┗━━{self.RESET}"
        
        for _ in downsampled:
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
