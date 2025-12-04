"""
gui_qt.services.window_manager - Manages child window lifecycle.

Provides lazy loading and caching of child windows to reduce resource usage
and ensure consistent window state across the application.

Usage:
    manager = get_window_manager()
    manager.set_main_window(main_window)

    # Show a window (creates if needed, shows if hidden)
    manager.show_window("recent_sales", RecentSalesWindow, ctx=app_context)

    # Close all windows on shutdown
    manager.close_all()
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Type, TYPE_CHECKING

from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class WindowManager:
    """
    Manages child window lifecycle with lazy loading and caching.

    Features:
    - Lazy instantiation: Windows are only created when first requested
    - Caching: Windows are reused across multiple show requests
    - Cleanup: Proper cleanup of all windows on application close
    - Factory support: Custom factory functions for complex window creation

    Signals/Slots:
        None - this is a pure service class

    Example:
        manager = WindowManager()
        manager.set_main_window(main_window)

        # Simple window
        manager.show_window("sales", RecentSalesWindow, ctx=ctx)

        # With factory for complex initialization
        def create_pob_window():
            return PoBCharacterWindow(
                character_manager,
                on_profile_selected=callback,
            )
        manager.register_factory("pob_characters", create_pob_window)
        manager.show_window("pob_characters")
    """

    _instance: Optional['WindowManager'] = None

    # Instance attributes - declared for type checking
    _windows: Dict[str, QWidget]
    _factories: Dict[str, Callable[[], QWidget]]
    _main_window: Optional[QMainWindow]

    def __new__(cls) -> 'WindowManager':
        """Singleton pattern - only one window manager per application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._windows = {}
            cls._instance._factories = {}
            cls._instance._main_window = None
        return cls._instance

    def set_main_window(self, window: 'QMainWindow') -> None:
        """Set the main window as parent for child windows."""
        self._main_window = window

    @property
    def main_window(self) -> Optional['QMainWindow']:
        """Get the main window reference."""
        return self._main_window

    def register_factory(
        self,
        window_id: str,
        factory: Callable[[], QWidget]
    ) -> None:
        """
        Register a factory function for creating a window.

        Use this for windows that need complex initialization or
        dependencies that aren't easily passed as kwargs.

        Args:
            window_id: Unique identifier for the window type
            factory: Callable that creates and returns the window
        """
        self._factories[window_id] = factory
        logger.debug(f"Registered factory for window: {window_id}")

    def get_window(
        self,
        window_id: str,
        window_class: Optional[Type[QWidget]] = None,
        **kwargs: Any
    ) -> Optional[QWidget]:
        """
        Get or create a window by ID.

        Args:
            window_id: Unique identifier for the window
            window_class: Class to instantiate if window doesn't exist
            **kwargs: Arguments passed to window constructor

        Returns:
            The window instance, or None if it couldn't be created
        """
        # Return existing window if valid
        if window_id in self._windows:
            window = self._windows[window_id]
            # Check if window was destroyed (e.g., closed with X button)
            try:
                # Accessing any property on destroyed QWidget raises RuntimeError
                _ = window.isVisible()
                return window
            except RuntimeError:
                # Window was destroyed, remove from cache
                del self._windows[window_id]
                logger.debug(f"Window {window_id} was destroyed, recreating")

        # Create new window
        window = self._create_window(window_id, window_class, **kwargs)
        if window:
            self._windows[window_id] = window

        return window

    def _create_window(
        self,
        window_id: str,
        window_class: Optional[Type[QWidget]],
        **kwargs: Any
    ) -> Optional[QWidget]:
        """Create a new window instance."""
        # Try factory first
        if window_id in self._factories:
            try:
                window = self._factories[window_id]()
                logger.info(f"Created window via factory: {window_id}")
                return window
            except Exception as e:
                logger.error(f"Factory failed for {window_id}: {e}")
                return None

        # Fall back to class instantiation
        if window_class is None:
            logger.error(f"No factory or class for window: {window_id}")
            return None

        try:
            # Add parent if not specified
            if 'parent' not in kwargs and self._main_window:
                kwargs['parent'] = self._main_window

            window = window_class(**kwargs)
            logger.info(f"Created window: {window_id} ({window_class.__name__})")
            return window
        except Exception as e:
            logger.error(f"Failed to create window {window_id}: {e}")
            return None

    def show_window(
        self,
        window_id: str,
        window_class: Optional[Type[QWidget]] = None,
        **kwargs: Any
    ) -> Optional[QWidget]:
        """
        Show a window, creating it if necessary.

        Args:
            window_id: Unique identifier for the window
            window_class: Class to instantiate if window doesn't exist
            **kwargs: Arguments passed to window constructor

        Returns:
            The window instance, or None if it couldn't be created
        """
        window = self.get_window(window_id, window_class, **kwargs)
        if window:
            window.show()
            window.raise_()
            window.activateWindow()
        return window

    def hide_window(self, window_id: str) -> bool:
        """
        Hide a window if it exists.

        Returns:
            True if window was hidden, False if not found
        """
        if window_id in self._windows:
            try:
                self._windows[window_id].hide()
                return True
            except RuntimeError:
                # Window was destroyed
                del self._windows[window_id]
        return False

    def close_window(self, window_id: str) -> bool:
        """
        Close and remove a window from the cache.

        Returns:
            True if window was closed, False if not found
        """
        if window_id in self._windows:
            try:
                self._windows[window_id].close()
            except RuntimeError:
                pass  # Already destroyed
            del self._windows[window_id]
            logger.debug(f"Closed window: {window_id}")
            return True
        return False

    def is_visible(self, window_id: str) -> bool:
        """Check if a window is currently visible."""
        if window_id in self._windows:
            try:
                return self._windows[window_id].isVisible()
            except RuntimeError:
                del self._windows[window_id]
        return False

    def close_all(self) -> int:
        """
        Close all managed windows.

        Returns:
            Number of windows closed
        """
        count = 0
        for window_id in list(self._windows.keys()):
            if self.close_window(window_id):
                count += 1
        logger.info(f"Closed {count} managed windows")
        return count

    def get_open_windows(self) -> list[str]:
        """Get list of currently open (visible) window IDs."""
        visible = []
        for window_id in list(self._windows.keys()):
            if self.is_visible(window_id):
                visible.append(window_id)
        return visible

    @classmethod
    def reset_for_testing(cls) -> None:
        """
        Reset the singleton instance for test isolation.

        Call this in test fixtures to ensure tests don't affect each other.
        """
        if cls._instance:
            cls._instance.close_all()
        cls._instance = None
        logger.debug("WindowManager reset for testing")


# Module-level singleton accessor
_window_manager: Optional[WindowManager] = None


def get_window_manager() -> WindowManager:
    """Get the global window manager instance."""
    global _window_manager
    if _window_manager is None:
        _window_manager = WindowManager()
    return _window_manager
