"""
gui_qt.controllers - Controller layer for the GUI.

Controllers coordinate between services and UI widgets:
- PriceCheckController: Manages price checking workflow and result formatting
"""

from gui_qt.controllers.price_check_controller import PriceCheckController

__all__ = ["PriceCheckController"]
