#!/usr/bin/env python3
"""Demo: Animated vertical stacked colored bars chart.

FINAL DESIGN - matches user requirements:
- Vertical stacked bars (each column = time point)
- No empty 0.0 line
- No leading spaces (bars start at left edge)
- Animated like pip progress bars
- Pip-style timeline (colored → faded last → gap → grey to terminal width)
"""

import time
import sys
from pathlib import Path

# ANSI colors
RESET = '\033[0m'
GRAY = '\033[38;5;240m'
BLUE = '\033[38;5;110m'    # Discovery
GREEN = '\033[38;5;108m'   # Execution  
YELLOW = '\033[38;5;180m'  # AI Analysis
RED = '\033[38;5;174m'     # Auto-fix
CYAN = '\033[38;5;109m'    # Cache
FADED_GREEN = '\033[38;5;65m'  # Faded for blinking last char

# Braille dense block
BLOCK = '⣿'


def main():
    """Run animated demo."""
    print("\n" + "="*80)
    print("  ANIMATED DEMO: Vertical Stacked Colored Bars")
    print("="*80 + "\n")
    time.sleep(1)
    
    # Sample data
    timeline = [
        {'discovery': 2},
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
    ]
    
    levels = [12, 6, 3, 1]  # Skip 0.0
    
    # Animation loop
    for frame in range(len(timeline)):
        sys.stdout.write("\033[2J\033[H")  # Clear screen
        
        print(f"\n{'='*80}")
        print(f"  Frame {frame + 1}/{len(timeline)}")
        print(f"{'='*80}\n")
        
        # Render chart rows (NO empty 0.0 line, NO leading spaces)
        for level in levels:
            # Y-axis label
            label = f"{GRAY}{level:3d} ┃{RESET}" if level > 1 else f"{GRAY}  {level} ┃{RESET}"
            line = label
            
            # Render bars up to current frame
            for i in range(frame + 1):
                point = timeline[i]
                if not point:
                    line += " "
                    continue
                
                # Stack colors bottom-up
                cumulative = 0
                drawn = False
                
                for op, color in [('discovery', BLUE), ('execution', GREEN),
                                 ('ai', YELLOW), ('fix', RED), ('cache', CYAN)]:
                    if op in point:
                        count = point[op]
                        bottom = cumulative
                        top = cumulative + count
                        cumulative += count
                        
                        if top >= level and bottom < level:
                            line += color + BLOCK + RESET
                            drawn = True
                            break
                
                if not drawn:
                    line += " "
            
            print(line)
        
        # Pip-style timeline
        import shutil
        tw = shutil.get_terminal_size().columns
        
        # Find last data point
        last_idx = -1
        for i in range(frame, -1, -1):
            if timeline[i]:
                last_idx = i
                break
        
        tl = f"{GRAY}    ┗━━{RESET}"
        
        # Colored progress + faded last
        for i in range(frame + 1):
            if i < last_idx:
                tl += f"{GREEN}━{RESET}"
            elif i == last_idx:
                tl += f"{FADED_GREEN}━{RESET}"  # Blinking last char
        
        # Gap + grey to end
        tl += " "
        vis = 7 + (last_idx + 1 if last_idx >= 0 else 0) + 1
        remaining = tw - vis - 1
        if remaining > 0:
            tl += f"{GRAY}{'━' * remaining}┛{RESET}"
        else:
            tl += f"{GRAY}┛{RESET}"
        
        print(tl)
        
        sys.stdout.flush()
        time.sleep(0.15)
    
    print("\n" + "="*80)
    print("  ✓ Animation complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye! 👋\n")
