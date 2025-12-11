"""
Top 20 Price Rankings with local caching.

COMPATIBILITY SHIM: This module re-exports from core.rankings for backward compatibility.
New code should import directly from core.rankings.

Provides cached top 20 items by median price for various categories:
- Currency
- Uniques (by slot: weapons, armour, accessories, flasks, jewels)
- Fragments
- Divination Cards
- Essences, Fossils, Scarabs, Oils, Incubators, Vials

Cache is stored locally and only refreshed after 24 hours.
"""

# Re-export everything from the new rankings package for backward compatibility
from core.rankings import (
    # Models
    RankedItem,
    CategoryRanking,
    # Constants
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
    # Cache
    PriceRankingCache,
    # Calculator
    Top20Calculator,
    # History
    PriceRankingHistory,
    # CLI
    print_ranking,
    print_trending,
    cli_main,
    # Convenience functions
    get_rankings_by_group,
    get_top20_rankings,
    get_top20_for_category,
    get_top20_for_slot,
    get_all_slot_rankings,
)

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

if __name__ == "__main__":
    cli_main()
