Here’s a development doc you can drop into `docs/` or the repo root as something like `DEVELOPMENT_GUIDE.md`. It’s based on the current snapshot in `exilePriceCheck.zip` (not generic guesses).

---

# PoE Price Checker – Development Guide

*Last updated: 2025-11-22*

## 1. Project Goals & Non-Functional Requirements

**High-level vision**

PoE Price Checker is a desktop-first tool for Path of Exile 1 & 2 that aims to be:

* A **serious portfolio piece** (clean architecture, tests, logging, config management).
* A **practical trading tool** that:

  * Parses in-game item text.
  * Queries multiple external data sources (e.g., PoE Ninja, Trade API).
  * Shows consolidated pricing with trade URLs and quick actions.
* A foundation for:

  * **Sales tracking** and profit analytics.
  * **Price-learning logic** that incorporates personal sales history.
  * A **plugin system** for extensibility.

**Non-functional goals**

* Python **3.12+**.
* Strong use of **type hints**, **dataclasses**, and **logging**.
* Clear separation between:

  * Core domain logic (`core/`)
  * External data sources (`data_sources/`)
  * Persistence layer (`core/database.py`)
  * UI (`gui/`)
* Easy to test:

  * Unit tests for core modules and data sources.
  * Integration tests for the GUI and `AppContext`.
* Configuration stored in a **user directory** (`~/.poe_price_checker/`).

---

## 2. Repository Layout

Top-level structure (excluding virtualenv and tooling artifacts):

* `poe_price_checker.py` – primary entrypoint to launch the app.
* `main.py` – older/secondary entrypoint; currently present but `poe_price_checker.py` is the canonical one.
* `core/` – core domain logic and services:

  * `app_context.py` – wiring factory / dependency injection for the app.
  * `config.py` – config file handling, game/league settings.
  * `database.py` – SQLite schema and persistence layer (checked items, sales, price history, plugin state).
  * `game_version.py` – enums/data for PoE1/PoE2 and related config (`GameVersion`, `GameConfig`).
  * `item_parser.py` – parsing PoE item text into structured models.
  * `price_service.py` – single-source pricing service (currently PoE Ninja).
  * `price_multi.py` – multi-source aggregation (PoE Ninja, undercut logic, etc.).
  * `value_rules.py` – heuristics & flags about item “value”.
  * `derived_sources.py` – logic that derives extra metrics from other sources (e.g., undercut).
  * `logging_setup.py` – centralized logging configuration for the app.
* `data_sources/` – integration with external APIs:

  * `base_api.py` – base API client with rate limiting, caching, retry logic.
  * `pricing/poe_ninja.py` – PoE Ninja API client and source adapter.
  * `pricing/trade_api.py` – stubbed official Trade API source.
  * `official/` – placeholder for official API integrations.
  * `wiki/` – placeholder for wiki integrations.
* `gui/`:

  * `main_window.py` – Tkinter GUI (`PriceCheckerGUI` and related widgets).
* `plugins/`:

  * `examples/` – currently only an empty `__init__.py`; future plugin examples go here.
* `scripts/` – reserved for helper scripts; currently empty or minimal.
* `tests/`:

  * `unit/core/` – tests for config, database, item parser, multi-source pricing, value rules, undercut source.
  * `unit/data_sources/` – tests for PoE Ninja client and trade API stub.
  * `integration/core/` – `AppContext`-level tests (league handling, etc.).
  * `integration/gui/` – GUI behavior tests (copy row, details, export TSV, item inspector, etc.).
  * `fixtures/` – test fixtures as needed.
  * `README_test.md` – testing notes.
* Docs & meta:

  * `README.md` – project overview and quickstart.
  * `Context.md` – narrative context / design background.
  * `roadmap.md` – feature roadmap.
  * `TESTING.md`, `TESTING_SUMMARY.md` – how tests are structured and current coverage.
  * `code_review.md` – earlier code review notes.

---

## 3. Runtime Architecture

### 3.1 AppContext (Composition Root)

**File:** `core/app_context.py`

`AppContext` is the central wiring object that creates and holds:

* `Config` instance (user settings, league, etc.).
* `Database` instance (SQLite database under `~/.poe_price_checker/data.db` by default).
* `ItemParser`.
* `PoeNinjaAPI` client.
* `PriceService` + `MultiSourcePriceService`.
* `GameConfig` / `GameVersion`.

This file is effectively the **composition root**:

* `create_app_context()` is the canonical factory used by the entrypoint (`poe_price_checker.py`).
* The Tkinter GUI receives an `AppContext` which it uses to access services and the DB.

**Best practice status:**
Good separation of concerns; `AppContext` keeps wiring out of UI and core modules. Dependencies are clearly injected.

---

### 3.2 Configuration & Game Version

**File:** `core/config.py`, `core/game_version.py`

* `GameVersion` enum describes PoE1 vs PoE2.
* `GameConfig` holds per-version config (leagues, base URLs, etc.).
* `Config` is responsible for:

  * Loading and saving a JSON config file from the user directory.
  * Storing:

    * Current game version & league.
    * UI preferences.
    * Data source settings.
    * Misc app settings.

Config uses `pathlib.Path` for paths and logs actions through the `logging` module.

**Best practice status:**
Reasonable use of structured config. Could in future adopt `pydantic` or similar, but current approach is clean enough.

---

### 3.3 Database Layer (SQLite)

**File:** `core/database.py`

**Responsibilities:**

* Managing a single SQLite connection (`self.conn`).
* Initializing / migrating schema via `_initialize_schema()`:

  * `schema_version` – internal version tracking.
  * `checked_items` – history of items the user has price-checked.
  * `sales` – sales/tracking table.
  * `price_history` – snapshots of price data over time.
  * `plugin_state` – persisted plugin enable/disable state and config blobs.
* Providing methods such as:

  * `add_checked_item(...)` – stores a record for each processed item.
  * `get_recent_checked_items(...)` – used for session/history views.
  * `create_sale_entry(...)` – creates a sale row (listed item).
  * `complete_sale(...)` – marks a sale as sold, computes `time_to_sale_hours`.
  * `get_sales(sold_only=False, limit=...)` – sales listing API for dashboards.
  * `add_price_snapshot(...)` / `get_price_history(...)` – handle price history.
  * `get_stats()` – aggregated metrics (count of checked_items, sales, etc.).
* Utilities:

  * `_ensure_utc(..)` & `_parse_db_timestamp(..)` normalizing timestamps and preventing negative durations.
  * `transaction()` context manager for explicit transactional scopes.

**Current sales schema** (abridged, from code):

* `sales`:

  * `id INTEGER PRIMARY KEY`
  * `item_id INTEGER` (optional link to `checked_items`)
  * `item_name TEXT NOT NULL`
  * `item_base_type TEXT`
  * `listed_price_chaos REAL NOT NULL`
  * `listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
  * `sold_at TIMESTAMP`
  * `actual_price_chaos REAL`
  * `time_to_sale_hours REAL`
  * `relisted BOOLEAN DEFAULT 0`
  * `notes TEXT`

This provides a good starting point for your “Record Sale” feature:

* **Listing**: `create_sale_entry(...)`
* **Sale completion**: `complete_sale(...)`

**Best practice status:**

* Uses **parameterized queries** (good for injection safety).
* Explicit schema versioning.
* Logging present.
* Direct `sqlite3` usage is fine for a project of this size.
* There is a clear separation between **schema initialization** and **query methods**.

Recommended improvements (non-blocking):

* Consider thin **data classes** for rows (`CheckedItem`, `Sale`, etc.) to avoid raw `dict` results.
* Centralize timestamp handling by always storing ISO-8601 UTC and parsing using a helper (already partially done).
* Future: if complexity grows, consider a lightweight ORM (e.g., SQLModel, SQLAlchemy) – but *not required* right now.

---

### 3.4 Item Parsing & Value Heuristics

**Files:** `core/item_parser.py`, `core/value_rules.py`

* `ItemParser`:

  * Takes raw PoE item text (copied from the game).
  * Produces a structured object with:

    * Item name, base type.
    * Rarity, item level, required level, influences, etc.
    * Affixes, sockets, other metadata.
  * Has comprehensive unit tests in `tests/unit/core/test_item_parser.py` that cover parsing of different categories.

* `value_rules.py`:

  * Encodes “value rules” via dataclasses like `ValueRule`.
  * Rules include:

    * `slots` (what kind of items they apply to).
    * `conditions` (strings / predicates used to flag interesting items).
    * Optional `weight` and `flag` to indicate value categories (e.g., “High-value base”, “Check further”, etc.).
  * There are unit tests in `test_value_rules.py` to validate rule application logic.

**Best practice status:**

* Good separation: parsing vs value heuristics.
* Dataclasses + type hints make it easy to extend.
* Tests already exist and should be kept updated as parsing logic evolves for PoE2.

---

### 3.5 Pricing Services (Single-Source and Multi-Source)

**Files:** `core/price_service.py`, `core/price_multi.py`, `core/derived_sources.py`, `data_sources/pricing/poe_ninja.py`

* `PriceService`:

  * Uses `Config`, `ItemParser`, `Database`, and `PoeNinjaAPI` to:

    * Parse item text.
    * Fetch prices from PoE Ninja.
    * Persist a `checked_items` record.
    * Return a normalized result suitable for display in the GUI.

* `MultiSourcePriceService`:

  * Composes multiple pricing sources:

    * PoE Ninja.
    * Derived/undercut sources (e.g., computing a “list slightly under market” value).
  * Produces a multi-source record used by the GUI:

    * One row per source.
    * Trade URL per source.
    * Display fields (chaos/divine values, relative value, etc.).
  * There are unit tests for MultiSource behavior (`tests/unit/core/test_price_multi.py`), including:

    * Sorting/ordering behavior.
    * Under-cut logic.

* `derived_sources.py`:

  * Implements logic for synthesizing derived sources from base sources (e.g., undercut by X%, combine PoE Ninja data into a “recommended price”).

* `PoeNinjaAPI` (`data_sources/pricing/poe_ninja.py`):

  * Extends `BaseAPIClient`.
  * Integrates PoE Ninja endpoints for:

    * Leagues.
    * Raw pricing data (currencies, items).
  * Unit tests in `tests/unit/data_sources/test_poeninja_*`.

**Best practice status:**

* Good boundary: data_sources contain HTTP logic; core services use them.
* Multi-source aggregation is clearly separated in `price_multi.py`.
* Tests verify expected behaviors for price merging.

Recommended improvement:

* Remove the `sys.path.insert(...)` hack in `poe_ninja.py` and use standard imports (the project is already importable as a package from the repo root when run correctly).

---

### 3.6 GUI Architecture (Tkinter)

**File:** `gui/main_window.py`

Key components:

* `PriceCheckerGUI` – main window class, responsible for:

  * Tk root creation and main loop.
  * Menu bar (File, View, Dev, Help).
  * Item input area:

    * Multi-line text box to paste item text.
    * “Check Price” button + keyboard shortcuts (`Ctrl+Enter`, etc.).
  * **Results table**:

    * Displays the multi-source pricing rows.
    * Newest results shown first.
    * Right-click context menu:

      * Open selected row’s trade URL in a browser.
      * Copy row as text.
      * Copy row as TSV.
      * View row details.
      * (Planned) “Record Sale…” per row.
  * **Item Inspector sidebar**:

    * Shows parsed item info from the current input:

      * Name, base type, rarity, item level.
      * Derived value flags.
      * Source summary.
    * Graceful handling of parse failures.
    * Backed by integration tests in `tests/integration/gui/test_gui_item_inspector_and_sources.py`.
  * **Summary banner**:

    * Shows human-readable summary of current results.
    * “Copy Summary” action for quick sharing.
  * **Dev menu**:

    * Sample item paste buttons:

      * Currency / Map / Unique / Rare, etc. – very useful for demos and testing.

The GUI interacts with the backend via `AppContext` and `MultiSourcePriceService`, **not** directly with data sources or HTTP clients.

**Best practice status:**

* GUI code is fairly well-structured for Tkinter:

  * Uses helper methods to build each section.
  * Keeps stateful attributes on `PriceCheckerGUI`.
  * Uses tests to verify behavior (rare but great for Tkinter).
* Clear separation between display logic and backend services.

Recommended future structure:

* As complexity grows (e.g., adding a “Recent Sales” panel), consider:

  * Splitting some GUI components into smaller classes (e.g., `ItemInspectorFrame`, `ResultsTableFrame`).
  * Keeping event handlers thin and delegating logic to methods that are easier to test.

---

### 3.7 Entry Points & Scripts

**File:** `poe_price_checker.py`

* Primary console entrypoint:

  * Sets up logging via `core.logging_setup`.
  * Calls `create_app_context()`.
  * Launches the Tkinter GUI (`PriceCheckerGUI`).

**File:** `main.py`

* Present, but appears to be a legacy/alternate entry; `poe_price_checker.py` is preferred and consistent with tests and docs.

**scripts/**

* Currently empty or minimal – reserved for future:

  * DB maintenance/util scripts.
  * Data export/import tools.
  * CLI tools for batch operations.

---

### 3.8 Data Sources & Base API Client

**File:** `data_sources/base_api.py`

* Provides a reusable base for HTTP API clients with:

  * `requests` for network calls.
  * Simple in-memory caching.
  * Rate limiting.
  * `retry_with_backoff` decorator for retries on failure.
  * Basic error handling and logging.

**File:** `data_sources/pricing/trade_api.py`

* Skeleton adapter for the official trade API:

  * Uses a `TradeApiSource` class.
  * `check_item(...)` currently:

    * Calls `search_and_fetch(...)` on a `client` object.
    * Iterates a stub list of `listing` dicts.
    * Populates normalized fields with `# TODO` markers (e.g., `item_name`, `variant`, `links`, `chaos_value`, etc.).
  * Unit test exists (`tests/unit/data_sources/test_trade_api_source.py`) that expects the interface to be stable, even if implementation is stubbed.

**Best practice status:**

* Base API client is fine for a small desktop app, but:

  * It uses `logging.basicConfig` which can conflict with the more deliberate logging setup in `core/logging_setup.py`. It’s better to:

    * Remove `logging.basicConfig` here and rely on centralized logging configuration.
* Trade API implementation is intentionally incomplete; TODOs are clear and localized.

---

### 3.9 Plugin System (Current State)

**Files:** `plugins/`, `core/database.py` (`plugin_state` table)

* There is a `plugin_state` table in the DB schema:

  * Stores plugin IDs, enabled flag, and JSON config.
* `plugins/examples/__init__.py` exists but contains no sample plugins yet.
* No dynamic plugin loading logic is present yet (e.g., no discovery of `plugins/*.py` modules).

**Current practical status:**

* The **infrastructure** (DB table, folder structure, roadmap) is in place.
* A real plugin system still needs:

  * A loader that:

    * Scans `plugins/`.
    * Imports modules implementing a defined interface (`register_sources`, `on_item_parsed`, etc.).
  * Integration logic in `AppContext` to wire plugin sources into `MultiSourcePriceService`.
  * Example plugins under `plugins/examples/` demonstrating the interface.

---

## 4. Testing Strategy

**Configuration:** `pytest.ini`, `TESTING.md`, `TESTING_SUMMARY.md`

* **Unit tests**:

  * `tests/unit/core/`:

    * `test_config.py` – config load/save.
    * `test_database.py` – DB behavior including sales, price history, stats.
    * `test_item_parser.py` – parsing for multiple item types.
    * `test_price_multi.py` – multi-source price aggregation logic.
    * `test_undercut_source.py` – checks derived/undercut logic.
    * `test_value_rules.py` – value rule behavior.
  * `tests/unit/data_sources/`:

    * `test_poeninja_leagues.py`, `test_poeninja_gems_and_divcards.py` – PoE Ninja client behavior.
    * `test_trade_api_source.py` – Trade API stub’s interface.

* **Integration tests**:

  * `tests/integration/core/test_app_context_league.py` – ensures `AppContext` uses correct league / config wiring.
  * `tests/integration/gui/`:

    * `test_gui_copy_row.py` – copying results row to clipboard/TSV.
    * `test_gui_export_and_copy_all_tsv.py` – TSV export of results.
    * `test_gui_details_and_status.py` – detail windows and status messages.
    * `test_gui_item_inspector_and_sources.py` – item inspector + multi-source display.

* **Fixtures**:

  * `tests/fixtures/` – provides sample item text, sample responses, etc.

**How to run tests:**

From the repo root:

```bash
pytest
```

(Optionally use markers like `-m unit` vs `-m integration` if configured.)

**Best practice status:**

* Strong test structure for a desktop app.
* GUI tests via Tkinter are non-trivial and add a lot of value.
* DB behavior and sales logic are covered, which is crucial for your upcoming “record sale” features.

---

## 5. Logging & Error Handling

**File:** `core/logging_setup.py`

* Central place to configure logging:

  * File handler with detailed formatter (timestamps, module, level).
  * Console handler with simpler format.
  * Log file stored in the user’s PoE Price Checker directory.

**Cross-cutting behavior:**

* Most major modules (`config`, `database`, `price_service`, `data_sources`) obtain per-module loggers via `logging.getLogger(__name__)`.
* Error conditions from external APIs and DB operations are logged, not silently ignored.

**Recommended alignment:**

* `data_sources/base_api.py` currently calls `logging.basicConfig`. In a larger app with custom logging, this can conflict; it should instead just use `logging.getLogger(__name__)` and let the app configure handlers centrally.

---

## 6. Identified Inconsistencies & Recommended Improvements

These are **non-blocking** issues but worth noting for future refactors:

1. **Import / path hack in `poe_ninja.py`**

   * `sys.path.insert(0, str(Path(__file__).parent.parent.parent))` is used to make imports work when running the file directly.
   * Recommendation:

     * Rely on the package layout instead (run from repo root with `python -m poe_price_checker` or similar).
     * Remove the `sys.path` manipulation once you standardize how the app and tests are invoked.

2. **Logging configuration duplication**

   * `data_sources/base_api.py` uses `logging.basicConfig(level=logging.INFO)`.
   * `core/logging_setup.py` sets up the “real” configuration (file + console handlers).
   * Recommendation:

     * Remove `basicConfig` from `base_api.py` and rely on app-level logging config only.

3. **Database row handling**

   * DB methods return `dict` objects for rows (via `sqlite3.Row` to dict).
   * Recommendation:

     * Non-urgent, but consider thin dataclasses like `CheckedItemRow`, `SaleRow` if you want more structure & IDE help.

4. **Trade API stub (`trade_api.py`)**

   * Contains TODOs around extracting specific fields from `listing`.
   * Recommendation:

     * When you are ready to integrate the official Trade API, treat this file as the main place to implement real HTTP calls and robust normalization logic.

5. **Tests naming/comment mismatch in `test_database.py`**

   * The header text mentions “patches” and “these patches should be applied to test_database.py”, which doesn’t match the file’s role inside the repo.
   * Recommendation:

     * Clean up the header comment so the intent is clear (it’s the main `test_database.py`, not a patch file).

6. **Plugin system not yet wired**

   * Schema and folder structure support plugins, but:

     * No loader.
     * No plugin interface.
   * Recommendation:

     * Define a simple plugin protocol (e.g., `def register(app_context: AppContext) -> None`) and a loader that imports modules from `plugins/`.

---

## 7. How Upcoming Features Fit Into the Current Design

You’ve already planned:

1. **Sales Recording Backend & GUI**

   * Use existing DB methods:

     * `create_sale_entry(...)` for listings.
     * `complete_sale(...)` for marking as sold.
   * The new “Record Sale…” UI action in `PriceCheckerGUI` should:

     * Use the selected result row (item name, base type, league, chaos price).
     * Create a sale entry for the listing.
     * Immediately call `complete_sale(...)` or store as “listed” and let the user complete it later.
   * `Database.get_sales(...)` already supports retrieving latest sales for a “Recent Sales” widget.

2. **Sales Dashboard**

   * Build on `get_sales()` and `get_price_history()` to compute:

     * 7-day chaos earned.
     * Best-selling items (by count, by chaos).
   * This can be a new panel/tab in the GUI, or a simple modal dialog.

3. **Price Learning Engine**

   * Combine:

     * External prices (from PoE Ninja, Trade API).
     * Internal realized prices (from `sales.actual_price_chaos`).
   * MultiSourcePriceService is a good place to:

     * Inject a “learned price” as an additional source or derived metric.
     * Store snapshots of learned values into `price_history` for analysis.

4. **Plugin System Foundations**

   * `plugin_state` table and `plugins/` folder are ready.
   * You can introduce:

     * A plugin loading module in `core/plugins.py` (or similar).
     * A registration interface for:

       * New pricing sources.
       * Post-processing hooks on parsed items.
       * Notification hooks when items meet certain value rules.

---

## 8. Conventions & Best Practices to Follow Going Forward

* **Python version:** stick with 3.12+ (as advertised).
* **Type hints everywhere** where practical (functions, methods, attributes).
* **Dataclasses** for domain entities (items, rules, sales, configs where appropriate).
* **Logging**:

  * Use module-level `LOG = logging.getLogger(__name__)`.
  * Avoid calling `logging.basicConfig` inside modules.
* **Database access**:

  * Always use parameterized queries (`?` placeholders).
  * Use helper methods for time handling (`_ensure_utc`, `_parse_db_timestamp`).
* **Testing**:

  * For any new feature:

    * Unit test in the appropriate `tests/unit/...` module.
    * Integration test if it touches the GUI (`tests/integration/gui/...`) or AppContext wiring.
* **GUI structure**:

  * Keep Tkinter event handlers thin.
  * Extract reusable widgets into small classes if complexity grows.
* **Data sources**:

  * Keep HTTP logic in `data_sources/`.
  * Keep business logic (how to interpret prices, what to show to users) in `core/`.

---

## 9. Suggested File to Add to the Repo

You can save this document as:

* `DEVELOPMENT_GUIDE.md` (recommended)
  or
* `docs/development_guide.md` (and link it from `README.md`)

This document is intended to:

* Serve as a **single reference** for the architecture and main components.
* Help future ChatGPT sessions quickly regain context by referring to:

  * `AppContext`
  * `Database` methods and schema
  * Pricing service structure
  * GUI behavior and tests
* Guide contributors on **where to put new code** and how to keep it consistent.

---
