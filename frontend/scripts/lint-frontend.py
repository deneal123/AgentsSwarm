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

def run_bundle_smoke_check():
    budget_bytes = int(os.getenv("FRONTEND_BUNDLE_BUDGET_BYTES", str(900 * 1024)))
    dist_dir = frontend_dir / "dist" / "assets"
    if not dist_dir.exists():
        print("Bundle smoke check failed: dist/assets not found")
        return 1

    js_files = list(dist_dir.glob("*.js"))
    if not js_files:
        print("Bundle smoke check failed: no JS bundles found")
        return 1

    largest_bundle = max(js_files, key=lambda file: file.stat().st_size)
    largest_size = largest_bundle.stat().st_size
    total_size = sum(file.stat().st_size for file in js_files)

    print(f"Bundle budget bytes: {budget_bytes}")
    print(f"Largest JS bundle: {largest_bundle.name} ({largest_size} bytes)")
    print(f"Total JS bundles size: {total_size} bytes")

    if largest_size > budget_bytes:
        print("Bundle smoke check failed: largest JS bundle exceeds budget")
        return 1
    return 0

# Run lint then format check. Return non-zero if any step fails.
exit_code = 0
exit_code = run("npm run lint") or exit_code
if exit_code == 0:
    exit_code = run("npm run format -- --check") or exit_code
if exit_code == 0:
    exit_code = run("npm run build") or exit_code
if exit_code == 0:
    exit_code = run_bundle_smoke_check() or exit_code

sys.exit(exit_code)
