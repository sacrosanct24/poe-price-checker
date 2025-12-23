# M3 — Flake8 Inventory (Pre-Removal)

**Date:** 2025-12-19
**Purpose:** Document all flake8 references before removing it from the project

## Summary

Flake8 is currently installed and used in multiple locations. This document inventories all references before M3 removes them.

## Flake8 References Found

### CI/CD Workflows

1. **`.github/workflows/ci.yml`** (lines 32, 34-36)
   - Line 32: `pip install flake8 mypy`
   - Lines 34-36: Dedicated "Lint (flake8)" step that runs `flake8 .`

2. **`.github/workflows/python-package.yml`** (lines 45, 48-51)
   - Line 45: `python -m pip install flake8 pytest pytest-cov pytest-xdist mypy types-requests`
   - Lines 48-51: "Lint with flake8" step that runs `flake8 core gui_qt data_sources tests --count --show-source --statistics`
   - **Note:** This workflow appears to be an older/alternative CI configuration

### Configuration Files

3. **`.flake8`** (entire file)
   - Standalone config file with:
     - max-line-length = 127
     - max-complexity = 15
     - Extensive ignore list (W, E1, E2, E3, E402, E501, E704, E731, E741, C901, F401, F541, F811, F841)
     - Per-file ignores for tests and __init__.py

4. **`.pre-commit-config.yaml`** (lines 7-14)
   - Flake8 hook configured at: `https://github.com/pycqa/flake8`
   - Rev: v7.3.0
   - Args: `[--config=.flake8]`
   - Additional dependencies: flake8-bugbear, flake8-comprehensions

### Dependency Files

5. **`requirements-dev.txt`** (lines 22-24, 74)
   - Line 22: `flake8>=6.1.0`
   - Line 23: `flake8-bugbear>=23.7.0`
   - Line 24: `flake8-comprehensions>=3.14.0`
   - Line 74: Comment showing example usage: `flake8 core/ gui_qt/ data_sources/`

6. **`pyproject.toml`** (lines 53-55, 158-159)
   - Lines 53-55: Dev dependencies in project.optional-dependencies.dev
     - `flake8>=6.1.0`
     - `flake8-bugbear>=23.7.0`
     - `flake8-comprehensions>=3.14.0`
   - Lines 158-159: Ruff config for flake8-bugbear and flake8-import-conventions (these are for ruff's compatibility mode)

### Documentation

7. **`CONTRIBUTING.md`** (line 121)
   - Example command: `flake8 core/ gui_qt/ data_sources/`

### Operational Scripts

8. **`ops/inventory/README.md`** (pointer)
   - Repo-local pointer to canonical inventory in devcenter-system
   - The `collect_env_snapshot.sh` script is no longer in this repo

9. **`ops/locks/`** (not present)
   - Repo-local lock snapshots are not present in this repo
   - Historical lock data should be referenced from canonical inventory when available

## Ruff Status (Already Installed)

Ruff is already present and configured:
- Listed in CI workflows
- Has pyproject.toml configuration
- Currently running Tier-0 checks: F401, F821, F841, F811, F541, E741, A001

## M3 Removal Plan

### Files to Modify
1. `.github/workflows/ci.yml` - Remove flake8, keep ruff Tier-0
2. `requirements-dev.txt` - Remove flake8 and plugins
3. `pyproject.toml` - Remove flake8 from dev dependencies (keep ruff config sections)
4. `.pre-commit-config.yaml` - Remove flake8 hook
5. `CONTRIBUTING.md` - Update lint commands to use ruff

### Files to Delete
1. `.flake8` - No longer needed

### Files to Leave Unchanged
1. `.github/workflows/python-package.yml` - Will be updated separately or deprecated
2. `pyproject.toml` [tool.ruff.lint] sections - Keep all ruff config

## Notes

- Flake8 had an extensive ignore list, suggesting it was not being used for strict enforcement
- Ruff Tier-0 is already more restrictive than flake8 was in practice
- No behavior changes expected since flake8 was largely ignoring most rules
