"""Tests for gui_qt.main_window - PriceCheckerWindow."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt

from gui_qt.main_window import PriceCheckerWindow
from gui_qt.styles import Theme
from gui_qt.services.history_manager import HistoryManager
from core.result import Ok, Err


@pytest.fixture(autouse=True)
def reset_history_manager():
    """Reset HistoryManager singleton before and after each test."""
    HistoryManager.reset_for_testing()
    yield
    HistoryManager.reset_for_testing()


@pytest.fixture
def mock_ctx():
    """Create a mock AppContext."""
    ctx = MagicMock()
    ctx.config = MagicMock()
    ctx.config.theme = "dark"
    ctx.config.accent_color = None
    ctx.config.minimize_to_tray = False
    ctx.config.show_tray_notifications = False
    ctx.config.tray_alert_threshold = 100
    ctx.parser = MagicMock()
    ctx.price_service = MagicMock()
    ctx.db = MagicMock()
    return ctx


@pytest.fixture
def window(qtbot, mock_ctx):
    """Create a PriceCheckerWindow for testing."""
    with patch('gui_qt.main_window.RankingsPopulationWorker'):
        with patch('gui_qt.main_window.SystemTrayManager'):
            with patch('gui_qt.main_window.get_window_manager') as mock_wm:
                mock_wm.return_value = MagicMock()
                window = PriceCheckerWindow(mock_ctx)
                qtbot.addWidget(window)
                # Mock the session_tabs for easier testing
                window._mock_session_tabs = MagicMock()
                yield window


@pytest.fixture
def window_with_mock_panel(window):
    """Window with a mock panel configured."""
    mock_panel = MagicMock()
    mock_panel.input_text = MagicMock()
    mock_panel.item_inspector = MagicMock()
    mock_panel.results_table = MagicMock()
    mock_panel.filter_input = MagicMock()
    mock_panel.source_filter = MagicMock()
    mock_panel.rare_eval_panel = MagicMock()
    mock_panel.check_btn = MagicMock()
    mock_panel._all_results = []

    with patch.object(window.session_tabs, 'get_current_panel', return_value=mock_panel):
        with patch.object(window.session_tabs, 'get_panel', return_value=mock_panel):
            with patch.object(window.session_tabs, 'currentIndex', return_value=0):
                window._mock_panel = mock_panel
                yield window


class TestPriceCheckerWindowInit:
    """Tests for PriceCheckerWindow initialization."""

    def test_window_title(self, window):
        """Window has correct title."""
        assert window.windowTitle() == "PoE Price Checker"

    def test_minimum_size(self, window):
        """Window has minimum size set."""
        assert window.minimumWidth() == 1200
        assert window.minimumHeight() == 800

    def test_context_stored(self, window, mock_ctx):
        """Context is stored."""
        assert window.ctx is mock_ctx

    def test_history_initialized(self, window):
        """History manager is initialized."""
        assert window._history_manager is not None
        assert window._history_manager.is_empty()

    def test_check_not_in_progress(self, window):
        """Check flag is initially False."""
        assert window._check_in_progress is False

    def test_status_bar_created(self, window):
        """Status bar is created."""
        assert window.status_bar is not None

    def test_session_tabs_created(self, window):
        """Session tabs widget is created."""
        assert window.session_tabs is not None


class TestPriceCheckerWindowDelegation:
    """Tests for __getattr__ delegation to session panel."""

    def test_delegated_attr_returns_panel_attr(self, window_with_mock_panel):
        """Delegated attrs return panel's attribute."""
        result = window_with_mock_panel.input_text
        assert result is window_with_mock_panel._mock_panel.input_text

    def test_delegated_attr_returns_none_when_no_panel(self, window):
        """Delegated attrs return None when no panel."""
        with patch.object(window.session_tabs, 'get_current_panel', return_value=None):
            result = window.input_text
            assert result is None

    def test_non_delegated_attr_raises_error(self, window):
        """Non-delegated attrs raise AttributeError."""
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = window.nonexistent_attribute

    def test_all_delegated_attrs(self, window):
        """All expected attrs are in delegated set."""
        expected = {'input_text', 'item_inspector', 'results_table',
                    'filter_input', 'source_filter', 'rare_eval_panel', 'check_btn'}
        assert PriceCheckerWindow._DELEGATED_ATTRS == expected


class TestPriceCheckerWindowStatus:
    """Tests for status bar methods."""

    def test_set_status(self, window):
        """_set_status updates status bar."""
        window._set_status("Test message")
        assert window.status_bar.currentMessage() == "Test message"

    def test_update_summary_no_panel(self, window):
        """_update_summary handles no panel."""
        with patch.object(window.session_tabs, 'get_current_panel', return_value=None):
            window._update_summary()
            assert window.summary_label.text() == "No results"

    def test_update_summary_no_results(self, window_with_mock_panel):
        """_update_summary shows 'No results' when empty."""
        window_with_mock_panel._mock_panel._all_results = []
        window_with_mock_panel._update_summary()
        assert window_with_mock_panel.summary_label.text() == "No results"

    def test_update_summary_with_results(self, window_with_mock_panel):
        """_update_summary shows count and total."""
        window_with_mock_panel._mock_panel._all_results = [
            {"chaos_value": 100.0},
            {"chaos_value": 50.5},
            {"chaos_value": 25.0},
        ]
        window_with_mock_panel._update_summary()
        assert "3 items" in window_with_mock_panel.summary_label.text()
        assert "175.5c" in window_with_mock_panel.summary_label.text()

    def test_update_summary_handles_invalid_values(self, window_with_mock_panel):
        """_update_summary handles non-numeric values."""
        window_with_mock_panel._mock_panel._all_results = [
            {"chaos_value": 100.0},
            {"chaos_value": "invalid"},
            {"chaos_value": None},
            {},
        ]
        window_with_mock_panel._update_summary()
        assert "4 items" in window_with_mock_panel.summary_label.text()
        assert "100.0c" in window_with_mock_panel.summary_label.text()


class TestPriceCheckerWindowPriceCheck:
    """Tests for price checking functionality."""

    def test_on_check_price_no_text(self, window_with_mock_panel):
        """_on_check_price does nothing with empty text."""
        window_with_mock_panel._mock_panel.input_text.toPlainText.return_value = "   "
        window_with_mock_panel._on_check_price()
        assert window_with_mock_panel.status_bar.currentMessage() == "No item text to check"

    def test_on_check_price_already_in_progress(self, window_with_mock_panel):
        """_on_check_price skips if already in progress."""
        window_with_mock_panel._check_in_progress = True
        window_with_mock_panel._on_check_price()
        # Should not call check_btn.setEnabled since we skipped
        window_with_mock_panel._mock_panel.check_btn.setEnabled.assert_not_called()

    def test_do_price_check_no_panel(self, window):
        """_do_price_check handles missing panel."""
        with patch.object(window.session_tabs, 'get_panel', return_value=None):
            window._do_price_check("test item", 0)
            assert window.status_bar.currentMessage() == "No active session"

    def test_do_price_check_error_result(self, window_with_mock_panel):
        """_do_price_check handles error result."""
        with patch.object(window_with_mock_panel._price_controller, 'check_price', return_value=Err("Parse error")):
            window_with_mock_panel._do_price_check("test item", 0)
            assert window_with_mock_panel.status_bar.currentMessage() == "Parse error"
            assert window_with_mock_panel._check_in_progress is False

    def test_do_price_check_success(self, window_with_mock_panel):
        """_do_price_check handles successful result."""
        mock_data = MagicMock()
        mock_data.parsed_item = MagicMock()
        mock_data.formatted_rows = [{"item": "test"}]
        mock_data.is_rare = False
        mock_data.evaluation = None
        mock_data.results = []

        with patch.object(window_with_mock_panel._price_controller, 'check_price', return_value=Ok(mock_data)):
            with patch.object(window_with_mock_panel._price_controller, 'get_price_summary', return_value="Found 1 result"):
                with patch.object(window_with_mock_panel._price_controller, 'should_show_toast', return_value=(False, None, None)):
                    window_with_mock_panel._do_price_check("test item", 0)
                    window_with_mock_panel._mock_panel.item_inspector.set_item.assert_called_once_with(mock_data.parsed_item)
                    window_with_mock_panel._mock_panel.set_results.assert_called_once_with(mock_data.formatted_rows)
                    assert window_with_mock_panel._check_in_progress is False

    def test_do_price_check_with_rare_evaluation(self, window_with_mock_panel):
        """_do_price_check shows rare eval panel for rare items."""
        mock_data = MagicMock()
        mock_data.parsed_item = MagicMock()
        mock_data.formatted_rows = []
        mock_data.is_rare = True
        mock_data.evaluation = MagicMock()
        mock_data.results = []

        with patch.object(window_with_mock_panel._price_controller, 'check_price', return_value=Ok(mock_data)):
            with patch.object(window_with_mock_panel._price_controller, 'get_price_summary', return_value="Rare item"):
                with patch.object(window_with_mock_panel._price_controller, 'should_show_toast', return_value=(False, None, None)):
                    window_with_mock_panel._do_price_check("rare item", 0)
                    window_with_mock_panel._mock_panel.rare_eval_panel.set_evaluation.assert_called_once_with(mock_data.evaluation)
                    window_with_mock_panel._mock_panel.rare_eval_panel.setVisible.assert_called_with(True)

    def test_do_price_check_exception(self, window_with_mock_panel):
        """_do_price_check handles exceptions."""
        with patch.object(window_with_mock_panel._price_controller, 'check_price', side_effect=RuntimeError("API error")):
            window_with_mock_panel._do_price_check("test item", 0)
            assert "Error:" in window_with_mock_panel.status_bar.currentMessage()
            assert window_with_mock_panel._check_in_progress is False


class TestPriceCheckerWindowClipboard:
    """Tests for clipboard operations."""

    def test_clear_input(self, window_with_mock_panel):
        """_clear_input clears input and inspector."""
        window_with_mock_panel._clear_input()
        window_with_mock_panel._mock_panel.input_text.clear.assert_called_once()
        window_with_mock_panel._mock_panel.item_inspector.clear.assert_called_once()

    def test_paste_and_check(self, window_with_mock_panel, qtbot):
        """_paste_and_check pastes and triggers check."""
        window_with_mock_panel._mock_panel.input_text.toPlainText.return_value = "pasted item"
        QApplication.clipboard().setText("test item text")

        with patch.object(window_with_mock_panel, '_do_price_check') as mock_check:
            window_with_mock_panel._paste_and_check()
            window_with_mock_panel._mock_panel.input_text.setPlainText.assert_called_once_with("test item text")

    def test_copy_all_as_tsv(self, window_with_mock_panel):
        """_copy_all_as_tsv copies to clipboard."""
        window_with_mock_panel._mock_panel.results_table.to_tsv.return_value = "col1\tcol2\nval1\tval2"
        window_with_mock_panel._copy_all_as_tsv()
        assert QApplication.clipboard().text() == "col1\tcol2\nval1\tval2"
        assert "copied" in window_with_mock_panel.status_bar.currentMessage().lower()


class TestPriceCheckerWindowTheme:
    """Tests for theme management."""

    def test_set_theme(self, window):
        """_set_theme calls theme controller."""
        window._theme_controller = MagicMock()

        window._set_theme(Theme.DARK)

        window._theme_controller.set_theme.assert_called_once_with(Theme.DARK, window)

    def test_toggle_theme(self, window):
        """_toggle_theme calls theme controller."""
        window._theme_controller = MagicMock()

        window._toggle_theme()

        window._theme_controller.toggle_theme.assert_called_once_with(window)

    def test_set_accent_color(self, window):
        """_set_accent_color calls theme controller."""
        window._theme_controller = MagicMock()

        window._set_accent_color("chaos")

        window._theme_controller.set_accent_color.assert_called_once_with("chaos", window)

    def test_cycle_theme(self, window):
        """_cycle_theme calls theme controller."""
        window._theme_controller = MagicMock()

        window._cycle_theme()

        window._theme_controller.cycle_theme.assert_called_once_with(window)


class TestPriceCheckerWindowMenuActions:
    """Tests for menu action handlers."""

    def test_paste_sample(self, window_with_mock_panel):
        """_paste_sample pastes sample item."""
        with patch('gui_qt.main_window.SAMPLE_ITEMS', {'map': ['Sample Map Item']}):
            window_with_mock_panel._paste_sample('map')
            window_with_mock_panel._mock_panel.input_text.setPlainText.assert_called_once_with('Sample Map Item')
            assert "sample map" in window_with_mock_panel.status_bar.currentMessage().lower()

    def test_paste_sample_empty(self, window_with_mock_panel):
        """_paste_sample handles empty sample list."""
        with patch('gui_qt.main_window.SAMPLE_ITEMS', {'map': []}):
            window_with_mock_panel._paste_sample('map')
            window_with_mock_panel._mock_panel.input_text.setPlainText.assert_not_called()

    def test_show_data_sources(self, window):
        """_show_data_sources shows info dialog."""
        with patch.object(QMessageBox, 'information') as mock_info:
            window._show_data_sources()
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "poe.ninja" in call_args[0][2]
            assert "Trade API" in call_args[0][2]

    def test_show_history_empty(self, window):
        """_show_history shows message when empty."""
        window._history_manager.clear()
        with patch.object(QMessageBox, 'information') as mock_info:
            window._show_history()
            mock_info.assert_called_once()
            assert "No items" in mock_info.call_args[0][2]

    def test_show_history_with_items(self, window):
        """_show_history opens dialog with items."""
        from core.history import HistoryEntry
        window._history_manager.add_entry_direct(HistoryEntry(
            timestamp="2025-01-01T00:00:00",
            item_text="Test Item",
            item_name="Test",
            results_count=1,
            best_price=100.0,
        ))
        with patch('gui_qt.dialogs.recent_items_dialog.RecentItemsDialog') as mock_dialog:
            mock_dialog.return_value.exec.return_value = None
            window._show_history()
            mock_dialog.assert_called_once()

    def test_recheck_item_from_history(self, window_with_mock_panel):
        """_recheck_item_from_history sets text and checks."""
        window_with_mock_panel._mock_panel.input_text.toPlainText.return_value = "history item"
        with patch.object(window_with_mock_panel, '_do_price_check') as mock_check:
            window_with_mock_panel._recheck_item_from_history("history item")
            window_with_mock_panel._mock_panel.input_text.setPlainText.assert_called_once_with("history item")


class TestPriceCheckerWindowFileOperations:
    """Tests for file-related operations."""

    def test_open_log_file_not_exists(self, window):
        """_open_log_file shows message when not exists."""
        with patch.object(Path, 'exists', return_value=False):
            with patch.object(QMessageBox, 'information') as mock_info:
                window._open_log_file()
                mock_info.assert_called_once()
                assert "No log file" in mock_info.call_args[0][2]

    def test_export_results_no_results(self, window_with_mock_panel):
        """_export_results shows message when no results."""
        window_with_mock_panel._mock_panel._all_results = []
        with patch.object(QMessageBox, 'information') as mock_info:
            window_with_mock_panel._export_results()
            mock_info.assert_called_once()
            assert "No results" in mock_info.call_args[0][2]

    def test_export_results_cancelled(self, window_with_mock_panel):
        """_export_results handles cancelled dialog."""
        window_with_mock_panel._mock_panel._all_results = [{"item": "test"}]
        with patch.object(QFileDialog, 'getSaveFileName', return_value=("", "")):
            window_with_mock_panel._export_results()
            window_with_mock_panel._mock_panel.results_table.export_tsv.assert_not_called()

    def test_export_results_success(self, window_with_mock_panel, tmp_path):
        """_export_results exports to file."""
        window_with_mock_panel._mock_panel._all_results = [{"item": "test"}]
        export_path = str(tmp_path / "export.tsv")
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(export_path, "")):
            window_with_mock_panel._export_results()
            window_with_mock_panel._mock_panel.results_table.export_tsv.assert_called_once_with(export_path)
            assert "Exported" in window_with_mock_panel.status_bar.currentMessage()


class TestPriceCheckerWindowDatabase:
    """Tests for database operations."""

    def test_wipe_database_confirmed(self, window, mock_ctx):
        """_wipe_database wipes on confirmation."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes):
            window._wipe_database()

            mock_ctx.db.wipe.assert_called_once()
            assert "wiped" in window.status_bar.currentMessage().lower()

    def test_wipe_database_cancelled(self, window, mock_ctx):
        """_wipe_database does nothing on cancel."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.No):
            window._wipe_database()

            mock_ctx.db.wipe.assert_not_called()

    def test_wipe_database_error(self, window, mock_ctx):
        """_wipe_database shows error on failure."""
        mock_ctx.db.wipe.side_effect = Exception("DB error")

        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes):
            with patch.object(QMessageBox, 'critical') as mock_critical:
                window._wipe_database()

                mock_critical.assert_called_once()


class TestPriceCheckerWindowColumnVisibility:
    """Tests for column visibility."""

    def test_toggle_column(self, window_with_mock_panel):
        """_toggle_column calls results table."""
        window_with_mock_panel._toggle_column("chaos_value", False)
        window_with_mock_panel._mock_panel.results_table.set_column_visible.assert_called_once_with("chaos_value", False)


class TestPriceCheckerWindowFocus:
    """Tests for focus management."""

    def test_focus_input(self, window_with_mock_panel):
        """_focus_input focuses input text."""
        window_with_mock_panel._focus_input()
        window_with_mock_panel._mock_panel.input_text.setFocus.assert_called_once()

    def test_focus_filter(self, window_with_mock_panel):
        """_focus_filter focuses filter input."""
        window_with_mock_panel._focus_filter()
        window_with_mock_panel._mock_panel.filter_input.setFocus.assert_called_once()
        window_with_mock_panel._mock_panel.filter_input.selectAll.assert_called_once()

    def test_toggle_rare_panel(self, window_with_mock_panel):
        """_toggle_rare_panel toggles visibility."""
        window_with_mock_panel._mock_panel.rare_eval_panel.isVisible.return_value = True
        window_with_mock_panel._toggle_rare_panel()
        window_with_mock_panel._mock_panel.rare_eval_panel.setVisible.assert_called_once_with(False)


class TestPriceCheckerWindowRankings:
    """Tests for rankings worker callbacks."""

    def test_on_rankings_progress(self, window):
        """_on_rankings_progress logs message."""
        window._on_rankings_progress("Test progress")
        # Just verify it doesn't raise

    def test_on_rankings_finished(self, window):
        """_on_rankings_finished clears worker."""
        window._rankings_worker = MagicMock()

        window._on_rankings_finished(5)

        assert window._rankings_worker is None

    def test_on_rankings_error(self, window):
        """_on_rankings_error clears worker."""
        window._rankings_worker = MagicMock()

        window._on_rankings_error("Error", "Traceback")

        assert window._rankings_worker is None


class TestPriceCheckerWindowSystemTray:
    """Tests for system tray functionality."""

    def test_should_minimize_to_tray_no_manager(self, window):
        """_should_minimize_to_tray returns False without manager."""
        window._tray_manager = None

        assert window._should_minimize_to_tray() is False

    def test_should_minimize_to_tray_not_initialized(self, window):
        """_should_minimize_to_tray returns False when not initialized."""
        window._tray_manager = MagicMock()
        window._tray_manager.is_initialized.return_value = False

        assert window._should_minimize_to_tray() is False

    def test_should_minimize_to_tray_config_disabled(self, window, mock_ctx):
        """_should_minimize_to_tray respects config."""
        window._tray_manager = MagicMock()
        window._tray_manager.is_initialized.return_value = True
        mock_ctx.config.minimize_to_tray = False

        assert window._should_minimize_to_tray() is False

    def test_should_minimize_to_tray_enabled(self, window, mock_ctx):
        """_should_minimize_to_tray returns True when enabled."""
        window._tray_manager = MagicMock()
        window._tray_manager.is_initialized.return_value = True
        mock_ctx.config.minimize_to_tray = True

        assert window._should_minimize_to_tray() is True

    def test_hide_to_tray(self, window):
        """_hide_to_tray calls tray manager."""
        window._tray_manager = MagicMock()

        window._hide_to_tray()

        window._tray_manager.hide_to_tray.assert_called_once()

    def test_show_tray_notification_disabled(self, window, mock_ctx):
        """_show_tray_notification respects config."""
        window._tray_manager = MagicMock()
        window._tray_manager.is_initialized.return_value = True
        mock_ctx.config.show_tray_notifications = False

        window._show_tray_notification("Item", 100.0)

        window._tray_manager.show_price_alert.assert_not_called()

    def test_show_tray_notification_enabled(self, window, mock_ctx):
        """_show_tray_notification shows alert when enabled."""
        window._tray_manager = MagicMock()
        window._tray_manager.is_initialized.return_value = True
        mock_ctx.config.show_tray_notifications = True

        window._show_tray_notification("Item", 100.0, 0.5)

        window._tray_manager.show_price_alert.assert_called_once_with("Item", 100.0, 0.5)


class TestPriceCheckerWindowCleanup:
    """Tests for cleanup and close."""

    def test_cleanup_before_close(self, window):
        """_cleanup_before_close cleans up resources."""
        window._rankings_worker = MagicMock()
        window._tray_manager = MagicMock()

        window._cleanup_before_close()

        window._rankings_worker.quit.assert_called_once()
        window._window_manager.close_all.assert_called_once()
        window._tray_manager.cleanup.assert_called_once()

    def test_cleanup_before_close_no_worker(self, window):
        """_cleanup_before_close handles no worker."""
        window._rankings_worker = None
        window._tray_manager = MagicMock()

        window._cleanup_before_close()  # Should not raise

    def test_quit_application(self, window):
        """_quit_application cleans up and quits."""
        with patch.object(window, '_cleanup_before_close') as mock_cleanup:
            with patch.object(QApplication, 'instance') as mock_app:
                mock_app.return_value = MagicMock()
                window._quit_application()

                mock_cleanup.assert_called_once()
                mock_app.return_value.quit.assert_called_once()


class TestPriceCheckerWindowPinning:
    """Tests for item pinning."""

    def test_on_pin_items_requested_success(self, window):
        """_on_pin_items_requested shows success toast."""
        window.pinned_items_widget = MagicMock()
        window.pinned_items_widget.pin_items.return_value = 2
        window._toast_manager = MagicMock()

        window._on_pin_items_requested([{"item": "a"}, {"item": "b"}])

        window._toast_manager.success.assert_called_once()
        assert "Pinned 2" in window._toast_manager.success.call_args[0][0]

    def test_on_pin_items_requested_already_pinned(self, window):
        """_on_pin_items_requested shows warning when already pinned."""
        window.pinned_items_widget = MagicMock()
        window.pinned_items_widget.pin_items.return_value = 0
        window._toast_manager = MagicMock()

        window._on_pin_items_requested([{"item": "a"}])

        window._toast_manager.warning.assert_called_once()

    def test_on_pinned_item_inspected_with_item(self, window_with_mock_panel):
        """_on_pinned_item_inspected updates inspector."""
        mock_item = MagicMock()
        # Mock _current_build_stats which is used in the method
        window_with_mock_panel._current_build_stats = None
        window_with_mock_panel._on_pinned_item_inspected({"_item": mock_item})
        window_with_mock_panel._mock_panel.item_inspector.set_item.assert_called()

    def test_on_pinned_item_inspected_without_item(self, window):
        """_on_pinned_item_inspected shows status without item."""
        window._on_pinned_item_inspected({"item_name": "Test Item"})

        assert "Test Item" in window.status_bar.currentMessage()


class TestPriceCheckerWindowComparison:
    """Tests for item comparison."""

    def test_on_compare_items_too_few(self, window):
        """_on_compare_items_requested warns with too few items."""
        window._toast_manager = MagicMock()

        window._on_compare_items_requested([{"item": "a"}])

        window._toast_manager.warning.assert_called_once()
        assert "2-3" in window._toast_manager.warning.call_args[0][0]

    def test_on_compare_items_too_many(self, window):
        """_on_compare_items_requested warns with too many items."""
        window._toast_manager = MagicMock()

        window._on_compare_items_requested([
            {"item": "a"}, {"item": "b"}, {"item": "c"}, {"item": "d"}
        ])

        window._toast_manager.warning.assert_called_once()

    def test_on_compare_items_valid(self, window):
        """_on_compare_items_requested opens dialog with valid items."""
        window._toast_manager = MagicMock()
        # Mock _current_build_stats which is used in the method
        window._current_build_stats = None
        items = [
            {"_item": MagicMock()},
            {"_item": MagicMock()},
        ]

        with patch('gui_qt.dialogs.item_comparison_dialog.ItemComparisonDialog') as mock_dialog:
            mock_dialog.return_value.exec.return_value = None
            window._on_compare_items_requested(items)
            mock_dialog.assert_called_once()


class TestPriceCheckerWindowResultsContextMenu:
    """Tests for results context menu."""

    def test_copy_selected_row(self, window_with_mock_panel):
        """_copy_selected_row copies to clipboard."""
        window_with_mock_panel._mock_panel.results_table.get_selected_row.return_value = {
            "item_name": "Test",
            "chaos_value": 100,
        }
        window_with_mock_panel._copy_selected_row()
        clipboard_text = QApplication.clipboard().text()
        assert "item_name: Test" in clipboard_text
        assert "chaos_value: 100" in clipboard_text

    def test_copy_row_as_tsv(self, window_with_mock_panel):
        """_copy_row_as_tsv copies tab-separated values."""
        window_with_mock_panel._mock_panel.results_table.get_selected_row.return_value = {
            "item_name": "Test",
            "chaos_value": 100,
        }
        window_with_mock_panel._mock_panel.results_table.columns = ["item_name", "chaos_value"]
        window_with_mock_panel._copy_row_as_tsv()
        clipboard_text = QApplication.clipboard().text()
        assert "\t" in clipboard_text
