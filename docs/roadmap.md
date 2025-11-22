Here’s an updated **Roadmap v2 – 2025-11-21** you can drop straight into `ROADMAP.md` and call it a night. 😴

I’ve **kept your original structure**, but updated Phase 1 to reflect what we’ve actually done (GUI refactor + live poe.ninja pricing), and added a new **“Near-Term Next Steps”** block so tomorrow’s session has a clean landing zone.

---

# PoE Price Checker – Development Roadmap (Updated 2025-11-21)

**Project Vision:** Over-engineered, portfolio-worthy PoE economy tool supporting both PoE1 & PoE2

---

## 🎯 PROJECT GOALS

### Primary Objectives

1. **Learning Experience:** Deep dive into Python architecture, APIs, databases, plugins
2. **Portfolio Piece:** Demonstrate professional development practices
3. **Practical Tool:** Actually useful for PoE trading and economy analysis
4. **Expandability:** Plugin system for community contributions

### Success Criteria

* [ ] Supports both PoE1 and PoE2 seamlessly
* [ ] 5+ data sources integrated
* [ ] Plugin system with 3+ example plugins
* [ ] Sales tracking with price learning
* [ ] Web API + documentation
* [ ] 80%+ test coverage
* [ ] Clean, documented code reviewable by other LLMs

---

## 📊 FEATURE BREAKDOWN

### ✅ Phase 1: Foundation, GUI Refactor & Pricing Integration (CURRENT)

#### Week 1–2: Infrastructure

* [x] PyCharm setup
* [x] Initial working GUI
* [ ] Git initialization
* [ ] GitHub repository creation
* [ ] Project structure refactoring
* [ ] CONTEXT.md (this file)
* [ ] requirements.txt
* [ ] .gitignore setup

#### Week 2–3: Core Architecture

* [x] `game_version.py` – PoE1/PoE2 enum
* [x] `config.py` – Config object with per-game settings and league info
* [x] `item_parser.py` – Parser wired into the app (basic PoE1 support)
* [x] `database.py` – SQLite wrapper (initial version) used by app context
* [ ] `database.py` – Migrations, helpers & query utilities polished
* [ ] `config.py` – Enhanced validation, error reporting
* [ ] `item_parser.py` – Refined parsing rules + full unit test suite

#### Week 3–4: Data Sources – Pricing (PoE1 focus)

* [x] `data_sources/base_api.py` – Abstract API client with:

  * [x] Base request logic
  * [x] Simple rate limiting
  * [x] Caching via in-memory store
  * [x] Request logging + User-Agent
* [x] `data_sources/pricing/poe_ninja.py` – PoE1 pricing

  * [x] Leagues detection (`get_current_leagues`, `detect_current_league`)
  * [x] `get_currency_overview()` with divine/chaos rate
  * [x] `load_all_prices()` cache (currency + uniques + misc)
  * [x] `find_item_price()` for:

    * Gems (`SkillGem` overview)
    * Uniques (weapons, armour, accessories, flasks, jewels)
    * Divination cards
    * Fragments
    * Unique maps (+ fallback to Map)
    * Essences, fossils, scarabs, oils, incubators, vials via name heuristics
* [ ] `poe2_scout.py` – PoE2 pricing integration

  * [ ] Swagger/OpenAPI client
  * [ ] PoE2-specific error handling & fallbacks
* [ ] `poe_watch.py` – Historical pricing

  * [ ] Time-series data storage
  * [ ] Trend helpers

#### Phase 1.5: App Context, GUI Wiring & Live Pricing (COMPLETED THIS WEEK)

* [x] `core/app_context.py`

  * [x] Central `AppContext` dataclass with:

    * `config`, `parser`, `db`, `poe_ninja`, `price_service`
  * [x] `create_app_context()`:

    * Builds config
    * Initializes DB
    * Initializes `PoeNinjaAPI` with league detection
    * Injects `PriceService`

* [x] `core/price_service.py`

  * [x] `PriceService.check_item(item_text: str) -> list[dict]`
  * [x] Uses `ItemParser` → parsed item
  * [x] Uses `PoeNinjaAPI`:

    * Currency via `get_currency_overview()` (e.g., Divine Orb)
    * Items via `find_item_price(...)`
  * [x] Chaos → Divine conversion using:

    * `Config.divine_rate` (if set) OR
    * `PoeNinjaAPI.divine_chaos_rate`
  * [x] Graceful fallbacks for unsupported/unknown items (`source="not found"`)

* [x] GUI entrypoint & logging

  * [x] `main.py` using `create_app_context()` and `gui.main_window.run(ctx)`
  * [x] Unified logging via `core.logging_setup` (app + GUI + API + DB)
  * [x] Status bar & log messages wired (Ready / Checking / Complete / Error)

#### GUI Refactor & Results Table (UPDATED)

* [x] `gui/main_window.py` refactor:

  * [x] Split `_create_layout()` into:

    * `_create_input_area()`
    * `_create_results_area()`
    * `_create_status_bar()`
  * [x] MainWindow uses an injected `AppContext` with `price_service`
  * [x] Status bar integrated with live league/status messages
  * [x] Robust logging on price check, clear, errors

* [x] `ResultsTable` abstraction (inside `gui/main_window.py` for now):

  * [x] Encapsulates `ttk.Treeview` for results
  * [x] Column configuration + tags
  * [x] Autosize columns helper
  * [x] `insert_results(rows)` normalizing:

    * `item_name`, `variant`, `links`, `chaos_value`, `divine_value`, `listing_count`, `source`
  * [x] Row highlighting hooks (e.g. high-value, fractured, craft bases – ready to extend)
  * [x] `copy_row_as_tsv()` / `_copy_row_tsv()` helper
  * [x] `export_tsv(...)` implementation (hooked to “Export TSV…” menu)
  * [x] Column visibility support (backend ready; UI toggle gear planned)

* [x] GUI Quality-of-Life:

  * [x] Auto-paste detection (<<Paste>> triggers auto-check)
  * [x] Menus:

    * File (Clear, Export TSV, Open Log, Open Config Folder)
    * Help / Links (GGG, PoEDB, Maxroll, etc.)
    * About dialog
  * [x] Results table supports Ctrl+C copy of selected row as TSV
  * [x] Cleaned Tk callback signatures (no bogus `event` warnings)
  * [x] Removed unstable dark mode; planned redesigned theming later

#### Testing (Phase 1 scope)

* [x] All existing tests green after refactor:

  * [x] `tests/test_gui_copy_row.py`

    * Headless Tk fixture (`tk_root`)
    * `_make_fake_gui(...)` constructing a fake `PriceCheckerGUI` + tree
    * `_get_selected_row()` returns all columns
    * `_copy_row_tsv()` verified TSV string content
  * [x] GUI tests now resilient to missing physical display (`TclError`→skip)
* [ ] Expanded tests for:

  * [ ] `PriceService.check_item` (with mocks for `PoeNinjaAPI`)
  * [ ] `PoeNinjaAPI.find_item_price` edge cases
  * [ ] AppContext creation for PoE1 vs PoE2

**Phase 1 Deliverable (updated):**
Working PoE1-focused price checker with:

* Live poe.ninja integration
* Functional GUI with clean architecture
* Logging, basic exports, copy-to-clipboard, and a refactored ResultsTable

---

### 🔌 Phase 2: Plugin System (Weeks 5–7) *(unchanged, not started yet)*

**Core Plugin Infrastructure**

* [ ] `base_plugin.py` – Plugin interface:

  ```python
  class PluginBase(ABC):
      def initialize(app_context)
      def on_item_checked(item_data)
      def on_price_update(price_data)
      def on_sale_recorded(sale_data)
      def get_config_schema()
      def shutdown()
  ```
* [ ] `plugin_manager.py` – Discovery & lifecycle:

  * Auto-discover plugins in `/plugins`
  * Dependency resolution
  * Enable/disable via GUI
  * Config UI generation from schema
  * Sandbox/safety checks
* [ ] Plugin DB table for plugin state

**Example Plugins**

1. **Price Alert Plugin**
2. **Export Plugin**
3. **Statistics Plugin**

**Deliverable:** Plugin system with 3 working plugins, GUI management.

---

### 📈 Phase 3: Sales Tracking & Price Learning (Weeks 8–10)

*(Same high-level plan as before – not started yet, but Phase 1 groundwork supports it.)*

---

### 🎮 Phase 4: Meta Analysis from PoB (Weeks 11–13)

*(Same as before.)*

---

### 🌐 Phase 5: Official Trade API Integration (Weeks 14–16)

*(Same as before; `PriceService` and `AppContext` are now good injection points for Trade API pricing.)*

---

### 🔧 Debugging Task: Chaos Orb / Currency Normalization

**Status:** Partially addressed, still worth a future normalization pass
**Category:** Parser / Name Matching
**Severity:** Low (Chaos Orb = 1c by definition; Divine & other currency now work well)

**Current State**

* Currency now uses `PoeNinjaAPI.get_currency_overview()`:

  * `Divine Orb` verified working (`138.7c`, `1.00 div`, `source = poe.ninja currency`)
* Chaos Orb currently handled via:

  * Normalized matching logic
  * (Optionally) special-case fallback = 1c

**Long-Term Fix Plan (keep):**

1. Debug tracing for unmatched currency keys
2. Shared `normalize(name: str) -> str` helper
3. Improved multi-step currency matching (strict → normalized → fuzzy)
4. Unit tests for Chaos Orb & common currencies
5. Retire hard-coded fallback once matching is robust

---

### 🖼️ Phase 6: Computer Vision (Weeks 17–19)

*(Same as before.)*

---

### 🌍 Phase 7: Web Dashboard & API (Weeks 20–23)

*(Same as before.)*

---

### 📊 Phase 8: Market Trend Analysis (Weeks 24–26)

*(Same as before.)*

---

### 🔔 Phase 9: Real-Time Alerts & Webhooks (Weeks 27–28)

*(Same as before.)*

---

### 🧪 Phase 10: Testing & Documentation (Weeks 29–30)

*(Same as before, but Phase 1 is already nudging coverage up.)*

---

## 🛠️ TECH STACK (UNCHANGED)

*(Keep your existing section; still valid.)*

---

## 📁 FINAL PROJECT STRUCTURE (UNCHANGED, BUT NOW PARTIALLY REAL)

Note: `core/app_context.py`, `core/price_service.py`, `data_sources/pricing/poe_ninja.py`, and `gui/main_window.py` are now aligned with this layout.

---

## 🎓 LEARNING OBJECTIVES / DEVOPS / TIMELINE

*(Keep as-is; roadmap still holds.)*

---

## 🎯 NEAR-TERM NEXT STEPS (NEXT 1–2 SESSIONS)

When you open a fresh chat tomorrow, this is the “start here” list:

1. **Threading for Price Checks**

   * Move `PriceService.check_item` calls onto a worker thread
   * Keep GUI responsive for long-running lookups
   * Add a “spinner” or subtle status indicator

2. **ResultsTable & Export Polish**

   * Add CSV/Excel export option alongside TSV
   * Make “Export TSV…” respect current column visibility
   * Add keyboard shortcuts (Ctrl+L clear, Ctrl+E export, Ctrl+R re-check)

3. **Column Visibility UI**

   * Add a small gear icon / menu to toggle columns
   * Persist column visibility in config

4. **Unit Tests**

   * Add tests for `PriceService.check_item` (mock `PoeNinjaAPI`)
   * Add tests for `_lookup_currency_price` (Divine, Exalt, Chaos, etc.)
   * Add tests for `PoeNinjaAPI.find_item_price` with fake responses

5. **Prep for PoE2**

   * Add a stub `Poe2PricingService` + `Poe2API` interface
   * Make `AppContext` choose price service based on `GameVersion`

---

## 🧭 END-OF-SESSION SUMMARY (2025-11-21)

**Focus:** Live Pricing Integration & Coverage

**Work Completed**

* Created and wired `PriceService` into `AppContext` and GUI
* Integrated `PoeNinjaAPI` with:

  * Currency (`get_currency_overview`)
  * Uniques, div cards, fragments, etc. (`find_item_price`)
* Implemented `PriceService.check_item` → GUI-friendly rows
* Implemented currency pricing (e.g., Divine Orb) with chaos/divine conversion
* Extended poe.ninja coverage to:

  * Unique maps
  * Fragments, essences, fossils, scarabs, oils, incubators, vials (heuristic-based)
* Verified GUI behavior:

  * Status updates for ready/checking/complete/error
  * Logs show correct wiring and no unhandled exceptions
  * All existing tests green, including GUI copy-row tests

**Blockers / To Watch**

* Rare items (like rare cluster jewels) still “not found” – require Trade API or live search
* No threading yet → heavy operations still synchronous
* Chaos/currency normalization could use a proper normalization layer + tests

**Next Session – Recommended First Tasks**

1. Add background worker for price checks (no GUI freeze)
2. Add CSV/Excel export option to ResultsTable
3. Wire up column visibility UI + persistence
4. Start adding unit tests around `PriceService` and `PoeNinjaAPI`

---

Sleep brain now, ship brain tomorrow. 🧠💤
When you spin up the new chat, just say “load the latest PoE roadmap” and we can jump straight into the next steps.
