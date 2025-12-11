---
title: Feature Roadmap
status: current
stability: living
last_reviewed: 2025-12-10
review_frequency: monthly
---

# PoE Price Checker - Feature Roadmap

**Single source of truth for planned features and enhancements.**

---

## Recently Completed (v1.6.x)

### Quick Verdict System
- [x] **Quick Verdict Calculator** - Simple keep/vendor/maybe verdicts for casual players
- [x] **Meta Integration** - Verdicts boosted by current meta build popularity
- [x] **Stash Viewer Verdicts** - Quick verdicts in stash tab viewer
- [x] **Verdict/Eval Tier Alignment** - Consistent ratings across systems
- [x] **Settings UI for Thresholds** - League timing presets (start/mid/late/SSF)
- [x] **Session Statistics Widget** - Track keep/vendor/maybe counts per session
- [x] **Database Persistence** - Stats saved across app restarts (per league/day)

---

## Planned Features

### High Priority

#### Price History & Trends
- [ ] **Price History Charts** - Visualize item price trends over time
  - Line chart showing price changes
  - Compare prices across leagues
  - Integration with poe.ninja historical data

#### Export & Reporting
- [ ] **Export Results** - Save price check results to CSV/JSON
  - Session export with all checked items
  - Filtered export by verdict type
  - Include item details and prices

### Medium Priority

#### Batch Operations
- [ ] **Batch Price Checking** - Check multiple items from a list
  - Paste multiple items at once
  - Queue system for rate limiting
  - Progress indicator and summary

#### Notifications
- [ ] **Sound Notifications** - Audio alerts for specific conditions
  - High-value item sound
  - Custom sound per verdict type
  - Volume control in settings

- [ ] **Price Alerts** - Notifications when items match criteria
  - Set price thresholds for alerts
  - System tray notifications
  - Optional desktop notifications

### Lower Priority

#### Analytics
- [ ] **Verdict Analytics Dashboard** - Historical stats visualization
  - Charts showing verdict distribution over time
  - Value trends per league
  - Meta bonus effectiveness metrics

#### UX Improvements
- [ ] **Quick Actions** - One-click common operations
  - Copy price to clipboard
  - Open on trade site
  - Add to watchlist

- [ ] **Keyboard Navigation** - Full keyboard-only workflow
  - Navigate results with arrow keys
  - Quick verdict override shortcuts

---

## Technical Debt & Improvements

### Code Quality
- [x] Complete type hints across all modules (mypy: 0 errors)
- [x] Reduce `type: ignore` comments (28 → 20)
- [x] ~~Increase test coverage to 80%~~ **Currently at 72%** (up from ~60%)

### Large File Refactoring ✅ COMPLETED

**All 4 phases completed.** Files have been split into focused packages.

#### Phase 1: Low-Risk, High-Impact ✅

| File | Status | Result |
|------|--------|--------|
| `gui_qt/styles.py` | ✅ Done | `gui_qt/themes/` package |
| `core/price_rankings.py` | ✅ Done | `core/rankings/` package |
| `gui_qt/windows/stash_viewer_window.py` | ✅ Done | `gui_qt/stash_viewer/` package |

#### Phase 2: Medium Complexity ✅

| File | Status | Result |
|------|--------|--------|
| `core/pob_integration.py` | ✅ Done | `core/pob/` package |
| `core/league_economy_history.py` | ✅ Done | `core/economy/` package |
| `core/config.py` | ✅ Done | `core/config/` package |

#### Phase 3: Core Infrastructure ✅

| File | Status | Result |
|------|--------|--------|
| `core/database.py` | ✅ Done | `core/database/` package |
| `core/price_service.py` | ✅ Done | `core/pricing/` package |

#### Phase 4: Complex Evaluation ✅

| File | Status | Result |
|------|--------|--------|
| `core/rare_item_evaluator.py` | ✅ Done | `core/rare_evaluation/` package |
| `gui_qt/main_window.py` | ✅ Done | Extracted `UpgradeAnalysisController` |

#### Remaining Large Files (Future Work)

| File | Lines | Notes |
|------|-------|-------|
| `core/database/base.py` | 1,939 | Could benefit from repository pattern |
| `gui_qt/main_window.py` | 1,665 | More controller extraction possible |
| `core/pricing/service.py` | 1,315 | Functional, may split further |
| `core/rare_evaluation/evaluator.py` | 1,288 | Functional, low priority |
| `core/economy/service.py` | 1,192 | Functional, low priority |

### Performance ✅ COMPLETED

- [x] **Lazy loading for large stash tabs** - Incremental batch processing with `items_batch` signal
- [x] **Background price refresh** - `PriceRefreshService` with configurable intervals
- [x] **Item price caching** - LRU `ItemPriceCache` with TTL expiration (5 min default)

---

## Feature Requests

*Track community requests here. Move to "Planned" when accepted.*

None currently tracked.

---

## Versioning

| Version | Focus | Status |
|---------|-------|--------|
| 1.6.x | Quick Verdict System | Completed |
| 1.7.x | Price History & Export | Planned |
| 1.8.x | Batch Operations | Planned |
| 2.0.x | Major UX Overhaul | Future |

---

## Contributing

To propose a feature:
1. Check this roadmap first to avoid duplicates
2. Open a GitHub issue with `[Feature Request]` prefix
3. Include use case and expected behavior
4. Features are prioritized based on user impact and complexity

---

*Last updated: 2025-12-10*
