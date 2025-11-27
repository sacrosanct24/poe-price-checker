# PoE Price Checker Documentation

**Quick Navigation** - All essential documentation for development and usage.

---

## 📚 Core References

### Game Knowledge
- **[Rare Item Valuation Guide](RARE_ITEM_VALUATION.md)** ⭐ - Comprehensive guide to PoE rare item economy
- [PoE API Reference](POE_API_REFERENCE.md) - Official trade API docs
- [PoE.Watch API Reference](POEWATCH_API_REFERENCE.md) - Alternative pricing API

### Project Planning
- [Roadmap](roadmap.md) - Future features and plans

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

---

## 🛠️ Development

### Setup & Architecture
- **[Development Guide](development/DEVELOPMENT_GUIDE.md)** ⭐ - Core architecture and practices
- [PyCharm Setup](development/PYCHARM_SETUP.md) - IDE configuration with Continue AI
- [Context](development/Context.md) - Design decisions and rationale
- [Code Review](development/code_review.md) - Code quality notes

### Data Integration
- **[Cargo API Guide](development/CARGO_API_GUIDE.md)** - PoE Wiki Cargo API for mod/item data
- [Continuation Guide](development/CONTINUATION.md) - Session continuation notes

### Plugin System
- [Plugin Specification](development/PLUGIN_SPEC.md) - How to create plugins

### Stash Scanner (Future)
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

## 🔧 Troubleshooting

- [Parser Issues](troubleshooting/PARSER_ISSUES.md) - "Unknown Item" problems
- [Unknown Item](troubleshooting/UNKNOWN_ITEM.md) - Detailed troubleshooting
- [Item Class Bug](troubleshooting/ITEM_CLASS_BUG.md) - Fixed: PoE item format issue

---

## 📂 Documentation Structure

```
docs/
├── INDEX.md (this file)
├── RARE_ITEM_VALUATION.md ⭐⭐⭐ (Essential reference)
├── POE_API_REFERENCE.md
├── POEWATCH_API_REFERENCE.md
├── roadmap.md
│
├── features/          # User guides
├── development/       # Dev guides & architecture
├── testing/          # Test documentation
├── mcp/              # AI assistant integration
└── troubleshooting/  # Problem solving
```

---

**⭐ = Most Important Documents**
