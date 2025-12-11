"""
Top 20 price ranking calculator.

Calculates top 20 items by price for each category using PoE Ninja API.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from core.rankings.models import RankedItem, CategoryRanking
from core.rankings.constants import get_rarity_for_category
from core.rankings.cache import PriceRankingCache

logger = logging.getLogger(__name__)


class Top20Calculator:
    """
    Calculates top 20 items by price for each category.

    Uses PoE Ninja API to fetch current prices and ranks items.
    """

    def __init__(self, cache: PriceRankingCache, poe_ninja_api: Any = None):
        """
        Initialize the calculator.

        Args:
            cache: PriceRankingCache instance for storage
            poe_ninja_api: Optional PoeNinjaAPI instance (created if not provided)
        """
        self.cache = cache
        self._api = poe_ninja_api

    @property
    def api(self):
        """Lazy-load PoE Ninja API."""
        if self._api is None:
            from data_sources.pricing.poe_ninja import PoeNinjaAPI
            self._api = PoeNinjaAPI(league=self.cache.league)
        return self._api

    def refresh_all(self, force: bool = False) -> Dict[str, CategoryRanking]:
        """
        Refresh all category rankings.

        Args:
            force: If True, refresh even if cache is valid

        Returns:
            Dict of category -> CategoryRanking
        """
        if not force and self.cache.is_cache_valid():
            age = self.cache.get_cache_age_days()
            logger.info(f"Cache is valid ({age:.1f} days old), skipping refresh")
            return self.cache.get_all_rankings()

        logger.info("Refreshing all price rankings...")

        # Get divine rate for conversions
        divine_rate = self.api.ensure_divine_rate()

        # Refresh each category
        for category in PriceRankingCache.CATEGORIES:
            try:
                self._refresh_category(category, divine_rate)
            except Exception as e:
                logger.error(f"Failed to refresh {category}: {e}")

        # Save to file
        self.cache._save_cache()

        return self.cache.get_all_rankings()

    def refresh_category(self, category: str, force: bool = False) -> Optional[CategoryRanking]:
        """
        Refresh a single category ranking.

        Args:
            category: Category key to refresh
            force: If True, refresh even if cache is valid

        Returns:
            CategoryRanking if successful
        """
        if not force and self.cache.is_cache_valid(category):
            return self.cache.get_ranking(category)

        divine_rate = self.api.ensure_divine_rate()
        ranking = self._refresh_category(category, divine_rate)
        self.cache._save_cache()
        return ranking

    def _refresh_category(self, category: str, divine_rate: float) -> Optional[CategoryRanking]:
        """
        Internal method to refresh a category.

        Args:
            category: Category key
            divine_rate: Current divine/chaos rate for conversions

        Returns:
            CategoryRanking if successful
        """
        api_type = PriceRankingCache.CATEGORY_TO_API_TYPE.get(category)
        display_name = PriceRankingCache.CATEGORIES.get(category, category)

        if not api_type:
            logger.warning(f"Unknown category: {category}")
            return None

        logger.info(f"Fetching top 20 for {display_name}...")

        try:
            if category == "currency":
                items = self._fetch_currency_top20(divine_rate)
            else:
                items = self._fetch_item_top20(api_type, divine_rate, category)

            ranking = CategoryRanking(
                category=category,
                display_name=display_name,
                items=items,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            self.cache._rankings[category] = ranking
            logger.info(f"Got {len(items)} items for {display_name}")
            return ranking

        except Exception as e:
            logger.error(f"Failed to fetch {category}: {e}")
            return None

    def _fetch_currency_top20(self, divine_rate: float) -> List[RankedItem]:
        """Fetch top 20 currency items."""
        data = self.api.get_currency_overview()
        lines = data.get("lines", [])

        # Sort by chaos equivalent value
        sorted_items = sorted(
            lines,
            key=lambda x: float(x.get("chaosEquivalent") or x.get("chaosValue") or 0),
            reverse=True
        )

        items = []
        for i, item in enumerate(sorted_items[:20], start=1):
            chaos_value = float(item.get("chaosEquivalent") or item.get("chaosValue") or 0)
            items.append(RankedItem(
                rank=i,
                name=item.get("currencyTypeName", "Unknown"),
                chaos_value=chaos_value,
                divine_value=chaos_value / divine_rate if divine_rate > 0 else None,
                icon=item.get("icon"),
                rarity="currency",
            ))

        return items

    def _fetch_item_top20(
        self,
        api_type: str,
        divine_rate: float,
        category: str = "",
    ) -> List[RankedItem]:
        """Fetch top 20 items for a given API type."""
        data = self.api._get_item_overview(api_type)
        if not data:
            return []

        lines = data.get("lines", [])

        # Sort by chaos value
        sorted_items = sorted(
            lines,
            key=lambda x: float(x.get("chaosValue") or 0),
            reverse=True
        )

        # Determine rarity from category
        rarity = get_rarity_for_category(category)

        items = []
        for i, item in enumerate(sorted_items[:20], start=1):
            chaos_value = float(item.get("chaosValue") or 0)
            items.append(RankedItem(
                rank=i,
                name=item.get("name", "Unknown"),
                chaos_value=chaos_value,
                divine_value=chaos_value / divine_rate if divine_rate > 0 else None,
                base_type=item.get("baseType"),
                icon=item.get("icon"),
                item_class=item.get("itemClass"),
                rarity=rarity,
            ))

        return items

    def refresh_slot(self, slot: str, force: bool = False) -> Optional[CategoryRanking]:
        """
        Refresh top 20 for a specific equipment slot.

        Args:
            slot: Slot key (e.g., "helmet", "body_armour", "sword")
            force: If True, refresh even if cache is valid

        Returns:
            CategoryRanking if successful
        """
        slot_key = f"slot_{slot}"

        if not force and self.cache.is_cache_valid(slot_key):
            return self.cache.get_ranking(slot_key)

        divine_rate = self.api.ensure_divine_rate()
        ranking = self._refresh_slot(slot, divine_rate)

        if ranking:
            self.cache._save_cache()

        return ranking

    def _refresh_slot(self, slot: str, divine_rate: float) -> Optional[CategoryRanking]:
        """
        Internal method to refresh a slot ranking.

        Args:
            slot: Slot key
            divine_rate: Current divine/chaos rate

        Returns:
            CategoryRanking if successful
        """
        slot_config = PriceRankingCache.EQUIPMENT_SLOTS.get(slot)
        if not slot_config:
            logger.warning(f"Unknown slot: {slot}")
            return None

        api_type, item_types = slot_config
        display_name = PriceRankingCache.SLOT_DISPLAY_NAMES.get(slot, slot.title())

        logger.info(f"Fetching top 20 for {display_name}...")

        try:
            # Convert item_types to expected type (str or List[str])
            item_types_arg = list(item_types) if not isinstance(item_types, str) else item_types
            items = self._fetch_slot_top20(api_type, item_types_arg, divine_rate)

            slot_key = f"slot_{slot}"
            ranking = CategoryRanking(
                category=slot_key,
                display_name=display_name,
                items=items,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            self.cache._rankings[slot_key] = ranking
            logger.info(f"Got {len(items)} items for {display_name}")
            return ranking

        except Exception as e:
            logger.error(f"Failed to fetch slot {slot}: {e}")
            return None

    def _fetch_slot_top20(
        self,
        api_type: str,
        item_types: Union[str, List[str]],
        divine_rate: float,
    ) -> List[RankedItem]:
        """
        Fetch top 20 items filtered by equipment slot (itemType).

        Args:
            api_type: API category (e.g., "UniqueArmour", "UniqueWeapon")
            item_types: Single itemType string or list of itemType strings to filter
            divine_rate: Current divine/chaos rate

        Returns:
            List of top 20 RankedItems
        """
        data = self.api._get_item_overview(api_type)
        if not data:
            return []

        lines = data.get("lines", [])

        # Normalize item_types to a list
        if isinstance(item_types, str):
            type_filter = [item_types]
        else:
            type_filter = item_types

        # Filter by itemType
        filtered = [
            item for item in lines
            if item.get("itemType") in type_filter
        ]

        # Sort by chaos value
        sorted_items = sorted(
            filtered,
            key=lambda x: float(x.get("chaosValue") or 0),
            reverse=True
        )

        items = []
        for i, item in enumerate(sorted_items[:20], start=1):
            chaos_value = float(item.get("chaosValue") or 0)
            items.append(RankedItem(
                rank=i,
                name=item.get("name", "Unknown"),
                chaos_value=chaos_value,
                divine_value=chaos_value / divine_rate if divine_rate > 0 else None,
                base_type=item.get("baseType"),
                icon=item.get("icon"),
                item_class=item.get("itemClass"),
                rarity="unique",  # All equipment slots are unique items
            ))

        return items

    def refresh_all_slots(self, force: bool = False) -> Dict[str, CategoryRanking]:
        """
        Refresh top 20 for all equipment slots.

        Args:
            force: If True, refresh even if cache is valid

        Returns:
            Dict of slot_key -> CategoryRanking
        """
        divine_rate = self.api.ensure_divine_rate()
        results = {}

        for slot in PriceRankingCache.EQUIPMENT_SLOTS:
            ranking = self._refresh_slot(slot, divine_rate)
            if ranking:
                results[ranking.category] = ranking

        self.cache._save_cache()
        return results
