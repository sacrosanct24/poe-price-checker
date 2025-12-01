"""
Tests for poe.ninja API Client.

Tests the client structure and data classes.
Network tests are mocked to avoid requiring real API calls.
"""
import pytest
from unittest.mock import patch

from data_sources.poe_ninja_client import (
    NinjaPrice,
    NinjaPriceDatabase,
    PoeNinjaClient,
    get_ninja_client,
)


class TestNinjaPrice:
    """Tests for NinjaPrice dataclass."""

    def test_basic_creation(self):
        """Test creating a basic price."""
        price = NinjaPrice(
            name="Chaos Orb",
            chaos_value=1.0,
        )
        assert price.name == "Chaos Orb"
        assert price.chaos_value == 1.0

    def test_display_price_high_value(self):
        """Test display price for high value items."""
        price = NinjaPrice(name="Divine Orb", chaos_value=150.0)
        assert price.display_price == "150c"

    def test_display_price_medium_value(self):
        """Test display price for medium value items."""
        price = NinjaPrice(name="Exalted Orb", chaos_value=15.5)
        assert price.display_price == "15.5c"

    def test_display_price_low_value(self):
        """Test display price for low value items."""
        price = NinjaPrice(name="Alteration Orb", chaos_value=0.05)
        assert price.display_price == "0.05c"

    def test_full_attributes(self):
        """Test price with all attributes."""
        price = NinjaPrice(
            name="Mageblood",
            chaos_value=50000.0,
            divine_value=300.0,
            base_type="Heavy Belt",
            variant="4 Flask",
            links=0,
            item_class="UniqueAccessory",
            icon="https://example.com/icon.png",
            details_id="mageblood",
        )
        assert price.base_type == "Heavy Belt"
        assert price.variant == "4 Flask"
        assert price.divine_value == 300.0


class TestNinjaPriceDatabase:
    """Tests for NinjaPriceDatabase."""

    def test_empty_database(self):
        """Test creating empty database."""
        db = NinjaPriceDatabase(league="Phrecia")
        assert db.league == "Phrecia"
        assert len(db.currency) == 0
        assert len(db.uniques) == 0

    def test_get_price_from_currency(self):
        """Test getting price from currency database."""
        db = NinjaPriceDatabase(league="Phrecia")
        db.currency["divine orb"] = NinjaPrice(name="Divine Orb", chaos_value=150.0)

        price = db.get_price("divine orb")
        assert price is not None
        assert price.chaos_value == 150.0

    def test_get_price_case_insensitive(self):
        """Test price lookup is case insensitive."""
        db = NinjaPriceDatabase(league="Phrecia")
        db.currency["divine orb"] = NinjaPrice(name="Divine Orb", chaos_value=150.0)

        # Lookup with different cases - get_price lowercases the input
        assert db.get_price("DIVINE ORB") is not None  # Case insensitive
        assert db.get_price("Divine Orb") is not None
        assert db.get_price("divine orb") is not None

    def test_get_price_with_item_class(self):
        """Test getting price with specific item class."""
        db = NinjaPriceDatabase(league="Phrecia")
        db.currency["chaos orb"] = NinjaPrice(name="Chaos Orb", chaos_value=1.0)
        db.uniques["chaos orb"] = NinjaPrice(name="Chaos Orb", chaos_value=50.0)  # Different

        # Should find currency first when item_class is specified
        price = db.get_price("chaos orb", item_class="currency")
        assert price.chaos_value == 1.0

    def test_get_price_not_found(self):
        """Test getting price for unknown item."""
        db = NinjaPriceDatabase(league="Phrecia")
        price = db.get_price("Unknown Item XYZ")
        assert price is None

    def test_get_all_prices(self):
        """Test getting all prices merged."""
        db = NinjaPriceDatabase(league="Phrecia")
        db.currency["chaos orb"] = NinjaPrice(name="Chaos Orb", chaos_value=1.0)
        db.uniques["mageblood"] = NinjaPrice(name="Mageblood", chaos_value=50000.0)

        all_prices = db.get_all_prices()
        assert len(all_prices) == 2
        assert "chaos orb" in all_prices
        assert "mageblood" in all_prices


class TestPoeNinjaClient:
    """Tests for PoeNinjaClient class."""

    def test_client_initialization(self):
        """Test client initializes correctly."""
        client = PoeNinjaClient()
        assert client.base_url == "https://poe.ninja/api/data"

    def test_cache_key_generation(self):
        """Test cache key generation."""
        client = PoeNinjaClient()
        key = client._get_cache_key("currencyoverview", {"league": "Phrecia", "type": "Currency"})
        assert "poeninja:" in key
        assert "currencyoverview" in key
        assert "Phrecia" in key

    @patch.object(PoeNinjaClient, 'get')
    def test_get_currency_prices(self, mock_get):
        """Test getting currency prices."""
        mock_get.return_value = {
            "lines": [
                {
                    "currencyTypeName": "Divine Orb",
                    "chaosEquivalent": 150.0,
                    "icon": "https://example.com/divine.png",
                    "detailsId": "divine-orb",
                },
                {
                    "currencyTypeName": "Exalted Orb",
                    "chaosEquivalent": 15.0,
                    "icon": "https://example.com/exalted.png",
                    "detailsId": "exalted-orb",
                },
            ]
        }

        client = PoeNinjaClient()
        prices = client.get_currency_prices("Phrecia")

        assert len(prices) == 2
        assert prices[0].name == "Divine Orb"
        assert prices[0].chaos_value == 150.0
        assert prices[1].name == "Exalted Orb"

    @patch.object(PoeNinjaClient, 'get')
    def test_get_item_prices(self, mock_get):
        """Test getting item prices."""
        mock_get.return_value = {
            "lines": [
                {
                    "name": "Mageblood",
                    "chaosValue": 50000.0,
                    "divineValue": 300.0,
                    "baseType": "Heavy Belt",
                    "variant": "4 Flask",
                    "links": 0,
                    "icon": "https://example.com/mageblood.png",
                },
                {
                    "name": "Headhunter",
                    "chaosValue": 8000.0,
                    "divineValue": 50.0,
                    "baseType": "Leather Belt",
                    "variant": None,
                    "links": 0,
                    "icon": "https://example.com/headhunter.png",
                },
            ]
        }

        client = PoeNinjaClient()
        prices = client.get_item_prices("Phrecia", "UniqueAccessory")

        assert len(prices) == 2
        assert prices[0].name == "Mageblood"
        assert prices[0].chaos_value == 50000.0
        assert prices[0].base_type == "Heavy Belt"
        assert prices[1].name == "Headhunter"

    @patch.object(PoeNinjaClient, 'get')
    def test_get_divine_chaos_rate(self, mock_get):
        """Test getting divine to chaos rate."""
        mock_get.return_value = {
            "lines": [
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1.0},
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 150.0},
                {"currencyTypeName": "Exalted Orb", "chaosEquivalent": 15.0},
            ]
        }

        client = PoeNinjaClient()
        rate = client.get_divine_chaos_rate("Phrecia")

        assert rate == 150.0

    @patch.object(PoeNinjaClient, 'get')
    def test_get_divine_chaos_rate_fallback(self, mock_get):
        """Test divine rate fallback when not found."""
        mock_get.return_value = {
            "lines": [
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1.0},
            ]
        }

        client = PoeNinjaClient()
        rate = client.get_divine_chaos_rate("Phrecia")

        assert rate == 1.0  # Fallback

    @patch.object(PoeNinjaClient, 'get_currency_prices')
    @patch.object(PoeNinjaClient, 'get_item_prices')
    def test_build_price_database(self, mock_items, mock_currency):
        """Test building price database."""
        mock_currency.return_value = [
            NinjaPrice(name="Divine Orb", chaos_value=150.0),
            NinjaPrice(name="Chaos Orb", chaos_value=1.0),
        ]
        mock_items.return_value = [
            NinjaPrice(name="Mageblood", chaos_value=50000.0, base_type="Heavy Belt"),
        ]

        client = PoeNinjaClient()
        db = client.build_price_database("Phrecia", item_types=["UniqueAccessory"])

        assert db.league == "Phrecia"
        assert "divine orb" in db.currency
        assert db.currency["divine orb"].chaos_value == 150.0

    @patch.object(PoeNinjaClient, 'get_currency_prices')
    @patch.object(PoeNinjaClient, 'get_item_prices')
    def test_build_price_database_with_progress(self, mock_items, mock_currency):
        """Test progress callback is called."""
        mock_currency.return_value = []
        mock_items.return_value = []

        progress_calls = []
        def progress(cur, total, name):
            progress_calls.append((cur, total, name))

        client = PoeNinjaClient()
        client.build_price_database("Phrecia", item_types=[], progress_callback=progress)

        # Should have 2 calls for currency types
        assert len(progress_calls) >= 2


class TestGetNinjaClient:
    """Tests for singleton client."""

    def test_returns_singleton(self):
        """Test that get_ninja_client returns same instance."""
        client1 = get_ninja_client()
        client2 = get_ninja_client()
        assert client1 is client2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
