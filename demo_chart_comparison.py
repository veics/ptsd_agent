#!/usr/bin/env python3
"""Demo comparing both chart versions side by side."""

import time
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ptsd_agent.ui.thread_chart import ThreadChartRenderer, OperationType
from ptsd_agent.ui.thread_chart_v2 import ThreadChartRendererV2


def clear_screen():
    """Clear terminal."""
    print("\033[2J\033[H", end="")


def demo_comparison():
    """Run comparison demo showing both versions."""
    
    # Initialize both renderers
    chart_v1 = ThreadChartRenderer(max_threads=12, terminal_width=80, height=5)
    chart_v2 = ThreadChartRendererV2(max_threads=12, terminal_width=80, height=5)
    
    # Simulate test execution flow
    test_flow = [
        # Discovery phase
        *[{OperationType.DISCOVERY: 2} for _ in range(3)],
        *[{OperationType.DISCOVERY: 4} for _ in range(2)],
        
        # Discovery + Execution overlap
        *[{OperationType.DISCOVERY: 1, OperationType.EXECUTION: 5} for _ in range(2)],
        
        # Execution peak
        *[{OperationType.EXECUTION: 9} for _ in range(3)],
        
        # Execution + AI overlap
        *[{OperationType.EXECUTION: 6, OperationType.AI_ANALYSIS: 2} for _ in range(2)],
        
        # AI Analysis + Auto-Fix
        *[{OperationType.AI_ANALYSIS: 4, OperationType.AUTO_FIX: 2} for _ in range(2)],
        
        # Cache operations
        *[{OperationType.CACHE: 1} for _ in range(4)],
    ]
    
    # Feed data to both charts
    for i, ops in enumerate(test_flow):
        clear_screen()
        
        chart_v1.add_data_point(ops)
        chart_v2.add_data_point(ops)
        
        print("=" * 80)
        print(f"  Comparison Demo - Step {i+1}/{len(test_flow)}")
        print("=" * 80)
        print()
        
        # Show VERSION 1
        print("VERSION 1: Spaced Curve (Clear separation)")
        print("─" * 80)
        print(chart_v1.render())
        print()
        print()
        
        # Show VERSION 2
        print("VERSION 2: Sparse Dot Line (Minimal dots)")
        print("─" * 80)
        print(chart_v2.render())
        print()
        
        print("─" * 80)
        print("  🔵 Blue = Discovery  🟢 Green = Execution  🟡 Yellow = AI")
        print("  🔴 Red = Auto-Fix    🔷 Cyan = Cache")
        print("─" * 80)
        
        time.sleep(0.15)
    
    # Final display
    print()
    print("=" * 80)
    print("  ✓ Comparison complete! Which version do you prefer?")
    print("=" * 80)


if __name__ == "__main__":
    demo_comparison()
