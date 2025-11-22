# 📘 Test Suite Guide – *PoE Price Checker*

This project uses **pytest** with a clean separation between **unit tests** and **integration tests**, along with a small set of custom markers.
This document explains how the tests are organized and how to run them effectively.

---

# 🗂️ Test Directory Structure

```
tests/
  unit/
    core/
    data_sources/
  integration/
    gui/
    core/
  fixtures/
  conftest.py
  README_tests.md   ← (this file)
```

### ✔ Unit tests

* Fast, isolated, no real I/O
* Test logic, parsing, pure functions, small services
* Located under: `tests/unit/**`
* Marked with: `@pytest.mark.unit` (or `pytestmark = pytest.mark.unit`)

### ✔ Integration tests

* Exercise multiple components together
* GUI tests, real database behavior, AppContext wiring
* Located under: `tests/integration/**`
* Marked with: `@pytest.mark.integration`

---

# 🏷️ Available Test Markers

These come from `pytest.ini`:

| Marker        | Purpose                                             |
| ------------- | --------------------------------------------------- |
| `unit`        | Unit tests (fast, no external dependencies)         |
| `integration` | Integration tests (GUI, DB, multi-component)        |
| `slow`        | Tests known to take a long time                     |
| `api`         | Tests that hit external APIs (PoE Ninja, GGG, etc.) |

All markers are *strict*, meaning typos will raise errors.

---

# ▶️ Running Tests

### Run everything

```bash
pytest
```

### Run only unit tests

```bash
pytest -m unit
```

### Run only integration tests

```bash
pytest -m integration
```

### Run everything except slow tests

```bash
pytest -m "not slow"
```

### Run only API tests

```bash
pytest -m api
```

### Run a single file

```bash
pytest tests/unit/core/test_price_multi.py
```

### Run a specific test inside a file

```bash
pytest tests/unit/core/test_price_multi.py::test_multi_source_aggregator_combines_rows
```

---

# 🧪 Test Conventions

### Naming conventions

* Files must be named `test_*.py`
* Test functions must be named `test_*`
* Test classes should start with `Test`

### Module-level markers

Every test file begins with:

```python
import pytest
pytestmark = pytest.mark.unit      # or integration
```

This avoids marking every test individually.

### Fixtures

Reusable test fixtures live in:

```
tests/fixtures/
tests/conftest.py
```

Pytest automatically discovers these.

---

# 🧹 Running Coverage

Coverage is preconfigured in `pytest.ini`.

```bash
pytest --cov
```

HTML report:

```bash
pytest --cov --cov-report=html
```

Output goes to:

```
htmlcov/index.html
```

---

# ❓ Need help?

If a test fails or an import breaks:

* Make sure you’re running pytest from the **project root**, not inside the `tests/` folder.
* In PyCharm, confirm the test run configuration sets **Working Directory = project root**.