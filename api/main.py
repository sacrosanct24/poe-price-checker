"""
api.main - FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload
    python -m api.main
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    health_router,
    price_check_router,
    items_router,
    sales_router,
    stats_router,
)
from api.middleware import setup_error_handlers

if TYPE_CHECKING:
    from core.interfaces import IAppContext

logger = logging.getLogger(__name__)

# Global app context (initialized at startup)
_app_context: "IAppContext | None" = None


def get_app_context() -> "IAppContext":
    """Get the global app context. Must be called after app startup."""
    if _app_context is None:
        raise RuntimeError("App context not initialized. Server not started?")
    return _app_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global _app_context

    # Startup
    logger.info("Starting PoE Price Checker API...")
    from core.app_context import create_app_context

    _app_context = create_app_context()
    logger.info("App context initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down PoE Price Checker API...")
    if _app_context is not None:
        _app_context.close()
        _app_context = None
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="PoE Price Checker API",
    description="RESTful API for Path of Exile item price checking and tracking",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup error handlers
setup_error_handlers(app)

# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(price_check_router, prefix="/api/v1", tags=["Price Check"])
app.include_router(items_router, prefix="/api/v1", tags=["Items"])
app.include_router(sales_router, prefix="/api/v1", tags=["Sales"])
app.include_router(stats_router, prefix="/api/v1", tags=["Statistics"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "PoE Price Checker API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
