"""
Tests for Stash Valuator.

Tests the stash valuation module structure and pricing logic.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from core.stash_valuator import (
    PriceSource,
    PricedItem,
    PricedTab,
    ValuationResult,
    StashValuator,
    get_valuator,
)
from data_sources.poe_stash_api import StashTab, StashSnapshot
from data_sources.poe_ninja_client import NinjaPrice, NinjaPriceDatabase


class TestPricedItem:
    """Tests for PricedItem dataclass."""

    def test_basic_creation(self):
        """Test creating a basic priced item."""
        item = PricedItem(
            name="Mageblood",
            type_line="Heavy Belt",
            base_type="Heavy Belt",
            item_class="unique",
        )
        assert item.name == "Mageblood"
        assert item.type_line == "Heavy Belt"

    def test_display_name_unique(self):
        """Test display name for unique items."""
        item = PricedItem(
            name="Mageblood",
            type_line="Heavy Belt",
            base_type="Heavy Belt",
            item_class="unique",
        )
        assert item.display_name == "Mageblood Heavy Belt"

    def test_display_name_currency(self):
        """Test display name for currency."""
        item = PricedItem(
            name="",
            type_line="Chaos Orb",
            base_type="Chaos Orb",
            item_class="currency",
        )
        assert item.display_name == "Chaos Orb"

    def test_display_price_high(self):
        """Test display price for high value."""
        item = PricedItem(
            name="Test",
            type_line="Test",
            base_type="Test",
            item_class="unique",
            total_price=500.0,
        )
        assert item.display_price == "500c"

    def test_display_price_medium(self):
        """Test display price for medium value."""
        item = PricedItem(
            name="Test",
            type_line="Test",
            base_type="Test",
            item_class="unique",
            total_price=15.5,
        )
        assert item.display_price == "15.5c"

    def test_display_price_low(self):
        """Test display price for low value."""
        item = PricedItem(
            name="Test",
            type_line="Test",
            base_type="Test",
            item_class="currency",
            total_price=0.05,
        )
        assert item.display_price == "0.05c"

    def test_display_price_unknown(self):
        """Test display price for unpriced item."""
        item = PricedItem(
            name="Test",
            type_line="Test",
            base_type="Test",
            item_class="rare",
            total_price=0.0,
        )
        assert item.display_price == "?"

    def test_is_valuable_true(self):
        """Test is_valuable returns true for valuable items."""
        item = PricedItem(
            name="Test",
            type_line="Test",
            base_type="Test",
            item_class="unique",
            total_price=10.0,
        )
        assert item.is_valuable is True

    def test_is_valuable_false(self):
        """Test is_valuable returns false for cheap items."""
        item = PricedItem(
            name="Test",
            type_line="Test",
            base_type="Test",
            item_class="currency",
            total_price=0.5,
        )
        assert item.is_valuable is False

    def test_stack_size_total_price(self):
        """Test total price with stack size."""
        item = PricedItem(
            name="",
            type_line="Chaos Orb",
            base_type="Chaos Orb",
            item_class="currency",
            stack_size=100,
            unit_price=1.0,
            total_price=100.0,
        )
        assert item.total_price == 100.0


class TestPricedTab:
    """Tests for PricedTab dataclass."""

    def test_basic_creation(self):
        """Test creating a basic priced tab."""
        tab = PricedTab(
            id="abc123",
            name="Currency",
            index=0,
            tab_type="CurrencyStash",
        )
        assert tab.name == "Currency"
        assert tab.total_value == 0.0
        assert len(tab.items) == 0

    def test_display_value_high(self):
        """Test display value for high value tabs."""
        tab = PricedTab(
            id="abc",
            name="Test",
            index=0,
            tab_type="NormalStash",
            total_value=5000.0,
        )
        assert "5.0k" in tab.display_value

    def test_display_value_medium(self):
        """Test display value for medium value tabs."""
        tab = PricedTab(
            id="abc",
            name="Test",
            index=0,
            tab_type="NormalStash",
            total_value=500.0,
        )
        assert tab.display_value == "500c"

    def test_display_value_low(self):
        """Test display value for low value tabs."""
        tab = PricedTab(
            id="abc",
            name="Test",
            index=0,
            tab_type="NormalStash",
            total_value=5.5,
        )
        assert tab.display_value == "5.5c"


class TestValuationResult:
    """Tests for ValuationResult dataclass."""

    def test_basic_creation(self):
        """Test creating a basic result."""
        result = ValuationResult(
            league="Phrecia",
            account_name="TestAccount",
        )
        assert result.league == "Phrecia"
        assert result.total_value == 0.0

    def test_display_total_high(self):
        """Test display total for high value."""
        result = ValuationResult(
            league="Phrecia",
            account_name="TestAccount",
            total_value=50000.0,
        )
        assert "50.0k" in result.display_total

    def test_display_total_low(self):
        """Test display total for low value."""
        result = ValuationResult(
            league="Phrecia",
            account_name="TestAccount",
            total_value=500.0,
        )
        assert result.display_total == "500c"


class TestStashValuator:
    """Tests for StashValuator class."""

    def test_valuator_creation(self):
        """Test valuator can be created."""
        valuator = StashValuator()
        assert valuator is not None
        assert valuator.price_db is None

    def test_classify_currency(self):
        """Test classifying currency items."""
        valuator = StashValuator()
        item = {"frameType": 5, "typeLine": "Chaos Orb", "icon": ""}
        assert valuator._classify_item(item) == "currency"

    def test_classify_divination_card(self):
        """Test classifying divination cards."""
        valuator = StashValuator()
        item = {"frameType": 6, "typeLine": "The Doctor", "icon": ""}
        assert valuator._classify_item(item) == "divination card"

    def test_classify_unique(self):
        """Test classifying unique items."""
        valuator = StashValuator()
        item = {"frameType": 3, "typeLine": "Leather Belt", "name": "Headhunter", "icon": ""}
        assert valuator._classify_item(item) == "unique"

    def test_classify_gem(self):
        """Test classifying gem items."""
        valuator = StashValuator()
        item = {"frameType": 4, "typeLine": "Awakened Multistrike Support", "icon": ""}
        assert valuator._classify_item(item) == "gem"

    def test_classify_rare(self):
        """Test classifying rare items."""
        valuator = StashValuator()
        item = {"frameType": 2, "typeLine": "Leather Belt", "icon": ""}
        assert valuator._classify_item(item) == "rare"

    def test_classify_magic(self):
        """Test classifying magic items."""
        valuator = StashValuator()
        item = {"frameType": 1, "typeLine": "Leather Belt", "icon": ""}
        assert valuator._classify_item(item) == "magic"

    def test_classify_scarab(self):
        """Test classifying scarab items."""
        valuator = StashValuator()
        item = {"frameType": 0, "typeLine": "Gilded Breach Scarab", "icon": ""}
        assert valuator._classify_item(item) == "scarab"

    def test_classify_essence(self):
        """Test classifying essence items."""
        valuator = StashValuator()
        item = {"frameType": 0, "typeLine": "Deafening Essence of Woe", "icon": ""}
        assert valuator._classify_item(item) == "essence"

    def test_get_item_links(self):
        """Test getting item links."""
        valuator = StashValuator()

        # 6-linked item
        item = {
            "sockets": [
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "G"},
                {"group": 0, "sColour": "G"},
                {"group": 0, "sColour": "B"},
                {"group": 0, "sColour": "B"},
            ]
        }
        assert valuator._get_item_links(item) == 6

        # 4-linked item
        item = {
            "sockets": [
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "G"},
                {"group": 0, "sColour": "G"},
                {"group": 1, "sColour": "B"},
                {"group": 1, "sColour": "B"},
            ]
        }
        assert valuator._get_item_links(item) == 4

        # No sockets
        assert valuator._get_item_links({}) == 0

    def test_price_item_currency(self):
        """Test pricing a currency item."""
        valuator = StashValuator()

        # Set up mock price database
        valuator.price_db = NinjaPriceDatabase(league="Phrecia")
        valuator.price_db.currency["divine orb"] = NinjaPrice(name="Divine Orb", chaos_value=150.0)
        valuator._current_league = "Phrecia"

        item = {
            "name": "",
            "typeLine": "Divine Orb",
            "frameType": 5,
            "stackSize": 5,
            "icon": "",
        }

        tab = StashTab(id="t1", name="Currency", index=0, type="CurrencyStash")
        priced = valuator._price_item(item, tab)

        assert priced.type_line == "Divine Orb"
        assert priced.unit_price == 150.0
        assert priced.total_price == 750.0  # 5 * 150
        assert priced.price_source == PriceSource.POE_NINJA

    def test_price_item_unique(self):
        """Test pricing a unique item."""
        valuator = StashValuator()

        # Set up mock price database
        valuator.price_db = NinjaPriceDatabase(league="Phrecia")
        valuator.price_db.uniques["headhunter"] = NinjaPrice(name="Headhunter", chaos_value=8000.0)
        valuator._current_league = "Phrecia"

        item = {
            "name": "<<set:MS>><<set:M>><<set:S>>Headhunter",
            "typeLine": "Leather Belt",
            "baseType": "Leather Belt",
            "frameType": 3,
            "icon": "",
        }

        tab = StashTab(id="t1", name="Uniques", index=0, type="NormalStash")
        priced = valuator._price_item(item, tab)

        assert priced.name == "Headhunter"  # Name cleaned
        assert priced.rarity == "Unique"
        assert priced.unit_price == 8000.0

    def test_price_item_unknown(self):
        """Test pricing an unknown item."""
        valuator = StashValuator()
        valuator.price_db = NinjaPriceDatabase(league="Phrecia")
        valuator._current_league = "Phrecia"

        item = {
            "name": "Random Rare",
            "typeLine": "Leather Belt",
            "frameType": 2,
            "icon": "",
        }

        tab = StashTab(id="t1", name="Dump", index=0, type="NormalStash")
        priced = valuator._price_item(item, tab)

        assert priced.price_source == PriceSource.UNKNOWN
        assert priced.total_price == 0.0

    def test_valuate_tab(self):
        """Test valuating a full tab."""
        valuator = StashValuator()
        valuator.price_db = NinjaPriceDatabase(league="Phrecia")
        valuator.price_db.currency["chaos orb"] = NinjaPrice(name="Chaos Orb", chaos_value=1.0)
        valuator._current_league = "Phrecia"

        tab = StashTab(
            id="t1",
            name="Currency",
            index=0,
            type="CurrencyStash",
            items=[
                {"name": "", "typeLine": "Chaos Orb", "frameType": 5, "stackSize": 100, "icon": ""},
                {"name": "", "typeLine": "Chaos Orb", "frameType": 5, "stackSize": 50, "icon": ""},
            ]
        )

        priced_tab = valuator.valuate_tab(tab)

        assert priced_tab.name == "Currency"
        assert len(priced_tab.items) == 2
        assert priced_tab.total_value == 150.0  # 100 + 50
        assert priced_tab.valuable_count == 2

    def test_valuate_snapshot(self):
        """Test valuating a full snapshot."""
        valuator = StashValuator()
        valuator.price_db = NinjaPriceDatabase(league="Phrecia")
        valuator.price_db.currency["chaos orb"] = NinjaPrice(name="Chaos Orb", chaos_value=1.0)
        valuator._current_league = "Phrecia"

        snapshot = StashSnapshot(
            account_name="TestAccount",
            league="Phrecia",
            tabs=[
                StashTab(
                    id="t1", name="Tab 1", index=0, type="NormalStash",
                    items=[{"name": "", "typeLine": "Chaos Orb", "frameType": 5, "stackSize": 100, "icon": ""}]
                ),
                StashTab(
                    id="t2", name="Tab 2", index=1, type="NormalStash",
                    items=[{"name": "", "typeLine": "Chaos Orb", "frameType": 5, "stackSize": 50, "icon": ""}]
                ),
            ],
            total_items=2,
        )

        result = valuator.valuate_snapshot(snapshot)

        assert result.account_name == "TestAccount"
        assert result.league == "Phrecia"
        assert len(result.tabs) == 2
        assert result.total_value == 150.0
        assert result.total_items == 2


class TestGetValuator:
    """Tests for singleton valuator."""

    def test_returns_singleton(self):
        """Test that get_valuator returns same instance."""
        valuator1 = get_valuator()
        valuator2 = get_valuator()
        assert valuator1 is valuator2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
