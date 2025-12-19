"""Tests for data_sources/pricing/poe2_ninja.py - PoE2.ninja API Client."""

import time
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

from data_sources.pricing.poe2_ninja import Poe2NinjaAPI


# ============================================================================
# Poe2NinjaAPI Initialization Tests
# ============================================================================


class TestPoe2NinjaAPIInit:
    """Tests for Poe2NinjaAPI initialization."""

    @patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__')
    def test_default_league(self, mock_base_init):
        """Default league is Standard."""
        mock_base_init.return_value = None

        api = Poe2NinjaAPI()

        assert api.league == "Standard"

    @patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__')
    def test_init_with_league(self, mock_base_init):
        """Initializes with specified league."""
        mock_base_init.return_value = None

        api = Poe2NinjaAPI(league="Dawn of the Hunt")

        assert api.league == "Dawn of the Hunt"
        assert api.divine_exalted_rate == 0.0
        assert api._currency_index == {}

    @patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__')
    def test_init_base_url(self, mock_base_init):
        """Base URL is set to poe2.ninja API."""
        mock_base_init.return_value = None

        Poe2NinjaAPI()

        mock_base_init.assert_called_once()
        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['base_url'] == "https://poe2.ninja/api/data"

    @patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__')
    def test_init_rate_limit(self, mock_base_init):
        """Rate limit is conservative at 0.33."""
        mock_base_init.return_value = None

        Poe2NinjaAPI()

        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['rate_limit'] == 0.33

    @patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__')
    def test_init_cache_ttl(self, mock_base_init):
        """Cache TTL is 1 hour."""
        mock_base_init.return_value = None

        Poe2NinjaAPI()

        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['cache_ttl'] == 3600


# ============================================================================
# Divine Rate Tests (PoE2 uses Exalted as base)
# ============================================================================


class TestDivineRate:
    """Tests for divine rate methods (Divine per Exalted in PoE2)."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__'):
            api = Poe2NinjaAPI.__new__(Poe2NinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_exalted_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_refresh_divine_rate_success(self, api):
        """Should extract divine rate from currency overview."""
        # Mock get method to return currency overview data with exaltedValue
        api.get = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Chaos Orb", "exaltedValue": 0.14},
                {"currencyTypeName": "Divine Orb", "exaltedValue": 80.0},
            ]
        })

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 80.0
        assert api.divine_exalted_rate == 80.0

    def test_refresh_divine_rate_uses_exalted_value(self, api):
        """Should use exaltedValue if exaltedEquivalent missing."""
        api.get = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Divine Orb", "exaltedValue": 75.0},
            ]
        })

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 75.0

    def test_refresh_divine_rate_divine_not_found(self, api):
        """Should return 0 if Divine Orb not in response."""
        api.get = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Chaos Orb", "exaltedValue": 0.14},
            ]
        })

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 0.0
        assert api.divine_exalted_rate == 0.0

    def test_refresh_divine_rate_handles_exception(self, api):
        """Should return 0 on network exception."""
        api.get = Mock(side_effect=requests.RequestException("API error"))

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 0.0
        assert api.divine_exalted_rate == 0.0

    def test_ensure_divine_rate_uses_cache(self, api):
        """Should use cached rate if not expired."""
        api.divine_exalted_rate = 80.0
        api._divine_rate_expiry = time.time() + 3600  # 1 hour from now

        rate = api.ensure_divine_rate()

        assert rate == 80.0

    def test_ensure_divine_rate_refreshes_on_expiry(self, api):
        """Should refresh rate if cache expired."""
        api.divine_exalted_rate = 80.0
        api._divine_rate_expiry = time.time() - 1  # Already expired
        api.refresh_divine_rate_from_currency = Mock(return_value=90.0)

        rate = api.ensure_divine_rate()

        assert rate == 90.0
        api.refresh_divine_rate_from_currency.assert_called_once()


# ============================================================================
# Currency Overview Tests
# ============================================================================


class TestCurrencyOverview:
    """Tests for currency overview methods."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__'):
            api = Poe2NinjaAPI.__new__(Poe2NinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_exalted_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_get_currency_overview_builds_index(self, api):
        """Should build currency index from response."""
        api.get = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Divine Orb", "exaltedEquivalent": 80.0},
                {"currencyTypeName": "Chaos Orb", "exaltedEquivalent": 0.14},
            ]
        })

        api.get_currency_overview()

        assert "divine orb" in api._currency_index
        assert "chaos orb" in api._currency_index
        assert api.divine_exalted_rate == 80.0

    def test_get_currency_overview_clears_old_index(self, api):
        """Should clear old index before rebuilding."""
        api._currency_index = {"old": "data"}
        api.get = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Divine Orb", "exaltedEquivalent": 80.0},
            ]
        })

        api.get_currency_overview()

        assert "old" not in api._currency_index
        assert "divine orb" in api._currency_index


# ============================================================================
# Currency Price Tests
# ============================================================================


class TestCurrencyPrice:
    """Tests for get_currency_price method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__'):
            api = Poe2NinjaAPI.__new__(Poe2NinjaAPI)
            api.league = "Standard"
            api._currency_index = {
                "divine orb": {"exaltedValue": 80.0},
                "chaos orb": {"exaltedValue": 0.14},
            }
            api.divine_exalted_rate = 80.0
            api._divine_rate_expiry = 0.0
            return api

    def test_get_currency_price_found(self, api):
        """Should return price tuple for currency in index."""
        price, source = api.get_currency_price("Divine Orb")

        assert price == 80.0
        assert "poe2.ninja" in source

    def test_get_currency_price_exalted_orb(self, api):
        """Exalted Orb is always 1.0 (base currency in PoE2)."""
        price, source = api.get_currency_price("Exalted Orb")

        assert price == 1.0
        assert "reference" in source

    def test_get_currency_price_not_found(self, api):
        """Should return 0.0 and 'not found' for unknown currency."""
        price, source = api.get_currency_price("Unknown Currency")

        assert price == 0.0
        assert "not found" in source

    def test_get_currency_price_empty_name(self, api):
        """Should return 0.0 and 'empty name' for empty name."""
        price, source = api.get_currency_price("")

        assert price == 0.0
        assert "empty" in source

    def test_get_currency_price_populates_index_if_empty(self, api):
        """Should fetch currency overview if index is empty."""
        api._currency_index = {}
        api.get_currency_overview = Mock(return_value={"lines": []})

        api.get_currency_price("Divine Orb")

        api.get_currency_overview.assert_called_once()


# ============================================================================
# Find Item Price Tests
# ============================================================================


class TestFindItemPrice:
    """Tests for find_item_price method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__'):
            api = Poe2NinjaAPI.__new__(Poe2NinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_exalted_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_find_gem_price(self, api):
        """Should find gem price."""
        api._find_gem_price = Mock(return_value={"name": "Fireball", "exaltedValue": 50})

        result = api.find_item_price("Fireball", None, rarity="GEM")

        api._find_gem_price.assert_called_once()
        assert result is not None

    def test_find_unique_item_price(self, api):
        """Should search unique item overviews."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "Voidfletcher", "baseType": "Spine Bow", "exaltedValue": 500}
            ]
        })

        result = api.find_item_price("Voidfletcher", "Spine Bow", rarity="UNIQUE")

        assert result is not None
        assert result["name"] == "Voidfletcher"

    def test_find_rune_price(self, api):
        """Should find rune price (PoE2-specific item type)."""
        api._find_from_overview_by_name = Mock(return_value={"name": "Glacial Rune", "exaltedValue": 10})

        api.find_item_price("Glacial Rune", None, rarity="RUNE")

        api._find_from_overview_by_name.assert_called_with("Rune", "Glacial Rune")

    def test_find_soulcore_price(self, api):
        """Should find soul core price (PoE2-specific item type)."""
        api._find_from_overview_by_name = Mock(return_value={"name": "Soul Core of Azcapa", "exaltedValue": 100})

        api.find_item_price("Soul Core of Azcapa", None, rarity="SOULCORE")

        api._find_from_overview_by_name.assert_called_with("SoulCore", "Soul Core of Azcapa")

    def test_returns_none_for_unknown(self, api):
        """Should return None for unknown items."""
        api._find_from_overview_by_name = Mock(return_value=None)
        api._get_item_overview = Mock(return_value={"lines": []})

        result = api.find_item_price("Random Rare Item", "Iron Ring", rarity="RARE")

        assert result is None


# ============================================================================
# Find From Overview Tests
# ============================================================================


class TestFindFromOverview:
    """Tests for _find_from_overview_by_name method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__'):
            api = Poe2NinjaAPI.__new__(Poe2NinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_exalted_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_exact_match(self, api):
        """Should find exact name match."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "Glacial Rune"},
                {"name": "Fire Rune"},
            ]
        })

        result = api._find_from_overview_by_name("Rune", "Glacial Rune")

        assert result is not None
        assert result["name"] == "Glacial Rune"

    def test_case_insensitive_match(self, api):
        """Should match case-insensitively."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "Glacial Rune"},
            ]
        })

        result = api._find_from_overview_by_name("Rune", "glacial rune")

        assert result is not None

    def test_returns_none_if_not_found(self, api):
        """Should return None if not found."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "Glacial Rune"},
            ]
        })

        result = api._find_from_overview_by_name("Rune", "Nonexistent")

        assert result is None


# ============================================================================
# Gem Price Tests
# ============================================================================


class TestGemPrice:
    """Tests for _find_gem_price method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__'):
            api = Poe2NinjaAPI.__new__(Poe2NinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_exalted_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_find_gem_exact_match(self, api):
        """Should find gem by exact name."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Fireball", "gemLevel": 20, "gemQuality": 20, "exaltedValue": 100},
            ]
        })

        result = api._find_gem_price("Fireball", None, None, None)

        assert result is not None
        assert result["name"] == "Fireball"

    def test_filter_by_gem_level(self, api):
        """Should filter by gem level."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Fireball", "gemLevel": 1, "exaltedValue": 1},
                {"name": "Fireball", "gemLevel": 21, "exaltedValue": 500},
            ]
        })

        result = api._find_gem_price("Fireball", gem_level=21, gem_quality=None, corrupted=None)

        assert result["gemLevel"] == 21

    def test_returns_none_if_not_found(self, api):
        """Should return None if gem not found."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Other Gem", "exaltedValue": 100},
            ]
        })

        result = api._find_gem_price("Fireball", None, None, None)

        assert result is None


# ============================================================================
# Item Type Tests
# ============================================================================


class TestItemTypes:
    """Tests for PoE2-specific item type constants."""

    @patch('data_sources.pricing.poe2_ninja.BaseAPIClient.__init__')
    def test_item_types_include_poe2_items(self, mock_base_init):
        """ITEM_TYPES should include PoE2-specific item types."""
        mock_base_init.return_value = None

        api = Poe2NinjaAPI()

        # PoE2-specific item types
        assert "Rune" in api.ITEM_TYPES
        assert "SoulCore" in api.ITEM_TYPES
        assert "SkillGem" in api.ITEM_TYPES
        # Uniques
        assert "UniqueWeapon" in api.ITEM_TYPES
        assert "UniqueArmour" in api.ITEM_TYPES
        # Note: Currency is handled separately via get_currency_overview, not ITEM_TYPES
