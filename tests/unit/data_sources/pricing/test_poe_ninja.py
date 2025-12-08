"""Tests for data_sources/pricing/poe_ninja.py - PoE.ninja API Client."""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock

from data_sources.pricing.poe_ninja import PoeNinjaAPI


# ============================================================================
# PoeNinjaAPI Initialization Tests
# ============================================================================


class TestPoeNinjaAPIInit:
    """Tests for PoeNinjaAPI initialization."""

    @patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__')
    def test_default_league(self, mock_base_init):
        """Default league is Standard."""
        mock_base_init.return_value = None

        api = PoeNinjaAPI()

        assert api.league == "Standard"

    @patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__')
    def test_init_with_league(self, mock_base_init):
        """Initializes with specified league."""
        mock_base_init.return_value = None

        api = PoeNinjaAPI(league="Keepers")

        assert api.league == "Keepers"
        assert api.divine_chaos_rate == 0.0
        assert api._currency_index == {}

    @patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__')
    def test_init_base_url(self, mock_base_init):
        """Base URL is set to poe.ninja API."""
        mock_base_init.return_value = None

        api = PoeNinjaAPI()

        mock_base_init.assert_called_once()
        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['base_url'] == "https://poe.ninja/api/data"

    @patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__')
    def test_init_rate_limit(self, mock_base_init):
        """Rate limit is conservative at 0.33."""
        mock_base_init.return_value = None

        api = PoeNinjaAPI()

        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['rate_limit'] == 0.33

    @patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__')
    def test_init_cache_ttl(self, mock_base_init):
        """Cache TTL is 1 hour."""
        mock_base_init.return_value = None

        api = PoeNinjaAPI()

        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['cache_ttl'] == 3600


# ============================================================================
# Cache Key Generation Tests
# ============================================================================


class TestCacheKeyGeneration:
    """Tests for _get_cache_key method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_cache_key_with_endpoint_only(self, api):
        """Cache key with endpoint only."""
        key = api._get_cache_key("leagues")
        assert key == "leagues::"

    def test_cache_key_with_league(self, api):
        """Cache key includes league param."""
        key = api._get_cache_key("get", {'league': 'Standard'})
        assert "Standard" in key

    def test_cache_key_with_type(self, api):
        """Cache key includes type param."""
        key = api._get_cache_key("get", {'league': 'Standard', 'type': 'Currency'})
        assert "Currency" in key


# ============================================================================
# Divine Rate Tests
# ============================================================================


class TestDivineRate:
    """Tests for divine rate methods."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_refresh_divine_rate_success(self, api):
        """Should extract divine rate from currency overview."""
        api.get_currency_overview = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Exalted Orb", "chaosEquivalent": 15.0},
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 180.0},
            ]
        })

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 180.0
        assert api.divine_chaos_rate == 180.0

    def test_refresh_divine_rate_uses_chaos_value(self, api):
        """Should use chaosValue if chaosEquivalent missing."""
        api.get_currency_overview = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Divine Orb", "chaosValue": 175.0},
            ]
        })

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 175.0

    def test_refresh_divine_rate_divine_not_found(self, api):
        """Should return 0 if Divine Orb not in response."""
        api.get_currency_overview = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Exalted Orb", "chaosEquivalent": 15.0},
            ]
        })

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 0.0
        assert api.divine_chaos_rate == 0.0

    def test_refresh_divine_rate_handles_exception(self, api):
        """Should return 0 on exception."""
        api.get_currency_overview = Mock(side_effect=Exception("API error"))

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 0.0
        assert api.divine_chaos_rate == 0.0

    def test_refresh_divine_rate_invalid_value(self, api):
        """Should handle invalid chaos value."""
        api.get_currency_overview = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": "invalid"},
            ]
        })

        rate = api.refresh_divine_rate_from_currency()

        assert rate == 0.0

    def test_ensure_divine_rate_uses_cache(self, api):
        """Should use cached rate if not expired."""
        api.divine_chaos_rate = 180.0
        api._divine_rate_expiry = time.time() + 3600  # 1 hour from now

        rate = api.ensure_divine_rate()

        assert rate == 180.0

    def test_ensure_divine_rate_refreshes_on_expiry(self, api):
        """Should refresh rate if cache expired."""
        api.divine_chaos_rate = 180.0
        api._divine_rate_expiry = time.time() - 1  # Already expired
        api.refresh_divine_rate_from_currency = Mock(return_value=200.0)

        rate = api.ensure_divine_rate()

        assert rate == 200.0
        api.refresh_divine_rate_from_currency.assert_called_once()

    def test_ensure_divine_rate_refreshes_on_invalid_cache(self, api):
        """Should refresh if cached rate is too low (bogus)."""
        api.divine_chaos_rate = 5.0  # Too low - bogus value
        api._divine_rate_expiry = time.time() + 3600
        api.refresh_divine_rate_from_currency = Mock(return_value=180.0)

        rate = api.ensure_divine_rate()

        assert rate == 180.0


# ============================================================================
# League Detection Tests
# ============================================================================


class TestLeagueDetection:
    """Tests for league detection methods."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    @patch('requests.get')
    def test_get_current_leagues_success(self, mock_get, api):
        """Should fetch leagues from trade API."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {"id": "Standard", "text": "Standard", "realm": "pc"},
                {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
                {"id": "Keepers", "text": "Keepers of the Trove", "realm": "pc"},
            ]
        }
        mock_get.return_value = mock_response

        leagues = api.get_current_leagues()

        assert len(leagues) == 3
        assert {"name": "Standard", "displayName": "Standard"} in leagues

    @patch('requests.get')
    def test_get_current_leagues_filters_non_pc(self, mock_get, api):
        """Should filter out non-PC realm leagues."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {"id": "Standard", "text": "Standard", "realm": "pc"},
                {"id": "Console Standard", "text": "Console Standard", "realm": "sony"},
            ]
        }
        mock_get.return_value = mock_response

        leagues = api.get_current_leagues()

        assert len(leagues) == 1
        assert leagues[0]["name"] == "Standard"

    @patch('requests.get')
    def test_get_current_leagues_deduplicates(self, mock_get, api):
        """Should deduplicate leagues by ID."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {"id": "Standard", "text": "Standard", "realm": "pc"},
                {"id": "Standard", "text": "Standard 2", "realm": "pc"},  # Duplicate
            ]
        }
        mock_get.return_value = mock_response

        leagues = api.get_current_leagues()

        assert len(leagues) == 1

    @patch('requests.get')
    def test_get_current_leagues_fallback_on_error(self, mock_get, api):
        """Should fallback to static leagues on error."""
        mock_get.side_effect = Exception("Network error")

        leagues = api.get_current_leagues()

        assert len(leagues) == 2
        names = [l["name"] for l in leagues]
        assert "Standard" in names
        assert "Hardcore" in names

    @patch('requests.get')
    def test_get_current_leagues_fallback_on_empty(self, mock_get, api):
        """Should fallback if no PC leagues found."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        leagues = api.get_current_leagues()

        assert len(leagues) == 2

    def test_detect_current_league_temp_league(self, api):
        """Should detect temp league as current."""
        api.get_current_leagues = Mock(return_value=[
            {"name": "Standard", "displayName": "Standard"},
            {"name": "Hardcore", "displayName": "Hardcore"},
            {"name": "Keepers", "displayName": "Keepers of the Trove"},
        ])

        league = api.detect_current_league()

        assert league == "Keepers"

    def test_detect_current_league_fallback_standard(self, api):
        """Should fallback to Standard if no temp league."""
        api.get_current_leagues = Mock(return_value=[
            {"name": "Standard", "displayName": "Standard"},
            {"name": "Hardcore", "displayName": "Hardcore"},
        ])

        league = api.detect_current_league()

        assert league == "Standard"


# ============================================================================
# Currency Overview Tests
# ============================================================================


class TestCurrencyOverview:
    """Tests for currency overview methods."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_get_currency_overview_builds_index(self, api):
        """Should build currency index from response."""
        api.get = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 180.0},
                {"currencyTypeName": "Exalted Orb", "chaosEquivalent": 15.0},
            ]
        })

        api.get_currency_overview()

        assert "divine orb" in api._currency_index
        assert "exalted orb" in api._currency_index
        assert api.divine_chaos_rate == 180.0

    def test_get_currency_overview_clears_old_index(self, api):
        """Should clear old index before rebuilding."""
        api._currency_index = {"old": "data"}
        api.get = Mock(return_value={
            "lines": [
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 180.0},
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
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {
                "divine orb": {"chaosEquivalent": 180.0},
                "exalted orb": {"chaosValue": 15.0},
            }
            api.divine_chaos_rate = 180.0
            api._divine_rate_expiry = 0.0
            return api

    def test_get_currency_price_found(self, api):
        """Should return price for currency in index."""
        price, source = api.get_currency_price("Divine Orb")

        assert price == 180.0
        assert "poe.ninja" in source

    def test_get_currency_price_chaos_orb(self, api):
        """Chaos Orb is always 1.0."""
        price, source = api.get_currency_price("Chaos Orb")

        assert price == 1.0
        assert "reference" in source

    def test_get_currency_price_not_found(self, api):
        """Should return 0 for unknown currency."""
        price, source = api.get_currency_price("Unknown Currency")

        assert price == 0.0
        assert "not found" in source

    def test_get_currency_price_empty_name(self, api):
        """Should return 0 for empty name."""
        price, source = api.get_currency_price("")

        assert price == 0.0
        assert "empty" in source

    def test_get_currency_price_populates_index_if_empty(self, api):
        """Should fetch currency overview if index is empty."""
        api._currency_index = {}
        api.get_currency_overview = Mock(return_value={"lines": []})

        api.get_currency_price("Divine Orb")

        api.get_currency_overview.assert_called_once()

    def test_get_currency_price_handles_fetch_error(self, api):
        """Should return error on fetch failure."""
        api._currency_index = {}
        api.get_currency_overview = Mock(side_effect=Exception("API error"))

        price, source = api.get_currency_price("Divine Orb")

        assert price == 0.0
        assert "error" in source


# ============================================================================
# Item Overview Tests
# ============================================================================


class TestItemOverview:
    """Tests for item overview methods."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_get_item_overview_success(self, api):
        """Should fetch item overview."""
        api.get = Mock(return_value={
            "lines": [
                {"name": "Headhunter", "chaosValue": 50000},
            ]
        })

        result = api._get_item_overview("UniqueArmour")

        assert result is not None
        assert result["lines"][0]["name"] == "Headhunter"

    def test_get_item_overview_handles_error(self, api):
        """Should return None on error."""
        api.get = Mock(side_effect=Exception("API error"))

        result = api._get_item_overview("UniqueArmour")

        assert result is None

    def test_get_skill_gem_overview(self, api):
        """Should fetch skill gem overview."""
        api._get_item_overview = Mock(return_value={"lines": []})

        api.get_skill_gem_overview()

        api._get_item_overview.assert_called_once_with("SkillGem")


# ============================================================================
# Load All Prices Tests
# ============================================================================


class TestLoadAllPrices:
    """Tests for load_all_prices method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_load_all_prices_structure(self, api):
        """Should return cache with all categories."""
        api.get_currency_overview = Mock(return_value={"lines": []})
        api._get_item_overview = Mock(return_value={"lines": []})

        cache = api.load_all_prices()

        assert "currency" in cache
        assert "uniques" in cache
        assert "fragments" in cache
        assert "divination" in cache
        assert "essences" in cache
        assert "fossils" in cache
        assert "scarabs" in cache
        assert "oils" in cache

    def test_load_all_prices_handles_errors(self, api):
        """Should handle errors for individual categories."""
        api.get_currency_overview = Mock(return_value={"lines": []})
        api._get_item_overview = Mock(side_effect=Exception("API error"))

        # Should not raise
        cache = api.load_all_prices()

        assert cache is not None


# ============================================================================
# Find Item Price Tests
# ============================================================================


class TestFindItemPrice:
    """Tests for find_item_price method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_find_gem_price(self, api):
        """Should find gem price."""
        api._find_gem_price = Mock(return_value={"name": "Vaal Grace", "chaosValue": 100})

        result = api.find_item_price("Vaal Grace", None, rarity="GEM")

        api._find_gem_price.assert_called_once()
        assert result is not None

    def test_find_divination_card_price(self, api):
        """Should find divination card price."""
        api._find_from_overview_by_name = Mock(return_value={"name": "The Doctor", "chaosValue": 5000})

        result = api.find_item_price("The Doctor", None, rarity="DIVINATION")

        api._find_from_overview_by_name.assert_called_with("DivinationCard", "The Doctor")

    def test_find_fragment_price(self, api):
        """Should find fragment price."""
        api._find_from_overview_by_name = Mock(return_value={"name": "Mortal Ignorance", "chaosValue": 50})

        result = api.find_item_price("Mortal Ignorance", None, rarity="FRAGMENT")

        api._find_from_overview_by_name.assert_called_with("Fragment", "Mortal Ignorance")

    def test_find_unique_item_price(self, api):
        """Should search unique item overviews."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "Headhunter", "baseType": "Leather Belt", "chaosValue": 50000}
            ]
        })

        result = api.find_item_price("Headhunter", "Leather Belt", rarity="UNIQUE")

        assert result is not None
        assert result["name"] == "Headhunter"

    def test_find_scarab_by_name(self, api):
        """Should find scarab by name substring."""
        api._find_from_overview_by_name = Mock(return_value={"name": "Gilded Breach Scarab", "chaosValue": 10})

        result = api.find_item_price("Gilded Breach Scarab", None)

        api._find_from_overview_by_name.assert_called_with("Scarab", "Gilded Breach Scarab")

    def test_find_essence_by_name(self, api):
        """Should find essence by name substring."""
        api._find_from_overview_by_name = Mock(return_value={"name": "Deafening Essence of Woe"})

        result = api.find_item_price("Deafening Essence of Woe", None)

        api._find_from_overview_by_name.assert_called_with("Essence", "Deafening Essence of Woe")

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
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_exact_match(self, api):
        """Should find exact name match."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "The Doctor"},
                {"name": "The Nurse"},
            ]
        })

        result = api._find_from_overview_by_name("DivinationCard", "The Doctor")

        assert result is not None
        assert result["name"] == "The Doctor"

    def test_case_insensitive_match(self, api):
        """Should match case-insensitively."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "The Doctor"},
            ]
        })

        result = api._find_from_overview_by_name("DivinationCard", "the doctor")

        assert result is not None

    def test_substring_fallback(self, api):
        """Should fall back to substring match."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "Gilded Breach Scarab"},
            ]
        })

        result = api._find_from_overview_by_name("Scarab", "Breach Scarab")

        assert result is not None

    def test_returns_none_if_not_found(self, api):
        """Should return None if not found."""
        api._get_item_overview = Mock(return_value={
            "lines": [
                {"name": "The Doctor"},
            ]
        })

        result = api._find_from_overview_by_name("DivinationCard", "Nonexistent")

        assert result is None

    def test_returns_none_if_overview_empty(self, api):
        """Should return None if overview is empty."""
        api._get_item_overview = Mock(return_value={"lines": []})

        result = api._find_from_overview_by_name("DivinationCard", "The Doctor")

        assert result is None

    def test_returns_none_if_overview_none(self, api):
        """Should return None if overview fetch fails."""
        api._get_item_overview = Mock(return_value=None)

        result = api._find_from_overview_by_name("DivinationCard", "The Doctor")

        assert result is None

    def test_returns_none_for_empty_name(self, api):
        """Should return None for empty name."""
        api._get_item_overview = Mock(return_value={
            "lines": [{"name": "The Doctor"}]
        })

        result = api._find_from_overview_by_name("DivinationCard", "")

        assert result is None


# ============================================================================
# Gem Price Tests
# ============================================================================


class TestGemPrice:
    """Tests for _find_gem_price method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_ninja.BaseAPIClient.__init__'):
            api = PoeNinjaAPI.__new__(PoeNinjaAPI)
            api.league = "Standard"
            api._currency_index = {}
            api.divine_chaos_rate = 0.0
            api._divine_rate_expiry = 0.0
            return api

    def test_find_gem_exact_match(self, api):
        """Should find gem by exact name."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Vaal Grace", "gemLevel": 20, "gemQuality": 20, "chaosValue": 100},
            ]
        })

        result = api._find_gem_price("Vaal Grace", None, None, None)

        assert result is not None
        assert result["name"] == "Vaal Grace"

    def test_filter_by_gem_level(self, api):
        """Should filter by gem level."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Vaal Grace", "gemLevel": 1, "chaosValue": 10},
                {"name": "Vaal Grace", "gemLevel": 21, "chaosValue": 500},
            ]
        })

        result = api._find_gem_price("Vaal Grace", gem_level=21, gem_quality=None, corrupted=None)

        assert result["gemLevel"] == 21

    def test_filter_by_quality(self, api):
        """Should filter by quality."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Vaal Grace", "gemLevel": 20, "gemQuality": 0, "chaosValue": 50},
                {"name": "Vaal Grace", "gemLevel": 20, "gemQuality": 23, "chaosValue": 200},
            ]
        })

        result = api._find_gem_price("Vaal Grace", gem_level=20, gem_quality=23, corrupted=None)

        assert result["gemQuality"] == 23

    def test_filter_by_corrupted(self, api):
        """Should filter by corruption."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Vaal Grace", "corrupted": False, "chaosValue": 50},
                {"name": "Vaal Grace", "corrupted": True, "chaosValue": 100},
            ]
        })

        result = api._find_gem_price("Vaal Grace", None, None, corrupted=True)

        assert result["corrupted"] is True

    def test_returns_highest_value_when_multiple(self, api):
        """Should return highest value gem when multiple candidates."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Vaal Grace", "chaosValue": 50},
                {"name": "Vaal Grace", "chaosValue": 200},
                {"name": "Vaal Grace", "chaosValue": 100},
            ]
        })

        result = api._find_gem_price("Vaal Grace", None, None, None)

        assert result["chaosValue"] == 200

    def test_returns_none_if_not_found(self, api):
        """Should return None if gem not found."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [
                {"name": "Other Gem", "chaosValue": 100},
            ]
        })

        result = api._find_gem_price("Vaal Grace", None, None, None)

        assert result is None

    def test_returns_none_if_overview_empty(self, api):
        """Should return None if overview empty."""
        api.get_skill_gem_overview = Mock(return_value={"lines": []})

        result = api._find_gem_price("Vaal Grace", None, None, None)

        assert result is None

    def test_returns_none_if_overview_none(self, api):
        """Should return None if overview fetch fails."""
        api.get_skill_gem_overview = Mock(return_value=None)

        result = api._find_gem_price("Vaal Grace", None, None, None)

        assert result is None

    def test_returns_none_for_empty_name(self, api):
        """Should return None for empty name."""
        api.get_skill_gem_overview = Mock(return_value={
            "lines": [{"name": "Vaal Grace", "chaosValue": 100}]
        })

        result = api._find_gem_price("", None, None, None)

        assert result is None
