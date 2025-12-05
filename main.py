# main.py
"""
PoE Price Checker - PyQt6 desktop application.

Entry point for the application.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from core.logging_setup import setup_logging


def main() -> None:
    """Main entry point for the PoE Price Checker application."""
    # Initialize logging once for the whole app
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting PoE Price Checker GUI")

    # Initialize Qt app early so we can show loading screen
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon

    # Set Windows AppUserModelID for proper taskbar icon grouping
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "sacrosanct.poe-price-checker.1.0"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set application icon
    app_icon = None
    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)
    else:
        png_path = Path(__file__).parent / "assets" / "icon.png"
        if png_path.exists():
            app_icon = QIcon(str(png_path))
            app.setWindowIcon(app_icon)

    # Show loading screen immediately
    from gui_qt.widgets.loading_screen import LoadingScreen
    loading = LoadingScreen()
    if app_icon:
        loading.set_icon(app_icon)
    loading.set_version("1.5.0")
    loading.show()
    app.processEvents()

    # Phase 1: Configuration
    loading.set_status("Loading configuration...")
    loading.set_progress(5)
    app.processEvents()

    from core.config import Config
    config = Config()

    # Phase 2: Database
    loading.set_status("Connecting to database...")
    loading.set_progress(15)
    app.processEvents()

    from core.database import Database
    db = Database()

    # Phase 3: Item parser
    loading.set_status("Initializing item parser...")
    loading.set_progress(25)
    app.processEvents()

    from core.item_parser import ItemParser
    parser = ItemParser()

    # Phase 4: Pricing services
    loading.set_status("Setting up pricing services...")
    loading.set_progress(35)
    app.processEvents()

    # Create full app context (this does the heavy API initialization)
    loading.set_status("Connecting to poe.ninja...")
    loading.set_progress(45)
    app.processEvents()

    from core.app_context import create_app_context
    ctx = create_app_context()

    loading.set_status("Initializing price service...")
    loading.set_progress(65)
    app.processEvents()

    # Sanity check
    if not hasattr(ctx, "price_service"):
        raise RuntimeError(
            "AppContext is missing price_service – check core.app_context.create_app_context"
        )

    # Phase 5: Main window creation
    loading.set_status("Creating main window...")
    loading.set_progress(80)
    app.processEvents()

    from gui_qt.main_window import PriceCheckerWindow
    window = PriceCheckerWindow(ctx)

    # Complete loading
    loading.set_status("Ready!")
    loading.set_progress(100)
    app.processEvents()

    # Close loading screen and show main window
    loading.close()
    window.showMaximized()

    logger.info("Application ready")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
