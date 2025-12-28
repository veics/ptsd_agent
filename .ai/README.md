# PTSD Agent - AI Development Guide

## Quick Start for AI Agents

PTSD Agent is a **contracts-first** universal test runner. All interfaces are defined upfront before implementation.

**Key Principles:**
1. **Contracts First** - Define interfaces in `core/interfaces.py` before implementing
2. **Modularity** - Each component is pluggable via protocols
3. **Zero Duplication** - Shared code lives in `core/` and utilities
4. **Type Safety** - Full type hints, mypy strict mode
5. **Testability** - Every module has corresponding tests

## Project Structure

```
src/ptsd_agent/
├── core/          # Core abstractions & contracts
├── discovery/     # Test discovery engines  
├── execution/     # Test execution engines
├── metrics/       # Metrics collection & aggregation
├── diagnostics/   # Diagnostic analysis & parsing
├── dependencies/  # Dependency graph & tracking
├── ui/            # Terminal UI rendering
├── storage/       # Data persistence (SQLite)
├── mcp/           # MCP server & tools
└── cli/           # CLI interface
```

## Development Workflow

1. **Read** [ARCHITECTURE.md](ARCHITECTURE.md) - Understand system design
2. **Check** [CONTRACTS.md](CONTRACTS.md) - Review interfaces
3. **Follow** [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - Implementation patterns
4. **Test** [TESTING_GUIDE.md](TESTING_GUIDE.md) - Write tests

## Key Files

### For Understanding
- `ARCHITECTURE.md` - System overview, data flow, diagrams
- `CONTRACTS.md` - All protocol definitions
- `diagrams/` - Mermaid diagrams for visual understanding

### For Development
- `DEVELOPMENT_GUIDE.md` - Coding patterns, adding features
- `TESTING_GUIDE.md` - How to test PTSD Agent and target projects
- `examples/` - Real-world implementation examples

## Quick Reference

### Adding New Test Framework Support
1. Implement `TestDiscoverer` protocol in `discovery/your_framework.py`
2. Implement `TestExecutor` protocol in `execution/your_framework.py`
3. Register in config system
4. Add tests in `tests/unit/discovery/` and `tests/unit/execution/`

### Adding New UI Section
1. Define `UISection` protocol in `core/interfaces.py`
2. Implement in `ui/sections/your_section.py`
3. Register in `ui/renderer.py`
4. Write tests in `tests/unit/ui/`

### Adding New Diagnostic Type
1. Extend `DiagnosticType` enum in `core/types.py`
2. Add parser logic in `diagnostics/parser.py`
3. Update display in `ui/diagnostics.py`
4. Add classification rules in `diagnostics/classifier.py`

## YOLO Mode (Contracts-First Development)

Since all contracts are predefined, you can:
1. **Read the contract** - See what interface you need to implement
2. **Implement it** - Follow the protocol definition
3. **Type check** - Run `mypy` to verify compliance
4. **Test it** - Write tests against the contract

Example:
```python
# Contract is already defined in core/interfaces.py
from ptsd_agent.core.interfaces import TestDiscoverer

# Just implement it!
class MyDiscoverer:
    def discover_files(self, root: Path, patterns: List[str]) -> AsyncIterator[TestFile]:
        # Implementation here
        ...
```

## Getting Help

- Architecture questions → `ARCHITECTURE.md`
- Interface questions → `CONTRACTS.md`  
- Implementation patterns → `DEVELOPMENT_GUIDE.md`
- Testing strategy → `TESTING_GUIDE.md`
- Examples → `examples/`
