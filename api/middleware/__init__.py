"""API middleware package."""

from api.middleware.error_handling import setup_error_handlers

__all__ = ["setup_error_handlers"]
