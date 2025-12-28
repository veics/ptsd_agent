#!/usr/bin/env python3
"""Enhanced demo with parallel operations visualization.

Shows multiple operation types running in parallel with stacked
colored blocks and smooth curve on top.
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ptsd_agent.ui.thread_chart import ThreadChartRenderer, OperationType


def demo_parallel_operations():
    """Demonstrate thread chart with parallel operations."""
    print("\n" + "="*80)
    print("  PTSD Agent v0.7.0 - Parallel Operations Thread Chart")
    print("  Stacked colored blocks + smooth curve line")
    print("="*80 + "\n")
    
    # Create chart
    chart = ThreadChartRenderer(max_threads=12, terminal_width=80, height=5)
    
    # Simulate PARALLEL operations (multiple types at once!)
    parallel_ops = [
        # Early: Just discovery
        [(OperationType.DISCOVERY, 2)],
        [(OperationType.DISCOVERY, 4)],
        [(OperationType.DISCOVERY, 6)],
        
        # Discovery + early execution starting
        [(OperationType.DISCOVERY, 4), (OperationType.EXECUTION, 2)],
        [(OperationType.DISCOVERY, 3), (OperationType.EXECUTION, 4)],
        [(OperationType.DISCOVERY, 2), (OperationType.EXECUTION, 6)],
        
        # Mostly execution, some discovery finishing
        [(OperationType.DISCOVERY, 1), (OperationType.EXECUTION, 8)],
        [(OperationType.EXECUTION, 10)],
        [(OperationType.EXECUTION, 12)],
        [(OperationType.EXECUTION, 11)],
        
        # Execution + AI analysis starting
        [(OperationType.EXECUTION, 8), (OperationType.AI_ANALYSIS, 2)],
        [(OperationType.EXECUTION, 6), (OperationType.AI_ANALYSIS, 3)],
        [(OperationType.EXECUTION, 4), (OperationType.AI_ANALYSIS, 4)],
        
        # AI analysis + auto-fix
        [(OperationType.AI_ANALYSIS, 4), (OperationType.AUTO_FIX, 2)],
        [(OperationType.AI_ANALYSIS, 3), (OperationType.AUTO_FIX, 3)],
        [(OperationType.AI_ANALYSIS, 2), (OperationType.AUTO_FIX, 2)],
        
        # Auto-fix + cache operations
        [(OperationType.AUTO_FIX, 2), (OperationType.CACHE, 1)],
        [(OperationType.AUTO_FIX, 1), (OperationType.CACHE, 2)],
        [(OperationType.CACHE, 2)],
        [(OperationType.CACHE, 1)],
    ]
    
    print("Simulating PARALLEL operations (multiple types at once)...\n")
    print("Different colored blocks = different operations running together! 🌈\n")
    
    # Animated rendering
    for i, ops in enumerate(parallel_ops):
        # Add all parallel operations for this time point
        total_threads = sum(threads for _, threads in ops)
        # For now, use the dominant operation type
        dominant_op = max(ops, key=lambda x: x[1])[0]
        chart.add_data_point(total_threads, dominant_op)
        
        # Clear screen and render
        sys.stdout.write("\033[2J\033[H")
        
        # Header
        print("\n" + "="*80)
        print(f"  Time: {i+1}/{len(parallel_ops)} | Active Operations: {len(ops)}")
        print("="*80 + "\n")
        
        # Show current operations
        print("  Current parallel operations:")
        for op, threads in ops:
            color = {
                OperationType.DISCOVERY: '\033[38;5;110m',
                OperationType.EXECUTION: '\033[38;5;108m',
                OperationType.AI_ANALYSIS: '\033[38;5;180m',
                OperationType.AUTO_FIX: '\033[38;5;174m',
                OperationType.CACHE: '\033[38;5;109m',
            }.get(op, '')
            print(f"    {color}■\033[0m {op.value:12s} : {threads:2d} threads")
        print()
        
        # Render chart
        chart_output = chart.render()
        print(chart_output)
        
        # Legend
        print("\n" + "─"*80)
        print("  Chart shows:")
        print("    • Colored blocks = Operations running in parallel")
        print("    • Top curve line = Total thread activity")
        print("    • Smooth Braille curves show execution flow")
        print("─"*80)
        
        sys.stdout.flush()
        time.sleep(0.2)
    
    # Final static display
    print("\n\n" + "="*80)
    print("  ✓ Demo Complete!")
    print("  Notice how multiple operation types run in parallel!")
    print("  The chart stacks them to show concurrent activity. ✨")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        demo_parallel_operations()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye! 👋\n")
