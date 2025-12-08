# Pre-PR Check Command

Run the full CI validation suite before creating a pull request.

## Execution Steps

Run these checks in order and report results:

### 1. Linting (flake8)
```bash
flake8 core/ gui_qt/ data_sources/ api/ --count --show-source --statistics
```

### 2. Import Sorting (isort)
```bash
isort --check-only --diff core/ gui_qt/ data_sources/ api/
```

### 3. Type Checking (mypy)
```bash
mypy --config-file=mypy.ini core/ data_sources/
```

### 4. Unit Tests
```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/unit/ -v --tb=short --timeout=120 -q 2>&1 | tail -50
```

### 5. Summary
After running all checks:
- Report which checks passed/failed
- For failures, provide specific line numbers and suggested fixes
- If all pass, confirm the code is ready for PR

## Success Criteria
- Zero flake8 errors
- Imports properly sorted
- No mypy type errors (in checked modules)
- All unit tests passing
