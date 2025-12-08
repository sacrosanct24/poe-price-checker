# Test Module Command

Run tests for a specific module with coverage reporting.

## Usage
`/test-module <module_name>`

## Arguments
- `$ARGUMENTS` - The module name (e.g., `core`, `gui_qt`, `data_sources`, or specific file like `core/item_parser`)

## Execution

Run tests for the specified module: **$ARGUMENTS**

```bash
# Set Qt offscreen for headless testing
export QT_QPA_PLATFORM=offscreen

# Run pytest with coverage for the module
pytest tests/ -v --cov=$ARGUMENTS --cov-report=term-missing -k "$ARGUMENTS" --timeout=120 2>&1 | head -100
```

If tests fail, analyze the failures and suggest fixes. If they pass, report coverage statistics.
