"""
api.dependencies - FastAPI dependency injection providers.

Provides access to core services through FastAPI's dependency injection system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from core.interfaces import IAppContext


def get_app_context() -> "IAppContext":
    """
    Get the global application context.

    This is the main dependency for accessing all services.
    Must be called after app startup (lifespan context).
    """
    from api.main import get_app_context as _get_ctx

    return _get_ctx()
