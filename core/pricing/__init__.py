"""
Pricing Package.

Provides price checking services for Path of Exile items.

Public API:
- PriceService: Main service for price lookups
- PriceExplanation: Structured explanation for price results
- ItemPriceCache: LRU cache for recently checked items
- get_item_price_cache: Get global cache instance

Example:
    from core.pricing import PriceService, PriceExplanation
    service = PriceService(config, parser, db, poe_ninja)
    results = service.check_item(item_text)
"""
from core.pricing.models import PriceExplanation
from core.pricing.service import PriceService
from core.pricing.cache import (
    ItemPriceCache,
    CacheStats,
    get_item_price_cache,
    clear_item_price_cache,
)

__all__ = [
    "PriceService",
    "PriceExplanation",
    "ItemPriceCache",
    "CacheStats",
    "get_item_price_cache",
    "clear_item_price_cache",
]
