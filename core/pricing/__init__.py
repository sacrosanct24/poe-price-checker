"""
Pricing Package.

Provides price checking services for Path of Exile items.

Public API:
- PriceService: Main service for price lookups
- PriceExplanation: Structured explanation for price results

Example:
    from core.pricing import PriceService, PriceExplanation
    service = PriceService(config, parser, db, poe_ninja)
    results = service.check_item(item_text)
"""
from core.pricing.models import PriceExplanation
from core.pricing.service import PriceService

__all__ = [
    "PriceService",
    "PriceExplanation",
]
