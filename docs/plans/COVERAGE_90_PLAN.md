# Coverage Improvement Plan: Target 90%

## Current State
- **Overall Coverage**: ~70%
- **Core Module**: ~81% (good baseline)
- **GUI Module**: ~10% (critical gap)
- **Data Sources**: ~40% (needs work)

## Target: 90% Overall Coverage

### Strategy Overview
Focus on high-impact, low-effort tests first. GUI testing requires PyQt6 fixtures but many components can be unit-tested by mocking Qt dependencies.

---

## Phase 1: Core Module - Reach 90% (Priority: HIGH)

**Current: 81% → Target: 90%**

### 1.1 Low-Coverage Core Files (< 80%)

| File | Current | Missing Lines | Priority |
|------|---------|---------------|----------|
| `core/rankings/cli.py` | 21% | 105 | LOW (CLI, skip) |
| `core/pricing/models.py` | 32% | 35 | HIGH |
| `core/pricing/service.py` | 71% | 154 | HIGH |
| `core/pricing/cache.py` | 74% | 34 | MEDIUM |
| `core/smart_trade_filters.py` | 75% | 28 | MEDIUM |
| `core/services/export_service.py` | 72% | 36 | MEDIUM |
| `core/rare_evaluation/evaluator.py` | 76% | 119 | MEDIUM |
| `core/stash_storage.py` | 79% | 25 | MEDIUM |
| `core/upgrade_finder.py` | 81% | 36 | LOW |
| `core/stash_scanner.py` | 81% | 28 | LOW |

### Phase 1 Tasks (in order):

1. **`core/pricing/models.py`** - Add tests for PriceResult, PriceData models
2. **`core/pricing/service.py`** - Test price fetching, caching, error handling
3. **`core/pricing/cache.py`** - Test cache expiration, invalidation
4. **`core/smart_trade_filters.py`** - Test filter generation logic
5. **`core/services/export_service.py`** - Test CSV/JSON export functions
6. **`core/rare_evaluation/evaluator.py`** - Test evaluation scoring paths

**Estimated Tests**: ~50 new tests
**Expected Coverage Gain**: +9% on core (81% → 90%)

---

## Phase 2: Data Sources - Reach 70% (Priority: MEDIUM)

**Current: ~40% → Target: 70%**

### 2.1 Key Data Source Files

| File | Priority | Notes |
|------|----------|-------|
| `data_sources/base_api.py` | HIGH | Base class, affects all clients |
| `data_sources/poe_ninja_client.py` | HIGH | Primary pricing source |
| `data_sources/poe_trade_client.py` | MEDIUM | Trade API integration |
| `data_sources/ai/*.py` | LOW | AI providers (mock-heavy) |

### Phase 2 Tasks:

1. **`base_api.py`** - Test rate limiting, retry logic, caching
2. **`poe_ninja_client.py`** - Test API parsing, error handling
3. **`poe_trade_client.py`** - Test query building, response parsing

**Estimated Tests**: ~30 new tests
**Expected Coverage Gain**: +30% on data_sources

---

## Phase 3: GUI Module - Reach 50% (Priority: MEDIUM-HIGH)

**Current: ~10% → Target: 50%**

### 3.1 Strategy for GUI Testing

GUI tests require `pytest-qt` and `QT_QPA_PLATFORM=offscreen`. Focus on:
1. **Widget logic** - Test without rendering where possible
2. **Signal/slot connections** - Verify signals emit correctly
3. **Data models** - Test underlying data structures

### 3.2 High-Value GUI Files (testable without full Qt)

| File | Lines | Strategy |
|------|-------|----------|
| `gui_qt/services/*.py` | 200+ | Pure Python, easy to test |
| `gui_qt/models/*.py` | 150+ | Data models, no Qt dependency |
| `gui_qt/themes/*.py` | 300+ | Theme logic, partially testable |
| `gui_qt/workers/*.py` | 200+ | Worker logic with mocked signals |

### 3.3 Widget Testing (requires pytest-qt)

| Widget | Priority | Notes |
|--------|----------|-------|
| `widgets/results_table.py` | HIGH | Core functionality |
| `widgets/item_inspector.py` | HIGH | Item display logic |
| `widgets/session_tabs.py` | MEDIUM | Tab management |
| `windows/*.py` | LOW | Full window tests (integration) |

### Phase 3 Tasks:

1. **`gui_qt/services/`** - Test window manager, navigation service
2. **`gui_qt/models/`** - Test data models
3. **`gui_qt/themes/theme_manager.py`** - Test theme switching
4. **`gui_qt/workers/base_worker.py`** - Test worker lifecycle
5. **`gui_qt/widgets/results_table.py`** - Test table logic with qtbot

**Estimated Tests**: ~80 new tests
**Expected Coverage Gain**: +40% on gui_qt (10% → 50%)

---

## Phase 4: Final Push to 90% (Priority: HIGH)

After Phases 1-3, expected overall: ~75-80%

### 4.1 Gap Analysis
- Identify remaining low-coverage files
- Add edge case tests to existing test files
- Add integration tests for critical paths

### 4.2 Integration Tests
- End-to-end price checking flow
- Build import/analysis flow
- Export functionality

---

## Execution Order (Priority List)

### Week 1: Core Foundation
1. ✅ `core/pricing/models.py` - 35 lines
2. ✅ `core/pricing/service.py` - 154 lines (critical path)
3. ✅ `core/pricing/cache.py` - 34 lines

### Week 2: Core Services
4. `core/services/export_service.py` - 36 lines
5. `core/smart_trade_filters.py` - 28 lines
6. `core/rare_evaluation/evaluator.py` - 119 lines

### Week 3: Data Sources
7. `data_sources/base_api.py`
8. `data_sources/poe_ninja_client.py`
9. `data_sources/poe_trade_client.py`

### Week 4: GUI Foundation
10. `gui_qt/services/*.py`
11. `gui_qt/workers/*.py`
12. `gui_qt/themes/theme_manager.py`

### Week 5: GUI Widgets
13. `gui_qt/widgets/results_table.py`
14. `gui_qt/widgets/item_inspector.py`
15. `gui_qt/widgets/session_tabs.py`

### Week 6: Final Push
16. Gap analysis and targeted tests
17. Integration tests
18. Re-enable `fail_under = 90` in `.coveragerc`

---

## Success Metrics

| Phase | Module | Start | Target | Tests Added |
|-------|--------|-------|--------|-------------|
| 1 | core | 81% | 90% | ~50 |
| 2 | data_sources | 40% | 70% | ~30 |
| 3 | gui_qt | 10% | 50% | ~80 |
| 4 | overall | 70% | 90% | ~20 |
| **Total** | - | - | **90%** | **~180** |

---

## Testing Guidelines

### For Core Module
```python
# Use fixtures for common setup
@pytest.fixture
def price_service(mock_config, mock_ninja_client):
    return PriceService(config=mock_config, ninja=mock_ninja_client)

# Test both success and error paths
def test_get_price_success(price_service):
    ...

def test_get_price_api_error(price_service):
    ...
```

### For GUI Module
```python
# Use qtbot fixture from pytest-qt
def test_widget_signal(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.data_changed):
        widget.update_data({"key": "value"})
```

### For Data Sources
```python
# Mock HTTP responses
@pytest.fixture
def mock_response():
    return {"lines": [{"name": "Exalt", "chaosValue": 150}]}

def test_parse_ninja_response(mock_response):
    client = PoeNinjaClient()
    result = client._parse_response(mock_response)
    assert result["Exalt"] == 150
```

---

## Notes

- Skip CLI modules (`rankings/cli.py`) - low value for coverage
- Skip `__main__.py` files - entry points, not business logic
- Focus on testable logic, not Qt rendering
- Use mocks liberally for external dependencies
