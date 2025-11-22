# tests/integration/gui/test_gui_item_inspector_and_sources.py

import tkinter as tk

import pytest

from gui.main_window import PriceCheckerGUI, RESULT_COLUMNS

pytestmark = pytest.mark.integration


# -------------------------------------------------------------------
# Fixtures and test helpers
# -------------------------------------------------------------------

@pytest.fixture
def tk_root() -> tk.Tk:
    """
    Yield a hidden Tk root window and ensure it is destroyed after the test.

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


class FakeParsedItem:
    """Simple stand-in for a ParsedItem returned by ItemParser.parse."""

    def __init__(self) -> None:
        self.name = "Test Name"
        self.base_type = "Test Base"
        self.rarity = "Rare"
        self.variant = "V0"
        self.item_level = 82
        self.map_tier = None
        self.gem_level = None
        self.quality = "+20%"
        self.sockets = "W-W-W-W"
        self.links = 4
        self.influences = "Shaper, Elder"
        self.tags = ["ring", "life", "resistance"]


class FakeParser:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.last_text: str | None = None

    def parse(self, text: str) -> FakeParsedItem:
        self.last_text = text
        if self.should_fail:
            raise ValueError("parse error")
        return FakeParsedItem()


class FakePriceService:
    """
    Minimal fake multi-source price service for GUI tests.
    """

    def __init__(self) -> None:
        # Simulate a couple of named sources
        self._enabled_state: dict[str, bool] = {
            "poe_ninja": True,
            "suggested_undercut": True,
        }
        self.calls: list[str] = []

    def check_item(self, text: str):
        self.calls.append(text)
        # Return a simple list of dicts compatible with RESULT_COLUMNS
        return [
            {
                "item_name": "ExportedItem",
                "variant": "v1",
                "links": "6",
                "chaos_value": "10",
                "divine_value": "0.1",
                "listing_count": "3",
                "source": "poe_ninja",
            }
        ]

    # Multi-source toggling API:

    def get_enabled_state(self) -> dict[str, bool]:
        return dict(self._enabled_state)

    def set_enabled_state(self, state: dict[str, bool]) -> None:
        self._enabled_state = dict(state)


class _DummyContext:
    """
    Minimal stand-in for app_context used by PriceCheckerGUI in tests.
    Allows injecting parser and price_service.
    """
    def __init__(self, parser=None, price_service=None) -> None:
        self.logger = None  # GUI resolves its own fallback logger
        self.parser = parser
        self.price_service = price_service
        self.config = None  # not needed for these tests


@pytest.fixture
def gui_with_parser(tk_root: tk.Tk) -> PriceCheckerGUI:
    parser = FakeParser(should_fail=False)
    ctx = _DummyContext(parser=parser, price_service=None)
    return PriceCheckerGUI(tk_root, ctx)


@pytest.fixture
def gui_with_parser_and_service(tk_root: tk.Tk) -> tuple[PriceCheckerGUI, FakeParser, FakePriceService]:
    parser = FakeParser(should_fail=False)
    service = FakePriceService()
    ctx = _DummyContext(parser=parser, price_service=service)
    gui = PriceCheckerGUI(tk_root, ctx)
    return gui, parser, service


@pytest.fixture
def gui_basic(tk_root: tk.Tk) -> PriceCheckerGUI:
    """GUI with no parser/price service, used for filter-only behavior tests."""
    ctx = _DummyContext(parser=None, price_service=None)
    return PriceCheckerGUI(tk_root, ctx)


# -------------------------------------------------------------------
# Item Inspector tests
# -------------------------------------------------------------------

def test_item_inspector_displays_parsed_fields(gui_with_parser: PriceCheckerGUI) -> None:
    """
    The Item Inspector should display basic parsed fields from the parser:
    Name, Rarity, Item Level, etc.
    """
    sample_text = "Rarity: Rare\nSome Item\n--------\nItem Level: 82\n"
    gui_with_parser._update_item_inspector(sample_text)

    # Read text from the inspector widget
    inspector_text = gui_with_parser.item_inspector_text.get("1.0", "end").strip()

    assert "Name: Test Name" in inspector_text
    assert "Base: Test Base" in inspector_text
    assert "Rarity: Rare" in inspector_text
    assert "Item Level: 82" in inspector_text
    assert "Sockets/Links: W-W-W-W (4L)" in inspector_text
    assert "Influences: Shaper, Elder" in inspector_text
    # Tags are optional but our FakeParsedItem populates them
    assert "Tags: ['ring', 'life', 'resistance']" in inspector_text


def test_item_inspector_handles_parse_failure(tk_root: tk.Tk) -> None:
    """
    When the parser raises, the Item Inspector should show a helpful message
    instead of crashing or showing raw text.
    """
    parser = FakeParser(should_fail=True)
    ctx = _DummyContext(parser=parser, price_service=None)
    gui = PriceCheckerGUI(tk_root, ctx)

    sample_text = "Rarity: Rare\nBroken Item\n--------\nItem Level: 42\n"
    gui._update_item_inspector(sample_text)

    inspector_text = gui.item_inspector_text.get("1.0", "end").strip()

    assert "Parser: failed to parse item." in inspector_text
    # First line hint should also be present
    assert "First line: Rarity: Rare" in inspector_text


# -------------------------------------------------------------------
# Dev menu: Paste Sample Item
# -------------------------------------------------------------------

def test_paste_sample_item_triggers_price_check(gui_with_parser_and_service, monkeypatch) -> None:
    """
    Dev → Paste Sample Map should fill the input, update status, and when we
    run the check it should call the price service.
    """
    gui, parser, service = gui_with_parser_and_service

    # Avoid any accidental messagebox popups
    import tkinter.messagebox as messagebox_module

    monkeypatch.setattr(messagebox_module, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(messagebox_module, "showinfo", lambda *a, **k: None)

    gui._paste_sample_item("map")

    # After paste, input should not be empty
    input_text = gui._get_input_text()
    assert input_text
    assert "Rarity:" in input_text

    # Now run the price check directly (bypassing Tk's .after scheduling)
    gui._run_price_check()

    # Price service should have been called at least once
    assert len(service.calls) >= 1
    assert service.calls[-1] == input_text

    # Status should reflect the paste action (may have been updated by check)
    # Just assert the prefix to avoid depending on exact sequence.
    paste_status_prefix = "Pasted sample map item"
    assert any(
        gui.status_var.get().startswith(prefix)
        for prefix in (paste_status_prefix, "Price check complete.", "Checking prices...")
    )


# -------------------------------------------------------------------
# Source filter behavior
# -------------------------------------------------------------------

def test_source_filter_restricts_rows_by_source(gui_basic: PriceCheckerGUI) -> None:
    """
    When a source filter value is active, only rows with that source should be shown.
    """
    gui = gui_basic

    rows = [
        {
            "item_name": "Item1",
            "variant": "v1",
            "links": "6",
            "chaos_value": "10",
            "divine_value": "0.1",
            "listing_count": "3",
            "source": "poe_ninja",
        },
        {
            "item_name": "Item2",
            "variant": "v1",
            "links": "6",
            "chaos_value": "8",
            "divine_value": "0.08",
            "listing_count": "2",
            "source": "suggested_undercut",
        },
    ]

    gui._all_result_rows = rows
    gui.results_table.clear()
    gui.results_table.insert_rows(rows)

    # Manually set the source filter (we don't have a real multi-source service here)
    gui._source_filter_value = "poe_ninja"
    gui.source_filter_var.set("poe_ninja")

    gui._apply_filter("")

    visible_rows = list(gui.results_table.iter_rows())
    assert visible_rows, "Expected some rows to be visible after filtering."

    # All visible rows should have source == 'poe_ninja'
    source_idx = RESULT_COLUMNS.index("source")
    for row in visible_rows:
        assert row[source_idx] == "poe_ninja"


# -------------------------------------------------------------------
# Data sources dialog behavior
# -------------------------------------------------------------------

def test_sources_dialog_applies_enabled_state(tk_root: tk.Tk, monkeypatch) -> None:
    """
    The Data Sources dialog should read enabled_state from price_service,
    and _sources_apply_visibility should call set_enabled_state with
    the updated values.
    """
    service = FakePriceService()
    ctx = _DummyContext(parser=None, price_service=service)
    gui = PriceCheckerGUI(tk_root, ctx)

    # Avoid any popups from showinfo
    import tkinter.messagebox as messagebox_module

    monkeypatch.setattr(messagebox_module, "showinfo", lambda *a, **k: None)

    gui._show_sources_dialog()

    # All sources initially enabled
    initial_state = service.get_enabled_state()
    assert initial_state == {
        "poe_ninja": True,
        "suggested_undercut": True,
    }

    # Simulate user unchecking one of the sources in the dialog
    assert "poe_ninja" in gui._source_vars
    gui._source_vars["poe_ninja"].set(False)

    gui._sources_apply_visibility()

    updated_state = service.get_enabled_state()
    assert updated_state["poe_ninja"] is False
    assert updated_state["suggested_undercut"] is True

    # Status should indicate how many are enabled
    status = gui.status_var.get()
    assert "Updated data sources" in status
    assert "1/2 enabled" in status

def test_copy_last_summary_uses_clipboard(gui_with_parser_and_service, monkeypatch) -> None:
    """
    _copy_last_summary should copy the current summary_var text to the clipboard
    (via _set_clipboard) when a non-empty summary is present.
    """
    gui, parser, service = gui_with_parser_and_service

    captured: dict[str, str] = {}

    def fake_set_clipboard(text: str) -> None:
        captured["value"] = text

    monkeypatch.setattr(gui, "_set_clipboard", fake_set_clipboard)

    # Simulate a populated summary
    gui.summary_var.set("Tabula Rasa (6L) – 23.4c (0.12d) 34 listing(s) total sources: poe_ninja")

    gui._copy_last_summary()

    assert "value" in captured
    assert captured["value"] == gui.summary_var.get()
    # Status should reflect a successful copy
    assert "copied" in gui.status_var.get().lower()
