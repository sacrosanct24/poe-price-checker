"""
gui_qt.services.system_tray_manager - System tray management.

Handles system tray icon, notifications, and minimize-to-tray functionality.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class SystemTrayManager(QObject):
    """
    Manages system tray icon and notifications.

    Features:
    - System tray icon with context menu
    - Minimize to tray on window minimize
    - System notifications for price alerts
    - Restore window on tray icon click

    Signals:
        show_requested: Emitted when user requests to show the main window
        quit_requested: Emitted when user requests to quit via tray menu
        settings_requested: Emitted when user requests settings via tray menu
    """

    show_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QMainWindow] = None,
        app_name: str = "PoE Price Checker",
        icon: Optional[QIcon] = None,
    ):
        """
        Initialize the system tray manager.

        Args:
            parent: Parent window (main window)
            app_name: Application name for notifications
            icon: Application icon for tray
        """
        super().__init__(parent)
        self._parent = parent
        self._app_name = app_name
        self._icon = icon or self._get_default_icon()

        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._context_menu: Optional[QMenu] = None
        self._is_initialized = False

        # Menu actions for external access
        self._show_action: Optional[QAction] = None
        self._settings_action: Optional[QAction] = None
        self._quit_action: Optional[QAction] = None

    def _get_default_icon(self) -> QIcon:
        """Get the default application icon."""
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            icon = app.windowIcon()
            if not icon.isNull():
                return icon
        return QIcon()

    def initialize(self) -> bool:
        """
        Initialize the system tray.

        Returns:
            True if system tray is available and initialized, False otherwise.
        """
        if self._is_initialized:
            return True

        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this platform")
            return False

        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self._icon, self._parent)
        self._tray_icon.setToolTip(self._app_name)

        # Create context menu
        self._create_context_menu()

        # Connect signals
        self._tray_icon.activated.connect(self._on_tray_activated)

        # Show the tray icon
        self._tray_icon.show()
        self._is_initialized = True

        logger.info("System tray initialized successfully")
        return True

    def _create_context_menu(self) -> None:
        """Create the tray icon context menu."""
        self._context_menu = QMenu()

        # Show/Restore action
        self._show_action = QAction("Show Window", self._context_menu)
        self._show_action.triggered.connect(self._on_show_triggered)
        self._context_menu.addAction(self._show_action)

        self._context_menu.addSeparator()

        # Settings action
        self._settings_action = QAction("Settings...", self._context_menu)
        self._settings_action.triggered.connect(self._on_settings_triggered)
        self._context_menu.addAction(self._settings_action)

        self._context_menu.addSeparator()

        # Quit action
        self._quit_action = QAction("Quit", self._context_menu)
        self._quit_action.triggered.connect(self._on_quit_triggered)
        self._context_menu.addAction(self._quit_action)

        if self._tray_icon:
            self._tray_icon.setContextMenu(self._context_menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - toggle window visibility
            self._toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click - show window
            self._show_window()

    def _toggle_window(self) -> None:
        """Toggle main window visibility."""
        if self._parent:
            if self._parent.isVisible() and not self._parent.isMinimized():
                self._parent.hide()
                self._update_show_action_text("Show Window")
            else:
                self._show_window()

    def _show_window(self) -> None:
        """Show and activate the main window."""
        if self._parent:
            self._parent.show()
            self._parent.showNormal()
            self._parent.activateWindow()
            self._parent.raise_()
            self._update_show_action_text("Hide Window")
        self.show_requested.emit()

    def _update_show_action_text(self, text: str) -> None:
        """Update the show action text."""
        if self._show_action:
            self._show_action.setText(text)

    def _on_show_triggered(self) -> None:
        """Handle show action triggered."""
        self._show_window()

    def _on_settings_triggered(self) -> None:
        """Handle settings action triggered."""
        self._show_window()
        self.settings_requested.emit()

    def _on_quit_triggered(self) -> None:
        """Handle quit action triggered."""
        self.quit_requested.emit()

    def show_notification(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 5000,
    ) -> bool:
        """
        Show a system tray notification.

        Args:
            title: Notification title
            message: Notification message
            icon: Notification icon type
            duration_ms: How long to show notification (milliseconds)

        Returns:
            True if notification was shown, False otherwise.
        """
        if not self._is_initialized or not self._tray_icon:
            logger.debug("Cannot show notification - tray not initialized")
            return False

        if not self._tray_icon.supportsMessages():
            logger.debug("System tray does not support messages")
            return False

        self._tray_icon.showMessage(title, message, icon, duration_ms)
        logger.debug(f"Tray notification shown: {title}")
        return True

    def show_price_alert(
        self,
        item_name: str,
        price_chaos: float,
        price_divine: Optional[float] = None,
    ) -> bool:
        """
        Show a price alert notification.

        Args:
            item_name: Name of the item
            price_chaos: Price in chaos orbs
            price_divine: Optional price in divine orbs

        Returns:
            True if notification was shown, False otherwise.
        """
        # Build message
        if price_divine and price_divine >= 1:
            price_str = f"{price_divine:.1f} div ({price_chaos:.0f}c)"
        else:
            price_str = f"{price_chaos:.0f}c"

        message = f"{item_name}\nValue: {price_str}"

        return self.show_notification(
            title="High Value Item Found!",
            message=message,
            icon=QSystemTrayIcon.MessageIcon.Information,
            duration_ms=7000,
        )

    def hide_to_tray(self) -> None:
        """Hide the main window to system tray."""
        if self._parent and self._is_initialized:
            self._parent.hide()
            self._update_show_action_text("Show Window")

            # Show a brief notification on first minimize
            # (disabled for now to avoid being annoying)
            # self.show_notification(
            #     self._app_name,
            #     "Minimized to system tray",
            #     QSystemTrayIcon.MessageIcon.Information,
            #     2000,
            # )

    def set_icon(self, icon: QIcon) -> None:
        """Update the tray icon."""
        self._icon = icon
        if self._tray_icon:
            self._tray_icon.setIcon(icon)

    def set_tooltip(self, tooltip: str) -> None:
        """Update the tray icon tooltip."""
        if self._tray_icon:
            self._tray_icon.setToolTip(tooltip)

    def update_tooltip_with_stats(
        self,
        items_checked: int = 0,
        pending_sales: int = 0,
    ) -> None:
        """
        Update tooltip with current statistics.

        Args:
            items_checked: Number of items checked today
            pending_sales: Number of pending sales
        """
        tooltip = self._app_name
        if items_checked or pending_sales:
            parts = []
            if items_checked:
                parts.append(f"{items_checked} checked")
            if pending_sales:
                parts.append(f"{pending_sales} pending")
            tooltip += f"\n{', '.join(parts)}"
        self.set_tooltip(tooltip)

    def add_recent_item(self, item_name: str, callback: Callable[[], None]) -> None:
        """
        Add a recent item to the context menu.

        Args:
            item_name: Name of the item to display
            callback: Function to call when item is clicked
        """
        if not self._context_menu or not self._show_action:
            return

        # Find or create "Recent Items" submenu
        recent_menu = None
        for action in self._context_menu.actions():
            menu = action.menu()
            if menu and action.text() == "Recent Items":
                recent_menu = menu
                break

        if not recent_menu:
            # Insert before separator
            recent_menu = QMenu("Recent Items", self._context_menu)
            # Insert after Show Window
            actions = self._context_menu.actions()
            if len(actions) > 1:
                self._context_menu.insertMenu(actions[1], recent_menu)

        # Add item (limit to 5 recent items)
        if recent_menu.actions().__len__() >= 5:
            recent_menu.removeAction(recent_menu.actions()[-1])

        action = QAction(item_name[:30] + "..." if len(item_name) > 30 else item_name)
        action.triggered.connect(callback)
        recent_menu.insertAction(
            recent_menu.actions()[0] if recent_menu.actions() else None,
            action,
        )

    def is_available(self) -> bool:
        """Check if system tray is available."""
        return QSystemTrayIcon.isSystemTrayAvailable()

    def is_initialized(self) -> bool:
        """Check if tray manager is initialized."""
        return self._is_initialized

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None
        self._is_initialized = False
        logger.info("System tray cleaned up")
