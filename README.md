# PTSD Agent

**Progressive Test Status Dashboard** - A universal, intelligent test runner with rich diagnostics and beautiful terminal UI.

## Features

- 🚀 **Universal Test Runner** - Support for pytest (more frameworks coming)
- 📊 **Rich Diagnostics** - Detailed warnings, errors, failures, and skip tracking
- 🌲 **Tree View** - Hierarchical display of test results
- 📈 **Progress Tracking** - Real-time progress with accurate test counts
- 💾 **History & Trends** - SQLite-based test run history
- 🔗 **Dependency Tracking** - Cross-component dependency management
- 🎯 **Known Issues Registry** - Document and filter known test problems
- 🔌 **MCP Integration** - Model Context Protocol support for AI tools
- ⚡ **Parallel Execution** - Component-level and test-level parallelism

## Quick Start

### Installation

```bash
pip install ptsd-agent
```

### Basic Usage

```bash
# Run all tests
ptsd_agent --run-tests

# Run specific phase/component
ptsd_agent --run-tests --phase 2 --component rag_core

# Show overview without running tests
ptsd_agent --overview

# View diagnostics
ptsd_agent --run-tests --diagnostics

# Parallel execution
ptsd_agent --run-tests --parallel 12
```

## Configuration

Create `.ptsd.yaml` in your project root:

```yaml
project:
  name: "My Project"
  root: "."

structure:
  type: "phases"
  phases:
    - id: 1
      name: "Foundation"
      components:
        - name: "core"
          path: "src/core"
          tests: "tests/unit/core"

execution:
  parallel_workers: 12
  framework: pytest
  venv_detection: true

diagnostics:
  tree_view: true
  show_known_issues: false
```

## Documentation

- [Getting Started](docs/getting_started.md)
- [Configuration Guide](docs/configuration.md)
- [MCP Integration](docs/mcp_integration.md)
- [Development Guide](.ai/DEVELOPMENT_GUIDE.md)

## For AI Agents

If you're an AI agent working on this project, start here:
- [.ai/README.md](.ai/README.md) - Quick start guide
- [.ai/ARCHITECTURE.md](.ai/ARCHITECTURE.md) - System architecture
- [.ai/CONTRACTS.md](.ai/CONTRACTS.md) - API contracts
- [.ai/DEVELOPMENT_GUIDE.md](.ai/DEVELOPMENT_GUIDE.md) - Development workflow

## License

MIT License - see LICENSE file for details
