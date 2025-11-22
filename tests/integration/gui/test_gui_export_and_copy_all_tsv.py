# tests/test_gui_export_and_copy_all_tsv.py

import tkinter as tk
from pathlib import Path

import pytest

from gui.main_window import PriceCheckerGUI

pytestmark = pytest.mark.integration


@pytest.fixture
def tk_root() -> tk.Tk:
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
def gui_with_results(tk_root: tk.Tk) -> PriceCheckerGUI:
    gui = PriceCheckerGUI(tk_root, _DummyContext())
    # Insert a couple of rows into the real ResultsTable.
    # NOTE: The GUI now also adds aggregate rows per logical item,
    # so the final table will contain more than just these two rows.
    rows = [
        {
            "item_name": "ExportItem1",
            "variant": "v1",
            "links": "6",
            "chaos_value": "10",
            "divine_value": "0.1",
            "listing_count": "3",
            "source": "test",
        },
        {
            "item_name": "ExportItem2",
            "variant": "v2",
            "links": "4",
            "chaos_value": "5",
            "divine_value": "0.05",
            "listing_count": "2",
            "source": "test",
        },
    ]
    gui._insert_result_rows(rows)
    return gui


def test_copy_all_rows_as_tsv_uses_clipboard(gui_with_results: PriceCheckerGUI, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_set_clipboard(text: str) -> None:
        captured["value"] = text

    # Avoid real message boxes during test
    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        captured["info"] = (title, message)

    monkeypatch.setattr(gui_with_results, "_set_clipboard", fake_set_clipboard)
    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    gui_with_results._copy_all_rows_as_tsv()

    assert "value" in captured
    tsv = captured["value"]
    assert isinstance(tsv, str)

    lines = tsv.splitlines()
    # We expect at least:
    #   1 header line + 2 per-source rows + 2 aggregate rows = 5
    # but future sources or changes may add more. So just require >= 3.
    assert len(lines) >= 3

    header = lines[0]
    assert "item_name" in header
    assert "source" in header

    # Data lines (skip header)
    data_lines = lines[1:]

    # Ensure our two logical items appear somewhere in the TSV
    assert any("ExportItem1" in line for line in data_lines)
    assert any("ExportItem2" in line for line in data_lines)

    # We should also have seen the informational dialog
    assert "info" in captured
    title, msg = captured["info"]  # type: ignore[assignment]
    assert "Copy All Rows as TSV" in title


def test_export_results_tsv_calls_export_and_handles_path(
    gui_with_results: PriceCheckerGUI,
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Monkeypatch asksaveasfilename to return a path
    from tkinter import filedialog as filedialog_module

    export_target = tmp_path / "gui_export.tsv"

    def fake_asksaveasfilename(**kwargs) -> str:
        return str(export_target)

    monkeypatch.setattr(filedialog_module, "asksaveasfilename", fake_asksaveasfilename)

    # Monkeypatch ResultsTable.export_tsv to track that it was called with the same path
    called: dict[str, object] = {}

    def fake_export_tsv(path: str | Path, include_header: bool = False) -> None:
        called["path"] = Path(path)
        called["include_header"] = include_header
        # Optionally, write something so we can assert file existence
        Path(path).write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(gui_with_results.results_table, "export_tsv", fake_export_tsv)

    # Avoid real messageboxes
    import tkinter.messagebox as messagebox_module

    def fake_showinfo(title: str, message: str) -> None:
        called["info"] = (title, message)

    monkeypatch.setattr(messagebox_module, "showinfo", fake_showinfo)

    gui_with_results._export_results_tsv()

    assert "path" in called
    assert called["path"] == export_target
    assert called["include_header"] is True
    assert export_target.exists()
    assert "info" in called
