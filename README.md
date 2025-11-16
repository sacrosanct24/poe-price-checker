# PoE Price Checker

> **A comprehensive item price checker for Path of Exile 1 & 2 with plugin system and sales tracking**

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

![PoE Price Checker Demo](docs/images/demo-screenshot.png)
*Screenshot coming soon*

## 🎯 Overview

PoE Price Checker is an over-engineered, portfolio-worthy economy tool that helps Path of Exile players quickly price check items from both PoE1 and PoE2. Built with a modular architecture, plugin system, and comprehensive data persistence, this project demonstrates professional Python development practices while solving real trading challenges.

### Key Features

- ✅ **Dual Game Support** - Seamless switching between PoE1 and PoE2
- ✅ **Multi-Source Pricing** - Integrates with poe.ninja, poe2scout, and official trade API
- ✅ **Smart Item Parser** - Handles currency, uniques, rares, maps, and more
- ✅ **Auto-Paste Detection** - Automatically checks prices when you paste items
- ✅ **SQLite Database** - Tracks price history, sales, and checked items
- 🚧 **Plugin System** - Extensible architecture for custom features
- 🚧 **Sales Tracking** - Learn optimal pricing from your trade history
- 🚧 **Meta Analysis** - Evaluate items based on popular build requirements
- 🚧 **Web Dashboard** - Access your data from any device

*Legend: ✅ Implemented | 🚧 In Progress | 📋 Planned*

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- Windows (primary), Linux/Mac (untested but should work)
- Path of Exile account (for API features)

### Installation

```bash
# Clone the repository
git clone https://github.com/sacrosanct24/poe-price-checker.git
cd poe-price-checker

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Basic Usage

1. **Launch the app**: `python main.py`
2. **Copy an item** in Path of Exile (hover over item, press `Ctrl+C`)
3. **Paste into the app** (`Ctrl+V` in the input box)
4. **View prices** - Results appear automatically with chaos/divine values
5. **Filter results** - Set minimum chaos value or toggle vendor items

## 📖 Documentation

- **[Context Document](Context.md)** - Complete technical reference for LLM-assisted development
- **[Development Roadmap](roadmap.md)** - Feature timeline and architecture decisions
- **[API Documentation](docs/api-reference.md)** - *(Coming soon)*
- **[Plugin Development Guide](docs/plugin-guide.md)** - *(Coming soon)*

## 🏗️ Architecture

```
poe-price-checker/
├── core/                    # Core application logic
│   ├── config.py           # JSON-based configuration
│   ├── database.py         # SQLite persistence layer
│   ├── item_parser.py      # Item text parsing engine
│   └── game_version.py     # PoE1/PoE2 version management
├── data_sources/           # External API integrations
│   ├── base_api.py         # Rate limiting + caching base class
│   ├── pricing/
│   │   ├── poe_ninja.py    # PoE1 pricing via poe.ninja
│   │   └── poe2_scout.py   # PoE2 pricing (planned)
│   └── official/           # GGG official APIs (planned)
├── gui/                    # Tkinter user interface
│   └── main_window.py      # Main application window
├── plugins/                # Plugin system (in development)
└── tests/                  # Test suite (planned)
```

### Design Principles

- **Adapter Pattern** - Unified interface for multiple pricing APIs
- **Plugin Architecture** - Extensible without modifying core code
- **Rate Limiting** - Respects API limits with exponential backoff
- **Caching** - Reduces API calls with TTL-based response cache
- **Database Migrations** - Schema versioning for smooth upgrades

## 🔌 Plugin System *(In Development)*

The plugin system allows community contributions without modifying core code:

```python
from plugins.base_plugin import PluginBase

class PriceAlertPlugin(PluginBase):
    def on_item_checked(self, item_data):
        if item_data['chaos_value'] > self.config['threshold']:
            self.send_discord_webhook(item_data)
```

### Example Plugins (Planned)

- **Price Alerts** - Discord/Telegram notifications for valuable drops
- **Export Tools** - CSV, Excel, Google Sheets integration
- **Statistics Dashboard** - Profit/loss tracking with charts
- **Build Analyzer** - Match items to meta PoB builds

## 💾 Database Schema

```sql
-- Checked items history
CREATE TABLE checked_items (
    id INTEGER PRIMARY KEY,
    game_version TEXT,
    league TEXT,
    item_name TEXT,
    chaos_value REAL,
    stack_size INTEGER,
    checked_at TIMESTAMP
);

-- Sales tracking
CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    item_name TEXT,
    listed_price_chaos REAL,
    sold_at TIMESTAMP,
    time_to_sale_hours REAL
);

-- Price history for trend analysis
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY,
    item_name TEXT,
    chaos_value REAL,
    recorded_at TIMESTAMP
);
```

## 🛠️ Development

### Running Tests

```bash
pytest tests/
pytest --cov=core --cov-report=html  # With coverage
```

### Code Style

This project uses:
- **Black** for formatting
- **Ruff** for linting
- **mypy** for type checking

```bash
black .
ruff check .
mypy core/ data_sources/
```

### Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-plugin`)
3. Commit changes (`git commit -m 'Add amazing plugin'`)
4. Push to branch (`git push origin feature/amazing-plugin`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📊 Roadmap

### Phase 1: Foundation ✅ (Complete)
- ✅ Core item parser
- ✅ poe.ninja integration
- ✅ SQLite database
- ✅ GUI with auto-paste
- ✅ Config persistence

### Phase 2: Plugin System 🚧 (Current)
- 🚧 Plugin manager
- 🚧 Example plugins (alerts, export, stats)
- 📋 Plugin marketplace

### Phase 3: Sales Tracking 📋
- 📋 Sale recording UI
- 📋 Price learning algorithm
- 📋 Optimal pricing suggestions

### Phase 4: Meta Analysis 📋
- 📋 PoB parser integration
- 📋 Build requirement database
- 📋 Smart item scoring

See [roadmap.md](roadmap.md) for complete timeline (30 weeks / 7-8 months).

## 🔗 API Rate Limits & Etiquette

This tool respects API rate limits:

- **poe.ninja**: ~1 request per 3 seconds (community standard)
- **GGG Official API**: Dynamic limits via `X-Rate-Limit-*` headers
- **poe2scout**: Include User-Agent with email for high usage

All API clients implement:
- Exponential backoff on 429 errors
- Response caching (1 hour TTL)
- Request logging for debugging

## 📝 Configuration

Configuration stored in `~/.poe_price_checker/config.json`:

```json
{
  "current_game": "poe1",
  "games": {
    "poe1": {
      "league": "Keepers of the Flame",
      "divine_chaos_rate": 317.2
    }
  },
  "ui": {
    "min_value_chaos": 0.0,
    "show_vendor_items": true,
    "window_width": 1200,
    "window_height": 800
  }
}
```

## 🐛 Known Issues

- **Chaos Orb matching** - Occasional quirks in currency detection (fallback to 1c works correctly)
- **Large paste operations** - Slight CPU spike during bulk parsing (future: threading)
- **Dark mode** - Pending full theme system implementation

See [Issues](https://github.com/sacrosanct24/poe-price-checker/issues) for complete list.

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Path of Exile** by Grinding Gear Games
- **poe.ninja** for providing free economy data
- **poe2scout** for PoE2 early access pricing
- **Community** - All the PoE tool developers who came before

## 📧 Contact

- **Author**: Todd (sacrosanct24)
- **GitHub**: [@sacrosanct24](https://github.com/sacrosanct24)
- **PoE Account**: sacrosanct24
- **Main Character**: TripSevens (Level 90 RF Chieftain)

## 🎓 Portfolio Notes

This project demonstrates:
- **API Integration** - Multiple sources with rate limiting and caching
- **Database Design** - SQLite with migrations and versioning
- **Plugin Architecture** - ABC-based extensibility
- **GUI Development** - Tkinter with proper event handling
- **Error Handling** - Exponential backoff, retry logic
- **Testing Practices** - Unit and integration tests
- **Documentation** - Context-driven development with LLMs
- **Git Workflow** - Feature branches, conventional commits

Built as a learning project to showcase professional Python development while solving real Path of Exile trading challenges.

---

**Status**: Active Development (v0.2.0-dev) | **Started**: November 2025 | **Language**: Python 3.12

⚡ *Making PoE trading less painful, one divine orb at a time* ⚡
