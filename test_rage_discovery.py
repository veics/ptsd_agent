"""Test discovering RAGE project tests."""

import asyncio
from pathlib import Path
from ptsd_agent.discovery.pytest import PytestDiscoverer

async def main():
    discoverer = PytestDiscoverer()
    rage_root = Path("/Users/vx/github/rage/services/rag_core")
    
    print(f"Discovering tests in {rage_root}...")
    
    files = []
    async for file in discoverer.discover_files(
        rage_root,
        patterns=["test_*.py", "*_test.py"]
    ):
        estimated = discoverer.estimate_test_count(file)
        files.append((file, estimated))
        print(f"  {file.path.relative_to(rage_root)}: ~{estimated} tests")
    
    total_files = len(files)
    total_tests = sum(est for _, est in files)
    print(f"\n✓ Found {total_files} files with ~{total_tests} tests")

if __name__ == "__main__":
    asyncio.run(main())
