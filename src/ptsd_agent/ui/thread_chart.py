"""Professional thread utilization chart with gradient shading and axes.

Shows thread activity throughout execution with:
- Y-axis labels (thread count)
- X-axis labels (time markers)
- Gradient block shading (░▒▓)
- Smooth Braille baseline
"""

import time
from typing import List
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
    """Renders professional thread chart with gradient shading."""
    
    # Block shading characters (light to heavy)
    SHADE_CHARS = ['░', '▒', '▓', '█']
    
    # Braille for smooth baseline
    BRAILLE_CHARS = [' ', '⠁', '⠃', '⠇', '⠏', '⠟', '⠿', '⣿']
    
    # ANSI color codes
    COLORS = {
        OperationType.DISCOVERY: '\033[34m',     # Blue
        OperationType.EXECUTION: '\033[32m',     # Green  
        OperationType.AI_ANALYSIS: '\033[33m',   # Yellow
        OperationType.AUTO_FIX: '\033[31m',      # Red
        OperationType.CACHE: '\033[36m',         # Cyan
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    def __init__(self, max_threads: int = 12, terminal_width: int = 80, height: int = 5):
        """Initialize chart renderer.
        
        Args:
            max_threads: Maximum number of threads
            terminal_width: Width of terminal
            height: Height in rows (default 5)
        """
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        self.chart_width = terminal_width - 8  # Reserve for Y-axis labels
        
        # Full timeline data
        self.timeline_data: List[DataPoint] = []
        self.start_time = time.time()
    
    def add_data_point(self, active_threads: int, operation_type: OperationType):
        """Add a data point to timeline.
        
        Args:
            active_threads: Number of threads currently active
            operation_type: Type of operation
        """
        point = DataPoint(
            timestamp=time.time(),
            active_threads=active_threads,
            operation_type=operation_type
        )
        self.timeline_data.append(point)
    
    def _get_shade_char(self, value: float, level_min: float, level_max: float) -> str:
        """Get shading character for value at this level.
        
        Args:
            value: Thread count
            level_min: Minimum threads for this level
            level_max: Maximum threads for this level
        
        Returns:
            Shade character or space
        """
        if value <= level_min:
            return ' '
        elif value >= level_max:
            return self.SHADE_CHARS[-1]  # Full block
        else:
            # Gradient based on how far into this level
            ratio = (value - level_min) / (level_max - level_min)
            index = int(ratio * len(self.SHADE_CHARS))
            index = min(index, len(self.SHADE_CHARS) - 1)
            return self.SHADE_CHARS[index]
    
    def render(self) -> str:
        """Render professional thread chart.
        
        Returns:
            Multi-line chart with axes
        """
        if not self.timeline_data:
            return ""
        
        # Downsample to chart width
        downsampled = self._downsample_data(self.timeline_data, self.chart_width)
        
        lines = []
        
        # Calculate level thresholds
        threads_per_level = self.max_threads / self.height
        
        # Render from top to bottom (high to low)
        for level_idx in range(self.height - 1, -1, -1):
            level_max = (level_idx + 1) * threads_per_level
            level_min = level_idx * threads_per_level
            
            # Y-axis label (show max threads for top levels)
            if level_idx == self.height - 1:
                label = f"{int(self.max_threads):3d}"
            elif level_idx == 0:
                label = "0.0"
            else:
                label = f" {int(level_max):2d}"
            
            # Build line
            line = f"{label} ┃ "
            
            for point in downsampled:
                char = self._get_shade_char(point.active_threads, level_min, level_max)
                
                # Color based on operation type
                if char != ' ':
                    color = self.COLORS.get(point.operation_type, self.RESET)
                    line += color + char + self.RESET
                else:
                    line += char
            
            lines.append(line)
        
        # X-axis line
        x_axis = "    ┗" + "━" * self.chart_width
        lines.append(x_axis)
        
        # X-axis time labels (every ~5-10 chars)
        total_time = time.time() - self.start_time
        label_interval = max(int(self.chart_width / 10), 5)
        
        time_labels = "      "
        for i in range(0, self.chart_width, label_interval):
            time_sec = int((i / self.chart_width) * total_time)
            time_labels += f"{time_sec:02d}    "
        
        lines.append(self.DIM + time_labels + self.RESET)
        
        return '\n'.join(lines)
    
    def render_realtime_chart(self) -> str:
        """Render chart (alias for render()).
        
        Returns:
            Thread utilization chart
        """
        return self.render()
    
    def _downsample_data(self, data: List[DataPoint], target_width: int) -> List[DataPoint]:
        """Downsample data to fit target width.
        
        Args:
            data: Full data list
            target_width: Target number of points
        
        Returns:
            Downsampled data
        """
        if len(data) <= target_width:
            # Pad with empty points
            padding = target_width - len(data)
            padded = list(data) + [DataPoint(0, 0, OperationType.CACHE) for _ in range(padding)]
            return padded
        
        # Downsample via averaging
        step = len(data) / target_width
        downsampled = []
        
        for i in range(target_width):
            start_idx = int(i * step)
            end_idx = int((i + 1) * step)
            chunk = data[start_idx:end_idx]
            
            if chunk:
                avg_threads = sum(p.active_threads for p in chunk) // len(chunk)
                most_common_op = max(
                    set(p.operation_type for p in chunk), 
                    key=lambda x: sum(1 for p in chunk if p.operation_type == x)
                )
                
                downsampled.append(DataPoint(
                    timestamp=chunk[0].timestamp,
                    active_threads=avg_threads,
                    operation_type=most_common_op
                ))
        
        return downsampled
