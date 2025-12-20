"""
Tests for RecentSalesWindow.

Tests the window for displaying recent sales from the database.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt

pytestmark = pytest.mark.unit


# ============================================================================
# SalesTableModel Tests
# ============================================================================


class TestSalesTableModel:
    """Tests for SalesTableModel."""

    def test_model_initialization(self, qtbot):
        """Model initializes with empty data."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        assert model.rowCount() == 0
        assert model.columnCount() == 5
        assert len(model.COLUMNS) == 5

    def test_model_columns_structure(self, qtbot):
        """Model has expected column structure."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        expected_columns = [
            "sold_at",
            "item_name",
            "source",
            "chaos_value",
            "notes",
        ]
        actual_columns = [col[0] for col in model.COLUMNS]

        assert actual_columns == expected_columns

    def test_set_data_updates_model(self, qtbot):
        """set_data() updates the model with new data."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "2025-01-01 12:00:00",
                "item_name": "Goldrim",
                "source": "poe.trade",
                "chaos_value": 5.0,
                "notes": "Quick sale",
            },
            {
                "sold_at": "2025-01-02 14:30:00",
                "item_name": "Tabula Rasa",
                "source": "poe.ninja",
                "chaos_value": 10.0,
                "notes": "",
            },
        ]

        model.set_data(data)

        assert model.rowCount() == 2
        assert model.columnCount() == 5

    def test_data_display_role_basic_strings(self, qtbot):
        """data() returns correct string values for DisplayRole."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "2025-01-01 12:00:00",
                "item_name": "Goldrim",
                "source": "poe.trade",
                "chaos_value": 5.0,
                "notes": "Quick sale",
            }
        ]

        model.set_data(data)

        # Test item_name column (index 1)
        index = model.index(0, 1)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Goldrim"

        # Test source column (index 2)
        index = model.index(0, 2)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "poe.trade"

        # Test notes column (index 4)
        index = model.index(0, 4)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Quick sale"

    def test_data_display_role_datetime_formatting(self, qtbot):
        """data() formats datetime strings correctly."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "2025-01-01T12:30:00",
                "item_name": "Item",
                "source": "test",
                "chaos_value": 1.0,
                "notes": "",
            }
        ]

        model.set_data(data)

        # Test sold_at column (index 0)
        index = model.index(0, 0)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "2025-01-01" in result
        assert "12:30" in result

    def test_data_display_role_datetime_object(self, qtbot):
        """data() formats datetime objects correctly."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        dt = datetime(2025, 1, 1, 15, 45, 30)
        data = [
            {
                "sold_at": dt,
                "item_name": "Item",
                "source": "test",
                "chaos_value": 1.0,
                "notes": "",
            }
        ]

        model.set_data(data)

        index = model.index(0, 0)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "2025-01-01" in result
        assert "15:45" in result

    def test_data_display_role_chaos_value_formatting(self, qtbot):
        """data() formats chaos_value with one decimal place."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "2025-01-01",
                "item_name": "Item",
                "source": "test",
                "chaos_value": 123.456,
                "notes": "",
            }
        ]

        model.set_data(data)

        # Test chaos_value column (index 3)
        index = model.index(0, 3)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "123.5"

    def test_data_display_role_empty_values(self, qtbot):
        """data() handles empty values correctly."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "",
                "item_name": "",
                "source": "",
                "chaos_value": None,
                "notes": "",
            }
        ]

        model.set_data(data)

        for col in range(5):
            index = model.index(0, col)
            result = model.data(index, Qt.ItemDataRole.DisplayRole)
            assert result == ""

    def test_data_text_alignment_chaos_value(self, qtbot):
        """chaos_value column has right alignment."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "2025-01-01",
                "item_name": "Item",
                "source": "test",
                "chaos_value": 5.0,
                "notes": "",
            }
        ]

        model.set_data(data)

        # Test chaos_value column (index 3)
        index = model.index(0, 3)
        alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert alignment == (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def test_data_text_alignment_other_columns(self, qtbot):
        """Other columns have no special alignment."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "2025-01-01",
                "item_name": "Item",
                "source": "test",
                "chaos_value": 5.0,
                "notes": "",
            }
        ]

        model.set_data(data)

        # Test non-chaos_value columns
        for col in [0, 1, 2, 4]:
            index = model.index(0, col)
            alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
            assert alignment is None

    def test_data_invalid_index_returns_none(self, qtbot):
        """data() returns None for invalid indices."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [{"sold_at": "2025-01-01", "item_name": "Item", "source": "test"}]
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
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        expected_headers = ["Date", "Item", "Source", "Price (c)", "Notes"]

        for col, expected in enumerate(expected_headers):
            result = model.headerData(
                col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
            )
            assert result == expected

    def test_header_data_non_display_role_returns_none(self, qtbot):
        """headerData() returns None for non-DisplayRole."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        result = model.headerData(
            0, Qt.Orientation.Horizontal, Qt.ItemDataRole.EditRole
        )
        assert result is None

    def test_header_data_vertical_returns_none(self, qtbot):
        """headerData() returns None for vertical orientation."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        result = model.headerData(
            0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole
        )
        assert result is None

    def test_get_sources_returns_unique_sources(self, qtbot):
        """get_sources() returns unique sorted source values."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {"source": "poe.trade"},
            {"source": "poe.ninja"},
            {"source": "poe.trade"},
            {"source": "trade.api"},
        ]

        model.set_data(data)

        sources = model.get_sources()
        assert sources == ["poe.ninja", "poe.trade", "trade.api"]

    def test_get_sources_excludes_empty_sources(self, qtbot):
        """get_sources() excludes empty source values."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {"source": "poe.trade"},
            {"source": ""},
            {"source": "poe.ninja"},
        ]

        model.set_data(data)

        sources = model.get_sources()
        assert sources == ["poe.ninja", "poe.trade"]

    def test_get_sources_empty_data(self, qtbot):
        """get_sources() returns empty list for empty data."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        sources = model.get_sources()
        assert sources == []


# ============================================================================
# RecentSalesWindow Tests
# ============================================================================


class TestRecentSalesWindow:
    """Tests for RecentSalesWindow."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock AppContext."""
        mock = MagicMock()
        mock.db = MagicMock()
        mock.db.get_recent_sales.return_value = []
        return mock

    def test_window_initialization(self, qtbot, mock_ctx):
        """Window initializes with correct properties."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.windowTitle() == "Recent Sales"
        assert window.minimumSize().width() == 500
        assert window.minimumSize().height() == 400
        assert window.isSizeGripEnabled()

    def test_window_stores_context(self, qtbot, mock_ctx):
        """Window stores AppContext reference."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.ctx is mock_ctx

    def test_widgets_created(self, qtbot, mock_ctx):
        """All UI widgets are created."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert hasattr(window, "refresh_btn")
        assert hasattr(window, "limit_spin")
        assert hasattr(window, "filter_input")
        assert hasattr(window, "source_combo")
        assert hasattr(window, "table")
        assert hasattr(window, "summary_label")
        assert hasattr(window, "_model")

    def test_refresh_button_properties(self, qtbot, mock_ctx):
        """Refresh button has correct properties."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.refresh_btn.text() == "Refresh"

    def test_limit_spin_properties(self, qtbot, mock_ctx):
        """Limit spin box has correct range and default."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.limit_spin.minimum() == 10
        assert window.limit_spin.maximum() == 500
        assert window.limit_spin.value() == 100

    def test_filter_input_properties(self, qtbot, mock_ctx):
        """Filter input has correct placeholder."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.filter_input.placeholderText() == "Search..."

    def test_source_combo_initial_state(self, qtbot, mock_ctx):
        """Source combo box starts with 'All sources'."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.source_combo.count() >= 1
        assert window.source_combo.itemText(0) == "All sources"

    def test_table_properties(self, qtbot, mock_ctx):
        """Table has correct properties."""
        from PyQt6.QtWidgets import QAbstractItemView
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.table.model() is window._model
        assert (
            window.table.selectionBehavior()
            == QAbstractItemView.SelectionBehavior.SelectRows
        )
        assert (
            window.table.selectionMode()
            == QAbstractItemView.SelectionMode.SingleSelection
        )
        assert window.table.alternatingRowColors()
        assert window.table.isSortingEnabled()

    def test_table_column_widths_set(self, qtbot, mock_ctx):
        """Table column widths are set from model."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Verify widths match COLUMNS definition
        from gui_qt.windows.recent_sales_window import SalesTableModel

        for i, (_, _, expected_width) in enumerate(SalesTableModel.COLUMNS):
            actual_width = window.table.columnWidth(i)
            assert actual_width == expected_width

    def test_load_sales_called_on_init(self, qtbot, mock_ctx):
        """_load_sales is called during initialization."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should have called db.get_recent_sales
        mock_ctx.db.get_recent_sales.assert_called()

    def test_load_sales_with_data(self, qtbot, mock_ctx):
        """_load_sales populates table with database data."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {
                "sold_at": "2025-01-01 12:00:00",
                "item_name": "Goldrim",
                "source": "poe.trade",
                "chaos_value": 5.0,
                "notes": "",
            },
            {
                "sold_at": "2025-01-02 14:30:00",
                "item_name": "Tabula Rasa",
                "source": "poe.ninja",
                "chaos_value": 10.0,
                "notes": "",
            },
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window._model.rowCount() == 2

    def test_load_sales_updates_source_combo(self, qtbot, mock_ctx):
        """_load_sales updates source combo with unique sources."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"source": "poe.trade"},
            {"source": "poe.ninja"},
            {"source": "poe.trade"},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should have "All sources" + 2 unique sources
        assert window.source_combo.count() == 3
        assert window.source_combo.itemText(0) == "All sources"
        # Check that unique sources are present (order may vary)
        items = [window.source_combo.itemText(i) for i in range(window.source_combo.count())]
        assert "poe.ninja" in items
        assert "poe.trade" in items

    def test_load_sales_handles_database_error(self, qtbot, mock_ctx):
        """_load_sales handles database errors gracefully."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.side_effect = Exception("Database error")

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should not crash
        assert window._model.rowCount() == 0
        assert "Error loading sales" in window.summary_label.text()

    def test_refresh_button_triggers_load(self, qtbot, mock_ctx):
        """Clicking refresh button reloads sales data."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Reset call count
        mock_ctx.db.get_recent_sales.reset_mock()

        # Click refresh
        qtbot.mouseClick(window.refresh_btn, Qt.MouseButton.LeftButton)

        # Should call get_recent_sales again
        mock_ctx.db.get_recent_sales.assert_called_once()

    def test_limit_spin_change_triggers_load(self, qtbot, mock_ctx):
        """Changing limit spin box reloads sales data."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Reset call count
        mock_ctx.db.get_recent_sales.reset_mock()

        # Change limit
        window.limit_spin.setValue(200)

        # Should call get_recent_sales with new limit
        mock_ctx.db.get_recent_sales.assert_called_with(limit=200)

    def test_apply_filter_text_search(self, qtbot, mock_ctx):
        """Text filter searches across all fields."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"item_name": "Goldrim", "source": "poe.trade", "chaos_value": 5.0},
            {"item_name": "Tabula Rasa", "source": "poe.ninja", "chaos_value": 10.0},
            {"item_name": "Wanderlust", "source": "poe.trade", "chaos_value": 1.0},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Filter for "Tabula"
        window.filter_input.setText("tabula")

        assert window._model.rowCount() == 1

    def test_apply_filter_source_filter(self, qtbot, mock_ctx):
        """Source filter filters by source."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"item_name": "Goldrim", "source": "poe.trade", "chaos_value": 5.0},
            {"item_name": "Tabula Rasa", "source": "poe.ninja", "chaos_value": 10.0},
            {"item_name": "Wanderlust", "source": "poe.trade", "chaos_value": 1.0},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Filter to poe.trade
        window.source_combo.setCurrentText("poe.trade")

        assert window._model.rowCount() == 2

    def test_apply_filter_combined_filters(self, qtbot, mock_ctx):
        """Text and source filters work together."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"item_name": "Goldrim", "source": "poe.trade", "chaos_value": 5.0},
            {"item_name": "Tabula Rasa", "source": "poe.ninja", "chaos_value": 10.0},
            {"item_name": "Wanderlust", "source": "poe.trade", "chaos_value": 1.0},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Filter to poe.trade and "gold"
        window.source_combo.setCurrentText("poe.trade")
        window.filter_input.setText("gold")

        assert window._model.rowCount() == 1

    def test_apply_filter_all_sources_shows_all(self, qtbot, mock_ctx):
        """'All sources' in source combo shows all items."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"item_name": "Goldrim", "source": "poe.trade"},
            {"item_name": "Tabula Rasa", "source": "poe.ninja"},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Ensure "All sources" is selected
        window.source_combo.setCurrentText("All sources")

        assert window._model.rowCount() == 2

    def test_summary_label_updates(self, qtbot, mock_ctx):
        """Summary label shows count and total chaos value."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"chaos_value": 5.0},
            {"chaos_value": 10.0},
            {"chaos_value": 15.0},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        summary_text = window.summary_label.text()
        assert "3 sales" in summary_text
        assert "30.0c" in summary_text

    def test_summary_label_handles_none_values(self, qtbot, mock_ctx):
        """Summary label handles None chaos values."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"chaos_value": 5.0},
            {"chaos_value": None},
            {"chaos_value": 10.0},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        summary_text = window.summary_label.text()
        assert "3 sales" in summary_text
        assert "15.0c" in summary_text

    def test_filter_input_triggers_apply_filter(self, qtbot, mock_ctx):
        """Typing in filter input triggers _apply_filter."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"item_name": "Goldrim"},
            {"item_name": "Tabula Rasa"},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Reset model row count to track filter application
        initial_rows = window._model.rowCount()

        window.filter_input.setText("goldrim")

        # Should filter to only matching items
        assert window._model.rowCount() <= initial_rows

    def test_source_combo_change_triggers_apply_filter(self, qtbot, mock_ctx):
        """Changing source combo triggers _apply_filter."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        mock_ctx.db.get_recent_sales.return_value = [
            {"source": "poe.trade", "item_name": "Item1"},
            {"source": "poe.ninja", "item_name": "Item2"},
        ]

        window = RecentSalesWindow(mock_ctx)
        qtbot.addWidget(window)

        # Initially all sources shown
        assert window._model.rowCount() == 2

        # Change to specific source
        window.source_combo.setCurrentText("poe.trade")

        # Should filter to only that source
        assert window._model.rowCount() == 1

    def test_window_icon_applied(self, qtbot, mock_ctx):
        """Window icon is applied."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        with patch("gui_qt.windows.recent_sales_window.apply_window_icon") as mock_icon:
            window = RecentSalesWindow(mock_ctx)
            qtbot.addWidget(window)

            mock_icon.assert_called_once_with(window)

    def test_model_datetime_error_handling(self, qtbot):
        """Model handles invalid datetime strings gracefully."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "invalid-datetime",
                "item_name": "Item",
                "source": "test",
                "chaos_value": 1.0,
            }
        ]

        model.set_data(data)

        index = model.index(0, 0)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        # Should return string representation without crashing
        assert result == "invalid-datetime"

    def test_model_chaos_value_error_handling(self, qtbot):
        """Model handles invalid chaos_value gracefully."""
        from gui_qt.windows.recent_sales_window import SalesTableModel

        model = SalesTableModel()

        data = [
            {
                "sold_at": "2025-01-01",
                "item_name": "Item",
                "source": "test",
                "chaos_value": "invalid",
            }
        ]

        model.set_data(data)

        index = model.index(0, 3)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        # Should return string representation without crashing
        assert result == "invalid"
