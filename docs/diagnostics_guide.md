# PTSD Agent Diagnostics Guide

## Display Modes

### Flat View (Default)

Traditional list-based diagnostic display:

```
Diagnostics (3 wr | 2 sk | 1 fl)                                    ▼

    === Warnings (3) ===
    [1] DeprecationWarning: message...
    [2] UserWarning: message...
    
    === Skipped Tests (2) ===
    [1] component::test_name
        → Reason: ... (SKIPIF)
```

### Tree View (New in v0.7.0)

Hierarchical tree display matching test execution structure:

```
Diagnostics (15 total: [8 wr | 4 sk | 2 fl | 1 er])                 ▼

✓ Phase 1: Architecture & Foundation                 [8 wr | 4 sk] ▼
  ├─ architecture                                         [7 wr] ▼
  │  └─ Warnings (7)                                              ▼
  │     ├─ tests/integration/architecture/test_core.py       (3) ►
  │     └─ tests/integration/architecture/test_schema.py     (4) ►
  │
  └─ acl                                              [1 wr | 4 sk] ▼
     ├─ Warnings (1)                                                ►
     └─ Skipped Tests (4)                                          ▼
        └─ tests/acl/test_permissions.py                       (4) ▼
```

**Benefits:**
- Shows hierarchy: Phase → Component → Type → File → Test
- Matches test execution tree structure
- File-level grouping for better context
- Smart filtering (hides clean branches)
- Easier to locate specific component issues

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

### Enable Tree View

```bash
ptsd_agent --diagnostics --diagnostics-tree
```

Shows diagnostics in hierarchical tree format instead of flat list.

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
ptsd_agent --phase 2 --component models --diagnostics --diagnostics-tree
```

Show detailed tree-view diagnostics for the `models` component in Phase 2.

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

Configure diagnostic behavior in `ptsd_agent.config.json`:

```json
{
  "diagnostics": {
    "show_diagnostics": false,
    "use_tree_view": false,
    "diagnostics_limits": {
      "max_warnings": 20,
      "max_errors": 10,
      "max_failures": 10,
      "max_skipped": 50
    }
  }
}
```

**Options:**
- `show_diagnostics`: Enable diagnostics by default
- `use_tree_view`: Use tree view instead of flat view
- `diagnostics_limits`: Limit displayed items per category

## Best Practices

1. **Start broad, then narrow**: Run full suite first, then use filters
2. **Use tree view for complex projects**: Better for multi-phase/component setups
3. **Use flat view for quick scans**: Faster to read for simple projects
4. **Check warnings regularly**: Warnings often indicate future problems
5. **Document skip reasons**: Use clear, actionable skip messages
6. **Filter effectively**: Use `--phase` and `--component` to focus

## Examples

### Find all warnings in Phase 2 (tree view)

```bash
ptsd_agent --phase 2 --diagnostics --diagnostics-tree | grep "Warning"
```

### Check skip reasons for a component

```bash
ptsd_agent --component auth --diagnostics | grep "Reason:"
```

### Get full diagnostic report (tree view)

```bash
ptsd_agent --diagnostics --diagnostics-tree > diagnostics_report.txt
```

## Troubleshooting

**Q: Diagnostics not showing?**  
A: Ensure you're using `--diagnostics` flag or have enabled it in config

**Q: Too many warnings?**  
A: Use `max_warnings_displayed` in config to limit output

**Q: Tree view not working?**  
A: Ensure both `--diagnostics` and `--diagnostics-tree` flags are set

**Q: How to make tree view default?**  
A: Set `"use_tree_view": true` in `ptsd_agent.config.json`

---

**Version**: 0.7.0-dev  
**Updated**: 2025-12-28
