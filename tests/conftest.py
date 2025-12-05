import pytest
import time
import sys
import faulthandler
from core.config import Config
from core.database import Database
from core.item_parser import ItemParser


# =============================================================================
# Global singleton reset fixture for test isolation
# =============================================================================

@pytest.fixture(autouse=True)
def reset_qt_singletons():
    """
    Reset all Qt/GUI singletons after each test for proper isolation.

    This autouse fixture ensures no test can leak state to another test through
    singleton instances. The reset happens after yield (during teardown).

    Singletons reset:
    - ThemeManager: Theme state and callbacks
    - WindowManager: Window cache and factories
    - ShortcutManager: Keyboard shortcut registrations
    - HistoryManager: Price check history
    """
    # Run the test
    yield

    # Teardown: reset all singletons
    # Import here to avoid circular imports and only when tests use GUI code
    try:
        from gui_qt.styles import ThemeManager
        ThemeManager.reset_for_testing()
    except ImportError:
        pass

    try:
        from gui_qt.services.window_manager import WindowManager
        WindowManager.reset_for_testing()
    except ImportError:
        pass

    try:
        from gui_qt.shortcuts import ShortcutManager
        ShortcutManager.reset_for_testing()
    except ImportError:
        pass

    try:
        from gui_qt.services.history_manager import HistoryManager
        HistoryManager.reset_for_testing()
    except ImportError:
        pass

    try:
        from gui_qt.widgets.poe_item_tooltip import PoEItemTooltip
        PoEItemTooltip.reset_for_testing()
    except ImportError:
        pass


@pytest.fixture
def temp_config(tmp_path):
    """
    Provide a fresh Config with validation.

    This fixture GUARANTEES a clean config or fails loudly.
    """
    # Create unique config file
    config_path = tmp_path / f"config_{id(tmp_path)}_{time.time_ns()}.json"

    # Create config
    config = Config(config_file=config_path)

    # VALIDATE it starts clean (will fail test if not)
    assert config.min_value_chaos == 0.0, \
        f"FIXTURE CONTAMINATED! min_value={config.min_value_chaos}, file={config.config_file}"
    assert config.show_vendor_items is True, \
        f"FIXTURE CONTAMINATED! show_vendor={config.show_vendor_items}, file={config.config_file}"
    assert config.league == "Standard", \
        f"FIXTURE CONTAMINATED! league={config.league}, file={config.config_file}"
    assert config.window_size == (1200, 800), \
        f"FIXTURE CONTAMINATED! window={config.window_size}, file={config.config_file}"

    return config


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / f"db_{id(tmp_path)}_{time.time_ns()}.db"
    db = Database(db_path=db_path)
    yield db
    db.close()


@pytest.fixture
def parser():
    return ItemParser()


def pytest_sessionstart(session):  # pragma: no cover - test harness init
    """Enable faulthandler for the entire test run to aid diagnosing hangs.

    When a test times out (via pytest-timeout) or when a manual break occurs,
    Python will dump stack traces of all threads to stderr. This is a best-effort
    hook and will silently continue if enabling fails.
    """
    try:
        faulthandler.enable(file=sys.stderr, all_threads=True)
    except Exception:
        pass
