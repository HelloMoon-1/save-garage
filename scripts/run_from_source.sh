#!/bin/bash
# Runs Save Garage from source on macOS or Linux: creates a virtual environment on first run.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; }
exec .venv/bin/python engine/main.py --open "$@"
