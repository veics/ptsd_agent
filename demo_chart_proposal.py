#!/usr/bin/env python3
"""FINAL DESIGN - Braille chart with prominent curve and crisp edges.

User specification:
- Prominent color curve line (top edge)
- Crisp edges/peaks showing transitions
- Each block colored by operation type
- Green timeline → blink (1 block) → gap → grey
"""

import time
import sys

# ANSI colors
RESET = '\033[0m'
GRAY = '\033[38;5;240m'
BLUE = '\033[38;5;110m'    # Discovery
GREEN = '\033[38;5;108m'   # Execution  
YELLOW = '\033[38;5;180m'  # AI
RED = '\033[38;5;174m'     # Auto-fix
CYAN = '\033[38;5;109m'    # Cache
FADED_GREEN = '\033[38;5;65m'

# Braille characters for different purposes
FULL_BLOCK = '⣿'  # Dense block for filled areas
EDGE_CHARS = '⣸⣰⣇⣀⢀⡀'  # For prominent curve/edges
SPARSE_CHARS = '⠊⠑⠒⠱⠴⠳'  # For crisp peaks


def get_operation_color(operations, level):
    """Get the color for the operation at this level."""
    cumulative = 0
    
    for op, color in [('discovery', BLUE), ('execution', GREEN),
                     ('ai', YELLOW), ('fix', RED), ('cache', CYAN)]:
        if op in operations:
            count = operations[op]
            bottom = cumulative
            top = cumulative + count
            cumulative += count
            
            # If this level is within this operation's range
            if level <= top and level > bottom:
                return color, op
    
    return None, None


def main():
    """Run animated demo."""
    print("\n" + "="*80)
    print("  FINAL DESIGN: Prominent Curve + Crisp Edges + Colored Blocks")
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
    
    levels = [12, 9, 6, 3, 1]  # 5 levels!
    
    # Animation loop
    for frame in range(len(timeline)):
        sys.stdout.write("\033[2J\033[H")
        
        print(f"\n{'='*80}")
        print(f"  Frame {frame + 1}/{len(timeline)}")
        print(f"{'='*80}\n")
        
        # Calculate total threads for each point up to current frame
        totals = []
        for i in range(frame + 1):
            totals.append(sum(timeline[i].values()))
        
        # Render each level
        for level_idx, level in enumerate(levels):
            # Y-axis label
            label = f"{GRAY}{level:3d} ┃{RESET}" if level > 1 else f"{GRAY}  {level} ┃{RESET}"
            line = label
            
            # Render each column
            for i in range(frame + 1):
                point = timeline[i]
                total = totals[i]
                
                if total == 0:
                    line += " "
                    continue
                
                # Get color for this level
                color, op = get_operation_color(point, level)
                
                if level_idx == 0:
                    # PROMINENT YELLOW CURVE - tracks data closely!
                    # Show when max data is within 3 levels
                    max_here = max(totals[max(0, i-1):min(len(totals), i+2)]) if totals else 0
                    if max_here > level - 3:
                        sparse_char = SPARSE_CHARS[i % len(SPARSE_CHARS)]
                        line += YELLOW + sparse_char + RESET  # Always YELLOW!
                    else:
                        line += " "
                elif color:
                    # Check for crisp edges at operation transitions
                    prev_color, prev_op = None, None
                    if i > 0:
                        prev_color, prev_op = get_operation_color(timeline[i-1], level)
                    
                    # CREATIVE CRISP EDGES - variety of partial Braille!
                    if prev_op and prev_op != op:
                        # Choose edge char based on transition type
                        edge_varieties = [
                            '⣸',  # Left-heavy  (discovery→execution)
                            '⣰',  # Top-left    (execution→ai)
                            '⣇',  # Right-heavy (ai→fix)
                            '⣀',  # Bottom      (fix→cache)
                            '⢀',  # Top-right   (cache→discovery)
                            '⡀',  # Top-left dot
                            '⠄',  # Middle dots
                            '⠂',  # Vertical dots
                        ]
                        op_list = ['discovery', 'execution', 'ai', 'fix', 'cache']
                        try:
                            edge_idx = (op_list.index(prev_op) * 2 + op_list.index(op)) % len(edge_varieties)
                        except ValueError:
                            edge_idx = 0
                        edge_char = edge_varieties[edge_idx]
                        line += color + edge_char + RESET
                    else:
                        # Full 8-dot block (⣿)
                        line += color + FULL_BLOCK + RESET
                else:
                    line += " "
            
            print(line)
        
        # GREEN timeline with BLINKING last block
        import shutil
        tw = shutil.get_terminal_size().columns
        
        # Find last data point
        last_idx = -1
        for i in range(frame, -1, -1):
            if timeline[i]:
                last_idx = i
                break
        
        tl = f"{GRAY}    ┗━━{RESET}"
        
        # GREEN progress
        for i in range(frame + 1):
            if i < last_idx:
                tl += f"{GREEN}━{RESET}"
            elif i == last_idx:
                # BLINK: washed green ↔ grey
                if frame % 2 == 0:
                    tl += f"{FADED_GREEN}━{RESET}"
                else:
                    tl += f"{GRAY}━{RESET}"
        
        # Gap + grey to terminal width
        tl += " "
        vis = 7 + (last_idx + 1 if last_idx >= 0 else 0) + 1
        remaining = tw - vis - 1
        if remaining > 0:
            tl += f"{GRAY}{'━' * remaining}┛{RESET}"
        else:
            tl += f"{GRAY}┛{RESET}"
        
        print(tl)
        
        sys.stdout.flush()
        time.sleep(0.2)
    
    print("\n" + "="*80)
    print("  ✓ Final design complete!")
    print(f"  - Prominent curve: {YELLOW}⠊⠑⠒⠱⠴⠳{RESET}")
    print(f"  - Crisp edges: {GREEN}⣶⣿⣷{RESET}")
    print(f"  - Colored blocks: {BLUE}⣿{GREEN}⣿{YELLOW}⣿{RED}⣿{CYAN}⣿{RESET}")
    print(f"  - Timeline: {GREEN}━━━━{FADED_GREEN}━{RESET} {GRAY}━━━{RESET}")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye! 👋\n")
