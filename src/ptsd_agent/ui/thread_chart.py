"""Stunning thread chart with colored timeline axis.

The bottom axis itself becomes a beautiful visualization showing
operation types over time with smooth color transitions!
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
    """Renders stunning thread chart with colored timeline."""
    
    # Gradient characters
    GRADIENT_CHARS = ['░', '▒', '▓', '█']
    
    # ANSI 256-color codes for smooth gradients
    COLOR_GRADIENTS = {
        OperationType.DISCOVERY: ['\033[38;5;27m', '\033[38;5;33m', '\033[38;5;39m', '\033[38;5;45m'],
        OperationType.EXECUTION: ['\033[38;5;28m', '\033[38;5;34m', '\033[38;5;40m', '\033[38;5;46m'],
        OperationType.AI_ANALYSIS: ['\033[38;5;136m', '\033[38;5;142m', '\033[38;5;148m', '\033[38;5;154m'],
        OperationType.AUTO_FIX: ['\033[38;5;124m', '\033[38;5;160m', '\033[38;5;196m', '\033[38;5;202m'],
        OperationType.CACHE: ['\033[38;5;30m', '\033[38;5;36m', '\033[38;5;42m', '\033[38;5;48m'],
    }
    
    # Solid colors for timeline
    TIMELINE_COLORS = {
        OperationType.DISCOVERY: '\033[48;5;33m',     # Blue background
        OperationType.EXECUTION: '\033[48;5;34m',     # Green background
        OperationType.AI_ANALYSIS: '\033[48;5;142m',  # Yellow background
        OperationType.AUTO_FIX: '\033[48;5;160m',     # Red background
        OperationType.CACHE: '\033[48;5;36m',         # Cyan background
    }
    
    RESET = '\033[0m'
    DIM = '\033[2m'
    BOLD = '\033[1m'
    GRAY = '\033[1;30m'
    WHITE = '\033[97m'
    
    def __init__(self, max_threads: int = 12, terminal_width: int = 80, height: int = 5):
        """Initialize chart renderer."""
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        self.chart_width = terminal_width - 8
        
        self.timeline_data: List[DataPoint] = []
        self.start_time = time.time()
    
    def add_data_point(self, active_threads: int, operation_type: OperationType):
        """Add data point to timeline."""
        point = DataPoint(
            timestamp=time.time(),
            active_threads=active_threads,
            operation_type=operation_type
        )
        self.timeline_data.append(point)
    
    def _get_char_for_level(self, idx: int, value: float, level_min: float, level_max: float, op_type: OperationType) -> str:
        """Get character for this position and level."""
        if value <= level_min:
            return ' '
        elif value >= level_max:
            color = self.COLOR_GRADIENTS[op_type][-1]
            return color + self.GRADIENT_CHARS[-1] + self.RESET
        else:
            ratio = (value - level_min) / (level_max - level_min)
            
            char_index = int(ratio * len(self.GRADIENT_CHARS))
            char_index = min(char_index, len(self.GRADIENT_CHARS) - 1)
            char = self.GRADIENT_CHARS[char_index]
            
            color_index = int(ratio * len(self.COLOR_GRADIENTS[op_type]))
            color_index = min(color_index, len(self.COLOR_GRADIENTS[op_type]) - 1)
            color = self.COLOR_GRADIENTS[op_type][color_index]
            
            return color + char + self.RESET
    
    def render(self) -> str:
        """Render stunning thread chart with colored timeline."""
        if not self.timeline_data:
            return ""
        
        downsampled = self._downsample_data(self.timeline_data, self.chart_width)
        
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
            
            for idx, point in enumerate(downsampled):
                char = self._get_char_for_level(idx, point.active_threads, level_min, level_max, point.operation_type)
                line += char
            
            lines.append(line)
        
        # Beautiful colored timeline axis!
        timeline_line = f"{self.GRAY}    ┗━━{self.RESET}"
        
        prev_op = None
        for idx, point in enumerate(downsampled):
            # Add delimiter when operation type changes
            if prev_op and prev_op != point.operation_type:
                timeline_line += self.RESET + self.GRAY + "╸" + self.RESET
            
            # Colored timeline segment
            color = self.TIMELINE_COLORS.get(point.operation_type, '')
            timeline_line += color + " " + self.RESET
            
            prev_op = point.operation_type
        
        timeline_line += self.GRAY + "┛" + self.RESET
        lines.append(timeline_line)
        
        # Time labels with tick marks
        total_time = time.time() - self.start_time
        tick_interval = max(int(self.chart_width / 8), 8)
        
        time_labels = "      "
        for i in range(0, self.chart_width, tick_interval):
            time_sec = int((i / self.chart_width) * total_time)
            time_labels += f"{self.DIM}{time_sec:02d}     {self.RESET}"
        
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
