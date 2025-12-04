"""
Tests for SalesDashboardWindow.

Tests the window for displaying sales analytics and statistics.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget

pytestmark = pytest.mark.unit


# ============================================================================
# DailyStatsModel Tests
# ============================================================================


class TestDailyStatsModel:
    """Tests for DailyStatsModel."""

    def test_model_initialization(self, qtbot):
        """Model initializes with empty data."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        assert model.rowCount() == 0
        assert model.columnCount() == 4
        assert len(model.COLUMNS) == 4

    def test_model_columns_structure(self, qtbot):
        """Model has expected column structure."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        expected_columns = ["date", "count", "total_chaos", "avg_chaos"]
        actual_columns = [col[0] for col in model.COLUMNS]

        assert actual_columns == expected_columns

    def test_set_data_updates_model(self, qtbot):
        """set_data() updates the model with new data."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [
            {"date": "2025-01-01", "count": 5, "total_chaos": 100.0, "avg_chaos": 20.0},
            {"date": "2025-01-02", "count": 3, "total_chaos": 45.0, "avg_chaos": 15.0},
        ]

        model.set_data(data)

        assert model.rowCount() == 2
        assert model.columnCount() == 4

    def test_data_display_role_basic_strings(self, qtbot):
        """data() returns correct string values for DisplayRole."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [
            {"date": "2025-01-01", "count": 5, "total_chaos": 100.0, "avg_chaos": 20.0}
        ]

        model.set_data(data)

        # Test date column (index 0)
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "2025-01-01"

        # Test count column (index 1)
        index = model.index(0, 1)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "5"

    def test_data_display_role_chaos_formatting(self, qtbot):
        """data() formats chaos values with one decimal place."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [
            {
                "date": "2025-01-01",
                "count": 5,
                "total_chaos": 123.456,
                "avg_chaos": 78.901,
            }
        ]

        model.set_data(data)

        # Test total_chaos column (index 2)
        index = model.index(0, 2)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "123.5"

        # Test avg_chaos column (index 3)
        index = model.index(0, 3)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "78.9"

    def test_data_display_role_empty_values(self, qtbot):
        """data() handles empty values correctly."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [{"date": "", "count": "", "total_chaos": None, "avg_chaos": None}]

        model.set_data(data)

        # Date and count should be empty string
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == ""
        index = model.index(0, 1)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == ""

        # Chaos values should default to "0.0"
        index = model.index(0, 2)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "0.0"
        index = model.index(0, 3)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "0.0"

    def test_data_text_alignment_numeric_columns(self, qtbot):
        """Numeric columns have right alignment."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [
            {"date": "2025-01-01", "count": 5, "total_chaos": 100.0, "avg_chaos": 20.0}
        ]

        model.set_data(data)

        # Test count, total_chaos, avg_chaos columns (indices 1, 2, 3)
        for col in [1, 2, 3]:
            index = model.index(0, col)
            alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
            assert alignment == (
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

    def test_data_text_alignment_date_column(self, qtbot):
        """Date column has no special alignment."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [{"date": "2025-01-01", "count": 5}]
        model.set_data(data)

        # Test date column (index 0)
        index = model.index(0, 0)
        alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert alignment is None

    def test_data_invalid_index_returns_none(self, qtbot):
        """data() returns None for invalid indices."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [{"date": "2025-01-01", "count": 5}]
        model.set_data(data)

        # Invalid row
        index = model.index(10, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) is None

        # Invalid index
        from PyQt6.QtCore import QModelIndex

        invalid_index = QModelIndex()
        assert model.data(invalid_index, Qt.ItemDataRole.DisplayRole) is None

    def test_header_data_horizontal(self, qtbot):
        """headerData() returns column headers."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        expected_headers = ["Date", "Sales", "Total (c)", "Average (c)"]

        for col, expected in enumerate(expected_headers):
            result = model.headerData(
                col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
            )
            assert result == expected

    def test_header_data_non_display_role_returns_none(self, qtbot):
        """headerData() returns None for non-DisplayRole."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        result = model.headerData(
            0, Qt.Orientation.Horizontal, Qt.ItemDataRole.EditRole
        )
        assert result is None

    def test_header_data_vertical_returns_none(self, qtbot):
        """headerData() returns None for vertical orientation."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        result = model.headerData(
            0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole
        )
        assert result is None

    def test_data_chaos_value_error_handling(self, qtbot):
        """data() handles invalid chaos values gracefully."""
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        model = DailyStatsModel()

        data = [
            {
                "date": "2025-01-01",
                "count": 5,
                "total_chaos": "invalid",
                "avg_chaos": "bad",
            }
        ]

        model.set_data(data)

        # Should return "0.0" for invalid values
        index = model.index(0, 2)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "0.0"
        index = model.index(0, 3)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "0.0"


# ============================================================================
# SalesDashboardWindow Tests
# ============================================================================


class TestSalesDashboardWindow:
    """Tests for SalesDashboardWindow."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock AppContext."""
        mock = MagicMock()
        mock.db = MagicMock()
        mock.db.get_recent_sales.return_value = []
        return mock

    def test_window_initialization(self, qtbot, mock_ctx):
        """Window initializes with correct properties."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.windowTitle() == "Sales Dashboard"
        assert window.minimumSize().width() == 450
        assert window.minimumSize().height() == 400
        assert window.isSizeGripEnabled()

    def test_window_stores_context(self, qtbot, mock_ctx):
        """Window stores AppContext reference."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.ctx is mock_ctx

    def test_widgets_created(self, qtbot, mock_ctx):
        """All UI widgets are created."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Control widgets
        assert hasattr(window, "days_spin")
        assert hasattr(window, "refresh_btn")

        # Summary labels
        assert hasattr(window, "total_sales_label")
        assert hasattr(window, "total_chaos_label")
        assert hasattr(window, "avg_chaos_label")
        assert hasattr(window, "most_sold_label")

        # Table
        assert hasattr(window, "table")
        assert hasattr(window, "_model")

    def test_days_spin_properties(self, qtbot, mock_ctx):
        """Days spin box has correct range and default."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.days_spin.minimum() == 7
        assert window.days_spin.maximum() == 365
        assert window.days_spin.value() == 30

    def test_refresh_button_properties(self, qtbot, mock_ctx):
        """Refresh button has correct properties."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.refresh_btn.text() == "Refresh"

    def test_summary_labels_initial_state(self, qtbot, mock_ctx):
        """Summary labels are populated after initialization."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # With empty data, labels show 0 values
        assert window.total_sales_label.text() == "0"
        assert window.total_chaos_label.text() == "0.0c"
        assert window.avg_chaos_label.text() == "0.0c"
        assert window.most_sold_label.text() == "-"

    def test_table_properties(self, qtbot, mock_ctx):
        """Table has correct properties."""
        from PyQt6.QtWidgets import QAbstractItemView
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.table.model() is window._model
        assert (
            window.table.selectionBehavior()
            == QAbstractItemView.SelectionBehavior.SelectRows
        )
        assert window.table.alternatingRowColors()
        assert window.table.isSortingEnabled()

    def test_table_column_widths_set(self, qtbot, mock_ctx):
        """Table column widths are set from model."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Verify widths match COLUMNS definition for first 3 columns
        # (last column stretches to fill available space)
        from gui_qt.windows.sales_dashboard_window import DailyStatsModel

        for i in range(len(DailyStatsModel.COLUMNS) - 1):
            _, _, expected_width = DailyStatsModel.COLUMNS[i]
            actual_width = window.table.columnWidth(i)
            assert actual_width == expected_width

    def test_load_data_called_on_init(self, qtbot, mock_ctx):
        """_load_data is called during initialization."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should have called db.get_recent_sales
        mock_ctx.db.get_recent_sales.assert_called()

    def test_load_data_filters_by_date_range(self, qtbot, mock_ctx):
        """_load_data filters sales by date range."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()
        old_sale = now - timedelta(days=50)
        recent_sale = now - timedelta(days=10)

        mock_ctx.db.get_recent_sales.return_value = [
            {"sold_at": old_sale, "chaos_value": 5.0, "item_name": "Old Item"},
            {
                "sold_at": recent_sale,
                "chaos_value": 10.0,
                "item_name": "Recent Item",
            },
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Default is 30 days, so only recent_sale should be counted
        assert window.total_sales_label.text() == "1"

    def test_load_data_calculates_summary_stats(self, qtbot, mock_ctx):
        """_load_data calculates summary statistics correctly."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()

        mock_ctx.db.get_recent_sales.return_value = [
            {
                "sold_at": now - timedelta(days=1),
                "chaos_value": 10.0,
                "item_name": "Item1",
            },
            {
                "sold_at": now - timedelta(days=2),
                "chaos_value": 20.0,
                "item_name": "Item2",
            },
            {
                "sold_at": now - timedelta(days=3),
                "chaos_value": 30.0,
                "item_name": "Item3",
            },
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.total_sales_label.text() == "3"
        assert window.total_chaos_label.text() == "60.0c"
        assert window.avg_chaos_label.text() == "20.0c"

    def test_load_data_finds_most_sold_item(self, qtbot, mock_ctx):
        """_load_data identifies the most sold item."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()

        mock_ctx.db.get_recent_sales.return_value = [
            {
                "sold_at": now - timedelta(days=1),
                "item_name": "Goldrim",
                "chaos_value": 5.0,
            },
            {
                "sold_at": now - timedelta(days=2),
                "item_name": "Tabula Rasa",
                "chaos_value": 10.0,
            },
            {
                "sold_at": now - timedelta(days=3),
                "item_name": "Goldrim",
                "chaos_value": 5.0,
            },
            {
                "sold_at": now - timedelta(days=4),
                "item_name": "Goldrim",
                "chaos_value": 5.0,
            },
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert "Goldrim" in window.most_sold_label.text()
        assert "(3x)" in window.most_sold_label.text()

    def test_load_data_handles_empty_data(self, qtbot, mock_ctx):
        """_load_data handles empty sales data."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        mock_ctx.db.get_recent_sales.return_value = []

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.total_sales_label.text() == "0"
        assert window.total_chaos_label.text() == "0.0c"
        assert window.avg_chaos_label.text() == "0.0c"
        assert window.most_sold_label.text() == "-"

    def test_load_data_handles_none_chaos_values(self, qtbot, mock_ctx):
        """_load_data handles None chaos values."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()

        mock_ctx.db.get_recent_sales.return_value = [
            {"sold_at": now - timedelta(days=1), "chaos_value": 10.0},
            {"sold_at": now - timedelta(days=2), "chaos_value": None},
            {"sold_at": now - timedelta(days=3), "chaos_value": 20.0},
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.total_chaos_label.text() == "30.0c"

    def test_load_data_calculates_daily_stats(self, qtbot, mock_ctx):
        """_load_data calculates daily breakdown statistics."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()
        today = now.replace(hour=12, minute=0, second=0, microsecond=0)

        mock_ctx.db.get_recent_sales.return_value = [
            {"sold_at": today, "chaos_value": 10.0, "item_name": "Item1"},
            {"sold_at": today, "chaos_value": 20.0, "item_name": "Item2"},
            {
                "sold_at": today - timedelta(days=1),
                "chaos_value": 30.0,
                "item_name": "Item3",
            },
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should have 2 rows in daily stats
        assert window._model.rowCount() == 2

    def test_load_data_handles_string_datetime(self, qtbot, mock_ctx):
        """_load_data handles datetime as ISO string."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()
        now_str = now.isoformat()

        mock_ctx.db.get_recent_sales.return_value = [
            {"sold_at": now_str, "chaos_value": 10.0, "item_name": "Item1"}
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should not crash
        assert window.total_sales_label.text() == "1"

    def test_load_data_skips_invalid_datetime_strings(self, qtbot, mock_ctx):
        """_load_data skips sales with invalid datetime strings."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()

        mock_ctx.db.get_recent_sales.return_value = [
            {"sold_at": now - timedelta(days=1), "chaos_value": 10.0},
            {"sold_at": "invalid-datetime", "chaos_value": 20.0},
            {"sold_at": now - timedelta(days=2), "chaos_value": 30.0},
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should only count valid datetime sales
        assert window.total_sales_label.text() == "2"

    def test_load_data_handles_database_error(self, qtbot, mock_ctx):
        """_load_data handles database errors gracefully."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        mock_ctx.db.get_recent_sales.side_effect = Exception("Database error")

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should show error
        assert window.total_sales_label.text() == "Error"
        assert window._model.rowCount() == 0

    def test_refresh_button_triggers_load(self, qtbot, mock_ctx):
        """Clicking refresh button reloads data."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Reset call count
        mock_ctx.db.get_recent_sales.reset_mock()

        # Click refresh
        qtbot.mouseClick(window.refresh_btn, Qt.MouseButton.LeftButton)

        # Should call get_recent_sales again
        mock_ctx.db.get_recent_sales.assert_called_once()

    def test_days_spin_change_triggers_load(self, qtbot, mock_ctx):
        """Changing days spin box reloads data."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Reset call count
        mock_ctx.db.get_recent_sales.reset_mock()

        # Change days
        window.days_spin.setValue(60)

        # Should call get_recent_sales again
        mock_ctx.db.get_recent_sales.assert_called_once()

    def test_daily_stats_sorted_by_date_descending(self, qtbot, mock_ctx):
        """Daily stats are sorted by date in descending order."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()

        mock_ctx.db.get_recent_sales.return_value = [
            {
                "sold_at": now - timedelta(days=3),
                "chaos_value": 10.0,
                "item_name": "Item1",
            },
            {
                "sold_at": now - timedelta(days=1),
                "chaos_value": 20.0,
                "item_name": "Item2",
            },
            {
                "sold_at": now - timedelta(days=2),
                "chaos_value": 30.0,
                "item_name": "Item3",
            },
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Get first row's date (should be most recent)
        index = window._model.index(0, 0)
        first_date = window._model.data(index, Qt.ItemDataRole.DisplayRole)

        # Get last row's date (should be oldest)
        last_row = window._model.rowCount() - 1
        index = window._model.index(last_row, 0)
        last_date = window._model.data(index, Qt.ItemDataRole.DisplayRole)

        # First date should be >= last date (descending order)
        assert first_date >= last_date

    def test_daily_stats_calculates_averages(self, qtbot, mock_ctx):
        """Daily stats calculate average price per sale."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()
        today = now.replace(hour=12, minute=0, second=0, microsecond=0)

        mock_ctx.db.get_recent_sales.return_value = [
            {"sold_at": today, "chaos_value": 10.0, "item_name": "Item1"},
            {"sold_at": today, "chaos_value": 20.0, "item_name": "Item2"},
            {"sold_at": today, "chaos_value": 30.0, "item_name": "Item3"},
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Get average for today
        index = window._model.index(0, 3)  # avg_chaos column
        avg = window._model.data(index, Qt.ItemDataRole.DisplayRole)

        # Average should be (10 + 20 + 30) / 3 = 20.0
        assert avg == "20.0"

    def test_window_icon_applied(self, qtbot, mock_ctx):
        """Window icon is applied."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        with patch(
            "gui_qt.windows.sales_dashboard_window.apply_window_icon"
        ) as mock_icon:
            window = SalesDashboardWindow(mock_ctx)
            qtbot.addWidget(window)

            mock_icon.assert_called_once_with(window)

    def test_load_data_skips_sales_without_sold_at(self, qtbot, mock_ctx):
        """_load_data skips sales without sold_at field."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        now = datetime.now()

        mock_ctx.db.get_recent_sales.return_value = [
            {"sold_at": now - timedelta(days=1), "chaos_value": 10.0},
            {"sold_at": None, "chaos_value": 20.0},
            {"chaos_value": 30.0},  # Missing sold_at
        ]

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should only count sales with valid sold_at
        assert window.total_sales_label.text() == "1"

    def test_load_data_with_large_limit(self, qtbot, mock_ctx):
        """_load_data uses large limit (9999) to get all recent sales."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        window = SalesDashboardWindow(mock_ctx)
        qtbot.addWidget(window)

        # Verify that get_recent_sales was called with limit=9999
        mock_ctx.db.get_recent_sales.assert_called_with(limit=9999)
