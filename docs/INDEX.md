---
title: Documentation Index
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
---

# PoE Price Checker Documentation

**Quick Navigation** - All essential documentation for development and usage.

---

## 🗺️ Roadmap

- **[Feature Roadmap](ROADMAP.md)** ⭐ - Planned features and development priorities

---

## 📚 Core References

### Game Knowledge
- **[Rare Item Valuation Guide](RARE_ITEM_VALUATION.md)** ⭐ - Comprehensive guide to PoE rare item economy
- [PoE API Reference](POE_API_REFERENCE.md) - Official trade API docs
- [PoE.Watch API Reference](POEWATCH_API_REFERENCE.md) - Alternative pricing API

---

## 🎮 Features & User Guides

### Multi-Source Pricing
- [Quick Reference](features/QUICK_REFERENCE.md) - Using multi-source pricing
- [How to See Multi-Source Pricing](features/HOW_TO_SEE_MULTI_SOURCE_PRICING.md) - Detailed walkthrough

### Rare Item Evaluator
- **[Rare Evaluator Quick Start](features/RARE_EVALUATOR_QUICK_START.md)** ⭐ - Get started quickly
- [GUI Integration Guide](features/GUI_INTEGRATION_GUIDE.md) - How evaluation integrates with GUI
- [Integration Guide](features/INTEGRATION_GUIDE.md) - Meta integration and build archetypes

### BiS Search & Build Priorities
- **[BiS Search Guide](features/BIS_SEARCH_GUIDE.md)** ⭐ - Find optimal gear upgrades
  - Build priority system (Critical/Important/Nice-to-have)
  - Affix tier calculator with ilvl requirements
  - Guide gear extraction from reference builds

### Item Comparison & DPS Impact
- **[Item Comparison Guide](features/ITEM_COMPARISON_GUIDE.md)** ⭐ - Side-by-side item comparison
  - Compare two items to see stat differences
  - DPS impact estimation based on your PoB build
  - Upgrade/downgrade/sidegrade verdicts

### Keyboard Shortcuts
- **[Keyboard Shortcuts](features/KEYBOARD_SHORTCUTS.md)** - All available shortcuts
  - F1 for shortcuts reference
  - Ctrl+K for command palette
  - Category-organized shortcuts (General, Price Check, Build, Navigation, View)

### PoE2 Support
- Rune socket parsing and rune data (28+ runes across tiers)
- Charm modifier data with tier progression
- PoE2 Trade API stat ID mappings
- Pseudo stat aggregation (resistances, life, attributes)
- Goodness score calculations for mod roll quality
- New item types: Focus, Crossbow, Flail, Spear, Warstaff, Charm, Soulcore

---

## 🛠️ Development

### Setup & Architecture
- **[Development Guide](development/DEVELOPMENT_GUIDE.md)** ⭐ - Core architecture and practices

### Data Integration
- **[Cargo API Guide](development/CARGO_API_GUIDE.md)** - PoE Wiki Cargo API for mod/item data
- **[Data Sources Guide](development/DATA_SOURCES_GUIDE.md)** - Authoritative data source reference

### Plugin System
- [Plugin Specification](development/PLUGIN_SPEC.md) - How to create plugins

### Stash Scanner
- [Stash Scanner Setup](development/STASH_SCANNER_SETUP.md) - Setup instructions
- [Stash Scanner Checklist](development/STASH_SCANNER_CHECKLIST.md) - Implementation checklist

---

## 🧪 Testing

- **[Test Suite Guide](testing/TEST_SUITE_GUIDE.md)** ⭐ - Running and writing tests
- [Testing Guide](testing/TESTING_GUIDE.md) - General testing practices
- [Coverage Gaps](testing/COVERAGE_GAPS.md) - Areas needing more tests

---

## 🔌 MCP Integration (AI Assistant)

### Setup Guides
- **[Quick Start](mcp/QUICK_START.md)** ⭐ - Get MCP running in 5 minutes
- [Setup Guide](mcp/SETUP_GUIDE.md) - Detailed setup instructions
- [Claude Setup](mcp/CLAUDE_SETUP.md) - Configure Claude Desktop
- [MCP without Node.js](mcp/MCP_NO_NODEJS.md) - Python-only setup

### Reference
- [MCP Integration](mcp/MCP_INTEGRATION.md) - Complete integration documentation
- [Why MCP?](mcp/WHY_MCP.md) - Benefits and analysis

---

## 🔗 External Integrations

- **[Maxroll Build Integration](integration/MAXROLL_INTEGRATION.md)** - Import and compare builds from Maxroll.gg

---

## 🔧 Troubleshooting

- [Parser Issues](troubleshooting/PARSER_ISSUES.md) - "Unknown Item" problems
- [Unknown Item](troubleshooting/UNKNOWN_ITEM.md) - Detailed troubleshooting
- [Item Class Bug](troubleshooting/ITEM_CLASS_BUG.md) - Fixed: PoE item format issue

---

## 📋 Documentation Management

- **[Documentation Manifest](DOCS_MANIFEST.md)** - Registry of all docs with status tracking

---

## 📂 Documentation Structure

```
docs/
├── INDEX.md                    # This file
├── DOCS_MANIFEST.md            # Documentation registry
├── RARE_ITEM_VALUATION.md      # Essential rare item reference ⭐
├── POE_API_REFERENCE.md        # Official trade API
├── POEWATCH_API_REFERENCE.md   # Alternative pricing API
│
├── development/                # Dev guides & architecture
├── features/                   # User guides
├── integration/                # External service integrations
├── mcp/                        # AI assistant integration
├── testing/                    # Test documentation
└── troubleshooting/            # Problem solving
```

---

**⭐ = Most Important Documents**
