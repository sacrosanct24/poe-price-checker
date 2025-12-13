"""
gui_qt.dialogs.tabs - Tab widgets for Item Planning Hub.

These tabs are extracted from the original dialogs to enable a unified
item planning experience with shared profile/priority state.
"""

from gui_qt.dialogs.tabs.upgrade_finder_tab import UpgradeFinderTab
from gui_qt.dialogs.tabs.bis_guide_tab import BiSGuideTab

__all__ = [
    "UpgradeFinderTab",
    "BiSGuideTab",
]
