"""Thread chart with Braille-based visualization - PROVEN ANIMATION LOGIC!

Based on working matrix_chart_demo_6.py - smooth LUT rendering with left-to-right animation.
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
    """Working animation - based on proven demo!"""
    
    # 5x5 LUT for smooth Braille edges (from working demo!)
    LUT = [
, '⢸'],         ['⠀', '⢀', '⢠', '
        ['⡀', '⣀', '⣠', '⣰', '⣸'], 
        ['⡄', '⣄', '⣤', '⣴', '⣼'], 
        ['⡆', '⣆', '⣦', '⣶', '⣾'], 
        ['⡇', '⣇', '⣧', '⣷', '⣿'] 
    ]
    
    # Colors - MATCH ORIGINAL REQUEST
    ORANGE = '\033[38;5;214m'  # Top edge
    GREEN = '\033[38;5;108m'   # Timeline
    FADED_GREEN = '\033[38;5;65m'
    GRAY = '\033[38;5;240m'
    
    OP_COLORS = {
        OperationType.DISCOVERY: '\033[38;5;110m',    # Blue
        OperationType.EXECUTION: '\033[38;5;108m',    # Green  
        OperationType.AI_ANALYSIS: '\033[38;5;180m',  # Yellow
        OperationType.AUTO_FIX: '\033[38;5;174m',     # Red
        OperationType.CACHE: '\033[38;5;109m',        # Cyan
    }
    
    RESET = '\033[0m'
    
    def __init__(self, max_threads: int = 12, terminal_width: int = None, height: int = 5):
        """Initialize chart renderer."""
        if terminal_width is None:
            import shutil
            terminal_width = shutil.get_terminal_size().columns
        
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        self.chart_width = terminal_width - 5  # Y-axis space
        
        self.timeline_data: List[DataPoint] = []
        self.start_time = time.time()
        self.frame_count = 0
    
    def add_data_point(self, operations: Dict[OperationType, int]):
        """Add data point."""
        point = DataPoint(
            timestamp=time.time(),
            operations=operations
        )
        self.timeline_data.append(point)
    
    def render(self) -> str:
        """Render chart using PROVEN animation logic from demo!"""
        if not self.timeline_data:
            return ""
        
        self.frame_count += 1
        
        # Extract thread counts for rendering
        values = [p.total_threads for p in self.timeline_data]
        visible_idx = len(values)
        
        # Normalize data (demo logic!)
        max_val = max(values) if values else 1
        scale_y = (self.height * 4) / (max_val + 2)
        norm_data = [(v * scale_y) for v in values]
        
        lines = []
        
        # Render rows top-to-bottom (demo logic!)
        for r in range(self.height - 1, -1, -1):
            line_buffer = f"{self.GRAY}{str(int((r+1) * (max_val / self.height))):>2} ┃{self.RESET}"
            row_bottom = r * 4
            row_top = (r + 1) * 4
            
            for i in range(min(len(norm_data) - 1, self.chart_width)):
                y1, y2 = norm_data[i], norm_data[i+1]
                
                char = " "
                color = self.RESET
                
                if y1 >= row_top and y2 >= row_top:
                    # Full block - use operation color
                    point = self.timeline_data[i]
                    if point.operations:
                        op = max(point.operations.items(), key=lambda x: x[1])[0]
                        color = self.OP_COLORS.get(op, self.RESET)
                    char = "⣿"
                
                elif y1 < row_bottom and y2 < row_bottom:
                    # Empty
                    char = " "
                
                else:
                    # EDGE - Orange LUT (demo logic!)
                    ly1 = int(max(0, min(4, y1 - row_bottom)))
                    ly2 = int(max(0, min(4, y2 - row_bottom)))
                    char = self.LUT[ly1][ly2]
                    color = self.ORANGE
                
                line_buffer += f"{color}{char}{self.RESET}"
            
            lines.append(line_buffer)
        
        # Timeline (demo logic!)
        last_idx = visible_idx - 1
        timeline = f"{self.GRAY}    {self.GREEN}┗━━{self.RESET}"
        
        for i in range(min(visible_idx, self.chart_width)):
            if i < last_idx:
                timeline += f"{self.GREEN}━{self.RESET}"
            elif i == last_idx:
                if self.frame_count % 4 < 2:
                    timeline += f"{self.FADED_GREEN}━{self.RESET}"
                else:
                    timeline += f"{self.GRAY}━{self.RESET}"
        
        # Fill rest with gray
        remaining = self.chart_width - visible_idx
        if remaining > 0:
            timeline += f"{self.GRAY}{'─' * remaining}┛{self.RESET}"
        else:
            timeline += f"{self.GRAY}┛{self.RESET}"
        
        lines.append(timeline)
        
        return '\n'.join(lines)
    
    def render_realtime_chart(self) -> str:
        return self.render()
