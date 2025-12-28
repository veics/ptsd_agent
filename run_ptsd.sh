#!/bin/bash
# PTSD Agent v0.7.0-dev Test Runner
# Run this script to test PTSD Agent on RAGE with all Phase 1+2 features

cd /Users/vx/github/ptsd_agent
source .venv/bin/activate
PYTHONPATH=/Users/vx/github/ptsd_agent/src python -m ptsd_agent.cli.legacy_main "$@"
