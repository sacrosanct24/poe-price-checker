"""API routers package."""

from api.routers.health import router as health_router
from api.routers.price_check import router as price_check_router
from api.routers.items import router as items_router
from api.routers.sales import router as sales_router
from api.routers.stats import router as stats_router

__all__ = [
    "health_router",
    "price_check_router",
    "items_router",
    "sales_router",
    "stats_router",
]
