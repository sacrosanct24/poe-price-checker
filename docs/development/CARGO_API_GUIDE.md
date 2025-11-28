---
title: Cargo API Integration Guide
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
related_code:
  - data_sources/cargo_api_client.py
---

# Cargo API Integration Guide

## Overview

This guide explains how to populate the mod database using the PoE Wiki Cargo API.

## Supported Wikis

Both Path of Exile wikis use the MediaWiki Cargo extension for structured data queries:

| Wiki | Base URL | Cargo Tables |
|------|----------|--------------|
| PoE1 | https://www.poewiki.net | https://www.poewiki.net/wiki/Special:CargoTables |
| PoE2 | https://www.poe2wiki.net | https://www.poe2wiki.net/wiki/Special:CargoTables |

The `CargoAPIClient` supports both wikis - just specify the base URL when initializing.

## Quick Start

Once the wiki is online, populate the database with:

```bash
python data_sources/mod_data_loader.py
```

This will:
1. Fetch all item mods from Cargo API
2. Store in SQLite database (`data/mods.db`)
3. Set metadata (league, update time)

## Manual Population (Python)

```python
from data_sources.mod_data_loader import ensure_mod_database_updated

# Populate database for current league
db = ensure_mod_database_updated(league="Settlers", force_update=True)

# Check stats
print(f"Mods loaded: {db.get_mod_count()}")
print(f"Last update: {db.get_last_update_time()}")
```

## Using PoE2 Wiki

```python
from data_sources.cargo_api_client import CargoAPIClient

# Query PoE2 wiki
poe2_client = CargoAPIClient(wiki="poe2")
results = poe2_client.query(
    tables="mods",
    fields="mods.id,mods.name",
    limit=10
)

# Query PoE1 wiki (default)
poe1_client = CargoAPIClient(wiki="poe1")
```

## Query Examples

Based on PoE Wiki Cargo API documentation:

### 1. Get Life Mods (Suffixes)

```
https://www.poewiki.net/w/api.php?
  action=cargoquery&
  tables=mods&
  fields=mods.id,mods.name,mods.stat_text,mods.stat1_min,mods.stat1_max&
  where=mods.domain=1 AND mods.generation_type=7&
  limit=100&
  order_by=mods.stat1_max DESC
```

**Parameters:**
- `domain=1` → Item mods (not flask, monster, etc.)
- `generation_type=7` → Suffix (6 = prefix)
- `order_by=mods.stat1_max DESC` → Highest values first (T1 tiers)

### 2. Get Movement Speed Mods

```python
from data_sources.cargo_api_client import CargoAPIClient

client = CargoAPIClient()
results = client.query(
    tables="mods",
    fields="mods.id,mods.name,mods.stat_text,mods.stat1_min,mods.stat1_max",
    where='mods.domain=1 AND mods.generation_type=7',
    order_by="mods.stat1_max DESC",
    limit=100
)
```

### 3. Get All Item Mods (Paginated)

```python
client = CargoAPIClient()
all_mods = client.get_all_item_mods(
    generation_type=None,  # Both prefixes and suffixes
    batch_size=500,
    max_total=5000
)
print(f"Fetched {len(all_mods)} total mods")
```

## Database Schema

```sql
CREATE TABLE mods (
    id TEXT PRIMARY KEY,              -- Mod ID (e.g., "LifeT1")
    name TEXT NOT NULL,               -- Internal name (e.g., "of the Titan")
    stat_text TEXT,                   -- Display text ("+# to maximum Life")
    domain INTEGER,                   -- 1=item, 2=flask, 3=monster, etc.
    generation_type INTEGER,          -- 6=prefix, 7=suffix
    mod_group TEXT,                   -- Mod group (e.g., "IncreasedLife")
    required_level INTEGER,           -- Minimum item level
    stat1_id TEXT,                    -- Primary stat ID
    stat1_min INTEGER,                -- Minimum value
    stat1_max INTEGER,                -- Maximum value
    stat2_id TEXT,                    -- Secondary stat (optional)
    stat2_min INTEGER,
    stat2_max INTEGER,
    tags TEXT,                        -- Mod tags
    created_at TIMESTAMP
);
```

## Cargo API Response Format

### Successful Response

```json
{
  "cargoquery": [
    {
      "title": {
        "id": "LifeT1",
        "name": "of the Titan",
        "stat text": "+# to maximum Life",
        "stat1 min": "100",
        "stat1 max": "109",
        "required level": "44",
        "generation type": "7",
        "domain": "1"
      }
    },
    {
      "title": {
        "id": "LifeT2",
        "name": "of the Bear",
        "stat text": "+# to maximum Life",
        "stat1 min": "90",
        "stat1 max": "99",
        ...
      }
    }
  ]
}
```

### Error Response

```json
{
  "error": {
    "code": "internal_api_error_MWException",
    "info": "[trace_id] Caught exception of type MWException",
    "errorclass": "MWException"
  }
}
```

## Using the Database

### Query Tier Ranges

```python
from data_sources.mod_database import ModDatabase

db = ModDatabase()

# Get life tiers
life_tiers = db.get_affix_tiers("%to maximum Life")
for tier, min_val, max_val in life_tiers:
    print(f"T{tier}: {min_val}-{max_val} Life")

# Output:
# T1: 100-109 Life
# T2: 90-99 Life
# T3: 80-89 Life
# ...
```

### Find Mods by Pattern

```python
# Find all life mods
life_mods = db.find_mods_by_stat_text("%maximum Life%", generation_type=7)
print(f"Found {len(life_mods)} life suffix mods")

for mod in life_mods[:5]:
    print(f"{mod['name']}: {mod['stat1_min']}-{mod['stat1_max']}")
```

## Hybrid System (Database + JSON Fallback)

The `AffixDataProvider` automatically uses the best available source:

```python
from data_sources.affix_data_provider import get_affix_provider

provider = get_affix_provider()

# Check which source is active
print(provider.get_source_info())
# "ModDatabase: 3000 mods, league=Settlers" OR
# "JSON Fallback: 18 affix types from data/valuable_affixes.json"

# Get tier ranges (from database if available, else JSON)
life_tiers = provider.get_affix_tiers(
    affix_type="life",
    stat_text_pattern="%to maximum Life"  # Only used if database available
)
```

## Update Schedule

The database auto-updates when:
1. **League changes** - Detected by comparing stored vs current league
2. **Data is stale** - More than 7 days old
3. **Manual trigger** - `force_update=True`

```python
# Check if update needed
from data_sources.mod_data_loader import ModDataLoader

loader = ModDataLoader()
if loader.should_update("Settlers"):
    print("Database needs updating")
    loader.load_all_mods("Settlers")
```

## Troubleshooting

### Wiki Returns 503 Errors

The PoE Wiki may be temporarily unavailable. The system falls back to JSON automatically.

### Empty Database

If database has 0 mods, the system uses JSON fallback. Check:

```python
from data_sources.mod_database import ModDatabase

db = ModDatabase()
print(f"Mod count: {db.get_mod_count()}")
print(f"Last update: {db.get_last_update_time()}")
print(f"League: {db.get_current_league()}")
```

### Cargo API Errors

Check the error response for details:

```python
from data_sources.cargo_api_client import CargoAPIClient

client = CargoAPIClient()
try:
    results = client.query(tables="mods", fields="mods.id", limit=1)
except Exception as e:
    print(f"API Error: {e}")
```

## Next Steps

1. **Wait for Wiki** - Currently experiencing 503 errors
2. **Populate Database** - Run `mod_data_loader.py` once wiki is up
3. **Verify Data** - Check tier ranges match game
4. **Enable Auto-Updates** - Set league in config for automatic updates

## References

- [PoE1 Wiki Cargo API Docs](https://www.poewiki.net/wiki/Path_of_Exile_Wiki:Data_query_API)
- [PoE2 Wiki Cargo API Docs](https://www.poe2wiki.net/wiki/Path_of_Exile_2_Wiki:Data_query_API)
- [Cargo Query Format](https://www.mediawiki.org/wiki/Extension:Cargo/Querying_data)
