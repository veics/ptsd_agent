# PTSD Agent - Setup Instructions

## Copy Foundation to Actual Repository

```bash
# Create the actual repository location
mkdir -p /Users/vx/github/ptsd_agent

# Copy all foundation files
cp -r /Users/vx/github/rage/ptsd_agent_foundation/* /Users/vx/github/ptsd_agent/

# Initialize git
cd /Users/vx/github/ptsd_agent
git init
git add .
git commit -m "Initial commit: PTSD Agent foundation"
```

## Create Remaining Directory Structure

```bash
cd /Users/vx/github/ptsd_agent

# Create all module directories
mkdir -p src/ptsd_agent/{discovery,execution,metrics,diagnostics,dependencies,ui,storage,mcp,cli}
mkdir -p tests/{unit,integration,fixtures}

# Create __init__.py files
touch src/ptsd_agent/discovery/__init__.py
touch src/ptsd_agent/execution/__init__.py
touch src/ptsd_agent/metrics/__init__.py
touch src/ptsd_agent/diagnostics/__init__.py
touch src/ptsd_agent/dependencies/__init__.py
touch src/ptsd_agent/ui/__init__.py
touch src/ptsd_agent/storage/__init__.py
touch src/ptsd_agent/mcp/__init__.py
touch src/ptsd_agent/cli/__init__.py
```

## Install Development Environment

```bash
# Create virtual environment
python3.14 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
python -c "import ptsd_agent; print(ptsd_agent.__version__)"
```

## Next Steps

1. **Migrate code from RAGE** - Copy existing ptsd_agent code to appropriate modules
2. **Refactor to contracts** - Ensure all modules implement protocols
3. **Write tests** - Create unit tests for each module
4. **Update AI workspace** - Add `/Users/vx/github/ptsd_agent` to workspace

## Development Workflow

```bash
# Run tests
pytest

# Type check
mypy src/

# Format code
black src/ tests/

# Lint
ruff check src/ tests/
```

## Migration Checklist

- [ ] Copy foundation files to /Users/vx/github/ptsd_agent
- [ ] Create directory structure
- [ ] Install development environment
- [ ] Migrate discovery code
- [ ] Migrate execution code
- [ ] Migrate metrics code
- [ ] Migrate diagnostics code
- [ ] Migrate UI code
- [ ] Migrate storage code
- [ ] Migrate MCP server
- [ ] Migrate CLI
- [ ] Write unit tests
- [ ] Test against RAGE project
- [ ] Update documentation
