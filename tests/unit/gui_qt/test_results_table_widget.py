"""
Tests for PyQt6 ResultsTableWidget.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def qapp():
    """Create a QApplication instance for testing."""
    from PyQt6.QtWidgets import QApplication

    # Check if an instance already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_results_table_model_columns(qapp):
    """Test that the table model has expected columns."""
    from gui_qt.widgets.results_table import ResultsTableModel

    model = ResultsTableModel()
    expected_columns = [
        "item_name", "variant", "links", "chaos_value", "profit", "divine_value",
        "trend_7d", "listing_count", "source", "upgrade", "price_explanation"
    ]

    assert model.columns == expected_columns


def test_results_table_model_set_data(qapp):
    """Test setting data on the model."""
    from gui_qt.widgets.results_table import ResultsTableModel

    model = ResultsTableModel()

    data = [
        {"item_name": "Goldrim", "chaos_value": 5.0, "source": "test"},
        {"item_name": "Tabula Rasa", "chaos_value": 10.0, "source": "test"},
    ]

    model.set_data(data)

    assert model.rowCount() == 2
    assert model.columnCount() == 11  # Includes profit column


def test_results_table_model_get_row(qapp):
    """Test getting a specific row."""
    from gui_qt.widgets.results_table import ResultsTableModel

    model = ResultsTableModel()

    data = [
        {"item_name": "Goldrim", "chaos_value": 5.0},
        {"item_name": "Tabula Rasa", "chaos_value": 10.0},
    ]

    model.set_data(data)

    row = model.get_row(0)
    assert row is not None
    assert row["item_name"] == "Goldrim"

    row = model.get_row(1)
    assert row["item_name"] == "Tabula Rasa"

    # Out of bounds
    assert model.get_row(99) is None


def test_results_table_widget_creation(qapp):
    """Test creating the results table widget."""
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    assert widget is not None
    assert len(widget.columns) == 11  # Includes profit column


def test_results_table_widget_set_data(qapp):
    """Test setting data on the widget."""
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    data = [
        {"item_name": "Test Item", "chaos_value": 100, "source": "test"},
    ]

    widget.set_data(data)

    # Verify data was set (model row count)
    assert widget._model.rowCount() == 1


def test_results_table_to_tsv(qapp):
    """Test exporting table data to TSV."""
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    data = [
        {"item_name": "Goldrim", "chaos_value": 5.0, "source": "test"},
    ]

    widget.set_data(data)

    tsv = widget.to_tsv(include_header=True)

    assert "Item Name" in tsv  # Header
    assert "Goldrim" in tsv  # Data
    assert "\t" in tsv  # Tab-separated


# ============================================================================
# Bulk Selection Tests
# ============================================================================


def test_results_table_extended_selection_mode(qapp):
    """Test that table supports extended (multi) selection."""
    from PyQt6.QtWidgets import QAbstractItemView
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    assert widget.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection


def test_results_table_get_selected_rows_empty(qapp):
    """Test get_selected_rows returns empty list when nothing selected."""
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    data = [
        {"item_name": "Goldrim", "chaos_value": 5.0},
        {"item_name": "Tabula Rasa", "chaos_value": 10.0},
    ]

    widget.set_data(data)

    # No selection
    assert widget.get_selected_rows() == []
    assert widget.get_selection_count() == 0


def test_results_table_get_selection_count(qapp):
    """Test get_selection_count returns correct count."""
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    data = [
        {"item_name": "Goldrim", "chaos_value": 5.0},
        {"item_name": "Tabula Rasa", "chaos_value": 10.0},
        {"item_name": "Wanderlust", "chaos_value": 1.0},
    ]

    widget.set_data(data)

    # Select all
    widget.select_all()

    assert widget.get_selection_count() == 3


def test_results_table_select_all_and_clear(qapp):
    """Test select_all and clear_selection methods."""
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    data = [
        {"item_name": "Goldrim", "chaos_value": 5.0},
        {"item_name": "Tabula Rasa", "chaos_value": 10.0},
    ]

    widget.set_data(data)

    # Select all
    widget.select_all()
    assert widget.get_selection_count() == 2

    # Clear selection
    widget.clear_selection()
    assert widget.get_selection_count() == 0


def test_results_table_bulk_signals_exist(qapp):
    """Test that bulk selection signals are defined."""
    from gui_qt.widgets.results_table import ResultsTableWidget

    widget = ResultsTableWidget()

    # Check signals exist
    assert hasattr(widget, "rows_selected")
    assert hasattr(widget, "compare_requested")
    assert hasattr(widget, "pin_requested")
    assert hasattr(widget, "export_selected_requested")


def test_results_table_profit_column_display(qapp):
    """Test profit column displays correctly."""
    from PyQt6.QtCore import Qt
    from gui_qt.widgets.results_table import ResultsTableModel

    model = ResultsTableModel()

    data = [
        {"item_name": "Item1", "chaos_value": 100.0, "purchase_price": 50.0},
        {"item_name": "Item2", "chaos_value": 30.0, "purchase_price": 50.0},
        {"item_name": "Item3", "chaos_value": 50.0, "purchase_price": 50.0},
    ]

    model.set_data(data, calculate_trends=False)

    # Find profit column index
    profit_col = model.columns.index("profit")

    # Positive profit
    idx0 = model.index(0, profit_col)
    assert "+50.0c" in model.data(idx0, Qt.ItemDataRole.DisplayRole)

    # Negative profit
    idx1 = model.index(1, profit_col)
    assert "-20.0c" in model.data(idx1, Qt.ItemDataRole.DisplayRole)

    # No profit (zero)
    idx2 = model.index(2, profit_col)
    assert "+0.0c" in model.data(idx2, Qt.ItemDataRole.DisplayRole)


def test_results_table_profit_column_no_purchase_price(qapp):
    """Test profit column empty when no purchase price."""
    from PyQt6.QtCore import Qt
    from gui_qt.widgets.results_table import ResultsTableModel

    model = ResultsTableModel()

    data = [
        {"item_name": "Item1", "chaos_value": 100.0},  # No purchase_price
    ]

    model.set_data(data, calculate_trends=False)

    profit_col = model.columns.index("profit")
    idx = model.index(0, profit_col)

    assert model.data(idx, Qt.ItemDataRole.DisplayRole) == ""
