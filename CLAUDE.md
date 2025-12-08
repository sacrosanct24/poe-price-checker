# Claude Code Project Context

This file provides essential context for AI assistants working on this codebase.

## Project Overview

**PoE Price Checker** is a PyQt6 desktop application for Path of Exile (PoE1 & PoE2) that provides:
- Multi-source price checking (PoE Ninja, poe.watch, Trade API)
- Build optimization via Path of Building integration
- AI-powered upgrade recommendations
- Sales tracking and economy analytics

**Current Version**: 1.6.0 (3-Screen Architecture)

## Architecture

### Core Principles
1. **Separation of Concerns**: `core/` (business logic) → `gui_qt/` (presentation) → `data_sources/` (external APIs)
2. **Dependency Injection**: Use `AppContext` for service instantiation
3. **No global state**: Services injected via constructors

### Module Structure
```
core/           # Business logic - NO UI dependencies
├── app_context.py      # DI factory - entry point for services
├── config.py           # User configuration management
├── database.py         # SQLAlchemy/SQLite persistence
├── item_parser.py      # PoE item text parsing
├── price_service.py    # Single-source pricing
├── price_integrator.py # Multi-source aggregation
└── ...

gui_qt/         # PyQt6 presentation layer
├── main_window.py      # Application shell
├── screens/            # Main screens (Ctrl+1/2/3)
├── widgets/            # Reusable components
├── dialogs/            # Modal dialogs
└── services/           # GUI services (window_manager, etc.)

data_sources/   # External API clients
├── base_api.py         # Base with rate limiting, caching, retry
├── poe_ninja_client.py # Primary pricing source
├── ai/                 # AI providers (gemini, claude, openai, etc.)
└── pricing/            # Pricing source adapters
```

### Key Patterns

**AppContext Usage**:
```python
from core.app_context import AppContext

ctx = AppContext()
price_service = ctx.get_price_service()
database = ctx.get_database()
```

**PyQt6 Signal/Slot**:
```python
class MyWidget(QWidget):
    data_loaded = pyqtSignal(dict)  # Define signals as class attributes

    def __init__(self):
        super().__init__()
        self.data_loaded.connect(self._on_data_loaded)  # Connect in init
```

**Worker Thread Pattern** (for async operations):
```python
from gui_qt.workers.base_worker import BaseWorker

class PriceWorker(BaseWorker):
    result_ready = pyqtSignal(dict)

    def run(self):
        result = self.fetch_prices()
        self.result_ready.emit(result)
```

## Testing

### Quick Commands
```bash
# All tests
pytest tests/ -v --timeout=120

# Unit tests only (fast)
pytest tests/unit/ -v

# Specific module
pytest tests/unit/core/test_item_parser.py -v

# With coverage
pytest tests/ --cov=core --cov-report=term-missing

# Qt tests (needs offscreen)
QT_QPA_PLATFORM=offscreen pytest tests/unit/gui_qt/ -v
```

### Test Markers
- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Database/API tests
- `@pytest.mark.slow` - Skip with `-m "not slow"`

### Critical Test Fixtures
- `qapp` (from pytest-qt) - Required for all Qt widget tests
- `tmp_path` - Temporary directory for file tests
- `mock_config` - Pre-configured Config mock

### Common Pitfalls
1. **Qt singletons**: Reset in `conftest.py` between tests
2. **Time-dependent code**: Mock `time.sleep`, `datetime.now()`
3. **File paths**: Use `tmp_path` fixture, not hardcoded paths

## Code Style

### Standards
- Python 3.10+ with type hints
- PEP 8 compliant (flake8)
- Max line length: 127 characters
- Google-style docstrings

### Type Hints
```python
from typing import Optional, List, Dict
from dataclasses import dataclass

def get_price(item: str, league: Optional[str] = None) -> Dict[str, float]:
    ...
```

### Pre-commit Checks
```bash
pre-commit run --all-files
```

Runs: flake8, isort, mypy, trailing whitespace, YAML validation

## Common Tasks

### Adding a New Pricing Source
1. Create adapter in `data_sources/pricing/`
2. Implement `BasePricingSource` interface
3. Register in `price_integrator.py`
4. Add tests in `tests/unit/data_sources/`

### Adding a New Qt Widget
1. Create in `gui_qt/widgets/`
2. Follow existing widget patterns (signals, init structure)
3. Add to parent screen/dialog
4. Test with `pytest-qt` fixtures

### Modifying Item Parser
1. Update `core/item_parser.py`
2. Add test cases with real item examples
3. Test edge cases (corrupted, influenced, etc.)

## Configuration

### User Config Location
- `~/.poe_price_checker/config.json`

### Environment Variables
- `QT_QPA_PLATFORM=offscreen` - Headless Qt testing
- `POE_DISABLE_PLUGIN_AUTOLOAD=1` - Disable plugins in tests
- `RETRY_MAX_SLEEP=0.001` - Fast retries in tests

## Known Technical Debt

1. **Gradual typing**: Not all modules have complete type hints
2. **Test coverage**: ~60%, goal is 80%
3. **Some large files**: `main_window.py`, `item_parser.py` could be split

## AI Provider Integration

Supported providers in `data_sources/ai/`:
- Google Gemini (free tier available)
- Anthropic Claude
- OpenAI GPT
- Groq Cloud
- xAI Grok
- Ollama (local)

API keys stored encrypted in user config.

## MCP Server

The `mcp_poe_server.py` exposes tools for AI assistants:
- `parse_item` - Parse PoE item text
- `get_item_price` - Database price lookup
- `get_sales_summary` - Sales analytics
- `list_characters` - PoB character profiles
- `suggest_upgrades` - Upgrade recommendations
- `run_tests` - Execute pytest with options
- `run_linter` - Code quality checks
- `run_security_scan` - Security analysis

## Persona-Based Review System

This project uses specialized reviewer personas for comprehensive code review.
See `.claude/personas/` for detailed persona definitions.

| Persona | Focus | Command |
|---------|-------|---------|
| Security Auditor | OWASP, secrets, injection | `/review-security` |
| Performance Engineer | Complexity, async, memory | `/review-performance` |
| Architecture Guardian | SOLID, patterns, layers | `/review-architecture` |
| Test Strategist | Coverage, test quality | `/review-tests` |
| Accessibility Champion | A11y, keyboard, screen reader | `/review-accessibility` |
| Documentation Curator | Docstrings, ADRs | `/review-docs` |

### Using Personas
```bash
# Single review
/review-security core/item_parser.py

# Full multi-persona audit
/audit-full core/
```

## Quality Gates

All code must pass quality gates before merge. See `docs/development/QUALITY_GATES.md`.

Key gates:
1. **Automated**: flake8, isort, mypy, pytest, bandit
2. **Coverage**: ≥70% for core/, ≥60% overall
3. **Persona Reviews**: Security, Architecture, Tests

## Quick Reference

| Task | Command |
|------|---------|
| Run app | `python main.py` |
| Run tests | `pytest tests/ -v` |
| Run API | `python run_api.py` |
| Build exe | `python build.py` |
| Lint | `flake8 core/ gui_qt/` |
| Type check | `mypy --config-file=mypy.ini` |
| Format imports | `isort core/ gui_qt/` |
| Security scan | `bandit -r core/ -ll` |
| Pre-PR check | `/check-pr` |
| Full audit | `/audit-full <path>` |
| Update meta builds | `/update-meta-builds` |

## Meta Builds Knowledge

The project tracks current meta builds to improve item evaluation accuracy:
- **Location**: `data/meta_builds/poe1/` and `data/meta_builds/poe2/`
- **Update schedule**: Pre-league, then weekly during league
- **Integration**: `core/meta_analyzer.py` loads weights for `price_integrator.py`

See `data/meta_builds/README.md` for schema and update procedures.

## Further Reading

- **Quality Gates**: `docs/development/QUALITY_GATES.md`
- **LLM Workflow**: `docs/development/LLM_DEVELOPMENT_WORKFLOW.md`
- **PoE Dev Reference**: `docs/development/POE_DEVELOPMENT_REFERENCE.md`
- **Personas**: `.claude/personas/README.md`
- **PoE Glossary**: `.claude/personas/poe-glossary.md`
- **Meta Builds**: `data/meta_builds/README.md`
- **ADRs**: `docs/decisions/README.md`
