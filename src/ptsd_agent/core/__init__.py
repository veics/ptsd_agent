"""Core package initialization."""

from ptsd_agent.core.types import (
    TestStatus,
    DiagnosticType,
    DiagnosticCategory,
    TestFile,
    TestUnit,
    ProgressUpdate,
    Warning,
    Failure,
    Error,
    SkippedTest,
    Diagnostics,
    TestResult,
    ComponentMetrics,
    PhaseMetrics,
    TestRunSummary,
    ExecutionConfig,
)

from ptsd_agent.core.interfaces import (
    TestDiscoverer,
    TestExecutor,
    MetricsCollector,
    UIRenderer,
    HistoryStore,
)

__all__ = [
    # Types
    "TestStatus",
    "DiagnosticType",
    "DiagnosticCategory",
    "TestFile",
    "TestUnit",
    "ProgressUpdate",
    "Warning",
    "Failure",
    "Error",
    "SkippedTest",
    "Diagnostics",
    "TestResult",
    "ComponentMetrics",
    "PhaseMetrics",
    "TestRunSummary",
    "ExecutionConfig",
    # Protocols
    "TestDiscoverer",
    "TestExecutor",
    "MetricsCollector",
    "UIRenderer",
    "HistoryStore",
]
