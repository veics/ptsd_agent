"""Stunning thread chart with smooth Braille curves.

Creates elegant curved lines connecting data points using
Braille characters, with background fills for beautiful visualization.
"""

import time
from typing import List, Optional
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
    """Renders stunning thread chart with Braille curves."""
    
    # Braille patterns for smooth curves (connecting points)
    CURVE_RISE = ['⢠', '⣀', '⣠', '⣤', '⣴', '⣶', '⣷', '⣿']
    CURVE_FALL = ['⠻', '⠹', '⠱', '⠡', '⠁']
    
    # Background fill characters
    FILL_CHARS = ['░', '▒', '▓', '█']
    
    # Color schemes (softer, more elegant)
    COLORS = {
        OperationType.DISCOVERY: {
            'fg': '\033[38;5;110m',
            'bg': '\033[48;5;17m',
        },
        OperationType.EXECUTION: {
            'fg': '\033[38;5;108m',
            'bg': '\033[48;5;22m',
        },
        OperationType.AI_ANALYSIS: {
            'fg': '\033[38;5;180m',
            'bg': '\033[48;5;94m',
        },
        OperationType.AUTO_FIX: {
            'fg': '\033[38;5;174m',
            'bg': '\033[48;5;52m',
        },
        OperationType.CACHE: {
            'fg': '\033[38;5;109m',
            'bg': '\033[48;5;23m',
        },
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
    
    def add_data_point(self, active_threads: int, operation_type: OperationType):
        """Add data point to timeline."""
        point = DataPoint(
            timestamp=time.time(),
            active_threads=active_threads,
            operation_type=operation_type
        )
        self.timeline_data.append(point)
    
    def _get_char_at_position(self, idx: int, value: float, prev_value: Optional[float], 
                             next_value: Optional[float], level_min: float, level_max: float, 
                             op_type: OperationType) -> str:
        """Get character at this position - curve, fill, or space."""
        colors = self.COLORS.get(op_type, self.COLORS[OperationType.CACHE])
        
        # Empty space below threshold
        if value <= level_min:
            return ' '
        
        # Check if this is an edge (curve needed)
        is_rising_edge = prev_value is not None and prev_value < level_min and value >= level_min
        is_falling_edge = next_value is not None and value >= level_max and next_value < level_max
        
        # Rising curve
        if is_rising_edge:
            curve_progress = min((value - level_min) / (level_max - level_min), 1.0)
            curve_idx = int(curve_progress * (len(self.CURVE_RISE) - 1))
            char = self.CURVE_RISE[curve_idx]
            return colors['fg'] + char + self.RESET
        
        # Falling curve  
        if is_falling_edge:
            curve_progress = min((next_value - level_min) / (level_max - level_min), 1.0) if next_value else 0
            curve_idx = int(curve_progress * (len(self.CURVE_FALL) - 1))
            char = self.CURVE_FALL[curve_idx]
            return colors['fg'] + char + self.RESET
        
        # Full fill with background
        if value >= level_max:
            fill_idx = min(int((value / self.max_threads) * len(self.FILL_CHARS)), len(self.FILL_CHARS) - 1)
            char = self.FILL_CHARS[fill_idx]
            return colors['bg'] + colors['fg'] + char + self.RESET
        
        # Partial fill - gradient
        ratio = (value - level_min) / (level_max - level_min)
        fill_idx = int(ratio * len(self.FILL_CHARS))
        fill_idx = min(fill_idx, len(self.FILL_CHARS) - 1)
        char = self.FILL_CHARS[fill_idx]
        
        return colors['bg'] + colors['fg'] + char + self.RESET
    
    def render(self) -> str:
        """Render stunning Braille curve chart."""
        if not self.timeline_data:
            return ""
        
        self.downsampled_data = self._downsample_data(self.timeline_data, self.chart_width)
        
        lines = []
        threads_per_level = self.max_threads / self.height
        
        # Render levels from top to bottom
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
            
            for idx, point in enumerate(self.downsampled_data):
                prev_val = self.downsampled_data[idx - 1].active_threads if idx > 0 else None
                next_val = self.downsampled_data[idx + 1].active_threads if idx < len(self.downsampled_data) - 1 else None
                
                char = self._get_char_at_position(idx, point.active_threads, prev_val, next_val,
                                                 level_min, level_max, point.operation_type)
                line += char
            
            lines.append(line)
        
        # Beautiful colored timeline axis
        timeline_line = f"{self.GRAY}    ┗━━{self.RESET}"
        
        prev_op = None
        for idx, point in enumerate(self.downsampled_data):
            if prev_op and prev_op != point.operation_type:
                timeline_line += self.RESET + self.GRAY + "╸" + self.RESET
            
            colors = self.COLORS.get(point.operation_type, self.COLORS[OperationType.CACHE])
            timeline_line += colors['bg'] + " " + self.RESET
            
            prev_op = point.operation_type
        
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
        """Render chart (alias)."""
        return self.render()
    
    def _downsample_data(self, data: List[DataPoint], target_width: int) -> List[DataPoint]:
        """Downsample data to fit target width."""
        if len(data) <= target_width:
            padding = target_width - len(data)
            return list(data) + [DataPoint(0, 0, OperationType.CACHE) for _ in range(padding)]
        
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
