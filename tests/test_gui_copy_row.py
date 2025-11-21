# tests/test_gui_copy_row.py

import tkinter as tk
from tkinter import ttk
from typing import Iterator
import pytest

from gui.main_window import PriceCheckerGUI


@pytest.fixture
def tk_root() -> Iterator[tk.Tk]:
    """Yield a hidden Tk root window and ensure it is destroyed after the test.

    If Tk cannot be initialized (e.g., in a headless or misconfigured environment),
    skip these GUI tests instead of failing the whole suite.
    """
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter is not available or cannot be initialized in this environment.")
    else:
        # Hide the main window to avoid it flashing during tests
        root.withdraw()
        try:
            yield root
        finally:
            root.destroy()


def _make_fake_gui(root: tk.Tk) -> PriceCheckerGUI:
    """
    Create a PriceCheckerGUI-like object without running its __init__,
    and attach a Treeview + status_var for testing copy helpers.
    """
    gui = PriceCheckerGUI.__new__(PriceCheckerGUI)  # type: ignore[misc]
    gui.root = root
    gui.status_var = tk.StringVar(value="")

    # Define columns exactly as in the updated GUI:
    # ("Item", "Rarity", "Item Level", "Stack", "Chaos Value",
    #  "Divine Value", "Total Value", "Value Flag")
    columns = (
        "Item",
        "Rarity",
        "Item Level",
        "Stack",
        "Chaos Value",
        "Divine Value",
        "Total Value",
        "Value Flag",
    )

    tree = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")
    gui.tree = tree

    # Stub out _copy_to_clipboard to capture the last copied text
    def fake_copy(text: str) -> None:
        gui._last_clipboard_text = text  # type: ignore[attr-defined]

    gui._copy_to_clipboard = fake_copy  # type: ignore[method-assign]

    return gui


def test_get_selected_row_returns_all_columns(tk_root):
    gui = _make_fake_gui(tk_root)

    # Insert a row with 8 values (one per column)
    values = (
        "Fate Hood (Hubris Circlet)",
        "RARE",
        "84",
        "1",
        "0.0",
        "0.0",
        "0.0",
        "fracture_base",
    )
    iid = gui.tree.insert("", "end", values=values)
    gui.tree.selection_set(iid)

    # This assumes you've updated _get_selected_row to return all values,
    # not just the first 6.
    row = gui._get_selected_row()

    assert row is not None
    assert len(row) == len(values)
    assert row == values


def test_copy_row_tsv_includes_all_columns(tk_root):
    gui = _make_fake_gui(tk_root)

    values = (
        "Blight Shelter (Astral Plate)",
        "RARE",
        "84",
        "1",
        "",
        "",
        "",
        "craft_base",
    )
    iid = gui.tree.insert("", "end", values=values)
    gui.tree.selection_set(iid)

    # Call the copy helper
    gui._copy_row_tsv()

    # Ensure _copy_to_clipboard was called with a TSV string
    assert hasattr(gui, "_last_clipboard_text")
    copied = gui._last_clipboard_text  # type: ignore[attr-defined]

    # Should be tab-joined, all columns present
    parts = copied.split("\t")
    assert parts == list(values)
