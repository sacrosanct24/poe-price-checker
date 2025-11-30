"""
api.routers.health - Health check endpoints.

Provides endpoints for monitoring service health and status.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from api.models import HealthResponse, ConfigResponse
from api.dependencies import get_app_context

if TYPE_CHECKING:
    from core.interfaces import IAppContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    ctx: "IAppContext" = Depends(get_app_context),
) -> HealthResponse:
    """
    Check API health status.

    Returns the overall health of the service including database connectivity
    and status of individual services.
    """
    services: dict[str, str] = {}

    # Check database
    db_status = "disconnected"
    try:
        # Try a simple query
        ctx.database.get_checked_items(limit=1)
        db_status = "connected"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        db_status = f"error: {str(e)[:50]}"

    services["database"] = db_status

    # Check price service
    try:
        if ctx.price_service is not None:
            services["price_service"] = "available"
        else:
            services["price_service"] = "unavailable"
    except Exception:
        services["price_service"] = "error"

    # Determine overall status
    overall_status = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        database=db_status,
        services=services,
    )


@router.get("/health/ready")
async def readiness_check(
    ctx: "IAppContext" = Depends(get_app_context),
) -> dict[str, str]:
    """
    Kubernetes-style readiness probe.

    Returns 200 if the service is ready to accept traffic.
    """
    try:
        ctx.database.get_checked_items(limit=1)
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {e}")


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Kubernetes-style liveness probe.

    Returns 200 if the service is alive (even if not fully ready).
    """
    return {"status": "alive"}


@router.get("/config", response_model=ConfigResponse)
async def get_config(
    ctx: "IAppContext" = Depends(get_app_context),
) -> ConfigResponse:
    """
    Get current configuration.

    Returns non-sensitive configuration values.
    """
    config = ctx.config
    return ConfigResponse(
        game_version=str(config.game_version.value) if hasattr(config, 'game_version') else "poe1",
        league=config.league or "Standard",
        auto_detect_league=getattr(config, 'auto_detect_league', True),
        cache_ttl_seconds=getattr(config, 'cache_ttl_seconds', 3600),
    )
