"""Tests for gui_qt/windows/loot_dashboard_window.py - Loot tracking dashboard."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch, PropertyMock

from PyQt6.QtCore import Qt, QModelIndex

from gui_qt.windows.loot_dashboard_window import (
    TopDropsModel,
    MapRunsModel,
    LootDashboardWindow,
)


# =============================================================================
# TopDropsModel Tests
# =============================================================================


class TestTopDropsModelInit:
    """Tests for TopDropsModel initialization."""

    def test_init_creates_empty_data(self):
        """Should initialize with empty data list."""
        model = TopDropsModel()
        assert model.rowCount() == 0
        assert model.columnCount() == 5

    def test_columns_constant(self):
        """Should have expected columns."""
        assert len(TopDropsModel.COLUMNS) == 5
        col_names = [c[0] for c in TopDropsModel.COLUMNS]
        assert "item_name" in col_names
        assert "stack_size" in col_names
        assert "chaos_value" in col_names
        assert "rarity" in col_names
        assert "detected_at" in col_names


class TestTopDropsModelData:
    """Tests for TopDropsModel data handling."""

    @pytest.fixture
    def model(self):
        """Create model with sample data."""
        model = TopDropsModel()
        model.set_data([
            {
                "item_name": "Exalted Orb",
                "stack_size": 2,
                "chaos_value": 150.0,
                "rarity": "Currency",
                "detected_at": datetime(2025, 1, 15, 10, 30, 45),
            },
            {
                "item_name": "Divine Orb",
                "stack_size": 1,
                "chaos_value": 180.0,
                "rarity": "Currency",
                "detected_at": "2025-01-15T11:00:00",
            },
        ])
        return model

    def test_row_count_matches_data(self, model):
        """Should return correct row count."""
        assert model.rowCount() == 2

    def test_data_returns_item_name(self, model):
        """Should return item name for first column."""
        index = model.index(0, 0)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "Exalted Orb"

    def test_data_returns_stack_size(self, model):
        """Should return stack size."""
        index = model.index(0, 1)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "2"

    def test_data_returns_total_chaos_value(self, model):
        """Should return total value (value * stack_size)."""
        index = model.index(0, 2)  # chaos_value column
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        # 150.0 * 2 = 300.0
        assert value == "300.0"

    def test_data_formats_datetime(self, model):
        """Should format datetime as time string."""
        index = model.index(0, 4)  # detected_at column
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "10:30:45"

    def test_data_parses_iso_datetime_string(self, model):
        """Should parse ISO datetime string."""
        index = model.index(1, 4)  # Second row, detected_at
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "11:00:00"

    def test_data_returns_none_for_invalid_index(self, model):
        """Should return None for out of bounds index."""
        index = model.index(100, 0)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value is None

    def test_data_alignment_for_numeric_columns(self, model):
        """Should right-align numeric columns."""
        stack_index = model.index(0, 1)
        value_index = model.index(0, 2)

        stack_align = model.data(stack_index, Qt.ItemDataRole.TextAlignmentRole)
        value_align = model.data(value_index, Qt.ItemDataRole.TextAlignmentRole)

        expected = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        assert stack_align == expected
        assert value_align == expected

    def test_data_tooltip(self, model):
        """Should return tooltip with item details."""
        index = model.index(0, 0)
        tooltip = model.data(index, Qt.ItemDataRole.ToolTipRole)
        assert "Exalted Orb" in tooltip
        assert "Currency" in tooltip

    def test_header_data(self, model):
        """Should return column headers."""
        header = model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header == "Item"

        header = model.headerData(2, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header == "Value (c)"

    def test_clear_removes_all_data(self, model):
        """Should clear all data."""
        assert model.rowCount() == 2
        model.clear()
        assert model.rowCount() == 0


class TestTopDropsModelEdgeCases:
    """Edge case tests for TopDropsModel."""

    def test_handles_invalid_chaos_value(self):
        """Should handle non-numeric chaos value."""
        model = TopDropsModel()
        model.set_data([{"chaos_value": "invalid", "stack_size": 1}])
        index = model.index(0, 2)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "0.0"

    def test_handles_missing_stack_size(self):
        """Should default to 1 for missing stack size."""
        model = TopDropsModel()
        model.set_data([{"chaos_value": 100.0}])
        index = model.index(0, 2)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "100.0"

    def test_handles_invalid_datetime_string(self):
        """Should return raw string for invalid datetime."""
        model = TopDropsModel()
        model.set_data([{"detected_at": "not-a-date"}])
        index = model.index(0, 4)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "not-a-date"

    def test_handles_empty_values(self):
        """Should handle empty/None values."""
        model = TopDropsModel()
        model.set_data([{"item_name": None, "rarity": ""}])

        index = model.index(0, 0)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == ""

        index = model.index(0, 3)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == ""


# =============================================================================
# MapRunsModel Tests
# =============================================================================


class TestMapRunsModelInit:
    """Tests for MapRunsModel initialization."""

    def test_init_creates_empty_data(self):
        """Should initialize with empty data list."""
        model = MapRunsModel()
        assert model.rowCount() == 0
        assert model.columnCount() == 5

    def test_columns_constant(self):
        """Should have expected columns."""
        assert len(MapRunsModel.COLUMNS) == 5
        col_names = [c[0] for c in MapRunsModel.COLUMNS]
        assert "map_name" in col_names
        assert "area_level" in col_names
        assert "drop_count" in col_names
        assert "total_chaos_value" in col_names
        assert "duration" in col_names


class TestMapRunsModelData:
    """Tests for MapRunsModel data handling."""

    @pytest.fixture
    def model(self):
        """Create model with sample data."""
        model = MapRunsModel()
        model.set_data([
            {
                "map_name": "Crimson Temple",
                "area_level": 83,
                "drop_count": 15,
                "total_chaos_value": 250.5,
                "duration_seconds": 185,  # 3:05
            },
            {
                "map_name": "Strand",
                "area_level": 81,
                "drop_count": 8,
                "total_chaos_value": 100.0,
                "duration_seconds": 0,
            },
        ])
        return model

    def test_row_count_matches_data(self, model):
        """Should return correct row count."""
        assert model.rowCount() == 2

    def test_data_returns_map_name(self, model):
        """Should return map name."""
        index = model.index(0, 0)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "Crimson Temple"

    def test_data_returns_area_level(self, model):
        """Should return area level."""
        index = model.index(0, 1)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "83"

    def test_data_formats_chaos_value(self, model):
        """Should format chaos value with one decimal."""
        index = model.index(0, 3)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "250.5"

    def test_data_formats_duration(self, model):
        """Should format duration as minutes:seconds."""
        index = model.index(0, 4)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "3:05"

    def test_data_formats_zero_duration(self, model):
        """Should return dash for zero duration."""
        index = model.index(1, 4)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "-"

    def test_data_alignment_for_numeric_columns(self, model):
        """Should right-align numeric columns."""
        level_index = model.index(0, 1)
        count_index = model.index(0, 2)
        value_index = model.index(0, 3)

        expected = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        assert model.data(level_index, Qt.ItemDataRole.TextAlignmentRole) == expected
        assert model.data(count_index, Qt.ItemDataRole.TextAlignmentRole) == expected
        assert model.data(value_index, Qt.ItemDataRole.TextAlignmentRole) == expected

    def test_header_data(self, model):
        """Should return column headers."""
        header = model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header == "Map"

        header = model.headerData(4, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header == "Duration"

    def test_clear_removes_all_data(self, model):
        """Should clear all data."""
        assert model.rowCount() == 2
        model.clear()
        assert model.rowCount() == 0


class TestMapRunsModelEdgeCases:
    """Edge case tests for MapRunsModel."""

    def test_handles_invalid_chaos_value(self):
        """Should handle non-numeric chaos value."""
        model = MapRunsModel()
        model.set_data([{"total_chaos_value": "invalid"}])
        index = model.index(0, 3)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "0.0"

    def test_handles_missing_area_level(self):
        """Should show dash for missing area level."""
        model = MapRunsModel()
        model.set_data([{"area_level": None}])
        index = model.index(0, 1)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "-"

    def test_handles_invalid_index(self):
        """Should return None for invalid index."""
        model = MapRunsModel()
        index = model.index(100, 0)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value is None


# =============================================================================
# LootDashboardWindow Tests
# =============================================================================


class TestLootDashboardWindowInit:
    """Tests for LootDashboardWindow initialization."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        ctx = MagicMock()
        ctx.config = MagicMock()
        return ctx

    @pytest.fixture
    def mock_controller(self):
        """Create mock controller with all required signals."""
        controller = MagicMock()
        # Mock signals
        controller.session_started = MagicMock()
        controller.session_ended = MagicMock()
        controller.session_state_changed = MagicMock()
        controller.drops_detected = MagicMock()
        controller.stats_updated = MagicMock()
        controller.status_message = MagicMock()
        controller.snapshot_started = MagicMock()
        controller.snapshot_completed = MagicMock()
        controller.snapshot_error = MagicMock()
        controller.high_value_drop = MagicMock()

        # Make signals have connect method
        for signal in [
            controller.session_started,
            controller.session_ended,
            controller.session_state_changed,
            controller.drops_detected,
            controller.stats_updated,
            controller.status_message,
            controller.snapshot_started,
            controller.snapshot_completed,
            controller.snapshot_error,
            controller.high_value_drop,
        ]:
            signal.connect = MagicMock()

        # Mock methods
        controller.get_current_session.return_value = None
        controller.is_auto_tracking_enabled.return_value = False
        controller.is_monitoring.return_value = False
        controller.load_session_history.return_value = []

        return controller

    def test_init_sets_title(self, qtbot, mock_ctx, mock_controller):
        """Should set window title."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window.windowTitle() == "Loot Tracking Dashboard"

    def test_init_sets_minimum_size(self, qtbot, mock_ctx, mock_controller):
        """Should set minimum window size."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window.minimumWidth() == 700
        assert window.minimumHeight() == 550

    def test_init_creates_start_button(self, qtbot, mock_ctx, mock_controller):
        """Should create start button."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window._start_btn is not None
        assert window._start_btn.text() == "Start Session"
        assert window._start_btn.isEnabled()

    def test_init_creates_stop_button_disabled(self, qtbot, mock_ctx, mock_controller):
        """Should create disabled stop button."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window._stop_btn is not None
        assert window._stop_btn.text() == "Stop Session"
        assert not window._stop_btn.isEnabled()

    def test_init_creates_auto_track_checkbox(self, qtbot, mock_ctx, mock_controller):
        """Should create auto-track checkbox."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window._auto_track_cb is not None
        assert not window._auto_track_cb.isChecked()

    def test_init_creates_drops_table(self, qtbot, mock_ctx, mock_controller):
        """Should create drops table with model."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window._drops_table is not None
        assert window._drops_model is not None
        assert window._drops_table.model() == window._drops_model

    def test_init_creates_maps_table(self, qtbot, mock_ctx, mock_controller):
        """Should create maps table with model."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window._maps_table is not None
        assert window._maps_model is not None
        assert window._maps_table.model() == window._maps_model

    def test_init_connects_controller_signals(self, qtbot, mock_ctx, mock_controller):
        """Should connect all controller signals."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        mock_controller.session_started.connect.assert_called_once()
        mock_controller.session_ended.connect.assert_called_once()
        mock_controller.session_state_changed.connect.assert_called_once()
        mock_controller.drops_detected.connect.assert_called_once()


class TestLootDashboardWindowWithActiveSession:
    """Tests for window with an active session."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session object."""
        session = MagicMock()
        session.name = "Test Session"
        session.duration = timedelta(hours=1, minutes=30)
        session.total_maps = 15
        session.total_drops = 45
        session.total_chaos_value = 2500.0
        session.chaos_per_hour = 1666.0
        session.top_drops = []
        session.map_runs = []
        return session

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        ctx = MagicMock()
        ctx.config = MagicMock()
        return ctx

    @pytest.fixture
    def mock_controller(self, mock_session):
        """Create mock controller with active session."""
        controller = MagicMock()
        # Mock signals
        for attr in ['session_started', 'session_ended', 'session_state_changed',
                     'drops_detected', 'stats_updated', 'status_message',
                     'snapshot_started', 'snapshot_completed', 'snapshot_error',
                     'high_value_drop']:
            signal = MagicMock()
            signal.connect = MagicMock()
            setattr(controller, attr, signal)

        controller.get_current_session.return_value = mock_session
        controller.is_auto_tracking_enabled.return_value = True
        controller.is_monitoring.return_value = True
        controller.load_session_history.return_value = []

        return controller

    def test_start_button_disabled_when_session_active(self, qtbot, mock_ctx, mock_controller):
        """Should disable start button with active session."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert not window._start_btn.isEnabled()
        assert window._stop_btn.isEnabled()

    def test_auto_track_checked_when_enabled(self, qtbot, mock_ctx, mock_controller):
        """Should check auto-track when enabled."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert window._auto_track_cb.isChecked()

    def test_monitoring_label_shows_active(self, qtbot, mock_ctx, mock_controller):
        """Should show monitoring active state."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        assert "Active" in window._monitoring_label.text()


class TestLootDashboardWindowButtonHandlers:
    """Tests for button click handlers."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        ctx = MagicMock()
        ctx.config = MagicMock()
        return ctx

    @pytest.fixture
    def mock_controller(self):
        """Create mock controller."""
        controller = MagicMock()
        for attr in ['session_started', 'session_ended', 'session_state_changed',
                     'drops_detected', 'stats_updated', 'status_message',
                     'snapshot_started', 'snapshot_completed', 'snapshot_error',
                     'high_value_drop']:
            signal = MagicMock()
            signal.connect = MagicMock()
            setattr(controller, attr, signal)

        controller.get_current_session.return_value = None
        controller.is_auto_tracking_enabled.return_value = False
        controller.is_monitoring.return_value = False
        controller.load_session_history.return_value = []

        return controller

    def test_start_click_calls_controller(self, qtbot, mock_ctx, mock_controller):
        """Should call controller.start_session on start click."""
        from core.result import Ok
        mock_controller.start_session.return_value = Ok(MagicMock())

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._start_btn.click()
        mock_controller.start_session.assert_called_once()

    def test_start_click_shows_error(self, qtbot, mock_ctx, mock_controller):
        """Should show error in status label on failure."""
        from core.result import Err
        mock_controller.start_session.return_value = Err("Test error")

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._start_btn.click()
        assert "Test error" in window._status_label.text()

    def test_stop_click_calls_controller(self, qtbot, mock_ctx, mock_controller):
        """Should call controller.end_session on stop click."""
        from core.result import Ok
        mock_controller.end_session.return_value = Ok(MagicMock())

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)
        window._stop_btn.setEnabled(True)

        window._stop_btn.click()
        mock_controller.end_session.assert_called_once()

    def test_auto_track_toggle_calls_controller(self, qtbot, mock_ctx, mock_controller):
        """Should call controller.enable_auto_tracking on toggle."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._auto_track_cb.setChecked(True)
        mock_controller.enable_auto_tracking.assert_called_with(True)

    def test_snapshot_click_calls_controller(self, qtbot, mock_ctx, mock_controller):
        """Should call controller.take_manual_snapshot on click."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._snapshot_btn.click()
        mock_controller.take_manual_snapshot.assert_called_once()


class TestLootDashboardWindowSignalHandlers:
    """Tests for signal handlers."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        return MagicMock()

    @pytest.fixture
    def window_and_controller(self, qtbot, mock_ctx):
        """Create window with mock controller."""
        controller = MagicMock()
        for attr in ['session_started', 'session_ended', 'session_state_changed',
                     'drops_detected', 'stats_updated', 'status_message',
                     'snapshot_started', 'snapshot_completed', 'snapshot_error',
                     'high_value_drop']:
            signal = MagicMock()
            signal.connect = MagicMock()
            setattr(controller, attr, signal)

        controller.get_current_session.return_value = None
        controller.is_auto_tracking_enabled.return_value = False
        controller.is_monitoring.return_value = False
        controller.load_session_history.return_value = []

        window = LootDashboardWindow(mock_ctx, controller)
        qtbot.addWidget(window)
        return window, controller

    def test_on_session_started(self, window_and_controller):
        """Should update UI on session started."""
        window, controller = window_and_controller
        session = MagicMock()
        session.name = "New Session"

        window._on_session_started(session)

        assert "New Session" in window._status_label.text()

    def test_on_session_ended(self, window_and_controller):
        """Should update status on session ended."""
        window, controller = window_and_controller
        session = MagicMock()
        session.total_maps = 10
        session.total_chaos_value = 500.0

        window._on_session_ended(session)

        assert "10 maps" in window._status_label.text()
        assert "500" in window._status_label.text()

    def test_on_state_changed(self, window_and_controller):
        """Should update status on state change."""
        window, controller = window_and_controller

        window._on_state_changed("mapping")

        assert "mapping" in window._status_label.text()

    def test_on_drops_detected(self, window_and_controller):
        """Should update status with drop info."""
        window, controller = window_and_controller
        drop1 = MagicMock()
        drop1.chaos_value = 100.0
        drop1.stack_size = 1
        drop2 = MagicMock()
        drop2.chaos_value = 50.0
        drop2.stack_size = 2

        window._on_drops_detected([drop1, drop2])

        assert "2 drops" in window._status_label.text()
        # Total: 100*1 + 50*2 = 200
        assert "200" in window._status_label.text()

    def test_on_status_message(self, window_and_controller):
        """Should display status message."""
        window, controller = window_and_controller

        window._on_status_message("Test status message")

        assert window._status_label.text() == "Test status message"

    def test_on_snapshot_started(self, window_and_controller):
        """Should disable snapshot button during fetch."""
        window, controller = window_and_controller

        window._on_snapshot_started()

        assert not window._snapshot_btn.isEnabled()
        assert "Fetching" in window._snapshot_btn.text()

    def test_on_snapshot_completed(self, window_and_controller):
        """Should re-enable button and show count."""
        window, controller = window_and_controller
        window._snapshot_btn.setEnabled(False)

        window._on_snapshot_completed(150)

        assert window._snapshot_btn.isEnabled()
        assert "150 items" in window._status_label.text()

    def test_on_snapshot_error(self, window_and_controller):
        """Should re-enable button and show error."""
        window, controller = window_and_controller
        window._snapshot_btn.setEnabled(False)

        window._on_snapshot_error("API rate limited")

        assert window._snapshot_btn.isEnabled()
        assert "API rate limited" in window._status_label.text()

    def test_on_high_value_drop(self, window_and_controller):
        """Should display high value drop notification."""
        window, controller = window_and_controller
        drop = MagicMock()
        drop.item_name = "Mirror of Kalandra"
        drop.chaos_value = 50000.0

        window._on_high_value_drop(drop)

        assert "Mirror of Kalandra" in window._status_label.text()
        assert "50000" in window._status_label.text()


class TestLootDashboardWindowLiveStats:
    """Tests for live statistics display."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        return MagicMock()

    @pytest.fixture
    def mock_controller(self):
        """Create mock controller."""
        controller = MagicMock()
        for attr in ['session_started', 'session_ended', 'session_state_changed',
                     'drops_detected', 'stats_updated', 'status_message',
                     'snapshot_started', 'snapshot_completed', 'snapshot_error',
                     'high_value_drop']:
            signal = MagicMock()
            signal.connect = MagicMock()
            setattr(controller, attr, signal)

        controller.get_current_session.return_value = None
        controller.is_auto_tracking_enabled.return_value = False
        controller.is_monitoring.return_value = False
        controller.load_session_history.return_value = []

        return controller

    def test_displays_dashes_when_no_session(self, qtbot, mock_ctx, mock_controller):
        """Should display dashes for all stats when no session."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._update_live_stats()

        assert window._duration_label.text() == "--"
        assert window._maps_label.text() == "--"
        assert window._drops_label.text() == "--"
        assert window._value_label.text() == "--"
        assert window._rate_label.text() == "--"

    def test_displays_stats_with_session(self, qtbot, mock_ctx, mock_controller):
        """Should display session statistics."""
        session = MagicMock()
        session.duration = timedelta(minutes=45, seconds=30)
        session.total_maps = 10
        session.total_drops = 35
        session.total_chaos_value = 850.0
        session.chaos_per_hour = 750.0  # Under 1000 to avoid "k" formatting
        session.top_drops = []
        session.map_runs = []

        mock_controller.get_current_session.return_value = session

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._update_live_stats()

        assert window._duration_label.text() == "45:30"
        assert window._maps_label.text() == "10"
        assert window._drops_label.text() == "35"
        assert window._value_label.text() == "850c"
        assert window._rate_label.text() == "750"

    def test_formats_hours_in_duration(self, qtbot, mock_ctx, mock_controller):
        """Should format duration with hours."""
        session = MagicMock()
        session.duration = timedelta(hours=2, minutes=15)
        session.total_maps = 0
        session.total_drops = 0
        session.total_chaos_value = 0
        session.chaos_per_hour = 0
        session.top_drops = []
        session.map_runs = []

        mock_controller.get_current_session.return_value = session

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._update_live_stats()

        assert "2h" in window._duration_label.text()
        assert "15m" in window._duration_label.text()

    def test_formats_large_values_as_thousands(self, qtbot, mock_ctx, mock_controller):
        """Should format large values with k suffix."""
        session = MagicMock()
        session.duration = timedelta(hours=1)
        session.total_maps = 20
        session.total_drops = 100
        session.total_chaos_value = 5500.0
        session.chaos_per_hour = 5500.0
        session.top_drops = []
        session.map_runs = []

        mock_controller.get_current_session.return_value = session

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        window._update_live_stats()

        assert "5.5k" in window._value_label.text()
        assert "5.5k" in window._rate_label.text()


class TestLootDashboardWindowHistory:
    """Tests for session history tab."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        return MagicMock()

    @pytest.fixture
    def mock_controller(self):
        """Create mock controller."""
        controller = MagicMock()
        for attr in ['session_started', 'session_ended', 'session_state_changed',
                     'drops_detected', 'stats_updated', 'status_message',
                     'snapshot_started', 'snapshot_completed', 'snapshot_error',
                     'high_value_drop']:
            signal = MagicMock()
            signal.connect = MagicMock()
            setattr(controller, attr, signal)

        controller.get_current_session.return_value = None
        controller.is_auto_tracking_enabled.return_value = False
        controller.is_monitoring.return_value = False

        return controller

    def test_loads_history_on_init(self, qtbot, mock_ctx, mock_controller):
        """Should load history on initialization."""
        mock_controller.load_session_history.return_value = [
            {
                "name": "Session 1",
                "started_at": "2025-01-15T10:00:00",
                "total_chaos_value": 500,
                "total_maps": 5,
            }
        ]

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        mock_controller.load_session_history.assert_called()
        assert window._history_list.count() == 1

    def test_history_item_display_format(self, qtbot, mock_ctx, mock_controller):
        """Should format history items correctly."""
        mock_controller.load_session_history.return_value = [
            {
                "name": "Evening Session",
                "started_at": "2025-01-15T18:30:00",
                "total_chaos_value": 1250,
                "total_maps": 12,
            }
        ]

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        item_text = window._history_list.item(0).text()
        assert "Evening Session" in item_text
        assert "12 maps" in item_text
        assert "1250c" in item_text

    def test_history_item_stores_data(self, qtbot, mock_ctx, mock_controller):
        """Should store session data in item."""
        session_data = {
            "name": "Test",
            "started_at": "2025-01-15T10:00:00",
            "total_chaos_value": 100,
            "total_maps": 2,
        }
        mock_controller.load_session_history.return_value = [session_data]

        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        item = window._history_list.item(0)
        stored = item.data(Qt.ItemDataRole.UserRole)
        assert stored == session_data


class TestLootDashboardWindowCleanup:
    """Tests for window cleanup."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        return MagicMock()

    @pytest.fixture
    def mock_controller(self):
        """Create mock controller."""
        controller = MagicMock()
        for attr in ['session_started', 'session_ended', 'session_state_changed',
                     'drops_detected', 'stats_updated', 'status_message',
                     'snapshot_started', 'snapshot_completed', 'snapshot_error',
                     'high_value_drop']:
            signal = MagicMock()
            signal.connect = MagicMock()
            setattr(controller, attr, signal)

        controller.get_current_session.return_value = None
        controller.is_auto_tracking_enabled.return_value = False
        controller.is_monitoring.return_value = False
        controller.load_session_history.return_value = []

        return controller

    def test_close_stops_timer(self, qtbot, mock_ctx, mock_controller):
        """Should stop update timer on close."""
        window = LootDashboardWindow(mock_ctx, mock_controller)
        qtbot.addWidget(window)

        assert window._update_timer.isActive()
        window.close()
        assert not window._update_timer.isActive()
