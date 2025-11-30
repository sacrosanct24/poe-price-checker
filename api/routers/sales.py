"""
api.routers.sales - Sales tracking endpoints.

Provides endpoints for recording and managing item sales.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query

from api.models import (
    SaleCreate,
    SaleUpdate,
    SaleResponse,
    SalesListResponse,
)
from api.dependencies import get_app_context

if TYPE_CHECKING:
    from core.interfaces import IAppContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sales", response_model=SalesListResponse)
async def list_sales(
    ctx: "IAppContext" = Depends(get_app_context),
    status: Optional[str] = Query(
        None,
        description="Filter by status: 'pending' or 'completed'",
        pattern="^(pending|completed)$",
    ),
    limit: int = Query(50, ge=1, le=500, description="Maximum sales to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> SalesListResponse:
    """
    List sales records.

    Returns sales ordered by most recent first.
    Filter by status to see pending (listed) or completed sales.
    """
    try:
        # Get sales from database
        all_sales = ctx.database.get_sales(limit=limit + offset + 100)

        # Apply status filter
        filtered_sales = []
        for sale in all_sales:
            sold_at = getattr(sale, 'sold_at', None)
            is_completed = sold_at is not None

            if status == "pending" and is_completed:
                continue
            if status == "completed" and not is_completed:
                continue

            filtered_sales.append(sale)

        # Apply pagination
        total = len(filtered_sales)
        paginated = filtered_sales[offset : offset + limit]

        # Convert to response models
        response_sales = []
        for sale in paginated:
            response_sales.append(
                SaleResponse(
                    id=getattr(sale, 'id', 0),
                    item_name=getattr(sale, 'item_name', 'Unknown'),
                    listed_price_chaos=getattr(sale, 'listed_price_chaos', 0),
                    actual_price_chaos=getattr(sale, 'actual_price_chaos', None),
                    listed_at=getattr(sale, 'listed_at', datetime.utcnow()),
                    sold_at=getattr(sale, 'sold_at', None),
                    time_to_sale_hours=getattr(sale, 'time_to_sale_hours', None),
                    notes=getattr(sale, 'notes', None),
                )
            )

        return SalesListResponse(
            sales=response_sales,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.exception(f"Failed to list sales: {e}")
        return SalesListResponse(
            sales=[],
            total=0,
            limit=limit,
            offset=offset,
        )


@router.post("/sales", response_model=SaleResponse, status_code=201)
async def create_sale(
    sale: SaleCreate,
    ctx: "IAppContext" = Depends(get_app_context),
) -> SaleResponse:
    """
    Create a new sale listing.

    Records an item as listed for sale at the specified price.
    """
    try:
        # Record the sale
        sale_id = ctx.database.record_sale(
            item_name=sale.item_name,
            listed_price_chaos=sale.listed_price_chaos,
            notes=sale.notes,
        )

        return SaleResponse(
            id=sale_id,
            item_name=sale.item_name,
            listed_price_chaos=sale.listed_price_chaos,
            actual_price_chaos=None,
            listed_at=datetime.utcnow(),
            sold_at=None,
            time_to_sale_hours=None,
            notes=sale.notes,
        )

    except Exception as e:
        logger.exception(f"Failed to create sale: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create sale: {e}")


@router.get("/sales/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int,
    ctx: "IAppContext" = Depends(get_app_context),
) -> SaleResponse:
    """
    Get a specific sale by ID.
    """
    # Find the sale
    sales = ctx.database.get_sales(limit=1000)

    for sale in sales:
        if getattr(sale, 'id', None) == sale_id:
            return SaleResponse(
                id=sale_id,
                item_name=getattr(sale, 'item_name', 'Unknown'),
                listed_price_chaos=getattr(sale, 'listed_price_chaos', 0),
                actual_price_chaos=getattr(sale, 'actual_price_chaos', None),
                listed_at=getattr(sale, 'listed_at', datetime.utcnow()),
                sold_at=getattr(sale, 'sold_at', None),
                time_to_sale_hours=getattr(sale, 'time_to_sale_hours', None),
                notes=getattr(sale, 'notes', None),
            )

    raise HTTPException(status_code=404, detail=f"Sale with ID {sale_id} not found")


@router.put("/sales/{sale_id}", response_model=SaleResponse)
async def update_sale(
    sale_id: int,
    update: SaleUpdate,
    ctx: "IAppContext" = Depends(get_app_context),
) -> SaleResponse:
    """
    Update a sale (typically to mark as sold).

    Set actual_price_chaos to record the final sale price.
    """
    try:
        # Complete the sale
        if update.actual_price_chaos is not None:
            ctx.database.complete_sale(
                sale_id=sale_id,
                actual_price_chaos=update.actual_price_chaos,
            )

        # Get updated sale
        return await get_sale(sale_id, ctx)

    except Exception as e:
        logger.exception(f"Failed to update sale: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update sale: {e}")


@router.delete("/sales/{sale_id}")
async def delete_sale(
    sale_id: int,
    ctx: "IAppContext" = Depends(get_app_context),
) -> dict[str, str]:
    """
    Delete a sale record.
    """
    try:
        if hasattr(ctx.database, 'delete_sale'):
            ctx.database.delete_sale(sale_id)
            return {"status": "deleted", "id": str(sale_id)}
        else:
            raise HTTPException(
                status_code=501,
                detail="Delete operation not supported",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sales/instant", response_model=SaleResponse, status_code=201)
async def record_instant_sale(
    sale: SaleCreate,
    ctx: "IAppContext" = Depends(get_app_context),
) -> SaleResponse:
    """
    Record an instant sale (already sold).

    Useful for recording sales that happened immediately without being listed.
    """
    try:
        # Record as instant sale
        sale_id = ctx.database.record_instant_sale(
            item_name=sale.item_name,
            price_chaos=sale.listed_price_chaos,
            notes=sale.notes,
        )

        now = datetime.utcnow()
        return SaleResponse(
            id=sale_id,
            item_name=sale.item_name,
            listed_price_chaos=sale.listed_price_chaos,
            actual_price_chaos=sale.listed_price_chaos,
            listed_at=now,
            sold_at=now,
            time_to_sale_hours=0,
            notes=sale.notes,
        )

    except Exception as e:
        logger.exception(f"Failed to record instant sale: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record sale: {e}")
