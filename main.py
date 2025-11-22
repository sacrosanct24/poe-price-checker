# main.py
from __future__ import annotations

import logging

from core.logging_setup import setup_logging
from core.app_context import create_app_context
from gui.main_window import run


def main() -> None:
    # Initialize logging once for the whole app
    setup_logging()
    logging.getLogger(__name__).info("Starting PoE Price Checker GUI")

    # This MUST return an object with .price_service on it
    ctx = create_app_context()

    # Sanity check (helps debug if it's still not wired)
    if not hasattr(ctx, "price_service"):
        raise RuntimeError("AppContext is missing price_service – check core.app_context.create_app_context")

    run(ctx)


if __name__ == "__main__":
    main()
