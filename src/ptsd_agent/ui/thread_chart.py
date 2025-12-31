"""Thread chart - REBUILT from matrix_chart_demo_9.py!

Perfect animation with Y-axis labels, smooth LUT rendering, timeline.
"""

import time
import math
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum


class OperationType(Enum):
    """Types of operations."""
    DISCOVERY = "discovery"
    EXECUTION = "execution"
    AI_ANALYSIS = "ai"
    AUTO_FIX = "fix"
    CACHE = "cache"


@dataclass
class DataPoint:
    """Single data point."""
    timestamp: float
    operations: Dict[OperationType, int]
    
    @property
    def total_threads(self) -> int:
        return sum(self.operations.values())

# --- LUTs ---
LUT_SMOOTH = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

LUT_CHAIN = [
    ['⠤', '⠤', '⠔', '⠴', '⠴'], 
    ['⠤', '⠒', '⠊', '⠴', '⠴'], 
    ['⠑', '⠑', '⠒', '⠊', '⠊'], 
    ['⠱', '⠱', '⠑', '⠒', '⠊'], 
    ['⠱', '⠱', '⠱', '⠑', '⠉']  
]

CHAR_FILL = '⣿'


class ThreadChartRenderer:
    """Perfect chart from matrix_chart_demo_9!"""
    
    # Default colors (can be overridden via config)
    C_ORANGE = '\033[38;5;214m'
    C_GREEN = '\033[38;5;46m'
    C_LABEL = '\033[38;5;250m'
    C_RESET = '\033[0m'
    
    # Operation colors - use string VALUES for compatibility across modules
    OP_COLORS_MAP = {
        'discovery': '\033[38;5;110m',   # Light blue
        'execution': '\033[38;5;108m',   # Sage green
        'ai': '\033[38;5;180m',          # Tan/khaki
        'fix': '\033[38;5;174m',         # Dusty rose
        'cache': '\033[38;5;109m',       # Teal
        'research': '\033[38;5;139m',    # Purple (new)
    }
    
    def __init__(self, max_threads: int = 12, terminal_width: int = None, height: int = 6, colors: dict = None):
        """Initialize.
        
        Args:
            max_threads: Max threads for Y-axis scale
            terminal_width: Chart width in columns
            height: Number of rows
            colors: Optional dict with 'axis', 'empty', 'blink', 'blink_chars' keys
        """
        if terminal_width is None:
            import shutil
            terminal_width = shutil.get_terminal_size().columns
        
        self.max_threads = max_threads
        self.terminal_width = terminal_width
        self.height = height
        # Y-axis is: 4-char label + space + ┃ + space = 7 chars
        self.chart_width = terminal_width - 7
        
        # Configurable colors (with defaults)
        colors = colors or {}
        axis_code = colors.get('axis', 94)
        empty_code = colors.get('empty', 236)
        blink_code = colors.get('blink', 214)
        self.blink_chars = colors.get('blink_chars', 2)
        
        self.C_AXIS = f'\033[38;5;{axis_code}m'
        self.C_EMPTY = f'\033[38;5;{empty_code}m'
        self.C_BLINK = f'\033[38;5;{blink_code}m'
        
        self.timeline_data: List[DataPoint] = []
        self.start_time = time.time()
        self._pending_max_threads = None
    
    def set_max_threads(self, max_threads: int):
        """Update max_threads for Y-axis scaling (call when parallel count is known)."""
        self._pending_max_threads = max_threads
    
    def add_data_point(self, operations: Dict[OperationType, int]):
        """Add data point."""
        self.timeline_data.append(DataPoint(
            timestamp=time.time(),
            operations=operations
        ))
    
    def render(self, terminal_width: int = None, progress_pct: float = None) -> str:
        """Render using demo 9 logic!
        
        Args:
            terminal_width: Override terminal width (for dynamic resizing)
            progress_pct: Current progress percentage (0-100) for timeline sync
        """
        if not self.timeline_data:
            return ""
        
        # Store progress for timeline calculation
        self._progress_pct = progress_pct
        
        # Update chart_width dynamically if terminal_width provided
        if terminal_width is not None:
            self.terminal_width = terminal_width
            self.chart_width = terminal_width - 7  # Y-axis is 7 chars
        
        # Update max_threads if set
        if self._pending_max_threads is not None:
            self.max_threads = self._pending_max_threads
            self._pending_max_threads = None
        
        # DYNAMIC SCALING: Calculate actual max from data
        # Use max of (max_threads setting, actual data max) so chart scales up as needed
        actual_max = max(p.total_threads for p in self.timeline_data)
        effective_max = max(self.max_threads, actual_max, 1)  # At least 1
        
        output = []
        
        # Y-axis labels based on effective_max (linear scale)
        # Row 0 = bottom (value 0), Row height-1 = top (value effective_max)
        # When rendering, we go from r=height-1 down to r=0, using y_labels[r]
        step = effective_max / (self.height - 1) if self.height > 1 else effective_max
        # Index by row: y_labels[r] = value that row represents
        y_labels = [f"{int(r * step):>4}" for r in range(self.height)]
        # So y_labels[0]=0, y_labels[height-1]=effective_max
        
        # Extract values
        values = [p.total_threads for p in self.timeline_data]
        visible_idx = len(values)
        
        # Scale based on effective_max (dynamic scaling) - use FULL height
        scale_y = (self.height * 4) / (effective_max + 1)
        norm_data = [(v * scale_y) for v in values]
        
        # Calculate filled columns once (used by all rows)
        if self._progress_pct is not None:
            filled_columns = int((self._progress_pct / 100.0) * self.chart_width)
        else:
            filled_columns = len(norm_data) if norm_data else 0
        filled_columns = min(filled_columns, self.chart_width)
        
        # Render DATA rows with integrated green line at TOP EDGE
        for r in range(self.height - 1, -1, -1):
            line_buffer = ""
            
            # Y-axis with cyan separator
            if r < len(y_labels):
                line_buffer += f"{self.C_LABEL}{y_labels[r]} {self.C_AXIS}┃ {self.C_RESET}"
            else:
                line_buffer += f"     {self.C_AXIS}┃ {self.C_RESET}"
            
            row_bottom = r * 4
            row_top = (r + 1) * 4
            
            # Render FULL chart width
            for i in range(self.chart_width):
                # After filled area, render empty space
                if i >= filled_columns:
                    line_buffer += " "
                    continue
                
                # Map chart position to data index (stretch data to fill progress area)
                if len(norm_data) > 1 and filled_columns > 1:
                    data_idx = int(i * (len(norm_data) - 1) / (filled_columns - 1))
                    data_idx = min(data_idx, len(norm_data) - 2)
                else:
                    data_idx = 0
                
                if data_idx >= len(norm_data) - 1:
                    line_buffer += " "
                    continue
                
                y1, y2 = norm_data[data_idx], norm_data[data_idx + 1]
                y_max = max(y1, y2)  # Top edge of the data at this column
                y_min = min(y1, y2)
                
                char_final = " "
                color_final = self.C_RESET
                
                # Only render green on the SINGLE HIGHEST row - no stacking!
                top_row = max(int(y1 / 4), int(y2 / 4))
                is_top_row = (r == top_row)
                
                # Get operation color for this data point
                point = self.timeline_data[min(data_idx, len(self.timeline_data) - 1)]
                op_color = self.C_ORANGE  # Default orange
                if point.operations:
                    op = max(point.operations.items(), key=lambda x: x[1])[0]
                    # Use .value to get string key for lookup (handles different OperationType enums)
                    op_key = op.value if hasattr(op, 'value') else str(op)
                    op_color = self.OP_COLORS_MAP.get(op_key, self.C_ORANGE)
                
                # LAYER 1: Base chart (colored by operation type)
                if y1 >= row_top and y2 >= row_top:
                    # Full block - use operation color
                    color_final = op_color
                    char_final = CHAR_FILL
                    
                    # ALSO render green on top if this is THE top row
                    if is_top_row:
                        # Add wave oscillation for dynamic appearance
                        wave = math.sin(i * 0.3) * 1.5
                        wave_pos1 = int(max(1, min(4, 3 + wave)))
                        wave_pos2 = int(max(1, min(4, 3 + math.sin((i + 1) * 0.3) * 1.5)))
                        char_final = LUT_CHAIN[wave_pos1][wave_pos2]
                        color_final = self.C_GREEN
                
                elif y1 < row_bottom and y2 < row_bottom:
                    char_final = " "
                
                else:
                    # EDGE row
                    ly1 = int(max(0, min(4, y1 - row_bottom + 0.5)))
                    ly2 = int(max(0, min(4, y2 - row_bottom + 0.5)))
                    
                    if is_top_row:
                        # Top edge - render as green with wave
                        wave = math.sin(i * 0.3) * 0.8
                        gy1 = int(max(0, min(4, ly1 + wave)))
                        gy2 = int(max(0, min(4, ly2 + math.sin((i + 1) * 0.3) * 0.8)))
                        char_final = LUT_CHAIN[gy1][gy2]
                        color_final = self.C_GREEN
                    else:
                        # Lower edge - use operation color with braille pattern
                        char_final = LUT_SMOOTH[ly1][ly2]
                        color_final = op_color
                
                line_buffer += f"{color_final}{char_final}"
            
            output.append(line_buffer + self.C_RESET)
        
        # Timeline - sync with progress bar using progress_pct
        # If progress_pct provided, use it; otherwise fall back to data point ratio
        if self._progress_pct is not None:
            # Timeline fills proportionally to progress percentage
            filled_len = int((self._progress_pct / 100.0) * self.chart_width)
        else:
            # Fallback: use data points ratio
            filled_len = visible_idx
        
        if filled_len >= self.chart_width:
            filled_len = self.chart_width
            gap_len = 0
            remaining_len = 0
        else:
            gap_len = 1
            if filled_len > self.chart_width - 1:
                filled_len = self.chart_width - 1
            remaining_len = self.chart_width - filled_len - gap_len
        
        bar_filled = f"{self.C_AXIS}" + ("━" * filled_len)
        bar_gap = " " * gap_len
        bar_empty = f"{self.C_EMPTY}" + ("━" * remaining_len)
        corner = f"   0 {self.C_AXIS}┗━"
        
        axis_line = f"{corner}{bar_filled}{bar_gap}{bar_empty}{self.C_RESET}"
        output.append(axis_line)
        
        # Time labels
        elapsed = time.time() - self.start_time
        padding = " " * 7
        label_chars = [" "] * self.chart_width
        
        label_start = "0s"
        for k, ch in enumerate(label_start):
            if k < self.chart_width:
                label_chars[k] = ch
        
        t_str = f"{elapsed:.1f}s"
        pos = filled_len
        if pos < 2:
            pos = 2
        # Cap position to leave space for green line indicator on the right
        # Leave at least 15% of chart width empty on the right
        max_pos = int(self.chart_width * 0.85) - len(t_str)
        if pos > max_pos:
            pos = max_pos
        
        for k, ch in enumerate(t_str):
            if pos + k < self.chart_width:
                label_chars[pos + k] = ch
        
        label_line = "".join(label_chars)
        output.append(f"{padding}{self.C_LABEL}{label_line}{self.C_RESET}")
        
        return '\n'.join(output)
    
    def render_realtime_chart(self) -> str:
        return self.render()
