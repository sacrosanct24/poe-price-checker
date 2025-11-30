"""
api.middleware.error_handling - Global error handling for API.

Provides consistent error responses across all endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """Register global error handlers on the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions with consistent format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors with detailed feedback."""
        errors: list[dict[str, Any]] = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "status_code": 422,
                "message": "Validation error",
                "details": errors,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(f"Unexpected error on {request.url.path}: {exc}")

        # Don't expose internal details in production
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "message": "Internal server error",
                "path": str(request.url.path),
            },
        )
