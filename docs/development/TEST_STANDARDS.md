# Test Quality Standards

This document defines the testing standards for the PoE Price Checker project. All tests should follow these guidelines to ensure meaningful coverage and maintainable test code.

## Core Principles

### 1. Test Behavior, Not Implementation
Tests should verify **what** the code does, not **how** it does it. This allows refactoring without breaking tests.

```python
# GOOD - Tests behavior
def test_price_service_returns_lowest_price(self, service):
    prices = [100, 50, 75]
    result = service.aggregate_prices(prices)
    assert result == 50

# BAD - Tests implementation
def test_price_service_calls_sort(self, service, mocker):
    mocker.patch.object(service, '_sort_prices')
    service.aggregate_prices([100, 50])
    service._sort_prices.assert_called_once()
```

### 2. Every Test Must Have Meaningful Assertions
Assertions should verify observable behavior. Avoid tests that only check object creation.

```python
# GOOD - Meaningful assertion
def test_item_parser_extracts_rarity(self, parser):
    item = parser.parse("Rarity: Rare\nDream Bane\nImperial Claw")
    assert item.rarity == "Rare"

# BAD - Superficial assertion
def test_item_parser_exists(self, parser):
    assert parser is not None
```

### 3. Test Edge Cases
Always consider boundary conditions, empty inputs, and error scenarios.

```python
class TestPriceEstimation:
    def test_estimate_with_single_quote(self): ...
    def test_estimate_with_empty_quotes(self): ...
    def test_estimate_with_outlier_prices(self): ...
    def test_estimate_with_all_same_prices(self): ...
    def test_estimate_handles_negative_prices(self): ...
```

### 4. Test Error Conditions
Verify that code handles failures gracefully.

```python
def test_api_client_handles_timeout(self, client):
    with pytest.raises(TimeoutError):
        client.fetch(timeout=0.001)

def test_api_client_returns_err_on_failure(self, client):
    result = client.safe_fetch("invalid")
    assert result.is_err()
    assert "failed" in result.unwrap_err().lower()
```

---

## Anti-Patterns to Avoid

### 1. Testing Enum String Values
Don't test that `ViewMode.TABLE.value == "table"`. Test how the enum is used.

```python
# BAD - Tests enum value
def test_table_value(self):
    assert ViewMode.TABLE.value == "table"

# GOOD - Tests enum usage
def test_toggle_switches_to_table_mode(self, qtbot, toggle):
    toggle.set_view(ViewMode.TABLE)
    assert toggle.current_view == ViewMode.TABLE
    assert toggle._buttons[ViewMode.TABLE].isChecked()
```

### 2. Testing Only Object Creation
If you only test that something can be created, you're not testing behavior.

```python
# BAD - Only tests creation
def test_window_creates(self, qtbot):
    window = MainWindow()
    assert window is not None

# GOOD - Tests initial state
def test_window_starts_with_empty_results(self, qtbot):
    window = MainWindow()
    assert window.results_table.rowCount() == 0
    assert window.status_label.text() == "Ready"
```

### 3. Over-Mocking
Mocking everything makes tests brittle and doesn't verify real behavior.

```python
# BAD - Mocks everything
def test_price_check(self, mocker):
    mocker.patch.object(service, 'parse')
    mocker.patch.object(service, 'fetch')
    mocker.patch.object(service, 'format')
    service.check_price("item")
    service.parse.assert_called_once()

# GOOD - Uses fake with real behavior
def test_price_check(self, fake_api):
    fake_api.set_price("Headhunter", 50.0)
    service = PriceService(api=fake_api)
    result = service.check_price("Headhunter")
    assert result.price == 50.0
```

### 4. Testing Private Methods
Test public API. Private methods are implementation details.

```python
# BAD - Tests private method
def test_parse_mods_internal(self, parser):
    result = parser._parse_mod_line("Adds 10 to 20 Fire Damage")
    assert result == ("fire_damage", 10, 20)

# GOOD - Tests through public API
def test_parser_extracts_fire_damage_mod(self, parser):
    item = parser.parse(ITEM_WITH_FIRE_DAMAGE)
    assert any("Fire Damage" in mod for mod in item.mods)
```

---

## Preferred Patterns

### Use pytest-qt for Qt Testing

```python
class TestWidget:
    def test_button_click_emits_signal(self, qtbot, widget):
        with qtbot.waitSignal(widget.clicked, timeout=1000):
            qtbot.mouseClick(widget.button, Qt.MouseButton.LeftButton)

    def test_signal_carries_correct_data(self, qtbot, widget):
        received = []
        widget.data_changed.connect(received.append)
        widget.set_data("test")
        QApplication.processEvents()
        assert received == ["test"]
```

### Use Fake Objects Over MagicMock

Create fake implementations for complex dependencies:

```python
# In tests/conftest_utils.py
class FakePriceSource:
    def __init__(self):
        self._prices = {}

    def set_price(self, item: str, price: float):
        self._prices[item] = price

    def get_price(self, item: str) -> float | None:
        return self._prices.get(item)

# In tests
def test_price_aggregation(self, fake_source):
    fake_source.set_price("Exalted Orb", 150.0)
    service = PriceService(source=fake_source)
    assert service.get_price("Exalted Orb") == 150.0
```

### Use Parametrize for Similar Cases

```python
@pytest.mark.parametrize("rarity,expected_color", [
    ("Normal", "#ffffff"),
    ("Magic", "#8888ff"),
    ("Rare", "#ffff77"),
    ("Unique", "#af6025"),
])
def test_item_color_by_rarity(self, rarity, expected_color):
    color = get_rarity_color(rarity)
    assert color == expected_color
```

### Use Fixtures for Setup

```python
@pytest.fixture
def configured_service(fake_api, fake_db):
    """Service with standard test configuration."""
    return PriceService(
        api=fake_api,
        db=fake_db,
        cache_ttl=0,  # Disable caching in tests
    )

def test_service_fetches_from_api(self, configured_service, fake_api):
    fake_api.set_price("item", 100)
    result = configured_service.get_price("item")
    assert result == 100
```

---

## Qt-Specific Guidelines

### Avoid qtbot.wait() on Windows
`qtbot.wait()` can cause crashes on Windows CI. Use `QApplication.processEvents()` instead.

```python
# BAD - Can crash on Windows
def test_signal(self, qtbot, widget):
    widget.do_action()
    qtbot.wait(50)
    assert widget.state == "done"

# GOOD - Cross-platform
def test_signal(self, qtbot, widget):
    widget.do_action()
    QApplication.processEvents()
    assert widget.state == "done"
```

### Skip Timer-Dependent Tests on Windows CI
If a test requires QTimer behavior, skip it on Windows CI:

```python
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="QTimer + qtbot.wait() causes crashes on Windows CI"
)
def test_countdown_timer(self, qtbot, widget):
    ...
```

### Use waitSignal for Async Operations

```python
def test_worker_completes(self, qtbot, worker):
    with qtbot.waitSignal(worker.finished, timeout=5000):
        worker.start()
    assert worker.result is not None
```

---

## Test Organization

### File Naming
- Unit tests: `tests/unit/<module>/test_<filename>.py`
- Integration tests: `tests/integration/test_<workflow>.py`
- Test file should mirror source file structure

### Class Organization
```python
class TestPriceService:
    """Tests for PriceService."""

    class TestGetPrice:
        """Tests for get_price method."""
        def test_returns_price_for_known_item(self): ...
        def test_returns_none_for_unknown_item(self): ...
        def test_handles_api_timeout(self): ...

    class TestAggregation:
        """Tests for price aggregation."""
        def test_uses_median_for_outliers(self): ...
```

### Docstrings
Include docstrings for non-obvious test names:

```python
def test_price_within_confidence_interval(self, service):
    """Price should be within 2 standard deviations of mean."""
    ...
```

---

## Coverage Requirements

### Overall Targets
| Component | Target Coverage |
|-----------|----------------|
| core/ | 85% |
| gui_qt/ | 75% |
| data_sources/ | 75% |
| **Overall** | **80%** |

### What to Cover
- All public methods and functions
- Error handling paths
- Edge cases and boundary conditions
- Integration between components

### What to Exclude
- UI-only code with no logic (pure layout)
- Generated code
- Third-party library wrappers with no custom logic
- `if __name__ == "__main__"` blocks

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=gui_qt --cov=data_sources --cov-report=term-missing

# Run specific module tests
pytest tests/unit/core/test_price_service.py -v

# Run in parallel
pytest -n auto

# Stop on first failure
pytest -x --tb=short

# Generate HTML coverage report
pytest --cov=core --cov-report=html
```

---

## Checklist for New Tests

Before submitting tests, verify:

- [ ] Tests verify behavior, not implementation
- [ ] No `assert x is not None` as sole assertion
- [ ] No tests that only check enum string values
- [ ] Edge cases covered (empty, null, boundary)
- [ ] Error conditions tested
- [ ] No `qtbot.wait()` on Windows-sensitive paths
- [ ] Docstrings for complex test scenarios
- [ ] Tests run in isolation (no shared state)
- [ ] Fixtures used for repeated setup
