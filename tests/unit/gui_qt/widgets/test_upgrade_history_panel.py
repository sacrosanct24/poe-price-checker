"""Tests for UpgradeHistoryPanel widget."""

from __future__ import annotations

from typing import List, Dict, Any

import pytest

from gui_qt.widgets.upgrade_history_panel import UpgradeHistoryPanel


@pytest.fixture
def panel(qtbot):
    """Create a UpgradeHistoryPanel for testing."""
    widget = UpgradeHistoryPanel()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def sample_history() -> List[Dict[str, Any]]:
    """Sample history data for testing."""
    return [
        {
            "id": 1,
            "profile_name": "TestBuild",
            "slot": "Helmet",
            "item_hash": "abc123",
            "advice_text": "# Analysis\n\nThis is a test analysis with some **bold** text.",
            "ai_model": "gemini-2.0-flash",
            "ai_provider": "gemini",
            "include_stash": True,
            "stash_candidates_count": 5,
            "created_at": "2025-12-07 14:30:00",
        },
        {
            "id": 2,
            "profile_name": "TestBuild",
            "slot": "Helmet",
            "item_hash": "abc123",
            "advice_text": "# Second Analysis\n\nAnother test.",
            "ai_model": None,
            "ai_provider": "claude",
            "include_stash": False,
            "stash_candidates_count": 0,
            "created_at": "2025-12-06 10:15:00",
        },
    ]


class TestUpgradeHistoryPanelInit:
    """Tests for initialization."""

    def test_init_creates_widgets(self, panel):
        """Test that all required widgets are created."""
        assert panel.slot_label is not None
        assert panel.history_list is not None
        assert panel.preview_text is not None
        assert panel.use_btn is not None

    def test_init_default_state(self, panel):
        """Test initial state of panel."""
        assert panel._current_slot is None
        assert panel._history_items == []
        assert panel._selected_id is None

    def test_init_use_btn_disabled(self, panel):
        """Test that use button is initially disabled."""
        assert not panel.use_btn.isEnabled()


class TestLoadHistory:
    """Tests for load_history method."""

    def test_load_history_updates_slot_label(self, panel, sample_history):
        """Test that loading history updates the slot label."""
        panel.load_history("Helmet", sample_history)
        assert "Helmet" in panel.slot_label.text()
        assert "(2)" in panel.slot_label.text()

    def test_load_history_populates_list(self, panel, sample_history):
        """Test that loading history populates the list."""
        panel.load_history("Helmet", sample_history)
        assert panel.history_list.count() == 2

    def test_load_history_stores_items(self, panel, sample_history):
        """Test that history items are stored."""
        panel.load_history("Helmet", sample_history)
        assert panel._history_items == sample_history
        assert panel._current_slot == "Helmet"

    def test_load_empty_history(self, panel):
        """Test loading empty history shows placeholder."""
        panel.load_history("Helmet", [])
        assert panel.history_list.count() == 1
        item = panel.history_list.item(0)
        assert "No previous" in item.text()

    def test_load_history_formats_timestamp(self, panel, sample_history):
        """Test that timestamps are formatted correctly."""
        panel.load_history("Helmet", sample_history)
        item = panel.history_list.item(0)
        # Should contain date like "Dec 07"
        assert "Dec 07" in item.text() or "14:30" in item.text()

    def test_load_history_shows_provider(self, panel, sample_history):
        """Test that AI provider is shown."""
        panel.load_history("Helmet", sample_history)
        item = panel.history_list.item(0)
        assert "Gemini" in item.text()

    def test_load_history_shows_stash_indicator(self, panel, sample_history):
        """Test stash indicator appears."""
        panel.load_history("Helmet", sample_history)
        first_item = panel.history_list.item(0)
        second_item = panel.history_list.item(1)
        assert "+stash" in first_item.text()
        assert "trade" in second_item.text()


class TestItemClick:
    """Tests for item click handling."""

    def test_item_click_shows_preview(self, panel, sample_history, qtbot):
        """Test clicking an item shows preview."""
        panel.load_history("Helmet", sample_history)

        item = panel.history_list.item(0)
        panel._on_item_clicked(item)

        assert panel._selected_id == 1
        assert panel.use_btn.isEnabled()

    def test_item_click_emits_signal(self, panel, sample_history, qtbot):
        """Test clicking an item emits history_selected signal."""
        panel.load_history("Helmet", sample_history)

        with qtbot.waitSignal(panel.history_selected, timeout=1000) as blocker:
            item = panel.history_list.item(0)
            panel._on_item_clicked(item)

        assert blocker.args == [1]

    def test_item_double_click_emits_use_cached(self, panel, sample_history, qtbot):
        """Test double-clicking emits use_cached signal."""
        panel.load_history("Helmet", sample_history)

        with qtbot.waitSignal(panel.use_cached, timeout=1000) as blocker:
            item = panel.history_list.item(0)
            panel._on_item_double_clicked(item)

        assert blocker.args == [1]


class TestUseCached:
    """Tests for use cached functionality."""

    def test_use_btn_click_emits_signal(self, panel, sample_history, qtbot):
        """Test clicking use button emits use_cached signal."""
        panel.load_history("Helmet", sample_history)

        # First select an item
        item = panel.history_list.item(0)
        panel._on_item_clicked(item)

        # Then click use button
        with qtbot.waitSignal(panel.use_cached, timeout=1000) as blocker:
            panel.use_btn.click()

        assert blocker.args == [1]


class TestClear:
    """Tests for clear method."""

    def test_clear_resets_state(self, panel, sample_history):
        """Test that clear resets all state."""
        panel.load_history("Helmet", sample_history)
        panel._selected_id = 1

        panel.clear()

        assert panel._current_slot is None
        assert panel._history_items == []
        assert panel._selected_id is None
        assert panel.history_list.count() == 0


class TestGetEntryById:
    """Tests for get_entry_by_id method."""

    def test_get_existing_entry(self, panel, sample_history):
        """Test getting an existing entry by ID."""
        panel.load_history("Helmet", sample_history)

        entry = panel.get_entry_by_id(1)

        assert entry is not None
        assert entry["id"] == 1
        assert entry["ai_provider"] == "gemini"

    def test_get_nonexistent_entry(self, panel, sample_history):
        """Test getting a non-existent entry returns None."""
        panel.load_history("Helmet", sample_history)

        entry = panel.get_entry_by_id(999)

        assert entry is None


class TestGetSelectedId:
    """Tests for get_selected_id method."""

    def test_initial_selected_id_is_none(self, panel):
        """Test that initial selected ID is None."""
        assert panel.get_selected_id() is None

    def test_selected_id_after_click(self, panel, sample_history):
        """Test selected ID after clicking an item."""
        panel.load_history("Helmet", sample_history)

        item = panel.history_list.item(0)
        panel._on_item_clicked(item)

        assert panel.get_selected_id() == 1
