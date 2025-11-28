---
title: LLM Context Document
status: current
stability: volatile
last_reviewed: 2025-11-28
review_frequency: monthly
---

# PoE Price Checker - LLM Context Document
**Version:** 2.5 Enhanced | **Last Updated:** 2025-11-28 | **Python:** 3.12

## CRITICAL GOTCHAS & LESSONS LEARNED

### Rate Limiting (MOST IMPORTANT)
**GGG Official API Rate Limits:**
- Dynamic limits via headers: `X-Rate-Limit-Client`, `X-Rate-Limit-Ip-State`
- Format: `max:window:penalty` e.g., `10:5:10` = 10 req per 5 sec, 10 sec penalty
- 429 = Too Many Requests → MUST parse `Retry-After` header
- **4xx errors COUNT against rate limit** - avoid invalid requests
- Trade API: ~4 req/sec general, ~1 req/sec for stash tabs
- Public stash stream: 5-minute delay on data

**poe.ninja:**
- Unofficial, no documented limits
- Community standard: ~1 request per 3 seconds
- Cache aggressively (data updates hourly)

**poe2scout:**
- Open API, include User-Agent header with email
- High usage? Contact maintainer for custom endpoints

**Implementation Pattern:**
```python
# MUST implement exponential backoff
def request_with_backoff(url, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(url)
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
            time.sleep(retry_after)
            continue
        return response
```

### API-Specific Issues

**Official Trade API:**
- CORS blocking for browser-based apps → need backend proxy
- League names are case-sensitive: "Standard" not "standard"
- Search returns IDs → separate fetch call needed for actual item data
- Maintenance windows (patch days) → handle connection failures gracefully

**poe.ninja:**
- No PoE2 price data yet (as of Nov 2025), use poe2scout instead
- Old leagues removed from API without notice
- `chaosValue` can be 0 for untradeable items
- PoE1 divine/chaos conversion: fetch Divine Orb price first

**Character API:**
- Requires `POESESSID` cookie OR OAuth token
- Privacy settings can hide characters
- Max 10 characters returned per call

### Data Parsing

**Item Text Format:**
- Multiple separators (`--------`) group sections
- Stack size format: `Stack Size: 15/40` (current/max)
- Influences can be combined (e.g., Shaper + Elder)
- Fractured/Synthesised items need special handling
- Quality on gems vs armor vs weapons - different meanings

**PoB (Path of Building):**
- XML format with base64-encoded build data
- Must decode → parse XML → extract gear requirements
- Life/ES/Resist requirements most relevant for pricing

## PROJECT ARCHITECTURE

### File Structure
```
exilePriceCheck/
├── CONTEXT.md                    # This file - LLM reference
├── README.md                     # Human documentation (end of project)
├── requirements.txt              # Dependencies
├── .gitignore                    # Git exclusions
├── poe_price_checker.py          # Legacy (will refactor)
├── core/
│   ├── __init__.py
│   ├── database.py               # SQLite layer + ORM
│   ├── game_version.py           # POE1/POE2 enum
│   ├── item_parser.py            # Parse item text
│   ├── config.py                 # Persistent config
│   └── models.py                 # DB models
├── data_sources/
│   ├── __init__.py
│   ├── base_api.py               # Abstract base (rate limiting, caching)
│   ├── official/
│   │   ├── trade_api.py          # pathofexile.com/api/trade
│   │   ├── character_api.py      # character-window endpoints
│   │   ├── oauth_client.py       # OAuth 2.1 (future)
│   │   └── public_stash.py       # Stash stream (future)
│   ├── pricing/
│   │   ├── poe_ninja.py          # PoE1 pricing
│   │   ├── poe2_scout.py         # PoE2 pricing
│   │   └── poe_watch.py          # Historical (future)
│   └── wiki/
│       └── cargo_api.py          # Item database (future)
├── plugins/
│   ├── __init__.py
│   ├── base_plugin.py            # Plugin interface
│   ├── plugin_manager.py         # Discovery & loading
│   └── examples/
│       └── price_alert.py        # Example plugin
├── gui/
│   └── main_window.py            # Tkinter GUI
└── tests/
    ├── test_parser.py
    ├── test_database.py
    └── fixtures/
        └── sample_items.txt
```

### Database Schema (SQLite)
```sql
-- Game configuration
CREATE TABLE game_configs (
    id INTEGER PRIMARY KEY,
    game_version TEXT NOT NULL,  -- 'poe1' or 'poe2'
    league TEXT NOT NULL,
    last_price_update TIMESTAMP,
    divine_chaos_rate REAL
);

-- Checked items history
CREATE TABLE checked_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_version TEXT NOT NULL,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_rarity TEXT,
    chaos_value REAL,
    divine_value REAL,
    stack_size INTEGER DEFAULT 1,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data TEXT  -- Full item text
);

-- Sales tracking
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER REFERENCES checked_items(id),
    listed_price_chaos REAL,
    listed_at TIMESTAMP,
    sold_at TIMESTAMP,
    actual_price_chaos REAL,
    time_to_sale_hours REAL,
    relisted BOOLEAN DEFAULT FALSE,
    notes TEXT
);

-- Meta builds affixes (future)
CREATE TABLE meta_affixes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_version TEXT NOT NULL,
    build_name TEXT,
    affix_text TEXT NOT NULL,
    priority INTEGER,  -- 1=required, 2=high value, 3=nice to have
    source_pob_url TEXT,
    updated_at TIMESTAMP
);

-- Price history (future)
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_version TEXT NOT NULL,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    chaos_value REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Plugin state
CREATE TABLE plugin_state (
    plugin_name TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    config_json TEXT
);
```

### Plugin System Architecture
```python
# base_plugin.py
from abc import ABC, abstractmethod

class PluginBase(ABC):
    """All plugins inherit from this"""
    
    @abstractmethod
    def initialize(self, app_context):
        """Called when plugin loads"""
        pass
    
    @abstractmethod
    def on_item_checked(self, item_data):
        """Hook: after item price checked"""
        pass
    
    @abstractmethod
    def on_price_update(self, price_data):
        """Hook: after price data refresh"""
        pass
    
    def get_name(self):
        return self.__class__.__name__
    
    def get_version(self):
        return "1.0.0"

# plugin_manager.py
class PluginManager:
    """Discovers and loads plugins from plugins/ directory"""
    
    def discover_plugins(self):
        # Scan for .py files in plugins/
        # Import and instantiate classes inheriting PluginBase
        pass
    
    def call_hook(self, hook_name, *args):
        # Execute hook on all enabled plugins
        for plugin in self.active_plugins:
            getattr(plugin, hook_name)(*args)
```

## DATA SOURCES REFERENCE

### 1. poe.ninja (PoE1)
**Endpoints:**
- `/api/data/currencyoverview?league={league}&type=Currency`
- `/api/data/itemoverview?league={league}&type={type}`
  - Types: UniqueWeapon, UniqueArmour, UniqueAccessory, UniqueFlask, UniqueJewel, Fragment, DivinationCard, Essence, Fossil, Scarab, Oil, Incubator, Vial
- `/api/data/economyleagues` - Get active leagues

**Response Fields:**
- `chaosValue` - Current price in chaos
- `divineValue` - Price in divines (if >= 0.1div)
- `sparkline.data[]` - 7-day price history
- `lowConfidenceSparkline` - Low sample size data

### 2. poe2scout.com (PoE2)
**Base:** `https://poe2scout.com/api`
**Docs:** `/api/swagger`
**Features:** Real-time prices, currency exchange, open API
**Requirements:** User-Agent header with email

### 3. Official Trade API
**Search:** `POST /api/trade/search/{league}`
**Fetch:** `GET /api/trade/fetch/{item_ids}?query={search_id}`
**Headers Required:**
- `User-Agent: your-app-name, your@email.com`
- Rate limit headers returned in response

**Query Structure:**
```json
{
  "query": {
    "status": {"option": "online"},
    "name": "Shavronne's Wrappings",
    "type": "Occultist's Vestment",
    "stats": [{"type": "and", "filters": []}]
  },
  "sort": {"price": "asc"}
}
```

### 4. Wiki Cargo API
**Base:** `https://www.poewiki.net/w/api.php`
**Action:** `?action=cargoquery`
**Use:** Item base types, mod pools, skill data
**Query:** SQL-like syntax

## CURRENT STATE

### Working Features
- [x] Parse items from clipboard
- [x] poe.ninja price lookups (PoE1)
- [x] GUI with Tkinter
- [x] Excel export with openpyxl
- [x] Stack size handling
- [x] Config persistence (pickle)
- [x] League auto-detection

### In Progress
- [ ] Refactor into modular structure
- [ ] SQLite database integration
- [ ] Plugin system foundation
- [ ] GitHub repository setup

### Planned Features
1. **Phase 1:** Multi-API infrastructure, PoE2 support
2. **Phase 2:** Sales tracking, price alerts (webhook to Discord)
3. **Phase 3:** Meta affix analysis from PoB, computer vision OCR
4. **Phase 4:** Web dashboard + REST API

## DEPENDENCIES

**Core:**
- `requests` - API calls
- `tkinter` - GUI (built-in)

**Optional:**
- `openpyxl` - Excel export
- `pytest` - Testing
- `sqlalchemy` - ORM (future)
- `fastapi` - Web API (future)
- `opencv-python` - CV (future)
- `pytesseract` - OCR (future)

## DESIGN DECISIONS

1. **SQLite over PostgreSQL:** Lightweight, no server, portable, good for learning
2. **Pickle for config:** Simple, built-in, sufficient for user settings
3. **Tkinter over Qt/Web:** Cross-platform, no dependencies, faster dev
4. **Plugin system:** Extensibility, separation of concerns, portfolio value
5. **Unified PoE1/PoE2:** Same codebase, game version as parameter
6. **Adapter pattern for APIs:** Swap implementations, easy testing, rate limit abstraction

## DEVELOPMENT WORKFLOW

### Git Strategy
- `main` branch = stable releases
- `develop` branch = active development
- Feature branches: `feature/plugin-system`
- Commit messages: Conventional Commits format

### Testing Approach
- Unit tests for parsers, database layer
- Integration tests with mock APIs
- Manual testing for GUI

### GitHub Codespaces
- Cloud IDE for mobile work
- LLMs can read repo directly
- Free tier: 60 hours/month

## PORTFOLIO VALUE

**Demonstrates:**
- API integration (multiple sources)
- Database design & SQL
- Plugin architecture
- GUI development
- Error handling & rate limiting
- Testing practices
- Git workflow
- Documentation

**Unique aspects:**
- PoE1 + PoE2 unified tool (gap in ecosystem)
- LLM-assisted development (this doc!)
- Sales tracking for price learning
- Meta analysis from build data

## QUICK REFERENCE

**User's System:**
- OS: Windows
- Python: 3.12
- IDE: PyCharm
- Project: `C:\Users\toddb\PycharmProjects\exilePriceCheck`
- PoE Account: sacrosanct24
- Main Character: TripSevens (Level 90 RF Chieftain)

**Current League:** Keepers of the Flame (3.27)
**PoE2 Status:** Early Access 0.4.x

## NEXT IMMEDIATE STEPS

1. Initialize Git repository
2. Create GitHub repo
3. Refactor current code into modules
4. Implement base_api.py with rate limiting
5. Create database.py with SQLite schema
6. Build plugin_manager.py
7. Update CONTEXT.md as we progress

---
PoE Price Checker – Master Context File (Updated)
1. Project Overview

The project is a Python-based price checking and item parsing tool for Path of Exile.
It includes:

Config management (core/config.py)

SQLite persistence (core/database.py)

POE item text parser (core/item_parser.py)

Game configuration types (core/game_version.py)

A growing test suite (58+ tests)

The goal: a reliable, cross-version PoE item price checker with plugin support and GUI integration in the future.

2. Current Architecture Summary
Configuration Layer (core/config.py)

Responsible for:

Loading/saving JSON config

Managing per-game settings (PoE1/PoE2)

UI preferences (min chaos, window size, vendor visibility)

API settings (auto-detect league)

Plugin enable/disable

Resetting config to defaults

Ensuring deep-copy of defaults (no test contamination)

Status: Fully refactored and stable.

Database Layer (core/database.py)

SQLite-backed storage for:

Recent item checks

Sales & completion times

Price history snapshots

Plugin state + config

Stats aggregation

Schema versioning

Timestamp normalization to UTC

Safe transaction wrapper

Deterministic ordering for checked items

Status: Fully refactored and stable.

Item Parsing Layer (core/item_parser.py)

Parses POE clipboard text into ParsedItem objects:

Rarity

Name / base type

Item level / quality

Requirements block

Sockets & links

Influences (Shaper, Elder, Exarch, etc.)

Flags (Corrupted, Fractured, Synthesised, Mirrored)

Implicit, explicit, enchant mods

Multi-item parsing (parse_multiple)

Status: Fully refactored and stable.

3. Test Suite Summary (58+ tests)
Covers:

Config defaults, persistence, deep-copy isolation

Multi-game settings transitions

UI preference persistence

API flag persistence

Plugin enable/disable/config storage

Database filters (game, league, sold-only, etc.)

Sales time normalization (UTC-safe)

Price history retrieval & ordering

Item parser: implicit, explicit, enchant, requirements, sockets, links, influences

Validity checks for malformed text

Everything passes after refactor.

4. Known Good State

As of the last commit:

All tests pass across all modules

Behavior remains backward compatible

Refactored modules are cleaner, modular, and extensible

Developer workflow validated through PyCharm + pytest

Ready for future features: GUI, plug-ins, async fetchers, schema upgrades

5. Your Workflow Preferences

You want clean, maintainable code, not just “it works.”

You like deep refactors when the tests guarantee safety.

You prefer short, actionable commit messages for version control.

You rely on ChatGPT as a pair programmer and expect output that can be pasted directly into PyCharm.

You want ChatGPT to:

maintain high context continuity

provide safe refactors

design additional tests

produce standalone files for copy/paste

help with PRs, summaries, changelogs, and architecture decisions

6. Next Steps You’ve Expressed Interest In

You haven’t chosen yet, but future tasks may include:

Potential Phase 4: Project Polish

Add pyproject.toml packaging

Consistent logging

Type hinting across modules

Black/Ruff/Isort formatting profile

Coverage config

Potential Phase 5: More Tests

Integration tests across config→parser→database

Schema-migration tests

Multi-item parsing edge cases

Plugin system round-trip expansion

Potential Phase 6: Performance Improvements

Prepared SQLite statements

Caching strategies

Parser speedups

Bulk inserts

Async API fetchers via asyncio

Potential Phase 7: Feature Development

GUI (Tkinter or PyQt)

Plugin interfaces

Pricing engine enhancements

PoE2-specific logic separation

UI theme/layout updates

7. How to use this Context File in the Future

If starting a new session:

“Load this context file for the PoE Price Checker project:”
[Paste everything from “PoE Price Checker – Master Context File” onward]

I will restore full continuity immediately.

**For LLM:** This document contains ALL critical context. Read this first on new sessions. Key sections: Gotchas (rate limits!), Architecture, Database Schema, Data Sources.
