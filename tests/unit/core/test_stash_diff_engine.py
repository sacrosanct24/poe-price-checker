"""Tests for stash_diff_engine.py - Stash snapshot comparison for loot detection."""

import pytest
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from core.stash_diff_engine import (
    ItemFingerprint,
    StackChange,
    StashDiff,
    StashDiffEngine,
    extract_item_value,
    get_rarity_name,
)


# =============================================================================
# Mock Classes for Testing
# =============================================================================


@dataclass
class MockStashTab:
    """Mock stash tab for testing."""
    id: str
    name: str
    index: int
    type: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    folder: Optional[str] = None
    children: List["MockStashTab"] = field(default_factory=list)


@dataclass
class MockStashSnapshot:
    """Mock stash snapshot for testing."""
    account_name: str
    league: str
    tabs: List[MockStashTab] = field(default_factory=list)
    total_items: int = 0
    fetched_at: str = ""


# =============================================================================
# ItemFingerprint Tests
# =============================================================================


class TestItemFingerprintBasics:
    """Basic tests for ItemFingerprint."""

    def test_from_item_currency(self):
        """Can create fingerprint from currency item."""
        item = {
            "name": "",
            "typeLine": "Chaos Orb",
            "stackSize": 10,
            "x": 0,
            "y": 0,
            "frameType": 5,
            "ilvl": 0,
        }
        fp = ItemFingerprint.from_item(item, "tab-1")

        assert fp.name == ""
        assert fp.base_type == "Chaos Orb"
        assert fp.stack_size == 10
        assert fp.position == (0, 0)
        assert fp.tab_id == "tab-1"
        assert fp.rarity == 5

    def test_from_item_unique(self):
        """Can create fingerprint from unique item."""
        item = {
            "name": "Headhunter",
            "typeLine": "Leather Belt",
            "x": 5,
            "y": 3,
            "frameType": 3,
            "ilvl": 83,
        }
        fp = ItemFingerprint.from_item(item, "tab-2")

        assert fp.name == "Headhunter"
        assert fp.base_type == "Leather Belt"
        assert fp.stack_size == 1
        assert fp.rarity == 3
        assert fp.ilvl == 83

    def test_from_item_with_mods(self):
        """Fingerprint includes mods in hash."""
        item = {
            "name": "Mystic Ring",
            "typeLine": "Amethyst Ring",
            "x": 0,
            "y": 0,
            "frameType": 2,
            "ilvl": 75,
            "explicitMods": ["+30 to Maximum Life", "+20% to Fire Resistance"],
            "implicitMods": ["+15% Chaos Resistance"],
        }
        fp = ItemFingerprint.from_item(item, "tab-1")

        # Hash should be deterministic
        assert len(fp.item_hash) == 16

    def test_from_item_with_sockets(self):
        """Fingerprint includes sockets in hash."""
        item = {
            "name": "Test Armor",
            "typeLine": "Astral Plate",
            "x": 0,
            "y": 0,
            "frameType": 2,
            "sockets": [
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "G"},
                {"group": 1, "sColour": "B"},
            ],
        }
        fp = ItemFingerprint.from_item(item, "tab-1")
        assert fp.item_hash is not None


class TestItemFingerprintProperties:
    """Tests for ItemFingerprint properties."""

    def test_display_name_with_name(self):
        """display_name includes both name and base type."""
        fp = ItemFingerprint(
            name="Headhunter",
            base_type="Leather Belt",
            stack_size=1,
            position=(0, 0),
            tab_id="tab-1",
            item_hash="abc123",
        )
        assert fp.display_name == "Headhunter Leather Belt"

    def test_display_name_without_name(self):
        """display_name uses only base type if no name."""
        fp = ItemFingerprint(
            name="",
            base_type="Chaos Orb",
            stack_size=10,
            position=(0, 0),
            tab_id="tab-1",
            item_hash="abc123",
        )
        assert fp.display_name == "Chaos Orb"

    def test_position_key(self):
        """position_key format is correct."""
        fp = ItemFingerprint(
            name="Test",
            base_type="Test",
            stack_size=1,
            position=(5, 3),
            tab_id="tab-1",
            item_hash="abc123",
        )
        assert fp.position_key == "tab-1:5,3"

    def test_content_key(self):
        """content_key format is correct."""
        fp = ItemFingerprint(
            name="Test",
            base_type="Test",
            stack_size=1,
            position=(0, 0),
            tab_id="tab-1",
            item_hash="abc123",
        )
        assert fp.content_key == "tab-1:abc123"


class TestItemFingerprintHashing:
    """Tests for fingerprint hash consistency."""

    def test_same_item_same_hash(self):
        """Same item produces same hash."""
        item = {
            "name": "Headhunter",
            "typeLine": "Leather Belt",
            "x": 0,
            "y": 0,
            "frameType": 3,
            "ilvl": 83,
        }
        fp1 = ItemFingerprint.from_item(item, "tab-1")
        fp2 = ItemFingerprint.from_item(item, "tab-1")
        assert fp1.item_hash == fp2.item_hash

    def test_different_position_same_hash(self):
        """Items at different positions have same hash if content identical."""
        item1 = {
            "name": "Headhunter",
            "typeLine": "Leather Belt",
            "x": 0,
            "y": 0,
            "frameType": 3,
            "ilvl": 83,
        }
        item2 = {
            "name": "Headhunter",
            "typeLine": "Leather Belt",
            "x": 5,
            "y": 3,
            "frameType": 3,
            "ilvl": 83,
        }
        fp1 = ItemFingerprint.from_item(item1, "tab-1")
        fp2 = ItemFingerprint.from_item(item2, "tab-1")
        assert fp1.item_hash == fp2.item_hash

    def test_different_mods_different_hash(self):
        """Items with different mods have different hashes."""
        item1 = {
            "name": "Ring",
            "typeLine": "Ruby Ring",
            "x": 0,
            "y": 0,
            "frameType": 2,
            "explicitMods": ["+30 to Maximum Life"],
        }
        item2 = {
            "name": "Ring",
            "typeLine": "Ruby Ring",
            "x": 0,
            "y": 0,
            "frameType": 2,
            "explicitMods": ["+40 to Maximum Life"],
        }
        fp1 = ItemFingerprint.from_item(item1, "tab-1")
        fp2 = ItemFingerprint.from_item(item2, "tab-1")
        assert fp1.item_hash != fp2.item_hash


# =============================================================================
# StackChange Tests
# =============================================================================


class TestStackChange:
    """Tests for StackChange dataclass."""

    def test_is_gain_positive_delta(self):
        """is_gain returns True for positive delta."""
        fp = ItemFingerprint(
            name="", base_type="Chaos Orb", stack_size=100,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        change = StackChange(item={}, delta=10, fingerprint=fp)
        assert change.is_gain is True
        assert change.is_loss is False

    def test_is_loss_negative_delta(self):
        """is_loss returns True for negative delta."""
        fp = ItemFingerprint(
            name="", base_type="Chaos Orb", stack_size=90,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        change = StackChange(item={}, delta=-10, fingerprint=fp)
        assert change.is_gain is False
        assert change.is_loss is True

    def test_zero_delta(self):
        """Zero delta is neither gain nor loss."""
        fp = ItemFingerprint(
            name="", base_type="Chaos Orb", stack_size=100,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        change = StackChange(item={}, delta=0, fingerprint=fp)
        assert change.is_gain is False
        assert change.is_loss is False


# =============================================================================
# StashDiff Tests
# =============================================================================


class TestStashDiffBasics:
    """Basic tests for StashDiff."""

    def test_empty_diff(self):
        """Empty diff has no changes."""
        diff = StashDiff()
        assert not diff.has_changes
        assert diff.loot_count == 0
        assert diff.items_gained == 0
        assert diff.items_lost == 0

    def test_has_changes_with_added(self):
        """has_changes is True with added items."""
        diff = StashDiff(added_items=[{"typeLine": "Divine Orb"}])
        assert diff.has_changes is True

    def test_has_changes_with_removed(self):
        """has_changes is True with removed items."""
        diff = StashDiff(removed_items=[{"typeLine": "Divine Orb"}])
        assert diff.has_changes is True

    def test_has_changes_with_stack_changes(self):
        """has_changes is True with stack changes."""
        fp = ItemFingerprint(
            name="", base_type="Chaos", stack_size=100,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        diff = StashDiff(stack_changes=[StackChange(item={}, delta=10, fingerprint=fp)])
        assert diff.has_changes is True


class TestStashDiffCounts:
    """Tests for StashDiff count properties."""

    def test_loot_count_added_only(self):
        """loot_count counts added items."""
        diff = StashDiff(added_items=[{}, {}, {}])
        assert diff.loot_count == 3

    def test_loot_count_with_stack_gains(self):
        """loot_count includes stack gains."""
        fp = ItemFingerprint(
            name="", base_type="Chaos", stack_size=100,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        diff = StashDiff(
            added_items=[{}],
            stack_changes=[StackChange(item={}, delta=10, fingerprint=fp)],
        )
        assert diff.loot_count == 2

    def test_items_gained(self):
        """items_gained counts added items and stack gains."""
        fp = ItemFingerprint(
            name="", base_type="Chaos", stack_size=100,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        diff = StashDiff(
            added_items=[{}, {}],
            stack_changes=[StackChange(item={}, delta=15, fingerprint=fp)],
        )
        assert diff.items_gained == 17  # 2 added + 15 stack gain

    def test_items_lost(self):
        """items_lost counts removed items and stack losses."""
        fp = ItemFingerprint(
            name="", base_type="Chaos", stack_size=100,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        diff = StashDiff(
            removed_items=[{}],
            stack_changes=[StackChange(item={}, delta=-10, fingerprint=fp)],
        )
        assert diff.items_lost == 11  # 1 removed + 10 stack loss


class TestStashDiffSummary:
    """Tests for StashDiff summary."""

    def test_get_summary_no_changes(self):
        """Summary shows no changes."""
        diff = StashDiff()
        assert diff.get_summary() == "No changes"

    def test_get_summary_added_only(self):
        """Summary shows added count."""
        diff = StashDiff(added_items=[{}, {}])
        summary = diff.get_summary()
        assert "+2 new" in summary

    def test_get_summary_removed_only(self):
        """Summary shows removed count."""
        diff = StashDiff(removed_items=[{}, {}, {}])
        summary = diff.get_summary()
        assert "-3 removed" in summary

    def test_get_summary_mixed(self):
        """Summary shows all change types."""
        fp = ItemFingerprint(
            name="", base_type="Chaos", stack_size=100,
            position=(0, 0), tab_id="tab-1", item_hash="abc",
        )
        diff = StashDiff(
            added_items=[{}],
            removed_items=[{}],
            stack_changes=[StackChange(item={}, delta=10, fingerprint=fp)],
        )
        summary = diff.get_summary()
        assert "+1 new" in summary
        assert "-1 removed" in summary


# =============================================================================
# StashDiffEngine Tests
# =============================================================================


class TestStashDiffEngineBasics:
    """Basic tests for StashDiffEngine."""

    def test_init_default(self):
        """Engine initializes with defaults."""
        engine = StashDiffEngine()
        assert not engine.has_before_snapshot
        assert engine._tracked_tabs is None

    def test_init_with_tracked_tabs(self):
        """Engine can be initialized with tracked tabs."""
        engine = StashDiffEngine(tracked_tabs=["Currency", "Quad"])
        assert engine._tracked_tabs == {"Currency", "Quad"}

    def test_init_ignore_currency(self):
        """Engine can be set to ignore currency changes."""
        engine = StashDiffEngine(ignore_currency_changes=True)
        assert engine._ignore_currency_changes is True

    def test_has_before_snapshot_false(self):
        """has_before_snapshot is False initially."""
        engine = StashDiffEngine()
        assert engine.has_before_snapshot is False


class TestStashDiffEngineSetBefore:
    """Tests for setting before snapshot."""

    def test_set_before_snapshot(self):
        """Can set before snapshot."""
        engine = StashDiffEngine()
        tab = MockStashTab(
            id="tab-1", name="Currency", index=0, type="CurrencyStash",
            items=[{"typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0}],
        )
        snapshot = MockStashSnapshot(
            account_name="test", league="Settlers", tabs=[tab],
        )
        engine.set_before_snapshot(snapshot)

        assert engine.has_before_snapshot is True

    def test_clear(self):
        """Can clear before snapshot."""
        engine = StashDiffEngine()
        tab = MockStashTab(
            id="tab-1", name="Currency", index=0, type="CurrencyStash",
            items=[{"typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0}],
        )
        snapshot = MockStashSnapshot(
            account_name="test", league="Settlers", tabs=[tab],
        )
        engine.set_before_snapshot(snapshot)
        engine.clear()

        assert engine.has_before_snapshot is False


class TestStashDiffEngineComputeDiff:
    """Tests for computing stash diffs."""

    def test_diff_no_before_snapshot(self):
        """Returns empty diff if no before snapshot."""
        engine = StashDiffEngine()
        after = MockStashSnapshot(account_name="test", league="Settlers")
        diff = engine.compute_diff(after)

        assert not diff.has_changes

    def test_diff_no_changes(self):
        """Detects when there are no changes."""
        items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5},
        ]
        tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[tab])

        # Same items in after
        after_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=items.copy())
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

        engine = StashDiffEngine()
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert not diff.has_changes

    def test_diff_added_item(self):
        """Detects added items."""
        before_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5},
        ]
        before_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=before_items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[before_tab])

        after_items = before_items + [
            {"name": "", "typeLine": "Divine Orb", "stackSize": 1, "x": 1, "y": 0, "frameType": 5},
        ]
        after_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=after_items)
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

        engine = StashDiffEngine()
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert len(diff.added_items) == 1
        assert diff.added_items[0]["typeLine"] == "Divine Orb"

    def test_diff_removed_item(self):
        """Detects removed items."""
        before_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5},
            {"name": "Headhunter", "typeLine": "Leather Belt", "x": 1, "y": 0, "frameType": 3, "ilvl": 83},
        ]
        before_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=before_items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[before_tab])

        # Remove the headhunter
        after_items = [before_items[0]]
        after_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=after_items)
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

        engine = StashDiffEngine()
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert len(diff.removed_items) == 1
        assert diff.removed_items[0]["name"] == "Headhunter"

    def test_diff_stack_increase(self):
        """Detects stack size increases."""
        before_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        before_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=before_items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[before_tab])

        after_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 150, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        after_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=after_items)
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

        engine = StashDiffEngine()
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert len(diff.stack_changes) == 1
        assert diff.stack_changes[0].delta == 50
        assert diff.stack_changes[0].is_gain

    def test_diff_stack_decrease(self):
        """Detects stack size decreases."""
        before_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        before_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=before_items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[before_tab])

        after_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 80, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        after_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=after_items)
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

        engine = StashDiffEngine()
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert len(diff.stack_changes) == 1
        assert diff.stack_changes[0].delta == -20
        assert diff.stack_changes[0].is_loss


class TestStashDiffEngineTabFiltering:
    """Tests for tab filtering."""

    def test_tracked_tabs_only(self):
        """Only tracked tabs are processed."""
        currency_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5},
        ]
        quad_items = [
            {"name": "", "typeLine": "Divine Orb", "stackSize": 1, "x": 0, "y": 0, "frameType": 5},
        ]

        currency_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=currency_items)
        quad_tab = MockStashTab(id="tab-2", name="Quad", index=1, type="QuadStash", items=quad_items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[currency_tab, quad_tab])

        # Add item only to Currency tab
        after_currency_items = currency_items + [
            {"name": "", "typeLine": "Exalted Orb", "stackSize": 1, "x": 1, "y": 0, "frameType": 5},
        ]
        after_currency_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=after_currency_items)
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_currency_tab, quad_tab])

        # Only track Quad tab - should not see Currency changes
        engine = StashDiffEngine(tracked_tabs=["Quad"])
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert len(diff.added_items) == 0  # Currency tab not tracked

    def test_should_track_tab(self):
        """_should_track_tab works correctly."""
        engine = StashDiffEngine(tracked_tabs=["Currency", "Quad"])
        assert engine._should_track_tab("Currency") is True
        assert engine._should_track_tab("Quad") is True
        assert engine._should_track_tab("Normal") is False

    def test_no_filter_tracks_all(self):
        """Without filter, all tabs are tracked."""
        engine = StashDiffEngine()
        assert engine._should_track_tab("Currency") is True
        assert engine._should_track_tab("Anything") is True


class TestStashDiffEngineIgnoreCurrency:
    """Tests for ignoring small currency changes."""

    def test_ignore_small_currency_changes(self):
        """Small currency stack changes are ignored."""
        before_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        before_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=before_items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[before_tab])

        # Small change of +3
        after_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 103, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        after_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=after_items)
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

        engine = StashDiffEngine(ignore_currency_changes=True)
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        # Small currency change should be ignored
        assert len(diff.stack_changes) == 0

    def test_large_currency_changes_not_ignored(self):
        """Large currency stack changes are not ignored."""
        before_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        before_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=before_items)
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[before_tab])

        # Large change of +50
        after_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 150, "x": 0, "y": 0, "frameType": 5, "ilvl": 0},
        ]
        after_tab = MockStashTab(id="tab-1", name="Currency", index=0, type="CurrencyStash", items=after_items)
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

        engine = StashDiffEngine(ignore_currency_changes=True)
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert len(diff.stack_changes) == 1


class TestStashDiffEngineChildTabs:
    """Tests for handling child tabs (folder stashes)."""

    def test_processes_child_tabs(self):
        """Child tabs are processed."""
        child_items = [
            {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5},
        ]
        child_tab = MockStashTab(id="child-1", name="Child Tab", index=0, type="NormalStash", items=child_items)
        parent_tab = MockStashTab(
            id="tab-1", name="Folder", index=0, type="FolderStash",
            children=[child_tab],
        )
        before = MockStashSnapshot(account_name="test", league="Settlers", tabs=[parent_tab])

        # Add item to child tab
        after_child_items = child_items + [
            {"name": "", "typeLine": "Divine Orb", "stackSize": 1, "x": 1, "y": 0, "frameType": 5},
        ]
        after_child_tab = MockStashTab(id="child-1", name="Child Tab", index=0, type="NormalStash", items=after_child_items)
        after_parent_tab = MockStashTab(
            id="tab-1", name="Folder", index=0, type="FolderStash",
            children=[after_child_tab],
        )
        after = MockStashSnapshot(account_name="test", league="Settlers", tabs=[after_parent_tab])

        engine = StashDiffEngine()
        engine.set_before_snapshot(before)
        diff = engine.compute_diff(after)

        assert len(diff.added_items) == 1


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestExtractItemValue:
    """Tests for extract_item_value utility."""

    def test_extract_basic_item(self):
        """Extracts basic item properties."""
        item = {
            "name": "Headhunter",
            "typeLine": "Leather Belt",
            "stackSize": 1,
            "frameType": 3,
            "ilvl": 83,
            "identified": True,
            "corrupted": False,
            "icon": "http://example.com/icon.png",
        }
        result = extract_item_value(item)

        assert result["name"] == "Headhunter"
        assert result["base_type"] == "Leather Belt"
        assert result["display_name"] == "Headhunter Leather Belt"
        assert result["rarity"] == 3
        assert result["ilvl"] == 83
        assert result["identified"] is True
        assert result["corrupted"] is False

    def test_extract_currency(self):
        """Extracts currency (no name)."""
        item = {
            "name": "",
            "typeLine": "Chaos Orb",
            "stackSize": 10,
            "frameType": 5,
        }
        result = extract_item_value(item)

        assert result["name"] == ""
        assert result["display_name"] == "Chaos Orb"
        assert result["stack_size"] == 10

    def test_extract_defaults(self):
        """Uses defaults for missing fields."""
        item = {"typeLine": "Some Item"}
        result = extract_item_value(item)

        assert result["stack_size"] == 1
        assert result["rarity"] == 0
        assert result["identified"] is True
        assert result["corrupted"] is False


class TestGetRarityName:
    """Tests for get_rarity_name utility."""

    def test_rarity_names(self):
        """Returns correct rarity names."""
        assert get_rarity_name(0) == "Normal"
        assert get_rarity_name(1) == "Magic"
        assert get_rarity_name(2) == "Rare"
        assert get_rarity_name(3) == "Unique"
        assert get_rarity_name(4) == "Gem"
        assert get_rarity_name(5) == "Currency"
        assert get_rarity_name(6) == "Divination Card"
        assert get_rarity_name(7) == "Quest"
        assert get_rarity_name(8) == "Prophecy"
        assert get_rarity_name(9) == "Foil/Relic"

    def test_unknown_rarity(self):
        """Returns 'Unknown' for invalid frame types."""
        assert get_rarity_name(99) == "Unknown"
        assert get_rarity_name(-1) == "Unknown"
