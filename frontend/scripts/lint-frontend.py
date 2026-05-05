#!/usr/bin/env python3
"""Cross-platform frontend linting script (moved to frontend/scripts)."""
import os
import subprocess
import sys
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()
# frontend_dir is current directory (script lives in frontend/scripts)
frontend_dir = script_dir.parent

# Change to frontend directory
os.chdir(frontend_dir)


def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode


# Run lint then format check. Return non-zero if any step fails.
exit_code = 0
exit_code = run("npm run lint") or exit_code
if exit_code == 0:
    # run prettier in check mode
    exit_code = run("npm run format -- --check") or exit_code

sys.exit(exit_code)
