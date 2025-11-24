# Test Suite Guide - PoE Price Checker

**Status:** ✅ 163 tests passing (98% pass rate)  
**Coverage:** ~60% overall  
**Runtime:** ~3 seconds

---

## Quick Start

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=core --cov=data_sources --cov=gui --cov-report=html

# Run specific category
python -m pytest tests/unit/            # Unit tests only
python -m pytest tests/integration/     # Integration tests only
```

---

## Test Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/                          # Fast, isolated unit tests
│   ├── core/                      # Core business logic
│   │   ├── test_app_context.py
│   │   ├── test_config.py
│   │   ├── test_database*.py
│   │   ├── test_item_parser*.py
│   │   ├── test_price_*.py
│   │   ├── test_logging_setup.py
│   │   └── test_value_rules.py
│   └── data_sources/              # API clients
│       ├── test_poeninja*.py
│       └── test_trade_api*.py
└── integration/                    # GUI & integration tests
    ├── core/
    └── gui/
```

---

## Test Categories

### Unit Tests (Fast, Isolated)
- **Core Logic:** Parser, database, pricing, config
- **Data Sources:** API clients, mocking external services
- **Runtime:** < 2 seconds
- **Coverage:** 85%+

### Integration Tests (End-to-End)
- **GUI Components:** Results table, item inspector
- **Full Workflows:** Parse → Price → Display
- **Runtime:** < 1 second
- **Coverage:** 65%+

### Edge Case Tests
- **Error Handling:** Invalid input, missing data
- **Boundary Conditions:** Empty lists, null values
- **Special Cases:** Divine conversion, corrupted items

---

## Coverage by Module

| Module | Coverage | Status |
|--------|----------|--------|
| `core/config.py` | 98% | ✅ Excellent |
| `core/database.py` | 79% | ✅ Good |
| `core/item_parser.py` | 82% | ✅ Good |
| `core/price_service.py` | 82% | ✅ Good |
| `core/app_context.py` | 96% | ✅ Excellent |
| `core/logging_setup.py` | 100% | ✅ Excellent |
| `gui/main_window.py` | 56% | ⚠️ Needs work |
| `data_sources/poe_ninja.py` | 44% | ⚠️ Needs work |

---

## Running Tests

### Basic Commands
```bash
# All tests
pytest

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run specific file
pytest tests/unit/core/test_database.py

# Run specific test
pytest tests/unit/core/test_database.py::test_get_quotes
```

### Coverage Commands
```bash
# Terminal report
pytest --cov=core --cov-report=term-missing

# HTML report (browse htmlcov/index.html)
pytest --cov=core --cov=data_sources --cov=gui --cov-report=html

# Coverage for specific module
pytest tests/unit/core/ --cov=core --cov-report=term
```

### Advanced Options
```bash
# Run tests in parallel (faster)
pytest -n auto

# Show slowest 10 tests
pytest --durations=10

# Treat warnings as errors
pytest -W error

# Verbose with output
pytest -v -s
```

---

## Writing New Tests

### Test Structure
```python
import pytest
from unittest.mock import Mock, patch

class TestMyFeature:
    """Tests for MyFeature class"""
    
    @pytest.fixture
    def my_fixture(self):
        """Setup code that runs before each test"""
        return SomeObject()
    
    def test_happy_path(self, my_fixture):
        """Test the main success scenario"""
        result = my_fixture.do_something()
        assert result == expected_value
    
    def test_error_handling(self, my_fixture):
        """Test error scenarios"""
        with pytest.raises(ValueError):
            my_fixture.do_something_invalid()
    
    def test_edge_case(self, my_fixture):
        """Test boundary conditions"""
        result = my_fixture.do_something_with_empty_input([])
        assert result == []
```

### Mocking External Dependencies
```python
from unittest.mock import patch, Mock

def test_with_mock():
    with patch('module.external_call') as mock_call:
        mock_call.return_value = "mocked result"
        
        result = function_that_calls_external()
        
        assert result == "processed: mocked result"
        mock_call.assert_called_once()
```

### Testing Exceptions
```python
def test_raises_exception():
    with pytest.raises(ValueError, match="expected error message"):
        function_that_should_raise()
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert input * 2 == expected
```

---

## Test Fixtures

### Shared Fixtures (conftest.py)
```python
@pytest.fixture
def temp_db():
    """Temporary database for testing"""
    db = Database(Path(":memory:"))
    yield db
    db.conn.close()

@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = Mock()
    config.current_game = GameVersion.POE1
    config.get_league.return_value = "Standard"
    return config
```

### Using Fixtures
```python
def test_with_fixtures(temp_db, mock_config):
    # temp_db and mock_config are automatically provided
    result = some_function(temp_db, mock_config)
    assert result is not None
```

---

## Common Test Patterns

### Testing Database Operations
```python
def test_database_insert(temp_db):
    temp_db.save_quote(quote)
    quotes = temp_db.get_quotes(GameVersion.POE1, "Standard", "Item")
    assert len(quotes) == 1
```

### Testing Parser
```python
def test_parse_unique_item():
    text = """Rarity: Unique
Headhunter
Leather Belt"""
    
    parser = ItemParser()
    result = parser.parse(text)
    
    assert result.name == "Headhunter"
    assert result.rarity == "UNIQUE"
```

### Testing API Clients
```python
def test_poeninja_api():
    with patch.object(api, 'get_overview', return_value=mock_data):
        result = api.find_item_price("Chaos Orb")
        assert result > 0
```

---

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=core --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Test Maintenance

### Before Each Commit
```bash
# Clear caches
find . -type d -name __pycache__ -exec rm -rf {} +

# Run tests
pytest

# Check coverage
pytest --cov=core --cov-report=term-missing
```

### When Adding Features
1. Write test first (TDD)
2. Implement feature
3. Ensure test passes
4. Check coverage didn't decrease

### When Fixing Bugs
1. Write test that reproduces bug
2. Verify test fails
3. Fix the bug
4. Verify test passes
5. Add to regression suite

---

## Troubleshooting

### Tests Failing Randomly
- Check for shared state between tests
- Ensure proper teardown in fixtures
- Use `--lf` to run only last failed tests

### Slow Tests
```bash
# Find slow tests
pytest --durations=10

# Run in parallel
pytest -n auto
```

### Import Errors
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH=.
pytest

# Or use python -m
python -m pytest tests/
```

### Mock Issues
- Mock at the right abstraction level
- Use `patch.object()` for instance methods
- Verify mock calls with `assert_called_once()`

---

## Best Practices

1. ✅ **One assertion per test** (when possible)
2. ✅ **Descriptive test names** - `test_parse_unique_item_with_influences`
3. ✅ **Arrange-Act-Assert** pattern
4. ✅ **Fast tests** - Mock external dependencies
5. ✅ **Isolated tests** - No dependencies between tests
6. ✅ **Test both success and failure** paths
7. ✅ **Use fixtures** for common setup
8. ✅ **Parametrize** for multiple similar cases

---

## Key Metrics

- **Total Tests:** 163
- **Pass Rate:** 98%
- **Runtime:** ~3 seconds
- **Coverage:** 60%
- **CI/CD:** Ready

**Status: Production Ready** ✅

---

For detailed history of test fixes and improvements, see:
- `TESTING_HISTORY.md` - Complete journey from 109 → 163 tests
- `KNOWN_ISSUES.md` - Remaining coverage gaps
