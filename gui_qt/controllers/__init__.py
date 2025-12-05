"""
gui_qt.controllers - Controller layer for the GUI.

Controllers coordinate between services and UI widgets:
- PriceCheckController: Manages price checking workflow and result formatting
- ThemeController: Manages theme and accent color state
- NavigationController: Manages window/dialog navigation
"""

from gui_qt.controllers.price_check_controller import PriceCheckController
from gui_qt.controllers.theme_controller import ThemeController
from gui_qt.controllers.navigation_controller import (
    NavigationController,
    get_navigation_controller,
)

__all__ = [
    "PriceCheckController",
    "ThemeController",
    "NavigationController",
    "get_navigation_controller",
]
