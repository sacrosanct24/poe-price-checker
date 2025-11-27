# BiS (Best-in-Slot) Search System

**Purpose:** Find optimal gear upgrades based on your build's needs
**Version:** 1.0 | **Last Updated:** 2025-11-26

---

## Overview

The BiS Search system helps you find optimal gear upgrades by:

1. **Analyzing your build stats** - Identifies gaps in resistances, attributes, and defenses
2. **Using your stat priorities** - Respects your Critical/Important/Nice-to-have priorities
3. **Understanding affix tiers** - Knows what mods are achievable at each item level
4. **Learning from build guides** - Can extract gear recommendations from reference builds

---

## Quick Start

### Opening BiS Search

1. Go to **View > Find BiS Item...**
2. Select your character profile
3. Choose an equipment slot
4. Click "Open in Browser" or "Search In-App"

### Setting Up Priorities

1. In the BiS Search dialog, click **"Edit Priorities"**
2. Add stats that matter to your build:
   - **Critical** - Must-have stats (e.g., life for life builds)
   - **Important** - High-priority stats (e.g., missing resistances)
   - **Nice to Have** - Bonus stats (e.g., movement speed)
3. Use **"Auto-Suggest from Build"** to populate based on your PoB stats
4. Click **Save** - priorities are stored with your profile

---

## Components

### 1. Build Priorities System

**File:** `core/build_priorities.py`

Stores your stat preferences in three tiers:

```python
# Example priorities
priorities = BuildPriorities()
priorities.add_priority("life", PriorityTier.CRITICAL, min_value=80)
priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT, min_value=40)
priorities.add_priority("movement_speed", PriorityTier.NICE_TO_HAVE)
```

**Available Stats:** 30+ including:
- Defensive: life, energy_shield, armour, evasion, spell_suppression
- Resistances: fire, cold, lightning, chaos, all_resistances
- Attributes: strength, dexterity, intelligence, all_attributes
- Offensive: attack_speed, cast_speed, crit_chance, crit_multi
- Utility: movement_speed, mana, life_regen, cooldown_recovery

### 2. Affix Tier Calculator

**File:** `core/affix_tier_calculator.py`

Knows what affix tiers are achievable at each item level:

```python
calc = AffixTierCalculator()

# What's the best life roll at ilvl 75?
tier = calc.get_best_tier_for_ilvl("life", 75)
# Returns: T3, 80-89 (requires ilvl 73+)

# What's the best at ilvl 86?
tier = calc.get_best_tier_for_ilvl("life", 86)
# Returns: T1, 100-109 (requires ilvl 86+)
```

**Key Features:**
- Knows ilvl requirements for each tier
- Knows which stats can roll on which slots
- Generates "ideal rare" specs based on priorities

### 3. Guide Gear Extractor

**File:** `core/guide_gear_extractor.py`

Extracts gear recommendations from reference builds:

```python
extractor = GuideGearExtractor(character_manager)
summary = extractor.extract_from_profile("My Reference Build")

# Shows uniques needed
print(summary.uniques_needed)  # ["Devoto's Devotion", "Headhunter"]

# Shows rare slot recommendations
print(summary.rare_slots)  # ["Body Armour", "Boots", "Ring 1"]
```

### 4. BiS Calculator

**File:** `core/bis_calculator.py`

Analyzes your build and generates trade search requirements:

```python
calc = BiSCalculator(build_stats)

# Get requirements for a slot
reqs = calc.calculate_requirements("Helmet", custom_priorities=priorities)

# Generates search with:
# - Required stats (critical priorities)
# - Desired stats (important + nice-to-have)
# - Proper trade API stat IDs
```

---

## How BiS Search Works

### Without Custom Priorities (Auto-Detection)

1. Analyzes your PoB stats
2. Determines build type (Life/ES/Hybrid)
3. Identifies resistance gaps (overcap < 30%)
4. Identifies attribute needs (< 100)
5. Generates slot-specific requirements

### With Custom Priorities

1. Loads your saved priorities for the profile
2. **Critical** stats become required in search
3. **Important** stats become high-priority desired
4. **Nice-to-have** stats fill remaining slots
5. Respects ilvl tier limitations

---

## Ideal Rare Generation

The system can generate an "ideal rare" specification:

```
=== Ideal Helmet (ilvl 84) ===
  T2 Maximum Life: 90-99 (requires ilvl 82)
  T1 Fire Resistance: 46-48 (requires ilvl 84)
  T1 Cold Resistance: 46-48 (requires ilvl 84)
  T1 Lightning Resistance: 46-48 (requires ilvl 84)
```

This tells you:
- What tier of each stat is achievable
- What ilvl you need to target
- Expected value ranges

---

## Guide Gear Integration

When you have a reference build (from Maxroll, pobb.in, etc.):

1. Import the build as a profile
2. The BiS system can extract:
   - **Unique items** the guide recommends
   - **Rare item bases** and their key mods
   - **Priority slots** for upgrades

### Example Output

```
=== Gear from: RF Chieftain ===

UNIQUE ITEMS NEEDED:
  [Helmet] Devoto's Devotion
      - +60 to Dexterity
      - 16% increased Attack Speed
      - 20% increased Movement Speed

RARE ITEM SLOTS:
  [Body Armour] Astral Plate
      - +105 to maximum Life
      - +45% to Fire Resistance
      - Triple resistance
```

---

## Trade Search Generation

The system generates trade API queries with:

1. **Stat filters** based on priorities
2. **Minimum values** from affix tier data
3. **Online-only** results
4. **Price sorting** (low to high)

### Search Modes

- **Open in Browser** - Opens pathofexile.com/trade with query copied
- **Search In-App** - Performs search and displays results inline

---

## Data Files

### Affix Tier Data

Embedded in `core/affix_tier_calculator.py`:

```python
AFFIX_TIER_DATA = {
    "life": [
        (1, 86, 100, 109),  # T1: ilvl 86+, 100-109
        (2, 82, 90, 99),    # T2: ilvl 82+, 90-99
        ...
    ],
}
```

### Slot Affix Availability

```python
SLOT_AVAILABLE_AFFIXES = {
    "Boots": ["life", "energy_shield", "resistances", "movement_speed", ...],
    "Gloves": ["life", "energy_shield", "resistances", "attack_speed", ...],
}
```

---

## Testing

Run BiS system tests:

```bash
python -m pytest tests/test_bis_system.py -v
```

Tests cover:
- BuildPriorities CRUD operations
- Priority serialization
- Affix tier lookups
- Ideal rare generation
- Guide gear extraction
- Integration scenarios

---

## Future Enhancements

- [ ] Update BiS dialog with tabbed interface (Guide Gear / Ideal Rare / Search)
- [ ] Live comparison with current equipped items
- [ ] Price estimation for ideal rares
- [ ] Integration with trade API rate limiting
- [ ] Support for influenced item mods

---

## Related Documentation

- [Rare Item Valuation Guide](../RARE_ITEM_VALUATION.md) - Understanding rare item economy
- [Integration Guide](INTEGRATION_GUIDE.md) - Build archetype integration
- [GUI Integration Guide](GUI_INTEGRATION_GUIDE.md) - UI components
