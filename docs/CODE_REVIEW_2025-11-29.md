# Deep Code Review - PoE Price Checker
**Date:** 2025-11-29
**Reviewer:** Principal Engineer Review
**Scope:** Core architecture, elegance, and performance

---

## Executive Summary

The codebase demonstrates solid fundamentals with good use of type hints, dataclasses, and Python 3.12 features. However, there are significant opportunities for improvement in architectural separation, performance optimization, and code elegance. The most pressing issue is the monolithic `main_window.py` (2001 lines) which violates single-responsibility principle.

**Priority Levels:**
- 🔴 **Critical** - Should address before adding features
- 🟡 **Important** - Address in next development cycle
- 🟢 **Nice-to-have** - Consider when touching related code

---

## 1. Architectural Issues

### 🔴 1.1 Monolithic Main Window (`gui_qt/main_window.py`)

**Problem:** The `PriceCheckerWindow` class is 2001 lines with ~15+ responsibilities:
- Menu bar creation (~400 lines)
- Worker thread management
- Price checking logic
- Window caching (10+ child windows)
- History management
- Session coordination
- Status bar updates
- Theme handling
- Shortcut management

**Impact:**
- Difficult to test individual components
- High cognitive load for maintenance
- Merge conflicts when multiple features touch this file
- Violates Open/Closed principle

**Recommendations:**

```python
# BEFORE: Everything in PriceCheckerWindow
class PriceCheckerWindow(QMainWindow):
    def _create_menu_bar(self):  # 400 lines of menu creation
        ...
    def _do_price_check(self):  # Business logic mixed with UI
        ...

# AFTER: Extracted components
# gui_qt/menus/menu_builder.py
class MenuBuilder:
    """Builds menu bar from declarative configuration."""
    def __init__(self, window: QMainWindow, actions: ActionRegistry):
        self.window = window
        self.actions = actions

    def build(self) -> QMenuBar:
        return self._build_from_config(MENU_CONFIG)

# gui_qt/controllers/price_check_controller.py
class PriceCheckController:
    """Coordinates price checking workflow."""
    def __init__(self, price_service: PriceService, session_manager: SessionManager):
        self.price_service = price_service
        self.session_manager = session_manager

    async def check_price(self, item_text: str, session_id: int) -> List[PriceResult]:
        ...

# gui_qt/services/window_manager.py
class WindowManager:
    """Manages child window lifecycle with lazy loading."""
    _windows: Dict[str, QWidget] = {}

    def get_or_create(self, window_type: str) -> QWidget:
        if window_type not in self._windows:
            self._windows[window_type] = self._factory(window_type)
        return self._windows[window_type]
```

**Refactoring Path:**
1. Extract `MenuBuilder` class with declarative menu configuration
2. Extract `PriceCheckController` for business logic
3. Extract `WindowManager` for child window lifecycle
4. Extract `ActionRegistry` for keyboard shortcuts and actions
5. Main window becomes thin coordinator (~500 lines max)

---

### 🟡 1.2 Worker Thread Patterns

**Problem:** Workers are defined inline within `main_window.py`:

```python
# Current: Tightly coupled to main window
class PriceCheckWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            results = self._window.ctx.price_service.get_prices(...)
```

**Recommendations:**

```python
# gui_qt/workers/base_worker.py
class BaseWorker(QObject):
    """Base class for all background workers with standardized error handling."""
    finished = pyqtSignal(object)  # Generic result
    error = pyqtSignal(str, str)   # message, traceback
    progress = pyqtSignal(int, int)  # current, total

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @abstractmethod
    def _execute(self) -> Any:
        """Override to implement actual work."""
        pass

    def run(self):
        try:
            if not self._cancelled:
                result = self._execute()
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e), traceback.format_exc())

# gui_qt/workers/price_check_worker.py
class PriceCheckWorker(BaseWorker):
    def __init__(self, price_service: PriceService, item_text: str, league: str):
        super().__init__()
        self.price_service = price_service
        self.item_text = item_text
        self.league = league

    def _execute(self) -> List[PriceResult]:
        return self.price_service.get_prices(self.item_text, self.league)
```

---

### 🟡 1.3 Circular Import Risk

**Problem:** `AppContext` import pattern creates potential circular imports:

```python
# main_window.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gui_qt.app_context import AppContext
```

**Recommendation:** Use dependency injection more explicitly:

```python
# Define interfaces in a separate module
# core/interfaces.py
from abc import ABC, abstractmethod

class IPriceService(ABC):
    @abstractmethod
    def get_prices(self, item_text: str, league: str) -> List[PriceResult]: ...

class IConfigService(ABC):
    @abstractmethod
    def get(self, key: str) -> Any: ...

# main_window.py - depends on interfaces, not implementations
class PriceCheckerWindow(QMainWindow):
    def __init__(self, price_service: IPriceService, config: IConfigService):
        ...
```

---

## 2. Performance Optimizations

### 🔴 2.1 Redundant Data Copying

**Problem in `core/config.py`:**

```python
# Current: Deep copy on every default access
@classmethod
def _default_config_deepcopy(cls) -> Dict[str, Any]:
    return copy.deepcopy(cls.DEFAULT_CONFIG)

def _load(self) -> Dict[str, Any]:
    if not os.path.exists(self.config_path):
        return self._default_config_deepcopy()  # Called frequently
```

**Recommendation:** Cache the deep copy or use frozen dataclasses:

```python
from dataclasses import dataclass, field
from typing import FrozenSet

@dataclass(frozen=True)
class DefaultConfig:
    """Immutable default configuration - no copy needed."""
    default_league: str = "Standard"
    theme: str = "dark"
    price_sources: FrozenSet[str] = field(default_factory=lambda: frozenset({"poe.ninja", "poe.watch"}))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to mutable dict for runtime config."""
        return {
            "default_league": self.default_league,
            "theme": self.theme,
            "price_sources": list(self.price_sources),
        }

DEFAULT_CONFIG = DefaultConfig()
```

---

### 🟡 2.2 History Deque Efficiency

**Current implementation:**

```python
self._history: Deque[Dict[str, Any]] = deque(maxlen=100)
```

**Issues:**
- Storing full result dicts duplicates large data
- No persistence across sessions
- Linear search for history lookups

**Recommendation:**

```python
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class HistoryEntry:
    """Lightweight history reference."""
    item_hash: str  # SHA256 of item text
    item_name: str  # Display name only
    timestamp: datetime
    result_count: int
    top_price: float

    @classmethod
    def from_results(cls, item_text: str, results: List[Dict]) -> "HistoryEntry":
        return cls(
            item_hash=hashlib.sha256(item_text.encode()).hexdigest()[:16],
            item_name=results[0].get("item_name", "Unknown")[:50] if results else "Unknown",
            timestamp=datetime.now(),
            result_count=len(results),
            top_price=max((r.get("chaos_value", 0) for r in results), default=0)
        )

class HistoryManager:
    """Efficient history with optional persistence."""
    def __init__(self, max_entries: int = 100, persist_path: Optional[Path] = None):
        self._entries: Deque[HistoryEntry] = deque(maxlen=max_entries)
        self._results_cache: Dict[str, List[Dict]] = {}  # LRU cache for full results
        self._persist_path = persist_path

    def add(self, item_text: str, results: List[Dict]):
        entry = HistoryEntry.from_results(item_text, results)
        self._entries.appendleft(entry)
        self._results_cache[entry.item_hash] = results
        # Evict old cache entries if needed
        self._evict_cache()
```

---

### 🟡 2.3 Theme Application Performance

**Problem in `styles.py`:**

```python
def apply_theme(self, app: QApplication) -> None:
    """Apply current theme to application."""
    colors = self.colors
    stylesheet = self._generate_stylesheet(colors)  # Regenerated every time
    app.setStyleSheet(stylesheet)
```

**Recommendation:** Cache generated stylesheets:

```python
class ThemeManager:
    def __init__(self):
        self._stylesheet_cache: Dict[Tuple[Theme, Optional[str]], str] = {}

    def apply_theme(self, app: QApplication) -> None:
        cache_key = (self._current_theme, self._accent_color)
        if cache_key not in self._stylesheet_cache:
            self._stylesheet_cache[cache_key] = self._generate_stylesheet(self.colors)
        app.setStyleSheet(self._stylesheet_cache[cache_key])

    def _invalidate_cache(self):
        """Call when theme definitions change."""
        self._stylesheet_cache.clear()
```

---

### 🔴 2.4 API Client Connection Pooling

**Problem in `data_sources/base_api.py`:**

```python
# Creates new session for each request potentially
def _make_request(self, url: str, params: Dict) -> Dict:
    response = requests.get(url, params=params, timeout=self.timeout)
```

**Recommendation:** Use connection pooling with `requests.Session`:

```python
class BaseAPIClient:
    _session: Optional[requests.Session] = None

    @classmethod
    def _get_session(cls) -> requests.Session:
        if cls._session is None:
            cls._session = requests.Session()
            # Configure connection pooling
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504]
                )
            )
            cls._session.mount('https://', adapter)
            cls._session.mount('http://', adapter)
        return cls._session

    def _make_request(self, url: str, params: Dict) -> Dict:
        session = self._get_session()
        response = session.get(url, params=params, timeout=self.timeout)
        ...
```

---

## 3. Code Elegance

### 🟡 3.1 Inconsistent Error Handling

**Problem:** Mixed patterns across codebase:

```python
# Pattern 1: Return None
def get_price(self, item: str) -> Optional[float]:
    try:
        return self._fetch_price(item)
    except Exception:
        return None

# Pattern 2: Raise
def parse_item(self, text: str) -> ParsedItem:
    if not text:
        raise ValueError("Empty item text")

# Pattern 3: Return tuple
def fetch_data(self) -> Tuple[Optional[Data], Optional[str]]:
    try:
        return (self._fetch(), None)
    except Exception as e:
        return (None, str(e))
```

**Recommendation:** Adopt Result pattern consistently:

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> T:
        return self.value

@dataclass
class Err(Generic[E]):
    error: E

    def is_ok(self) -> bool:
        return False

    def unwrap(self) -> Never:
        raise ValueError(f"Called unwrap on Err: {self.error}")

Result = Union[Ok[T], Err[E]]

# Usage:
def get_price(self, item: str) -> Result[float, str]:
    try:
        price = self._fetch_price(item)
        return Ok(price)
    except APIError as e:
        return Err(f"API error: {e}")
    except ParseError as e:
        return Err(f"Parse error: {e}")

# Caller:
result = service.get_price("Headhunter")
if result.is_ok():
    print(f"Price: {result.unwrap()}")
else:
    logger.warning(f"Failed: {result.error}")
```

---

### 🟡 3.2 Magic Numbers and Strings

**Problem:** Scattered constants:

```python
# main_window.py
self._history: Deque[Dict[str, Any]] = deque(maxlen=100)  # Why 100?

# styles.py
TIER_COLORS = {
    "T1": "#FFD700",  # What's special about this gold?
}

# Various files
if response.status_code == 429:  # Rate limited
    time.sleep(60)  # Why 60?
```

**Recommendation:** Centralize constants:

```python
# core/constants.py
"""Application-wide constants with documentation."""

from dataclasses import dataclass

@dataclass(frozen=True)
class HistoryConfig:
    MAX_ENTRIES: int = 100  # Balance between memory and usefulness
    PERSIST_INTERVAL_SECONDS: int = 300  # Auto-save every 5 minutes

@dataclass(frozen=True)
class RateLimitConfig:
    BACKOFF_SECONDS: int = 60  # PoE API rate limit reset time
    MAX_RETRIES: int = 3
    RETRY_MULTIPLIER: float = 2.0  # Exponential backoff

@dataclass(frozen=True)
class UIConfig:
    TOAST_DURATION_MS: int = 3000
    DEBOUNCE_DELAY_MS: int = 300  # For search inputs
    MAX_SESSIONS: int = 10

# colors.py - with named constants
class TierColors:
    """Mod tier colors matching PoE in-game display."""
    T1_GOLD = "#FFD700"  # Best possible roll
    T2_YELLOW = "#FFFF00"
    T3_GREEN = "#00FF00"
    # ... etc
```

---

### 🟢 3.3 Property Accessor Explosion

**Problem in `main_window.py`:**

```python
@property
def input_text(self) -> QPlainTextEdit:
    return self._session_tabs.get_current_panel().input_text

@property
def item_inspector(self) -> ItemInspector:
    return self._session_tabs.get_current_panel().item_inspector

@property
def results_table(self) -> ResultsTable:
    return self._session_tabs.get_current_panel().results_table

# ... 5+ more similar properties
```

**Recommendation:** Use delegation pattern or `__getattr__`:

```python
class PriceCheckerWindow(QMainWindow):
    # Delegate these attributes to current session panel
    _DELEGATED_ATTRS = frozenset({
        'input_text', 'item_inspector', 'results_table',
        'filter_input', 'source_filter', 'rare_eval_panel'
    })

    def __getattr__(self, name: str) -> Any:
        if name in self._DELEGATED_ATTRS:
            panel = self._session_tabs.get_current_panel()
            if panel:
                return getattr(panel, name)
            raise AttributeError(f"No active session panel for {name}")
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
```

---

### 🟢 3.4 Signal/Slot Documentation

**Problem:** Qt signals lack documentation:

```python
class SessionPanel(QWidget):
    check_price_requested = pyqtSignal(str)  # What string? Item text?
    results_updated = pyqtSignal(list)  # List of what?
```

**Recommendation:** Use typed signals with docstrings:

```python
from PyQt6.QtCore import pyqtSignal
from typing import List, Dict, Any

class SessionPanel(QWidget):
    """Panel for a single price-checking session.

    Signals:
        check_price_requested(item_text: str): Emitted when user requests price check.
            The item_text is the raw pasted item text from PoE.
        results_updated(results: List[PriceResult]): Emitted when price results change.
            Each result contains item_name, chaos_value, source, etc.
    """
    check_price_requested: pyqtSignal = pyqtSignal(str)
    results_updated: pyqtSignal = pyqtSignal(list)
```

---

## 4. Testing Improvements

### 🟡 4.1 Test Isolation

**Problem:** Tests may share state through singletons:

```python
# ThemeManager is a singleton - tests might affect each other
def test_theme_switching():
    tm = ThemeManager()
    tm.set_theme(Theme.LIGHT)
    # This persists to next test!
```

**Recommendation:** Add reset mechanism for testing:

```python
class ThemeManager:
    @classmethod
    def _reset_for_testing(cls):
        """Reset singleton state - only for tests."""
        cls._instance = None

# conftest.py
@pytest.fixture(autouse=True)
def reset_singletons():
    yield
    ThemeManager._reset_for_testing()
    Config._reset_for_testing()
```

---

### 🟡 4.2 Missing Integration Tests

**Current state:** Strong unit tests, but limited integration:

```
tests/
├── unit/          # Good coverage
├── integration/   # Mostly empty
└── acceptance/    # Manual tests
```

**Recommendation:** Add integration test suite:

```python
# tests/integration/test_price_workflow.py
class TestPriceCheckWorkflow:
    """Integration tests for complete price checking flow."""

    @pytest.fixture
    def app_context(self, tmp_path):
        """Create real AppContext with test config."""
        config = Config(config_path=tmp_path / "config.json")
        return AppContext(config=config)

    def test_price_check_end_to_end(self, app_context, qtbot):
        """Test: paste item -> check price -> display results."""
        window = PriceCheckerWindow(app_context)
        qtbot.addWidget(window)

        # Simulate pasting item
        window.input_text.setPlainText(SAMPLE_UNIQUE_ITEM)

        # Trigger price check
        with qtbot.waitSignal(window.price_check_complete, timeout=5000):
            window._on_check_price()

        # Verify results displayed
        assert window.results_table.rowCount() > 0
```

---

## 5. Specific File Recommendations

### `gui_qt/main_window.py` - Priority Refactoring

| Lines | Current | Recommended |
|-------|---------|-------------|
| 1-100 | Imports, class definition | Keep, clean up imports |
| 100-500 | `__init__`, menu creation | Extract `MenuBuilder` |
| 500-800 | Window creation methods | Extract `WindowManager` |
| 800-1200 | Price check logic | Extract `PriceCheckController` |
| 1200-1600 | Event handlers | Keep, but simplify |
| 1600-2000 | Utility methods | Extract relevant utilities |

**Target:** Reduce `main_window.py` to ~600 lines with clear single responsibility.

---

### `gui_qt/styles.py` - Good, Minor Improvements

| Aspect | Current | Recommendation |
|--------|---------|----------------|
| Structure | Excellent | Keep |
| Theme definitions | Inline dicts | Consider YAML/JSON for easier editing |
| Stylesheet generation | Regenerated each time | Add caching |
| Colorblind support | Excellent | Keep |

---

### `core/config.py` - Clean, Minor Improvements

| Aspect | Current | Recommendation |
|--------|---------|----------------|
| JSON persistence | Good | Keep |
| Encryption | Good | Keep |
| Default copying | Inefficient | Use frozen dataclass |
| Property accessors | Good | Keep |

---

## 6. Immediate Action Items

### Phase 1: Foundation (Do First)
1. ☐ Extract `MenuBuilder` from `main_window.py`
2. ☐ Create `BaseWorker` class and extract workers
3. ☐ Implement connection pooling in `BaseAPIClient`
4. ☐ Add stylesheet caching to `ThemeManager`

### Phase 2: Architecture (Next)
5. ☐ Create `WindowManager` for child window lifecycle
6. ☐ Extract `PriceCheckController`
7. ☐ Implement `Result` type for consistent error handling
8. ☐ Centralize constants in `core/constants.py`

### Phase 3: Polish (After)
9. ☐ Add integration test suite
10. ☐ Document all signals with types
11. ☐ Add singleton reset for testing
12. ☐ Consider interfaces for dependency injection

---

## 7. Metrics to Track

After refactoring, measure:

| Metric | Current | Target |
|--------|---------|--------|
| `main_window.py` lines | 2001 | <600 |
| Test coverage | ~60% | 75% |
| Cyclomatic complexity (max) | Unknown | <10 per function |
| Import depth | Unknown | <3 levels |
| Cold start time | Unknown | <2 seconds |

---

## Conclusion

The codebase has solid foundations but has grown organically. The primary technical debt is the monolithic main window. Addressing this will:

1. **Improve testability** - Smaller units are easier to test
2. **Reduce merge conflicts** - Separate concerns in separate files
3. **Enable parallel development** - Multiple devs can work without conflict
4. **Improve maintainability** - Clear responsibilities make bugs easier to find

The recommended refactoring can be done incrementally without disrupting current features. Start with extracting the menu builder (lowest risk, high reward) and progress to more complex extractions.

---

*Review completed: 2025-11-29*
