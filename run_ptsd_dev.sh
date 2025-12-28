#!/bin/bash
# Quick wrapper to run PTSD Agent from source on current project

# Export PYTHONPATH to include ptsd_agent source
export PYTHONPATH=/Users/vx/github/ptsd_agent/src

# Run ptsd_agent CLI with all arguments passed through
python3 -m ptsd_agent.cli.legacy_main "$@"
