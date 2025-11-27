# v1.0.2 - Performance Optimizations

## Performance Improvements

### Currency Lookup Optimization (O(n) to O(1))
- Currency prices now use indexed dictionary lookup instead of linear scanning
- Dramatically faster price checks for currency items

### Divine Rate Caching
- Divine orb chaos rate is now cached for 1 hour
- Reduces redundant API calls to poe.ninja
- Improves response time for items priced in divines

### Multi-Source Pricing Early Exit
- When poe.ninja returns high-confidence data (20+ listings), skip poe.watch API call
- Reduces latency for common items by avoiding redundant validation

### Memory Management
- Session history now uses bounded deque (max 100 entries)
- Prevents unbounded memory growth during long sessions

## CI/CD Improvements

### Enhanced GitHub Actions Workflow
- Added pip dependency caching for faster builds
- Coverage reporting with pytest-cov
- Updated to Python 3.10, 3.11, 3.12 (dropped 3.9)
- Updated to latest action versions (setup-python@v5, cache@v4)
- Integration tests properly excluded from CI runs

## Technical Details

- `data_sources/pricing/poe_ninja.py`: Added `_currency_index` dict and `get_currency_price()` method
- `core/price_service.py`: Updated `_lookup_currency_price()` to use O(1) lookup, added early exit in `_lookup_price_multi_source()`
- `gui_qt/main_window.py` and `gui/main_window.py`: Changed `_history` from unbounded list to `deque(maxlen=100)`
