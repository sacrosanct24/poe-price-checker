"""
Command Palette dialog for quick access to all actions.

Provides a fuzzy-searchable list of all available commands,
similar to VS Code's Ctrl+Shift+P feature.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QHBoxLayout,
    QWidget,
)

from gui_qt.styles import COLORS

logger = logging.getLogger(__name__)


class CommandPaletteItem(QWidget):
    """Custom widget for command palette list items."""

    def __init__(
        self,
        name: str,
        description: str,
        shortcut: str,
        category: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Left side: name and description
        left = QVBoxLayout()
        left.setSpacing(2)

        name_label = QLabel(name)
        name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text']};")
        left.addWidget(name_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        left.addWidget(desc_label)

        layout.addLayout(left, stretch=1)

        # Right side: category and shortcut
        right = QVBoxLayout()
        right.setSpacing(2)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)

        cat_label = QLabel(category)
        cat_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 10px;")
        cat_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(cat_label)

        if shortcut:
            shortcut_label = QLabel(shortcut)
            shortcut_label.setStyleSheet(
                f"background-color: {COLORS['surface']}; "
                f"color: {COLORS['text']}; "
                f"padding: 2px 6px; "
                f"border-radius: 3px; "
                f"font-size: 11px; "
                f"font-family: monospace;"
            )
            shortcut_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            right.addWidget(shortcut_label)

        layout.addLayout(right)


class CommandPaletteDialog(QDialog):
    """
    Command palette for quick access to all actions.

    Features:
    - Fuzzy search by name, description, or category
    - Shows keyboard shortcut for each action
    - Enter to execute selected action
    - Escape to close
    """

    def __init__(
        self,
        actions: List[Dict],
        on_action: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize command palette.

        Args:
            actions: List of action dicts with keys:
                     id, name, description, shortcut, category
            on_action: Callback when action is selected (receives action_id)
            parent: Parent widget
        """
        super().__init__(parent)
        self._actions = actions
        self._filtered_actions = list(actions)
        self._on_action = on_action

        self._setup_ui()
        self._populate_list()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Command Palette")
        self.setMinimumSize(500, 400)
        self.setMaximumSize(700, 600)

        # Remove title bar for cleaner look
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Type to search commands...")
        self._search_input.setStyleSheet(
            f"QLineEdit {{"
            f"  padding: 12px 16px;"
            f"  font-size: 14px;"
            f"  border: none;"
            f"  border-bottom: 1px solid {COLORS['border']};"
            f"  background-color: {COLORS['surface']};"
            f"  color: {COLORS['text']};"
            f"}}"
        )
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.returnPressed.connect(self._execute_selected)
        layout.addWidget(self._search_input)

        # Results list
        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget {{"
            f"  border: none;"
            f"  background-color: {COLORS['background']};"
            f"  outline: none;"
            f"}}"
            f"QListWidget::item {{"
            f"  border-bottom: 1px solid {COLORS['border']};"
            f"  padding: 0;"
            f"}}"
            f"QListWidget::item:selected {{"
            f"  background-color: {COLORS['surface']};"
            f"}}"
            f"QListWidget::item:hover {{"
            f"  background-color: {COLORS['hover']};"
            f"}}"
        )
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list)

        # Hints at bottom
        hints_layout = QHBoxLayout()
        hints_layout.setContentsMargins(12, 8, 12, 8)

        enter_hint = QLabel("Enter to execute")
        enter_hint.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        hints_layout.addWidget(enter_hint)

        hints_layout.addStretch()

        esc_hint = QLabel("Esc to close")
        esc_hint.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        hints_layout.addWidget(esc_hint)

        hints_widget = QWidget()
        hints_widget.setLayout(hints_layout)
        hints_widget.setStyleSheet(f"background-color: {COLORS['surface']};")
        layout.addWidget(hints_widget)

        # Set overall dialog style
        self.setStyleSheet(
            f"CommandPaletteDialog {{"
            f"  background-color: {COLORS['background']};"
            f"  border: 1px solid {COLORS['border']};"
            f"  border-radius: 8px;"
            f"}}"
        )

    def _populate_list(self) -> None:
        """Populate the list with filtered actions."""
        self._list.clear()

        for action in self._filtered_actions:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, action["id"])

            widget = CommandPaletteItem(
                name=action["name"],
                description=action["description"],
                shortcut=action.get("shortcut", ""),
                category=action.get("category", ""),
            )

            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

        # Select first item
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _on_search_changed(self, text: str) -> None:
        """Handle search text changes with debouncing."""
        self._filter_actions(text)

    def _filter_actions(self, query: str) -> None:
        """Filter actions based on query."""
        query = query.lower().strip()

        if not query:
            self._filtered_actions = list(self._actions)
        else:
            # Fuzzy match on name, description, and category
            scored = []
            for action in self._actions:
                score = self._match_score(query, action)
                if score > 0:
                    scored.append((score, action))

            # Sort by score (highest first)
            scored.sort(key=lambda x: x[0], reverse=True)
            self._filtered_actions = [a for _, a in scored]

        self._populate_list()

    def _match_score(self, query: str, action: Dict) -> int:
        """Calculate match score for an action."""
        name = action["name"].lower()
        desc = action["description"].lower()
        cat = action.get("category", "").lower()

        score = 0

        # Exact match in name
        if query == name:
            score += 100
        # Starts with query
        elif name.startswith(query):
            score += 80
        # Contains query
        elif query in name:
            score += 60

        # Word start matches (e.g., "bis" matches "BiS Item Search")
        words = name.split()
        if all(any(w.startswith(q) for w in words) for q in query.split()):
            score += 50

        # Description match
        if query in desc:
            score += 20

        # Category match
        if query in cat:
            score += 10

        # Fuzzy character match
        if self._fuzzy_match(query, name):
            score += 30

        return score

    def _fuzzy_match(self, query: str, text: str) -> bool:
        """Check if all query chars appear in order in text."""
        text_idx = 0
        for char in query:
            found = False
            while text_idx < len(text):
                if text[text_idx] == char:
                    found = True
                    text_idx += 1
                    break
                text_idx += 1
            if not found:
                return False
        return True

    def _execute_selected(self) -> None:
        """Execute the currently selected action."""
        current = self._list.currentItem()
        if current:
            action_id = current.data(Qt.ItemDataRole.UserRole)
            self.accept()
            self._on_action(action_id)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on item."""
        action_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        self._on_action(action_id)

    def keyPressEvent(self, event) -> None:
        """Handle key presses."""
        key = event.key()

        if key == Qt.Key.Key_Escape:
            self.reject()
        elif key == Qt.Key.Key_Up:
            current = self._list.currentRow()
            if current > 0:
                self._list.setCurrentRow(current - 1)
        elif key == Qt.Key.Key_Down:
            current = self._list.currentRow()
            if current < self._list.count() - 1:
                self._list.setCurrentRow(current + 1)
        else:
            super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        """Focus search input when shown."""
        super().showEvent(event)
        self._search_input.setFocus()
        self._search_input.selectAll()
