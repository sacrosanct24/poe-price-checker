# PoE Price Checker Documentation

Welcome to the PoE Price Checker documentation. Find guides for all features below.

---

## Core References

### Game Knowledge
- **[Rare Item Valuation Guide](RARE_ITEM_VALUATION.md)** - Comprehensive guide to PoE rare item economy
- [PoE API Reference](POE_API_REFERENCE.md) - Official trade API docs
- [PoE.Watch API Reference](POEWATCH_API_REFERENCE.md) - Alternative pricing API

---

## Features & User Guides

### Multi-Source Pricing
- [Quick Reference](features/QUICK_REFERENCE.md) - Using multi-source pricing
- [How to See Multi-Source Pricing](features/HOW_TO_SEE_MULTI_SOURCE_PRICING.md) - Detailed walkthrough

### Rare Item Evaluator
- **[Rare Evaluator Quick Start](features/RARE_EVALUATOR_QUICK_START.md)** - Get started quickly
- [GUI Integration Guide](features/GUI_INTEGRATION_GUIDE.md) - How evaluation integrates with GUI
- [Integration Guide](features/INTEGRATION_GUIDE.md) - Meta integration and build archetypes

### Item Planning Hub
- **Item Planning Hub** (Ctrl+U) - Unified upgrade finder and BiS search
  - Combines Upgrade Finder and BiS Guide into tabbed interface
  - Budget-based upgrade search with trade API integration
  - See [BiS Search Guide](features/BIS_SEARCH_GUIDE.md) for priority system details

### Build Manager
- **Build Manager** (Ctrl+B) - Unified build profile management
  - Profile list with filtering (class, category, favorites)
  - Equipment tab with item tree and price check integration
  - Details tab for metadata, notes, guide URLs

### Cross-Build Intelligence
- **"What builds want this item?"** analysis
  - 20+ meta build archetypes (RF Jugg, LA, Boneshatter, etc.)
  - Match percentage showing how well item fits each archetype
  - Integration with Rare Item Evaluator panel

### Unified Verdict Engine
- **Single-click comprehensive evaluation**
  - FOR YOU: Is this an upgrade?
  - TO SELL: Market value analysis
  - TO STASH: Good for alt characters?
  - WHY explanations showing calculation breakdown

### BiS Search & Build Priorities
- **[BiS Search Guide](features/BIS_SEARCH_GUIDE.md)** - Find optimal gear upgrades
  - Build priority system (Critical/Important/Nice-to-have)
  - Affix tier calculator with ilvl requirements
  - Guide gear extraction from reference builds

### Item Comparison & DPS Impact
- **[Item Comparison Guide](features/ITEM_COMPARISON_GUIDE.md)** - Side-by-side item comparison
  - Compare two items to see stat differences
  - DPS impact estimation based on your PoB build
  - Upgrade/downgrade/sidegrade verdicts

### Keyboard Shortcuts
- **[Keyboard Shortcuts](features/KEYBOARD_SHORTCUTS.md)** - All available shortcuts
  - F1 for shortcuts reference
  - Ctrl+K for command palette

### PoE2 Support
- Rune socket parsing and rune data (28+ runes across tiers)
- Charm modifier data with tier progression
- PoE2 Trade API stat ID mappings
- New item types: Focus, Crossbow, Flail, Spear, Warstaff, Charm, Soulcore

---

## External Integrations

- **[Maxroll Build Integration](integration/MAXROLL_INTEGRATION.md)** - Import and compare builds from Maxroll.gg

---

## Troubleshooting

- [Parser Issues](troubleshooting/PARSER_ISSUES.md) - "Unknown Item" problems
- [Unknown Item](troubleshooting/UNKNOWN_ITEM.md) - Detailed troubleshooting
- [Item Class Bug](troubleshooting/ITEM_CLASS_BUG.md) - Fixed: PoE item format issue

---

## For Developers

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup and guidelines.
