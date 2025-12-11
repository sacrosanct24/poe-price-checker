"""
core.rankings - Top 20 Price Rankings with local caching.

Provides cached top 20 items by median price for various categories:
- Currency
- Uniques (by slot: weapons, armour, accessories, flasks, jewels)
- Fragments
- Divination Cards
- Essences, Fossils, Scarabs, Oils, Incubators, Vials

Cache is stored locally and only refreshed after 24 hours.

Usage:
    from core.rankings import (
        PriceRankingCache,
        Top20Calculator,
        get_top20_rankings,
        get_top20_for_category,
    )

    # Get all rankings
    rankings = get_top20_rankings(league="Standard")

    # Or use the cache and calculator directly
    cache = PriceRankingCache(league="Standard")
    calculator = Top20Calculator(cache)
    rankings = calculator.refresh_all()
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

# Models
from core.rankings.models import (
    RankedItem,
    CategoryRanking,
)

# Constants
from core.rankings.constants import (
    CACHE_EXPIRY_DAYS,
    SECONDS_PER_DAY,
    CATEGORIES,
    CATEGORY_TO_API_TYPE,
    EQUIPMENT_SLOTS,
    SLOT_DISPLAY_NAMES,
    UNIQUE_CATEGORIES,
    EQUIPMENT_CATEGORIES,
    CONSUMABLE_CATEGORIES,
    CARD_CATEGORIES,
    CATEGORY_TO_RARITY,
    get_rarity_for_category,
)

# Cache
from core.rankings.cache import PriceRankingCache

# Calculator
from core.rankings.calculator import Top20Calculator

# History
from core.rankings.history import PriceRankingHistory

# CLI
from core.rankings.cli import (
    print_ranking,
    print_trending,
    cli_main,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Convenience functions
# =============================================================================

def get_rankings_by_group(
    group: str,
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Dict[str, CategoryRanking]:
    """
    Get rankings for a group of categories.

    Args:
        group: One of "uniques", "equipment", "consumables", "cards", or "all"
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        Dict of category -> CategoryRanking for the specified group
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)

    group_lower = group.lower()

    if group_lower in ("uniques", "equipment"):
        categories = UNIQUE_CATEGORIES
    elif group_lower == "consumables":
        categories = CONSUMABLE_CATEGORIES
    elif group_lower == "cards":
        categories = CARD_CATEGORIES
    elif group_lower == "all":
        return calculator.refresh_all(force=force_refresh)
    else:
        logger.warning(f"Unknown group: {group}, returning all")
        return calculator.refresh_all(force=force_refresh)

    # Refresh only the specified categories
    for category in categories:
        calculator.refresh_category(category, force=force_refresh)

    # Return only the requested categories
    all_rankings = cache.get_all_rankings()
    return {k: v for k, v in all_rankings.items() if k in categories}


def get_top20_rankings(
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Dict[str, CategoryRanking]:
    """
    Convenience function to get top 20 rankings for all categories.

    Args:
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        Dict of category -> CategoryRanking
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_all(force=force_refresh)


def get_top20_for_category(
    category: str,
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Optional[CategoryRanking]:
    """
    Convenience function to get top 20 for a specific category.

    Args:
        category: Category key (e.g., "currency", "unique_weapons")
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        CategoryRanking if successful
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_category(category, force=force_refresh)


def get_top20_for_slot(
    slot: str,
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Optional[CategoryRanking]:
    """
    Convenience function to get top 20 for a specific equipment slot.

    Args:
        slot: Slot key (e.g., "helmet", "body_armour", "sword")
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        CategoryRanking if successful
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_slot(slot, force=force_refresh)


def get_all_slot_rankings(
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Dict[str, CategoryRanking]:
    """
    Convenience function to get top 20 for all equipment slots.

    Args:
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        Dict of slot_key -> CategoryRanking
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_all_slots(force=force_refresh)


__all__ = [
    # Models
    "RankedItem",
    "CategoryRanking",
    # Constants
    "CACHE_EXPIRY_DAYS",
    "SECONDS_PER_DAY",
    "CATEGORIES",
    "CATEGORY_TO_API_TYPE",
    "EQUIPMENT_SLOTS",
    "SLOT_DISPLAY_NAMES",
    "UNIQUE_CATEGORIES",
    "EQUIPMENT_CATEGORIES",
    "CONSUMABLE_CATEGORIES",
    "CARD_CATEGORIES",
    "CATEGORY_TO_RARITY",
    "get_rarity_for_category",
    # Cache
    "PriceRankingCache",
    # Calculator
    "Top20Calculator",
    # History
    "PriceRankingHistory",
    # CLI
    "print_ranking",
    "print_trending",
    "cli_main",
    # Convenience functions
    "get_rankings_by_group",
    "get_top20_rankings",
    "get_top20_for_category",
    "get_top20_for_slot",
    "get_all_slot_rankings",
]
