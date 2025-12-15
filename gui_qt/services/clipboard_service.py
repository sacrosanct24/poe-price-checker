"""
Clipboard Service - Global hotkey support for price checking.

Provides system-wide hotkey support for triggering price checks
without requiring the application window to be focused.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from core.clipboard_monitor import ClipboardMonitor, KEYBOARD_AVAILABLE

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class ClipboardService(QObject):
    """
    Qt service wrapper for global hotkey-based clipboard price checking.

    Features:
    - Global hotkey support (works when app is not focused)
    - Configurable hotkey combination
    - Qt signal integration for thread-safe GUI updates
    - Graceful degradation when keyboard module unavailable

    Usage:
        service = ClipboardService(ctx)
        service.hotkey_triggered.connect(on_price_check)
        service.start()
    """

    # Emitted when hotkey is pressed and PoE item is in clipboard
    # Argument: item_text (str) - the raw item text to price check
    hotkey_triggered = pyqtSignal(str)

    # Emitted when hotkey is pressed but no PoE item in clipboard
    no_item_in_clipboard = pyqtSignal()

    # Emitted when service status changes
    status_changed = pyqtSignal(str)

    # Default hotkey if not configured
    DEFAULT_HOTKEY = "ctrl+shift+c"

    def __init__(
        self,
        ctx: "AppContext",
        parent: Optional[QObject] = None,
    ):
        """
        Initialize the clipboard service.

        Args:
            ctx: Application context with config access.
            parent: Parent QObject for lifecycle management.
        """
        super().__init__(parent)

        self._ctx = ctx
        self._monitor: Optional[ClipboardMonitor] = None
        self._hotkey = self.DEFAULT_HOTKEY
        self._enabled = True
        self._is_running = False

        # Load config
        self._load_config()

    def _load_config(self) -> None:
        """Load hotkey settings from config."""
        try:
            config_data = self._ctx.config.data
            shortcuts = config_data.get("shortcuts", {})
            global_hotkeys = shortcuts.get("global_hotkeys", {})

            self._hotkey = global_hotkeys.get("price_check", self.DEFAULT_HOTKEY)
            self._enabled = global_hotkeys.get("enabled", True)

            logger.debug(f"Loaded hotkey config: hotkey={self._hotkey}, enabled={self._enabled}")

        except Exception as e:
            logger.warning(f"Failed to load hotkey config: {e}")

    @property
    def is_available(self) -> bool:
        """Check if global hotkey support is available."""
        return KEYBOARD_AVAILABLE

    @property
    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self._is_running

    @property
    def current_hotkey(self) -> str:
        """Get the currently configured hotkey."""
        return self._hotkey

    def start(self) -> bool:
        """
        Start the clipboard service and register the global hotkey.

        Returns:
            True if started successfully, False otherwise.
        """
        if not self._enabled:
            logger.info("Clipboard service disabled in config")
            self.status_changed.emit("disabled")
            return False

        if not KEYBOARD_AVAILABLE:
            logger.warning("Global hotkeys unavailable - keyboard module not installed")
            self.status_changed.emit("unavailable")
            return False

        if self._is_running:
            logger.debug("Clipboard service already running")
            return True

        try:
            # Create monitor instance
            self._monitor = ClipboardMonitor()

            # Register the hotkey
            success = self._monitor.register_hotkey(
                self._hotkey,
                self._on_hotkey_pressed,
                "Check clipboard item price",
            )

            if success:
                self._is_running = True
                logger.info(f"Clipboard service started with hotkey: {self._hotkey}")
                self.status_changed.emit("running")
                return True
            else:
                logger.error(f"Failed to register hotkey: {self._hotkey}")
                self.status_changed.emit("failed")
                return False

        except Exception as e:
            logger.error(f"Failed to start clipboard service: {e}")
            self.status_changed.emit("error")
            return False

    def stop(self) -> None:
        """Stop the clipboard service and unregister hotkeys."""
        if not self._is_running:
            return

        try:
            if self._monitor:
                self._monitor.cleanup()
                self._monitor = None

            self._is_running = False
            logger.info("Clipboard service stopped")
            self.status_changed.emit("stopped")

        except Exception as e:
            logger.error(f"Error stopping clipboard service: {e}")

    def set_hotkey(self, hotkey: str) -> bool:
        """
        Change the global hotkey.

        Args:
            hotkey: New hotkey combination (e.g., "ctrl+shift+c")

        Returns:
            True if hotkey was changed successfully.
        """
        if not hotkey:
            return False

        was_running = self._is_running

        # Stop current hotkey
        if was_running:
            self.stop()

        # Update config
        self._hotkey = hotkey
        self._save_config()

        # Restart if was running
        if was_running:
            return self.start()

        return True

    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the clipboard service.

        Args:
            enabled: Whether to enable the service.
        """
        self._enabled = enabled
        self._save_config()

        if enabled and not self._is_running:
            self.start()
        elif not enabled and self._is_running:
            self.stop()

    def _save_config(self) -> None:
        """Save current settings to config."""
        try:
            config_data = self._ctx.config.data
            if "shortcuts" not in config_data:
                config_data["shortcuts"] = {}
            if "global_hotkeys" not in config_data["shortcuts"]:
                config_data["shortcuts"]["global_hotkeys"] = {}

            config_data["shortcuts"]["global_hotkeys"]["price_check"] = self._hotkey
            config_data["shortcuts"]["global_hotkeys"]["enabled"] = self._enabled

            self._ctx.config.save()
            logger.debug("Saved hotkey config")

        except Exception as e:
            logger.error(f"Failed to save hotkey config: {e}")

    def _on_hotkey_pressed(self) -> None:
        """Handle global hotkey press - check clipboard for PoE item."""
        if not self._monitor:
            return

        try:
            item_text = self._monitor.check_clipboard_now()

            if item_text:
                logger.info(f"Hotkey triggered - PoE item detected ({len(item_text)} chars)")
                self.hotkey_triggered.emit(item_text)
            else:
                logger.debug("Hotkey triggered - no PoE item in clipboard")
                self.no_item_in_clipboard.emit()

        except Exception as e:
            logger.error(f"Error handling hotkey press: {e}")

    def get_stats(self) -> dict:
        """Get service statistics."""
        stats = {
            "available": KEYBOARD_AVAILABLE,
            "enabled": self._enabled,
            "running": self._is_running,
            "hotkey": self._hotkey,
        }

        if self._monitor:
            stats.update(self._monitor.get_stats())

        return stats


# Singleton management
_instance: Optional[ClipboardService] = None


def get_clipboard_service() -> Optional[ClipboardService]:
    """Get the global clipboard service instance."""
    return _instance


def init_clipboard_service(ctx: "AppContext", parent: Optional[QObject] = None) -> ClipboardService:
    """
    Initialize the global clipboard service.

    Args:
        ctx: Application context.
        parent: Parent QObject.

    Returns:
        The initialized ClipboardService instance.
    """
    global _instance
    if _instance is None:
        _instance = ClipboardService(ctx, parent)
    return _instance


def shutdown_clipboard_service() -> None:
    """Shutdown and cleanup the global clipboard service."""
    global _instance
    if _instance:
        _instance.stop()
        _instance = None
        logger.info("Clipboard service shutdown complete")
