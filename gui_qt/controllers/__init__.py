"""
gui_qt.controllers - Controller layer for the GUI.

Controllers coordinate between services and UI widgets:
- PriceCheckController: Manages price checking workflow and result formatting
- ThemeController: Manages theme and accent color state
"""

from gui_qt.controllers.price_check_controller import PriceCheckController
from gui_qt.controllers.theme_controller import ThemeController

__all__ = ["PriceCheckController", "ThemeController"]
