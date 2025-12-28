#!/usr/bin/env python3
"""Demo script to test thread chart rendering.

Run this to see the minimalistic thread chart in action.
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ptsd_agent.ui.thread_chart import ThreadChartRenderer, OperationType


def demo_thread_chart():
    """Demonstrate thread chart rendering."""
    print("Thread Chart Demo")
    print("=" * 80)
    print()
    
    # Create chart
    chart = ThreadChartRenderer(max_threads=12, terminal_width=80)
    
    # Simulate test execution with varying thread usage
    operations = [
        (OperationType.DISCOVERY, 4),
        (OperationType.DISCOVERY, 6),
        (OperationType.DISCOVERY, 8),
        (OperationType.EXECUTION, 10),
        (OperationType.EXECUTION, 12),
        (OperationType.EXECUTION, 11),
        (OperationType.EXECUTION, 9),
        (OperationType.AI_ANALYSIS, 3),
        (OperationType.AI_ANALYSIS, 5),
        (OperationType.AUTO_FIX, 2),
        (OperationType.EXECUTION, 8),
        (OperationType.EXECUTION, 6),
        (OperationType.EXECUTION, 4),
        (OperationType.EXECUTION, 2),
    ]
    
    print("Simulating test execution with thread activity...")
    print()
    
    for i, (op_type, thread_count) in enumerate(operations):
        chart.add_data_point(thread_count, op_type)
        
        # Render chart
        sys.stdout.write("\r" + " " * 80 + "\r")  # Clear line
        chart_line = chart.render()
        sys.stdout.write(chart_line)
        sys.stdout.flush()
        
        time.sleep(0.2)  # Pause to show progression
    
    print()
    print()
    print("Chart Legend:")
    print("  Blue = Discovery")
    print("  Green = Execution")
    print("  Yellow = AI Analysis")
    print("  Orange = Auto-Fix")
    print()
    print("The chart shows thread utilization throughout the entire execution.")
    print("Width automatically scales to terminal width.")


if __name__ == "__main__":
    demo_thread_chart()
