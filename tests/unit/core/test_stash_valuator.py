"""Tests for core/stash_valuator.py - Stash Valuation Module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, field
from typing import List, Dict, Any

from core.stash_valuator import (
    PriceSource,
    PricedItem,
    PricedTab,
    ValuationResult,
    StashValuator,
    get_valuator,
    valuate_stash,
)


# ============================================================================
# PriceSource Enum Tests
# ============================================================================

class TestPriceSource:
    """Tests for PriceSource enum."""

    def test_poe_ninja_value(self):
        """POE_NINJA has correct value."""
        assert PriceSource.POE_NINJA.value == "poe.ninja"

    def test_poe_prices_value(self):
        """POE_PRICES has correct value."""
        assert PriceSource.POE_PRICES.value == "poeprices.info"

    def test_rare_evaluated_value(self):
        """RARE_EVALUATED has correct value."""
        assert PriceSource.RARE_EVALUATED.value == "rare_eval"

    def test_manual_value(self):
        """MANUAL has correct value."""
        assert PriceSource.MANUAL.value == "manual"

    def test_unknown_value(self):
        """UNKNOWN has correct value."""
        assert PriceSource.UNKNOWN.value == "unknown"


# ============================================================================
# PricedItem Dataclass Tests
# ============================================================================

class TestPricedItem:
    """Tests for PricedItem dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        item = PricedItem(
            name="Test",
            type_line="Type",
            base_type="Base",
            item_class="normal"
        )
        assert item.stack_size == 1
        assert item.ilvl == 0
        assert item.rarity == "Normal"
        assert item.identified is True
        assert item.corrupted is False
        assert item.links == 0
        assert item.unit_price == 0.0
        assert item.total_price == 0.0
        assert item.price_source == PriceSource.UNKNOWN

    def test_display_name_unique(self):
        """Display name combines name and type_line for uniques."""
        item = PricedItem(
            name="Headhunter",
            type_line="Leather Belt",
            base_type="Leather Belt",
            item_class="unique"
        )
        assert item.display_name == "Headhunter Leather Belt"

    def test_display_name_no_name(self):
        """Display name falls back to type_line."""
        item = PricedItem(
            name="",
            type_line="Divine Orb",
            base_type="Divine Orb",
            item_class="currency"
        )
        assert item.display_name == "Divine Orb"

    def test_display_name_same_name_type(self):
        """Display name shows only one when name equals type_line."""
        item = PricedItem(
            name="Divine Orb",
            type_line="Divine Orb",
            base_type="Divine Orb",
            item_class="currency"
        )
        assert item.display_name == "Divine Orb"

    def test_display_price_high_value(self):
        """Display price formats high values without decimals."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="test", total_price=150.75
        )
        assert item.display_price == "151c"

    def test_display_price_medium_value(self):
        """Display price formats medium values with one decimal."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="test", total_price=15.5
        )
        assert item.display_price == "15.5c"

    def test_display_price_low_value(self):
        """Display price formats low values with two decimals."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="test", total_price=0.25
        )
        assert item.display_price == "0.25c"

    def test_display_price_zero(self):
        """Display price shows ? for zero price."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="test", total_price=0.0
        )
        assert item.display_price == "?"

    def test_is_valuable_true(self):
        """Item is valuable when price >= 1."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="test", total_price=1.0
        )
        assert item.is_valuable is True

    def test_is_valuable_false(self):
        """Item is not valuable when price < 1."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="test", total_price=0.5
        )
        assert item.is_valuable is False

    def test_eval_fields_default(self):
        """Evaluation fields have correct defaults."""
        item = PricedItem(
            name="Test",
            type_line="Type",
            base_type="Base",
            item_class="rare"
        )
        assert item.eval_score == 0
        assert item.eval_tier == ""
        assert item.eval_summary == ""

    def test_display_price_evaluated_tier(self):
        """Display price shows tier for evaluated items without price."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="rare", total_price=0.0,
            price_source=PriceSource.RARE_EVALUATED,
            eval_tier="excellent"
        )
        assert item.display_price == "[excellent]"

    def test_display_price_evaluated_no_tier(self):
        """Display price shows ? for evaluated items without tier."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="rare", total_price=0.0,
            price_source=PriceSource.RARE_EVALUATED,
            eval_tier=""
        )
        assert item.display_price == "?"

    def test_is_valuable_evaluated_excellent(self):
        """Evaluated item with excellent tier is valuable."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="rare", total_price=0.0,
            price_source=PriceSource.RARE_EVALUATED,
            eval_tier="excellent"
        )
        assert item.is_valuable is True

    def test_is_valuable_evaluated_good(self):
        """Evaluated item with good tier is valuable."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="rare", total_price=0.0,
            price_source=PriceSource.RARE_EVALUATED,
            eval_tier="good"
        )
        assert item.is_valuable is True

    def test_is_valuable_evaluated_decent(self):
        """Evaluated item with decent tier is not valuable."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="rare", total_price=0.0,
            price_source=PriceSource.RARE_EVALUATED,
            eval_tier="decent"
        )
        assert item.is_valuable is False

    def test_is_valuable_evaluated_low(self):
        """Evaluated item with low tier is not valuable."""
        item = PricedItem(
            name="", type_line="Test", base_type="Test",
            item_class="rare", total_price=0.0,
            price_source=PriceSource.RARE_EVALUATED,
            eval_tier="low"
        )
        assert item.is_valuable is False


# ============================================================================
# PricedTab Dataclass Tests
# ============================================================================

class TestPricedTab:
    """Tests for PricedTab dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        tab = PricedTab(
            id="tab-1",
            name="Currency",
            index=0,
            tab_type="CurrencyStash"
        )
        assert tab.items == []
        assert tab.total_value == 0.0
        assert tab.valuable_count == 0

    def test_display_value_thousands(self):
        """Display value formats thousands correctly."""
        tab = PricedTab(
            id="tab-1", name="Test", index=0,
            tab_type="NormalStash", total_value=1500.0
        )
        assert tab.display_value == "1.5k c"

    def test_display_value_hundreds(self):
        """Display value formats hundreds correctly."""
        tab = PricedTab(
            id="tab-1", name="Test", index=0,
            tab_type="NormalStash", total_value=250.0
        )
        assert tab.display_value == "250c"

    def test_display_value_tens(self):
        """Display value formats tens correctly."""
        tab = PricedTab(
            id="tab-1", name="Test", index=0,
            tab_type="NormalStash", total_value=25.5
        )
        assert tab.display_value == "25.5c"

    def test_display_value_low(self):
        """Display value formats low values correctly."""
        tab = PricedTab(
            id="tab-1", name="Test", index=0,
            tab_type="NormalStash", total_value=0.50
        )
        assert tab.display_value == "0.50c"


# ============================================================================
# ValuationResult Dataclass Tests
# ============================================================================

class TestValuationResult:
    """Tests for ValuationResult dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        result = ValuationResult(
            league="Test League",
            account_name="TestAccount"
        )
        assert result.tabs == []
        assert result.total_value == 0.0
        assert result.total_items == 0
        assert result.priced_items == 0
        assert result.unpriced_items == 0
        assert result.errors == []

    def test_display_total_thousands(self):
        """Display total formats thousands correctly."""
        result = ValuationResult(
            league="Test", account_name="Test",
            total_value=5500.0
        )
        assert result.display_total == "5.5k c"

    def test_display_total_hundreds(self):
        """Display total formats hundreds correctly."""
        result = ValuationResult(
            league="Test", account_name="Test",
            total_value=500.0
        )
        assert result.display_total == "500c"


# ============================================================================
# StashValuator Tests
# ============================================================================

class TestStashValuator:
    """Tests for StashValuator class."""

    @pytest.fixture
    def mock_ninja_client(self):
        """Create mock ninja client."""
        with patch('core.stash_valuator.get_ninja_client') as mock:
            client = Mock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def valuator(self, mock_ninja_client):
        """Create valuator with mocked client."""
        return StashValuator()

    def test_init(self, mock_ninja_client):
        """Valuator initializes correctly."""
        valuator = StashValuator()
        assert valuator.price_db is None
        assert valuator._current_league == ""

    def test_load_prices(self, valuator, mock_ninja_client):
        """Load prices calls ninja client."""
        mock_db = Mock()
        mock_ninja_client.build_price_database.return_value = mock_db

        valuator.load_prices("TestLeague")

        mock_ninja_client.build_price_database.assert_called_once_with(
            "TestLeague", progress_callback=None
        )
        assert valuator.price_db == mock_db
        assert valuator._current_league == "TestLeague"

    def test_load_prices_cached(self, valuator, mock_ninja_client):
        """Load prices uses cache for same league."""
        mock_db = Mock()
        mock_ninja_client.build_price_database.return_value = mock_db

        valuator.load_prices("TestLeague")
        valuator.load_prices("TestLeague")  # Second call should use cache

        # Should only build database once
        assert mock_ninja_client.build_price_database.call_count == 1

    def test_load_prices_different_league(self, valuator, mock_ninja_client):
        """Load prices rebuilds for different league."""
        mock_db = Mock()
        mock_ninja_client.build_price_database.return_value = mock_db

        valuator.load_prices("League1")
        valuator.load_prices("League2")

        assert mock_ninja_client.build_price_database.call_count == 2

    def test_classify_item_currency(self, valuator):
        """Classify currency items correctly."""
        item = {"frameType": 5, "typeLine": "Divine Orb"}
        assert valuator._classify_item(item) == "currency"

    def test_classify_item_divination(self, valuator):
        """Classify divination cards correctly."""
        item = {"frameType": 6, "typeLine": "The Doctor"}
        assert valuator._classify_item(item) == "divination card"

    def test_classify_item_unique(self, valuator):
        """Classify unique items correctly."""
        item = {"frameType": 3, "name": "Headhunter", "typeLine": "Leather Belt"}
        assert valuator._classify_item(item) == "unique"

    def test_classify_item_gem(self, valuator):
        """Classify gem items correctly."""
        item = {"frameType": 4, "typeLine": "Vaal Grace"}
        assert valuator._classify_item(item) == "gem"

    def test_classify_item_scarab(self, valuator):
        """Classify scarab items correctly."""
        item = {"frameType": 0, "typeLine": "Winged Ambush Scarab"}
        assert valuator._classify_item(item) == "scarab"

    def test_classify_item_essence(self, valuator):
        """Classify essence items - currency frame type takes priority."""
        # Note: frameType 5 (currency) is checked first in the implementation
        item = {"frameType": 5, "typeLine": "Essence of Greed"}
        assert valuator._classify_item(item) == "currency"

    def test_classify_item_deafening_essence(self, valuator):
        """Classify deafening essence items - currency frame type takes priority."""
        item = {"frameType": 5, "typeLine": "Deafening Essence of Greed"}
        assert valuator._classify_item(item) == "currency"

    def test_classify_item_oil(self, valuator):
        """Classify oil items - currency frame type takes priority."""
        item = {"frameType": 5, "typeLine": "Golden Oil"}
        assert valuator._classify_item(item) == "currency"

    def test_classify_item_essence_by_name(self, valuator):
        """Essence in type_line with non-currency frame falls back to essence."""
        item = {"frameType": 0, "typeLine": "Essence of Greed"}
        assert valuator._classify_item(item) == "essence"

    def test_classify_item_oil_by_name(self, valuator):
        """Oil in type_line with non-currency frame falls back to oil."""
        item = {"frameType": 0, "typeLine": "Golden Oil"}
        assert valuator._classify_item(item) == "oil"

    def test_classify_item_oiled_not_oil(self, valuator):
        """Oiled items are not classified as oil."""
        item = {"frameType": 2, "typeLine": "Oiled Amulet"}
        assert valuator._classify_item(item) != "oil"

    def test_classify_item_fossil(self, valuator):
        """Classify fossil items - currency frame type takes priority."""
        item = {"frameType": 5, "typeLine": "Pristine Fossil"}
        assert valuator._classify_item(item) == "currency"

    def test_classify_item_fossil_by_name(self, valuator):
        """Fossil in type_line with non-currency frame falls back to fossil."""
        item = {"frameType": 0, "typeLine": "Pristine Fossil"}
        assert valuator._classify_item(item) == "fossil"

    def test_classify_item_resonator(self, valuator):
        """Classify resonator items - currency frame type takes priority."""
        item = {"frameType": 5, "typeLine": "Primitive Chaotic Resonator"}
        assert valuator._classify_item(item) == "currency"

    def test_classify_item_resonator_by_name(self, valuator):
        """Resonator in type_line with non-currency frame falls back to resonator."""
        item = {"frameType": 0, "typeLine": "Primitive Chaotic Resonator"}
        assert valuator._classify_item(item) == "resonator"

    def test_classify_item_fragment(self, valuator):
        """Classify fragment items correctly."""
        item = {"frameType": 0, "typeLine": "Fragment of the Phoenix"}
        assert valuator._classify_item(item) == "fragment"

    def test_classify_item_splinter(self, valuator):
        """Classify splinter items correctly."""
        item = {"frameType": 0, "typeLine": "Splinter of Xoph"}
        assert valuator._classify_item(item) == "fragment"

    def test_classify_item_rare(self, valuator):
        """Classify rare items correctly."""
        item = {"frameType": 2, "typeLine": "Cobalt Jewel"}
        assert valuator._classify_item(item) == "rare"

    def test_classify_item_magic(self, valuator):
        """Classify magic items correctly."""
        item = {"frameType": 1, "typeLine": "Augmented Cobalt Jewel"}
        assert valuator._classify_item(item) == "magic"

    def test_classify_item_normal(self, valuator):
        """Classify normal items correctly."""
        item = {"frameType": 0, "typeLine": "Simple Robe"}
        assert valuator._classify_item(item) == "normal"

    def test_classify_item_map_by_property(self, valuator):
        """Classify map items by Map Tier property."""
        item = {
            "frameType": 0,
            "typeLine": "Strand Map",
            "icon": "maps/strand",
            "properties": [{"name": "Map Tier", "values": [["16", 0]]}]
        }
        assert valuator._classify_item(item) == "map"

    def test_get_item_links_no_sockets(self, valuator):
        """Get links returns 0 for no sockets."""
        item = {"sockets": []}
        assert valuator._get_item_links(item) == 0

    def test_get_item_links_single_group(self, valuator):
        """Get links counts single group correctly."""
        item = {
            "sockets": [
                {"group": 0, "attr": "S"},
                {"group": 0, "attr": "S"},
                {"group": 0, "attr": "D"},
            ]
        }
        assert valuator._get_item_links(item) == 3

    def test_get_item_links_multiple_groups(self, valuator):
        """Get links returns max group size."""
        item = {
            "sockets": [
                {"group": 0, "attr": "S"},
                {"group": 0, "attr": "S"},
                {"group": 1, "attr": "D"},
                {"group": 1, "attr": "D"},
                {"group": 1, "attr": "D"},
                {"group": 1, "attr": "D"},
            ]
        }
        assert valuator._get_item_links(item) == 4

    def test_get_item_links_six_link(self, valuator):
        """Get links handles 6-link correctly."""
        item = {
            "sockets": [
                {"group": 0, "attr": "S"},
                {"group": 0, "attr": "S"},
                {"group": 0, "attr": "D"},
                {"group": 0, "attr": "D"},
                {"group": 0, "attr": "I"},
                {"group": 0, "attr": "I"},
            ]
        }
        assert valuator._get_item_links(item) == 6

    def test_price_item_currency(self, valuator, mock_ninja_client):
        """Price currency items correctly."""
        # Setup mock price database
        mock_price = Mock()
        mock_price.chaos_value = 150.0
        mock_db = Mock()
        mock_db.get_price.return_value = mock_price
        valuator.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Currency"
        mock_tab.index = 0

        item = {
            "frameType": 5,
            "typeLine": "Divine Orb",
            "stackSize": 5,
            "icon": "divine.png"
        }

        priced = valuator._price_item(item, mock_tab)

        assert priced.type_line == "Divine Orb"
        assert priced.stack_size == 5
        assert priced.unit_price == 150.0
        assert priced.total_price == 750.0  # 5 * 150
        assert priced.price_source == PriceSource.POE_NINJA
        assert priced.rarity == "Currency"

    def test_price_item_unique(self, valuator, mock_ninja_client):
        """Price unique items correctly."""
        mock_price = Mock()
        mock_price.chaos_value = 10000.0
        mock_db = Mock()
        mock_db.get_price.return_value = mock_price
        valuator.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Uniques"
        mock_tab.index = 1

        item = {
            "frameType": 3,
            "name": "<<set:MS>><<set:M>><<set:S>>Headhunter",
            "typeLine": "Leather Belt",
            "baseType": "Leather Belt",
            "identified": True,
            "corrupted": False,
            "ilvl": 85
        }

        priced = valuator._price_item(item, mock_tab)

        assert priced.name == "Headhunter"  # Prefix stripped
        assert priced.type_line == "Leather Belt"
        assert priced.rarity == "Unique"
        assert priced.total_price == 10000.0

    def test_price_item_no_price_db(self, valuator, mock_ninja_client):
        """Handle items when no price database loaded."""
        valuator.price_db = None

        mock_tab = Mock()
        mock_tab.name = "Test"
        mock_tab.index = 0

        item = {
            "frameType": 5,
            "typeLine": "Divine Orb",
        }

        priced = valuator._price_item(item, mock_tab)

        assert priced.unit_price == 0.0
        assert priced.price_source == PriceSource.UNKNOWN

    def test_price_item_not_found(self, mock_ninja_client):
        """Handle items not found in price database (without rare evaluation)."""
        # Use valuator with evaluation disabled to test original behavior
        valuator = StashValuator(evaluate_rares=False)
        mock_db = Mock()
        mock_db.get_price.return_value = None
        valuator.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Test"
        mock_tab.index = 0

        item = {
            "frameType": 2,
            "typeLine": "Unknown Rare",
        }

        priced = valuator._price_item(item, mock_tab)

        assert priced.unit_price == 0.0
        assert priced.price_source == PriceSource.UNKNOWN

    def test_price_item_socket_string(self, valuator, mock_ninja_client):
        """Build socket string correctly."""
        valuator.price_db = None

        mock_tab = Mock()
        mock_tab.name = "Test"
        mock_tab.index = 0

        item = {
            "frameType": 2,
            "typeLine": "Body Armour",
            "sockets": [
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "G"},
                {"group": 0, "sColour": "B"},
                {"group": 1, "sColour": "W"},
                {"group": 1, "sColour": "W"},
            ]
        }

        priced = valuator._price_item(item, mock_tab)

        assert priced.sockets == "RGB-WW"
        assert priced.links == 3

    def test_valuate_tab(self, valuator, mock_ninja_client):
        """Valuate a tab with multiple items."""
        # Setup price database
        mock_price = Mock()
        mock_price.chaos_value = 10.0
        mock_db = Mock()
        mock_db.get_price.return_value = mock_price
        valuator.price_db = mock_db

        mock_tab = Mock()
        mock_tab.id = "tab-123"
        mock_tab.name = "Currency"
        mock_tab.index = 0
        mock_tab.type = "CurrencyStash"
        mock_tab.items = [
            {"frameType": 5, "typeLine": "Chaos Orb", "stackSize": 100},
            {"frameType": 5, "typeLine": "Exalted Orb", "stackSize": 5},
        ]

        priced_tab = valuator.valuate_tab(mock_tab)

        assert priced_tab.id == "tab-123"
        assert priced_tab.name == "Currency"
        assert len(priced_tab.items) == 2
        assert priced_tab.total_value == 1050.0  # (100 * 10) + (5 * 10)
        assert priced_tab.valuable_count == 2  # Both items >= 1c

    def test_valuate_tab_sorted_by_value(self, valuator, mock_ninja_client):
        """Items in valuated tab are sorted by value."""
        mock_db = Mock()

        def price_lookup(name, cls=None):
            prices = {"divine orb": 150.0, "chaos orb": 1.0}
            mock = Mock()
            mock.chaos_value = prices.get(name, 0)
            return mock if name in prices else None

        mock_db.get_price.side_effect = price_lookup
        valuator.price_db = mock_db

        mock_tab = Mock()
        mock_tab.id = "tab-1"
        mock_tab.name = "Test"
        mock_tab.index = 0
        mock_tab.type = "NormalStash"
        mock_tab.items = [
            {"frameType": 5, "typeLine": "Chaos Orb", "stackSize": 10},
            {"frameType": 5, "typeLine": "Divine Orb", "stackSize": 1},
        ]

        priced_tab = valuator.valuate_tab(mock_tab)

        # Divine should be first (150c > 10c)
        assert priced_tab.items[0].type_line == "Divine Orb"
        assert priced_tab.items[1].type_line == "Chaos Orb"

    def test_valuate_snapshot(self, valuator, mock_ninja_client):
        """Valuate a complete stash snapshot."""
        mock_price = Mock()
        mock_price.chaos_value = 100.0
        mock_db = Mock()
        mock_db.get_price.return_value = mock_price
        valuator.price_db = mock_db

        # Create mock tabs
        tab1 = Mock()
        tab1.id = "tab-1"
        tab1.name = "Currency"
        tab1.index = 0
        tab1.type = "CurrencyStash"
        tab1.items = [{"frameType": 5, "typeLine": "Divine Orb", "stackSize": 2}]
        tab1.children = []

        tab2 = Mock()
        tab2.id = "tab-2"
        tab2.name = "Maps"
        tab2.index = 1
        tab2.type = "MapStash"
        tab2.items = [{"frameType": 5, "typeLine": "Chaos Orb", "stackSize": 50}]
        tab2.children = []

        mock_snapshot = Mock()
        mock_snapshot.league = "TestLeague"
        mock_snapshot.account_name = "TestAccount"
        mock_snapshot.tabs = [tab1, tab2]

        result = valuator.valuate_snapshot(mock_snapshot)

        assert result.league == "TestLeague"
        assert result.account_name == "TestAccount"
        assert result.total_items == 2
        assert result.total_value == 5200.0  # (2 * 100) + (50 * 100)
        assert len(result.tabs) == 2

    def test_valuate_snapshot_with_children(self, valuator, mock_ninja_client):
        """Valuate snapshot includes child tabs."""
        mock_price = Mock()
        mock_price.chaos_value = 10.0
        mock_db = Mock()
        mock_db.get_price.return_value = mock_price
        valuator.price_db = mock_db

        child = Mock()
        child.id = "child-1"
        child.name = "Subfolder"
        child.index = 1
        child.type = "NormalStash"
        child.items = [{"frameType": 5, "typeLine": "Test", "stackSize": 5}]
        child.children = []

        parent = Mock()
        parent.id = "parent-1"
        parent.name = "Folder"
        parent.index = 0
        parent.type = "FolderStash"
        parent.items = []
        parent.children = [child]

        mock_snapshot = Mock()
        mock_snapshot.league = "Test"
        mock_snapshot.account_name = "Test"
        mock_snapshot.tabs = [parent]

        result = valuator.valuate_snapshot(mock_snapshot)

        # Should include both parent and child tab
        assert len(result.tabs) == 2
        assert result.total_items == 1
        assert result.total_value == 50.0

    def test_valuate_snapshot_progress_callback(self, valuator, mock_ninja_client):
        """Progress callback is called during valuation."""
        mock_db = Mock()
        mock_db.get_price.return_value = None
        valuator.price_db = mock_db

        tab1 = Mock()
        tab1.id = "1"
        tab1.name = "Tab1"
        tab1.index = 0
        tab1.type = "Normal"
        tab1.items = []
        tab1.children = []

        mock_snapshot = Mock()
        mock_snapshot.league = "Test"
        mock_snapshot.account_name = "Test"
        mock_snapshot.tabs = [tab1]

        progress_calls = []

        def progress(cur, total, name):
            progress_calls.append((cur, total, name))

        valuator.valuate_snapshot(mock_snapshot, progress_callback=progress)

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1, "Tab1")


# ============================================================================
# Rare Item Evaluation Tests
# ============================================================================

class TestRareItemEvaluation:
    """Tests for rare item evaluation integration."""

    @pytest.fixture
    def mock_ninja_client(self):
        """Create mock ninja client."""
        with patch('core.stash_valuator.get_ninja_client') as mock:
            client = Mock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def valuator_with_eval(self, mock_ninja_client):
        """Create valuator with rare evaluation enabled."""
        return StashValuator(evaluate_rares=True)

    @pytest.fixture
    def valuator_without_eval(self, mock_ninja_client):
        """Create valuator with rare evaluation disabled."""
        return StashValuator(evaluate_rares=False)

    def test_init_with_evaluate_rares_enabled(self, mock_ninja_client):
        """Valuator initializes with evaluation enabled by default."""
        valuator = StashValuator()
        assert valuator._evaluate_rares is True
        assert valuator._rare_evaluator is None  # Lazy loaded

    def test_init_with_evaluate_rares_disabled(self, mock_ninja_client):
        """Valuator can disable evaluation."""
        valuator = StashValuator(evaluate_rares=False)
        assert valuator._evaluate_rares is False

    def test_get_rare_evaluator_lazy_load(self, valuator_with_eval):
        """Rare evaluator is lazy loaded."""
        assert valuator_with_eval._rare_evaluator is None
        evaluator = valuator_with_eval._get_rare_evaluator()
        assert evaluator is not None
        assert valuator_with_eval._rare_evaluator is evaluator
        # Second call returns same instance
        assert valuator_with_eval._get_rare_evaluator() is evaluator

    def test_price_rare_item_with_evaluation(self, valuator_with_eval):
        """Unpriced rare items get evaluated."""
        mock_db = Mock()
        mock_db.get_price.return_value = None  # No price found
        valuator_with_eval.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Rares"
        mock_tab.index = 0

        # Rare item with good mods
        item = {
            "frameType": 2,  # Rare
            "typeLine": "Vaal Regalia",
            "baseType": "Vaal Regalia",
            "ilvl": 86,
            "identified": True,
            "explicitMods": [
                "+120 to maximum Life",
                "+45% to Fire Resistance",
                "+45% to Cold Resistance",
            ]
        }

        priced = valuator_with_eval._price_item(item, mock_tab)

        assert priced.price_source == PriceSource.RARE_EVALUATED
        assert priced.eval_score > 0
        assert priced.eval_tier != ""
        assert priced.eval_summary != ""

    def test_price_rare_item_disabled_evaluation(self, valuator_without_eval):
        """Rare items not evaluated when disabled."""
        mock_db = Mock()
        mock_db.get_price.return_value = None
        valuator_without_eval.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Rares"
        mock_tab.index = 0

        item = {
            "frameType": 2,
            "typeLine": "Vaal Regalia",
            "baseType": "Vaal Regalia",
            "ilvl": 86,
            "identified": True,
            "explicitMods": ["+120 to maximum Life"]
        }

        priced = valuator_without_eval._price_item(item, mock_tab)

        assert priced.price_source == PriceSource.UNKNOWN
        assert priced.eval_score == 0
        assert priced.eval_tier == ""

    def test_price_unidentified_rare_not_evaluated(self, valuator_with_eval):
        """Unidentified rare items not evaluated."""
        mock_db = Mock()
        mock_db.get_price.return_value = None
        valuator_with_eval.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Rares"
        mock_tab.index = 0

        item = {
            "frameType": 2,
            "typeLine": "Vaal Regalia",
            "identified": False,
        }

        priced = valuator_with_eval._price_item(item, mock_tab)

        assert priced.price_source == PriceSource.UNKNOWN
        assert priced.eval_score == 0

    def test_price_rare_with_ninja_price_not_evaluated(self, valuator_with_eval):
        """Rare items with ninja price are not evaluated."""
        mock_price = Mock()
        mock_price.chaos_value = 50.0
        mock_db = Mock()
        mock_db.get_price.return_value = mock_price
        valuator_with_eval.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Rares"
        mock_tab.index = 0

        item = {
            "frameType": 2,
            "typeLine": "Some Priced Rare",
            "identified": True,
        }

        priced = valuator_with_eval._price_item(item, mock_tab)

        # Has price from ninja, not evaluated
        assert priced.price_source == PriceSource.POE_NINJA
        assert priced.total_price == 50.0
        assert priced.eval_score == 0

    def test_price_unique_not_evaluated(self, valuator_with_eval):
        """Unique items without price are not evaluated."""
        mock_db = Mock()
        mock_db.get_price.return_value = None
        valuator_with_eval.price_db = mock_db

        mock_tab = Mock()
        mock_tab.name = "Uniques"
        mock_tab.index = 0

        item = {
            "frameType": 3,  # Unique
            "name": "Unknown Unique",
            "typeLine": "Leather Belt",
            "identified": True,
        }

        priced = valuator_with_eval._price_item(item, mock_tab)

        # Not evaluated - only rares
        assert priced.price_source == PriceSource.UNKNOWN
        assert priced.eval_score == 0

    def test_valuate_tab_sorting_with_evaluated_items(self, valuator_with_eval):
        """Tab sorting places priced items before evaluated items."""
        mock_db = Mock()

        def price_lookup(name, cls=None):
            # Only currency has price
            if "chaos orb" in name:
                mock = Mock()
                mock.chaos_value = 1.0
                return mock
            return None

        mock_db.get_price.side_effect = price_lookup
        valuator_with_eval.price_db = mock_db

        mock_tab = Mock()
        mock_tab.id = "tab-1"
        mock_tab.name = "Mixed"
        mock_tab.index = 0
        mock_tab.type = "NormalStash"
        mock_tab.items = [
            # Rare with no price - will be evaluated
            {
                "frameType": 2,
                "typeLine": "Hubris Circlet",
                "ilvl": 86,
                "identified": True,
                "explicitMods": [
                    "+100 to maximum Energy Shield",
                    "+40% to Fire Resistance",
                ]
            },
            # Currency with price
            {"frameType": 5, "typeLine": "Chaos Orb", "stackSize": 5},
        ]

        priced_tab = valuator_with_eval.valuate_tab(mock_tab)

        # Priced item (5c) should be first, then evaluated item
        assert priced_tab.items[0].type_line == "Chaos Orb"
        assert priced_tab.items[0].price_source == PriceSource.POE_NINJA
        assert priced_tab.items[1].type_line == "Hubris Circlet"
        assert priced_tab.items[1].price_source == PriceSource.RARE_EVALUATED

    def test_valuate_tab_counts_evaluated_valuable(self, valuator_with_eval):
        """Valuable evaluated items are counted."""
        mock_db = Mock()
        mock_db.get_price.return_value = None
        valuator_with_eval.price_db = mock_db

        # Mock the rare evaluator to return excellent tier
        mock_evaluation = Mock()
        mock_evaluation.total_score = 150
        mock_evaluation.tier = "excellent"
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = mock_evaluation
        mock_evaluator.get_summary.return_value = "Excellent rare"
        valuator_with_eval._rare_evaluator = mock_evaluator

        mock_tab = Mock()
        mock_tab.id = "tab-1"
        mock_tab.name = "Rares"
        mock_tab.index = 0
        mock_tab.type = "NormalStash"
        mock_tab.items = [
            {
                "frameType": 2,
                "typeLine": "Great Rare",
                "ilvl": 86,
                "identified": True,
                "explicitMods": ["+100 to maximum Life"]
            }
        ]

        priced_tab = valuator_with_eval.valuate_tab(mock_tab)

        # Should count as valuable (excellent tier)
        assert priced_tab.valuable_count == 1


# ============================================================================
# Module-level Function Tests
# ============================================================================

class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_valuator_singleton(self):
        """get_valuator returns singleton instance."""
        with patch('core.stash_valuator._valuator', None):
            with patch('core.stash_valuator.get_ninja_client'):
                v1 = get_valuator()
                v2 = get_valuator()
                assert v1 is v2

    @patch('core.stash_valuator.PoEStashClient')
    @patch('core.stash_valuator.get_valuator')
    def test_valuate_stash(self, mock_get_valuator, mock_stash_client):
        """valuate_stash orchestrates the full process."""
        # Setup mock valuator
        mock_valuator = Mock()
        mock_result = ValuationResult(league="Test", account_name="Test")
        mock_valuator.valuate_snapshot.return_value = mock_result
        mock_get_valuator.return_value = mock_valuator

        # Setup mock stash client
        mock_client = Mock()
        mock_snapshot = Mock()
        mock_client.fetch_all_stashes.return_value = mock_snapshot
        mock_stash_client.return_value = mock_client

        result = valuate_stash(
            poesessid="test-session",
            account_name="TestAccount",
            league="TestLeague",
            max_tabs=5
        )

        # Verify load_prices was called
        mock_valuator.load_prices.assert_called_once_with("TestLeague")

        # Verify stash client was created with correct session
        mock_stash_client.assert_called_once_with("test-session")

        # Verify fetch was called with correct params
        mock_client.fetch_all_stashes.assert_called_once()
        call_args = mock_client.fetch_all_stashes.call_args
        assert call_args[0] == ("TestAccount", "TestLeague")
        assert call_args[1]["max_tabs"] == 5

        assert result == mock_result

    @patch('core.stash_valuator.PoEStashClient')
    @patch('core.stash_valuator.get_valuator')
    def test_valuate_stash_progress(self, mock_get_valuator, mock_stash_client):
        """valuate_stash calls progress callback."""
        mock_valuator = Mock()
        mock_result = ValuationResult(league="Test", account_name="Test")
        mock_valuator.valuate_snapshot.return_value = mock_result
        mock_get_valuator.return_value = mock_valuator

        mock_client = Mock()
        mock_snapshot = Mock()
        mock_client.fetch_all_stashes.return_value = mock_snapshot
        mock_stash_client.return_value = mock_client

        progress_calls = []

        def progress(cur, total, msg):
            progress_calls.append((cur, total, msg))

        valuate_stash(
            poesessid="test",
            account_name="Test",
            league="Test",
            progress_callback=progress
        )

        # Should have at least the initial progress calls
        assert any("Loading prices" in str(c) for c in progress_calls)
        assert any("Connecting" in str(c) for c in progress_calls)


# ============================================================================
# NINJA_CATEGORIES Tests
# ============================================================================

class TestNinjaCategories:
    """Tests for NINJA_CATEGORIES mapping."""

    def test_currency_category(self):
        """Currency maps correctly."""
        assert StashValuator.NINJA_CATEGORIES["currency"] == "currency"
        assert StashValuator.NINJA_CATEGORIES["stackablecurrency"] == "currency"

    def test_divination_category(self):
        """Divination cards map correctly."""
        assert StashValuator.NINJA_CATEGORIES["divinationcards"] == "div_cards"
        assert StashValuator.NINJA_CATEGORIES["divination card"] == "div_cards"

    def test_map_category(self):
        """Maps map correctly."""
        assert StashValuator.NINJA_CATEGORIES["maps"] == "maps"
        assert StashValuator.NINJA_CATEGORIES["map"] == "maps"

    def test_unique_category(self):
        """Uniques map correctly."""
        assert StashValuator.NINJA_CATEGORIES["unique"] == "uniques"

    def test_gem_category(self):
        """Gems map correctly."""
        assert StashValuator.NINJA_CATEGORIES["gem"] == "skill_gems"

    def test_jewel_category(self):
        """Jewels map to uniques."""
        assert StashValuator.NINJA_CATEGORIES["jewel"] == "uniques"

    def test_flask_category(self):
        """Flasks map to uniques."""
        assert StashValuator.NINJA_CATEGORIES["flask"] == "uniques"

    def test_all_categories_present(self):
        """All expected categories are in the mapping."""
        expected = [
            "currency", "stackablecurrency", "divinationcards", "divination card",
            "maps", "map", "unique", "gem", "jewel", "flask", "scarab",
            "essence", "oil", "fossil", "resonator", "incubator", "fragment", "beast"
        ]
        for cat in expected:
            assert cat in StashValuator.NINJA_CATEGORIES
