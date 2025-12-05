# main.py
"""
PoE Price Checker - PyQt6 desktop application.

Entry point for the application.
"""
from __future__ import annotations

import logging

from core.logging_setup import setup_logging
from core.app_context import create_app_context


def main() -> None:
    """Main entry point for the PoE Price Checker application."""
    # Initialize logging once for the whole app
    setup_logging()
    logging.getLogger(__name__).info("Starting PoE Price Checker GUI")

    # Create application context with all services
    ctx = create_app_context()

    # Sanity check
    if not hasattr(ctx, "price_service"):
        raise RuntimeError(
            "AppContext is missing price_service – check core.app_context.create_app_context"
        )

    # Run the PyQt6 GUI
    from gui_qt.main_window import run
    run(ctx)


if __name__ == "__main__":
    main()
