# 📦 PoE Price Checker

*A modern multi-source economy tool for Path of Exile (PoE1 + PoE2)*

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen?logo=pytest)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Continue](https://img.shields.io/badge/AI-Continue%20enabled-purple?logo=ai)

PoE Price Checker is a fully-featured desktop application for pricing Path of Exile items using **multiple sources**, a **modern parser**, **sales tracking**, and a **plugin system**.
Designed as an **over-engineered portfolio project**, it showcases clean architecture, strong testing, and extensibility.

---

# ✨ Features

### 🔍 Multi-Source Pricing

* PoE Ninja
* Derived sources (undercut / heuristic pricing)
* Plugin system for custom pricing sources

### 🧠 Smart Item Parsing

* Detects rarity, mods, sockets, influences, tags, and more
* Supports PoE1 and PoE2 item formats

### 🪄 Modern GUI (Tkinter)

* Paste item → auto-parse → price instantly
* Item Inspector sidebar
* Right-click: copy row, open trade URL, copy TSV
* Sample-item buttons for development

### 💾 Persistent Database

* Checked item history
* Sales tracking (listing → sold)
* Price snapshot history
* Plugin state/config

### 🧩 Plugin System

* Add your own pricing sources
* Add hooks that run after parse or after pricing
* Simple Python module interface

---

# 🚀 Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the application

```bash
python poe_price_checker.py
```

Runs with GUI on all major OSes.

### 3. Run the full test suite

```bash
pytest
```

### 4. (Optional) Setup Continue AI Assistant in PyCharm

This project includes [Continue](https://continue.dev) configuration for AI-assisted development.

👉 See **[PYCHARM_SETUP.md](docs/PYCHARM_SETUP.md)** for setup instructions.

---

# 📚 Documentation

All documentation is organized in the `docs/` directory:

## Development
- **[Development Guide](docs/development/DEVELOPMENT_GUIDE.md)** - Architecture & development practices
- **[PyCharm Setup](docs/development/PYCHARM_SETUP.md)** - AI assistant integration (Continue)
- **[Plugin Spec](docs/development/PLUGIN_SPEC.md)** - Plugin API documentation

## Testing
- **[Test Suite Guide](docs/testing/TEST_SUITE_GUIDE.md)** - Running and writing tests
- **[Testing History](docs/testing/TESTING_HISTORY.md)** - Test suite evolution (109 → 163 tests)
- **[Coverage Gaps](docs/testing/COVERAGE_GAPS.md)** - Areas needing more tests

## MCP Integration (AI Assistant)
- **[MCP Integration](docs/mcp/MCP_INTEGRATION.md)** - Complete guide to AI integration
- **[Quick Start](docs/mcp/QUICK_START.md)** - 5-minute setup
- **[Why MCP?](docs/mcp/WHY_MCP.md)** - Benefits and analysis

## Troubleshooting
- **[Parser Issues](docs/troubleshooting/PARSER_ISSUES.md)** - "Unknown Item" problems
- **[Item Class Bug](docs/troubleshooting/ITEM_CLASS_BUG.md)** - Fixed: PoE item format

## Project Management
- **[Roadmap](docs/roadmap.md)** - Future features
- **[Context](docs/Context.md)** - Design decisions
- **[Code Review](docs/code_review.md)** - Code quality notes

---

# 🗂️ Repository Structure

```text
poe-price-checker/
│
├── core/                # AppContext, database, parsing, pricing services
├── gui/                 # Tkinter GUI
├── data_sources/        # PoE Ninja + framework for more APIs
├── plugins/             # Third-party plugins & examples
│
├── docs/                # All documentation
├── tests/               # Unit + integration tests
│
├── .continue/           # Continue AI assistant configuration
└── poe_price_checker.py # Application entrypoint
```

---

# 🧩 Want to Create Plugins?

The plugin system is intentionally simple:

* Drop a Python file into `plugins/`
* Implement `register_plugin(...)`
* Register pricing sources or hooks

See:
👉 **`docs/PLUGIN_SPEC.md`**

---

# 🛠️ Contributing

Pull requests, bug reports, and plugin ideas are welcome.

When contributing:

* Follow project structure
* Add/update tests
* Keep PRs focused & small
* Update docs where appropriate

---

# 📄 License

This project is licensed under the **MIT License**.
