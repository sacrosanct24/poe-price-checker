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
- [ ] Increase test coverage to 80% (currently ~60%)
- [ ] Complete type hints across all modules
- [ ] Split large files (`main_window.py`, `item_parser.py`)

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
