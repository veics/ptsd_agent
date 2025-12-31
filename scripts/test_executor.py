#!/usr/bin/env python
import sys
print('Starting executor test...', flush=True)

from ptsd_agent.execution.legacy_executor import TestExecutor
from ptsd_agent.metrics.legacy_collector import MetricsCollector

collector = MetricsCollector()
executor = TestExecutor(collector, project_root='/Users/vx/github/rage')
print('Executor created, running single test file...', flush=True)

# Run just one test file
executor.run_component(1, 'architecture', 'tests/integration/architecture/test_100_coverage.py')
print('Execution complete', flush=True)

comp = collector.get_component('architecture')
print(f'\n=== RESULTS ===')
print(f'passed={comp.passed}, failed={comp.failed}, errors={comp.errors}, total={len(comp.tests)}')
print(f'\nTest statuses:')
for t in comp.tests:
    print(f'  {t.status}: {t.name}')
