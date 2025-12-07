"""
gui_qt.screens - Full-screen application screens for PoE Price Checker.

The application is divided into 3 main screens:
- Item Evaluator: Price checking and item analysis (main_view in main_window)
- AI Advisor: Build optimization and upgrade recommendations
- Daytrader: Economy analysis, sales tracking, and trading

Each screen is a full QWidget that replaces the main content area
when selected via the top navigation bar.

Note: Item Evaluator is the main_view which is built directly in main_window.py
rather than using a separate screen class.
"""

from gui_qt.screens.base_screen import BaseScreen
from gui_qt.screens.screen_controller import ScreenController, ScreenType
from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
from gui_qt.screens.daytrader_screen import DaytraderScreen

__all__ = [
    "BaseScreen",
    "ScreenController",
    "ScreenType",
    "AIAdvisorScreen",
    "DaytraderScreen",
]
