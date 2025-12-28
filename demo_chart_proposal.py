#!/usr/bin/env python3
"""Demo: Vertical stacked colored bars chart design.

Shows the intended design:
- Each vertical column = one time point
- Stacked colored blocks from bottom to top
- Each color = operation type consuming threads
- Full terminal width
- Time-based X-axis
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# ANSI colors
RESET = '\033[0m'
GRAY = '\033[38;5;240m'
BLUE = '\033[38;5;110m'    # Discovery
GREEN = '\033[38;5;108m'   # Execution
YELLOW = '\033[38;5;180m'  # AI Analysis
RED = '\033[38;5;174m'     # Auto-fix
CYAN = '\033[38;5;109m'    # Cache

# Braille dense block
BLOCK = '⣿'


def render_demo_chart():
    """Render demo chart with proposed design."""
    print("\n" + "="*80)
    print("  PROPOSED DESIGN: Vertical Stacked Colored Bars")
    print("="*80 + "\n")
    
    # Sample data: {time_point: {operation: thread_count}}
    # START WITH DATA (no empty points at beginning!)
    timeline = [
        {'discovery': 2},  # Start immediately
        {'discovery': 4},
        {'discovery': 6},
        {'discovery': 5, 'execution': 2},
        {'discovery': 3, 'execution': 4},
        {'execution': 8},
        {'execution': 10},
        {'execution': 12},
        {'execution': 11},
        {'execution': 9, 'ai': 2},
        {'execution': 6, 'ai': 4},
        {'execution': 4, 'ai': 5},
        {'ai': 6, 'fix': 2},
        {'ai': 4, 'fix': 3},
        {'fix': 3, 'cache': 1},
        {'fix': 2, 'cache': 2},
        {'cache': 2},
        {'cache': 1},
        {},  # End with empty
    ]
    
    max_threads = 12
    height = 5
    chart_width = len(timeline)
    
    # Y-axis levels (log scale would go here)
    levels = [12, 6, 3, 1, 0]
    
    # Render each row from top to bottom
    for level_idx, level_value in enumerate(levels):
        # Y-axis label
        if level_idx == 0:
            label = f"{GRAY}{level_value:3d} ┃{RESET}"
        elif level_idx == len(levels) - 1:
            label = f"{GRAY}0.0 ┃{RESET}"
        else:
            label = f"{GRAY} {level_value:2d} ┃{RESET}"
        
        line = label + " "
        
        # Each column - START FROM LEFT, NO GAPS
        for col_idx, point in enumerate(timeline):
            if not point:
                line += " "
                continue
            
            # Calculate total threads at this point
            total = sum(point.values())
            
            # Stack operations from bottom: discovery, execution, ai, fix, cache
            cumulative = 0
            char_added = False
            
            for op_name, color in [('discovery', BLUE), ('execution', GREEN), 
                                   ('ai', YELLOW), ('fix', RED), ('cache', CYAN)]:
                if op_name in point:
                    thread_count = point[op_name]
                    op_bottom = cumulative
                    op_top = cumulative + thread_count
                    cumulative += thread_count
                    
                    # Check if this level intersects with operation's range
                    # Using log scale for better visibility
                    if op_top >= level_value and op_bottom < level_value:
                        line += color + BLOCK + RESET
                        char_added = True
                        break
            
            if not char_added:
                line += " "
        
        print(line)
    
    # Timeline axis - pip install style with BLINKING last char!
    # [colored progress] [BLINKING last] [gap] [grey to terminal width]
    import shutil
    terminal_width = shutil.get_terminal_size().columns
    
    # Find last data point
    last_data_idx = -1
    for i in range(len(timeline) - 1, -1, -1):
        if timeline[i]:
            last_data_idx = i
            break
    
    # Count visible characters
    visible_start = "    ┗━━"
    visible_gap = 1
    visible_end = 1  # For ┛
    
    timeline_line = f"{GRAY}{visible_start}{RESET}"
    
    # Colored portion (solid progress)
    for i in range(len(timeline)):
        if i < last_data_idx:
            # Solid colored progress
            timeline_line += f"{GREEN}━{RESET}"
        elif i == last_data_idx:
            # BLINKING last character (washed/faded green ↔ grey)
            # For demo, show as faded green (in real implementation, this would blink)
            FADED_GREEN = '\033[38;5;65m'  # Washed out green
            timeline_line += f"{FADED_GREEN}━{RESET}"  # This would blink with grey in real impl
        else:
            # Past data - don't draw anything yet
            break
    
    # VISIBLE GAP (space between progress and grey remainder)
    timeline_line += " "
    
    # Grey extension to terminal width
    visible_so_far = len(visible_start) + (last_data_idx + 1) + visible_gap
    remaining = terminal_width - visible_so_far - visible_end
    
    if remaining > 0:
        timeline_line += f"{GRAY}{'━' * remaining}┛{RESET}"
    else:
        timeline_line += f"{GRAY}┛{RESET}"
    
    print(timeline_line)
    
    # Time labels (showing seconds)
    time_labels = "      "
    for i in range(0, len(timeline), max(len(timeline) // 8, 1)):
        # Simulate time in seconds
        time_sec = i * 7  # ~7 seconds per point in this demo
        time_labels += f"{GRAY}{time_sec:02d}     {RESET}"
    print(time_labels)
    
    print("\n" + "─"*80)
    print(f"  {BLUE}⣿{RESET} Discovery   {GREEN}⣿{RESET} Execution   {YELLOW}⣿{RESET} AI Analysis   {RED}⣿{RESET} Auto-fix   {CYAN}⣿{RESET} Cache")
    print("  Vertical bars = Stacked operations at each time point")
    print("─"*80 + "\n")


if __name__ == "__main__":
    print("\n🎨 CHART DESIGN PROPOSAL\n")
    render_demo_chart()
    print("\nKEY FEATURES:")
    print("  ✓ Vertical colored bars (each column = one time point)")
    print("  ✓ Stacked colors (bottom to top: Blue → Green → Yellow → Red → Cyan)")
    print("  ✓ Full terminal width")
    print("  ✓ Time-based X-axis (seconds)")
    print("  ✓ NO dotted baseline")
    print("  ✓ Each color = operation type consuming threads")
    print("\n" + "="*80)
    print("  Does this match your vision? (Run: python demo_chart_proposal.py)")
    print("="*80 + "\n")
