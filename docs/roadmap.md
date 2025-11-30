---
title: Development Roadmap
status: current
stability: volatile
last_reviewed: 2025-11-28
review_frequency: monthly
---

# PoE Price Checker – Development Roadmap

**Project Vision:** The ultimate PoE character item management tool - an over-engineered, portfolio-worthy economy analysis platform supporting PoE1 & PoE2 with desktop and web interfaces.

---

## Current State (v1.3.1)

**Completed Features:**
- Multi-source pricing (poe.ninja, poe.watch, Trade API)
- PyQt6 GUI with item inspector, stash scanner, sales tracking
- PoB integration with build decoding and stat analysis
- BiS search system with affix tier calculations
- OAuth stash tab scanning
- MCP integration for AI assistants
- Session tabs for multiple price-checking sessions
- 1226 tests passing, ~60% coverage
- Security hardening (encrypted tokens, CSRF protection)

---

## Phase A: UX/UI Enhancements (Next Priority)

### A.1 Visual Polish & Theming
- [x] **Dark/Light theme toggle** with system preference detection ✅
- [x] **Accent color customization** (match PoE currency colors) ✅
- [ ] **Compact mode** for smaller screens / overlay use
- [ ] **Font scaling** for accessibility
- [ ] **High-DPI support** improvements

### A.2 Results Table Improvements
- [x] **Inline item preview** - hover shows item tooltip with mods ✅
- [x] **Profit column** - show margin vs purchase price ✅
- [x] **Trend indicators** - up/down arrows for price movement ✅
- [x] **Bulk selection** - multi-select for batch operations ✅
- [x] **Custom column ordering** - drag-and-drop with persistence ✅
- [ ] **Saved column presets** - "Currency mode", "Gear mode", "Crafting mode"

### A.3 Item Inspector Enhancements
- [x] **Side-by-side comparison** - compare 2-3 items simultaneously ✅
- [x] **DPS/EHP calculator** - show theoretical impact on build ✅
- [x] **Mod tier highlighting** - color-code T1/T2/T3+ affixes ✅
- [ ] **Craft potential indicator** - "can become X with Y craft"
- [ ] **Similar items search** - one-click Trade search for comparable

### A.4 Navigation & Workflow
- [x] **Keyboard shortcuts** - configurable hotkeys for all actions ✅
- [x] **Command palette** (Ctrl+K) - quick access to any feature ✅
- [x] **Recent items history** - quick re-check previous items ✅
- [x] **Pinned items** - keep important items visible ✅
- [x] **Session tabs** - multiple price-checking sessions ✅

### A.5 Stash Visualization
- [x] **Stash grid preview** - visual representation of tab contents ✅
- [x] **Heatmap overlay** - color by value (red=high, blue=low) ✅
- [x] **Quick-filter** - show only items matching criteria ✅
- [ ] **Tab comparison** - diff between snapshots over time

### A.6 Notifications & Feedback
- [x] **Toast notifications** - non-blocking status updates ✅
- [ ] **Sound alerts** - configurable audio for price thresholds
- [ ] **System tray** - minimize to tray with price alerts
- [ ] **Progress indicators** - better feedback for long operations

---

## Phase B: Intelligence & Analytics

### B.1 Price Intelligence
- [ ] **Price trend analysis** - 24h/7d/30d trend graphs
- [ ] **Volatility warnings** - flag items with unstable prices
- [ ] **Confidence scoring** - weighted average across sources
- [ ] **Outlier detection** - identify price manipulation
- [ ] **Historical price lookup** - "what was X worth last league?"

### B.2 Build-Aware Recommendations
- [x] **Upgrade finder** - "best upgrades for your build under X budget" ✅
- [ ] **Stat gap analysis** - "you need 30 more cold res, here are options"
- [ ] **DPS optimization** - "swap X for Y = +15% DPS for 50c"
- [ ] **Build archetype detection** - auto-classify from PoB
- [ ] **Meta awareness** - weight stats by current meta popularity

### B.3 Crafting Intelligence
- [ ] **Craft profit calculator** - expected value of crafting operations
- [ ] **Recombinator simulator** - model outcomes with probabilities
- [ ] **Essence/Fossil recommendations** - "best method to hit X mod"
- [ ] **Awakener orb planner** - predict influence mod combinations
- [ ] **Harvest craft tracker** - log available crafts, suggest uses

### B.4 Market Analysis
- [ ] **Snipe detection** - alert when items listed below market
- [ ] **Flip finder** - identify arbitrage opportunities
- [ ] **League economy tracker** - currency ratios over time
- [ ] **Demand prediction** - anticipate price changes from patch notes
- [ ] **Build popularity correlation** - link item prices to build trends

### B.5 Personal Analytics
- [ ] **Profit/loss tracking** - running total of trading gains
- [ ] **Time-value analysis** - chaos per hour from different activities
- [ ] **Portfolio value** - total wealth across all tabs
- [ ] **Achievement tracking** - "first 100 div", "most profitable flip"

---

## Phase C: Character & Build Management

### C.1 Character Dashboard
- [ ] **Multi-character overview** - all characters at a glance
- [ ] **Gear score** - aggregate item quality metric
- [ ] **Resistance summary** - instant res overcap view
- [ ] **Attribute requirements** - highlight unmet requirements
- [ ] **Socket/link status** - visual gem setup display

### C.2 Gear Progression Planning
- [ ] **Upgrade roadmap** - prioritized gear improvements
- [ ] **Budget planner** - "reach T16 maps for under 1 div"
- [ ] **Leveling gear presets** - saved gear sets for alts
- [ ] **Goal tracking** - "save for Headhunter: 45/120 div"

### C.3 Build Library
- [x] **Build profiles** - save/load complete character setups ✅
- [ ] **Build comparison** - diff two builds side-by-side
- [x] **Build sharing** - export/import build configurations ✅
- [x] **Guide integration** - link builds to Maxroll/poe.ninja guides ✅
- [x] **SSF mode** - filter recommendations for self-found ✅

### C.4 Passive Tree Integration
- [ ] **Tree visualization** - display allocated passives
- [ ] **Cluster jewel planner** - optimize notable placement
- [ ] **Respec cost calculator** - plan passive changes
- [ ] **Mastery optimizer** - suggest best mastery choices

---

## Phase D: Web Implementation

### D.1 Architecture
- [ ] **FastAPI backend** - RESTful API with OpenAPI docs
- [ ] **WebSocket support** - real-time price updates
- [ ] **React/Vue frontend** - modern SPA with responsive design
- [ ] **PostgreSQL** - production database with proper scaling
- [ ] **Redis caching** - fast price lookups

### D.2 Core Web Features
- [ ] **User authentication** - OAuth with PoE account linking
- [ ] **Cloud sync** - preferences, builds, history across devices
- [ ] **Public API** - documented endpoints for third-party tools
- [ ] **Rate limiting** - protect against abuse
- [ ] **Webhook integrations** - Discord, Telegram notifications

### D.3 Web-Specific UI
- [ ] **Mobile-responsive design** - usable on phones/tablets
- [ ] **PWA support** - installable web app
- [ ] **Offline mode** - cached data for basic functionality
- [ ] **Browser extension** - quick price lookup on any page
- [ ] **Overlay mode** - transparent overlay for in-game use

### D.4 Social Features
- [ ] **Price alerts sharing** - community-curated alert configs
- [ ] **Build showcase** - public build profiles with gear
- [ ] **Trade reputation** - optional trader ratings
- [ ] **Guild features** - shared wishlists, group analytics
- [ ] **Leaderboards** - wealth tracking (opt-in)

---

## Phase E: Advanced Integrations

### E.1 External Tool Integration
- [ ] **Path of Building sync** - two-way build updates
- [ ] **Awakened PoE Trade** - complement, not replace
- [ ] **Exilence Next** - portfolio data sharing
- [ ] **Craft of Exile** - link craft simulations
- [ ] **PoE Overlay** - hotkey coordination

### E.2 Data Source Expansion
- [ ] **Official Trade API v2** - full listing support
- [ ] **TFT bulk pricing** - mirror tier item values
- [ ] **poe.ninja build data** - skill gem popularity
- [ ] **PoE-Racing** - league start economy patterns
- [ ] **Reddit sentiment** - gauge community reactions

### E.3 Automation (Ethical)
- [ ] **Auto-pricing suggestions** - "price this stack at X"
- [ ] **Bulk listing helper** - batch create forum posts
- [ ] **Inventory snapshots** - scheduled stash scans
- [ ] **Watchlist alerts** - notify when items appear
- [ ] **Smart filters** - learn from your pricing patterns

---

## Phase F: Machine Learning & AI

### F.1 Price Prediction
- [ ] **ML price model** - predict rare item values
- [ ] **Affix value weights** - learned from market data
- [ ] **Roll quality scoring** - tier + roll% = value
- [ ] **Seasonal adjustments** - league lifecycle patterns

### F.2 Natural Language
- [ ] **Chat interface** - "find me a 500 pdps axe under 1 div"
- [ ] **Voice commands** - "check this item" via microphone
- [ ] **Item description generation** - auto-create trade listings
- [ ] **Query translation** - natural language to Trade API filters

### F.3 Computer Vision
- [ ] **Screenshot parsing** - paste image, get item data
- [ ] **In-game overlay OCR** - read items without clipboard
- [ ] **Stash tab OCR** - visual inventory without API

---

## Implementation Priority

### Immediate (Next 2-4 weeks) - ✅ COMPLETED
1. ~~**Dark/Light theme toggle**~~ - ✅ `gui_qt/styles.py`, Ctrl+T
2. ~~**Keyboard shortcuts**~~ - ✅ `gui_qt/shortcuts.py`, F1/Ctrl+K
3. ~~**Price trend indicators**~~ - ✅ `core/price_trend_calculator.py`, 7d Trend column
4. ~~**Side-by-side item comparison**~~ - ✅ `gui_qt/dialogs/item_comparison_dialog.py`, Ctrl+Shift+I
5. ~~**DPS impact calculator**~~ - ✅ `core/dps_impact_calculator.py`, Item Inspector

### Short-term (1-2 months)
1. ~~**Upgrade finder**~~ - ✅ `core/upgrade_finder.py`, Ctrl+U
2. ~~**Stash grid visualization**~~ - ✅ `gui_qt/widgets/stash_grid_visualizer.py`, Grid View in Stash Viewer
3. ~~**Build profiles/library**~~ - ✅ `gui_qt/dialogs/build_library_dialog.py`, Ctrl+Alt+B
4. **FastAPI backend skeleton** - web foundation

### Medium-term (3-6 months)
1. **Full web implementation** - React frontend
2. **ML price prediction** - rare item valuation
3. **Craft profit calculator** - crafting intelligence
4. **Mobile-responsive web** - cross-platform access

### Long-term (6-12 months)
1. **Browser extension** - ubiquitous access
2. **Guild features** - social layer
3. **Voice/chat interface** - AI interaction
4. **Computer vision** - image-based lookup

---

## Tech Stack Evolution

### Current (Desktop)
- Python 3.12, PyQt6, SQLite
- pytest, requests, beautifulsoup4

### Web Addition
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery
- **Frontend:** React/Vue 3, TypeScript, TailwindCSS
- **Infrastructure:** Docker, nginx, GitHub Actions
- **Monitoring:** Prometheus, Grafana, Sentry

---

## Success Metrics

### User Experience
- [ ] < 100ms item lookup response time
- [ ] < 3 clicks to any feature
- [ ] 90%+ user satisfaction on core workflows

### Technical
- [ ] 80%+ test coverage
- [ ] < 1% error rate on API calls
- [ ] 99.9% uptime for web service

### Adoption
- [ ] 1000+ desktop downloads
- [ ] 500+ registered web users
- [ ] 10+ community plugin contributions

---

## What Makes This "Ultimate"

1. **Unified Experience** - Desktop, web, mobile, overlay all sync
2. **Build-Aware** - Every feature considers your character's needs
3. **Intelligence Layer** - Not just data, but actionable insights
4. **Community-Powered** - Plugins, shared configs, guild features
5. **Future-Proof** - ML models that improve with more data
6. **Professional Quality** - Production-grade code, documentation, tests

---

*Last updated: 2025-11-29*
*Next review: 2025-12-29*
