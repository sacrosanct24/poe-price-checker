# PoE Economy Historical Data Sources

This document describes how to obtain historical economy data for Path of Exile leagues.

## Data Sources

### 1. poe.ninja Data Dumps (Primary Source)

**URL**: https://poe.ninja/poe1/data

poe.ninja provides downloadable CSV dumps for all past challenge leagues dating back to **Essence League (2016)**. These files contain daily snapshots of currency and item prices.

#### CSV Format
- **Delimiter**: Semicolon (`;`)
- **Fields**: `League; Date; Get; Pay; Value; Confidence`
- **Example**: `Abyss; 2017-12-10; Exalted Orb; Chaos Orb; 35.92556; High`

#### File Structure
Each league has two files:
- `{League}.currency.csv` - Currency exchange rates (~9,500 lines per league)
- `{League}.items.csv` - Item prices (~225,000 lines per league)

#### Available Leagues (as of 2024)

| League | Start Date | Notes |
|--------|-----------|-------|
| Keepers | Dec 2024 | Current league |
| Settlers | Jul 2024 | |
| Necropolis | Mar 2024 | |
| Affliction | Dec 2023 | |
| Ancestor | Aug 2023 | |
| Crucible | Apr 2023 | |
| Forbidden Sanctum | Dec 2022 | |
| Lake of Kalandra | Aug 2022 | |
| Sentinel | May 2022 | |
| Archnemesis | Feb 2022 | |
| Scourge | Oct 2021 | |
| Expedition | Jul 2021 | |
| Ultimatum | Apr 2021 | |
| Ritual | Jan 2021 | |
| Heist | Sep 2020 | |
| Harvest | Jun 2020 | |
| Delirium | Mar 2020 | |
| Metamorph | Dec 2019 | |
| Blight | Sep 2019 | |
| Legion | Jun 2019 | |
| Synthesis | Mar 2019 | |
| Betrayal | Dec 2018 | |
| Delve | Aug 2018 | |
| Incursion | Jun 2018 | |
| Bestiary | Mar 2018 | |
| Abyss | Dec 2017 | |
| Harbinger | Aug 2017 | |
| Legacy | Mar 2017 | |
| Breach | Dec 2016 | |
| Essence | Sep 2016 | Earliest available |

### 2. poe.ninja Live API

For current league data, use the JSON API:

```
# Currency rates
https://poe.ninja/api/data/currencyoverview?league={league}&type=Currency

# Item prices
https://poe.ninja/api/data/itemoverview?league={league}&type={type}
```

**Item Types**: UniqueWeapon, UniqueArmour, UniqueAccessory, UniqueFlask, UniqueJewel, DivinationCard, SkillGem, Map, Scarab, Fossil, etc.

### 3. PoE Antiquary (Visualization)

**URL**: https://poe-antiquary.xyz/

Provides visualization of historical poe.ninja data for 30+ leagues. View-only (no API/download).

## Importing Data

### Step 1: Download CSV Files

1. Visit https://poe.ninja/poe1/data
2. Select the league you want
3. Download the ZIP file
4. Extract the CSV files

### Step 2: Place Files in Data Directory

```
data/
  economy/
    Keepers.currency.csv
    Keepers.items.csv
    Settlers.currency.csv
    Settlers.items.csv
    ...
```

### Step 3: Import Using the Service

```python
from pathlib import Path
from core.database import Database
from core.economy import LeagueEconomyService

db = Database()
service = LeagueEconomyService(db)

# Import currency data
csv_path = Path("data/economy/Necropolis.currency.csv")
csv_content = csv_path.read_text()
service.import_currency_csv(csv_content, "Necropolis")

# Import item data
csv_path = Path("data/economy/Necropolis.items.csv")
csv_content = csv_path.read_text()
service.import_item_csv(csv_content, "Necropolis", item_type="UniqueAccessory")
```

## Automatic Collection

For current leagues, use the collection script:

```bash
# Collect snapshots for current leagues
python scripts/collect_economy_snapshot.py --leagues Keepers,Standard

# Or use the menu: View → Collect Economy Snapshot
```

Schedule this to run daily to build historical data going forward.

## Data Schema

### Currency Rate Record
| Field | Type | Description |
|-------|------|-------------|
| league | TEXT | League name |
| currency_name | TEXT | e.g., "Divine Orb" |
| rate_date | TEXT | ISO date |
| chaos_value | REAL | Value in chaos |

### Item Price Record
| Field | Type | Description |
|-------|------|-------------|
| league | TEXT | League name |
| item_name | TEXT | Item name |
| base_type | TEXT | Base type |
| item_type | TEXT | Category (UniqueWeapon, etc.) |
| rate_date | TEXT | ISO date |
| chaos_value | REAL | Value in chaos |

## References

- [poe.ninja Data Page](https://poe.ninja/poe1/data)
- [poe.ninja API Documentation](https://github.com/ayberkgezer/poe.ninja-API-Document)
- [PoE Antiquary](https://poe-antiquary.xyz/)
- [produdez/poe-economy](https://github.com/produdez/poe-economy) - Example data analysis project
