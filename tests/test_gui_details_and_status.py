# tests/test_gui_details_and_status.py

import tkinter as tk
from tkinter import ttk

import pytest

from gui.main_window import PriceCheckerGUI, RESULT_COLUMNS


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


class _DummyContext:
    """Minimal stand-in for app_context used by PriceCheckerGUI in tests."""
    def __init__(self) -> None:
        self.logger = None  # GUI resolves its own fallback logger


@pytest.fixture
def gui(tk_root: tk.Tk) -> PriceCheckerGUI:
    return PriceCheckerGUI(tk_root, _DummyContext())


@pytest.fixture
def gui_with_one_row(gui: PriceCheckerGUI) -> PriceCheckerGUI:
    """GUI with one pre-inserted result row and that row selected."""
    rows = [
        {
            "item_name": "DetailItem",
            "variant": "vD",
            "links": "6",
            "chaos_value": "42",
            "divine_value": "0.42",
            "listing_count": "7",
            "source": "detail-test",
        }
    ]
    gui._insert_result_rows(rows)

    tree = gui.results_tree
    children = tree.get_children()
    assert len(children) == 1
    tree.selection_set(children[0])
    return gui


def test_view_selected_row_details_shows_message(gui_with_one_row: PriceCheckerGUI, monkeypatch) -> None:
    captured: dict[str, str | tuple[str, str]] = {}

    # Monkeypatch messagebox.showinfo to capture title and message
    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        captured["info"] = (title, message)

    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    gui_with_one_row._view_selected_row_details()

    assert "info" in captured
    title, message = captured["info"]  # type: ignore[assignment]
    assert "Item Details" in title
    # Should contain a line for at least the item name and chaos value
    assert "DetailItem" in message
    assert "Chaos Value" in message


def test_view_selected_row_details_no_selection(gui: PriceCheckerGUI, monkeypatch) -> None:
    captured: dict[str, str | tuple[str, str]] = {}

    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        captured["info"] = (title, message)

    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    # Ensure nothing is selected
    gui.results_tree.selection_remove(*gui.results_tree.get_children())

    gui._view_selected_row_details()

    # Should show an informational dialog about no selection
    assert "info" in captured
    title, message = captured["info"]  # type: ignore[assignment]
    assert "Item Details" in title
    assert "No row is currently selected" in message
    # Status should also be updated
    assert gui.status_var.get().startswith("No row selected")


def test_tree_double_click_triggers_view_details(gui_with_one_row: PriceCheckerGUI, monkeypatch) -> None:
    """
    Simulate a double-click event on the only row and assert that
    _view_selected_row_details is called (via its messagebox).
    """
    captured: dict[str, tuple[str, str]] = {}

    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        captured["info"] = (title, message)

    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    tree = gui_with_one_row.results_tree
    # Get row bbox to simulate a click inside its cell
    children = tree.get_children()
    assert len(children) == 1
    row_id = children[0]
    bbox = tree.bbox(row_id, column="#1")  # first visible column
    # If bbox is empty (e.g. not visible yet), just skip this test
    if not bbox:
        pytest.skip("Treeview row bbox not available in this environment.")

    x = bbox[0] + 5
    y = bbox[1] + 5

    event = tk.Event()
    event.x = x
    event.y = y
    event.x_root = x
    event.y_root = y

    gui_with_one_row._on_tree_double_click(event)

    assert "info" in captured
    title, message = captured["info"]
    assert "Item Details" in title
    assert "DetailItem" in message


def test_insert_result_rows_sets_status_with_row_count(gui: PriceCheckerGUI) -> None:
    rows = [
        {
            "item_name": "Row1",
            "variant": "v1",
            "links": "6",
            "chaos_value": "1",
            "divine_value": "0.01",
            "listing_count": "3",
            "source": "status-test",
        },
        {
            "item_name": "Row2",
            "variant": "v2",
            "links": "4",
            "chaos_value": "2",
            "divine_value": "0.02",
            "listing_count": "5",
            "source": "status-test",
        },
    ]

    gui._insert_result_rows(rows)

    status = gui.status_var.get()
    assert "Price check complete" in status
    assert "2 row(s)" in status
