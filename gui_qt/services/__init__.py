"""
gui_qt.services - Service layer components for the GUI.

This package contains extracted services that manage application-wide concerns:
- WindowManager: Child window lifecycle management with lazy loading
"""

from gui_qt.services.window_manager import WindowManager, get_window_manager

__all__ = ["WindowManager", "get_window_manager"]
