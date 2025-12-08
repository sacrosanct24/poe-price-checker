# ADR-005: PyQt6 UI Framework

## Status
Accepted

## Context

The application needed a desktop GUI framework. Key requirements:
- Cross-platform (Windows primary, macOS/Linux secondary)
- Rich widget set for complex UIs (tables, trees, custom widgets)
- Good performance for data-heavy displays
- Active maintenance and community
- Python bindings

Options considered:
1. **Tkinter**: Built-in, but dated appearance and limited widgets
2. **wxPython**: Native look, but smaller community
3. **PySide6/PyQt6**: Qt framework, feature-rich, large ecosystem
4. **Kivy**: Touch-focused, not ideal for desktop data apps
5. **Dear PyGui**: Fast but less mature

## Decision

Use **PyQt6** (Qt 6 bindings for Python):

- Modern Qt 6 framework with HiDPI support
- Extensive widget library (QTableView, QTreeView, etc.)
- Signal/slot pattern for clean event handling
- Stylesheets for theming (PoE dark theme)
- Strong typing with PyQt6-stubs
- pytest-qt for testing

Architecture patterns:
```python
# Signal/slot for events
class PriceChecker(QWidget):
    price_found = pyqtSignal(dict)  # Define signal

    def __init__(self):
        self.price_found.connect(self._on_price_found)  # Connect

    def check_price(self):
        result = self._fetch_price()
        self.price_found.emit(result)  # Emit

# Worker pattern for async
class PriceWorker(QThread):
    result_ready = pyqtSignal(dict)

    def run(self):
        result = long_running_operation()
        self.result_ready.emit(result)
```

## Consequences

### Positive
- **Professional appearance**: Native or styled, looks polished
- **Feature-rich**: Built-in widgets for most needs
- **Performance**: C++ backend, handles large datasets
- **Tooling**: Qt Designer for layouts, good debugger support
- **Testing**: pytest-qt provides excellent test fixtures

### Negative
- **License**: GPL (vs LGPL for PySide6) - acceptable for this project
- **Learning curve**: Qt concepts (signals, model/view) take time
- **Deployment size**: PyInstaller bundles are ~120MB
- **Qt quirks**: Singleton patterns, event loop complexity

### Neutral
- QSS (Qt StyleSheets) similar to CSS but not identical
- Must use offscreen rendering for CI testing
- Some platform differences (fonts, scroll behavior)

## References
- `gui_qt/` directory structure
- `gui_qt/styles.py` (PoE-themed stylesheets)
- `requirements.txt` (PyQt6 version)
- `pytest.ini` (pytest-qt configuration)
- `docs/testing/TEST_SUITE_GUIDE.md` (Qt testing patterns)
