---
title: Large File Refactoring Plan
status: planned
stability: living
last_reviewed: 2025-12-10
---

# Large File Refactoring Plan

Detailed implementation plans for splitting large files (>500 lines) into focused, maintainable modules.

**Total Lines to Refactor:** ~14,600 lines across 10 files

---

## Executive Summary

| Phase | Files | Total Lines | Effort | Risk |
|-------|-------|-------------|--------|------|
| 1 | styles, price_rankings, stash_viewer | 3,777 | 2.5 days | Low |
| 2 | pob_integration, league_economy, config | 3,795 | 3 days | Medium |
| 3 | database, price_service | 3,855 | 4.5 days | High |
| 4 | rare_evaluator, main_window | 3,175 | 3.5 days | Medium |

---

## Phase 1: Low-Risk, High-Impact

### 1.1 gui_qt/styles.py (1,317 lines)

**Current Structure:**
- Theme enum and display names
- 20+ color constant dictionaries
- ThemeManager singleton class
- Icon/stylesheet helper functions

**Proposed Structure:**
```
gui_qt/themes/
  __init__.py              # Re-exports (COLORS, get_theme_manager, etc.)
  theme_enum.py            # Theme enum, display names (~100 lines)
  colors/
    __init__.py            # Re-exports all color dicts
    rarity.py              # RARITY_COLORS, RARITY_COLORS_COLORBLIND
    value.py               # VALUE_COLORS, VALUE_COLORS_COLORBLIND
    status.py              # STATUS_COLORS, STAT_COLORS
    currency.py            # POE_CURRENCY_COLORS
    tiers.py               # TIER_COLORS
  palettes/
    __init__.py
    dark.py                # DARK_THEME dict
    light.py               # LIGHT_THEME dict
    high_contrast.py       # High contrast themes
    popular.py             # Dracula, Nord, Solarized, etc.
    colorblind.py          # Colorblind-friendly themes
  theme_manager.py         # ThemeManager class (~400 lines)
  icons.py                 # Icon/pixmap generation functions
  stylesheet_generator.py  # Stylesheet generation
```

**Backward Compatibility:**
```python
# gui_qt/styles.py (kept for compatibility)
from gui_qt.themes import *  # noqa: F401,F403
```

**Dependencies to Update:** ~50 files import from `gui_qt.styles`

---

### 1.2 core/price_rankings.py (1,324 lines)

**Current Structure:**
- `RankedItem`, `CategoryRanking` dataclasses
- `PriceRankingCache` for file-based caching
- `Top20Calculator` for ranking computation
- `PriceRankingHistory` for SQLite storage

**Proposed Structure:**
```
core/rankings/
  __init__.py              # Re-exports
  models.py                # RankedItem, CategoryRanking (~100 lines)
  constants.py             # CATEGORY_MAPPINGS, SLOT_CONFIGS (~200 lines)
  cache.py                 # PriceRankingCache (~200 lines)
  calculator.py            # Top20Calculator (~500 lines)
  history.py               # PriceRankingHistory (~300 lines)
```

**Dependencies to Update:**
- `gui_qt/widgets/price_rankings_panel.py`
- `gui_qt/workers/rankings_worker.py`

---

### 1.3 gui_qt/windows/stash_viewer_window.py (1,136 lines)

**Current Structure:**
- `FetchWorker` QThread
- `ItemTableModel` for item display
- `StashItemDetailsDialog`
- `StashViewerWindow` main widget

**Proposed Structure:**
```
gui_qt/windows/stash/
  __init__.py                    # Re-exports StashViewerWindow
  fetch_worker.py                # FetchWorker QThread (~80 lines)
  item_table_model.py            # ItemTableModel (~250 lines)
  item_details_dialog.py         # StashItemDetailsDialog (~120 lines)
  stash_viewer_window.py         # Main window (~700 lines)
```

**Dependencies to Update:**
- `gui_qt/controllers/navigation_controller.py`
- `gui_qt/screens/daytrader_screen.py`

---

## Phase 2: Medium Complexity

### 2.1 core/pob_integration.py (1,370 lines)

**Current Structure:**
- Data classes: `PoBItem`, `PoBBuild`, `CharacterProfile`
- `PoBDecoder` for parsing PoB codes
- `CharacterManager` for profile persistence
- `UpgradeChecker` for item comparison

**Proposed Structure:**
```
core/pob/
  __init__.py              # Re-exports for compatibility
  models.py                # PoBItem, PoBBuild, CharacterProfile (~200 lines)
  decoder.py               # PoBDecoder class (~400 lines)
  character_manager.py     # CharacterManager (~400 lines)
  upgrade_checker.py       # UpgradeChecker (~400 lines)
```

**Dependencies to Update:**
- `core/app_context.py`
- `gui_qt/controllers/pob_controller.py`
- `gui_qt/windows/pob_character_window.py`

---

### 2.2 core/league_economy_history.py (1,246 lines)

**Current Structure:**
- Data models: `CurrencySnapshot`, `UniqueSnapshot`, `LeagueEconomySnapshot`
- `LeagueEconomyService` with CSV import, queries, aggregation

**Proposed Structure:**
```
core/economy/
  __init__.py              # Re-exports
  models.py                # Snapshot dataclasses (~100 lines)
  csv_importer.py          # CSV import methods (~350 lines)
  snapshot_service.py      # Milestone snapshot CRUD (~200 lines)
  query_service.py         # Currency/item queries (~200 lines)
  aggregation_service.py   # Pre-aggregation methods (~400 lines)
```

**Dependencies to Update:**
- `core/database.py`
- `gui_qt/main_window.py`

---

### 2.3 core/config.py (1,179 lines)

**Current Structure:**
- `Config` class with DEFAULT_CONFIG dict
- Many property accessors for different settings categories

**Proposed Structure:**
```
core/config/
  __init__.py              # Re-exports Config
  defaults.py              # DEFAULT_CONFIG dict (~180 lines)
  config.py                # Config class (~800 lines)
```

**Note:** Conservative split recommended due to high coupling. Config is cohesive as a single class; only extract the large DEFAULT_CONFIG dict.

**Dependencies to Update:** Many modules import `Config`

---

## Phase 3: Core Infrastructure (High Risk)

### 3.1 core/database.py (2,519 lines) - HIGHEST PRIORITY

**Current Structure:**
- Single `Database` class with 11 schema versions
- 90+ methods across distinct domains

**Logical Groupings:**
1. Schema Management (lines 140-920)
2. Checked Items (lines 960-1010)
3. Sales Management (lines 1015-1190)
4. Price History & Checks (lines 1195-1490)
5. Plugin State (lines 1490-1540)
6. Statistics/Summaries (lines 1540-1750)
7. Currency Rates (lines 1750-1845)
8. Upgrade Advice Cache (lines 1890-2270)
9. Verdict Statistics (lines 2275-2505)

**Proposed Structure:**
```
core/database/
  __init__.py              # Re-exports Database class
  base.py                  # DatabaseConnection, lock, base execute
  schema.py                # Schema creation and migrations (~500 lines)
  repositories/
    __init__.py
    base_repository.py     # Base class with common patterns
    checked_items.py       # CheckedItemsRepository (~50 lines)
    sales.py               # SalesRepository (~200 lines)
    price_history.py       # PriceHistoryRepository (~300 lines)
    plugin_state.py        # PluginStateRepository (~50 lines)
    currency_rates.py      # CurrencyRatesRepository (~100 lines)
    upgrade_advice.py      # UpgradeAdviceRepository (~300 lines)
    verdict_stats.py       # VerdictStatisticsRepository (~200 lines)
```

**Migration Pattern:**
```python
# core/database/base.py
class Database:
    """Facade providing backward compatibility."""

    def __init__(self, db_path=None):
        self._conn = DatabaseConnection(db_path)
        self._checked_items = CheckedItemsRepository(self._conn)
        self._sales = SalesRepository(self._conn)
        # ...

    # Delegate to repositories
    def add_checked_item(self, *args, **kwargs):
        return self._checked_items.add(*args, **kwargs)

    def get_recent_sales(self, *args, **kwargs):
        return self._sales.get_recent(*args, **kwargs)
```

**Benefits:**
- Each repository can be unit tested independently
- Clear separation of concerns
- Easier to mock in tests

**Dependencies to Update:**
- `core/app_context.py`
- `core/league_economy_history.py`
- `gui_qt/windows/*.py`
- ~30 test files

---

### 3.2 core/price_service.py (1,336 lines)

**Current Structure:**
- `PriceExplanation` dataclass
- `PriceService` class handling all price lookups

**Proposed Structure:**
```
core/pricing/
  __init__.py              # Re-exports PriceService
  models.py                # PriceExplanation (~100 lines)
  currency_converter.py    # Currency rate handling (~100 lines)
  quote_storage.py         # Trade quote database operations (~200 lines)
  display_formatter.py     # Display price computation (~150 lines)
  multi_source_lookup.py   # Multi-source aggregation (~300 lines)
  ninja_lookup.py          # poe.ninja specific logic (~200 lines)
  service.py               # Main PriceService orchestrator (~350 lines)
```

**Dependencies to Update:**
- `core/app_context.py`
- `gui_qt/controllers/price_check_controller.py`

---

## Phase 4: Complex Evaluation

### 4.1 core/rare_item_evaluator.py (1,358 lines)

**Current Structure:**
- Single `RareItemEvaluator` class

**Proposed Structure:**
```
core/rare_evaluation/
  __init__.py              # Re-exports RareItemEvaluator
  models.py                # AffixMatch, RareItemEvaluation (~100 lines)
  data_loader.py           # Config/weights loading (~150 lines)
  pattern_matcher.py       # Regex compilation and matching (~200 lines)
  affix_evaluator.py       # Affix matching logic (~250 lines)
  synergy_checker.py       # Synergy/red flag detection (~150 lines)
  slot_rules.py            # Slot-specific evaluation (~150 lines)
  evaluator.py             # Main orchestrator (~400 lines)
```

**Dependencies to Update:**
- `core/price_service.py`
- `core/stash_valuator.py`
- `gui_qt/widgets/rare_evaluation_panel.py`

---

### 4.2 gui_qt/main_window.py (1,817 lines)

**Current Structure:**
- Already uses controller pattern
- Some responsibilities remain in main class

**Remaining Extractions:**
```
gui_qt/controllers/
  session_controller.py      # Session tab management (~150 lines)
  menu_controller.py         # Menu creation (~150 lines)
  settings_controller.py     # Settings dialog logic (~100 lines)
```

**Note:** main_window.py has already had significant controller extraction. The remaining code is mostly glue/orchestration which is appropriate for a main window class.

---

## Migration Strategy

### For Each File:

1. **Create Package Structure**
   ```bash
   mkdir -p core/database/repositories
   touch core/database/__init__.py
   touch core/database/repositories/__init__.py
   ```

2. **Extract Bottom-Up**
   - Start with data models/dataclasses
   - Then utilities/helpers
   - Then main classes

3. **Maintain Backward Compatibility**
   ```python
   # Original file becomes thin wrapper
   from core.database import Database  # noqa: F401
   ```

4. **Test at Each Step**
   ```bash
   # After each extraction
   pytest tests/unit/core/test_database.py -v
   pytest tests/ -x -q  # Full suite
   ```

5. **Update Imports Incrementally**
   - Use IDE refactoring tools
   - Search for `from core.database import`

---

## Success Metrics

| Metric | Target |
|--------|--------|
| File Size | No file exceeds 500 lines |
| Test Coverage | Maintain or improve (~60%) |
| Import Depth | Maximum 3 levels |
| Circular Dependencies | Zero |
| mypy Errors | Zero |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking tests | Run full suite after each extraction |
| Import cycles | Use TYPE_CHECKING, lazy loading |
| Performance regression | Profile critical paths |
| Incomplete migration | Maintain re-exports until updated |
| Merge conflicts | Dedicated feature branches |

---

## Git Branch Strategy

```
main
  └── refactor/large-files
        ├── refactor/styles-modularization
        ├── refactor/price-rankings-split
        ├── refactor/stash-viewer-split
        ├── refactor/pob-integration-split
        ├── refactor/database-repositories
        └── ... (one branch per major file)
```

---

*Last updated: 2025-12-10*
