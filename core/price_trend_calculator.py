"""
core.price_trend_calculator - Calculate price trends from historical data.

Provides trend indicators for items based on price history stored in the
PriceRankingHistory database.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PriceTrend:
    """Price trend data for an item."""

    change_percent: float  # Percentage change (e.g., +5.2 or -3.1)
    old_price: float  # Price N days ago
    new_price: float  # Current price
    trend: str  # "up", "down", or "stable"
    direction_symbol: str  # Arrow symbol
    volatility: float  # Price variation in %
    data_points: int  # Number of snapshots used

    @property
    def display_text(self) -> str:
        """Get display text for the trend (e.g., '+5.2%')."""
        if self.change_percent == 0:
            return "-"
        return f"{self.direction_symbol} {self.change_percent:+.1f}%"

    @property
    def tooltip(self) -> str:
        """Get detailed tooltip text."""
        trend_desc = {
            "up": "Rising",
            "down": "Falling",
            "stable": "Stable",
        }.get(self.trend, "Unknown")

        return (
            f"Trend: {trend_desc}\n"
            f"Current: {self.new_price:.1f}c\n"
            f"Previous: {self.old_price:.1f}c\n"
            f"Change: {self.change_percent:+.1f}%\n"
            f"Volatility: {self.volatility:.1f}%\n"
            f"Based on {self.data_points} data points"
        )


class TrendCache:
    """LRU cache for trend calculations with size bounds and TTL."""

    DEFAULT_MAX_SIZE = 1000

    def __init__(self, ttl_seconds: int = 3600, max_size: int = DEFAULT_MAX_SIZE):
        self._cache: Dict[str, tuple[PriceTrend, float]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._access_order: List[str] = []  # Track LRU order

    def get(self, key: str) -> Optional[PriceTrend]:
        """Get cached trend if still valid."""
        if key in self._cache:
            trend, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                # Update LRU order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return trend
            # Expired - remove
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
        return None

    def set(self, key: str, trend: PriceTrend) -> None:
        """Cache a trend calculation with LRU eviction."""
        # Evict oldest if at capacity
        while len(self._cache) >= self._max_size and self._access_order:
            oldest = self._access_order.pop(0)
            self._cache.pop(oldest, None)

        self._cache[key] = (trend, time.time())
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._access_order.clear()

    @property
    def size(self) -> int:
        """Current cache size."""
        return len(self._cache)


class PriceTrendCalculator:
    """
    Calculate price trends from historical snapshots.

    Uses the PriceRankingHistory database to compute trends
    showing how prices have changed over time.
    """

    _instance: Optional["PriceTrendCalculator"] = None
    _cache: TrendCache = TrendCache()

    def __new__(cls):
        """Singleton pattern for shared cache."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._history = None
        return cls._instance

    @property
    def history(self):
        """Lazy-load history database."""
        if self._history is None:
            try:
                from core.price_rankings import PriceRankingHistory

                self._history = PriceRankingHistory()
            except Exception as e:
                logger.warning(f"Failed to initialize PriceRankingHistory: {e}")
                return None
        return self._history

    def get_trend(
        self,
        item_name: str,
        league: str,
        days: int = 7,
        category: Optional[str] = None,
    ) -> Optional[PriceTrend]:
        """
        Get trend indicator for an item.

        Args:
            item_name: Name of the item
            league: League name (e.g., "Standard", "Settlers")
            days: Number of days to look back
            category: Optional category filter

        Returns:
            PriceTrend with change info, or None if insufficient data
        """
        if not self.history:
            return None

        # Check cache
        cache_key = f"{item_name}:{league}:{days}:{category or ''}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            entries = self.history.get_item_history(
                item_name, league, days=days, category=category
            )

            if len(entries) < 2:
                return None

            prices = [e["chaos_value"] for e in entries if e.get("chaos_value", 0) > 0]
            if len(prices) < 2:
                return None

            # entries are sorted DESC by date, so [0] is newest
            newest = prices[0]
            oldest = prices[-1]

            change_pct = ((newest - oldest) / oldest * 100) if oldest > 0 else 0

            # Calculate volatility (price range as % of min)
            min_price = min(prices)
            max_price = max(prices)
            volatility = (
                ((max_price - min_price) / min_price * 100) if min_price > 0 else 0
            )

            # Determine trend direction (with 0.5% threshold for "stable")
            if change_pct > 0.5:
                trend = "up"
                symbol = "^"  # Use ASCII for Windows compatibility
            elif change_pct < -0.5:
                trend = "down"
                symbol = "v"
            else:
                trend = "stable"
                symbol = "-"

            result = PriceTrend(
                change_percent=round(change_pct, 1),
                old_price=round(oldest, 2),
                new_price=round(newest, 2),
                trend=trend,
                direction_symbol=symbol,
                volatility=round(volatility, 1),
                data_points=len(prices),
            )

            self._cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.warning(f"Failed to calculate trend for {item_name}: {e}")
            return None

    def get_trending_items(
        self,
        league: str,
        category: str,
        days: int = 7,
        min_change_percent: float = 5.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top trending items in a category.

        Args:
            league: League name
            category: Item category
            days: Days to look back
            min_change_percent: Minimum change to include
            limit: Maximum items to return

        Returns:
            List of trending items sorted by absolute change
        """
        if not self.history:
            return []

        try:
            trending = self.history.get_trending_items(
                league, category, days=days, min_change_percent=min_change_percent
            )
            return sorted(trending, key=lambda x: abs(x["change_percent"]), reverse=True)[
                :limit
            ]
        except Exception as e:
            logger.warning(f"Failed to get trending items: {e}")
            return []

    def clear_cache(self) -> None:
        """Clear the trend cache."""
        self._cache.clear()


def get_trend_calculator() -> PriceTrendCalculator:
    """Get the singleton trend calculator instance."""
    return PriceTrendCalculator()
