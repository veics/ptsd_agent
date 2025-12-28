# PTSD Agent Diagnostics Guide

## Overview

The PTSD Agent provides comprehensive diagnostic capabilities to help you understand test failures, warnings, and skip reasons. This guide shows you how to effectively use the diagnostic features.

## Basic Diagnostic Display

By default, the PTSD Agent shows aggregated metrics in a compact format:

```
[war | fail | err | skip | cov | pass%]
```

- **war**: Warning count
- **fail**: Test failure count  
- **err**: Test error count
- **skip**: Skipped test count
- **cov**: Code coverage percentage
- **pass%**: Pass rate percentage

## Command-Line Options

### Show Detailed Diagnostics

```bash
ptsd_agent --diagnostics
```

Displays detailed diagnostic information including:
- Individual warning messages with source files
- Skip reasons for each skipped test
- Failure details with stack traces
- Error messages with locations

### Filter by Phase

```bash
ptsd_agent --phase 2
```

Run and show diagnostics only for Phase 2 components.

### Filter by Component

```bash
ptsd_agent --component rag_core
```

Run and show diagnostics only for the specified component.

### Combine Filters

```bash
ptsd_agent --phase 2 --component models --diagnostics
```

Show detailed diagnostics for the `models` component in Phase 2.

## Understanding Diagnostics

### Warnings

Warnings indicate potential issues that don't cause test failures:

```
DeprecationWarning: np.bool is deprecated (from test_utils.py::test_array_handling)
```

**Format**: `<WarningType>: <message> (from <source_file>::<test_name>)`

### Skipped Tests

Tests can be skipped for various reasons:

```
test_database_migration - Reason: Database not available (SKIPIF)
```

**Common skip markers**:
- `SKIPIF`: Conditional skip based on environment
- `SKIP`: Explicitly marked as skip
- `XFAIL`: Expected to fail (known issue)

### Failures

Test assertion failures show:
- Test name and location
- Assertion that failed
- Expected vs actual values

### Errors

Test execution errors show:
- Error type (ImportError, AttributeError, etc.)
- Error message
- Location where error occurred

## Integration with MCP Tools

The PTSD Agent provides MCP tools for programmatic access:

```python
# Diagnose entire project
diagnose()

# Diagnose specific component
diagnose(scope="component:acl", filter="failures")

# View logs and history
diagnose(include=["logs", "history"])
```

## Configuration

Configure diagnostic behavior in `.ptsd.yaml`:

```yaml
diagnostics:
  show_warnings: true
  show_skipped: true
  max_warnings_displayed: 20
  capture_warning_source: true  # NEW in v0.7.0
```

## Best Practices

1. **Start broad, then narrow**: Run full suite first, then use filters
2. **Check warnings regularly**: Warnings often indicate future problems
3. **Document skip reasons**: Use clear, actionable skip messages
4. **Use diagnostic help**: Run with `--diagnostics` to understand issues
5. **Filter effectively**: Use `--phase` and `--component` to focus

## Examples

### Find all warnings in Phase 2

```bash
ptsd_agent --phase 2 --diagnostics | grep "Warning"
```

### Check skip reasons for a component

```bash
ptsd_agent --component auth --diagnostics | grep "Reason:"
```

### Get full diagnostic report

```bash
ptsd_agent --diagnostics > diagnostics_report.txt
```

## Troubleshooting

**Q: Diagnostics not showing?**  
A: Ensure you're using `--diagnostics` flag or have enabled it in config

**Q: Too many warnings?**  
A: Use `max_warnings_displayed` in config to limit output

**Q: Warning source file missing?**  
A: Update to v0.7.0+ which includes warning source attribution

**Q: How to filter known issues?**  
A: Use the Known Issues Registry (coming in Phase 4)

---

**Version**: 0.7.0-dev  
**Updated**: 2025-12-28
