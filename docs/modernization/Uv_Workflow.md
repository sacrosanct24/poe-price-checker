# UV Workflow for PoE Price Checker

This document describes how to use `uv` as an optional, faster alternative to `pip` for development and testing. It is **additive only** and does not replace the existing `pip` workflow.

## Overview

`uv` is a fast Python package installer and resolver. It can install from `requirements.txt` files and is compatible with existing workflows.

## Prerequisites

- Python 3.11 (same as current baseline)
- `uv` (install instructions below)

## Installation

### Option 1: Install uv (if not present)

```bash
# On Ubuntu/Debian
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip (if you prefer)
pip install uv
```

### Option 2: Use the bootstrap script

```bash
bash ops/dev/uv_bootstrap.sh
```

This script will:
- Install `uv` if missing (or print instructions)
- Create `.venv` using `uv`
- Install dependencies from `requirements.txt` and `requirements-dev.txt`
- Run `./check.sh`

## Creating and Using a uv Environment

### Create environment

```bash
# Create .venv using uv (Python 3.11)
uv venv --python 3.11

# Activate
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### Install dependencies

```bash
# Install runtime dependencies
uv pip install -r requirements.txt

# Install dev dependencies
uv pip install -r requirements-dev.txt
```

### Run checks

```bash
# Run the same checks as the pip workflow
./check.sh
```

## Comparison with pip workflow

| Step | pip (existing) | uv (optional) |
|------|----------------|---------------|
| Create venv | `python -m venv .venv` | `uv venv --python 3.11` |
| Activate | `source .venv/bin/activate` | `source .venv/bin/activate` |
| Install | `pip install -r requirements.txt` | `uv pip install -r requirements.txt` |
| Run checks | `./check.sh` | `./check.sh` |

## Benefits of uv

- **Speed**: Faster dependency resolution and installation
- **Compatibility**: Works with existing `requirements.txt` files
- **Optional**: Does not break existing `pip` workflow

## Troubleshooting

### uv not found

If `uv` is not installed, the bootstrap script will attempt to install it. If that fails, follow the manual installation steps above.

### Python version mismatch

Ensure you are using Python 3.11, as specified in the project configuration.

### Virtual environment issues

If you encounter issues, you can always fall back to the `pip` workflow. The two are compatible and can coexist.

## CI Integration (Additive)

An optional CI job can be added to test the `uv` workflow without affecting the existing `pip` job. This is **additive only** and non-blocking.

## Notes

- This workflow is **optional** and **additive**
- Existing `pip` workflow remains the default
- Both workflows use the same `.venv` directory
- Both workflows install the same dependencies from the same files
- Both workflows run the same checks

## Rollback

To revert to the `pip` workflow:
1. Deactivate the current environment: `deactivate`
2. Remove `.venv` if desired: `rm -rf .venv`
3. Follow the existing `pip` workflow in `check.sh`

No code changes are required to switch between workflows.
