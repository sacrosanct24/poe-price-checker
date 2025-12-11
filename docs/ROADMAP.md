---
title: Feature Roadmap
status: current
stability: living
last_reviewed: 2025-12-09
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
- [ ] Increase test coverage to 80% (currently ~60%)

### Large File Refactoring

**Target:** Split files >500 lines into focused modules for better maintainability and testability.

#### Phase 1: Low-Risk, High-Impact (Recommended First)

| File | Lines | Proposed Split | Effort |
|------|-------|----------------|--------|
| `gui_qt/styles.py` | 1,317 | `gui_qt/themes/` package (colors, palettes, manager) | 1 day |
| `core/price_rankings.py` | 1,324 | `core/rankings/` package (models, cache, calculator, history) | 1 day |
| `gui_qt/windows/stash_viewer_window.py` | 1,136 | `gui_qt/windows/stash/` (worker, model, dialog, window) | 0.5 day |

#### Phase 2: Medium Complexity

| File | Lines | Proposed Split | Effort |
|------|-------|----------------|--------|
| `core/pob_integration.py` | 1,370 | `core/pob/` package (models, decoder, manager, checker) | 1.5 days |
| `core/league_economy_history.py` | 1,246 | `core/economy/` package (models, importer, services) | 1 day |
| `core/config.py` | 1,179 | `core/config/` package (defaults, config class) | 0.5 day |

#### Phase 3: Core Infrastructure (High Risk)

| File | Lines | Proposed Split | Effort |
|------|-------|----------------|--------|
| `core/database.py` | 2,519 | `core/database/` with repository pattern | 2.5 days |
| `core/price_service.py` | 1,336 | `core/pricing/` package (models, converters, lookups) | 2 days |

#### Phase 4: Complex Evaluation

| File | Lines | Proposed Split | Effort |
|------|-------|----------------|--------|
| `core/rare_item_evaluator.py` | 1,358 | `core/rare_evaluation/` package (matcher, synergy, rules) | 2 days |
| `gui_qt/main_window.py` | 1,817 | Extract remaining controllers (session, menu, settings) | 1.5 days |

#### Refactoring Guidelines

1. **Create package with `__init__.py`** - Re-export for backward compatibility
2. **Extract bottom-up** - Start with dataclasses, then utilities, then main classes
3. **Test at each step** - Run full test suite after each extraction
4. **Target:** No file exceeds 500 lines

See `docs/development/LARGE_FILE_REFACTORING.md` for detailed implementation plans.

### Performance
- [ ] Lazy loading for large stash tabs
- [ ] Background price refresh
- [ ] Caching optimization for repeated items

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

*Last updated: 2025-12-09*
