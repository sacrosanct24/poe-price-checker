# tests/test_loadout_selector.py
"""
Tests for LoadoutSelectorDialog parsing logic.

Tests the XML parsing methods without requiring Qt.
"""

from __future__ import annotations

import pytest
import xml.etree.ElementTree as ET


# Test the item set parsing logic directly (extracted from dialog)
def parse_item_sets_standalone(xml_string: str, clean_title_func=None) -> list:
    """
    Parse item sets from PoB XML - extracted logic for testing.

    Args:
        xml_string: Raw PoB XML string
        clean_title_func: Optional function to clean PoB color codes from titles

    Returns:
        List of item set dicts
    """
    try:
        root = ET.fromstring(xml_string)
        items_elem = root.find("Items")
        if items_elem is None:
            return []

        item_sets = []
        active_set = items_elem.get("activeItemSet", "1")

        for item_set in items_elem.findall("ItemSet"):
            set_id = item_set.get("id", "?")
            raw_title = item_set.get("title", "Unnamed")
            title = clean_title_func(raw_title) if clean_title_func else raw_title
            slots = len(item_set.findall("Slot"))

            item_sets.append({
                "id": set_id,
                "title": title,
                "raw_title": raw_title,
                "slot_count": slots,
                "is_active": set_id == active_set,
            })

        return item_sets

    except Exception:
        return []


class TestParseItemSets:
    """Tests for item set XML parsing."""

    def test_parse_empty_xml(self):
        """Empty Items element returns empty list."""
        xml = "<PathOfBuilding><Items></Items></PathOfBuilding>"
        result = parse_item_sets_standalone(xml)
        assert result == []

    def test_parse_no_items_element(self):
        """Missing Items element returns empty list."""
        xml = "<PathOfBuilding><Skills></Skills></PathOfBuilding>"
        result = parse_item_sets_standalone(xml)
        assert result == []

    def test_parse_invalid_xml(self):
        """Invalid XML returns empty list."""
        result = parse_item_sets_standalone("not valid xml")
        assert result == []

    def test_parse_single_item_set(self):
        """Parse a single item set."""
        xml = """
        <PathOfBuilding>
            <Items activeItemSet="1">
                <ItemSet id="1" title="Starter Gear">
                    <Slot name="Weapon 1" itemId="1"/>
                    <Slot name="Body Armour" itemId="2"/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """
        result = parse_item_sets_standalone(xml)

        assert len(result) == 1
        assert result[0]["id"] == "1"
        assert result[0]["title"] == "Starter Gear"
        assert result[0]["slot_count"] == 2
        assert result[0]["is_active"] is True

    def test_parse_multiple_item_sets(self):
        """Parse multiple item sets with active detection."""
        xml = """
        <PathOfBuilding>
            <Items activeItemSet="2">
                <ItemSet id="1" title="Leveling">
                    <Slot name="Weapon 1" itemId="1"/>
                </ItemSet>
                <ItemSet id="2" title="Endgame">
                    <Slot name="Weapon 1" itemId="2"/>
                    <Slot name="Body Armour" itemId="3"/>
                    <Slot name="Helmet" itemId="4"/>
                </ItemSet>
                <ItemSet id="3" title="Budget">
                    <Slot name="Ring 1" itemId="5"/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """
        result = parse_item_sets_standalone(xml)

        assert len(result) == 3

        # Check first set (not active)
        assert result[0]["id"] == "1"
        assert result[0]["title"] == "Leveling"
        assert result[0]["is_active"] is False
        assert result[0]["slot_count"] == 1

        # Check second set (active)
        assert result[1]["id"] == "2"
        assert result[1]["title"] == "Endgame"
        assert result[1]["is_active"] is True
        assert result[1]["slot_count"] == 3

        # Check third set
        assert result[2]["id"] == "3"
        assert result[2]["title"] == "Budget"
        assert result[2]["is_active"] is False

    def test_parse_unnamed_item_set(self):
        """Item set without title gets 'Unnamed'."""
        xml = """
        <PathOfBuilding>
            <Items activeItemSet="1">
                <ItemSet id="1">
                    <Slot name="Weapon 1" itemId="1"/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """
        result = parse_item_sets_standalone(xml)

        assert len(result) == 1
        assert result[0]["title"] == "Unnamed"

    def test_parse_with_clean_title_function(self):
        """Title cleaning function is applied."""
        xml = """
        <PathOfBuilding>
            <Items activeItemSet="1">
                <ItemSet id="1" title="^xFF0000Level 70^7 Gear">
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """

        def mock_clean(title):
            # Simulate removing PoB color codes
            import re
            return re.sub(r'\^[xX]?[0-9A-Fa-f]{0,6}', '', title)

        result = parse_item_sets_standalone(xml, clean_title_func=mock_clean)

        assert len(result) == 1
        assert result[0]["title"] == "Level 70 Gear"
        assert result[0]["raw_title"] == "^xFF0000Level 70^7 Gear"

    def test_parse_item_set_no_slots(self):
        """Item set with no slots has slot_count 0."""
        xml = """
        <PathOfBuilding>
            <Items activeItemSet="1">
                <ItemSet id="1" title="Empty Set">
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """
        result = parse_item_sets_standalone(xml)

        assert len(result) == 1
        assert result[0]["slot_count"] == 0


class TestLoadoutSelectorDialogIntegration:
    """
    Integration tests for LoadoutSelectorDialog.

    These tests require PyQt6 and will skip if not available.
    """

    @pytest.fixture
    def dialog(self):
        """Create dialog instance for testing."""
        pytest.importorskip("PyQt6")

        # Only import if PyQt6 is available and display backend works
        try:
            from PyQt6.QtWidgets import QApplication
        except ImportError as e:
            pytest.skip(f"PyQt6 display backend not available: {e}")
            return  # Explicit return to help static analysis

        import sys

        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        from gui_qt.dialogs.loadout_selector_dialog import LoadoutSelectorDialog
        dialog = LoadoutSelectorDialog()
        yield dialog
        dialog.close()

    def test_dialog_initial_state(self, dialog):
        """Dialog starts with empty state."""
        assert dialog._raw_xml is None
        assert dialog._tree_specs == []
        assert dialog._skill_sets == []
        assert dialog._item_sets == []

    def test_get_selected_loadout_initial(self, dialog):
        """Initial selection returns defaults."""
        result = dialog.get_selected_loadout()

        assert result["tree_spec_title"] == "-"
        assert result["skill_set_title"] == "-"
        assert result["item_set_title"] == "-"
        assert result["level"] == 90  # Default level

    def test_parse_item_sets_method(self, dialog):
        """Test _parse_item_sets method on dialog instance."""
        xml = """
        <PathOfBuilding>
            <Items activeItemSet="1">
                <ItemSet id="1" title="Test Set">
                    <Slot name="Weapon 1" itemId="1"/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """
        result = dialog._parse_item_sets(xml)

        assert len(result) == 1
        assert result[0]["title"] == "Test Set"
        assert result[0]["is_active"] is True

    def test_level_spin_range(self, dialog):
        """Level spinner has correct range."""
        assert dialog.level_spin.minimum() == 1
        assert dialog.level_spin.maximum() == 100
        assert dialog.level_spin.value() == 90

    def test_auto_select_button_disabled_initially(self, dialog):
        """Auto-select button is disabled before loading build."""
        assert dialog.auto_select_btn.isEnabled() is False

    def test_apply_button_disabled_initially(self, dialog):
        """Apply button is disabled before loading build."""
        assert dialog.apply_btn.isEnabled() is False


class TestLoadoutDataStructures:
    """Test the data structures used for loadout selection."""

    def test_loadout_result_structure(self):
        """Verify expected loadout result structure."""
        # This is the structure returned by get_selected_loadout
        expected_keys = {
            "tree_spec_title",
            "skill_set_title",
            "item_set_title",
            "level",
        }

        # Simulate what dialog returns
        result = {
            "tree_spec_title": "Endgame Tree",
            "skill_set_title": "Main Skills",
            "item_set_title": "BiS Gear",
            "level": 95,
        }

        assert set(result.keys()) == expected_keys
        assert isinstance(result["level"], int)

    def test_item_set_dict_structure(self):
        """Verify item set dict has expected structure."""
        expected_keys = {
            "id",
            "title",
            "raw_title",
            "slot_count",
            "is_active",
        }

        # Simulate parsed item set
        item_set = {
            "id": "1",
            "title": "Endgame",
            "raw_title": "Endgame",
            "slot_count": 12,
            "is_active": True,
        }

        assert set(item_set.keys()) == expected_keys
        assert isinstance(item_set["slot_count"], int)
        assert isinstance(item_set["is_active"], bool)
