import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TestResult:
    name: str
    status: str  # 'passed', 'failed', 'error', 'skipped'
    duration: float
    message: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ComponentMetrics:
    name: str
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    warnings: int = 0  # Pytest warnings count
    coverage: float = -1.0  # -1 = n/a (not applicable, e.g. YAML files)
    duration: float = 0.0
    discovered_total: int = 0  # Set before tests run, for progress calculation
    file_count: int = 0  # Number of test files in component
    test_file_count: int = 0  # Total test count from file scanning
    is_approximate: bool = True  # NEW: Track if counts are approximate (fast) or exact (pytest)
    tests: List[TestResult] = field(default_factory=list)
    
    # NEW: Detailed diagnostic information for --show-logs and Phase Overview
    failures: List[Dict[str, str]] = field(default_factory=list)
    # Each failure: {"test_name": str, "reason": str, "location": str}
    
    test_errors: List[Dict[str, str]] = field(default_factory=list)
    # Each error: {"test_name": str, "error_type": str, "message": str, "location": str}
    
    warning_details: List[Dict[str, str]] = field(default_factory=list)
    # Each warning: {"category": str, "message": str, "location": str}
    
    skipped_tests: List[Dict[str, str]] = field(default_factory=list)
    # Each skipped: {"test_name": str, "reason": str, "marker": str}

    @property
    def total(self) -> int:
        # Use discovered_total if set and no tests have run yet
        executed = self.passed + self.failed + self.errors + self.skipped
        return executed if executed > 0 else self.discovered_total

    @property
    def pass_rate(self) -> float:
        # Pass rate is passed / (passed + failed + errors) - skipped tests don't count
        executed = self.passed + self.failed + self.errors
        if executed == 0:
            return 0.0
        return (self.passed / executed) * 100

class MetricsCollector:
    """Collects and aggregates test metrics at all levels"""
    
    def __init__(self):
        self.components: Dict[str, ComponentMetrics] = {}
        self.start_time = time.time()
        self.skip_events: List[Dict] = []  # Track skip events for audit trail

    def get_component(self, name: str) -> ComponentMetrics:
        if name not in self.components:
            self.components[name] = ComponentMetrics(name=name)
        return self.components[name]

    def record_test(self, component_name: str, test: TestResult):
        comp = self.get_component(component_name)
        comp.tests.append(test)
        if test.status == 'passed':
            comp.passed += 1
        elif test.status == 'failed':
            comp.failed += 1
        elif test.status == 'error':
            comp.errors += 1
        elif test.status == 'skipped':
            comp.skipped += 1
        comp.duration += test.duration

    def set_coverage(self, component_name: str, coverage: float):
        comp = self.get_component(component_name)
        comp.coverage = coverage

    def set_discovered_total(self, component_name: str, count: int):
        """Set expected test count before tests run (for progress calculation)"""
        comp = self.get_component(component_name)
        comp.discovered_total = count

    def set_warnings(self, component_name: str, count: int):
        """Set warning count from pytest output"""
        comp = self.get_component(component_name)
        comp.warnings = count

    def set_file_stats(self, component_name: str, file_count: int, test_count: int = 0):
        """Set file and test count statistics for component"""
        comp = self.get_component(component_name)
        comp.file_count = file_count
        if test_count > 0:
            comp.test_file_count = test_count

    def get_summary(self) -> Dict:
        total_passed = sum(c.passed for c in self.components.values())
        total_failed = sum(c.failed for c in self.components.values())
        total_errors = sum(c.errors for c in self.components.values())
        total_skipped = sum(c.skipped for c in self.components.values())
        duration = time.time() - self.start_time
        
        total = total_passed + total_failed + total_errors + total_skipped
        pass_rate = (total_passed / total * 100) if total > 0 else 0.0
        
        return {
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "skipped": total_skipped,
            "total": total,
            "pass_rate": pass_rate,
            "duration": duration,
            "component_count": len(self.components)
        }
