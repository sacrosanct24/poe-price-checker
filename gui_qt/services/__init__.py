"""
gui_qt.services - Service layer components for the GUI.

This package contains extracted services that manage application-wide concerns:
- WindowManager: Child window lifecycle management with lazy loading
- SystemTrayManager: System tray icon and notifications
"""

from gui_qt.services.window_manager import WindowManager, get_window_manager
from gui_qt.services.system_tray_manager import SystemTrayManager

__all__ = ["WindowManager", "get_window_manager", "SystemTrayManager"]
