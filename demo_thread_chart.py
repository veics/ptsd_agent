#!/usr/bin/env python3
"""Enhanced demo script for thread chart visualization.

Shows beautiful Braille curves with varied thread activity patterns.
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ptsd_agent.ui.thread_chart import ThreadChartRenderer, OperationType


def demo_thread_chart():
    """Demonstrate thread chart with varied activity patterns."""
    print("\n" + "="*80)
    print("  PTSD Agent v0.7.0 - Thread Utilization Chart Demo")
    print("  Beautiful Braille curves with colored timeline")
    print("="*80 + "\n")
    
    # Create chart
    chart = ThreadChartRenderer(max_threads=12, terminal_width=80, height=5)
    
    # Simulate realistic test execution flow
    operations = [
        # Discovery phase - ramping up
        (OperationType.DISCOVERY, 2), (OperationType.DISCOVERY, 4),
        (OperationType.DISCOVERY, 6), (OperationType.DISCOVERY, 8),
        (OperationType.DISCOVERY, 10), (OperationType.DISCOVERY, 12),
        (OperationType.DISCOVERY, 11), (OperationType.DISCOVERY, 9),
        
        # Execution phase - high activity
        (OperationType.EXECUTION, 8), (OperationType.EXECUTION, 10),
        (OperationType.EXECUTION, 12), (OperationType.EXECUTION, 12),
        (OperationType.EXECUTION, 11), (OperationType.EXECUTION, 10),
        (OperationType.EXECUTION, 9), (OperationType.EXECUTION, 8),
        (OperationType.EXECUTION, 7), (OperationType.EXECUTION, 6),
        
        # AI analysis phase - medium activity
        (OperationType.AI_ANALYSIS, 4), (OperationType.AI_ANALYSIS, 5),
        (OperationType.AI_ANALYSIS, 6), (OperationType.AI_ANALYSIS, 5),
        (OperationType.AI_ANALYSIS, 4), (OperationType.AI_ANALYSIS, 3),
        
        # Auto-fix phase - sporadic
        (OperationType.AUTO_FIX, 2), (OperationType.AUTO_FIX, 4),
        (OperationType.AUTO_FIX, 3), (OperationType.AUTO_FIX, 2),
        
        # Cache operations - low activity
        (OperationType.CACHE, 1), (OperationType.CACHE, 2),
        (OperationType.CACHE, 1), (OperationType.CACHE, 0),
    ]
    
    print("Simulating test execution with realistic thread activity...\n")
    print("Watch the beautiful Braille curves form! 🌊\n")
    
    # Animated rendering
    for i, (op_type, thread_count) in enumerate(operations):
        chart.add_data_point(thread_count, op_type)
        
        # Clear screen and render
        sys.stdout.write("\033[2J\033[H")  # Clear and home
        
        # Header
        print("\n" + "="*80)
        print(f"  Progress: {i+1}/{len(operations)} data points")
        print("="*80 + "\n")
        
        # Render chart
        chart_output = chart.render()
        print(chart_output)
        
        # Legend
        print("\n" + "─"*80)
        print("  Chart Legend:")
        print("    \033[38;5;110m█\033[0m Blue    = Discovery")
        print("    \033[38;5;108m█\033[0m Green   = Execution")
        print("    \033[38;5;180m█\033[0m Yellow  = AI Analysis")
        print("    \033[38;5;174m█\033[0m Red     = Auto-Fix")
        print("    \033[38;5;109m█\033[0m Cyan    = Cache")
        print("─"*80)
        
        sys.stdout.flush()
        time.sleep(0.15)
    
    # Final static display
    print("\n\n" + "="*80)
    print("  ✓ Demo Complete!")
    print("  Chart shows thread utilization throughout entire execution.")
    print("  Notice the smooth Braille curves and colored timeline! ✨")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        demo_thread_chart()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye! 👋\n")
