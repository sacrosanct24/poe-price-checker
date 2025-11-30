"""
api.routers.price_check - Price checking endpoints.

Provides endpoints for checking item prices across multiple sources.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from api.models import (
    PriceCheckRequest,
    PriceCheckResponse,
    PriceSource,
    ParsedItemInfo,
)
from api.dependencies import get_app_context

if TYPE_CHECKING:
    from core.interfaces import IAppContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/price-check", response_model=PriceCheckResponse)
async def check_price(
    request: PriceCheckRequest,
    ctx: "IAppContext" = Depends(get_app_context),
) -> PriceCheckResponse:
    """
    Check the price of an item.

    Accepts raw item text (from Ctrl+C in game) and returns price information
    from multiple sources including poe.ninja, poe.watch, and trade API.
    """
    try:
        # Parse the item
        item_parser = ctx.item_parser
        parsed_item = item_parser.parse(request.item_text)

        if parsed_item is None:
            return PriceCheckResponse(
                success=False,
                error="Failed to parse item text. Ensure you copied the item correctly.",
                checked_at=datetime.utcnow(),
            )

        # Build parsed item info for response
        item_info = ParsedItemInfo(
            name=parsed_item.name or "Unknown",
            base_type=getattr(parsed_item, 'base_type', None),
            rarity=str(parsed_item.rarity.value) if parsed_item.rarity else None,
            item_level=getattr(parsed_item, 'item_level', None),
            mods=list(parsed_item.mods) if hasattr(parsed_item, 'mods') and parsed_item.mods else [],
            sockets=getattr(parsed_item, 'sockets', None),
            corrupted=getattr(parsed_item, 'corrupted', False),
            influences=list(parsed_item.influences) if hasattr(parsed_item, 'influences') and parsed_item.influences else [],
        )

        # Get prices from service
        price_service = ctx.price_service
        league = request.league or ctx.config.league or "Standard"

        # Call price service
        price_result = price_service.check_item(request.item_text)

        # Convert to response format
        prices: list[PriceSource] = []
        best_price: float | None = None

        if price_result:
            # Handle different result formats
            if hasattr(price_result, 'prices') and price_result.prices:
                for source_name, price_data in price_result.prices.items():
                    chaos_value = None
                    divine_value = None
                    listing_count = None

                    if isinstance(price_data, dict):
                        chaos_value = price_data.get('chaos')
                        divine_value = price_data.get('divine')
                        listing_count = price_data.get('count')
                    elif hasattr(price_data, 'chaos_value'):
                        chaos_value = price_data.chaos_value
                        divine_value = getattr(price_data, 'divine_value', None)
                        listing_count = getattr(price_data, 'listing_count', None)

                    if chaos_value is not None:
                        prices.append(PriceSource(
                            source=source_name,
                            chaos_value=chaos_value,
                            divine_value=divine_value,
                            listing_count=listing_count,
                        ))

                        if best_price is None or chaos_value < best_price:
                            best_price = chaos_value

            # Get explanation if available
            explanation = None
            if hasattr(price_result, 'explanation'):
                explanation = str(price_result.explanation)

        # Save to history
        try:
            from core.game_version import GameVersion
            game_ver = GameVersion(request.game_version.value)
            ctx.database.add_checked_item(
                game_version=game_ver,
                league=league,
                item_name=item_info.name,
                chaos_value=best_price,
                rarity=item_info.rarity,
            )
        except Exception as e:
            logger.warning(f"Failed to save to history: {e}")

        return PriceCheckResponse(
            success=True,
            item=item_info,
            prices=prices,
            best_price=best_price,
            explanation=explanation,
            checked_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.exception(f"Price check failed: {e}")
        return PriceCheckResponse(
            success=False,
            error=f"Price check failed: {str(e)}",
            checked_at=datetime.utcnow(),
        )


@router.post("/parse-item", response_model=ParsedItemInfo)
async def parse_item(
    request: PriceCheckRequest,
    ctx: "IAppContext" = Depends(get_app_context),
) -> ParsedItemInfo:
    """
    Parse item text without checking prices.

    Useful for validating item data before price checking.
    """
    item_parser = ctx.item_parser
    parsed_item = item_parser.parse(request.item_text)

    if parsed_item is None:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse item text. Ensure you copied the item correctly.",
        )

    return ParsedItemInfo(
        name=parsed_item.name or "Unknown",
        base_type=getattr(parsed_item, 'base_type', None),
        rarity=str(parsed_item.rarity.value) if parsed_item.rarity else None,
        item_level=getattr(parsed_item, 'item_level', None),
        mods=list(parsed_item.mods) if hasattr(parsed_item, 'mods') and parsed_item.mods else [],
        sockets=getattr(parsed_item, 'sockets', None),
        corrupted=getattr(parsed_item, 'corrupted', False),
        influences=list(parsed_item.influences) if hasattr(parsed_item, 'influences') and parsed_item.influences else [],
    )
