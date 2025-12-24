# Phase 4: Runtime & Release Hardening (Documentation)

## Purpose
Document deterministic startup, runtime configuration locations, strict GUI vs API
entrypoint separation, and reproducible build/release steps without changing
runtime behavior.

## Scope / Non-goals
- Documentation-only updates.
- No application logic changes or refactors.
- No runtime behavior changes.

## Deterministic Startup (GUI + API)
### GUI entrypoint
- **File:** `main.py`
- **Sequence:**
  1. `core.logging_setup.setup_logging()` initializes logging.
  2. `core.app_context.create_app_context()` constructs `AppContext`.
  3. GUI window is created with the fully wired `AppContext`.
- **Invariant:** `AppContext` is the only composition root.

### API entrypoint
- **File:** `run_api.py` (recommended) or `api/main.py` via `uvicorn`.
- **Sequence:**
  1. `run_api.py` parses CLI flags (host/port/reload/workers).
  2. `api.main:app` runs and initializes `AppContext` in the FastAPI lifespan.
- **Invariant:** API startup uses the same `AppContext` factory.

## Runtime Configuration (defaults + locations)
- **Config directory:** `~/.poe_price_checker/` (created on first run).
- **Config file:** `~/.poe_price_checker/config.json` (defaults from
  `core/config/defaults.py`).
- **Database:** `~/.poe_price_checker/data.db` (SQLite).
- **Logs:** `~/.poe_price_checker/app.log` (rotating log, ~1 MB x3).
- **Other runtime files (examples):**
  - `~/.poe_price_checker/price_rankings.db`
  - `~/.poe_price_checker/oauth_token.json`
  - `~/.poe_price_checker/.salt`

**Notes**
- Entry points do **not** accept a custom config path flag. Configuration is
  edited in-app or by editing the JSON file directly.

## Entry Point Separation (GUI vs API)
- **GUI:** `python main.py`
- **API:** `python run_api.py` (preferred) or `uvicorn api.main:app`
- **Rule:** GUI and API are separate entrypoints; both rely on
  `core/app_context.py` and do not wire dependencies elsewhere.

## Build & Release Reproducibility
### Local builds (spec-driven)
- **Command:** `python build.py`
- **Uses:** `poe_price_checker.spec`
- **Output:** `dist/PoEPriceChecker/`

### Release builds (workflow-driven)
- **Workflow:** `.github/workflows/build-release.yml`
- **Command (Windows):**
  - `pyinstaller --name "PoE-Price-Checker" --onefile --windowed --icon "assets/icon.ico" \
    --add-data "assets;assets" --add-data "data;data" --hidden-import "PyQt6.QtSvg" \
    --hidden-import "PyQt6.QtSvgWidgets" main.py`
- **Output:** `dist/PoE-Price-Checker.exe`

**Keep in sync**
- If assets, hidden imports, or entrypoints change in the spec, update the
  release workflow to match (and vice-versa) so local builds reproduce release
  behavior.

## Smoke Checklist (no network)
Run from the repo root:

```bash
python -c "from core.config.defaults import get_config_dir; print(get_config_dir())"
python build.py --help
python run_api.py --help
python -c "from pathlib import Path; print(Path('poe_price_checker.spec').exists())"
```

Expected outcomes:
- Config directory path prints without error.
- `build.py --help` prints usage.
- `run_api.py --help` prints API flags.
- Spec file existence prints `True`.

## References
- `main.py`
- `run_api.py`
- `api/main.py`
- `core/app_context.py`
- `core/config/defaults.py`
- `core/config/__init__.py`
- `core/logging_setup.py`
- `build.py`
- `poe_price_checker.spec`
- `.github/workflows/build-release.yml`
