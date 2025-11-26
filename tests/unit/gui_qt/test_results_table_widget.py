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
        "item_name", "variant", "links", "chaos_value", "divine_value",
        "listing_count", "source", "upgrade", "price_explanation"
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
    assert model.columnCount() == 9


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
    assert len(widget.columns) == 9


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
