"""Stunning thread chart with Braille curves and background colors.

Inspired by terminal analytics design - uses smooth Braille characters
with background colors for an elegant, modern visualization.
"""

import time
from typing import List, Tuple
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
    
    # Braille patterns for smooth curves
    BRAILLE_CURVES = {
        'top': '⠶',
        'rise_start': '⢠⠋',
        'rise_mid': '⣠⠃⠚',
        'rise_strong': '⡏⠁⠂',
        'baseline': '⠒',
        'peak': '⠉⠁',
        'fall': '⠈⠉',
    }
    
    # Background fill characters
    FILL_CHARS = {
        'light': '░',
        'medium': '▒',
        'heavy': '▓',
    }
    
    # Color schemes (softer, more elegant)
    COLORS = {
        OperationType.DISCOVERY: {
            'fg': '\033[38;5;110m',      # Soft blue
            'bg': '\033[48;5;17m',        # Dark blue bg
        },
        OperationType.EXECUTION: {
            'fg': '\033[38;5;108m',       # Soft green
            'bg': '\033[48;5;22m',        # Dark green bg
        },
        OperationType.AI_ANALYSIS: {
            'fg': '\033[38;5;180m',       # Soft yellow
            'bg': '\033[48;5;94m',        # Dark yellow bg
        },
        OperationType.AUTO_FIX: {
            'fg': '\033[38;5;174m',       # Soft red
            'bg': '\033[48;5;52m',        # Dark red bg
        },
        OperationType.CACHE: {
            'fg': '\033[38;5;109m',       # Soft cyan
            'bg': '\033[48;5;23m',        # Dark cyan bg
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
    
    def add_data_point(self, active_threads: int, operation_type: OperationType):
        """Add data point to timeline."""
        point = DataPoint(
            timestamp=time.time(),
            active_threads=active_threads,
            operation_type=operation_type
        )
        self.timeline_data.append(point)
    
    def _get_braille_segment(self, idx: int, value: float, level_min: float, level_max: float, op_type: OperationType) -> str:
        """Get beautiful Braille segment with background color."""
        colors = self.COLORS.get(op_type, self.COLORS[OperationType.CACHE])
        
        if value <= level_min:
            return ' '
        elif value >= level_max:
            # Full fill with background color
            return colors['bg'] + colors['fg'] + self.FILL_CHARS['heavy'] + self.RESET
        else:
            # Partial fill - gradient
            ratio = (value - level_min) / (level_max - level_min)
            
            if ratio < 0.33:
                char = self.FILL_CHARS['light']
            elif ratio < 0.67:
                char = self.FILL_CHARS['medium']
            else:
                char = self.FILL_CHARS['heavy']
            
            return colors['bg'] + colors['fg'] + char + self.RESET
    
    def _detect_edge(self, idx: int, downsampled: List[DataPoint], level_min: float, level_max: float) -> Tuple[bool, str]:
        """Detect if this is a rising/falling edge and return Braille character."""
        if idx == 0 or idx >= len(downsampled) - 1:
            return False, ''
        
        curr = downsampled[idx].active_threads
        prev = downsampled[idx - 1].active_threads
        
        # Rising edge entering this level
        if prev < level_min and curr >= level_min:
            return True, '⣠'
        
        # Falling edge leaving this level  
        if prev >= level_max and curr < level_max:
            return True, '⠹⣄'
        
        return False, ''
    
    def render(self) -> str:
        """Render stunning Braille curve chart."""
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
                seg = self._get_braille_segment(idx, point.active_threads, level_min, level_max, point.operation_type)
                line += seg
            
            lines.append(line)
        
        # Beautiful colored timeline axis
        timeline_line = f"{self.GRAY}    ┗━━{self.RESET}"
        
        prev_op = None
        for idx, point in enumerate(downsampled):
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
