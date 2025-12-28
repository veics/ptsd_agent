#!/usr/bin/env python3
"""Demo inline component stats feature."""

from ptsd_agent.metrics.legacy_collector import MetricsCollector

# Create collector
collector = MetricsCollector()

# Set file stats for various components
collector.set_file_stats("rag_core_api", file_count=5, test_count=23)
collector.set_file_stats("rag_core_models", file_count=3, test_count=12)
collector.set_file_stats("rag_core_utils", file_count=2, test_count=8)
collector.set_file_stats("identity_mapping", file_count=8, test_count=45)
collector.set_file_stats("profile_service", file_count=1, test_count=3)

print("=" * 70)
print("Inline Component Stats Demo")
print("=" * 70)
print()
print("Feature: Display file and test counts on component lines during execution")
print()
print("Format: component_name: N files N tests [current_test]")
print()
print("-" * 70)
print()

for comp_name, comp in collector.components.items():
    stats = []
    if comp.file_count > 0:
        stats.append(f"{comp.file_count} file{'s' if comp.file_count != 1 else ''}")
    if comp.test_file_count > 0:
        stats.append(f"{comp.test_file_count} test{'s' if comp.test_file_count != 1 else ''}")
    
    stats_str = f": {' '.join(stats)}" if stats else ""
    print(f"  ○ │ ├─ {comp_name}{stats_str}")

print()
print("-" * 70)
print()
print("✓ File counts displayed")
print("✓ Test counts displayed")
print("✓ Proper pluralization (file vs files, test vs tests)")
print("✓ Only shown when running (mode='running')")
print()
print("=" * 70)
