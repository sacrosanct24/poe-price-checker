#!/usr/bin/env bash
# PoE Price Checker CI-equivalent unit test runner
# This script mirrors the project's CI-equivalent unit test command

set -euo pipefail

echo "=== PoE Price Checker CI-equivalent Unit Test Runner ==="
echo "Starting checks..."

# Ensure we're in the repo root
if [[ ! -f "main.py" || ! -f "requirements-dev.txt" ]]; then
    echo "Error: This script must be run from the poe-price-checker repository root"
    exit 1
fi

echo "Step 1: Checking for existing virtual environment..."
if [[ -d ".venv" ]]; then
    echo "Found existing .venv directory"
else
    echo "Creating new virtual environment..."
    python3 -m venv .venv
fi

echo "Step 2: Activating virtual environment..."
source .venv/bin/activate

echo "Step 3: Installing development dependencies..."
pip install -r requirements-dev.txt

echo "Step 4: Running CI-equivalent unit tests..."
pytest -m unit -q --durations=20 --ignore=tests/unit/gui_qt --ignore=tests/test_shortcuts.py

echo "=== checks: PASS ==="
echo "All CI-equivalent unit tests completed successfully"
