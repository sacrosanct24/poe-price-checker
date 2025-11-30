"""Tests for the PoE-style item tooltip widget."""

from dataclasses import dataclass, field
from typing import List, Optional

import pytest
from PyQt6.QtCore import QPoint

from gui_qt.widgets.poe_item_tooltip import (
    PoEItemTooltip,
    ItemTooltipMixin,
    POE_TOOLTIP_COLORS,
    show_item_tooltip,
    hide_item_tooltip,
)


@dataclass
class MockParsedItem:
    """Mock ParsedItem for testing."""

    name: str = "Test Item"
    base_type: str = "Ruby Ring"
    rarity: str = "Rare"
    item_level: Optional[int] = 83
    quality: Optional[int] = None
    sockets: Optional[str] = None
    requirements: dict = field(default_factory=dict)
    implicits: List[str] = field(default_factory=list)
    explicits: List[str] = field(default_factory=list)
    enchants: List[str] = field(default_factory=list)
    is_corrupted: bool = False
    is_mirrored: bool = False
    is_fractured: bool = False
    is_synthesised: bool = False
    influences: List[str] = field(default_factory=list)
    flavour_text: Optional[str] = None


class TestPoEItemTooltip:
    """Tests for PoEItemTooltip class."""

    def test_singleton_instance(self, qtbot):
        """Test that instance() returns the same object."""
        # Reset singleton for clean test
        PoEItemTooltip._instance = None

        tooltip1 = PoEItemTooltip.instance()
        tooltip2 = PoEItemTooltip.instance()

        assert tooltip1 is tooltip2

    def test_show_for_item_basic(self, qtbot):
        """Test showing tooltip for a basic item."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(
            name="Test Ring",
            base_type="Ruby Ring",
            rarity="Rare",
            item_level=75,
        )

        tooltip.show_for_item(item, QPoint(100, 100))

        assert tooltip.isVisible()
        tooltip.hide()

    def test_show_for_item_with_mods(self, qtbot):
        """Test showing tooltip for item with mods."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(
            name="Rage Gyre",
            base_type="Ruby Ring",
            rarity="Rare",
            item_level=83,
            implicits=["+25% to Fire Resistance"],
            explicits=[
                "+58 to maximum Life",
                "+42% to Cold Resistance",
                "+35% to Lightning Resistance",
            ],
        )

        tooltip.show_for_item(item, QPoint(100, 100))

        assert tooltip.isVisible()
        content = tooltip._content.text()
        assert "Rage Gyre" in content
        assert "Ruby Ring" in content
        tooltip.hide()

    def test_show_for_item_corrupted(self, qtbot):
        """Test tooltip shows corrupted status."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(
            name="Corrupted Item",
            base_type="Gold Ring",
            rarity="Rare",
            is_corrupted=True,
        )

        tooltip.show_for_item(item, QPoint(100, 100))

        content = tooltip._content.text()
        assert "Corrupted" in content
        tooltip.hide()

    def test_show_for_item_unique_with_flavour(self, qtbot):
        """Test tooltip shows flavour text for uniques."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(
            name="Andvarius",
            base_type="Gold Ring",
            rarity="Unique",
            flavour_text="Fair and foul are near of kin.",
        )

        tooltip.show_for_item(item, QPoint(100, 100))

        content = tooltip._content.text()
        assert "Fair and foul" in content
        tooltip.hide()

    def test_show_for_none_item_hides(self, qtbot):
        """Test that showing None hides the tooltip."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        # First show an item
        item = MockParsedItem()
        tooltip.show_for_item(item, QPoint(100, 100))
        assert tooltip.isVisible()

        # Then show None
        tooltip.show_for_item(None, QPoint(100, 100))
        assert not tooltip.isVisible()

    def test_hide_after_delay(self, qtbot):
        """Test hide_after_delay method."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem()
        tooltip.show_for_item(item, QPoint(100, 100))
        assert tooltip.isVisible()

        tooltip.hide_after_delay(10)  # 10ms delay

        # Wait for timer
        qtbot.wait(50)
        assert not tooltip.isVisible()

    def test_cancel_hide(self, qtbot):
        """Test cancel_hide prevents hiding."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem()
        tooltip.show_for_item(item, QPoint(100, 100))

        tooltip.hide_after_delay(100)  # 100ms delay
        tooltip.cancel_hide()  # Cancel

        qtbot.wait(150)
        assert tooltip.isVisible()
        tooltip.hide()

    def test_tooltip_colors_defined(self):
        """Test that all required colors are defined."""
        required_colors = [
            "background",
            "border",
            "separator",
            "property_name",
            "property_value",
            "corrupted",
            "crafted",
            "mod_value",
            "mod_info",
        ]
        for color in required_colors:
            assert color in POE_TOOLTIP_COLORS


class TestItemTooltipMixin:
    """Tests for ItemTooltipMixin class."""

    def test_mixin_requires_implementation(self, qtbot):
        """Test that _get_item_at_pos must be implemented."""
        from PyQt6.QtWidgets import QWidget

        class TestWidget(QWidget, ItemTooltipMixin):
            def __init__(self):
                super().__init__()
                self._init_item_tooltip()

        widget = TestWidget()
        qtbot.addWidget(widget)

        with pytest.raises(NotImplementedError):
            widget._get_item_at_pos(QPoint(0, 0))


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_show_item_tooltip(self, qtbot):
        """Test show_item_tooltip convenience function."""
        PoEItemTooltip._instance = None

        item = MockParsedItem()
        show_item_tooltip(item, QPoint(100, 100))

        tooltip = PoEItemTooltip.instance()
        assert tooltip.isVisible()
        tooltip.hide()

    def test_hide_item_tooltip(self, qtbot):
        """Test hide_item_tooltip convenience function."""
        PoEItemTooltip._instance = None

        item = MockParsedItem()
        show_item_tooltip(item, QPoint(100, 100))

        hide_item_tooltip()

        # Wait for delayed hide
        qtbot.wait(100)
        tooltip = PoEItemTooltip.instance()
        assert not tooltip.isVisible()


class TestTooltipHTMLGeneration:
    """Tests for HTML generation in tooltip."""

    def test_header_includes_rarity_color(self, qtbot):
        """Test that header uses rarity color."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(rarity="Unique")
        tooltip.show_for_item(item, QPoint(100, 100))

        content = tooltip._content.text()
        # Check for unique color in content (orange-ish)
        assert "af6025" in content.lower() or "unique" in content.lower()
        tooltip.hide()

    def test_requirements_displayed(self, qtbot):
        """Test that requirements are displayed."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(
            requirements={"level": 60, "str": 100, "int": 50}
        )

        tooltip.show_for_item(item, QPoint(100, 100))

        content = tooltip._content.text()
        assert "Requires" in content or "Level" in content
        tooltip.hide()

    def test_influences_displayed(self, qtbot):
        """Test that influences are displayed."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(
            influences=["Shaper", "Elder"]
        )

        tooltip.show_for_item(item, QPoint(100, 100))

        content = tooltip._content.text()
        assert "Shaper" in content
        assert "Elder" in content
        tooltip.hide()

    def test_quality_displayed(self, qtbot):
        """Test that quality is displayed."""
        PoEItemTooltip._instance = None
        tooltip = PoEItemTooltip.instance()

        item = MockParsedItem(quality=20)

        tooltip.show_for_item(item, QPoint(100, 100))

        content = tooltip._content.text()
        assert "Quality" in content or "+20%" in content
        tooltip.hide()
