# tests/integration/gui/test_gui_export_and_copy_all_tsv.py

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest

from gui.main_window import PriceCheckerGUI, RESULT_COLUMNS

pytestmark = pytest.mark.integration


# ----------------------------------------
# Fixtures / dummy context
# ----------------------------------------


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


class _DummyConfig:
    def __init__(self) -> None:
        self.league = "Standard"
        self.window_size = (1200, 800)
        self.min_value_chaos = 0.0
        self.show_vendor_items = True
        self.auto_detect_league = False


class _DummyContext:
    def __init__(self) -> None:
        self.logger = None
        self.config = _DummyConfig()
        # price_service, parser, db etc are not needed for these GUI-only tests


@pytest.fixture
def gui(tk_root: tk.Tk) -> PriceCheckerGUI:
    return PriceCheckerGUI(tk_root, _DummyContext())


@pytest.fixture
def gui_with_results(gui: PriceCheckerGUI) -> PriceCheckerGUI:
    rows = [
        {
            "item_name": "Row1",
            "variant": "v1",
            "links": "6",
            "chaos_value": "1",
            "divine_value": "0.01",
            "listing_count": "3",
            "source": "export-test",
        },
        {
            "item_name": "Row2",
            "variant": "v2",
            "links": "4",
            "chaos_value": "2",
            "divine_value": "0.02",
            "listing_count": "5",
            "source": "export-test",
        },
    ]
    gui._insert_result_rows(rows)
    return gui


# ----------------------------------------
# Tests: Copy All Rows as TSV
# ----------------------------------------


def test_copy_all_rows_as_tsv_uses_clipboard(gui_with_results: PriceCheckerGUI, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_set_clipboard(text: str) -> None:
        captured["value"] = text

    monkeypatch.setattr(gui_with_results, "_set_clipboard", fake_set_clipboard)

    # Avoid real message boxes during test
    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        captured["info"] = (title, message)

    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    gui_with_results._copy_all_rows_as_tsv()

    assert "value" in captured
    tsv = captured["value"]
    assert isinstance(tsv, str)

    lines = tsv.splitlines()
    # First line is header with RESULT_COLUMNS
    header = lines[0].split("\t")
    assert header == list(RESULT_COLUMNS)

    # There should be at least header + 2 data lines
    assert len(lines) >= 3
    body = "\n".join(lines[1:])
    assert "Row1" in body
    assert "Row2" in body

    # Info dialog should have been shown
    assert "info" in captured
    title, msg = captured["info"]  # type: ignore[misc]
    assert "Copy All Rows as TSV" in title
    assert "copied to the clipboard" in msg


def test_copy_all_rows_as_tsv_no_rows_shows_message(gui: PriceCheckerGUI, monkeypatch) -> None:
    captured: dict[str, object] = {}

    # Avoid real message boxes
    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        captured["info"] = (title, message)

    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    gui._copy_all_rows_as_tsv()

    # Should not have tried to copy anything
    assert "info" in captured
    title, msg = captured["info"]  # type: ignore[misc]
    assert "Copy All Rows as TSV" in title
    assert "There are no rows" in msg
    assert gui.status_var.get() == "No rows to copy."


# ----------------------------------------
# Tests: Export as TSV
# ----------------------------------------


def test_export_results_tsv_writes_file_and_shows_info(
    gui_with_results: PriceCheckerGUI, tmp_path: Path, monkeypatch
) -> None:
    called: dict[str, object] = {}

    export_target = tmp_path / "export_results.tsv"

    # Monkeypatch asksaveasfilename to return our target path
    import tkinter.filedialog as filedialog_module

    def fake_asksaveasfilename(**kwargs) -> str:
        called["path"] = kwargs.get("initialfile") or str(export_target)
        return str(export_target)

    monkeypatch.setattr(filedialog_module, "asksaveasfilename", fake_asksaveasfilename)

    # Avoid real message boxes
    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        called["info"] = (title, message)

    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    gui_with_results._export_results_tsv()

    # Export path was chosen
    assert export_target.exists()
    assert "info" in called
    title, msg = called["info"]  # type: ignore[misc]
    assert "Export TSV" in title
    assert str(export_target) in msg
    status = gui_with_results.status_var.get()
    assert "Exported results to" in status


def test_export_results_tsv_cancelled_updates_status(
    gui_with_results: PriceCheckerGUI, monkeypatch
) -> None:
    import tkinter.filedialog as filedialog_module

    def fake_asksaveasfilename(**kwargs) -> str:
        return ""  # simulate cancel

    monkeypatch.setattr(filedialog_module, "asksaveasfilename", fake_asksaveasfilename)

    # Avoid message boxes entirely
    import tkinter.messagebox as messagebox_module

    monkeypatch.setattr(messagebox_module, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(messagebox_module, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(messagebox_module, "askyesno", lambda *a, **k: False)

    gui_with_results._export_results_tsv()

    assert gui_with_results.status_var.get() == "Export cancelled."
