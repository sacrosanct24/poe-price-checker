"""
api.routers.items - Item history endpoints.

Provides endpoints for querying checked item history.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query

from api.models import (
    CheckedItemResponse,
    ItemsListResponse,
    GameVersion,
)
from api.dependencies import get_app_context

if TYPE_CHECKING:
    from core.interfaces import IAppContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/items", response_model=ItemsListResponse)
async def list_items(
    ctx: "IAppContext" = Depends(get_app_context),
    game_version: Optional[GameVersion] = Query(
        None, description="Filter by game version"
    ),
    league: Optional[str] = Query(None, description="Filter by league"),
    rarity: Optional[str] = Query(None, description="Filter by rarity"),
    search: Optional[str] = Query(None, description="Search item names"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ItemsListResponse:
    """
    List checked items from history.

    Returns items ordered by most recently checked first.
    Supports filtering by game version, league, rarity, and item name search.
    """
    try:
        # Get items from database
        from core.game_version import GameVersion as CoreGameVersion

        # Convert game version if provided
        core_game_version = None
        if game_version:
            core_game_version = CoreGameVersion(game_version.value)

        # Get items - database may have different signature
        all_items = ctx.database.get_checked_items(
            limit=limit + offset + 100,  # Get extra for filtering
        )

        # Apply filters
        filtered_items = []
        for item in all_items:
            # Skip if game version doesn't match
            if game_version and getattr(item, 'game_version', None) != game_version.value:
                continue

            # Skip if league doesn't match
            if league and getattr(item, 'league', None) != league:
                continue

            # Skip if rarity doesn't match
            if rarity and getattr(item, 'rarity', None) != rarity:
                continue

            # Skip if search doesn't match
            if search:
                item_name = getattr(item, 'item_name', '') or getattr(item, 'name', '') or ''
                if search.lower() not in item_name.lower():
                    continue

            filtered_items.append(item)

        # Apply pagination
        total = len(filtered_items)
        paginated = filtered_items[offset : offset + limit]

        # Convert to response models
        response_items = []
        for item in paginated:
            # Handle different item formats
            item_id = getattr(item, 'id', 0)
            item_name = getattr(item, 'item_name', None) or getattr(item, 'name', 'Unknown')
            item_game_version = getattr(item, 'game_version', 'poe1')
            item_league = getattr(item, 'league', 'Standard')
            item_chaos = getattr(item, 'chaos_value', None)
            item_divine = getattr(item, 'divine_value', None)
            item_rarity = getattr(item, 'rarity', None)
            checked_at = getattr(item, 'checked_at', None) or datetime.utcnow()

            response_items.append(
                CheckedItemResponse(
                    id=item_id,
                    game_version=str(item_game_version),
                    league=item_league,
                    item_name=item_name,
                    chaos_value=item_chaos,
                    divine_value=item_divine,
                    rarity=item_rarity,
                    checked_at=checked_at,
                )
            )

        return ItemsListResponse(
            items=response_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.exception(f"Failed to list items: {e}")
        return ItemsListResponse(
            items=[],
            total=0,
            limit=limit,
            offset=offset,
        )


@router.get("/items/{item_id}", response_model=CheckedItemResponse)
async def get_item(
    item_id: int,
    ctx: "IAppContext" = Depends(get_app_context),
) -> CheckedItemResponse:
    """
    Get a specific checked item by ID.
    """
    # Try to find item in history
    items = ctx.database.get_checked_items(limit=1000)

    for item in items:
        if getattr(item, 'id', None) == item_id:
            return CheckedItemResponse(
                id=item_id,
                game_version=str(getattr(item, 'game_version', 'poe1')),
                league=getattr(item, 'league', 'Standard'),
                item_name=getattr(item, 'item_name', None) or getattr(item, 'name', 'Unknown'),
                chaos_value=getattr(item, 'chaos_value', None),
                divine_value=getattr(item, 'divine_value', None),
                rarity=getattr(item, 'rarity', None),
                checked_at=getattr(item, 'checked_at', datetime.utcnow()),
            )

    raise HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    ctx: "IAppContext" = Depends(get_app_context),
) -> dict[str, str]:
    """
    Delete a checked item from history.
    """
    try:
        # Check if delete method exists
        if hasattr(ctx.database, 'delete_checked_item'):
            ctx.database.delete_checked_item(item_id)
            return {"status": "deleted", "id": str(item_id)}
        else:
            raise HTTPException(
                status_code=501,
                detail="Delete operation not supported",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
