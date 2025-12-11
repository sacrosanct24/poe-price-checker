"""
gui_qt.controllers - Controller layer for the GUI.

Controllers coordinate between services and UI widgets:
- PriceCheckController: Manages price checking workflow and result formatting
- ThemeController: Manages theme and accent color state
- NavigationController: Manages window/dialog navigation
- ResultsContextController: Manages results table context menu
- TrayController: Manages system tray functionality
- PoBController: Manages Path of Building integration
- ViewMenuController: Manages View menu creation
- UpgradeAnalysisController: Manages AI-powered upgrade analysis orchestration
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
from gui_qt.controllers.pob_controller import (
    PoBController,
    get_pob_controller,
)
from gui_qt.controllers.view_menu_controller import (
    ViewMenuController,
    get_view_menu_controller,
)
from gui_qt.controllers.upgrade_analysis_controller import (
    UpgradeAnalysisController,
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
    "PoBController",
    "get_pob_controller",
    "ViewMenuController",
    "get_view_menu_controller",
    "UpgradeAnalysisController",
]
