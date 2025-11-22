# tests/integration/gui/test_gui_details_and_status.py

import tkinter as tk
from tkinter import ttk

import pytest

from gui.main_window import PriceCheckerGUI, RESULT_COLUMNS

pytestmark = pytest.mark.integration


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
        self.config = None  # no league/config in these tests


@pytest.fixture
def gui(tk_root: tk.Tk) -> PriceCheckerGUI:
    return PriceCheckerGUI(tk_root, _DummyContext())


@pytest.fixture
def gui_with_one_row(gui: PriceCheckerGUI) -> PriceCheckerGUI:
    """
    GUI with one logical result row inserted.

    NOTE: The GUI now also adds an aggregate row for each logical item,
    so we expect at least one row in the Treeview, but not exactly one.
    """
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
    # There should be at least one row (aggregate + per-source)
    assert len(children) >= 1
    # Select the first row for detail tests
    tree.selection_set(children[0])
    return gui


def test_view_selected_row_details_shows_message(gui_with_one_row: PriceCheckerGUI, monkeypatch) -> None:
    captured: dict[str, tuple[str, str]] = {}

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
    captured: dict[str, tuple[str, str]] = {}

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


def test_tree_double_click_opens_browser(gui_with_one_row: PriceCheckerGUI, monkeypatch) -> None:
    """
    Simulate a double-click event on the only logical row and assert that
    the GUI attempts to open a browser (trade page) for that row.

    Double-click no longer shows the details dialog by default; it now
    calls _open_selected_row_trade_url_or_details, which opens a browser
    and only falls back to the details dialog on error.
    """
    opened_urls: list[str] = []

    import gui.main_window as main_window_module

    def fake_open_new_tab(url: str) -> None:
        opened_urls.append(url)

    monkeypatch.setattr(main_window_module.webbrowser, "open_new_tab", fake_open_new_tab)

    tree = gui_with_one_row.results_tree
    children = tree.get_children()
    assert len(children) >= 1
    row_id = children[0]

    # Get row bbox to simulate a click inside its cell
    bbox = tree.bbox(row_id, column="#1")  # first visible column
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

    assert len(opened_urls) == 1
    assert "pathofexile.com" in opened_urls[0]


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
    # We now have aggregate rows + per-source rows:
    # 2 logical items → 2 aggregates + 2 per-source = 4 rows
    assert "4 row(s)" in status
