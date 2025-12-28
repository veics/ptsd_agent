#!/usr/bin/env python3
"""Demo script to test the new metrics format."""

from ptsd_agent.ui.legacy_components import MetricsBlock

# Create metrics block instance
metrics = MetricsBlock()

print("=" * 60)
print("PTSD Agent v0.7.0-dev: New Metrics Format Demo")
print("=" * 60)
print()

# Test various metric combinations
test_cases = [
    {
        "name": "Perfect Component",
        "war": 0, "fail": 0, "err": 0, "skip": 0, "cov": 100, "total": 50, "pass_rate": 100
    },
    {
        "name": "Component with Warnings",
        "war": 5, "fail": 0, "err": 0, "skip": 2, "cov": 95, "total": 48, "pass_rate": 100
    },
    {
        "name": "Component with Failures",
        "war": 2, "fail": 3, "err": 0, "skip": 1, "cov": 85, "total": 50, "pass_rate": 92
    },
    {
        "name": "Component with Errors",
        "war": 1, "fail": 2, "err": 3, "skip": 0, "cov": 75, "total": 45, "pass_rate": 87
    },
    {
        "name": "Mixed Issues",
        "war": 10, "fail": 5, "err": 2, "skip": 8, "cov": 68, "total": 100, "pass_rate": 85
    },
    {
        "name": "No Coverage (YAML)",
        "war": 0, "fail": 0, "err": 0, "skip": 0, "cov": -1, "total": 0, "pass_rate": 0
    }
]

print("Format: [war | fail | err | skip | cov | pass%]")
print("Old format was: [cov | war | fail | err | skip | total | pass%]")
print()
print("-" * 60)

for test in test_cases:
    name = test.pop("name")
    rendered = metrics.render(**test)
    print(f"{name:30s} {rendered}")

print("-" * 60)
print()
print(f"✓ Width: {metrics.width} chars (down from 49)")
print("✓ Order: warnings → failures → errors → skips → coverage → pass%")
print("✓ Total count removed (redundant)")
print()
print("=" * 60)
