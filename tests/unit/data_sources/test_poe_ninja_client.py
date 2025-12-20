"""Tests for data_sources/poe_ninja_client.py - poe.ninja API Client."""

from unittest.mock import patch

from data_sources.poe_ninja_client import (
    NinjaPrice,
    NinjaPriceDatabase,
    PoeNinjaClient,
    get_ninja_client,
    get_ninja_price,
)


# ============================================================================
# NinjaPrice Dataclass Tests
# ============================================================================

class TestNinjaPrice:
    """Tests for NinjaPrice dataclass."""

    def test_minimal_creation(self):
        """Create with only required fields."""
        price = NinjaPrice(name="Test Item", chaos_value=10.0)

        assert price.name == "Test Item"
        assert price.chaos_value == 10.0
        assert price.divine_value == 0.0
        assert price.base_type == ""
        assert price.variant == ""
        assert price.links == 0

    def test_full_creation(self):
        """Create with all fields."""
        price = NinjaPrice(
            name="Mageblood",
            chaos_value=50000.0,
            divine_value=300.0,
            base_type="Heavy Belt",
            variant="4 Flask",
            links=0,
            item_class="UniqueAccessory",
            icon="https://example.com/icon.png",
            stack_size=1,
            details_id="mageblood",
        )

        assert price.name == "Mageblood"
        assert price.base_type == "Heavy Belt"
        assert price.variant == "4 Flask"
        assert price.divine_value == 300.0
        assert price.item_class == "UniqueAccessory"

    def test_display_price_high(self):
        """Display price for >= 100c shows no decimals."""
        price = NinjaPrice(name="Divine", chaos_value=150.0)
        assert price.display_price == "150c"

        price = NinjaPrice(name="Divine", chaos_value=100.0)
        assert price.display_price == "100c"

    def test_display_price_medium(self):
        """Display price for 1-99c shows one decimal."""
        price = NinjaPrice(name="Exalted", chaos_value=15.5)
        assert price.display_price == "15.5c"

        price = NinjaPrice(name="Exalted", chaos_value=1.0)
        assert price.display_price == "1.0c"

    def test_display_price_low(self):
        """Display price for < 1c shows two decimals."""
        price = NinjaPrice(name="Alt", chaos_value=0.05)
        assert price.display_price == "0.05c"

        price = NinjaPrice(name="Alt", chaos_value=0.99)
        assert price.display_price == "0.99c"

    def test_display_price_boundary(self):
        """Test boundary values."""
        price = NinjaPrice(name="Test", chaos_value=99.99)
        assert price.display_price == "100.0c"  # rounds up

    def test_default_stack_size(self):
        """Default stack size is 1."""
        price = NinjaPrice(name="Test", chaos_value=1.0)
        assert price.stack_size == 1


# ============================================================================
# NinjaPriceDatabase Tests
# ============================================================================

class TestNinjaPriceDatabase:
    """Tests for NinjaPriceDatabase dataclass."""

    def test_empty_database(self):
        """Empty database has empty dicts."""
        db = NinjaPriceDatabase(league="Standard")

        assert db.league == "Standard"
        assert db.currency == {}
        assert db.fragments == {}
        assert db.uniques == {}
        assert db.skill_gems == {}

    def test_get_price_from_currency(self):
        """Get price from currency database."""
        db = NinjaPriceDatabase(league="Standard")
        db.currency["divine orb"] = NinjaPrice(name="Divine Orb", chaos_value=150.0)

        price = db.get_price("divine orb")

        assert price is not None
        assert price.chaos_value == 150.0

    def test_get_price_case_insensitive(self):
        """Price lookup is case insensitive."""
        db = NinjaPriceDatabase(league="Standard")
        db.currency["divine orb"] = NinjaPrice(name="Divine Orb", chaos_value=150.0)

        assert db.get_price("Divine Orb") is not None
        assert db.get_price("DIVINE ORB") is not None
        assert db.get_price("divine orb") is not None

    def test_get_price_with_item_class_currency(self):
        """Get price with currency item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.currency["test"] = NinjaPrice(name="Test", chaos_value=10.0)
        db.uniques["test"] = NinjaPrice(name="Test", chaos_value=100.0)

        price = db.get_price("test", item_class="currency")

        assert price.chaos_value == 10.0

    def test_get_price_with_item_class_unique(self):
        """Get price with unique item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.currency["test"] = NinjaPrice(name="Test", chaos_value=10.0)
        db.uniques["test"] = NinjaPrice(name="Test", chaos_value=100.0)

        price = db.get_price("test", item_class="unique")

        assert price.chaos_value == 100.0

    def test_get_price_with_item_class_fragment(self):
        """Get price with fragment item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.fragments["maven's writ"] = NinjaPrice(name="Maven's Writ", chaos_value=50.0)

        price = db.get_price("maven's writ", item_class="fragment")

        assert price is not None
        assert price.chaos_value == 50.0

    def test_get_price_with_item_class_map(self):
        """Get price with map item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.maps["crimson temple"] = NinjaPrice(name="Crimson Temple", chaos_value=5.0)

        price = db.get_price("crimson temple", item_class="map")

        assert price is not None

    def test_get_price_with_item_class_divination_card(self):
        """Get price with divination card item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.div_cards["the doctor"] = NinjaPrice(name="The Doctor", chaos_value=1000.0)

        price = db.get_price("the doctor", item_class="divination card")

        assert price is not None
        assert price.chaos_value == 1000.0

    def test_get_price_with_item_class_skill_gem(self):
        """Get price with skill gem item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.skill_gems["enlighten"] = NinjaPrice(name="Enlighten", chaos_value=200.0)

        price = db.get_price("enlighten", item_class="skill gem")

        assert price is not None

    def test_get_price_with_item_class_scarab(self):
        """Get price with scarab item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.scarabs["gilded scarab"] = NinjaPrice(name="Gilded Scarab", chaos_value=20.0)

        price = db.get_price("gilded scarab", item_class="scarab")

        assert price is not None

    def test_get_price_with_item_class_essence(self):
        """Get price with essence item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.essences["shrieking essence"] = NinjaPrice(name="Shrieking Essence", chaos_value=5.0)

        price = db.get_price("shrieking essence", item_class="essence")

        assert price is not None

    def test_get_price_with_item_class_oil(self):
        """Get price with oil item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.oils["golden oil"] = NinjaPrice(name="Golden Oil", chaos_value=100.0)

        price = db.get_price("golden oil", item_class="oil")

        assert price is not None

    def test_get_price_with_item_class_fossil(self):
        """Get price with fossil item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.fossils["pristine fossil"] = NinjaPrice(name="Pristine Fossil", chaos_value=3.0)

        price = db.get_price("pristine fossil", item_class="fossil")

        assert price is not None

    def test_get_price_with_item_class_resonator(self):
        """Get price with resonator item class."""
        db = NinjaPriceDatabase(league="Standard")
        db.resonators["prime resonator"] = NinjaPrice(name="Prime Resonator", chaos_value=10.0)

        price = db.get_price("prime resonator", item_class="resonator")

        assert price is not None

    def test_get_price_searches_all_databases(self):
        """Without item class, searches all databases."""
        db = NinjaPriceDatabase(league="Standard")
        db.beasts["fenumal plagued arachnid"] = NinjaPrice(name="Test Beast", chaos_value=500.0)

        price = db.get_price("fenumal plagued arachnid")

        assert price is not None
        assert price.chaos_value == 500.0

    def test_get_price_not_found(self):
        """Returns None for unknown item."""
        db = NinjaPriceDatabase(league="Standard")

        price = db.get_price("Nonexistent Item")

        assert price is None

    def test_get_all_prices_merges_dicts(self):
        """get_all_prices merges all dictionaries."""
        db = NinjaPriceDatabase(league="Standard")
        db.currency["divine"] = NinjaPrice(name="Divine", chaos_value=150.0)
        db.uniques["mageblood"] = NinjaPrice(name="Mageblood", chaos_value=50000.0)
        db.div_cards["doctor"] = NinjaPrice(name="Doctor", chaos_value=1000.0)

        all_prices = db.get_all_prices()

        assert len(all_prices) == 3
        assert "divine" in all_prices
        assert "mageblood" in all_prices
        assert "doctor" in all_prices

    def test_get_all_prices_handles_duplicates(self):
        """Later dicts override earlier ones in merge."""
        db = NinjaPriceDatabase(league="Standard")
        db.currency["test"] = NinjaPrice(name="Test", chaos_value=10.0)
        db.fragments["test"] = NinjaPrice(name="Test", chaos_value=20.0)

        all_prices = db.get_all_prices()

        # Later dict wins (fragments comes after currency in the list)
        assert all_prices["test"].chaos_value == 20.0


# ============================================================================
# PoeNinjaClient Tests
# ============================================================================

class TestPoeNinjaClient:
    """Tests for PoeNinjaClient class."""

    def test_initialization_defaults(self):
        """Default initialization values."""
        client = PoeNinjaClient()

        assert client.base_url == "https://poe.ninja/api/data"

    def test_initialization_custom_rate_limit(self):
        """Custom rate limit."""
        client = PoeNinjaClient(rate_limit=1.0)

        # Rate limit is passed to base class
        assert client.base_url == "https://poe.ninja/api/data"

    def test_cache_key_generation(self):
        """Cache key format."""
        client = PoeNinjaClient()

        key = client._get_cache_key("test", {"league": "Standard", "type": "Currency"})

        assert key.startswith("poeninja:")
        assert "test" in key
        assert "Standard" in key
        assert "Currency" in key

    def test_cache_key_no_params(self):
        """Cache key without params."""
        client = PoeNinjaClient()

        key = client._get_cache_key("endpoint")

        assert key == "poeninja:endpoint:"

    def test_cache_key_sorted_params(self):
        """Params are sorted for consistent keys."""
        client = PoeNinjaClient()

        key1 = client._get_cache_key("endpoint", {"a": "1", "b": "2"})
        key2 = client._get_cache_key("endpoint", {"b": "2", "a": "1"})

        assert key1 == key2

    def test_currency_types_constant(self):
        """CURRENCY_TYPES contains expected types."""
        assert "Currency" in PoeNinjaClient.CURRENCY_TYPES
        assert "Fragment" in PoeNinjaClient.CURRENCY_TYPES

    def test_item_types_constant(self):
        """ITEM_TYPES contains expected types."""
        assert "UniqueWeapon" in PoeNinjaClient.ITEM_TYPES
        assert "UniqueArmour" in PoeNinjaClient.ITEM_TYPES
        assert "DivinationCard" in PoeNinjaClient.ITEM_TYPES
        assert "SkillGem" in PoeNinjaClient.ITEM_TYPES
        assert "Map" in PoeNinjaClient.ITEM_TYPES
        assert "Scarab" in PoeNinjaClient.ITEM_TYPES

    @patch.object(PoeNinjaClient, 'get')
    def test_get_currency_prices(self, mock_get):
        """get_currency_prices parses response correctly."""
        mock_get.return_value = {
            "lines": [
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 150.0, "icon": "url", "detailsId": "divine"},
                {"currencyTypeName": "Exalted Orb", "chaosEquivalent": 15.0, "icon": "url", "detailsId": "exalted"},
            ]
        }

        client = PoeNinjaClient()
        prices = client.get_currency_prices("Standard", "Currency")

        assert len(prices) == 2
        assert prices[0].name == "Divine Orb"
        assert prices[0].chaos_value == 150.0
        assert prices[0].item_class == "currency"
        assert prices[1].name == "Exalted Orb"

    @patch.object(PoeNinjaClient, 'get')
    def test_get_currency_prices_fragment(self, mock_get):
        """get_currency_prices for fragments."""
        mock_get.return_value = {
            "lines": [
                {"currencyTypeName": "Maven's Writ", "chaosEquivalent": 50.0, "icon": "url", "detailsId": "maven"},
            ]
        }

        client = PoeNinjaClient()
        prices = client.get_currency_prices("Standard", "Fragment")

        assert len(prices) == 1
        assert prices[0].item_class == "fragment"

    @patch.object(PoeNinjaClient, 'get')
    def test_get_currency_prices_handles_error(self, mock_get):
        """get_currency_prices returns empty list on error."""
        mock_get.side_effect = Exception("API error")

        client = PoeNinjaClient()
        prices = client.get_currency_prices("Standard")

        assert prices == []

    @patch.object(PoeNinjaClient, 'get')
    def test_get_currency_prices_handles_missing_lines(self, mock_get):
        """get_currency_prices handles missing 'lines' key."""
        mock_get.return_value = {}

        client = PoeNinjaClient()
        prices = client.get_currency_prices("Standard")

        assert prices == []

    @patch.object(PoeNinjaClient, 'get')
    def test_get_item_prices(self, mock_get):
        """get_item_prices parses response correctly."""
        mock_get.return_value = {
            "lines": [
                {
                    "name": "Mageblood",
                    "chaosValue": 50000.0,
                    "divineValue": 300.0,
                    "baseType": "Heavy Belt",
                    "variant": "4 Flask",
                    "links": 0,
                    "icon": "url",
                    "detailsId": "mageblood",
                }
            ]
        }

        client = PoeNinjaClient()
        prices = client.get_item_prices("Standard", "UniqueAccessory")

        assert len(prices) == 1
        assert prices[0].name == "Mageblood"
        assert prices[0].chaos_value == 50000.0
        assert prices[0].divine_value == 300.0
        assert prices[0].base_type == "Heavy Belt"
        assert prices[0].variant == "4 Flask"

    @patch.object(PoeNinjaClient, 'get')
    def test_get_item_prices_handles_error(self, mock_get):
        """get_item_prices returns empty list on error."""
        mock_get.side_effect = Exception("Network error")

        client = PoeNinjaClient()
        prices = client.get_item_prices("Standard", "UniqueWeapon")

        assert prices == []

    @patch.object(PoeNinjaClient, 'get')
    def test_get_divine_chaos_rate(self, mock_get):
        """get_divine_chaos_rate returns divine price."""
        mock_get.return_value = {
            "lines": [
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1.0},
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 150.0},
            ]
        }

        client = PoeNinjaClient()
        rate = client.get_divine_chaos_rate("Standard")

        assert rate == 150.0

    @patch.object(PoeNinjaClient, 'get')
    def test_get_divine_chaos_rate_fallback(self, mock_get):
        """get_divine_chaos_rate returns 1.0 if divine not found."""
        mock_get.return_value = {
            "lines": [
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1.0},
            ]
        }

        client = PoeNinjaClient()
        rate = client.get_divine_chaos_rate("Standard")

        assert rate == 1.0

    @patch.object(PoeNinjaClient, 'get_currency_prices')
    @patch.object(PoeNinjaClient, 'get_item_prices')
    def test_build_price_database(self, mock_items, mock_currency):
        """build_price_database creates database with prices."""
        mock_currency.return_value = [
            NinjaPrice(name="Divine Orb", chaos_value=150.0),
        ]
        mock_items.return_value = [
            NinjaPrice(name="Headhunter", chaos_value=8000.0, base_type="Leather Belt"),
        ]

        client = PoeNinjaClient()
        db = client.build_price_database("Standard", item_types=["UniqueAccessory"])

        assert db.league == "Standard"
        assert "divine orb" in db.currency

    @patch.object(PoeNinjaClient, 'get_currency_prices')
    @patch.object(PoeNinjaClient, 'get_item_prices')
    def test_build_price_database_progress_callback(self, mock_items, mock_currency):
        """build_price_database calls progress callback."""
        mock_currency.return_value = []
        mock_items.return_value = []

        calls = []

        def progress(cur, total, name):
            calls.append((cur, total, name))

        client = PoeNinjaClient()
        client.build_price_database("Standard", item_types=[], progress_callback=progress)

        # Should be called for each currency type
        assert len(calls) >= 2
        assert calls[0][2] == "Currency"
        assert calls[1][2] == "Fragment"

    @patch.object(PoeNinjaClient, 'get_currency_prices')
    @patch.object(PoeNinjaClient, 'get_item_prices')
    def test_build_price_database_stores_currency_in_correct_dict(self, mock_items, mock_currency):
        """Currency goes to currency dict, fragments to fragments dict."""
        def currency_side_effect(league, ctype):
            if ctype == "Currency":
                return [NinjaPrice(name="Divine Orb", chaos_value=150.0)]
            elif ctype == "Fragment":
                return [NinjaPrice(name="Maven's Writ", chaos_value=50.0)]
            return []

        mock_currency.side_effect = currency_side_effect
        mock_items.return_value = []

        client = PoeNinjaClient()
        db = client.build_price_database("Standard", item_types=[])

        assert "divine orb" in db.currency
        assert "maven's writ" in db.fragments

    @patch.object(PoeNinjaClient, 'get_currency_prices')
    @patch.object(PoeNinjaClient, 'get_item_prices')
    def test_build_price_database_unique_key_includes_base(self, mock_items, mock_currency):
        """Unique items use name + base_type as key."""
        mock_currency.return_value = []
        mock_items.return_value = [
            NinjaPrice(name="Headhunter", chaos_value=8000.0, base_type="Leather Belt"),
        ]

        client = PoeNinjaClient()
        db = client.build_price_database("Standard", item_types=["UniqueAccessory"])

        assert "headhunter leather belt" in db.uniques

    @patch.object(PoeNinjaClient, 'get_currency_prices')
    @patch.object(PoeNinjaClient, 'get_item_prices')
    def test_build_price_database_prefers_higher_links(self, mock_items, mock_currency):
        """Database prefers items with more links."""
        mock_currency.return_value = []
        mock_items.return_value = [
            NinjaPrice(name="Carcass Jack", chaos_value=50.0, base_type="Varnished Coat", links=0),
            NinjaPrice(name="Carcass Jack", chaos_value=500.0, base_type="Varnished Coat", links=6),
        ]

        client = PoeNinjaClient()
        db = client.build_price_database("Standard", item_types=["UniqueArmour"])

        # Should keep the 6L version
        assert db.uniques["carcass jack varnished coat"].links == 6
        assert db.uniques["carcass jack varnished coat"].chaos_value == 500.0


# ============================================================================
# Singleton Function Tests
# ============================================================================

class TestSingletonFunctions:
    """Tests for singleton functions."""

    def test_get_ninja_client_returns_same_instance(self):
        """get_ninja_client returns singleton."""
        # Reset singleton for test
        import data_sources.poe_ninja_client as module
        original = module._client
        module._client = None

        try:
            client1 = get_ninja_client()
            client2 = get_ninja_client()

            assert client1 is client2
        finally:
            module._client = original

    @patch.object(PoeNinjaClient, 'build_price_database')
    def test_get_ninja_price(self, mock_build):
        """get_ninja_price looks up from database."""
        import data_sources.poe_ninja_client as module

        mock_db = NinjaPriceDatabase(league="Phrecia")
        mock_db.currency["divine orb"] = NinjaPrice(name="Divine Orb", chaos_value=150.0)
        mock_build.return_value = mock_db

        # Reset for test
        original_db = module._price_db
        module._price_db = None

        try:
            price = get_ninja_price("divine orb", "Phrecia")

            assert price is not None
            assert price.chaos_value == 150.0
        finally:
            module._price_db = original_db

    @patch.object(PoeNinjaClient, 'build_price_database')
    def test_get_ninja_price_rebuilds_for_different_league(self, mock_build):
        """get_ninja_price rebuilds database for different league."""
        import data_sources.poe_ninja_client as module

        mock_db = NinjaPriceDatabase(league="Standard")
        mock_build.return_value = mock_db

        # Set up existing DB for different league
        original_db = module._price_db
        module._price_db = NinjaPriceDatabase(league="OldLeague")

        try:
            get_ninja_price("test", "Standard")

            # Should have rebuilt because league changed
            mock_build.assert_called_once()
        finally:
            module._price_db = original_db


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_ninja_price_zero_chaos_value(self):
        """Handle zero chaos value."""
        price = NinjaPrice(name="Free Item", chaos_value=0.0)
        assert price.display_price == "0.00c"

    def test_ninja_price_negative_value(self):
        """Handle negative chaos value (shouldn't happen but test anyway)."""
        price = NinjaPrice(name="Bug", chaos_value=-5.0)
        # Will still format, just with negative
        assert "c" in price.display_price

    @patch.object(PoeNinjaClient, 'get')
    def test_get_currency_prices_empty_name(self, mock_get):
        """Handle items with empty currency name."""
        mock_get.return_value = {
            "lines": [
                {"currencyTypeName": "", "chaosEquivalent": 1.0},
                {"currencyTypeName": "Valid", "chaosEquivalent": 2.0},
            ]
        }

        client = PoeNinjaClient()
        prices = client.get_currency_prices("Standard")

        # Both should be returned (empty name is still valid data)
        assert len(prices) == 2

    @patch.object(PoeNinjaClient, 'get')
    def test_get_item_prices_missing_fields(self, mock_get):
        """Handle items with missing optional fields."""
        mock_get.return_value = {
            "lines": [
                {
                    "name": "Minimal Item",
                    "chaosValue": 100.0,
                    # Missing all optional fields
                }
            ]
        }

        client = PoeNinjaClient()
        prices = client.get_item_prices("Standard", "UniqueWeapon")

        assert len(prices) == 1
        assert prices[0].name == "Minimal Item"
        assert prices[0].divine_value == 0  # Default
        assert prices[0].base_type == ""
        assert prices[0].variant == ""
        assert prices[0].links == 0

    def test_database_item_class_case_insensitive(self):
        """Item class lookup is case insensitive."""
        db = NinjaPriceDatabase(league="Standard")
        db.currency["test"] = NinjaPrice(name="Test", chaos_value=10.0)

        # Various cases
        assert db.get_price("test", item_class="Currency") is not None
        assert db.get_price("test", item_class="CURRENCY") is not None
        assert db.get_price("test", item_class="currency") is not None
