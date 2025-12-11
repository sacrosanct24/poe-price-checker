"""
Price ranking cache with file-based storage.

Manages cached price rankings stored in JSON format.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from core.rankings.models import CategoryRanking
from core.rankings.constants import (
    CACHE_EXPIRY_DAYS,
    SECONDS_PER_DAY,
    CATEGORIES,
    CATEGORY_TO_API_TYPE,
    EQUIPMENT_SLOTS,
    SLOT_DISPLAY_NAMES,
)

logger = logging.getLogger(__name__)


class PriceRankingCache:
    """
    Manages cached price rankings with file-based storage.

    Rankings are stored in JSON format and refreshed after 24 hours.
    """

    # Re-export constants as class attributes for backward compatibility
    CATEGORIES = CATEGORIES
    CATEGORY_TO_API_TYPE = CATEGORY_TO_API_TYPE
    EQUIPMENT_SLOTS = EQUIPMENT_SLOTS
    SLOT_DISPLAY_NAMES = SLOT_DISPLAY_NAMES

    def __init__(self, cache_dir: Optional[Path] = None, league: str = "Standard"):
        """
        Initialize the price ranking cache.

        Args:
            cache_dir: Directory for cache files. Defaults to ~/.poe_price_checker/
            league: League name for pricing data
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".poe_price_checker"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.league = league
        self._cache_file = self.cache_dir / f"price_rankings_{league.lower().replace(' ', '_')}.json"

        # In-memory cache
        self._rankings: Dict[str, CategoryRanking] = {}
        self._cache_metadata: Dict[str, Any] = {}

        # Load existing cache
        self._load_cache()

        logger.info(f"PriceRankingCache initialized for league: {league}")

    def _load_cache(self) -> None:
        """Load rankings from cache file."""
        if not self._cache_file.exists():
            logger.info("No cache file found, will fetch fresh data")
            return

        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._cache_metadata = data.get("metadata", {})

            for cat_data in data.get("rankings", []):
                ranking = CategoryRanking.from_dict(cat_data)
                self._rankings[ranking.category] = ranking

            logger.info(f"Loaded {len(self._rankings)} category rankings from cache")

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self._rankings = {}
            self._cache_metadata = {}

    def _save_cache(self) -> None:
        """Save rankings to cache file."""
        try:
            data = {
                "metadata": {
                    "league": self.league,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "version": 1,
                },
                "rankings": [ranking.to_dict() for ranking in self._rankings.values()],
            }

            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self._rankings)} category rankings to cache")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def is_cache_valid(self, category: Optional[str] = None) -> bool:
        """
        Check if cache is still valid (not expired).

        Args:
            category: Specific category to check, or None for overall cache

        Returns:
            True if cache is valid and not expired
        """
        if category:
            ranking = self._rankings.get(category)
            if not ranking or not ranking.updated_at:
                return False
            updated_at = ranking.updated_at
        else:
            updated_at_raw = self._cache_metadata.get("last_updated")
            if not updated_at_raw:
                return False
            updated_at = str(updated_at_raw)

        try:
            updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            expiry = updated_dt + timedelta(days=CACHE_EXPIRY_DAYS)
            return datetime.now(timezone.utc) < expiry
        except (ValueError, AttributeError):
            return False

    def get_cache_age_days(self) -> Optional[float]:
        """Get the age of the cache in days."""
        updated_at = self._cache_metadata.get("last_updated")
        if not updated_at:
            return None

        try:
            updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - updated_dt
            return age.total_seconds() / SECONDS_PER_DAY
        except (ValueError, AttributeError):
            return None

    def get_ranking(self, category: str) -> Optional[CategoryRanking]:
        """
        Get cached ranking for a category.

        Args:
            category: Category key (e.g., "currency", "unique_weapons")

        Returns:
            CategoryRanking if cached, None otherwise
        """
        return self._rankings.get(category)

    def get_all_rankings(self) -> Dict[str, CategoryRanking]:
        """Get all cached rankings."""
        return self._rankings.copy()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._rankings = {}
        self._cache_metadata = {}
        if self._cache_file.exists():
            self._cache_file.unlink()
        logger.info("Cache cleared")
