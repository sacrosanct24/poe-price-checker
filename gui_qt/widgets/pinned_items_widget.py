"""
gui_qt.widgets.pinned_items_widget

Widget for displaying pinned items that persist across price checks.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFrame,
    QMenu,
    QApplication,
)

from gui_qt.styles import COLORS
from gui_qt.widgets.poe_item_tooltip import PoEItemTooltip

logger = logging.getLogger(__name__)


class PinnedItemWidget(QFrame):
    """Individual pinned item display."""

    unpin_requested = pyqtSignal(dict)  # Request to unpin this item
    inspect_requested = pyqtSignal(dict)  # Request to inspect this item

    def __init__(self, item_data: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._item_data = item_data

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Enable mouse tracking for Alt+hover tooltip
        self.setMouseTracking(True)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Setup the widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Item name
        name = self._item_data.get("item_name", "Unknown")
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        name_label.setToolTip(name)
        layout.addWidget(name_label, 1)

        # Price
        chaos_val = self._item_data.get("chaos_value", 0)
        if chaos_val:
            price_label = QLabel(f"{float(chaos_val):.1f}c")
            price_color = COLORS["high_value"] if float(chaos_val) >= 100 else COLORS["medium_value"] if float(chaos_val) >= 10 else COLORS["text"]
            price_label.setStyleSheet(f"color: {price_color};")
            layout.addWidget(price_label)

        # Unpin button
        unpin_btn = QPushButton("x")
        unpin_btn.setFixedSize(20, 20)
        unpin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        unpin_btn.clicked.connect(lambda: self.unpin_requested.emit(self._item_data))
        unpin_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS["text"]};
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #F44336;
            }}
        """)
        layout.addWidget(unpin_btn)

    def _apply_style(self) -> None:
        """Apply styling."""
        self.setStyleSheet(f"""
            PinnedItemWidget {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
            PinnedItemWidget:hover {{
                border-color: {COLORS["accent"]};
            }}
        """)

    def _show_context_menu(self, position) -> None:
        """Show context menu."""
        menu = QMenu(self)

        inspect_action = menu.addAction("Inspect")
        inspect_action.triggered.connect(
            lambda: self.inspect_requested.emit(self._item_data)
        )

        copy_action = menu.addAction("Copy Name")
        copy_action.triggered.connect(
            lambda: QApplication.clipboard().setText(self._item_data.get("item_name", ""))
        )

        menu.addSeparator()

        unpin_action = menu.addAction("Unpin")
        unpin_action.triggered.connect(
            lambda: self.unpin_requested.emit(self._item_data)
        )

        menu.exec(self.mapToGlobal(position))

    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click to inspect."""
        self.inspect_requested.emit(self._item_data)
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move to show/hide Alt+hover tooltip."""
        super().mouseMoveEvent(event)

        # Check if Alt is pressed
        modifiers = QApplication.keyboardModifiers()
        alt_pressed = bool(modifiers & Qt.KeyboardModifier.AltModifier)

        if alt_pressed:
            # Show tooltip for the item stored in this widget
            item = self._item_data.get("_item")
            if item is not None:
                tooltip = PoEItemTooltip.instance()
                tooltip.show_for_item(item, event.globalPosition().toPoint())
        else:
            # Hide tooltip
            tooltip = PoEItemTooltip.instance()
            tooltip.hide_after_delay(50)

    def leaveEvent(self, event) -> None:
        """Hide tooltip when mouse leaves the widget."""
        super().leaveEvent(event)
        tooltip = PoEItemTooltip.instance()
        tooltip.hide_after_delay(50)

    @property
    def item_data(self) -> Dict[str, Any]:
        """Get the item data."""
        return self._item_data


class PinnedItemsWidget(QWidget):
    """
    Widget for displaying and managing pinned items.

    Pinned items persist across price checks and can be used for
    quick reference or comparison.
    """

    item_inspected = pyqtSignal(dict)  # Request to inspect an item
    items_changed = pyqtSignal(list)  # Pinned items list changed

    # Storage file for pinned items
    STORAGE_FILE = "pinned_items.json"
    MAX_PINNED_ITEMS = 20

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pinned_items: List[Dict[str, Any]] = []
        self._item_widgets: List[PinnedItemWidget] = []

        self._setup_ui()
        self._load_pinned_items()

    def _setup_ui(self) -> None:
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 4, 8, 4)

        title_label = QLabel("Pinned Items")
        title_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        header_layout.addWidget(title_label)

        self._count_label = QLabel("(0)")
        self._count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header_layout.addWidget(self._count_label)

        header_layout.addStretch()

        # Clear all button
        clear_btn = QPushButton("Clear All")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_all)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS["text_secondary"]};
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                color: #F44336;
            }}
        """)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        # Items container
        self._items_container = QWidget()
        self._items_layout = QVBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(4, 0, 4, 4)
        self._items_layout.setSpacing(4)
        self._items_layout.addStretch()

        layout.addWidget(self._items_container, 1)

        # Empty state label
        self._empty_label = QLabel("No pinned items.\nRight-click items to pin them.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 20px;")
        layout.addWidget(self._empty_label)

        self._update_empty_state()

    def _update_empty_state(self) -> None:
        """Update visibility of empty state."""
        has_items = len(self._pinned_items) > 0
        self._items_container.setVisible(has_items)
        self._empty_label.setVisible(not has_items)
        self._count_label.setText(f"({len(self._pinned_items)})")

    def pin_item(self, item_data: Dict[str, Any]) -> bool:
        """
        Pin an item.

        Args:
            item_data: The item data to pin

        Returns:
            True if item was pinned, False if already pinned or at limit
        """
        # Check if already pinned (by item_name)
        item_name = item_data.get("item_name", "")
        for pinned in self._pinned_items:
            if pinned.get("item_name") == item_name:
                return False

        # Check limit
        if len(self._pinned_items) >= self.MAX_PINNED_ITEMS:
            return False

        # Add to list
        self._pinned_items.append(item_data)
        self._add_item_widget(item_data)
        self._update_empty_state()
        self._save_pinned_items()
        self.items_changed.emit(self._pinned_items)
        return True

    def pin_items(self, items: List[Dict[str, Any]]) -> int:
        """
        Pin multiple items.

        Args:
            items: List of item data to pin

        Returns:
            Number of items successfully pinned
        """
        count = 0
        for item in items:
            if self.pin_item(item):
                count += 1
        return count

    def unpin_item(self, item_data: Dict[str, Any]) -> bool:
        """
        Unpin an item.

        Args:
            item_data: The item data to unpin

        Returns:
            True if item was unpinned, False if not found
        """
        item_name = item_data.get("item_name", "")

        # Find and remove from list
        for i, pinned in enumerate(self._pinned_items):
            if pinned.get("item_name") == item_name:
                self._pinned_items.pop(i)
                break
        else:
            return False

        # Remove widget
        for widget in self._item_widgets:
            if widget.item_data.get("item_name") == item_name:
                self._items_layout.removeWidget(widget)
                widget.deleteLater()
                self._item_widgets.remove(widget)
                break

        self._update_empty_state()
        self._save_pinned_items()
        self.items_changed.emit(self._pinned_items)
        return True

    def clear_all(self) -> None:
        """Clear all pinned items."""
        self._pinned_items.clear()

        for widget in self._item_widgets:
            self._items_layout.removeWidget(widget)
            widget.deleteLater()
        self._item_widgets.clear()

        self._update_empty_state()
        self._save_pinned_items()
        self.items_changed.emit(self._pinned_items)

    def _add_item_widget(self, item_data: Dict[str, Any]) -> None:
        """Add a widget for a pinned item."""
        widget = PinnedItemWidget(item_data, self)
        widget.unpin_requested.connect(self.unpin_item)
        widget.inspect_requested.connect(self.item_inspected.emit)

        # Insert before the stretch
        self._items_layout.insertWidget(self._items_layout.count() - 1, widget)
        self._item_widgets.append(widget)

    def _get_storage_path(self) -> Path:
        """Get the path to the pinned items storage file."""
        # Store in user's app data directory
        from core.config import get_config_dir
        return get_config_dir() / self.STORAGE_FILE

    def _load_pinned_items(self) -> None:
        """Load pinned items from storage."""
        try:
            storage_path = self._get_storage_path()
            if storage_path.exists():
                with open(storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data[:self.MAX_PINNED_ITEMS]:
                            self._pinned_items.append(item)
                            self._add_item_widget(item)
                self._update_empty_state()
        except Exception as e:
            logger.warning(f"Failed to load pinned items: {e}")

    def _save_pinned_items(self) -> None:
        """Save pinned items to storage."""
        try:
            storage_path = self._get_storage_path()
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(storage_path, "w", encoding="utf-8") as f:
                # Only save serializable data
                serializable = []
                for item in self._pinned_items:
                    clean_item = {
                        k: v for k, v in item.items()
                        if not k.startswith("_") and isinstance(v, (str, int, float, bool, type(None), list, dict))
                    }
                    serializable.append(clean_item)
                json.dump(serializable, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save pinned items: {e}")

    @property
    def pinned_items(self) -> List[Dict[str, Any]]:
        """Get the list of pinned items."""
        return self._pinned_items.copy()

    def is_pinned(self, item_name: str) -> bool:
        """Check if an item is pinned by name."""
        return any(p.get("item_name") == item_name for p in self._pinned_items)
