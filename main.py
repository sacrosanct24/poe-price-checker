# main.py
from __future__ import annotations

import argparse
import logging

from core.logging_setup import setup_logging
from core.app_context import create_app_context


def main() -> None:
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PoE Price Checker")
    parser.add_argument(
        "--qt",
        action="store_true",
        help="Use PyQt6 GUI (default)",
    )
    parser.add_argument(
        "--tk",
        action="store_true",
        help="Use legacy tkinter GUI",
    )
    args = parser.parse_args()

    # Initialize logging once for the whole app
    setup_logging()
    logging.getLogger(__name__).info("Starting PoE Price Checker GUI")

    # This MUST return an object with .price_service on it
    ctx = create_app_context()

    # Sanity check (helps debug if it's still not wired)
    if not hasattr(ctx, "price_service"):
        raise RuntimeError("AppContext is missing price_service – check core.app_context.create_app_context")

    # Select GUI framework
    use_qt = args.qt or not args.tk  # Default to Qt now

    if use_qt:
        try:
            from gui_qt.main_window import run
            logging.getLogger(__name__).info("Using PyQt6 GUI")
        except ImportError as e:
            logging.getLogger(__name__).warning(f"PyQt6 not available: {e}, falling back to tkinter")
            from gui.main_window import run
    else:
        from gui.main_window import run
        logging.getLogger(__name__).info("Using tkinter GUI")

    run(ctx)


if __name__ == "__main__":
    main()
