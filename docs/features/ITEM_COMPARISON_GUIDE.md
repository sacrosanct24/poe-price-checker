---
title: Item Comparison Guide
status: current
stability: stable
last_reviewed: 2025-11-28
---

# Item Comparison Guide

Compare two items side-by-side to see stat differences, with DPS impact estimation based on your PoB build.

## Quick Start

1. **Open the dialog**: Menu `Build > Compare Items...` or press `Ctrl+Shift+I`
2. **Paste items**: Copy items from the game (Ctrl+C while hovering) and paste into each panel
3. **Click "Parse Item"** to analyze each item
4. **View comparison**: The summary section shows upgrade/downgrade verdict

## Features

### Side-by-Side View

Each item gets its own panel with:
- **Paste area**: Input raw item text from the game
- **Item Inspector**: Full breakdown of stats and mods
- **Build-effective values**: Shows how mods benefit your specific build

### Comparison Summary

When both items are loaded, the summary shows:
- **Verdict**: UPGRADE / DOWNGRADE / SIDEGRADE
- **Gains**: What Item 2 provides that Item 1 doesn't
- **Losses**: What you lose going from Item 1 to Item 2

### DPS Impact Estimation

If you have a PoB build loaded, the Item Inspector shows estimated DPS impact for offensive mods:

```
DPS Impact (2.50M base, Fire/Crit/Spell build):
  +35% Fire Damage     → ~7.0% DPS (+175K) [HIGH]
  +40% Crit Multi      → ~5.3% DPS (+133K) [HIGH]
  +25% Spell Damage    → ~5.0% DPS (+125K) [HIGH]
  Total: ~17.3% DPS increase
```

#### Supported Mod Types

The DPS calculator recognizes:
- **Damage types**: Physical, Fire, Cold, Lightning, Chaos, Elemental
- **Attack/Spell damage**: Scaled based on your build type
- **Crit stats**: Crit chance, crit multiplier (weighted for crit builds)
- **Speed mods**: Attack speed, cast speed
- **Added damage**: Adds X to Y Fire/Cold/Lightning/Physical damage

#### Build Detection

The calculator automatically detects:
- **Crit builds**: High crit chance (>40%) or medium crit with high multiplier
- **Spell builds**: Majority of DPS from spells
- **Attack builds**: Majority of DPS from attacks
- **Minion builds**: Majority of DPS from minions
- **DoT builds**: Majority of DPS from damage over time
- **Primary damage type**: Which element deals the most damage

#### Relevance Ratings

- **HIGH**: Mod directly benefits your primary damage type
- **MEDIUM**: Mod provides partial or indirect benefit
- **LOW**: Mod provides minimal benefit to your build
- **NONE**: Mod doesn't affect your DPS (e.g., attack speed on spell build)

## Using the Dialog

### Swap Items

Click **"Swap Items"** to switch Item 1 and Item 2 positions. Useful when you want to reverse the comparison.

### Clear All

Click **"Clear All"** to reset both items and start fresh.

### Programmatic Access

You can set items programmatically from other parts of the application:

```python
dialog = ItemComparisonDialog(parent, app_context)
dialog.set_item1(current_item)
dialog.set_item2(potential_upgrade)
dialog.exec()
```

## Technical Details

### Build Stats Integration

When a PoB build is loaded, the calculator uses:
- `CombinedDPS` for total damage reference
- Individual DPS values (PhysicalDPS, FireDPS, etc.) for damage type weighting
- `CritChance` and `CritMultiplier` for crit build detection
- `SpellDPS` / `AttackDPS` for build type detection

### DPS Estimation Model

The DPS impact uses a diminishing returns model:
- Assumes ~400% baseline increased damage (realistic for endgame builds)
- Uses the formula: `impact = raw_value / (baseline + raw_value) * relevance_weight`
- Accounts for damage type proportions (e.g., Fire damage scaled by fire_dps/combined_dps)

### Mod Extraction

Items can have mods in various attributes:
- `implicits` / `implicit_mods` - Implicit modifiers
- `explicits` / `explicit_mods` / `mods` - Explicit modifiers
- `enchants` - Enchantment modifiers

The comparison handles all formats automatically.

## Keyboard Shortcuts

- `Ctrl+Shift+I` - Open Item Comparison dialog
- `Ctrl+B` - Open PoB Characters (to load a build first)

## Related Features

- [BiS Search Guide](BIS_SEARCH_GUIDE.md) - Find optimal gear upgrades
- [Rare Evaluator Quick Start](RARE_EVALUATOR_QUICK_START.md) - Evaluate rare item quality
- [Keyboard Shortcuts](KEYBOARD_SHORTCUTS.md) - All available shortcuts
