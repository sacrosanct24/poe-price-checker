# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Deterministic concurrency/resiliency tests:
  - `tests/unit/data_sources/test_rate_limiter.py` and `test_rate_limiter_concurrency.py` validate spacing under contention without real sleeps.
  - `tests/unit/data_sources/test_retry_with_backoff.py` and `test_retry_env_cap.py` cover retry success/failure and sleep capping via `RETRY_MAX_SLEEP` or pytest default.
  - `tests/unit/data_sources/test_response_cache_ttl.py`, `test_response_cache_reentrancy.py`, and `test_response_cache_metrics.py` harden TTL/eviction, re‑entrancy under DEBUG logging, and ratio metrics.
  - `tests/unit/data_sources/test_poe_ninja_singleton_concurrency.py` verifies single DB build under concurrent calls.
  - `tests/unit/data_sources/test_retry_mixed_exceptions.py` validates mixed 429→network error backoff behavior with capping.
  - `tests/unit/core/test_clipboard_monitor_locking.py` checks PoE item detection and that callbacks run outside internal locks.

### Changed
- Hung‑test safeguards: `pytest-timeout` default 120s (`timeout_method=thread`) via `pytest.ini` and `requirements.txt`.
- Always report slowest tests with `--durations=20` in `pytest.ini`.
- Enabled global `faulthandler` at test session start (tests/conftest.py) to dump thread stacks on timeouts/breaks.
- Observability:
  - `RateLimiter` now tracks `total_sleeps` and `total_slept_seconds`; added `metrics()` snapshot.
  - `ResponseCache.stats()` includes `hit_ratio`, `miss_ratio`, and `fill_ratio`.
- Concurrency hardening:
  - `ResponseCache` uses `threading.RLock` and guards DEBUG stats logging to avoid re‑entrant deadlocks.
  - Reduced lock scope and moved logging/callbacks out of locks in `core/clipboard_monitor.py`.
  - `data_sources/poe_ninja_client.py` and `data_sources/affix_data_provider.py` build outside locks and publish with short double‑checked locks to avoid long critical sections.
  - `BaseAPIClient._make_request` decorated with `retry_with_backoff(..., use_env_cap=True)` to avoid long sleeps in tests; respects `RETRY_MAX_SLEEP`.

### Fixed
- Deadlock in `ResponseCache.set()` when DEBUG logging called `stats()` while holding a non‑reentrant lock. Replaced with `RLock` and conditional logging.

### Notes
- Local environments should `pip install -r requirements.txt` to ensure `pytest-timeout` is active; otherwise `pytest.ini` timeout keys are ignored with a warning.

---

## [1.4.0] - 2025-11-30

### Added

#### Major Features
- **Upgrade Finder** (`Ctrl+U`) - Find best gear upgrades for your build within a budget
  - Queries Trade API for items matching your build's stat priorities
  - Ranks results by defensive impact, DPS improvement, and resistance gaps
  - Supports all equipment slots with build-aware filtering

- **Stash Grid Visualization** - Visual representation of stash tab contents
  - Heatmap overlay showing item values (red=high, blue=low)
  - Click items to inspect, double-click to price check
  - Grid View toggle in Stash Viewer window

- **Build Library** (`Ctrl+Alt+B`) - Comprehensive build management
  - Save, organize, and categorize your PoB builds
  - Filter by category (League Starter, Mapper, Bosser, etc.)
  - Quick-switch between builds with one click
  - Import from Maxroll.gg guides

#### Security & CI
- **Bandit Security Scanning** - Automated Python security analysis in CI
  - Excludes test directories from security scanning
  - Integrated with GitHub Actions workflow

- **Enhanced Code Quality** - Comprehensive CodeQL improvements
  - Fixed URL substring sanitization vulnerabilities
  - Proper hostname validation using `urlparse()`
  - MD5 hash usage marked with `usedforsecurity=False`
  - Shell injection prevention with `subprocess.run()`

#### Architecture Improvements
- **WindowManager Service** - Centralized window lifecycle management
- **PriceCheckController** - Extracted business logic from main window
- **ThemeController** - Dedicated theme management with persistence
- **Result Type** - Consistent error handling across codebase
- **BaseWorker Pattern** - Reusable background thread base class
- **MenuBuilder** - Declarative menu construction system

### Changed
- Refactored `main_window.py` to use controller/service architecture
- Improved session panel with `__getattr__` delegation pattern
- Added LRU cache size limits to ResponseCache to prevent memory leaks
- Test suite expanded from 1226 to 1413 tests

### Fixed
- **Top 20 Rankings** - Fixed tier colors and added context menu support
- **UniqueStash handling** - Proper support for specialized stash tabs
- **History TypeError** - Fixed crash when chaos_value is string
- **Shortcut conflicts** - Resolved duplicate hotkey assignments
- **Flaky tests** - Improved timing and isolation in CI tests
- Removed 50+ unused imports across codebase
- Fixed unreachable code in test files
- Fixed variable redefinition warnings

### Security
- URL sanitization now uses proper hostname validation instead of substring checks
- Shell commands use `subprocess.run()` with argument lists (no shell injection)
- MD5 usage explicitly marked as non-security (cache key generation only)

### Technical Details
- `core/upgrade_finder.py` - Upgrade finding service with trade integration
- `gui_qt/widgets/stash_grid_visualizer.py` - Visual stash representation
- `gui_qt/dialogs/build_library_dialog.py` - Build management UI
- `gui_qt/controllers/` - New controller layer for business logic
- `gui_qt/services/window_manager.py` - Window lifecycle service
- `bandit.yaml` - Security scanner configuration

---

## [1.1.0] - 2025-11-28

### Security

This release addresses multiple security improvements identified during a comprehensive security audit.

#### Token Storage (HIGH)
- OAuth tokens are now encrypted at rest using Fernet encryption with PBKDF2 key derivation
- Token files have restricted permissions (owner-only access on Windows via `icacls`, 0600 on Unix)

#### OAuth Flow (MEDIUM)
- Added state parameter validation to prevent CSRF attacks during OAuth authentication
- State mismatch now properly logs and rejects the authentication attempt

#### API Security (HIGH)
- Fixed regex pattern in Cargo API client to properly sanitize input values
- Added exponential backoff for rate-limited requests (429 responses) in PoE Stash API

#### Input Validation (MEDIUM)
- PoB integration now uses `urlparse` for safer URL handling instead of string manipulation
- Item Inspector uses `html.escape()` to prevent XSS in displayed item names

### Changed
- Upgraded test suite from 671 to 1200+ tests with improved security coverage
- OAuth tests updated to verify encrypted token storage

### Technical Details
- `core/secure_storage.py`: Added `_restrict_file_permissions()` method for cross-platform file security
- `core/poe_oauth.py`: Integrated SecureStorage for token encryption/decryption
- `data_sources/cargo_api_client.py`: Improved regex character class for input sanitization
- `data_sources/poe_stash_api.py`: Added retry logic with exponential backoff (2s, 4s, 8s)
- `core/pob_integration.py`: Safe URL parsing with `urlparse`
- `gui_qt/widgets/item_inspector.py`: HTML escaping for user-visible content

---

## [1.0.0] - 2025-11-27

### Added

#### Core Features
- **Item Price Checking**: Paste items from Path of Exile to get instant price estimates
- **Clipboard Monitoring**: Automatic detection of copied items with Ctrl+C
- **Multiple Price Sources**: Integration with poe.ninja and poeprices.info APIs
- **PoE 2 Support**: Full compatibility with Path of Exile 2 items and mechanics

#### Build Integration
- **Path of Building Import**: Import character builds via PoB share codes or Pastebin URLs
- **Build Archetype Detection**: Automatic identification of build types (life, ES, hybrid, attack, spell, etc.)
- **Build-Effective Values**: See how item stats translate to actual build power
- **Upgrade Comparison**: Compare items against your current equipped gear

#### Rare Item Evaluation
- **Smart Scoring System**: Multi-factor evaluation considering build relevance
- **Tier Analysis**: Display of mod tiers with RePoE data integration
- **Archetype Matching**: Scores items based on compatibility with build archetypes
- **Configurable Weights**: Customize evaluation priorities for different build types

#### BiS Item Search
- **Trade Search Integration**: Generate optimized trade searches based on build needs
- **Guide Gear Extraction**: See what items your reference build recommends
- **Ideal Rare Calculator**: View ideal mod tiers for any equipment slot
- **Priority System**: Set critical, important, and nice-to-have stat priorities

#### Stash Viewer
- **Account Stash Access**: View all stash tabs with POESESSID authentication
- **Automatic Valuation**: Price all items in your stash tabs
- **Search and Filter**: Find items by name with minimum value filtering
- **Tab-by-Tab Browsing**: Navigate stash tabs with value summaries

#### Price Rankings
- **Market Overview**: See most valuable items by category
- **Currency Rates**: Live exchange rates for all PoE currencies
- **Historical Context**: Compare current prices to market trends

#### Sales Tracking
- **Record Sales**: Track items you've sold with prices and notes
- **Sales Dashboard**: View total earnings and daily statistics
- **Recent Sales History**: Browse past sales with filtering

#### User Interface
- **Dark Theme**: PoE-inspired dark color scheme with gold/blue accents
- **Responsive Layout**: Resizable windows with splitter panels
- **Item Inspector**: Detailed view with mod highlighting and copy support
- **Status Bar**: League info, Divine:Chaos ratio, and connection status

### Technical Features
- **PyQt6 GUI**: Modern, native-feeling desktop application
- **SQLite Database**: Local storage for sales, settings, and cache
- **Comprehensive Testing**: 200+ unit tests with pytest
- **Type Annotations**: Full type hints for better code quality
- **Modular Architecture**: Clean separation of core logic, data sources, and UI

### Documentation
- README with installation and usage instructions
- Development guides in `docs/` folder
- API integration documentation
- Code of Conduct and Contributing guidelines

---

## Version History Note

This is the initial public release (v1.0.0). The project was developed privately before this release. Future versions will include detailed changelogs tracking all modifications.

---

[Unreleased]: https://github.com/sacrosanct24/poe-price-checker/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/sacrosanct24/poe-price-checker/compare/v1.1.0...v1.4.0
[1.1.0]: https://github.com/sacrosanct24/poe-price-checker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/sacrosanct24/poe-price-checker/releases/tag/v1.0.0
