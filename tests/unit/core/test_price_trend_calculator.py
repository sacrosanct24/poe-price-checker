"""Tests for core/price_trend_calculator.py - Price trend calculations."""
import time
from unittest.mock import patch, MagicMock

import pytest

from core.price_trend_calculator import (
    PriceTrend,
    TrendCache,
    PriceTrendCalculator,
    get_trend_calculator,
)


class TestPriceTrend:
    """Tests for PriceTrend dataclass."""

    def test_display_text_positive(self):
        """Positive change should show + and up arrow."""
        trend = PriceTrend(
            change_percent=5.2,
            old_price=100.0,
            new_price=105.2,
            trend="up",
            direction_symbol="^",
            volatility=3.0,
            data_points=7,
        )
        assert "+" in trend.display_text
        assert "5.2%" in trend.display_text
        assert "^" in trend.display_text

    def test_display_text_negative(self):
        """Negative change should show - and down arrow."""
        trend = PriceTrend(
            change_percent=-3.1,
            old_price=100.0,
            new_price=96.9,
            trend="down",
            direction_symbol="v",
            volatility=2.0,
            data_points=5,
        )
        assert "-" in trend.display_text
        assert "3.1%" in trend.display_text

    def test_display_text_zero(self):
        """Zero change should show dash."""
        trend = PriceTrend(
            change_percent=0,
            old_price=100.0,
            new_price=100.0,
            trend="stable",
            direction_symbol="-",
            volatility=0.1,
            data_points=3,
        )
        assert trend.display_text == "-"

    def test_tooltip_contains_all_info(self):
        """Tooltip should contain trend details."""
        trend = PriceTrend(
            change_percent=10.5,
            old_price=100.0,
            new_price=110.5,
            trend="up",
            direction_symbol="^",
            volatility=5.2,
            data_points=10,
        )
        tooltip = trend.tooltip

        assert "Rising" in tooltip
        assert "110.5" in tooltip  # Current price
        assert "100.0" in tooltip  # Previous price
        assert "+10.5%" in tooltip  # Change
        assert "5.2%" in tooltip  # Volatility
        assert "10 data points" in tooltip


class TestTrendCache:
    """Tests for TrendCache class."""

    def test_set_and_get(self):
        """Cache should store and retrieve values."""
        cache = TrendCache(ttl_seconds=3600)
        trend = PriceTrend(
            change_percent=5.0,
            old_price=100.0,
            new_price=105.0,
            trend="up",
            direction_symbol="^",
            volatility=2.0,
            data_points=5,
        )

        cache.set("item:league:7:", trend)
        retrieved = cache.get("item:league:7:")

        assert retrieved is not None
        assert retrieved.change_percent == 5.0

    def test_get_nonexistent(self):
        """Getting nonexistent key should return None."""
        cache = TrendCache()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        """Expired entries should return None."""
        cache = TrendCache(ttl_seconds=0)  # Immediate expiry
        trend = PriceTrend(
            change_percent=5.0,
            old_price=100.0,
            new_price=105.0,
            trend="up",
            direction_symbol="^",
            volatility=2.0,
            data_points=5,
        )

        cache.set("key", trend)
        time.sleep(0.01)  # Wait for expiry

        assert cache.get("key") is None

    def test_clear_removes_all(self):
        """Clear should remove all entries."""
        cache = TrendCache()
        trend = PriceTrend(
            change_percent=5.0,
            old_price=100.0,
            new_price=105.0,
            trend="up",
            direction_symbol="^",
            volatility=2.0,
            data_points=5,
        )

        cache.set("key1", trend)
        cache.set("key2", trend)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestPriceTrendCalculator:
    """Tests for PriceTrendCalculator class."""

    @pytest.fixture
    def mock_history(self):
        """Create a mock PriceRankingHistory."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def calculator(self, mock_history):
        """Create calculator with mocked history."""
        # Reset singleton for testing
        PriceTrendCalculator._instance = None
        PriceTrendCalculator._cache = TrendCache()

        calc = PriceTrendCalculator()
        calc._history = mock_history
        return calc

    def test_singleton_pattern(self):
        """Calculator should use singleton pattern."""
        PriceTrendCalculator._instance = None
        calc1 = PriceTrendCalculator()
        calc2 = PriceTrendCalculator()
        assert calc1 is calc2

    def test_get_trend_returns_none_without_history(self):
        """Should return None if history unavailable."""
        PriceTrendCalculator._instance = None
        calc = PriceTrendCalculator()
        calc._history = None

        result = calc.get_trend("Item", "League")
        assert result is None

    def test_get_trend_returns_none_with_insufficient_data(self, calculator, mock_history):
        """Should return None with less than 2 data points."""
        mock_history.get_item_history.return_value = [
            {"chaos_value": 100.0}  # Only 1 entry
        ]

        result = calculator.get_trend("Item", "League")
        assert result is None

    def test_get_trend_calculates_upward(self, calculator, mock_history):
        """Should calculate upward trend correctly."""
        # Entries sorted DESC by date (newest first)
        mock_history.get_item_history.return_value = [
            {"chaos_value": 110.0},  # Newest
            {"chaos_value": 105.0},
            {"chaos_value": 100.0},  # Oldest
        ]

        result = calculator.get_trend("Item", "League")

        assert result is not None
        assert result.trend == "up"
        assert result.change_percent == 10.0  # 110/100 = +10%
        assert result.direction_symbol == "^"
        assert result.new_price == 110.0
        assert result.old_price == 100.0

    def test_get_trend_calculates_downward(self, calculator, mock_history):
        """Should calculate downward trend correctly."""
        mock_history.get_item_history.return_value = [
            {"chaos_value": 90.0},   # Newest
            {"chaos_value": 95.0},
            {"chaos_value": 100.0},  # Oldest
        ]

        result = calculator.get_trend("Item", "League")

        assert result is not None
        assert result.trend == "down"
        assert result.change_percent == -10.0
        assert result.direction_symbol == "v"

    def test_get_trend_calculates_stable(self, calculator, mock_history):
        """Should calculate stable trend for small changes."""
        mock_history.get_item_history.return_value = [
            {"chaos_value": 100.3},  # Newest
            {"chaos_value": 100.0},  # Oldest
        ]

        result = calculator.get_trend("Item", "League")

        assert result is not None
        assert result.trend == "stable"
        assert result.direction_symbol == "-"

    def test_get_trend_calculates_volatility(self, calculator, mock_history):
        """Should calculate volatility from price range."""
        mock_history.get_item_history.return_value = [
            {"chaos_value": 150.0},  # Max
            {"chaos_value": 100.0},  # Min
            {"chaos_value": 120.0},
        ]

        result = calculator.get_trend("Item", "League")

        assert result is not None
        assert result.volatility == 50.0  # (150-100)/100 = 50%

    def test_get_trend_uses_cache(self, calculator, mock_history):
        """Should use cached results."""
        mock_history.get_item_history.return_value = [
            {"chaos_value": 110.0},
            {"chaos_value": 100.0},
        ]

        # First call - should query history
        result1 = calculator.get_trend("Item", "League", days=7)
        assert mock_history.get_item_history.call_count == 1

        # Second call - should use cache
        result2 = calculator.get_trend("Item", "League", days=7)
        assert mock_history.get_item_history.call_count == 1  # Not increased

        assert result1.change_percent == result2.change_percent

    def test_get_trend_filters_zero_prices(self, calculator, mock_history):
        """Should filter out zero/invalid prices."""
        mock_history.get_item_history.return_value = [
            {"chaos_value": 110.0},
            {"chaos_value": 0},  # Invalid
            {"chaos_value": 100.0},
        ]

        result = calculator.get_trend("Item", "League")

        assert result is not None
        assert result.data_points == 2  # Only 2 valid prices

    def test_get_trending_items_empty_without_history(self, calculator):
        """Should return empty list without history."""
        calculator._history = None
        result = calculator.get_trending_items("League", "Currency")
        assert result == []

    def test_get_trending_items_sorted(self, calculator, mock_history):
        """Should return items sorted by absolute change."""
        mock_history.get_trending_items.return_value = [
            {"item_name": "A", "change_percent": 5.0},
            {"item_name": "B", "change_percent": -15.0},  # Highest absolute
            {"item_name": "C", "change_percent": 10.0},
        ]

        result = calculator.get_trending_items("League", "Currency", limit=3)

        assert len(result) == 3
        assert result[0]["item_name"] == "B"  # -15% absolute = 15
        assert result[1]["item_name"] == "C"  # 10% absolute = 10
        assert result[2]["item_name"] == "A"  # 5% absolute = 5

    def test_get_trending_items_respects_limit(self, calculator, mock_history):
        """Should respect limit parameter."""
        mock_history.get_trending_items.return_value = [
            {"item_name": "A", "change_percent": 5.0},
            {"item_name": "B", "change_percent": 10.0},
            {"item_name": "C", "change_percent": 15.0},
        ]

        result = calculator.get_trending_items("League", "Currency", limit=2)
        assert len(result) == 2

    def test_clear_cache(self, calculator):
        """Should clear the cache."""
        calculator._cache.set("key", MagicMock())
        assert calculator._cache.get("key") is not None

        calculator.clear_cache()
        assert calculator._cache.get("key") is None


class TestGetTrendCalculator:
    """Tests for get_trend_calculator function."""

    def test_returns_singleton(self):
        """Should return singleton calculator."""
        PriceTrendCalculator._instance = None
        calc1 = get_trend_calculator()
        calc2 = get_trend_calculator()
        assert calc1 is calc2
