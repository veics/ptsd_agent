#!/usr/bin/env python3
"""Demo fast test counter."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ptsd_agent.discovery.fast_counter import FastTestCounter

# Create counter
counter = FastTestCounter()

print("=" * 70)
print("Fast Test Counter Demo")
print("=" * 70)
print()

# Test on ptsd_agent itself
root = Path(__file__).parent / "tests"
if root.exists():
    print(f"Scanning: {root}")
    print()
    
    results = counter.scan_directory(root)
    
    for file_path, count in sorted(results.items()):
        rel_path = file_path.relative_to(root)
        print(f"  {rel_path}: ~{count} tests")
    
    file_count, test_count = counter.get_summary(root)
    print()
    print(f"Summary: ~{test_count} tests in {file_count} files")
else:
    print("No tests directory found")

print()
print("=" * 70)
