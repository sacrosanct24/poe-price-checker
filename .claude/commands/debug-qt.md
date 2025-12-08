# Debug Qt Tests Command

Run Qt GUI tests in verbose debug mode with proper display configuration.

## Usage
`/debug-qt [test_pattern]`

## Arguments
- `$ARGUMENTS` - Optional test pattern to filter (e.g., `test_main_window`, `results_table`)

## Execution

### Environment Setup
```bash
# Force offscreen rendering for headless testing
export QT_QPA_PLATFORM=offscreen

# Enable Qt debug output
export QT_DEBUG_PLUGINS=1

# Disable plugin autoload to avoid singleton issues
export POE_DISABLE_PLUGIN_AUTOLOAD=1
```

### Run Tests
If pattern provided ($ARGUMENTS):
```bash
pytest tests/unit/gui_qt/ tests/integration/gui/ -v -s --tb=long -k "$ARGUMENTS" --timeout=120 -p no:randomly 2>&1
```

If no pattern:
```bash
pytest tests/unit/gui_qt/ -v -s --tb=long --timeout=120 -p no:randomly -x 2>&1 | head -200
```

### Common Issues and Fixes

1. **Singleton conflicts**: Tests may fail if singletons aren't reset. Check `conftest.py` for reset fixtures.

2. **QApplication already exists**: Ensure tests use the `qapp` fixture from pytest-qt.

3. **Segfaults on Windows**: May need `pytest-timeout` with `method=thread`.

4. **Widget not shown**: Some tests need `widget.show()` before assertions.

### Debug Tips
- Use `-s` to see print statements
- Use `--tb=long` for full tracebacks
- Use `-x` to stop on first failure
- Use `-n0` to disable parallel execution for debugging
