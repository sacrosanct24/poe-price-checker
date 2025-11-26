from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import pytest

from gui.main_window import ResultsTable, RESULT_COLUMNS


@pytest.fixture
def tk_root():
    """
    Yield a hidden Tk root window and ensure it is destroyed after the test.

    If Tk cannot be initialized (e.g., truly headless environment),
    the test will be skipped automatically.
    """
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter not available in this environment")
        return

    yield root
    root.destroy()


def test_results_table_initialization(tk_root):
    frame = ttk.Frame(tk_root)
    table = ResultsTable(frame, RESULT_COLUMNS)
    tree = table.tree

    # Verify all expected columns exist
    assert set(tree["columns"]) == set(RESULT_COLUMNS)

    for col in RESULT_COLUMNS:
        assert tree.heading(col)["text"] == col.replace("_", " ").title()


def test_insert_rows_populates_tree_correctly(tk_root):
    frame = ttk.Frame(tk_root)
    table = ResultsTable(frame, RESULT_COLUMNS)

    rows = [
        {
            "item_name": "Goldrim",
            "variant": "",
            "links": "0",
            "chaos_value": "5.0",
            "divine_value": "0.02",
            "listing_count": "10",
            "source": "test",
            "upgrade": "",
            "price_explanation": "{}",
        },
        {
            "item_name": "Tabula Rasa",
            "variant": "",
            "links": "6",
            "chaos_value": "1",
            "divine_value": "0.01",
            "listing_count": "3",
            "source": "test",
            "upgrade": "",
            "price_explanation": "{}",
        },
    ]

    table.insert_rows(rows)

    # Tree item count must match rows inserted
    assert len(table.tree.get_children()) == 2

    # Validate the first row content
    first_id = table.tree.get_children()[0]
    values = table.tree.item(first_id, "values")

    # Values appear in RESULT_COLUMNS order
    expected = [rows[0].get(col, "") for col in RESULT_COLUMNS]
    assert list(values) == expected


def test_autosize_columns_operates_within_bounds(tk_root):
    frame = ttk.Frame(tk_root)
    table = ResultsTable(frame, RESULT_COLUMNS)

    rows = [
        {
            "item_name": "Goldrim",
            "variant": "",
            "links": "0",
            "chaos_value": "5.0",
            "divine_value": "0.02",
            "listing_count": "10",
            "source": "test",
            "upgrade": "",
            "price_explanation": "{}",
        },
        {
            "item_name": "Tabula Rasa",
            "variant": "",
            "links": "6",
            "chaos_value": "1",
            "divine_value": "0.01",
            "listing_count": "3",
            "source": "test",
            "upgrade": "",
            "price_explanation": "{}",
        },
    ]

    table.insert_rows(rows)

    # ensure no errors and width stays in bounds
    table.autosize_columns(min_width=80, max_width=320)

    # Check visible columns (price_explanation is hidden by default with width 0)
    hidden_columns = {"price_explanation"}
    for col in RESULT_COLUMNS:
        width = int(table.tree.column(col, "width"))
        if col in hidden_columns:
            # Hidden columns should have width 0
            assert width == 0, f"Hidden column '{col}' should have width 0, got {width}"
        else:
            assert 80 <= width <= 320, f"Column '{col}' width {width} not in range [80, 320]"
