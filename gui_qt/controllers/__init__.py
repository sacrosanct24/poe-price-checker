"""
gui_qt.controllers - Controller layer for the GUI.

Controllers coordinate between services and UI widgets:
- PriceCheckController: Manages price checking workflow and result formatting
- ThemeController: Manages theme and accent color state
- NavigationController: Manages window/dialog navigation
- ResultsContextController: Manages results table context menu
- TrayController: Manages system tray functionality
"""

from gui_qt.controllers.price_check_controller import PriceCheckController
from gui_qt.controllers.theme_controller import ThemeController
from gui_qt.controllers.navigation_controller import (
    NavigationController,
    get_navigation_controller,
)
from gui_qt.controllers.results_context_controller import (
    ResultsContextController,
    get_results_context_controller,
)
from gui_qt.controllers.tray_controller import (
    TrayController,
    get_tray_controller,
)

__all__ = [
    "PriceCheckController",
    "ThemeController",
    "NavigationController",
    "get_navigation_controller",
    "ResultsContextController",
    "get_results_context_controller",
    "TrayController",
    "get_tray_controller",
]
