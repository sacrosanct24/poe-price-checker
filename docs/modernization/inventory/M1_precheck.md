# M1 Pre-Check Inventory

**Date:** December 18, 2025
**Branch:** m1-pyproject-uv
**Purpose:** Document existing tooling configuration for Phase 1 dependency hygiene and optional `uv` workflow.

## Summary of Existing Configuration

### Package Management

**File:** `requirements.txt`
- Core dependencies: requests, openpyxl, beautifulsoup4, PyQt6, mcp[cli], sqlalchemy
- Data/ML: pandas, matplotlib, plotly, fastapi, uvicorn, pydantic, scikit-learn
- Utils: python-dotenv, pyperclip, keyboard, cryptography, defusedxml
- Build: pyinstaller, lxml
- **Note:** Runtime-only; dev/test tools are in requirements-dev.txt and pyproject optional-dependencies

**File:** `requirements-dev.txt`
- Includes `-r requirements.txt` and adds test/quality/security tooling
- Adds code quality tools: ruff, isort
- Adds security scanning: bandit, safety, pip-audit
- Adds pre-commit hooks: pre-commit

### Testing Configuration

**File:** `pytest.ini`
- Test paths: `tests`
- Python patterns: `test_*.py`, `Test*`, `test_*`
- Addopts: `-ra --strict-markers --strict-config --showlocals --tb=short -v --durations=20`
- Timeout: 120 seconds (via pytest-timeout)
- Coverage: Source includes `core,data_sources,gui`, omits tests and cache
- Markers: unit, integration, slow, api

### Code Quality Configuration

**File:** `.flake8`
- Max line length: 127
- Max complexity: 15
- Excludes: .git, __pycache__, build, dist, *.egg-info, venv, .venv, .eggs
- **Note:** Ignores many style warnings (W, E1, E2, E3, E402, E501, E704, E731, E741, C901, F401, F541, F811, F841)
- Per-file ignores for tests and __init__.py

**File:** `mypy.ini`
- Python version: 3.11
- Warn return any: True
- Warn unused ignores: True
- Show error codes: True
- Show error context: True
- **Note:** Very permissive settings (ignore_missing_imports=True, check_untyped_defs=False, disallow_untyped_defs=False)
- Files limited to specific modules: core/price_arbitration.py, core/clipboard_monitor.py, data_sources/base_api.py, data_sources/affix_data_provider.py, data_sources/poe_ninja_client.py
- Per-module strictness for core.config and core.game_version

**File:** `.pre-commit-config.yaml`
- Flake8: rev 7.1.1, includes flake8-bugbear, flake8-comprehensions
- isort: rev 5.13.2, profile=black, line-length=100
- Pre-commit hooks: trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-merge-conflict, debug-statements
- mypy: rev v1.13.0, stages: [manual] (only manual execution)

### CI/CD Configuration

**File:** `.github/workflows/ci.yml`
- Python version: 3.11
- Matrix: ubuntu-latest, windows-latest
- Steps:
  1. Checkout
  2. Set up Python 3.11
  3. Install dependencies: pip install -r requirements.txt, pip install flake8 mypy
  4. Lint: flake8 .
  5. Type check: mypy --install-types --non-interactive
  6. Tests: pytest -m unit -q --durations=20 --ignore=tests/unit/gui_qt --ignore=tests/test_shortcuts.py
- Additional jobs: security-deps, secrets-scan, integration-tests, complexity

### Build/Development Scripts

**File:** `check.sh`
- Bash script for CI-equivalent unit test runner
- Steps:
  1. Verify repo root
  2. Check/create .venv
  3. Activate .venv
  4. Install requirements-dev.txt
  5. Run pytest with unit marker, excluding gui_qt and test_shortcuts

## Key Observations

### Current State
- **pyproject.toml present** - dependency metadata is first-class
- **Dual requirements files** - runtime (requirements.txt) and dev (requirements-dev.txt)
- **Conservative tooling** - Permissive mypy settings, style ignores in flake8
- **CI uses Python 3.11** - This should be the baseline for pyproject.toml
- **Pre-commit is manual for mypy** - Only runs on manual trigger

### Compatibility Considerations
- pytest.ini and mypy.ini can coexist with pyproject.toml
- .flake8 can be migrated to pyproject.toml or kept
- Pre-commit config will need updates for new tool locations
- CI workflow will need additive job for uv testing

### Migration Strategy
- Keep existing config files initially (no deletion in M1)
- Align pyproject.toml with requirements files to reduce drift
- Add optional uv workflow documentation and bootstrap script
- Add CI job for uv (additive, non-blocking)

## Files to Create/Modify in M1

### New Files
- (None required for pyproject.toml; already present)
- `docs/modernization/Uv_Workflow.md` - uv workflow documentation
- `ops/dev/uv_bootstrap.sh` - uv environment setup script

### Modified Files (if any)
- `pyproject.toml` - Align metadata and dependency listings
- `.github/workflows/ci.yml` - Additive CI job only (optional)
- `check.sh` - Only if necessary for help message or stable targets

## Risk Assessment

### Low Risk
- Aligning existing pyproject.toml with requirements files
- Creating documentation and scripts
- Adding optional CI job

### Medium Risk
- Potential conflicts between pyproject.toml and existing config files
- CI job additions affecting build times

### Mitigation
- Keep existing configs unchanged initially
- Make uv workflow optional
- Add CI job as non-blocking
