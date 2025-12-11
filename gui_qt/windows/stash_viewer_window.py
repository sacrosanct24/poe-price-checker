"""
Stash Viewer Window - Compatibility Shim.

This module re-exports from gui_qt.stash_viewer for backward compatibility.
The implementation has been moved to the gui_qt/stash_viewer/ package.

For new code, import directly from gui_qt.stash_viewer:
    from gui_qt.stash_viewer import StashViewerWindow, FetchWorker, ItemTableModel
"""

from __future__ import annotations

# Re-export all public classes for backward compatibility
from gui_qt.stash_viewer import (
    StashViewerWindow,
    FetchWorker,
    ItemTableModel,
    StashItemDetailsDialog,
)

__all__ = [
    "StashViewerWindow",
    "FetchWorker",
    "ItemTableModel",
    "StashItemDetailsDialog",
]
