# tests/test_results_table.py

import tkinter as tk
from tkinter import ttk
from pathlib import Path

import pytest

from gui.main_window import ResultsTable, RESULT_COLUMNS


@pytest.fixture
def tk_root() -> tk.Tk:
    """Yield a hidden Tk root window and ensure it is destroyed after the test.

    If Tk cannot be initialized (e.g., in a headless or misconfigured environment),
    skip these GUI tests instead of failing the whole suite.
    """
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter is not available or cannot be initialized in this environment.")
    else:
        root.withdraw()
        try:
            yield root
        finally:
            root.destroy()


@pytest.fixture
def results_table(tk_root: tk.Tk) -> ResultsTable:
    frame = ttk.Frame(tk_root)
    frame.pack()
    return ResultsTable(frame, RESULT_COLUMNS)


def test_insert_rows_and_iter_rows(results_table: ResultsTable) -> None:
    rows = [
        {
            "item_name": "Item A",
            "variant": "v1",
            "links": "6",
            "chaos_value": "10",
            "divine_value": "0.1",
            "listing_count": "3",
            "source": "test",
        },
        {
            "item_name": "Item B",
            "variant": "v2",
            "links": "4",
            "chaos_value": "5",
            "divine_value": "0.05",
            "listing_count": "10",
            "source": "test",
        },
    ]

    results_table.insert_rows(rows)
    all_rows = list(results_table.iter_rows())

    assert len(all_rows) == 2
    # Ensure order and value mapping are preserved
    assert all_rows[0][0] == "Item A"
    assert all_rows[1][0] == "Item B"


def test_to_tsv_with_header(results_table: ResultsTable) -> None:
    rows = [
        {
            "item_name": "Alpha",
            "variant": "v1",
            "links": "6",
            "chaos_value": "1.5",
            "divine_value": "0.01",
            "listing_count": "2",
            "source": "unit-test",
        },
        {
            "item_name": "Beta",
            "variant": "v2",
            "links": "4",
            "chaos_value": "3.25",
            "divine_value": "0.02",
            "listing_count": "5",
            "source": "unit-test",
        },
    ]

    results_table.insert_rows(rows)

    tsv = results_table.to_tsv(include_header=True)
    lines = tsv.splitlines()

    assert len(lines) == 3  # header + 2 rows
    header = lines[0].split("\t")
    assert list(header) == list(RESULT_COLUMNS)

    row1 = lines[1].split("\t")
    assert row1[0] == "Alpha"
    row2 = lines[2].split("\t")
    assert row2[0] == "Beta"


def test_export_tsv_writes_file(tmp_path: Path, results_table: ResultsTable) -> None:
    rows = [
        {
            "item_name": "File Item",
            "variant": "vX",
            "links": "1",
            "chaos_value": "9",
            "divine_value": "0.09",
            "listing_count": "1",
            "source": "file-test",
        }
    ]
    results_table.insert_rows(rows)

    out_file = tmp_path / "results.tsv"
    results_table.export_tsv(out_file, include_header=True)

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "File Item" in content
    # Header should also be present
    assert "item_name" in content.splitlines()[0]


def test_sort_by_column_numeric(results_table: ResultsTable) -> None:
    rows = [
        {
            "item_name": "C",
            "variant": "v",
            "links": "6",
            "chaos_value": "10",
            "divine_value": "0.1",
            "listing_count": "3",
            "source": "test",
        },
        {
            "item_name": "A",
            "variant": "v",
            "links": "6",
            "chaos_value": "2",
            "divine_value": "0.02",
            "listing_count": "3",
            "source": "test",
        },
        {
            "item_name": "B",
            "variant": "v",
            "links": "6",
            "chaos_value": "5",
            "divine_value": "0.05",
            "listing_count": "3",
            "source": "test",
        },
    ]
    results_table.insert_rows(rows)

    # Sort ascending by chaos_value (numeric)
    results_table.sort_by_column("chaos_value", reverse=False)

    ordered = list(results_table.iter_rows())
    # Should be A (2), B (5), C (10)
    assert [r[0] for r in ordered] == ["A", "B", "C"]

    # Sort descending
    results_table.sort_by_column("chaos_value", reverse=True)
    ordered_desc = list(results_table.iter_rows())
    assert [r[0] for r in ordered_desc] == ["C", "B", "A"]


def test_autosize_columns_does_not_exceed_bounds(results_table: ResultsTable) -> None:
    # Insert a long-ish value to force wider columns
    rows = [
        {
            "item_name": "Very Long Item Name For Autosize Check",
            "variant": "v",
            "links": "6",
            "chaos_value": "1",
            "divine_value": "0.01",
            "listing_count": "3",
            "source": "test",
        }
    ]
    results_table.insert_rows(rows)

    # Just ensure this doesn't raise and widths are within configured bounds
    results_table.autosize_columns(min_width=80, max_width=320)

    for col in RESULT_COLUMNS:
        width = int(results_table.tree.column(col, "width"))
        assert 80 <= width <= 320
