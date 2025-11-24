Here’s a merged **`docs/TESTING_GUIDE.md`** you can drop in and then remove `TESTING.md`, `TESTING_SUMMARY.md`, and `tests/README_test.md`.

````md
# PoE Price Checker – Testing Guide

_Last updated: 2025-11-22_

This guide explains:

- How the test suite is structured
- How to run unit, integration, and GUI tests
- How fixtures and markers are used
- How to work with coverage and IDE configs

It replaces the older `TESTING.md`, `TESTING_SUMMARY.md`, and `tests/README_test.md`.

---

## 🧪 1. Test Suite Overview

The PoE Price Checker project uses **pytest** for all tests:

- **Unit tests**: fast, isolated, no real network calls
- **Integration tests**: exercise app wiring, database, and GUI behavior
- **GUI tests**: Tkinter tests that run against a hidden root window

The goal is to keep:

- Broad coverage of core logic (parsing, pricing, DB, config)
- Sanity checks on GUI flows (copy/export/inspector)
- A realistic but controllable environment for external APIs (PoE Ninja, trade API stub)

Target coverage: **~80%+** of core modules.

---

## 📁 2. Test Directory Structure

From the project root:

```text
tests/
  unit/
    core/
      test_config.py
      test_database.py
      test_item_parser.py
      test_price_multi.py
      test_undercut_source.py
      test_value_rules.py
    data_sources/
      test_poeninja_*.py
      test_trade_api_source.py
  integration/
    core/
      test_app_context_league.py
    gui/
      test_gui_copy_row.py
      test_gui_export_and_copy_all_tsv.py
      test_gui_details_and_status.py
      test_gui_item_inspector_and_sources.py
  fixtures/
    ... (sample items, JSON responses, etc.)
  conftest.py
````

### Unit tests

* Live under `tests/unit`.
* Focus on:

  * `core` modules: config, DB, item parsing, multi-source pricing, value rules, undercut logic.
  * `data_sources`: PoE Ninja client behavior and trade API stub.
* Use fixtures and small helper utilities from `tests/fixtures` and `conftest.py`.

### Integration tests

* Live under `tests/integration`.
* Focus on:

  * `core/app_context.py` wiring and league handling.
  * GUI behaviors in `gui/main_window.py`:

    * Copying rows
    * Exporting TSV
    * Detail dialogs
    * Item inspector + pricing sources display

---

## ▶️ 3. Running Tests

From the project root:

```bash
# All tests
pytest

# Only unit tests
pytest tests/unit

# Only integration tests
pytest tests/integration
```

You can combine them with markers (see next section) and/or specific paths.

### Running a single file

```bash
pytest tests/unit/core/test_item_parser.py
pytest tests/integration/gui/test_gui_item_inspector_and_sources.py
```

### Running a single test

```bash
pytest tests/unit/core/test_item_parser.py::test_parses_unique_item
```

---

## 🔖 4. Markers & Test Categories

The suite uses pytest markers to separate test types and behaviors. Typical categories (adjust if your `pytest.ini` differs):

* `unit` – fast, isolated unit tests
* `integration` – tests involving DB, AppContext, or GUI
* `gui` – Tkinter tests that construct a hidden root window
* `slow` – tests that are acceptable locally but skipped on quick runs
* `api` – tests that touch external services (usually mocked for CI)

Example commands:

```bash
# Run only unit tests via marker
pytest -m "unit"

# Run integration tests only
pytest -m "integration"

# Run GUI tests only
pytest -m "gui"

# Skip slow tests
pytest -m "not slow"

# Skip tests that rely on external APIs
pytest -m "not api"
```

Check `pytest.ini` and `tests/conftest.py` for the exact list of markers in use.

---

## 🧱 5. Fixtures & Utilities

`tests/conftest.py` and `tests/fixtures/` provide shared fixtures:

Typical patterns:

* **Config fixtures** – create a temporary config object and user directory.
* **Database fixtures** – spin up an in-memory or temp-file SQLite DB with the schema initialized.
* **AppContext fixtures** – build an `AppContext` wired to temporary config/DB.
* **Item fixtures** – sample PoE item text (currency, maps, uniques, rares) for parser and pricing tests.
* **HTTP mocking** – PoE Ninja and trade API tests use mocked responses to avoid network calls.

If you add new features, prefer:

1. Extending existing fixtures over inventing ad-hoc setup in each test.
2. Keeping fixture scopes tight (`function` where possible, `module` when setup is expensive).

---

## 🖥️ 6. GUI Test Notes (Tkinter)

The GUI tests live in `tests/integration/gui/` and target `PriceCheckerGUI` in `gui/main_window.py`.

Key points:

* Tests create a **hidden Tk root** window so nothing flashes on screen.
* They verify:

  * Copy row / copy-all behaviors
  * Export to TSV
  * Status messages
  * Item Inspector and multi-source pricing display

If you add new GUI features:

* Add a focused test in `tests/integration/gui/` that:

  * Uses the existing Tk root fixture
  * Interacts with widgets via methods on `PriceCheckerGUI`
  * Asserts on text / state rather than visuals

---

## 🛠️ 7. IDE & PyCharm Configuration

To run tests from PyCharm (or a similar IDE):

1. **Set the Working Directory** to the project root (the directory containing `poe_price_checker.py` and `tests/`).
2. Create a **pytest** run configuration:

   * Target: `tests/` or a specific test file.
   * Environment:

     * Use the project virtualenv.
     * Ensure `PYTHONPATH` includes the project root (PyCharm usually handles this automatically when using the root as working directory).
3. For GUI tests:

   * On Windows, they should run with the default interpreter without needing an X server.
   * On Linux/WSL, ensure you have a display or use headless-friendly Tk configuration (the existing tests create a withdrawn root window).

---

## 📊 8. Coverage & Quality Goals

### Coverage Expectations

* **Core modules (`core/`)**:

  * Config, AppContext, database, item parser, value rules, multi-source pricing: **high coverage** (aim for 80%+).
* **Data sources (`data_sources/`)**:

  * PoE Ninja client and trade API adapter: covered via mocked responses and integration-style tests.
* **GUI (`gui/`)**:

  * Key flows (paste → price → copy/export → inspector) should remain under tests.
  * New, complex GUI behavior should add corresponding tests.

### Running coverage

If you have `pytest-cov` installed:

```bash
pytest --cov=core --cov=data_sources --cov=gui --cov-report=term-missing
```

You can also generate HTML reports:

```bash
pytest --cov=core --cov=data_sources --cov=gui --cov-report=html
# Then open htmlcov/index.html in your browser
```

---

## 🚧 9. Adding New Tests (Checklist)

When you add a new feature:

1. **Decide test type(s):**

   * Core logic → `tests/unit/core/`
   * Data source behavior → `tests/unit/data_sources/`
   * Wiring behavior (AppContext) → `tests/integration/core/`
   * GUI interactions → `tests/integration/gui/`

2. **Reuse fixtures** where possible (config, DB, AppContext).

3. **Name tests descriptively**:

   * `test_creates_sale_entry_on_record_sale_click`
   * `test_item_inspector_handles_parse_failure_gracefully`

4. **Run the whole suite** before committing:

   ```bash
   pytest
   ```

5. **Optional:** run coverage to ensure new code is exercised.

---

## ✅ 10. Migration Notes

This document replaces:

* `TESTING.md`
* `TESTING_SUMMARY.md`
* `tests/README_test.md`

```
::contentReference[oaicite:0]{index=0}
```
