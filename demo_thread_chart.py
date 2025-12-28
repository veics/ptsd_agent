#!/usr/bin/env python3
"""Demo for Braille-only parallel operations chart."""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ptsd_agent.ui.thread_chart import ThreadChartRenderer, OperationType


def demo_braille_chart():
    """Demonstrate clean Braille-only chart."""
    print("\n" + "="*80)
    print("  PTSD Agent v0.7.0 - Braille-Only Thread Chart")
    print("  Clean stacked visualization with smooth curves")
    print("="*80 + "\n")
    
    chart = ThreadChartRenderer(max_threads=12, terminal_width=80, height=5)
    
    # Parallel operations timeline
    timeline = [
        # Discovery phase
        {OperationType.DISCOVERY: 2},
        {OperationType.DISCOVERY: 4},
        {OperationType.DISCOVERY: 6},
        {OperationType.DISCOVERY: 5, OperationType.EXECUTION: 2},
        {OperationType.DISCOVERY: 3, OperationType.EXECUTION: 4},
        
        # Execution phase
        {OperationType.EXECUTION: 8},
        {OperationType.EXECUTION: 10},
        {OperationType.EXECUTION: 12},
        {OperationType.EXECUTION: 11},
        {OperationType.EXECUTION: 9, OperationType.AI_ANALYSIS: 2},
        
        # Mixed phase
        {OperationType.EXECUTION: 6, OperationType.AI_ANALYSIS: 4},
        {OperationType.EXECUTION: 4, OperationType.AI_ANALYSIS: 5},
        {OperationType.AI_ANALYSIS: 6, OperationType.AUTO_FIX: 2},
        {OperationType.AI_ANALYSIS: 4, OperationType.AUTO_FIX: 3},
        
        # Cleanup
        {OperationType.AUTO_FIX: 3, OperationType.CACHE: 1},
        {OperationType.AUTO_FIX: 2, OperationType.CACHE: 2},
        {OperationType.CACHE: 2},
        {OperationType.CACHE: 1},
    ]
    
    print("Rendering Braille-only chart with parallel operations...\n")
    
    for i, ops in enumerate(timeline):
        chart.add_data_point(ops)
        
        sys.stdout.write("\033[2J\033[H")
        
        print("\n" + "="*80)
        print(f"  Time: {i+1}/{len(timeline)}")
        print("="*80 + "\n")
        
        print("  Active operations:")
        for op, threads in ops.items():
            color = {
                OperationType.DISCOVERY: '\033[38;5;110m',
                OperationType.EXECUTION: '\033[38;5;108m',
                OperationType.AI_ANALYSIS: '\033[38;5;180m',
                OperationType.AUTO_FIX: '\033[38;5;174m',
                OperationType.CACHE: '\033[38;5;109m',
            }.get(op, '')
            print(f"    {color}⣿\033[0m {op.value:12s} : {threads:2d} threads")
        print()
        
        print(chart.render())
        
        print("\n" + "─"*80)
        print("  \033[38;5;110m⣿\033[0m Blue   \033[38;5;108m⣿\033[0m Green   \033[38;5;180m⣿\033[0m Yellow   \033[38;5;174m⣿\033[0m Red   \033[38;5;109m⣿\033[0m Cyan")
        print("  Top line = Smooth curve  |  Blocks = Stacked operations")
        print("─"*80)
        
        sys.stdout.flush()
        time.sleep(0.2)
    
    print("\n\n" + "="*80)
    print("  ✓ Braille-only chart - clean and elegant! ✨")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        demo_braille_chart()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye! 👋\n")
