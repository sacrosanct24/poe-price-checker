"""
gui_qt.controllers.tray_controller - System tray functionality controller.

Extracts system tray logic from main_window.py:
- Tray initialization and callbacks
- Minimize to tray behavior
- Price alert notifications

Usage:
    controller = TrayController(parent=main_window, ctx=app_context)
    controller.initialize()
    controller.maybe_show_alert(price_data)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow

if TYPE_CHECKING:
    from gui_qt.services.system_tray import SystemTrayManager
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class TrayController:
    """
    Controller for system tray functionality.

    Handles:
    - System tray initialization
    - Minimize to tray behavior
    - Price alert notifications
    - Quit from tray menu
    """

    def __init__(
        self,
        parent: QMainWindow,
        ctx: "AppContext",
        on_settings: Optional[Callable[[], None]] = None,
        on_cleanup: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the tray controller.

        Args:
            parent: Parent main window.
            ctx: Application context with config.
            on_settings: Callback to show settings dialog.
            on_cleanup: Callback for cleanup before quit.
        """
        self._parent = parent
        self._ctx = ctx
        self._on_settings = on_settings
        self._on_cleanup = on_cleanup

        self._tray_manager: Optional["SystemTrayManager"] = None

    def initialize(self) -> bool:
        """
        Initialize the system tray icon and notifications.

        Returns:
            True if system tray was successfully initialized.
        """
        from gui_qt.services import SystemTrayManager

        self._tray_manager = SystemTrayManager(
            parent=self._parent,
            app_name="PoE Price Checker",
            icon=self._parent.windowIcon(),
        )

        if self._tray_manager.initialize():
            # Connect signals
            self._tray_manager.quit_requested.connect(self._quit_application)
            if self._on_settings:
                self._tray_manager.settings_requested.connect(self._on_settings)
            logger.info("System tray initialized")
            return True
        else:
            logger.warning("System tray not available")
            return False

    def is_initialized(self) -> bool:
        """Check if tray manager is initialized."""
        return self._tray_manager is not None and self._tray_manager.is_initialized()

    def should_minimize_to_tray(self) -> bool:
        """Check if we should minimize to tray based on config."""
        if not self.is_initialized():
            return False

        config = getattr(self._ctx, 'config', None)
        if config:
            return config.minimize_to_tray
        return True

    def hide_to_tray(self) -> None:
        """Hide the window to the system tray."""
        if self._tray_manager:
            self._tray_manager.hide_to_tray()

    def handle_minimize(self) -> bool:
        """
        Handle minimize event - potentially hide to tray.

        Returns:
            True if handled (should hide to tray), False otherwise.
        """
        if self.should_minimize_to_tray():
            # Use timer to avoid blocking the event
            QTimer.singleShot(0, self.hide_to_tray)
            return True
        return False

    def show_notification(
        self,
        item_name: str,
        price_chaos: float,
        price_divine: Optional[float] = None,
    ) -> None:
        """
        Show a system tray notification for a high-value item.

        Args:
            item_name: Name of the item.
            price_chaos: Price in chaos orbs.
            price_divine: Price in divine orbs (optional).
        """
        if not self.is_initialized():
            return

        config = getattr(self._ctx, 'config', None)
        if config and not config.show_tray_notifications:
            return

        self._tray_manager.show_price_alert(item_name, price_chaos, price_divine)

    def maybe_show_alert(self, data: Any) -> None:
        """
        Show tray notification if item exceeds alert threshold.

        Args:
            data: Price check result data with best_price and parsed_item.
        """
        if not self.is_initialized():
            return

        config = getattr(self._ctx, 'config', None)
        if not config or not config.show_tray_notifications:
            return

        # Get best price from results
        best_price = data.best_price if hasattr(data, 'best_price') else None
        if best_price is None:
            return

        # Check against threshold
        threshold = config.tray_alert_threshold
        if best_price >= threshold:
            # Get item name
            item_name = "Unknown Item"
            if hasattr(data, 'parsed_item') and data.parsed_item:
                item_name = data.parsed_item.name or item_name

            # Get divine value if available
            divine_value = None
            divine_rate = getattr(config, 'divine_chaos_rate', 0)
            if divine_rate and divine_rate > 0:
                divine_value = best_price / divine_rate

            self.show_notification(item_name, best_price, divine_value)

    def cleanup(self) -> None:
        """Clean up tray resources."""
        if self._tray_manager:
            self._tray_manager.cleanup()

    def _quit_application(self) -> None:
        """Quit the application (from tray menu)."""
        if self._on_cleanup:
            self._on_cleanup()
        QApplication.instance().quit()


def get_tray_controller(
    parent: QMainWindow,
    ctx: "AppContext",
    on_settings: Optional[Callable[[], None]] = None,
    on_cleanup: Optional[Callable[[], None]] = None,
) -> TrayController:
    """
    Factory function to create a TrayController.

    Args:
        parent: Parent main window.
        ctx: Application context.
        on_settings: Settings callback.
        on_cleanup: Cleanup callback.

    Returns:
        Configured TrayController instance.
    """
    return TrayController(
        parent=parent,
        ctx=ctx,
        on_settings=on_settings,
        on_cleanup=on_cleanup,
    )
