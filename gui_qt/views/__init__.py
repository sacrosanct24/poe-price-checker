"""
gui_qt.views - Full-screen view components for PoE Price Checker.

Views are full-screen replacements for the main content area,
distinct from windows (separate dialogs) and widgets (composable pieces).
"""

from gui_qt.views.upgrade_advisor_view import UpgradeAdvisorView

__all__ = [
    "UpgradeAdvisorView",
]
