"""
Tests for gui_qt.controllers.results_context_controller - ResultsContextController.
"""

import pytest
from unittest.mock import MagicMock, patch

from gui_qt.controllers.results_context_controller import (
    ResultsContextController,
    get_results_context_controller,
)


@pytest.fixture
def mock_ctx():
    """Create mock AppContext."""
    ctx = MagicMock()
    ctx.db = MagicMock()
    ctx.db.record_sale = MagicMock()
    return ctx


@pytest.fixture
def mock_parent():
    """Create mock parent widget."""
    return MagicMock()


@pytest.fixture
def mock_results_table():
    """Create mock results table widget."""
    table = MagicMock()
    table.columns = ["item_name", "chaos_value", "source", "price_explanation"]
    table.get_selected_row = MagicMock(return_value=None)
    table.mapToGlobal = MagicMock(return_value=MagicMock())
    return table


@pytest.fixture
def status_callback():
    """Create mock status callback."""
    return MagicMock()


@pytest.fixture
def toast_success_callback():
    """Create mock toast success callback."""
    return MagicMock()


@pytest.fixture
def toast_error_callback():
    """Create mock toast error callback."""
    return MagicMock()


@pytest.fixture
def controller(mock_ctx, mock_parent, status_callback, toast_success_callback, toast_error_callback):
    """Create ResultsContextController with mocked dependencies."""
    return ResultsContextController(
        ctx=mock_ctx,
        parent=mock_parent,
        on_status=status_callback,
        on_toast_success=toast_success_callback,
        on_toast_error=toast_error_callback,
    )


class TestResultsContextControllerInit:
    """Tests for ResultsContextController initialization."""

    def test_init_stores_dependencies(self, mock_ctx, mock_parent):
        """Controller should store all dependencies."""
        controller = ResultsContextController(
            ctx=mock_ctx,
            parent=mock_parent,
        )

        assert controller._ctx is mock_ctx
        assert controller._parent is mock_parent

    def test_init_with_callbacks(
        self, mock_ctx, mock_parent, status_callback, toast_success_callback, toast_error_callback
    ):
        """Controller should store callbacks."""
        controller = ResultsContextController(
            ctx=mock_ctx,
            parent=mock_parent,
            on_status=status_callback,
            on_toast_success=toast_success_callback,
            on_toast_error=toast_error_callback,
        )

        # Call status to verify it's wired up
        controller._on_status("test")
        status_callback.assert_called_with("test")

    def test_init_default_callbacks(self, mock_ctx, mock_parent):
        """Controller should have default no-op callbacks."""
        controller = ResultsContextController(
            ctx=mock_ctx,
            parent=mock_parent,
        )

        # Should not raise - uses no-op callbacks
        controller._on_status("test")
        controller._on_toast_success("test")
        controller._on_toast_error("test")


class TestShowContextMenu:
    """Tests for show_context_menu method."""

    def test_show_context_menu_no_selection(
        self, controller, mock_results_table
    ):
        """Context menu should still show even with no selection."""
        mock_results_table.get_selected_row.return_value = None

        with patch("gui_qt.controllers.results_context_controller.QMenu") as mock_menu_class:
            mock_menu = MagicMock()
            mock_menu_class.return_value = mock_menu

            controller.show_context_menu(MagicMock(), mock_results_table)

            mock_menu.exec.assert_called_once()

    def test_show_context_menu_with_selection(
        self, controller, mock_results_table
    ):
        """Context menu should show actions when row is selected."""
        mock_results_table.get_selected_row.return_value = {
            "item_name": "Test Item",
            "chaos_value": 100.0,
            "source": "test",
        }

        with patch("gui_qt.controllers.results_context_controller.QMenu") as mock_menu_class:
            mock_menu = MagicMock()
            mock_menu_class.return_value = mock_menu

            controller.show_context_menu(MagicMock(), mock_results_table)

            # Should add actions for selected row
            assert mock_menu.addAction.call_count >= 4  # Copy Row, Copy TSV, Why This Price, Record Sale
            mock_menu.exec.assert_called_once()


class TestCopyMethods:
    """Tests for copy methods."""

    def test_copy_selected_row(self, controller, mock_results_table, status_callback):
        """Should copy selected row as formatted text."""
        mock_results_table.get_selected_row.return_value = {
            "item_name": "Tabula Rasa",
            "chaos_value": 50.0,
            "source": "poe.ninja",
            "price_explanation": "{}",  # Should be excluded
        }

        with patch("gui_qt.controllers.results_context_controller.QApplication") as mock_app:
            mock_clipboard = MagicMock()
            mock_app.clipboard.return_value = mock_clipboard

            controller._copy_selected_row(mock_results_table)

            mock_clipboard.setText.assert_called_once()
            text = mock_clipboard.setText.call_args[0][0]
            assert "Tabula Rasa" in text
            assert "50.0" in text
            assert "price_explanation" not in text

            status_callback.assert_called_with("Row copied to clipboard")

    def test_copy_row_as_tsv(self, controller, mock_results_table, status_callback):
        """Should copy selected row as TSV."""
        mock_results_table.get_selected_row.return_value = {
            "item_name": "Tabula Rasa",
            "chaos_value": 50.0,
            "source": "poe.ninja",
            "price_explanation": "{}",
        }

        with patch("gui_qt.controllers.results_context_controller.QApplication") as mock_app:
            mock_clipboard = MagicMock()
            mock_app.clipboard.return_value = mock_clipboard

            controller._copy_row_as_tsv(mock_results_table)

            mock_clipboard.setText.assert_called_once()
            text = mock_clipboard.setText.call_args[0][0]
            assert "\t" in text  # TSV format

            status_callback.assert_called_with("Row copied as TSV")

    def test_copy_no_selection(self, controller, mock_results_table, status_callback):
        """Copy methods should do nothing when no selection."""
        mock_results_table.get_selected_row.return_value = None

        with patch("gui_qt.controllers.results_context_controller.QApplication") as mock_app:
            controller._copy_selected_row(mock_results_table)
            controller._copy_row_as_tsv(mock_results_table)

            mock_app.clipboard.assert_not_called()
            status_callback.assert_not_called()


class TestExplainPrice:
    """Tests for price explanation dialog."""

    def test_explain_price_no_selection(self, controller, mock_results_table):
        """Should do nothing when no row selected."""
        mock_results_table.get_selected_row.return_value = None

        with patch("gui_qt.controllers.results_context_controller.QMessageBox") as mock_box:
            controller._explain_price(mock_results_table)
            mock_box.information.assert_not_called()

    def test_explain_price_no_explanation(self, controller, mock_results_table, mock_parent):
        """Should show basic info when no explanation available."""
        mock_results_table.get_selected_row.return_value = {
            "item_name": "Test Item",
            "chaos_value": 100.0,
            "source": "test",
            "price_explanation": "",
        }

        with patch("gui_qt.controllers.results_context_controller.QMessageBox") as mock_box:
            controller._explain_price(mock_results_table)
            mock_box.information.assert_called_once()
            call_args = mock_box.information.call_args
            assert "Test Item" in call_args[0][2]
            assert "100" in call_args[0][2]


class TestRecordSale:
    """Tests for record sale functionality."""

    def test_record_sale_no_selection(self, controller, mock_results_table):
        """Should do nothing when no row selected."""
        mock_results_table.get_selected_row.return_value = None

        with patch("gui_qt.dialogs.record_sale_dialog.RecordSaleDialog"):
            # Should return early without showing dialog
            controller._record_sale(mock_results_table)

    def test_record_sale_cancelled(self, controller, mock_results_table):
        """Should not record when dialog is cancelled."""
        mock_results_table.get_selected_row.return_value = {
            "item_name": "Test Item",
            "chaos_value": 100.0,
            "source": "test",
        }

        with patch("gui_qt.dialogs.record_sale_dialog.RecordSaleDialog") as mock_dialog_class:
            from PyQt6.QtWidgets import QDialog

            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            mock_dialog_class.return_value = mock_dialog

            controller._record_sale(mock_results_table)

            controller._ctx.db.record_sale.assert_not_called()

    def test_record_sale_success(
        self, controller, mock_results_table, mock_ctx, status_callback, toast_success_callback
    ):
        """Should record sale when dialog is accepted."""
        mock_results_table.get_selected_row.return_value = {
            "item_name": "Test Item",
            "chaos_value": 100.0,
            "source": "test",
        }

        with patch("gui_qt.dialogs.record_sale_dialog.RecordSaleDialog") as mock_dialog_class:
            from PyQt6.QtWidgets import QDialog

            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_values.return_value = (95.0, "quick sale")
            mock_dialog_class.return_value = mock_dialog

            controller._record_sale(mock_results_table)

            mock_ctx.db.record_sale.assert_called_once_with(
                item_name="Test Item",
                chaos_value=95.0,
                source="test",
                notes="quick sale",
            )
            status_callback.assert_called()
            toast_success_callback.assert_called()


class TestGetResultsContextController:
    """Tests for factory function."""

    def test_get_results_context_controller_returns_instance(
        self, mock_ctx, mock_parent
    ):
        """Factory should return a ResultsContextController."""
        controller = get_results_context_controller(
            ctx=mock_ctx,
            parent=mock_parent,
        )

        assert isinstance(controller, ResultsContextController)

    def test_get_results_context_controller_with_callbacks(
        self, mock_ctx, mock_parent, status_callback, toast_success_callback, toast_error_callback
    ):
        """Factory should pass all parameters."""
        controller = get_results_context_controller(
            ctx=mock_ctx,
            parent=mock_parent,
            on_status=status_callback,
            on_toast_success=toast_success_callback,
            on_toast_error=toast_error_callback,
        )

        controller._on_status("test")
        status_callback.assert_called_with("test")
