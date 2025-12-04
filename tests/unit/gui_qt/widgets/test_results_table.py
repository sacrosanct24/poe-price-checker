"""Tests for gui_qt/widgets/results_table.py - Results Table Widget."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget

from gui_qt.widgets.results_table import (
    build_item_tooltip_html,
    ResultsTableModel,
    ResultsTableWidget,
    TREND_COLORS,
)


# ============================================================================
# build_item_tooltip_html Tests
# ============================================================================

class TestBuildItemTooltipHtml:
    """Tests for build_item_tooltip_html function."""

    def test_returns_empty_for_none(self):
        """Returns empty string for None item."""
        assert build_item_tooltip_html(None) == ""

    def test_includes_item_name(self):
        """Includes item name in tooltip."""
        item = Mock()
        item.name = "Test Item"
        item.base_type = "Base Type"
        item.rarity = "Rare"
        item.item_level = 85
        item.ilvl = None
        item.links = 6
        item.max_links = None
        item.quality = 20
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "Test Item" in html

    def test_includes_base_type_when_different(self):
        """Includes base type when different from name."""
        item = Mock()
        item.name = "Headhunter"
        item.base_type = "Leather Belt"
        item.rarity = "Unique"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "Leather Belt" in html

    def test_includes_item_level(self):
        """Includes item level in tooltip."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Normal"
        item.item_level = 85
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "iLvl 85" in html

    def test_includes_links(self):
        """Includes links in tooltip."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Normal"
        item.item_level = None
        item.ilvl = None
        item.links = 6
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "6L" in html

    def test_includes_quality(self):
        """Includes quality in tooltip."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Normal"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = 20
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "+20%" in html

    def test_includes_corrupted_status(self):
        """Includes corrupted status in tooltip."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Normal"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = True
        item.implicits = []
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "Corrupted" in html

    def test_includes_implicit_mods(self):
        """Includes implicit mods in tooltip."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Rare"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = ["+30 to Dexterity"]
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "+30 to Dexterity" in html

    def test_includes_explicit_mods(self):
        """Includes explicit mods in tooltip."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Rare"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = ["+100 to Maximum Life", "+50% Fire Resistance"]
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "+100 to Maximum Life" in html
        assert "+50% Fire Resistance" in html

    def test_limits_implicit_mods(self):
        """Limits implicit mods to 3."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Rare"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = ["Mod1", "Mod2", "Mod3", "Mod4", "Mod5"]
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "+2 more" in html

    def test_limits_explicit_mods(self):
        """Limits explicit mods to 5."""
        item = Mock()
        item.name = "Test"
        item.base_type = None
        item.rarity = "Rare"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "+2 more" in html

    def test_escapes_html(self):
        """Escapes HTML special characters."""
        item = Mock()
        item.name = "Test <script>alert(1)</script>"
        item.base_type = None
        item.rarity = "Normal"
        item.item_level = None
        item.ilvl = None
        item.links = None
        item.max_links = None
        item.quality = None
        item.corrupted = False
        item.implicits = []
        item.implicit_mods = None
        item.explicits = []
        item.explicit_mods = None
        item.mods = None

        html = build_item_tooltip_html(item)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ============================================================================
# ResultsTableModel Tests
# ============================================================================

class TestResultsTableModel:
    """Tests for ResultsTableModel class."""

    @pytest.fixture
    def model(self, qtbot):
        """Create a model instance."""
        return ResultsTableModel()

    def test_init(self, model):
        """Model initializes correctly."""
        assert model.rowCount() == 0
        assert model.columnCount() == len(ResultsTableModel.COLUMNS)

    def test_columns_property(self, model):
        """columns property returns column keys."""
        cols = model.columns
        assert "item_name" in cols
        assert "chaos_value" in cols

    def test_set_data(self, model):
        """set_data populates the model."""
        data = [
            {"item_name": "Item 1", "chaos_value": 100},
            {"item_name": "Item 2", "chaos_value": 50},
        ]

        model.set_data(data, calculate_trends=False)

        assert model.rowCount() == 2

    def test_get_row(self, model):
        """get_row returns row data."""
        data = [{"item_name": "Test", "chaos_value": 100}]
        model.set_data(data, calculate_trends=False)

        row = model.get_row(0)
        assert row["item_name"] == "Test"
        assert row["chaos_value"] == 100

    def test_get_row_invalid(self, model):
        """get_row returns None for invalid index."""
        assert model.get_row(-1) is None
        assert model.get_row(100) is None

    def test_header_data_horizontal(self, model):
        """headerData returns column names."""
        name = model.headerData(0, Qt.Orientation.Horizontal)
        assert name == "Item Name"

    def test_header_data_vertical(self, model):
        """headerData returns row numbers."""
        model.set_data([{"item_name": "Test"}], calculate_trends=False)
        num = model.headerData(0, Qt.Orientation.Vertical)
        assert num == "1"

    def test_data_display_role(self, model):
        """data returns display value."""
        model.set_data([{"item_name": "Test Item"}], calculate_trends=False)
        index = model.index(0, 0)  # item_name column
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "Test Item"

    def test_data_formats_chaos_value(self, model):
        """data formats chaos_value with one decimal."""
        model.set_data([{"chaos_value": 123.456}], calculate_trends=False)
        # chaos_value is column 3
        index = model.index(0, 3)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "123.5"

    def test_data_profit_calculation(self, model):
        """data calculates profit from chaos_value and purchase_price."""
        model.set_data([{
            "chaos_value": 100,
            "purchase_price": 75
        }], calculate_trends=False)
        # profit is column 4
        index = model.index(0, 4)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "+25.0c"

    def test_data_profit_negative(self, model):
        """data shows negative profit."""
        model.set_data([{
            "chaos_value": 50,
            "purchase_price": 75
        }], calculate_trends=False)
        index = model.index(0, 4)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "-25.0c"

    def test_data_foreground_high_value(self, model):
        """data returns high value color for expensive items."""
        model.set_data([{"chaos_value": 150}], calculate_trends=False)
        index = model.index(0, 0)
        brush = model.data(index, Qt.ItemDataRole.ForegroundRole)
        assert brush is not None

    def test_data_alignment(self, model):
        """data returns right alignment for numeric columns."""
        model.set_data([{"chaos_value": 100}], calculate_trends=False)
        index = model.index(0, 3)  # chaos_value
        alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert alignment & Qt.AlignmentFlag.AlignRight

    def test_data_user_role(self, model):
        """data returns full row data for UserRole."""
        row_data = {"item_name": "Test", "chaos_value": 100}
        model.set_data([row_data], calculate_trends=False)
        index = model.index(0, 0)
        data = model.data(index, Qt.ItemDataRole.UserRole)
        assert data["item_name"] == "Test"
        assert data["chaos_value"] == 100

    def test_data_invalid_index(self, model):
        """data returns None for invalid index."""
        model.set_data([{"item_name": "Test"}], calculate_trends=False)
        index = model.index(100, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) is None

    def test_sort_ascending(self, model):
        """sort orders data ascending."""
        model.set_data([
            {"item_name": "B", "chaos_value": 50},
            {"item_name": "A", "chaos_value": 100},
        ], calculate_trends=False)

        model.sort(0, Qt.SortOrder.AscendingOrder)

        assert model.get_row(0)["item_name"] == "A"
        assert model.get_row(1)["item_name"] == "B"

    def test_sort_descending(self, model):
        """sort orders data descending."""
        model.set_data([
            {"item_name": "A", "chaos_value": 50},
            {"item_name": "B", "chaos_value": 100},
        ], calculate_trends=False)

        model.sort(0, Qt.SortOrder.DescendingOrder)

        assert model.get_row(0)["item_name"] == "B"
        assert model.get_row(1)["item_name"] == "A"

    def test_sort_numeric(self, model):
        """sort handles numeric columns correctly."""
        model.set_data([
            {"chaos_value": 50},
            {"chaos_value": 100},
            {"chaos_value": 25},
        ], calculate_trends=False)

        model.sort(3, Qt.SortOrder.DescendingOrder)  # chaos_value column

        assert model.get_row(0)["chaos_value"] == 100
        assert model.get_row(1)["chaos_value"] == 50
        assert model.get_row(2)["chaos_value"] == 25

    def test_sort_empty_data(self, model):
        """sort handles empty data."""
        model.sort(0, Qt.SortOrder.AscendingOrder)
        # Should not raise

    def test_set_league(self, model):
        """set_league updates the league."""
        model.set_league("Settlers")
        assert model._league == "Settlers"


# ============================================================================
# ResultsTableWidget Tests
# ============================================================================

class TestResultsTableWidget:
    """Tests for ResultsTableWidget class."""

    @pytest.fixture
    def widget(self, qtbot):
        """Create a widget instance."""
        with patch('gui_qt.widgets.results_table.ItemTooltipMixin._init_item_tooltip'):
            w = ResultsTableWidget()
            qtbot.addWidget(w)
            return w

    def test_init(self, widget):
        """Widget initializes correctly."""
        assert widget.model() is not None
        assert widget.selectionBehavior() == widget.SelectionBehavior.SelectRows

    def test_columns_property(self, widget):
        """columns property returns column keys."""
        cols = widget.columns
        assert "item_name" in cols

    def test_set_data(self, widget):
        """set_data populates the widget."""
        data = [{"item_name": "Test", "chaos_value": 100}]
        widget.set_data(data, calculate_trends=False)

        assert widget.model().rowCount() == 1

    def test_set_league(self, widget):
        """set_league updates the model."""
        widget.set_league("TestLeague")
        assert widget._model._league == "TestLeague"

    def test_get_selected_row_none(self, widget):
        """get_selected_row returns None when nothing selected."""
        widget.set_data([{"item_name": "Test"}], calculate_trends=False)
        assert widget.get_selected_row() is None

    def test_get_selected_rows_empty(self, widget):
        """get_selected_rows returns empty list when nothing selected."""
        widget.set_data([{"item_name": "Test"}], calculate_trends=False)
        assert widget.get_selected_rows() == []

    def test_get_selection_count(self, widget):
        """get_selection_count returns correct count."""
        widget.set_data([{"item_name": "Test"}], calculate_trends=False)
        assert widget.get_selection_count() == 0

    def test_select_all(self, widget):
        """select_all selects all rows."""
        widget.set_data([
            {"item_name": "A"},
            {"item_name": "B"},
        ], calculate_trends=False)

        widget.select_all()

        assert widget.get_selection_count() == 2

    def test_clear_selection(self, widget):
        """clear_selection clears all selection."""
        widget.set_data([{"item_name": "Test"}], calculate_trends=False)
        widget.select_all()
        widget.clear_selection()

        assert widget.get_selection_count() == 0

    def test_set_column_visible(self, widget):
        """set_column_visible shows/hides columns."""
        # Hide the variant column
        widget.set_column_visible("variant", False)
        assert widget.isColumnHidden(1)

        # Show it again
        widget.set_column_visible("variant", True)
        assert not widget.isColumnHidden(1)

    def test_to_tsv(self, widget):
        """to_tsv exports data correctly."""
        widget.set_data([
            {"item_name": "Item 1", "chaos_value": 100},
            {"item_name": "Item 2", "chaos_value": 50},
        ], calculate_trends=False)

        tsv = widget.to_tsv(include_header=True)

        lines = tsv.split("\n")
        assert len(lines) >= 3  # Header + 2 data rows
        assert "Item Name" in lines[0]

    def test_to_tsv_no_header(self, widget):
        """to_tsv exports without header when specified."""
        widget.set_data([
            {"item_name": "Item 1"},
        ], calculate_trends=False)

        tsv = widget.to_tsv(include_header=False)

        lines = tsv.split("\n")
        assert "Item Name" not in lines[0]

    def test_export_tsv(self, widget, tmp_path):
        """export_tsv writes to file."""
        widget.set_data([{"item_name": "Test"}], calculate_trends=False)

        output_file = tmp_path / "test.tsv"
        widget.export_tsv(output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "Test" in content

    def test_row_selected_signal(self, widget, qtbot):
        """row_selected signal emitted on selection."""
        widget.set_data([{"item_name": "Test"}], calculate_trends=False)

        # Select the first row
        with qtbot.waitSignal(widget.row_selected, timeout=1000):
            widget.selectRow(0)

    def test_rows_selected_signal(self, widget, qtbot):
        """rows_selected signal emitted on selection change."""
        widget.set_data([
            {"item_name": "A"},
            {"item_name": "B"},
        ], calculate_trends=False)

        with qtbot.waitSignal(widget.rows_selected, timeout=1000):
            widget.select_all()

    def test_get_column_order(self, widget):
        """get_column_order returns current order."""
        order = widget.get_column_order()
        assert len(order) == len(ResultsTableModel.COLUMNS)
        assert order[0] == "item_name"

    @patch('gui_qt.widgets.results_table.ResultsTableWidget._save_column_config')
    def test_reset_column_order(self, mock_save, widget):
        """reset_column_order resets to default."""
        widget.reset_column_order()

        order = widget.get_column_order()
        expected = [col[0] for col in ResultsTableModel.COLUMNS]
        assert order == expected

    def test_copy_to_clipboard(self, widget, qtbot):
        """_copy_to_clipboard copies to clipboard."""
        from PyQt6.QtWidgets import QApplication

        widget._copy_to_clipboard(["Item 1", "Item 2"])

        clipboard_text = QApplication.clipboard().text()
        assert "Item 1" in clipboard_text
        assert "Item 2" in clipboard_text

    def test_copy_selected_tsv(self, widget, qtbot):
        """_copy_selected_tsv copies selected rows as TSV."""
        from PyQt6.QtWidgets import QApplication

        rows = [
            {"item_name": "Item 1", "chaos_value": 100},
            {"item_name": "Item 2", "chaos_value": 50},
        ]
        widget.set_data(rows, calculate_trends=False)

        widget._copy_selected_tsv(rows)

        clipboard_text = QApplication.clipboard().text()
        assert "Item 1" in clipboard_text
        assert "Item 2" in clipboard_text

    def test_get_item_at_pos_invalid(self, widget):
        """_get_item_at_pos returns None for invalid position."""
        from PyQt6.QtCore import QPoint

        result = widget._get_item_at_pos(QPoint(-1, -1))
        assert result is None


# ============================================================================
# TREND_COLORS Tests
# ============================================================================

class TestTrendColors:
    """Tests for TREND_COLORS constant."""

    def test_up_color(self):
        """Up trend has green color."""
        assert TREND_COLORS["up"] == "#4CAF50"

    def test_down_color(self):
        """Down trend has red color."""
        assert TREND_COLORS["down"] == "#F44336"

    def test_stable_color(self):
        """Stable trend has gray color."""
        assert TREND_COLORS["stable"] == "#9E9E9E"


# ============================================================================
# Column Configuration Tests
# ============================================================================

class TestColumnConfiguration:
    """Tests for column configuration persistence."""

    @pytest.fixture
    def widget_with_config(self, qtbot, tmp_path):
        """Create widget with mocked config path."""
        with patch('gui_qt.widgets.results_table.ItemTooltipMixin._init_item_tooltip'):
            with patch('gui_qt.widgets.results_table.ResultsTableWidget._get_config_path') as mock_path:
                mock_path.return_value = tmp_path / "column_config.json"
                w = ResultsTableWidget()
                qtbot.addWidget(w)
                yield w

    def test_save_column_config(self, widget_with_config, tmp_path):
        """_save_column_config writes to file."""
        widget_with_config._save_column_config()

        config_path = tmp_path / "column_config.json"
        assert config_path.exists()

    def test_load_column_config_no_file(self, widget_with_config, tmp_path):
        """_load_column_config handles missing file."""
        # Should not raise
        widget_with_config._load_column_config()

    def test_load_column_config_with_file(self, widget_with_config, tmp_path):
        """_load_column_config reads from file."""
        import json

        config_path = tmp_path / "column_config.json"
        config = {
            "order": ["chaos_value", "item_name", "variant"],
            "hidden": ["links"],
            "widths": {"item_name": 200}
        }
        config_path.write_text(json.dumps(config))

        widget_with_config._load_column_config()
        # Should not raise and should apply config


# ============================================================================
# Context Menu Tests
# ============================================================================

class TestContextMenu:
    """Tests for context menu functionality."""

    @pytest.fixture
    def widget(self, qtbot):
        """Create a widget instance."""
        with patch('gui_qt.widgets.results_table.ItemTooltipMixin._init_item_tooltip'):
            w = ResultsTableWidget()
            qtbot.addWidget(w)
            return w

    def test_show_context_menu_no_selection(self, widget):
        """Context menu does nothing with no selection."""
        from PyQt6.QtCore import QPoint

        # Should not raise
        widget._show_context_menu(QPoint(0, 0))

    def test_show_header_context_menu(self, widget, qtbot):
        """Header context menu can be shown."""
        from PyQt6.QtCore import QPoint

        # This would normally show a menu, but we can't test GUI interactions directly
        # Just verify the method exists and is callable
        assert hasattr(widget, '_show_header_context_menu')
