# Testing Guide

## 🧪 Test Suite Overview

The PoE Price Checker test suite provides comprehensive coverage of core functionality. Tests are organized by module and use pytest for execution.

### Test Statistics
- **Total Test Files**: 3 (+ conftest.py)
- **Estimated Test Count**: 100+ tests
- **Coverage Target**: 80%+

---

## 📁 Test Structure

```
tests/
├── conftest.py           # Shared fixtures and pytest configuration
├── test_item_parser.py   # Tests for item parsing (30+ tests)
├── test_database.py      # Tests for database operations (40+ tests)
└── test_config.py        # Tests for configuration (30+ tests)
```

---

## 🚀 Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_item_parser.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_item_parser.py::TestItemParserCurrency -v
```

### Run Specific Test
```bash
pytest tests/test_item_parser.py::TestItemParserCurrency::test_parse_currency_with_stack -v
```

### Run with Coverage Report
```bash
pytest tests/ --cov=core --cov=data_sources --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view detailed coverage.

### Run Only Fast Tests (Skip Slow)
```bash
pytest tests/ -m "not slow"
```

### Run Only Unit Tests
```bash
pytest tests/ -m unit
```

### Run with Verbose Output
```bash
pytest tests/ -vv --tb=long
```

---

## 🏷️ Test Markers

Tests are marked for easy filtering:

- `@pytest.mark.unit` - Fast unit tests, no external dependencies
- `@pytest.mark.integration` - Integration tests, may use database
- `@pytest.mark.slow` - Slow tests (performance tests)
- `@pytest.mark.api` - Tests that call external APIs (skip in CI)

### Examples:
```bash
# Run only fast unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Skip API tests (for offline testing)
pytest -m "not api"
```

---

## 📊 Coverage Goals

### Target Coverage by Module

| Module | Target | Priority |
|--------|--------|----------|
| core/item_parser.py | 95%+ | High |
| core/database.py | 90%+ | High |
| core/config.py | 90%+ | High |
| core/game_version.py | 100% | High |
| data_sources/base_api.py | 80%+ | Medium |
| data_sources/pricing/poe_ninja.py | 70%+ | Medium |
| gui/main_window.py | 50%+ | Low (GUI testing is hard) |

### Current Status
Run this to check:
```bash
pytest --cov=core --cov=data_sources --cov-report=term-missing
```

---

## 🔧 Fixtures Reference

### Database Fixtures
- `temp_db` - Clean temporary database
- `populated_db` - Database with test data

### Config Fixtures
- `temp_config` - Temporary config file

### Parser Fixtures
- `parser` - ItemParser instance
- `sample_currency_text` - Currency item text
- `sample_unique_text` - Unique item text
- `sample_rare_text` - Rare item text
- `sample_magic_text` - Magic item text
- `sample_normal_text` - Normal item text

### Mock Fixtures
- `mock_poe_ninja_response` - Mock poe.ninja API response
- `mock_unique_item_response` - Mock unique item API response

### Usage Example:
```python
def test_parse_currency(parser, sample_currency_text):
    item = parser.parse(sample_currency_text)
    assert item.is_currency()
```

---

## 🐛 Debugging Failed Tests

### Show Local Variables on Failure
```bash
pytest tests/ --showlocals
```

### Stop on First Failure
```bash
pytest tests/ -x
```

### Drop into Debugger on Failure
```bash
pytest tests/ --pdb
```

### See Full Traceback
```bash
pytest tests/ --tb=long
```

### Run Last Failed Tests Only
```bash
pytest tests/ --lf
```

---

## ✅ Test Examples

### Simple Unit Test
```python
def test_is_currency(parser, sample_currency_text):
    """Test that currency items are identified correctly."""
    item = parser.parse(sample_currency_text)
    assert item.is_currency() is True
```

### Test with Fixtures
```python
def test_add_item_to_database(temp_db):
    """Test adding an item to the database."""
    item_id = temp_db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Test Item",
        chaos_value=100.0
    )
    
    assert item_id > 0
    
    items = temp_db.get_checked_items(limit=1)
    assert len(items) == 1
    assert items[0]['item_name'] == "Test Item"
```

### Parametrized Test
```python
@pytest.mark.parametrize("rarity,expected", [
    ("UNIQUE", True),
    ("RARE", False),
    ("MAGIC", False),
    ("NORMAL", False),
])
def test_is_unique(parser, rarity, expected):
    """Test is_unique() for different rarities."""
    item = ParsedItem(raw_text="test", rarity=rarity)
    assert item.is_unique() == expected
```

### Testing Exceptions
```python
def test_invalid_input_raises_error():
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValueError):
        config.min_value_chaos = -10  # Negative not allowed
```

---

## 🎯 Writing New Tests

### Best Practices

1. **One Concept Per Test**
```python
# Good
def test_add_item():
    # Test just adding
    
def test_get_item():
    # Test just getting

# Bad
def test_add_and_get_and_update_item():
    # Testing too much
```

2. **Use Descriptive Names**
```python
# Good
def test_parse_currency_with_stack_size():

# Bad
def test_parse():
```

3. **Arrange, Act, Assert**
```python
def test_example():
    # Arrange - Set up test data
    parser = ItemParser()
    text = "Stack Size: 5/40\nChaos Orb"
    
    # Act - Execute the code being tested
    item = parser.parse(text)
    
    # Assert - Verify the results
    assert item.stack_size == 5
```

4. **Test Edge Cases**
```python
def test_parse_empty_string_returns_none():
    parser = ItemParser()
    assert parser.parse("") is None

def test_parse_very_long_item_name():
    # Test limits
    
def test_parse_unicode_characters():
    # Test special characters
```

---

## 🔄 Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest tests/ --cov=core --cov=data_sources -m "not slow and not api"
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 📈 Improving Coverage

### Find Untested Code
```bash
pytest --cov=core --cov-report=term-missing
```

Look for lines marked with `!!!!`:
```
core/item_parser.py    95%   !!!! 145-150
```

Lines 145-150 are not covered by tests.

### Add Tests for Uncovered Code
1. Identify uncovered lines
2. Write test that exercises those lines
3. Re-run coverage to verify

---

## 🚨 Common Issues

### Import Errors
```bash
# Make sure you're in the project root
cd /path/to/exilePriceCheck

# Run tests with python path
PYTHONPATH=. pytest tests/
```

### Database Locked
```python
# Always use temp_db fixture for tests
# Don't create databases manually
def test_something(temp_db):  # ✓ Good
    ...

def test_something_else():  # ✗ Bad
    db = Database("test.db")
    ...
```

### Fixture Not Found
```bash
# Make sure conftest.py is in tests/ directory
ls tests/conftest.py
```

---

## 📝 Test Checklist for New Features

When adding a new feature, write tests for:

- [ ] Happy path (normal usage)
- [ ] Edge cases (empty input, max values)
- [ ] Error cases (invalid input)
- [ ] Boundary conditions
- [ ] Integration with existing code

---

## 🎓 Learning Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

---

## 📞 Getting Help

If tests fail:
1. Read the error message carefully
2. Use `--tb=long` for full traceback
3. Use `--pdb` to debug interactively
4. Check the test documentation above
5. Review the conftest.py fixtures

---

**Happy Testing! 🧪**