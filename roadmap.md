# PoE Price Checker - Development Roadmap
**Project Vision:** Over-engineered, portfolio-worthy PoE economy tool supporting both PoE1 & PoE2

## 🎯 PROJECT GOALS

### Primary Objectives
1. **Learning Experience:** Deep dive into Python architecture, APIs, databases, plugins
2. **Portfolio Piece:** Demonstrate professional development practices
3. **Practical Tool:** Actually useful for PoE trading and economy analysis
4. **Expandability:** Plugin system for community contributions

### Success Criteria
- [ ] Supports both PoE1 and PoE2 seamlessly
- [ ] 5+ data sources integrated
- [ ] Plugin system with 3+ example plugins
- [ ] Sales tracking with price learning
- [ ] Web API + documentation
- [ ] 80%+ test coverage
- [ ] Clean, documented code reviewable by other LLMs

## 📊 FEATURE BREAKDOWN

### ✅ Phase 1: Foundation & Refactoring (CURRENT)

**Week 1-2: Infrastructure**
- [x] PyCharm setup
- [x] Initial working GUI
- [ ] Git initialization
- [ ] GitHub repository creation
- [ ] Project structure refactoring
- [ ] CONTEXT.md (this file)
- [ ] requirements.txt
- [ ] .gitignore setup

**Week 2-3: Core Architecture**
- [ ] `base_api.py` - Abstract API client with:
  - Rate limiting (exponential backoff)
  - Response caching (TTL-based)
  - Error handling & retries
  - Request logging
  - User-Agent management
- [ ] `database.py` - SQLite wrapper:
  - Connection pooling
  - Migration system
  - Transaction management
  - Query helpers
- [ ] `game_version.py` - PoE1/PoE2 enum
- [ ] `config.py` - Enhanced config with validation
- [ ] `item_parser.py` - Refactored parser with tests

**Week 3-4: Data Sources - Pricing**
- [ ] `poe_ninja.py` - PoE1 pricing (refactor existing)
- [ ] `poe2_scout.py` - PoE2 pricing integration
  - Swagger API client generation
  - Error handling for beta API changes
  - Fallback to manual trade searches
- [ ] `poe_watch.py` - Historical pricing
  - Time-series data storage
  - Trend analysis helpers

**Deliverable:** Working multi-source price checker with database persistence

---

### 🔌 Phase 2: Plugin System (Weeks 5-7)

**Core Plugin Infrastructure**
- [ ] `base_plugin.py` - Plugin interface:
  ```python
  class PluginBase(ABC):
      def initialize(app_context)
      def on_item_checked(item_data)
      def on_price_update(price_data)
      def on_sale_recorded(sale_data)
      def get_config_schema()
      def shutdown()
  ```
- [ ] `plugin_manager.py` - Discovery & lifecycle:
  - Auto-discover plugins in `/plugins` directory
  - Dependency resolution
  - Enable/disable via GUI
  - Config UI generation from schema
  - Sandbox/safety checks
- [ ] Plugin database table for state persistence

**Example Plugins (to demonstrate system)**
1. **Price Alert Plugin**
   - Monitor specific items
   - Webhook to Discord/Telegram when price drops
   - Configurable thresholds
   - Alert history tracking

2. **Export Plugin**
   - Additional export formats (CSV, JSON, Google Sheets)
   - Scheduled exports
   - Cloud backup integration

3. **Statistics Plugin**
   - Dashboard with charts (matplotlib/plotly)
   - Profit/loss tracking
   - Item flip suggestions

**Deliverable:** Plugin system with 3 working plugins, GUI management

---

### 📈 Phase 3: Sales Tracking & Price Learning (Weeks 8-10)

**Sales Recording System**
- [ ] GUI for recording sales:
  - Link checked item → sale record
  - Quick entry form (sold/not sold after 72h)
  - Batch processing
  - Import from clipboard (trade whispers)
- [ ] Automated tracking (future):
  - Parse Client.txt for trade whispers
  - Match whispers to listed items
  - Auto-record completed trades

**Price Learning Algorithm**
- [ ] Statistical analysis:
  - Compare poe.ninja price vs actual sale price
  - Time-to-sale correlation with price
  - Identify underpriced items (sold in <1 hour)
  - Identify overpriced items (no sale in 72h)
- [ ] Machine learning (stretch):
  - Feature extraction: item stats, league age, meta relevance
  - Predict optimal listing price
  - Confidence intervals
  - Model: scikit-learn Random Forest or XGBoost

**Deliverable:** Sales tracking UI, basic price adjustment recommendations

---

### 🎮 Phase 4: Meta Analysis from PoB (Weeks 11-13)

**PoB Parser Integration**
- [ ] Parse PoB links/files:
  - Decode base64 XML
  - Extract required item affixes
  - Identify gear slots with needs
  - Life/ES/Resist thresholds
  - Damage scaling stats (+gem levels, etc.)
- [ ] Meta database:
  - Store popular build requirements
  - Weight affixes by build popularity
  - Track meta shifts over time

**Smart Item Scoring**
- [ ] Affix matching engine:
  - Score items based on meta relevance
  - "This item is 9/10 for RF builds"
  - Highlight undervalued rares
- [ ] Build recommendation:
  - "Good for: Righteous Fire, RF/Scorching Ray"
  - Link to build guides

**Data Sources for Builds**
- [ ] poe.ninja builds endpoint
- [ ] Manual PoB import (user-provided)
- [ ] Scrape popular streamers/content creators (with respect)

**Deliverable:** Meta-aware pricing, rare item evaluation

---

### 🌐 Phase 5: Official Trade API Integration (Weeks 14-16)

**Trade API Client**
- [ ] OAuth 2.1 implementation:
  - Client registration with GGG
  - Authorization flow (web-based)
  - Token refresh handling
  - Scope management
- [ ] Trade search:
  - Query builder UI
  - Advanced filtering (mods, sockets, links)
  - Live search results
  - Price comparison
- [ ] Listing creation (future):
  - Post items to trade site
  - Update prices
  - Delist items

**Use Cases**
- Generate trade URLs for items
- Real-time price comparison
- Arbitrage detection (price differences between sellers)
- Market depth analysis

**Deliverable:** Trade search integration, OAuth setup guide

---
### 🔧 Debugging Task: Chaos Orb Matching / Parsing Issue

Status: Known Issue • Low Priority (workaround active)
Category: Parser Accuracy / Currency Matching
Severity: Low (Chaos Orb always = 1c by definition)
ETA: Phase 4 or Phase 5

🛑 Problem Summary

Chaos Orbs currently fail to match poe.ninja’s "currencyTypeName": "Chaos Orb" entry under certain parsing conditions. This results in:

Missing chaos values in the grid

Correct behavior for all other currencies (Divine, Exalted, Alchemy, Fusing, etc.)

Chaos Orb only appearing correctly due to a temporary hard-coded fallback

This inconsistency indicates a mismatch between the extracted item name/base type and poe.ninja’s currency names, likely due to subtle formatting differences.

💡 Suspected Root Causes

ItemParser may produce slightly inconsistent item.base_type / item.name for Chaos Orbs:

case differences

hidden whitespace

unicode clipboard characters

parse_multiple split behavior may fragment currency blocks in certain edge cases

fuzzy match logic may be too strict or too loose at different stages

normalization inconsistencies ("chaos orb" vs "Chaos Orb" vs "chaos")

✅ Temporary Fix (Implemented)

Chaos Orb is currently handled via a reliable special case:

if key in ("chaos orb", "chaos"):
    return {
        "currencyTypeName": "Chaos Orb",
        "chaosEquivalent": 1.0,
        "chaosValue": 1.0
    }


This is legitimate because Chaos Orb defines the chaos economy (always = 1c).

🎯 Long-Term Fix Plan
1. Add Debug Tracing

Enhance _lookup_price() to print unmatched currency keys:

Record normalized key

Log the first 10 poe.ninja currencyTypeName values

Identify exactly why Chaos fails matching

2. Normalize Item Data Consistently

Implement a shared helper:

normalize(name: str) -> str


That performs:

.lower()

unicode normalization

whitespace collapse

punctuation trimming

Use this everywhere in:

ItemParser

PoeNinjaAPI

Currency matcher

3. Improve Currency Matching Logic

Refactor the matching steps:

Step 1: strict equality

Step 2: trimmed equality

Step 3: normalized equality

Step 4: controlled fuzzy match (word boundary match)

Step 5: fallback to special cases

4. Add Unit Tests

Create explicit tests for:

"Chaos Orb"

"chaos"

Copy-pasted in-game Chaos Orb text

Mixed-case / whitespace variants

Edge cases involving multiple items in clipboard

5. Remove Temporary Hard-Code (Optional)

Once normalization + tests guarantee match correctness, retire the fallback.

📌 Priority Justification

Chaos Orb will continue to work correctly due to the special-case fallback.
Other currencies are unaffected.
Thus, this is a quality-of-implementation fix, not an end-user blocker.

Best addressed after core features are complete (Phase 4–5).

### 🖼️ Phase 6: Computer Vision (Weeks 17-19)

**OCR Item Recognition**
- [ ] Screenshot capture:
  - Hotkey to screenshot stash tab
  - Crop to individual items
  - Grid detection
- [ ] Text extraction:
  - pytesseract for OCR
  - Image preprocessing (contrast, noise reduction)
  - Template matching for icons
- [ ] Bulk processing:
  - Screenshot quad tab → price all 24 items
  - Export to spreadsheet
  - Flag valuable items

**Image Processing Pipeline**
```
Screenshot → Preprocessing → OCR → Parser → Price Lookup → UI Display
```

**Challenges & Solutions**
- Low contrast text: Adaptive thresholding
- Various resolutions: Scale normalization
- Non-English clients: Multi-language OCR models

**Deliverable:** Screenshot-to-price workflow

---

### 🌍 Phase 7: Web Dashboard & API (Weeks 20-23)

**REST API (FastAPI)**
- [ ] Endpoints:
  - `GET /api/items/{id}` - Item details
  - `POST /api/items/check` - Price check
  - `GET /api/sales` - Sales history
  - `GET /api/trends/{item}` - Price trends
  - `POST /api/plugins/{name}/execute` - Trigger plugin
- [ ] Authentication:
  - API key generation
  - Rate limiting per key
  - Usage tracking
- [ ] Documentation:
  - Auto-generated Swagger/OpenAPI
  - Example requests
  - SDKs (Python client)

**Web Frontend (React or Vue)**
- [ ] Dashboard views:
  - Price checker interface
  - Sales tracking
  - Charts & graphs (Chart.js)
  - Plugin management
- [ ] Mobile responsive
- [ ] Real-time updates (WebSocket)

**Deployment Options**
- Docker container
- Heroku/Railway.app (free tier)
- Self-hosted instructions

**Deliverable:** Web app accessible from any device

---

### 📊 Phase 8: Market Trend Analysis (Weeks 24-26)

**Historical Data Collection**
- [ ] Automated price snapshots:
  - Daily price recording for all items
  - League progression tracking
  - Volume indicators
- [ ] Database optimization for time-series:
  - Indexed by date + item
  - Aggregation queries
  - Data retention policy

**Visualization & Insights**
- [ ] Price charts:
  - Line graphs (matplotlib or Plotly)
  - Moving averages
  - Volatility indicators
- [ ] Trend detection:
  - Identify rising/falling items
  - Meta shift correlation
  - League start vs mid-league patterns
- [ ] Flip opportunities:
  - Buy low, sell high suggestions
  - Profit margin calculations
  - Risk assessment

**Export & Sharing**
- [ ] Report generation (PDF)
- [ ] Share charts (PNG/SVG)
- [ ] Public dashboards (read-only API)

**Deliverable:** Economic analysis tools

---

### 🔔 Phase 9: Real-Time Alerts & Webhooks (Weeks 27-28)

**Alert System**
- [ ] Trigger types:
  - Price drop below threshold
  - New item listed matching criteria
  - Meta build becomes popular
  - User-defined custom rules
- [ ] Notification channels:
  - Discord webhook
  - Telegram bot
  - Email (SMTP)
  - Desktop notifications
  - In-app alerts

**Webhook Integration**
- [ ] Outbound webhooks:
  - Custom URL + payload
  - Retry logic
  - Delivery confirmation
- [ ] Inbound webhooks:
  - Accept external triggers
  - Security (HMAC signatures)

**Use Cases**
- Alert me when Exalted Orb < 100c
- Notify when "Shavronne's Wrappings" 6-link listed < 5 div
- Daily summary of sales

**Deliverable:** Multi-channel alert system

---

### 🧪 Phase 10: Testing & Documentation (Weeks 29-30)

**Testing Suite**
- [ ] Unit tests (pytest):
  - All parsers
  - Database operations
  - API clients (with mocks)
  - Plugin system
- [ ] Integration tests:
  - End-to-end workflows
  - Database migrations
  - API endpoints
- [ ] Mock data:
  - Sample items
  - Fake API responses
  - Test database fixtures
- [ ] Coverage reporting:
  - pytest-cov
  - Target: 80%+ coverage

**Documentation**
- [ ] User manual:
  - Installation guide
  - Feature tutorials
  - FAQ
  - Troubleshooting
- [ ] Developer docs:
  - Architecture overview
  - Plugin development guide
  - API reference
  - Contributing guidelines
- [ ] Code documentation:
  - Docstrings (Google style)
  - Type hints throughout
  - Inline comments for complex logic

**Deliverable:** Production-ready with full docs

---

## 🛠️ TECHNICAL STACK

### Core Technologies
- **Language:** Python 3.12+
- **GUI:** Tkinter (initial), Web (later)
- **Database:** SQLite → PostgreSQL (if scaling needed)
- **API Framework:** FastAPI (web API)
- **Testing:** pytest, pytest-cov
- **Version Control:** Git + GitHub

### Key Libraries
```
# Core
requests>=2.31.0
tkinter (built-in)

# Data
openpyxl>=3.1.0
pandas>=2.0.0
sqlalchemy>=2.0.0

# Web (Phase 7)
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0

# ML (Phase 3)
scikit-learn>=1.3.0
xgboost>=2.0.0

# CV (Phase 6)
opencv-python>=4.8.0
pytesseract>=0.3.10
Pillow>=10.0.0

# Visualization
matplotlib>=3.7.0
plotly>=5.17.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0

# Utils
python-dotenv>=1.0.0
pyyaml>=6.0.0
```

### Development Tools
- **IDE:** PyCharm
- **Cloud IDE:** GitHub Codespaces
- **Linting:** ruff or pylint
- **Formatting:** black
- **Type Checking:** mypy
- **Documentation:** Sphinx or MkDocs

---

## 📁 FINAL PROJECT STRUCTURE

```
poe-price-checker/
├── .github/
│   └── workflows/
│       ├── tests.yml              # CI/CD
│       └── deploy.yml
├── docs/
│   ├── user_guide.md
│   ├── developer_guide.md
│   ├── api_reference.md
│   └── plugin_tutorial.md
├── core/
│   ├── __init__.py
│   ├── database.py
│   ├── game_version.py
│   ├── item_parser.py
│   ├── config.py
│   ├── models.py
│   └── exceptions.py
├── data_sources/
│   ├── __init__.py
│   ├── base_api.py
│   ├── official/
│   │   ├── trade_api.py
│   │   ├── character_api.py
│   │   ├── oauth_client.py
│   │   └── public_stash.py
│   ├── pricing/
│   │   ├── poe_ninja.py
│   │   ├── poe2_scout.py
│   │   └── poe_watch.py
│   └── wiki/
│       └── cargo_api.py
├── plugins/
│   ├── __init__.py
│   ├── base_plugin.py
│   ├── plugin_manager.py
│   └── examples/
│       ├── price_alert.py
│       ├── export_plugin.py
│       └── stats_plugin.py
├── gui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── price_checker_tab.py
│   ├── sales_tracker_tab.py
│   ├── plugin_manager_tab.py
│   └── settings_tab.py
├── web/
│   ├── __init__.py
│   ├── api/
│   │   ├── routes/
│   │   ├── models.py
│   │   └── auth.py
│   ├── frontend/
│   │   ├── src/
│   │   ├── public/
│   │   └── package.json
│   └── main.py
├── ml/
│   ├── __init__.py
│   ├── price_predictor.py
│   ├── meta_analyzer.py
│   └── models/                    # Trained models
├── cv/
│   ├── __init__.py
│   ├── screenshot.py
│   ├── ocr_engine.py
│   └── preprocessing.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── conftest.py
├── scripts/
│   ├── migrate_db.py
│   ├── seed_data.py
│   └── benchmark.py
├── .env.example
├── .gitignore
├── CONTEXT.md                     # LLM reference
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── Dockerfile
├── docker-compose.yml
└── LICENSE
```

---

## 🎓 LEARNING OBJECTIVES

### Python Advanced Concepts
- [ ] Abstract Base Classes (ABC)
- [ ] Decorators (caching, rate limiting)
- [ ] Context managers (database connections)
- [ ] Generators (large dataset processing)
- [ ] Type hints & mypy
- [ ] Async/await (web API)
- [ ] Metaclasses (plugin system)

### Software Engineering
- [ ] SOLID principles
- [ ] Design patterns:
  - Adapter (API clients)
  - Factory (plugin creation)
  - Observer (alerts)
  - Strategy (pricing algorithms)
  - Singleton (database connection)
- [ ] Dependency injection
- [ ] Clean architecture

### Data & ML
- [ ] SQL optimization
- [ ] Database indexing
- [ ] Feature engineering
- [ ] Model evaluation
- [ ] Cross-validation
- [ ] Hyperparameter tuning

### DevOps
- [ ] Git workflow (feature branches, PR reviews)
- [ ] CI/CD pipelines
- [ ] Docker containerization
- [ ] Environment management
- [ ] Logging & monitoring

---

## 📅 TIMELINE ESTIMATE

**Total Duration:** ~30 weeks (7-8 months part-time)

**Milestones:**
- **Month 1:** Foundation complete, refactored codebase
- **Month 2:** Plugin system working, 3 example plugins
- **Month 3:** Sales tracking & basic ML
- **Month 4:** Meta analysis, PoB integration
- **Month 5:** Trade API, OAuth setup
- **Month 6:** Computer vision, OCR
- **Month 7:** Web app MVP
- **Month 8:** Polish, testing, documentation

**Flexibility:** Phases can overlap, some features optional

---

## 🏆 PORTFOLIO HIGHLIGHTS

**What Makes This Special:**
1. **Dual-game support** - Unique in ecosystem
2. **Plugin architecture** - Shows extensibility
3. **ML integration** - Price prediction
4. **Full-stack** - Desktop → Web → API
5. **Real-world problem** - Actually useful
6. **LLM collaboration** - Novel development approach
7. **Open source** - Community value

**Talking Points for Interviews:**
- "Built a modular API aggregator with rate limiting and caching"
- "Designed a plugin system using ABC and dynamic imports"
- "Implemented price prediction ML model with 85% accuracy"
- "Created REST API serving 1000+ req/min"
- "Integrated computer vision for automated data entry"

---

## 🚀 GETTING STARTED CHECKLIST

### Today (Session 1)
- [x] Create CONTEXT.md
- [x] Create ROADMAP.md
- [ ] Initialize Git repository
- [ ] Create GitHub repository
- [ ] Push initial code

### Next Session
- [ ] Create feature branch: `feature/refactor-architecture`
- [ ] Build `data_sources/base_api.py`
- [ ] Implement rate limiting
- [ ] Write tests for base_api

### This Week
- [ ] Complete core/ module refactor
- [ ] Database schema implementation
- [ ] First migration
- [ ] Update CONTEXT.md with progress

---

## 📝 NOTES & DECISIONS LOG

### 2025-11-15: Initial Planning
- Chose SQLite over Postgres for simplicity
- Decided on plugin system for extensibility
- Unified PoE1/PoE2 approach confirmed
- Token-optimized CONTEXT.md created
- Roadmap established

### Future Decisions
- [TBD] Web framework: FastAPI vs Flask
- [TBD] Frontend: React vs Vue vs Svelte
- [TBD] ML library: scikit-learn vs PyTorch
- [TBD] Deployment: Self-hosted vs Cloud

---
Phase 1 — GUI Refactor & Polish (Updated 2025-11-16)
✔ Completed

Full GUI refactor into gui/main_window.py

Moved entry point to main.py with clean run_app()

Added:

Paste auto-detect (<<Paste>> → triggers price check automatically)

Better menu system + placeholders for future functionality

Help/Links menu (GGG, PoEDB, Maxroll, etc.)

“Open Log File” & “Open Config Folder” file-ops helpers

Status bar reads active league + window state

Implemented full application logging

Located in: ~/.poe_price_checker/app.log

Rotating logs supported

Colorized console output

Unified logging for GUI, DB, config, and API clients

Added:

About… dialog

Auto-paste → auto-check flow

Tk callback signature cleanup

Ensured tree results support Ctrl+C copy-to-clipboard

Removed unstable dark mode implementation pending full theme system

🧪 Verified Behaviors

Prices validated for various categories (currency, uniques, maps)

Chaos Orb fallback logic functioning

No blocking UI operations

Clean exit → saves window size + closes database safely

Logging works across all modules

🐞 Known Issues / Backlog

Chaos Orb behaviour still quirky when poe.ninja returns odd values
→ Added a fallback constant 1c
→ Will revisit during API validation pass

CPU usage spikes slightly during large paste operations
→ Future: thread off heavy operations

Dark mode needs real ttk-theming (use ttkbootstrap or custom themes)

📘 CONTEXT.md Updates

Add to "Current Immediate Issues" or "Debugging Notes" section:

GUI Polish + Logging (Nov 2025 Update)

Completed full GUI structural refactor

Implemented robust logging system (app.log in the user config directory)

Added user help menus + file-open utilities

Added About dialog

Ensured tree supports copy/paste

Added autopaste → price check callback

Next UI steps:

Migrate long-running price-check calls onto a worker thread
→ prevents GUI freeze

Add unified theme manager (switch light/dark)

Create a Results → “Export to Excel / CSV” menu

Plugin manager UI (enable/disable plugins, plugin list)

Eventually embed PoE icon/branding

Keyboard shortcuts: Ctrl+L (clear), Ctrl+E (export), Ctrl+R (refresh)

🧭 END-OF-SESSION SUMMARY (Paste Into Progress Log)

Date: 2025-11-16
Session: GUI Polish + Logging + Quality of Life

Work Completed

Cleaned up UI including:

Paste detection

Menus

Help links

About dialog

Log and config file open helpers

Implemented complete logging subsystem

Improved price checking logic for currency

Removed broken dark mode

Set up progress markers for next session

Blockers

Chaos Orb logic occasionally bypasses fallback — needs deeper inspection

GUI still synchronous — threading recommended

Dark theme will require dedicated styling library

Next Steps (First Tasks Next Session)

Add background worker threads for price checking

Create Export to Excel / CSV feature

Build Plugin Manager UI

Add “View Recent Checks” window (DB → table popup)

Stabilize currency fallback logic

**For LLM:** This is the master plan. Reference this for feature priorities, technical decisions, and implementation order. Update as we complete phases.
