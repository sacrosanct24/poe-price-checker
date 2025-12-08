# tests/unit/gui_qt/services/test_window_state.py
"""Tests for WindowStateManager service."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QMainWindow, QSplitter, QTableView

from gui_qt.services.window_state import (
    WindowGeometry,
    SplitterState,
    TableColumnState,
    WindowState,
    WindowStateManager,
    get_window_state_manager,
    save_window_state,
    restore_window_state,
)


# =============================================================================
# WindowGeometry Tests
# =============================================================================


class TestWindowGeometry:
    """Tests for WindowGeometry dataclass."""

    def test_default_values(self):
        """WindowGeometry should have sensible defaults."""
        geom = WindowGeometry()
        assert geom.x == 100
        assert geom.y == 100
        assert geom.width == 800
        assert geom.height == 600
        assert geom.maximized is False
        assert geom.full_screen is False

    def test_custom_values(self):
        """WindowGeometry should accept custom values."""
        geom = WindowGeometry(x=50, y=75, width=1024, height=768, maximized=True)
        assert geom.x == 50
        assert geom.y == 75
        assert geom.width == 1024
        assert geom.height == 768
        assert geom.maximized is True


# =============================================================================
# SplitterState Tests
# =============================================================================


class TestSplitterState:
    """Tests for SplitterState dataclass."""

    def test_default_values(self):
        """SplitterState should have empty defaults."""
        state = SplitterState()
        assert state.sizes == []
        assert state.orientation == "horizontal"

    def test_custom_values(self):
        """SplitterState should accept custom values."""
        state = SplitterState(sizes=[300, 500], orientation="vertical")
        assert state.sizes == [300, 500]
        assert state.orientation == "vertical"


# =============================================================================
# TableColumnState Tests
# =============================================================================


class TestTableColumnState:
    """Tests for TableColumnState dataclass."""

    def test_default_values(self):
        """TableColumnState should have empty defaults."""
        state = TableColumnState()
        assert state.widths == {}
        assert state.hidden == []
        assert state.order == []

    def test_custom_values(self):
        """TableColumnState should accept custom values."""
        state = TableColumnState(
            widths={0: 100, 1: 200},
            hidden=[2, 3],
            order=[1, 0, 2, 3],
        )
        assert state.widths == {0: 100, 1: 200}
        assert state.hidden == [2, 3]
        assert state.order == [1, 0, 2, 3]


# =============================================================================
# WindowState Tests
# =============================================================================


class TestWindowState:
    """Tests for WindowState dataclass."""

    def test_default_values(self):
        """WindowState should have empty defaults."""
        state = WindowState()
        assert isinstance(state.geometry, WindowGeometry)
        assert state.splitters == {}
        assert state.tables == {}
        assert state.custom == {}

    def test_to_dict(self):
        """to_dict should serialize to dictionary."""
        state = WindowState()
        state.geometry.x = 200
        state.custom["key"] = "value"

        result = state.to_dict()

        assert result["geometry"]["x"] == 200
        assert result["custom"]["key"] == "value"
        assert "splitters" in result
        assert "tables" in result

    def test_from_dict_empty(self):
        """from_dict should handle empty dict."""
        state = WindowState.from_dict({})
        assert isinstance(state.geometry, WindowGeometry)
        assert state.splitters == {}

    def test_from_dict_with_data(self):
        """from_dict should restore from dictionary."""
        data = {
            "geometry": {"x": 150, "y": 175, "width": 1000, "height": 700},
            "splitters": {"main": {"sizes": [200, 600], "orientation": "horizontal"}},
            "tables": {"results": {"widths": {0: 100}, "hidden": [1], "order": []}},
            "custom": {"setting": True},
        }

        state = WindowState.from_dict(data)

        assert state.geometry.x == 150
        assert state.geometry.width == 1000
        assert "main" in state.splitters
        assert state.splitters["main"].sizes == [200, 600]
        assert "results" in state.tables
        assert state.tables["results"].widths == {0: 100}
        assert state.custom["setting"] is True

    def test_roundtrip(self):
        """to_dict/from_dict should preserve data."""
        original = WindowState()
        original.geometry.x = 300
        original.geometry.maximized = True
        original.splitters["panel"] = SplitterState(sizes=[100, 400])
        original.custom["test"] = 123

        data = original.to_dict()
        restored = WindowState.from_dict(data)

        assert restored.geometry.x == 300
        assert restored.geometry.maximized is True
        assert restored.splitters["panel"].sizes == [100, 400]
        assert restored.custom["test"] == 123


# =============================================================================
# WindowStateManager Tests
# =============================================================================


class TestWindowStateManager:
    """Tests for WindowStateManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with TemporaryDirectory() as td:
            yield Path(td)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create manager with temp storage."""
        return WindowStateManager(storage_dir=temp_dir)

    @pytest.fixture
    def mock_window(self, qtbot):
        """Create mock window."""
        w = QWidget()
        qtbot.addWidget(w)
        w.setGeometry(100, 100, 800, 600)
        return w

    @pytest.fixture
    def mock_main_window(self, qtbot):
        """Create mock QMainWindow."""
        w = QMainWindow()
        qtbot.addWidget(w)
        w.setGeometry(100, 100, 800, 600)
        return w

    def test_init_creates_storage_dir(self, temp_dir):
        """Manager should create storage directory."""
        new_dir = temp_dir / "subdir"
        manager = WindowStateManager(storage_dir=new_dir)
        assert new_dir.exists()

    def test_get_state_creates_new(self, manager):
        """get_state should create new state if not exists."""
        state = manager.get_state("new_window")
        assert isinstance(state, WindowState)
        assert state.geometry.x == 100  # Default

    def test_get_state_returns_existing(self, manager):
        """get_state should return existing state."""
        state1 = manager.get_state("window1")
        state1.geometry.x = 999
        state2 = manager.get_state("window1")
        assert state2.geometry.x == 999

    def test_save_window_stores_geometry(self, manager, mock_window):
        """save_window should store window geometry."""
        mock_window.setGeometry(200, 150, 1024, 768)
        manager.save_window(mock_window, "test_window")

        state = manager.get_state("test_window")
        assert state.geometry.x == 200
        assert state.geometry.y == 150
        assert state.geometry.width == 1024
        assert state.geometry.height == 768

    def test_save_window_stores_maximized(self, manager, mock_main_window):
        """save_window should store maximized state for QMainWindow."""
        mock_main_window.showMaximized()
        # Need to process events for state to update
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        manager.save_window(mock_main_window, "main")
        state = manager.get_state("main")
        assert state.geometry.maximized is True

    def test_save_window_with_custom_state(self, manager, mock_window):
        """save_window should store custom state."""
        manager.save_window(
            mock_window,
            "window",
            custom={"theme": "dark", "font_size": 14},
        )

        state = manager.get_state("window")
        assert state.custom["theme"] == "dark"
        assert state.custom["font_size"] == 14

    def test_save_window_persists_to_disk(self, manager, mock_window, temp_dir):
        """save_window should persist to disk."""
        manager.save_window(mock_window, "saved_window")

        state_file = temp_dir / "window_state.json"
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)
        assert "saved_window" in data

    def test_restore_window_applies_geometry(self, manager, mock_window):
        """restore_window should apply saved geometry."""
        # Save initial state
        mock_window.setGeometry(300, 200, 1000, 700)
        manager.save_window(mock_window, "restore_test")

        # Change geometry
        mock_window.setGeometry(0, 0, 400, 300)

        # Restore
        manager.restore_window(mock_window, "restore_test")

        assert mock_window.geometry().x() == 300
        assert mock_window.geometry().y() == 200
        assert mock_window.geometry().width() == 1000
        assert mock_window.geometry().height() == 700

    def test_restore_window_returns_custom(self, manager, mock_window):
        """restore_window should return custom state."""
        manager.save_window(
            mock_window,
            "custom_test",
            custom={"value": 42},
        )

        result = manager.restore_window(mock_window, "custom_test")
        assert result["value"] == 42

    def test_restore_window_unknown_key_returns_empty(self, manager, mock_window):
        """restore_window with unknown key should return empty dict."""
        result = manager.restore_window(mock_window, "unknown")
        assert result == {}

    def test_save_custom(self, manager):
        """save_custom should save individual value."""
        manager.save_custom("window1", "setting", True)

        state = manager.get_state("window1")
        assert state.custom["setting"] is True

    def test_get_custom(self, manager):
        """get_custom should retrieve saved value."""
        manager.save_custom("window2", "count", 5)

        result = manager.get_custom("window2", "count")
        assert result == 5

    def test_get_custom_default(self, manager):
        """get_custom should return default if not found."""
        result = manager.get_custom("window3", "missing", default="default_value")
        assert result == "default_value"

    def test_clear_removes_state(self, manager, mock_window):
        """clear should remove state for a window."""
        manager.save_window(mock_window, "to_clear")
        assert "to_clear" in manager._states

        manager.clear("to_clear")
        assert "to_clear" not in manager._states

    def test_clear_all_removes_all(self, manager, mock_window, temp_dir):
        """clear_all should remove all states and file."""
        manager.save_window(mock_window, "window1")
        manager.save_window(mock_window, "window2")

        state_file = temp_dir / "window_state.json"
        assert state_file.exists()

        manager.clear_all()

        assert len(manager._states) == 0
        assert not state_file.exists()

    def test_load_from_disk(self, temp_dir, mock_window, qtbot):
        """Manager should load existing state from disk."""
        # Create first manager and save state
        manager1 = WindowStateManager(storage_dir=temp_dir)
        mock_window.setGeometry(400, 300, 1200, 800)
        manager1.save_window(mock_window, "persist_test")

        # Create second manager - should load from disk
        manager2 = WindowStateManager(storage_dir=temp_dir)
        state = manager2.get_state("persist_test")

        assert state.geometry.x == 400
        assert state.geometry.width == 1200


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_window_state_manager_returns_manager(self):
        """get_window_state_manager should return a manager."""
        # Reset global for test isolation
        import gui_qt.services.window_state as ws
        ws._manager = None

        manager = get_window_state_manager()
        assert isinstance(manager, WindowStateManager)

    def test_get_window_state_manager_returns_singleton(self):
        """get_window_state_manager should return same instance."""
        import gui_qt.services.window_state as ws
        ws._manager = None

        manager1 = get_window_state_manager()
        manager2 = get_window_state_manager()
        assert manager1 is manager2

        # Cleanup
        ws._manager = None

    def test_save_window_state_delegates(self, qtbot):
        """save_window_state should delegate to manager."""
        import gui_qt.services.window_state as ws
        ws._manager = None

        with TemporaryDirectory() as td:
            # Set up manager with temp dir
            manager = WindowStateManager(storage_dir=Path(td))
            ws._manager = manager

            window = QWidget()
            qtbot.addWidget(window)
            window.setGeometry(500, 400, 900, 700)

            save_window_state(window, "delegate_test")

            state = manager.get_state("delegate_test")
            assert state.geometry.x == 500

            ws._manager = None

    def test_restore_window_state_delegates(self, qtbot):
        """restore_window_state should delegate to manager."""
        import gui_qt.services.window_state as ws
        ws._manager = None

        with TemporaryDirectory() as td:
            manager = WindowStateManager(storage_dir=Path(td))
            ws._manager = manager

            window = QWidget()
            qtbot.addWidget(window)
            window.setGeometry(600, 500, 1100, 900)
            manager.save_window(window, "restore_delegate", custom={"key": "val"})

            window.setGeometry(0, 0, 100, 100)

            result = restore_window_state(window, "restore_delegate")

            assert result["key"] == "val"
            assert window.geometry().x() == 600

            ws._manager = None
