"""
Performance Package - Optimization utilities for large datasets and lazy loading.

Provides utilities for improving UI performance through lazy initialization,
virtual scrolling, and optimistic updates.

Modules:
    lazy_loader: Lazy widget initialization and progressive loading
    virtual_scroll: Virtual scrolling for large lists
"""

from gui_qt.performance.lazy_loader import (
    LazyLoader,
    LazyWidget,
    lazy_property,
    defer_initialization,
)
from gui_qt.performance.virtual_scroll import (
    VirtualScrollArea,
    VirtualListModel,
    RowDelegate,
)

__all__ = [
    # Lazy loading
    "LazyLoader",
    "LazyWidget",
    "lazy_property",
    "defer_initialization",
    # Virtual scrolling
    "VirtualScrollArea",
    "VirtualListModel",
    "RowDelegate",
]
