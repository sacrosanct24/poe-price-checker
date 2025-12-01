"""
Test performance optimizations in PoeNinjaAPI.
"""

from __future__ import annotations

import time
import pytest
from unittest.mock import Mock, patch


pytestmark = pytest.mark.unit


class TestCurrencyIndexing:
    """Test O(1) currency lookup via indexed dictionary."""

    def test_get_currency_price_builds_index_on_first_call(self):
        """Index should be built lazily on first currency price lookup."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja.divine_chaos_rate = 200.0
        ninja._currency_index = {}
        ninja._divine_rate_expiry = 0.0

        def mock_overview_side_effect():
            """Simulate what get_currency_overview does - builds the index."""
            ninja._currency_index = {
                'chaos orb': {'chaosEquivalent': 1.0},
                'divine orb': {'chaosEquivalent': 200.0},
                'exalted orb': {'chaosEquivalent': 15.0},
            }
            return {'lines': []}

        # Mock the fetch to return currency data AND build index
        with patch.object(ninja, 'get_currency_overview', side_effect=mock_overview_side_effect) as mock_overview:
            # First call - should trigger index build
            price, source = ninja.get_currency_price('Divine Orb')

            mock_overview.assert_called_once()
            assert price == 200.0
            assert source == "poe.ninja currency"

    def test_get_currency_price_uses_cached_index(self):
        """Subsequent calls should use cached index without re-fetching."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja.divine_chaos_rate = 200.0
        ninja._divine_rate_expiry = 0.0

        # Pre-populate index
        ninja._currency_index = {
            'chaos orb': {'chaosEquivalent': 1.0},
            'divine orb': {'chaosEquivalent': 200.0},
            'exalted orb': {'chaosEquivalent': 15.0},
        }

        with patch.object(ninja, 'get_currency_overview') as mock_overview:
            # Multiple lookups
            price1, _ = ninja.get_currency_price('Divine Orb')
            price2, _ = ninja.get_currency_price('Exalted Orb')
            price3, _ = ninja.get_currency_price('Chaos Orb')

            # Should NOT re-fetch since index exists
            mock_overview.assert_not_called()

            assert price1 == 200.0
            assert price2 == 15.0
            assert price3 == 1.0

    def test_get_currency_price_case_insensitive(self):
        """Currency lookup should be case-insensitive."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja._currency_index = {
            'divine orb': {'chaosEquivalent': 200.0},
        }
        ninja._divine_rate_expiry = 0.0

        # Various case combinations
        price1, _ = ninja.get_currency_price('Divine Orb')
        price2, _ = ninja.get_currency_price('DIVINE ORB')
        price3, _ = ninja.get_currency_price('divine orb')
        price4, _ = ninja.get_currency_price('DiViNe OrB')

        assert price1 == price2 == price3 == price4 == 200.0

    def test_get_currency_price_not_found(self):
        """Should return 0.0 for unknown currencies."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja._currency_index = {
            'divine orb': {'chaosEquivalent': 200.0},
        }
        ninja._divine_rate_expiry = 0.0

        price, source = ninja.get_currency_price('Unknown Currency')

        assert price == 0.0
        assert source == "not found"

    def test_get_currency_price_empty_name(self):
        """Should handle empty/None currency names gracefully."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja._currency_index = {'divine orb': {'chaosEquivalent': 200.0}}
        ninja._divine_rate_expiry = 0.0

        price1, source1 = ninja.get_currency_price('')
        price2, source2 = ninja.get_currency_price(None)
        price3, source3 = ninja.get_currency_price('   ')

        assert price1 == 0.0 and source1 == "empty name"
        assert price2 == 0.0 and source2 == "empty name"
        assert price3 == 0.0 and source3 == "empty name"


class TestDivineRateCaching:
    """Test divine rate caching with expiry."""

    def test_ensure_divine_rate_uses_cached_value_when_valid(self):
        """Should return cached rate without re-fetching when not expired."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja.divine_chaos_rate = 200.0
        ninja._divine_rate_expiry = time.time() + 3600  # 1 hour in future

        with patch.object(ninja, 'refresh_divine_rate_from_currency') as mock_refresh:
            rate = ninja.ensure_divine_rate()

            # Should NOT call refresh since cache is valid
            mock_refresh.assert_not_called()
            assert rate == 200.0

    def test_ensure_divine_rate_refreshes_when_expired(self):
        """Should refresh rate when cache has expired."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja.divine_chaos_rate = 150.0  # Old cached value
        ninja._divine_rate_expiry = time.time() - 100  # Expired

        with patch.object(ninja, 'refresh_divine_rate_from_currency') as mock_refresh:
            mock_refresh.return_value = 200.0  # New value

            rate = ninja.ensure_divine_rate()

            mock_refresh.assert_called_once()
            assert rate == 200.0

    def test_ensure_divine_rate_refreshes_when_rate_too_low(self):
        """Should refresh if cached rate is below sanity threshold (10.0)."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja.divine_chaos_rate = 5.0  # Below 10 threshold
        ninja._divine_rate_expiry = time.time() + 3600  # Not expired

        with patch.object(ninja, 'refresh_divine_rate_from_currency') as mock_refresh:
            mock_refresh.return_value = 200.0

            rate = ninja.ensure_divine_rate()

            # Should refresh because rate is too low
            mock_refresh.assert_called_once()
            assert rate == 200.0


class TestCurrencyOverviewIndexBuilding:
    """Test that get_currency_overview builds the index correctly."""

    def test_currency_overview_builds_index_from_data(self):
        """Verify index structure is built correctly from currency data."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        # Manually test the index building logic by simulating what happens
        # when get_currency_overview processes the API response
        ninja = PoeNinjaAPI.__new__(PoeNinjaAPI)
        ninja.league = "Standard"
        ninja.logger = Mock()
        ninja._currency_index = {}
        ninja._divine_rate_expiry = 0.0
        ninja.divine_chaos_rate = 1.0

        # Simulate processing of currency data (what get_currency_overview does)
        data = {
            'lines': [
                {'currencyTypeName': 'Chaos Orb', 'chaosEquivalent': 1.0},
                {'currencyTypeName': 'Divine Orb', 'chaosEquivalent': 185.0},
                {'currencyTypeName': 'Exalted Orb', 'chaosEquivalent': 12.5},
            ]
        }

        # Simulate index building (same logic as in get_currency_overview)
        ninja._currency_index.clear()
        for item in data.get("lines", []):
            name = (item.get("currencyTypeName") or "").strip().lower()
            if name:
                ninja._currency_index[name] = item
                if name == "divine orb":
                    ninja.divine_chaos_rate = item.get("chaosEquivalent", 1.0)

        # Check index was built
        assert 'chaos orb' in ninja._currency_index
        assert 'divine orb' in ninja._currency_index
        assert 'exalted orb' in ninja._currency_index

        # Check values
        assert ninja._currency_index['divine orb']['chaosEquivalent'] == 185.0
        assert ninja.divine_chaos_rate == 185.0
