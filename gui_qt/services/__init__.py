"""
gui_qt.services - Service layer components for the GUI.

This package contains extracted services that manage application-wide concerns:
- WindowManager: Child window lifecycle management with lazy loading
- SystemTrayManager: System tray icon and notifications
- HistoryManager: Price check session history with bounded storage
- PriceRefreshService: Background price data refresh
- PriceAlertService: Price alert monitoring and notifications
"""

from gui_qt.services.window_manager import WindowManager, get_window_manager
from gui_qt.services.system_tray_manager import SystemTrayManager
from gui_qt.services.history_manager import HistoryManager, get_history_manager
from gui_qt.services.price_refresh_service import (
    PriceRefreshService,
    get_price_refresh_service,
    shutdown_price_refresh_service,
)
from gui_qt.services.price_alert_service import (
    PriceAlertService,
    get_price_alert_service,
    shutdown_price_alert_service,
)

__all__ = [
    "WindowManager",
    "get_window_manager",
    "SystemTrayManager",
    "HistoryManager",
    "get_history_manager",
    "PriceRefreshService",
    "get_price_refresh_service",
    "shutdown_price_refresh_service",
    "PriceAlertService",
    "get_price_alert_service",
    "shutdown_price_alert_service",
]
