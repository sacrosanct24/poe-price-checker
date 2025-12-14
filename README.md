<p align="center">
  <img src="assets/banner.png" alt="PoE Price Checker" width="600">
</p>

<p align="center">
  <strong>A modern multi-source economy tool for Path of Exile</strong>
</p>

<p align="center">
  <a href="#download"><img src="https://img.shields.io/badge/Download-Windows-blue?style=for-the-badge&logo=windows" alt="Download"></a>
  <a href="#features"><img src="https://img.shields.io/badge/PoE1%20%2B%20PoE2-Supported-orange?style=for-the-badge" alt="PoE1 + PoE2"></a>
</p>

<p align="center">
  <a href="https://github.com/sacrosanct24/poe-price-checker/actions/workflows/python-package.yml"><img src="https://github.com/sacrosanct24/poe-price-checker/actions/workflows/python-package.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/sacrosanct24/poe-price-checker"><img src="https://codecov.io/gh/sacrosanct24/poe-price-checker/graph/badge.svg" alt="Coverage"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt6-41cd52?logo=qt" alt="PyQt6">
  <img src="https://img.shields.io/github/license/sacrosanct24/poe-price-checker" alt="License">
</p>

---

## Download

**Windows users:** Download the latest release and run - no Python installation required!

| Platform | Download | Size |
|----------|----------|------|
| Windows | [PoEPriceChecker.zip](https://github.com/sacrosanct24/poe-price-checker/releases/latest) | ~120 MB |
| macOS | Build from source (see below) | - |
| Linux | Build from source (see below) | - |

> **Note:** The Windows build includes everything needed to run the application. Just extract and double-click `PoEPriceChecker.exe`.

---

## Features

### Multi-Source Pricing
- **PoE Ninja** integration for real-time pricing
- **poe.watch** as secondary data source
- **Top 20 Price Rankings** by category with trend analysis
- Plugin system for custom pricing sources

### Smart Item Parsing
- Detects rarity, mods, sockets, influences, and more
- Supports both **PoE1** and **PoE2** item formats
- Paste from clipboard, instant results

### Path of Building Integration
- Import builds from PoB paste codes
- **Build-aware item evaluation** - see effective values based on your skill tree
- Character profile management with equipped item viewing
- Upgrade checking against your current gear

### Build Manager (Ctrl+B)
- Unified build profile management
- Save and organize multiple PoB builds with filtering
- Categorize builds (League Starter, Mapper, Bosser, etc.)
- Equipment tab with item tree and price check integration

### Item Planning Hub (Ctrl+U)
- Unified upgrade finder and BiS search
- Smart gear recommendations within your budget
- Queries Trade API for items matching your build priorities
- BiS Guide tab showing ideal affixes per slot

### Cross-Build Intelligence
- **"What builds want this item?"** analysis
- 20+ meta build archetypes (RF Jugg, Lightning Arrow, Boneshatter, etc.)
- Match percentage showing how well item fits each archetype
- Helps identify items valuable for trade or alt characters

### Unified Verdict Engine
- **Single-click comprehensive evaluation**
- FOR YOU: Is this an upgrade for your build?
- TO SELL: Market value and demand analysis
- TO STASH: Good for your alt characters?
- WHY explanations showing calculation breakdown

### AI Item Analysis
- **Ask AI about any item** via right-click context menu
- Supports **Google Gemini** (free tier available), **Claude**, and **OpenAI**
- **Build-aware analysis** - AI knows your PoB build context when evaluating items
- Get detailed explanations of item value, mod synergies, and upgrade recommendations

### Stash Visualization
- Visual grid view of stash tab contents
- Heatmap overlay showing item values
- Click to inspect, double-click to price check

### Loot Tracking
- Zone detection from Client.txt (map entry/exit)
- Stash diffing to detect new items between map runs
- Session management with duration, drop counts, and chaos/hour stats
- Loot Dashboard with live analytics

### Modern Interface
- Dark theme with PoE-style colors
- **Rare Item Evaluator** - scores items 0-100 with tier badges
- Item Inspector with mod breakdown
- Sales tracking and history
- Right-click menus for quick actions
- Session tabs for multiple price-checking workflows

### 3-Screen Architecture
The application is organized into three focused screens:

| Screen | Shortcut | Purpose |
|--------|----------|---------|
| **Item Evaluator** | Ctrl+1 | Price checking, session tabs, pinned items, price rankings |
| **AI Advisor** | Ctrl+2 | Build optimization, upgrade analysis, PoB integration |
| **Daytrader** | Ctrl+3 | Sales tracking, loot tracking, market analysis, stash viewer |

Switch screens via the top navigation bar or keyboard shortcuts.

---

## Quick Start

### Option 1: Download (Windows)
1. Download from [Releases](https://github.com/sacrosanct24/poe-price-checker/releases/latest)
2. Extract the zip file
3. Run `PoEPriceChecker.exe`

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/sacrosanct24/poe-price-checker.git
cd poe-price-checker

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Build Your Own Executable

```bash
python build.py
# Output: dist/PoEPriceChecker/
```

---

## Usage

1. **Copy an item** from Path of Exile (Ctrl+C on item)
2. **Paste into the app** (Ctrl+V or click Paste)
3. **View prices** from multiple sources instantly

### Pro Tips
- Use the **Build Manager** (Ctrl+B) to import your build and check upgrades
- Use the **Item Planning Hub** (Ctrl+U) to find upgrades within your budget
- Enable **Price Rankings** to see top items by category
- Right-click results for additional options (copy, record sale, ask AI)
- Configure AI in Settings > AI tab (Gemini offers a free tier)

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Keyboard Shortcuts](docs/features/KEYBOARD_SHORTCUTS.md) | All available shortcuts |
| [BiS Search Guide](docs/features/BIS_SEARCH_GUIDE.md) | Find optimal gear upgrades |
| [Item Comparison](docs/features/ITEM_COMPARISON_GUIDE.md) | Compare items side-by-side |
| [Troubleshooting](docs/troubleshooting/) | Common issues and fixes |

For developers:
| Guide | Description |
|-------|-------------|
| [Development Guide](docs/development/DEVELOPMENT_GUIDE.md) | Architecture & code style |
| [Plugin Spec](docs/development/PLUGIN_SPEC.md) | Create custom plugins |
| [Testing Guide](docs/testing/TESTING_GUIDE.md) | Running & writing tests |

---

## Project Structure

```
poe-price-checker/
├── core/           # Parsing, pricing, database services
├── gui_qt/         # PyQt6 interface
├── data_sources/   # PoE Ninja, poe.watch, AI providers
├── plugins/        # Custom pricing sources
├── tests/          # Unit & integration tests
└── docs/           # Documentation
```

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT License](LICENSE) - see LICENSE file for details.

---

<p align="center">
  <sub>Not affiliated with Grinding Gear Games. Path of Exile is a trademark of Grinding Gear Games.</sub>
</p>
