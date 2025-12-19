"""Tests for data_sources/pricing/poe_watch.py - poe.watch API Client."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from data_sources.pricing.poe_watch import PoeWatchAPI


# ============================================================================
# PoeWatchAPI Initialization Tests
# ============================================================================

class TestPoeWatchAPIInit:
    """Tests for PoeWatchAPI initialization."""

    def test_default_league(self):
        """Default league is Standard."""
        with patch.object(PoeWatchAPI, '__init__', lambda self, league: None):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            assert api.league == "Standard"

    @patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__')
    def test_init_with_league(self, mock_base_init):
        """Initializes with specified league."""
        mock_base_init.return_value = None

        api = PoeWatchAPI(league="Keepers")

        assert api.league == "Keepers"
        assert api._item_cache == {}
        assert api._category_cache is None
        assert api.request_count == 0

    @patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__')
    def test_init_base_url(self, mock_base_init):
        """Base URL is set to poe.watch API."""
        mock_base_init.return_value = None

        PoeWatchAPI()

        mock_base_init.assert_called_once()
        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['base_url'] == "https://api.poe.watch"

    @patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__')
    def test_init_rate_limit(self, mock_base_init):
        """Rate limit is conservative at 0.5 (1 request per 2 seconds)."""
        mock_base_init.return_value = None

        PoeWatchAPI()

        call_kwargs = mock_base_init.call_args[1]
        assert call_kwargs['rate_limit'] == 0.5

    @patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__')
    def test_init_cache_ttl(self, mock_base_init):
        """Cache TTL is 1 hour."""
        mock_base_init.return_value = None

        PoeWatchAPI()

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
        with patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__'):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            api._item_cache = {}
            api._category_cache = None
            api.request_count = 0
            return api

    def test_cache_key_with_endpoint_only(self, api):
        """Cache key with endpoint only."""
        key = api._get_cache_key("leagues")
        assert key == "leagues::::"

    def test_cache_key_with_league(self, api):
        """Cache key includes league param."""
        key = api._get_cache_key("get", {'league': 'Standard'})
        assert "Standard" in key

    def test_cache_key_with_category(self, api):
        """Cache key includes category param."""
        key = api._get_cache_key("get", {'league': 'Standard', 'category': 'currency'})
        assert "currency" in key

    def test_cache_key_with_id(self, api):
        """Cache key includes item ID param."""
        key = api._get_cache_key("history", {'league': 'Standard', 'id': 123})
        assert "123" in key

    def test_cache_key_with_query(self, api):
        """Cache key includes search query param."""
        key = api._get_cache_key("search", {'league': 'Standard', 'q': 'Divine Orb'})
        assert "Divine Orb" in key

    def test_cache_key_all_params(self, api):
        """Cache key with all params."""
        key = api._get_cache_key("get", {
            'league': 'Keepers',
            'category': 'gem',
            'id': 456,
            'q': 'test'
        })
        assert key == "get:Keepers:gem:456:test"


# ============================================================================
# Request Tracking Tests
# ============================================================================

class TestRequestTracking:
    """Tests for get method and request counting."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__'):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            api._item_cache = {}
            api._category_cache = None
            api.request_count = 0
            return api

    @patch('data_sources.base_api.BaseAPIClient.get')
    def test_get_increments_request_count(self, mock_get, api):
        """get() increments request count."""
        mock_get.return_value = []

        api.get("test")

        assert api.request_count == 1

    @patch('data_sources.base_api.BaseAPIClient.get')
    def test_get_tracks_multiple_requests(self, mock_get, api):
        """Multiple get() calls accumulate request count."""
        mock_get.return_value = []

        api.get("test1")
        api.get("test2")
        api.get("test3")

        assert api.request_count == 3


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestAPIEndpoints:
    """Tests for API endpoint methods."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__'):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            api._item_cache = {}
            api._category_cache = None
            api.request_count = 0
            return api

    @patch.object(PoeWatchAPI, 'get')
    def test_get_leagues(self, mock_get, api):
        """get_leagues calls correct endpoint."""
        mock_get.return_value = [{'name': 'Standard'}]

        result = api.get_leagues()

        mock_get.assert_called_once_with("leagues")
        assert result == [{'name': 'Standard'}]

    @patch.object(PoeWatchAPI, 'get')
    def test_get_categories_fetches_once(self, mock_get, api):
        """get_categories caches results."""
        mock_get.return_value = [{'id': 1, 'name': 'currency'}]

        result1 = api.get_categories()
        result2 = api.get_categories()

        # Should only call once due to caching
        mock_get.assert_called_once_with("categories")
        assert result1 == result2

    @patch.object(PoeWatchAPI, 'get')
    def test_get_categories_returns_cached(self, mock_get, api):
        """get_categories returns cached data if available."""
        api._category_cache = [{'id': 1, 'name': 'cached'}]

        result = api.get_categories()

        mock_get.assert_not_called()
        assert result == [{'id': 1, 'name': 'cached'}]

    @patch.object(PoeWatchAPI, 'get')
    def test_get_items_by_category(self, mock_get, api):
        """get_items_by_category calls correct endpoint with params."""
        mock_get.return_value = []

        api.get_items_by_category("currency")

        mock_get.assert_called_once_with("get", params={
            'league': 'Standard',
            'category': 'currency'
        })

    @patch.object(PoeWatchAPI, 'get')
    def test_get_items_by_category_with_filters(self, mock_get, api):
        """get_items_by_category passes additional filters."""
        mock_get.return_value = []

        api.get_items_by_category("gem", gemLevel=20, gemQuality=20)

        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params['gemLevel'] == 20
        assert params['gemQuality'] == 20

    @patch.object(PoeWatchAPI, 'get')
    def test_search_items(self, mock_get, api):
        """search_items calls correct endpoint with query."""
        mock_get.return_value = [{'name': 'Divine Orb'}]

        api.search_items("Divine")

        mock_get.assert_called_once_with("search", params={
            'league': 'Standard',
            'q': 'Divine'
        })

    @patch.object(PoeWatchAPI, 'get')
    def test_get_item_history(self, mock_get, api):
        """get_item_history calls correct endpoint with item ID."""
        mock_get.return_value = [{'mean': 150, 'date': '2024-01-01'}]

        api.get_item_history(123)

        mock_get.assert_called_once_with("history", params={
            'league': 'Standard',
            'id': 123
        })

    @patch.object(PoeWatchAPI, 'get')
    def test_get_enchants(self, mock_get, api):
        """get_enchants calls correct endpoint."""
        mock_get.return_value = [{'name': 'Enchant', 'value': 100}]

        api.get_enchants(456)

        mock_get.assert_called_once_with("enchants", params={
            'league': 'Standard',
            'id': 456
        })

    @patch.object(PoeWatchAPI, 'get')
    def test_get_enchants_handles_error(self, mock_get, api):
        """get_enchants returns empty list on error."""
        mock_get.side_effect = Exception("API error")

        result = api.get_enchants(456)

        assert result == []

    @patch.object(PoeWatchAPI, 'get')
    def test_get_corruptions(self, mock_get, api):
        """get_corruptions calls correct endpoint."""
        mock_get.return_value = [{'name': 'Corruption', 'mean': 50}]

        api.get_corruptions(789)

        mock_get.assert_called_once_with("corruptions", params={
            'league': 'Standard',
            'id': 789
        })

    @patch.object(PoeWatchAPI, 'get')
    def test_get_corruptions_handles_error(self, mock_get, api):
        """get_corruptions returns empty list on error."""
        mock_get.side_effect = Exception("API error")

        result = api.get_corruptions(789)

        assert result == []

    @patch.object(PoeWatchAPI, 'get')
    def test_get_compact_data(self, mock_get, api):
        """get_compact_data calls compact endpoint."""
        mock_get.return_value = {'items': []}

        api.get_compact_data()

        mock_get.assert_called_once_with("compact", params={
            'league': 'Standard'
        })

    @patch.object(PoeWatchAPI, 'get')
    def test_get_status(self, mock_get, api):
        """get_status calls status endpoint."""
        mock_get.return_value = {'changeID': '123', 'requestedStashes': 100}

        api.get_status()

        mock_get.assert_called_once_with("status")


# ============================================================================
# Load All Prices Tests
# ============================================================================

class TestLoadAllPrices:
    """Tests for load_all_prices method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__'):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            api._item_cache = {}
            api._category_cache = None
            api.request_count = 0
            return api

    @patch.object(PoeWatchAPI, 'get_compact_data')
    def test_load_all_prices_organizes_by_category(self, mock_compact, api):
        """load_all_prices organizes items by category."""
        mock_compact.return_value = {
            'items': [
                {'name': 'Divine Orb', 'category': 'currency'},
                {'name': 'Exalted Orb', 'category': 'currency'},
                {'name': 'Headhunter', 'category': 'unique'},
            ]
        }

        result = api.load_all_prices()

        assert 'currency' in result
        assert 'unique' in result
        assert 'divine orb' in result['currency']
        assert 'headhunter' in result['unique']

    @patch.object(PoeWatchAPI, 'get_compact_data')
    def test_load_all_prices_lowercase_keys(self, mock_compact, api):
        """load_all_prices uses lowercase item names as keys."""
        mock_compact.return_value = {
            'items': [
                {'name': 'Divine Orb', 'category': 'currency'},
            ]
        }

        result = api.load_all_prices()

        assert 'divine orb' in result['currency']
        assert 'Divine Orb' not in result['currency']

    @patch.object(PoeWatchAPI, 'get_compact_data')
    def test_load_all_prices_handles_error(self, mock_compact, api):
        """load_all_prices returns empty dict on error."""
        mock_compact.side_effect = Exception("Network error")

        result = api.load_all_prices()

        assert result == {}

    @patch.object(PoeWatchAPI, 'get_compact_data')
    def test_load_all_prices_skips_empty_names(self, mock_compact, api):
        """load_all_prices skips items with empty names."""
        mock_compact.return_value = {
            'items': [
                {'name': '', 'category': 'currency'},
                {'name': 'Divine Orb', 'category': 'currency'},
            ]
        }

        result = api.load_all_prices()

        assert '' not in result.get('currency', {})
        assert len(result['currency']) == 1

    @patch.object(PoeWatchAPI, 'get_compact_data')
    def test_load_all_prices_unknown_category(self, mock_compact, api):
        """load_all_prices handles items with unknown category."""
        mock_compact.return_value = {
            'items': [
                {'name': 'Mystery Item'},  # No category
            ]
        }

        result = api.load_all_prices()

        assert 'unknown' in result
        assert 'mystery item' in result['unknown']


# ============================================================================
# Find Item Price Tests
# ============================================================================

class TestFindItemPrice:
    """Tests for find_item_price method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__'):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            api._item_cache = {}
            api._category_cache = None
            api.request_count = 0
            return api

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_basic(self, mock_search, api):
        """find_item_price returns item data."""
        mock_search.return_value = [
            {'name': 'Divine Orb', 'mean': 150, 'daily': 1000}
        ]

        result = api.find_item_price("Divine Orb")

        assert result is not None
        assert result['name'] == 'Divine Orb'
        assert result['mean'] == 150

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_no_results(self, mock_search, api):
        """find_item_price returns None when no results."""
        mock_search.return_value = []

        result = api.find_item_price("Nonexistent Item")

        assert result is None

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_handles_error(self, mock_search, api):
        """find_item_price returns None on error."""
        mock_search.side_effect = Exception("API error")

        result = api.find_item_price("Divine Orb")

        assert result is None

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_gem_level_filter(self, mock_search, api):
        """find_item_price filters by gem level."""
        mock_search.return_value = [
            {'name': 'Vaal Grace', 'gemLevel': 20, 'mean': 100},
            {'name': 'Vaal Grace', 'gemLevel': 21, 'mean': 500},
        ]

        result = api.find_item_price("Vaal Grace", rarity="GEM", gem_level=21)

        assert result['gemLevel'] == 21
        assert result['mean'] == 500

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_gem_quality_filter(self, mock_search, api):
        """find_item_price filters by gem quality."""
        mock_search.return_value = [
            {'name': 'Vaal Grace', 'gemQuality': 0, 'mean': 50},
            {'name': 'Vaal Grace', 'gemQuality': 23, 'mean': 200},
        ]

        result = api.find_item_price("Vaal Grace", rarity="GEM", gem_quality=23)

        assert result['gemQuality'] == 23

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_corrupted_filter(self, mock_search, api):
        """find_item_price filters by corruption status."""
        mock_search.return_value = [
            {'name': 'Vaal Grace', 'gemIsCorrupted': False, 'mean': 50},
            {'name': 'Vaal Grace', 'gemIsCorrupted': True, 'mean': 100},
        ]

        result = api.find_item_price("Vaal Grace", rarity="GEM", corrupted=True)

        assert result['gemIsCorrupted'] is True

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_links_filter(self, mock_search, api):
        """find_item_price filters by link count."""
        mock_search.return_value = [
            {'name': 'Carcass Jack', 'linkCount': 0, 'mean': 50},
            {'name': 'Carcass Jack', 'linkCount': 6, 'mean': 500},
        ]

        result = api.find_item_price("Carcass Jack", links=6)

        assert result['linkCount'] == 6
        assert result['mean'] == 500

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_returns_highest_mean(self, mock_search, api):
        """find_item_price returns item with highest mean price."""
        mock_search.return_value = [
            {'name': 'Test Item', 'mean': 100},
            {'name': 'Test Item', 'mean': 500},
            {'name': 'Test Item', 'mean': 200},
        ]

        result = api.find_item_price("Test Item")

        assert result['mean'] == 500

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_fallback_to_first(self, mock_search, api):
        """find_item_price falls back to first result if no filter matches."""
        mock_search.return_value = [
            {'name': 'Test Item', 'linkCount': 0, 'mean': 50},
        ]

        # Request 6L but none available - should fall back
        result = api.find_item_price("Test Item", links=6)

        # Falls back to first result since no 6L found
        assert result is not None
        assert result['mean'] == 50


# ============================================================================
# Get Item With Confidence Tests
# ============================================================================

class TestGetItemWithConfidence:
    """Tests for get_item_with_confidence method."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__'):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            api._item_cache = {}
            api._category_cache = None
            api.request_count = 0
            return api

    @patch.object(PoeWatchAPI, 'find_item_price')
    def test_high_confidence(self, mock_find, api):
        """High confidence when lowConfidence=False and daily > 10."""
        mock_find.return_value = {
            'name': 'Divine Orb',
            'mean': 150,
            'daily': 1000,
            'lowConfidence': False
        }

        result = api.get_item_with_confidence("Divine Orb")

        assert result['confidence'] == 'high'

    @patch.object(PoeWatchAPI, 'find_item_price')
    def test_medium_confidence(self, mock_find, api):
        """Medium confidence when lowConfidence=False but daily <= 10."""
        mock_find.return_value = {
            'name': 'Rare Item',
            'mean': 50,
            'daily': 5,
            'lowConfidence': False
        }

        result = api.get_item_with_confidence("Rare Item")

        assert result['confidence'] == 'medium'

    @patch.object(PoeWatchAPI, 'find_item_price')
    def test_low_confidence(self, mock_find, api):
        """Low confidence when lowConfidence=True."""
        mock_find.return_value = {
            'name': 'Very Rare Item',
            'mean': 1000,
            'daily': 500,  # Even high daily doesn't matter
            'lowConfidence': True
        }

        result = api.get_item_with_confidence("Very Rare Item")

        assert result['confidence'] == 'low'

    @patch.object(PoeWatchAPI, 'find_item_price')
    def test_returns_none_when_not_found(self, mock_find, api):
        """Returns None when item not found."""
        mock_find.return_value = None

        result = api.get_item_with_confidence("Nonexistent")

        assert result is None

    @patch.object(PoeWatchAPI, 'find_item_price')
    def test_handles_missing_daily(self, mock_find, api):
        """Handles missing daily field."""
        mock_find.return_value = {
            'name': 'Item',
            'mean': 50,
            'lowConfidence': False
            # No 'daily' field
        }

        result = api.get_item_with_confidence("Item")

        # daily defaults to 0, so medium confidence
        assert result['confidence'] == 'medium'

    @patch.object(PoeWatchAPI, 'find_item_price')
    def test_passes_kwargs_to_find(self, mock_find, api):
        """Passes kwargs to find_item_price."""
        mock_find.return_value = {
            'name': 'Gem',
            'mean': 100,
            'daily': 50,
            'lowConfidence': False
        }

        api.get_item_with_confidence("Gem", rarity="GEM", gem_level=21)

        mock_find.assert_called_once_with("Gem", rarity="GEM", gem_level=21)


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def api(self):
        """Create mock API instance."""
        with patch('data_sources.pricing.poe_watch.BaseAPIClient.__init__'):
            api = PoeWatchAPI.__new__(PoeWatchAPI)
            api.league = "Standard"
            api._item_cache = {}
            api._category_cache = None
            api.request_count = 0
            return api

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_handles_none_mean(self, mock_search, api):
        """Handles items with None mean value."""
        mock_search.return_value = [
            {'name': 'Item1', 'mean': None},
            {'name': 'Item2', 'mean': 100},
        ]

        result = api.find_item_price("Item")

        # Should handle None gracefully
        assert result is not None
        assert result['mean'] == 100

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_handles_string_mean(self, mock_search, api):
        """Handles items with string mean value."""
        mock_search.return_value = [
            {'name': 'Item', 'mean': "150.5"},
        ]

        result = api.find_item_price("Item")

        # Should handle string via float conversion
        assert result is not None

    @patch.object(PoeWatchAPI, 'get')
    def test_league_used_in_requests(self, mock_get, api):
        """League is included in API requests."""
        api.league = "Keepers"
        mock_get.return_value = []

        api.get_items_by_category("currency")

        call_params = mock_get.call_args[1]['params']
        assert call_params['league'] == "Keepers"

    def test_cache_key_handles_none_params(self, api):
        """Cache key handles None params."""
        key = api._get_cache_key("endpoint", None)

        assert key == "endpoint::::"

    @patch.object(PoeWatchAPI, 'get_compact_data')
    def test_load_all_prices_handles_missing_items_key(self, mock_compact, api):
        """Handles compact response without 'items' key."""
        mock_compact.return_value = {}  # Missing 'items'

        result = api.load_all_prices()

        assert result == {}

    @patch.object(PoeWatchAPI, 'search_items')
    def test_find_item_price_case_insensitive_rarity(self, mock_search, api):
        """Rarity check is case insensitive."""
        mock_search.return_value = [
            {'name': 'Vaal Grace', 'gemLevel': 21, 'mean': 500},
        ]

        # lowercase "gem" should still work
        result = api.find_item_price("Vaal Grace", rarity="gem", gem_level=21)

        assert result is not None
        assert result['gemLevel'] == 21
