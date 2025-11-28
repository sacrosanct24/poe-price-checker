---
title: Data Sources Guide
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
related_code:
  - data_sources/
---

# Data Sources Guide

Authoritative reference for all data sources used in PoE Price Checker.

---

## Data Source Authority Tier List

### Tier 1: Authoritative Game Data (Most Trusted)

| Source | Data Type | Why Authoritative |
|--------|-----------|-------------------|
| **RePoE** | Mod tiers, base items, stat translations | Extracted directly from game files |
| **PoB (Build Data)** | Player stats, equipment, skills | User's actual build configuration |
| **Official Trade API** | Live listings, prices | Real market data |

### Tier 2: Aggregated Market Data (Highly Trusted)

| Source | Data Type | Notes |
|--------|-----------|-------|
| **poe.ninja** | Currency rates, unique prices | Aggregates trade API, high volume |
| **poe.watch** | Secondary price validation | Good for cross-referencing |

### Tier 3: Wiki/Community Data (Generally Trusted)

| Source | Data Type | Limitations |
|--------|-----------|-------------|
| **Cargo API (Wiki)** | Mods, items, uniques | May lag behind patches |
| **poeprices.info** | ML-based rare pricing | Varies in accuracy |

### Tier 4: Static/Hardcoded (Fallback Only)

| Source | Data Type | Use Case |
|--------|-----------|----------|
| **valuable_affixes.json** | Tier ranges, weights | Fallback when DB unavailable |
| **trade_stat_ids.py** | Stat ID mappings | Should be validated against RePoE |

---

## Current Usage Audit

### Module → Data Source Mapping

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA FLOW DIAGRAM                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User Input (Clipboard/PoB Code)                                    │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────┐                                                │
│  │  item_parser.py │ ── Parses item text (no external data)        │
│  └────────┬────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Evaluation Layer                                            │   │
│  │  ┌───────────────────────┐  ┌───────────────────────────┐   │   │
│  │  │ rare_item_evaluator   │  │ affix_tier_calculator     │   │   │
│  │  │ ────────────────────  │  │ ─────────────────────     │   │   │
│  │  │ Uses:                 │  │ Uses:                      │   │   │
│  │  │ - valuable_affixes    │  │ - RePoE (preferred)        │   │   │
│  │  │   .json (static)      │  │ - AFFIX_TIER_DATA (fallback)│  │   │
│  │  └───────────────────────┘  └───────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Pricing Layer                                               │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │   │
│  │  │ poe_ninja.py    │  │ poe_watch.py    │  │ poeprices.py │ │   │
│  │  │ (Primary)       │  │ (Secondary)     │  │ (Rares)      │ │   │
│  │  └─────────────────┘  └─────────────────┘  └──────────────┘ │   │
│  │                         │                                    │   │
│  │  ┌─────────────────────┴────────────────────────────────┐   │   │
│  │  │ trade_api.py - Official PoE Trade API queries        │   │   │
│  │  │ Uses: trade_stat_ids.py for stat ID mappings         │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Persistence Layer (database.py)                             │   │
│  │  - checked_items: Price check history                        │   │
│  │  - sales: User's sales records                               │   │
│  │  - price_history: Historical price snapshots                 │   │
│  │  - price_checks + price_quotes: Raw API responses            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Source Usage by Feature

| Feature | Data Sources Used | Authority Level |
|---------|-------------------|-----------------|
| **Unique Pricing** | poe.ninja → poe.watch | Tier 1-2 |
| **Currency Rates** | poe.ninja | Tier 1 |
| **Rare Evaluation** | valuable_affixes.json | Tier 4 (needs upgrade) |
| **Tier Calculation** | RePoE → hardcoded fallback | Tier 1 with fallback |
| **Trade Queries** | trade_stat_ids.py → Trade API | Tier 1 |
| **PoB Integration** | PoB share code (user data) | Tier 1 |
| **Mod Database** | Cargo API → SQLite cache | Tier 3 |

---

## Issues Identified

### Issue 1: Rare Evaluation Uses Static Data
**Current:** `rare_item_evaluator.py` loads `valuable_affixes.json`
**Problem:** Static weights don't reflect build context or current meta
**Fix:** Integrate with PoB archetype detection (Phase 2 of roadmap)

### Issue 2: trade_stat_ids.py May Drift from Game
**Current:** Hardcoded stat ID mappings
**Problem:** Can become stale after patches
**Fix:** Consider generating from RePoE stat translations

### Issue 3: No Price Trend Analysis
**Current:** price_history table exists but not used
**Problem:** Can't show "price is rising/falling"
**Fix:** Implement price trend queries and UI

### Issue 4: Duplicate Data Sources for Tiers
**Current:** Both RePoE and AFFIX_TIER_DATA exist
**Problem:** Can give different results
**Status:** OK - RePoE is primary, hardcoded is fallback

---

## Historical Analytics Storage

### Current Database Schema (v3)

```sql
-- Price check records
checked_items (
    game_version, league, item_name, item_base_type,
    chaos_value, checked_at
)

-- Sales tracking
sales (
    item_name, item_base_type, source,
    listed_price_chaos, listed_at,
    sold_at, actual_price_chaos, time_to_sale_hours
)

-- Price snapshots
price_history (
    game_version, league, item_name, item_base_type,
    chaos_value, divine_value, recorded_at
)

-- Raw API responses
price_checks (game_version, league, item_name, checked_at, source)
price_quotes (price_check_id, source, price_chaos, original_currency, ...)
```

### What We CAN Query Historically

1. **Price trends over time** - `price_history` table
2. **Personal sales performance** - `sales` table
3. **Item check frequency** - `checked_items` table
4. **Multi-source price variance** - `price_quotes` table

### What We CANNOT Query (Gaps)

| Missing Data | Why It Matters | Recommendation |
|--------------|----------------|----------------|
| **League info on sales** | Can't compare across leagues | Add `league` column to `sales` |
| **Item rarity/type** | Can't filter by rare/unique | Add `rarity` column |
| **Mod details on checks** | Can't analyze mod value trends | Store mod array JSON |
| **Build context** | Can't correlate prices to builds | Add `build_archetype` column |
| **Divine conversion rate** | Historical divine:chaos ratio | Store in `price_history` |

### Recommended Schema v4 Additions

```sql
-- Add to sales table
ALTER TABLE sales ADD COLUMN league TEXT;
ALTER TABLE sales ADD COLUMN rarity TEXT;  -- RARE, UNIQUE, CURRENCY, etc.
ALTER TABLE sales ADD COLUMN game_version TEXT;

-- Add to checked_items
ALTER TABLE checked_items ADD COLUMN rarity TEXT;
ALTER TABLE checked_items ADD COLUMN item_mods_json TEXT;  -- JSON array of mods
ALTER TABLE checked_items ADD COLUMN build_profile TEXT;   -- PoB profile name

-- New table for divine:chaos tracking
CREATE TABLE currency_rates (
    id INTEGER PRIMARY KEY,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL,
    divine_to_chaos REAL NOT NULL,
    exalt_to_chaos REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Analytics Questions We Want to Answer

### Personal Analytics
- What's my average profit margin per item type?
- How long do items take to sell at different price points?
- What item types sell fastest?
- What's my total profit this league?

### Market Analytics
- Is this item's price trending up or down?
- What's the price variance across sources?
- How does divine:chaos ratio affect pricing?

### Build Analytics (Future)
- What items are most checked for my build type?
- What mods are most valuable for my archetype?

---

## Recommendations

### Short Term (Next Session)
1. Add `league` and `rarity` to `sales` table
2. Store divine:chaos rate with each price check
3. Add price trend indicator to UI

### Medium Term
1. Generate trade_stat_ids from RePoE
2. Validate valuable_affixes against RePoE tiers
3. Build price trend analysis queries

### Long Term
1. Full build-aware evaluation (roadmap phases 1-6)
2. ML-enhanced rare pricing using historical data
3. Market analytics dashboard

---

## Data Source Reference

### RePoE Client
```python
from data_sources.repoe_client import RePoEClient
client = RePoEClient()
mods = client.get_mods()  # All game mods with tiers
bases = client.get_base_items()  # Base item definitions
```

### Cargo API
```python
from data_sources.cargo_api_client import CargoAPIClient
client = CargoAPIClient()
mods = client.fetch_mods()  # Wiki mod data
```

### Price APIs
```python
from data_sources.pricing.poe_ninja import PoeNinjaAPI
from data_sources.pricing.poe_watch import PoeWatchAPI
from data_sources.pricing.poeprices import PoePricesClient
```

### PoB Integration
```python
from core.pob_integration import PoBDecoder, CharacterManager
decoder = PoBDecoder()
build = decoder.decode(pob_code)  # Parse PoB share code
```
