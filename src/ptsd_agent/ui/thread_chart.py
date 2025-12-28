"""Minimalistic multi-line thread utilization chart for PTSD Agent.

Shows thread activity throughout entire execution as a compact,
multi-line vertical graph at the top of the display.
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
    """Renders minimalistic multi-line thread utilization chart."""
    
    # Braille Unicode patterns for smooth curves
    BRAILLE_CHARS = [' ', '⠁', '⠃', '⠇', '⠏', '⠟', '⠿', '⣿']
    
    # ANSI color codes
    COLORS = {
        OperationType.DISCOVERY: '\033[34m',    # Blue
        OperationType.EXECUTION: '\033[32m',    # Green  
        OperationType.AI_ANALYSIS: '\033[33m',  # Yellow
        OperationType.AUTO_FIX: '\033[38;5;208m',  # Orange
        OperationType.CACHE: '\033[36m',        # Cyan
    }
    RESET = '\033[0m'
    GRAY = '\033[90m'
    
    def __init__(self, max_threads: int = 12, terminal_width: int = 80, height: int = 5):
        """Initialize chart renderer.
        
        Args:
            max_threads: Maximum number of threads
            terminal_width: Width of terminal
            height: Height in lines (default 5 for minimalism)
        """
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        
        # Full timeline data (entire execution)
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
    
    def _get_braille_for_level(self, value: float, level: int) -> str:
        """Get Braille character for specific vertical level.
        
        Args:
            value: Thread count (0-max_threads)
            level: Vertical level (0=bottom, height-1=top)
        
        Returns:
            Braille character for this level
        """
        # Calculate threshold for this level (upside down)
        # Level 0 (bottom) = 0-20% of max
        # Level 1 = 20-40%
        # etc.
        level_ratio = (self.height - level - 1) / self.height
        next_level_ratio = (self.height - level) / self.height
        
        min_threshold = level_ratio * self.max_threads
        max_threshold = next_level_ratio * self.max_threads
        
        if value >= max_threshold:
            return self.BRAILLE_CHARS[-1]  # Full
        elif value <= min_threshold:
            return ' '  # Empty
        else:
            # Partial fill
            ratio = (value - min_threshold) / (max_threshold - min_threshold)
            index = int(ratio * (len(self.BRAILLE_CHARS) - 1))
            return self.BRAILLE_CHARS[index]
    
    def render(self) -> str:
        """Render multi-line thread chart.
        
        Returns:
            Multi-line chart (height lines)
        """
        if not self.timeline_data:
            return ""
        
        # Downsample to terminal width
        downsampled = self._downsample_data(self.timeline_data, self.terminal_width)
        
        lines = []
        
        # Build chart from top to bottom (upside down)
        for level in range(self.height - 1, -1, -1):
            line = ""
            for point in downsampled:
                char = self._get_braille_for_level(point.active_threads, level)
                color = self.COLORS.get(point.operation_type, self.RESET)
                line += color + char + self.RESET
            lines.append(line)
        
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
            # Pad with empty points if not enough data yet
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
                # Average active threads, take most common operation type
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
