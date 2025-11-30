"""
api.routers.stats - Statistics endpoints.

Provides endpoints for aggregated statistics and analytics.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

from fastapi import APIRouter, Depends, Query

from api.models import StatsResponse, DailySummary
from api.dependencies import get_app_context

if TYPE_CHECKING:
    from core.interfaces import IAppContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    ctx: "IAppContext" = Depends(get_app_context),
    days: int = Query(30, ge=1, le=365, description="Statistics period in days"),
) -> StatsResponse:
    """
    Get aggregated statistics for the specified period.

    Returns totals, averages, and daily breakdowns for price checks and sales.
    """
    try:
        # Get stats from database if available
        db = ctx.database

        # Get basic stats
        stats = {}
        if hasattr(db, 'get_stats'):
            stats = db.get_stats(days=days) or {}

        # Get daily summary if available
        daily_data: list[DailySummary] = []
        if hasattr(db, 'get_daily_sales_summary'):
            daily_raw = db.get_daily_sales_summary(days=days) or []
            for day in daily_raw:
                if isinstance(day, dict):
                    daily_data.append(DailySummary(
                        date=day.get('date', ''),
                        total_sales=day.get('total_sales', 0),
                        total_chaos=day.get('total_chaos', 0),
                        avg_time_to_sale=day.get('avg_time_to_sale'),
                    ))
                else:
                    daily_data.append(DailySummary(
                        date=getattr(day, 'date', ''),
                        total_sales=getattr(day, 'total_sales', 0),
                        total_chaos=getattr(day, 'total_chaos', 0),
                        avg_time_to_sale=getattr(day, 'avg_time_to_sale', None),
                    ))

        # Calculate checked items count
        total_checked = 0
        try:
            items = db.get_checked_items(limit=10000)
            # Filter by date
            cutoff = datetime.utcnow() - timedelta(days=days)
            for item in items:
                checked_at = getattr(item, 'checked_at', None)
                if checked_at and checked_at >= cutoff:
                    total_checked += 1
        except Exception:
            pass

        # Calculate sales stats
        total_sales = 0
        total_chaos = 0.0
        top_items: list[dict[str, Any]] = []

        try:
            sales = db.get_sales(limit=10000)
            cutoff = datetime.utcnow() - timedelta(days=days)

            sale_items = []
            for sale in sales:
                sold_at = getattr(sale, 'sold_at', None)
                if sold_at and sold_at >= cutoff:
                    total_sales += 1
                    actual_price = getattr(sale, 'actual_price_chaos', None) or 0
                    total_chaos += actual_price
                    sale_items.append({
                        'item_name': getattr(sale, 'item_name', 'Unknown'),
                        'price': actual_price,
                    })

            # Get top items by price
            sale_items.sort(key=lambda x: x['price'], reverse=True)
            top_items = sale_items[:10]
        except Exception:
            pass

        # Calculate averages
        avg_price = total_chaos / total_sales if total_sales > 0 else None

        # Calculate average time to sale
        avg_time: float | None = None
        try:
            sales = db.get_sales(limit=10000)
            times = []
            for sale in sales:
                time_to_sale = getattr(sale, 'time_to_sale_hours', None)
                if time_to_sale is not None:
                    times.append(time_to_sale)
            if times:
                avg_time = sum(times) / len(times)
        except Exception:
            pass

        # Get divine equivalent if we have exchange rate
        divine_equivalent: float | None = None
        try:
            if hasattr(db, 'get_currency_rate'):
                rate = db.get_currency_rate('divine')
                if rate and rate > 0:
                    divine_equivalent = total_chaos / rate
        except Exception:
            pass

        return StatsResponse(
            period_days=days,
            total_items_checked=total_checked,
            total_sales=total_sales,
            total_chaos_earned=total_chaos,
            total_divine_equivalent=divine_equivalent,
            avg_price_per_sale=avg_price,
            avg_time_to_sale_hours=avg_time,
            daily_summary=daily_data,
            top_items=top_items,
        )

    except Exception as e:
        logger.exception(f"Failed to get stats: {e}")
        return StatsResponse(
            period_days=days,
            total_items_checked=0,
            total_sales=0,
            total_chaos_earned=0,
            daily_summary=[],
            top_items=[],
        )


@router.get("/stats/summary")
async def get_quick_summary(
    ctx: "IAppContext" = Depends(get_app_context),
) -> dict[str, Any]:
    """
    Get a quick summary for dashboard display.

    Returns key metrics without full details.
    """
    try:
        db = ctx.database

        # Get recent activity counts
        items_today = 0
        sales_today = 0
        pending_sales = 0

        today = datetime.utcnow().date()

        try:
            items = db.get_checked_items(limit=1000)
            for item in items:
                checked_at = getattr(item, 'checked_at', None)
                if checked_at and checked_at.date() == today:
                    items_today += 1
        except Exception:
            pass

        try:
            sales = db.get_sales(limit=1000)
            for sale in sales:
                sold_at = getattr(sale, 'sold_at', None)
                if sold_at is None:
                    pending_sales += 1
                elif sold_at.date() == today:
                    sales_today += 1
        except Exception:
            pass

        return {
            "items_checked_today": items_today,
            "sales_completed_today": sales_today,
            "pending_sales": pending_sales,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.exception(f"Failed to get summary: {e}")
        return {
            "items_checked_today": 0,
            "sales_completed_today": 0,
            "pending_sales": 0,
            "error": str(e),
        }
