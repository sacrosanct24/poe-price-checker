# Meta Builds Knowledge Base

This directory contains curated meta build data used to enhance item evaluation accuracy. Items that match gear requirements for popular builds receive pricing adjustments.

## Update Schedule

| Timing | Action | Command |
|--------|--------|---------|
| **Pre-League** | Full refresh 1-2 days before | `/update-meta-builds` |
| **Week 1-2** | Daily updates (meta forming) | `/update-meta-builds` |
| **Week 3+** | Weekly updates | `/update-meta-builds` |
| **Mid-League** | Weekly maintenance | `/update-meta-builds` |

## Data Sources

### Primary Sources
- **poe.ninja/builds** - Aggregated ladder data, skill usage, item popularity
- **poe2.ninja/builds** - PoE2 equivalent
- **Maxroll.gg Meta** - Curated tier lists and build guides

### Secondary Sources
- **Community tier lists** - Reddit, Discord consensus
- **Streamer builds** - Popular content creator builds
- **League mechanic synergies** - Builds that synergize with current league

## File Structure

```
data/meta_builds/
├── README.md                    # This file
├── poe1/
│   ├── current_league.json      # Current PoE1 league meta
│   ├── standard.json            # Standard league meta
│   └── history/                 # Historical snapshots
│       └── 3.27_week1.json
├── poe2/
│   ├── current_league.json      # Current PoE2 league meta
│   └── history/
│       └── 0.4.0_week1.json
└── affix_weights.json           # Generated weights for price_integrator
```

## JSON Schema

### Build Entry
```json
{
  "id": "lightning_arrow_deadeye",
  "name": "Lightning Arrow Deadeye",
  "tier": "S",
  "popularity_percent": 32.5,
  "ascendancy": "Deadeye",
  "primary_skill": "Lightning Arrow",
  "archetype": "ranged_attack",
  "last_updated": "2025-12-08",
  "gear_requirements": {
    "weapon": {...},
    "helmet": {...},
    ...
  },
  "key_uniques": [...],
  "desired_affixes": {...}
}
```

### Gear Slot Schema
```json
{
  "slot": "bow",
  "base_types": ["Thicket Bow", "Imperial Bow"],
  "min_item_level": 83,
  "required_affixes": [
    {
      "type": "prefix",
      "name": "flat_phys",
      "pattern": "Adds # to # Physical Damage",
      "min_tier": 2,
      "priority": "required"
    }
  ],
  "desired_affixes": [
    {
      "type": "suffix",
      "name": "attack_speed",
      "pattern": "#% increased Attack Speed",
      "min_tier": 2,
      "priority": "high"
    }
  ],
  "influence_preference": "none"
}
```

## Integration with Item Evaluator

The meta builds data feeds into `core/price_integrator.py` via:

1. **Affix Weight Generation** (`affix_weights.json`)
   - Popular affixes get higher base weights
   - Build-specific affixes get multipliers

2. **Archetype Detection**
   - Items matching popular archetypes get bonuses
   - Example: Bow with attack speed + crit = ranged_attack archetype

3. **Unique Item Prioritization**
   - Key uniques for meta builds get price tracking priority
   - Example: If 30% of builds use "Hyrri's Ire", track its price closely

## Affix Priority Levels

| Priority | Weight Multiplier | Description |
|----------|-------------------|-------------|
| `required` | 2.0x | Build doesn't function without |
| `high` | 1.5x | Major DPS/defense increase |
| `medium` | 1.2x | Nice to have improvement |
| `low` | 1.0x | Minor optimization |

## Tier Definitions

| Tier | Description | Price Impact |
|------|-------------|--------------|
| S | Meta-defining, 20%+ of ladder | +50% weight |
| A | Strong meta pick, 10-20% | +30% weight |
| B | Viable, 5-10% | +15% weight |
| C | Off-meta but functional | +0% weight |
| D | Struggling/meme | -10% weight |
