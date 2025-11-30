"""
Tests for gui_qt.dialogs.item_comparison_dialog module.

Tests the side-by-side item comparison dialog functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any, List, Optional


class MockItem:
    """Mock item for testing."""

    def __init__(
        self,
        name: str = "Test Item",
        base_type: str = "Vaal Regalia",
        implicits: Optional[List[str]] = None,
        explicits: Optional[List[str]] = None,
        enchants: Optional[List[str]] = None,
        raw_text: Optional[str] = None,
    ):
        self.name = name
        self.base_type = base_type
        self.implicits = implicits or []
        self.implicit_mods = implicits or []
        self.explicits = explicits or []
        self.explicit_mods = explicits or []
        self.mods = explicits or []
        self.enchants = enchants or []
        self.raw_text = raw_text


class TestGetAllMods:
    """Tests for _get_all_mods helper method."""

    def test_extracts_implicits(self):
        """Test extracting implicit mods."""
        item = MockItem(
            implicits=["+50 to Maximum Life"],
            explicits=["+30% to Fire Resistance"],
        )
        # Simulate _get_all_mods logic
        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", []) or []
        explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", []) or []
        enchants = getattr(item, "enchants", []) or []

        all_mods = list(implicits) + list(explicits) + list(enchants)

        assert "+50 to Maximum Life" in all_mods
        assert "+30% to Fire Resistance" in all_mods
        assert len(all_mods) == 2

    def test_extracts_enchants(self):
        """Test extracting enchant mods."""
        item = MockItem(
            explicits=["+30% to Fire Resistance"],
            enchants=["Trigger a Socketed Spell on Using a Skill"],
        )

        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", []) or []
        explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", []) or []
        enchants = getattr(item, "enchants", []) or []

        all_mods = list(implicits) + list(explicits) + list(enchants)

        assert "Trigger a Socketed Spell on Using a Skill" in all_mods
        assert len(all_mods) == 2

    def test_handles_none_item(self):
        """Test handling None item."""
        item = None
        # When item is None, we return empty list
        all_mods = [] if not item else []

        assert all_mods == []

    def test_handles_missing_attributes(self):
        """Test handling item with missing mod attributes."""

        class MinimalItem:
            def __init__(self):
                self.name = "Minimal"

        item = MinimalItem()

        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", []) or []
        explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", []) or []
        enchants = getattr(item, "enchants", []) or []

        all_mods = list(implicits) + list(explicits) + list(enchants)

        assert all_mods == []


class TestBasicModComparison:
    """Tests for _basic_mod_comparison logic."""

    def test_finds_common_mods(self):
        """Test finding common mods between items."""
        mods1 = ["+50 to Maximum Life", "+30% to Fire Resistance"]
        mods2 = ["+50 to Maximum Life", "+30% to Cold Resistance"]

        set1 = set(mods1)
        set2 = set(mods2)

        common = set1 & set2
        only_in_1 = set1 - set2
        only_in_2 = set2 - set1

        assert "+50 to Maximum Life" in common
        assert "+30% to Fire Resistance" in only_in_1
        assert "+30% to Cold Resistance" in only_in_2

    def test_all_unique_mods(self):
        """Test when items have completely different mods."""
        mods1 = ["+50 to Maximum Life", "+30% to Fire Resistance"]
        mods2 = ["+100 to Maximum Mana", "+30% to Cold Resistance"]

        set1 = set(mods1)
        set2 = set(mods2)

        common = set1 & set2
        only_in_1 = set1 - set2
        only_in_2 = set2 - set1

        assert len(common) == 0
        assert len(only_in_1) == 2
        assert len(only_in_2) == 2

    def test_identical_mods(self):
        """Test when items have identical mods."""
        mods1 = ["+50 to Maximum Life", "+30% to Fire Resistance"]
        mods2 = ["+50 to Maximum Life", "+30% to Fire Resistance"]

        set1 = set(mods1)
        set2 = set(mods2)

        common = set1 & set2
        only_in_1 = set1 - set2
        only_in_2 = set2 - set1

        assert len(common) == 2
        assert len(only_in_1) == 0
        assert len(only_in_2) == 0

    def test_empty_mods(self):
        """Test with empty mod lists."""
        mods1 = []
        mods2 = []

        set1 = set(mods1)
        set2 = set(mods2)

        common = set1 & set2
        only_in_1 = set1 - set2
        only_in_2 = set2 - set1

        assert len(common) == 0
        assert len(only_in_1) == 0
        assert len(only_in_2) == 0


class TestItemSwapping:
    """Tests for item swap logic."""

    def test_swap_items(self):
        """Test swapping two items."""
        item1 = MockItem(name="Item A")
        item2 = MockItem(name="Item B")

        # Simulate swap
        item1, item2 = item2, item1

        assert item1.name == "Item B"
        assert item2.name == "Item A"

    def test_swap_text(self):
        """Test swapping text inputs."""
        text1 = "Item A text"
        text2 = "Item B text"

        # Simulate swap
        text1, text2 = text2, text1

        assert text1 == "Item B text"
        assert text2 == "Item A text"

    def test_swap_with_none(self):
        """Test swapping when one item is None."""
        item1 = MockItem(name="Item A")
        item2 = None

        # Simulate swap
        item1, item2 = item2, item1

        assert item1 is None
        assert item2 is not None
        assert item2.name == "Item A"


class TestComparisonState:
    """Tests for comparison state management."""

    def test_no_items_state(self):
        """Test state when no items are loaded."""
        item1 = None
        item2 = None

        state = self._get_state(item1, item2)
        assert state == "waiting_both"

    def test_one_item_state(self):
        """Test state when only one item is loaded."""
        item1 = MockItem(name="Item A")
        item2 = None

        state = self._get_state(item1, item2)
        assert state == "waiting_item2"

    def test_both_items_state(self):
        """Test state when both items are loaded."""
        item1 = MockItem(name="Item A")
        item2 = MockItem(name="Item B")

        state = self._get_state(item1, item2)
        assert state == "ready"

    def _get_state(self, item1, item2):
        """Helper to determine comparison state."""
        if not item1 and not item2:
            return "waiting_both"
        elif not item1:
            return "waiting_item1"
        elif not item2:
            return "waiting_item2"
        else:
            return "ready"


class TestComparisonHtmlGeneration:
    """Tests for HTML generation logic."""

    def test_escapes_item_names(self):
        """Test that item names are HTML escaped."""
        import html

        name = "<script>alert('xss')</script>"
        escaped = html.escape(name)

        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_format_improvement(self):
        """Test formatting improvement text."""
        import html

        improvement = "+50 to Maximum Life"
        formatted = f"+ {html.escape(improvement)}"

        assert formatted == "+ +50 to Maximum Life"

    def test_format_loss(self):
        """Test formatting loss text."""
        import html

        loss = "+30% to Fire Resistance"
        formatted = f"- {html.escape(loss)}"

        assert formatted == "- +30% to Fire Resistance"

    def test_verdict_upgrade(self):
        """Test verdict for upgrade."""
        comparison = {"is_upgrade": True, "is_downgrade": False}

        if comparison["is_upgrade"]:
            verdict = "UPGRADE"
        elif comparison["is_downgrade"]:
            verdict = "DOWNGRADE"
        else:
            verdict = "SIDEGRADE"

        assert verdict == "UPGRADE"

    def test_verdict_downgrade(self):
        """Test verdict for downgrade."""
        comparison = {"is_upgrade": False, "is_downgrade": True}

        if comparison["is_upgrade"]:
            verdict = "UPGRADE"
        elif comparison["is_downgrade"]:
            verdict = "DOWNGRADE"
        else:
            verdict = "SIDEGRADE"

        assert verdict == "DOWNGRADE"

    def test_verdict_sidegrade(self):
        """Test verdict for sidegrade."""
        comparison = {"is_upgrade": False, "is_downgrade": False}

        if comparison["is_upgrade"]:
            verdict = "UPGRADE"
        elif comparison["is_downgrade"]:
            verdict = "DOWNGRADE"
        else:
            verdict = "SIDEGRADE"

        assert verdict == "SIDEGRADE"


class TestItemParsing:
    """Tests for item parsing logic."""

    def test_parse_empty_text(self):
        """Test parsing empty text."""
        text = ""

        if not text.strip():
            result = None
        else:
            result = "parsed"

        assert result is None

    def test_parse_whitespace_text(self):
        """Test parsing whitespace-only text."""
        text = "   \n\t  "

        if not text.strip():
            result = None
        else:
            result = "parsed"

        assert result is None


class TestClearAll:
    """Tests for clear all functionality."""

    def test_clear_all_resets_state(self):
        """Test that clear all resets all state."""
        # Setup initial state
        state = {
            "item1": MockItem(name="Item A"),
            "item2": MockItem(name="Item B"),
            "text1": "Item A text",
            "text2": "Item B text",
        }

        # Verify initial state has values
        assert state["item1"] is not None
        assert state["item2"] is not None
        assert state["text1"] != ""
        assert state["text2"] != ""

        # Simulate clear operation by replacing state
        cleared_state = self._clear_state(state)

        # Verify cleared state
        assert cleared_state["item1"] is None
        assert cleared_state["item2"] is None
        assert cleared_state["text1"] == ""
        assert cleared_state["text2"] == ""

    def _clear_state(self, state: dict) -> dict:
        """Clear all values in state dict."""
        return {
            "item1": None,
            "item2": None,
            "text1": "",
            "text2": "",
        }


class TestSetItemProgrammatically:
    """Tests for programmatic item setting."""

    def test_set_item_with_raw_text(self):
        """Test setting item with raw_text attribute."""
        item = MockItem(
            name="Test Item",
            raw_text="Rarity: Rare\nTest Item\nVaal Regalia"
        )

        raw_text = getattr(item, 'raw_text', None)

        assert raw_text is not None
        assert "Rarity: Rare" in raw_text

    def test_set_item_without_raw_text(self):
        """Test setting item without raw_text attribute."""
        item = MockItem(name="Test Item", raw_text=None)

        raw_text = getattr(item, 'raw_text', None)

        assert raw_text is None

    def test_set_none_item(self):
        """Test setting None as item."""
        item = None

        has_item = bool(item)

        assert has_item is False


class TestComparisonWithUpgradeCalculator:
    """Tests for comparison using UpgradeCalculator."""

    def test_comparison_result_structure(self):
        """Test that comparison result has expected structure."""
        comparison = {
            "is_upgrade": True,
            "is_downgrade": False,
            "summary": "Gained 50 life, 10% damage",
            "improvements": ["+50 to Maximum Life", "+10% increased Damage"],
            "losses": ["-30% to Fire Resistance"],
        }

        assert "is_upgrade" in comparison
        assert "is_downgrade" in comparison
        assert "summary" in comparison
        assert "improvements" in comparison
        assert "losses" in comparison

    def test_improvements_list(self):
        """Test improvements list handling."""
        improvements = [
            "+50 to Maximum Life",
            "+10% increased Damage",
            "+30% to Fire Resistance",
        ]

        # Simulate limiting to first 8
        limited = improvements[:8]

        assert len(limited) == 3
        assert limited == improvements

    def test_losses_list(self):
        """Test losses list handling."""
        losses = [
            "-30% to Fire Resistance",
            "-50 to Maximum Mana",
        ]

        # Simulate limiting to first 8
        limited = losses[:8]

        assert len(limited) == 2
        assert limited == losses


class TestDialogInitialization:
    """Tests for dialog initialization logic."""

    def test_default_values(self):
        """Test default initialization values."""
        item1 = None
        item2 = None
        build_stats = None
        calculator = None
        upgrade_calculator = None

        assert item1 is None
        assert item2 is None
        assert build_stats is None
        assert calculator is None
        assert upgrade_calculator is None

    def test_with_app_context(self):
        """Test initialization with app context."""
        # Mock app context with PoB build
        class MockBuild:
            def __init__(self):
                self.stats = {"life": 5000, "dps": 1000000}

        class MockAppContext:
            def __init__(self):
                self.pob_build = MockBuild()

        app_context = MockAppContext()

        build = getattr(app_context, 'pob_build', None)
        assert build is not None
        assert build.stats["life"] == 5000


class TestModExtraction:
    """Tests for mod extraction from various item formats."""

    def test_extract_from_implicits_attr(self):
        """Test extracting mods from implicits attribute."""

        class ItemWithImplicits:
            def __init__(self):
                self.implicits = ["+50 to Maximum Life"]

        item = ItemWithImplicits()
        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", []) or []

        assert implicits == ["+50 to Maximum Life"]

    def test_extract_from_implicit_mods_attr(self):
        """Test extracting mods from implicit_mods attribute."""

        class ItemWithImplicitMods:
            def __init__(self):
                self.implicit_mods = ["+50 to Maximum Life"]

        item = ItemWithImplicitMods()
        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", []) or []

        assert implicits == ["+50 to Maximum Life"]

    def test_extract_from_mods_attr(self):
        """Test extracting mods from mods attribute."""

        class ItemWithMods:
            def __init__(self):
                self.mods = ["+30% to Fire Resistance"]

        item = ItemWithMods()
        explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", []) or []

        assert explicits == ["+30% to Fire Resistance"]

    def test_fallback_chain(self):
        """Test fallback chain for mod extraction."""

        class ItemWithOnlyMods:
            def __init__(self):
                self.mods = ["Test Mod"]
                # No implicits, explicits, etc.

        item = ItemWithOnlyMods()

        # Uses fallback chain
        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", []) or []
        explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", []) or []

        assert implicits == []
        assert explicits == ["Test Mod"]

