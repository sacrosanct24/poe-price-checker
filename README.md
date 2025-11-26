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
  <img src="https://img.shields.io/badge/Python-3.12+-3776ab?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Tests-671%20passing-brightgreen?logo=pytest" alt="Tests">
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

### Maxroll Integration
- Import builds directly from Maxroll.gg guides
- Compare against meta builds

### Modern Interface
- Dark theme with PoE-style colors
- **Rare Item Evaluator** - scores items 0-100 with tier badges
- Item Inspector with mod breakdown
- Sales tracking and history
- Right-click menus for quick actions

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
- Use the **PoB Panel** to import your build and check upgrades
- Enable **Price Rankings** to see top items by category
- Right-click results for additional options (copy, record sale, explain price)

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Development Guide](docs/development/DEVELOPMENT_GUIDE.md) | Architecture & code style |
| [Plugin Spec](docs/development/PLUGIN_SPEC.md) | Create custom plugins |
| [Test Suite Guide](docs/testing/TEST_SUITE_GUIDE.md) | Running & writing tests |
| [Maxroll Integration](docs/integration/MAXROLL_INTEGRATION.md) | Import builds from Maxroll |

---

## Project Structure

```
poe-price-checker/
├── core/           # Parsing, pricing, database services
├── gui_qt/         # PyQt6 interface (default)
├── data_sources/   # PoE Ninja, poe.watch, and more
├── plugins/        # Custom pricing sources
├── tests/          # 671+ unit & integration tests
└── docs/           # Documentation
```

---

## Contributing

Contributions are welcome! Please:
- Follow the existing code style
- Add tests for new features
- Keep PRs focused and small

---

## License

[MIT License](LICENSE) - see LICENSE file for details.

---

<p align="center">
  <sub>Not affiliated with Grinding Gear Games. Path of Exile is a trademark of Grinding Gear Games.</sub>
</p>
