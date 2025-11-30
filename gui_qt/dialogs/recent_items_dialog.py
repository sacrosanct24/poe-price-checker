"""
gui_qt.dialogs.recent_items_dialog

Dialog for viewing and re-checking recently checked items.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from PyQt6.QtCore import Qt, pyqtSignal

from core.history import HistoryEntry
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QAbstractItemView,
)

from gui_qt.styles import COLORS, get_theme_manager


class RecentItemsDialog(QDialog):
    """Dialog for viewing and re-checking recently checked items."""

    item_selected = pyqtSignal(str)  # Emits item text for re-checking

    def __init__(
        self,
        history: List[Union[HistoryEntry, Dict[str, Any]]],
        parent: Optional[Any] = None,
    ):
        super().__init__(parent)
        self._history = list(history)  # Copy to avoid mutation

        self.setWindowTitle("Recent Items")
        self.setMinimumSize(600, 400)
        self.resize(700, 450)

        self._setup_ui()
        self._apply_theme()
        self._populate_table()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel(f"Recently Checked Items ({len(self._history)} items)")
        header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text']};")
        layout.addWidget(header)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Time", "Item", "Price", "Results"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)

        # Configure header
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # Double-click to select
        self._table.cellDoubleClicked.connect(self._on_double_click)

        layout.addWidget(self._table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._recheck_btn = QPushButton("Re-check Selected")
        self._recheck_btn.clicked.connect(self._on_recheck)
        self._recheck_btn.setEnabled(False)
        btn_layout.addWidget(self._recheck_btn)

        btn_layout.addStretch()

        self._clear_btn = QPushButton("Clear History")
        self._clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self._clear_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Connect selection change
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

    def _apply_theme(self) -> None:
        """Apply the current theme to the dialog."""
        theme_manager = get_theme_manager()
        self.setStyleSheet(theme_manager.get_stylesheet())

    def _populate_table(self) -> None:
        """Populate the table with history entries."""
        self._table.setRowCount(len(self._history))

        # Show most recent first
        for row, entry in enumerate(reversed(self._history)):
            # Time column
            try:
                ts = datetime.fromisoformat(entry.get("timestamp", ""))
                time_str = ts.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                time_str = "??:??:??"

            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, time_item)

            # Item name column
            item_name = entry.get("item_name", entry.get("item", "Unknown"))
            name_item = QTableWidgetItem(item_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setData(Qt.ItemDataRole.UserRole, entry)  # Store full entry
            self._table.setItem(row, 1, name_item)

            # Price column
            best_price = entry.get("best_price", 0)
            if best_price and best_price > 0:
                price_str = f"{best_price:.1f}c"
                price_item = QTableWidgetItem(price_str)
                # Color based on value
                if best_price >= 100:
                    price_item.setForeground(QColor(COLORS.get("high_value", "#FFD700")))
                elif best_price >= 10:
                    price_item.setForeground(QColor(COLORS.get("medium_value", "#90EE90")))
            else:
                price_item = QTableWidgetItem("-")
            price_item.setFlags(price_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 2, price_item)

            # Results count column
            results_count = entry.get("results_count", 0)
            results_item = QTableWidgetItem(str(results_count))
            results_item.setFlags(results_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            results_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, results_item)

    def _on_selection_changed(self) -> None:
        """Handle selection change."""
        has_selection = len(self._table.selectedItems()) > 0
        self._recheck_btn.setEnabled(has_selection)

    def _on_double_click(self, row: int, column: int) -> None:
        """Handle double-click on a row."""
        self._recheck_selected_item()

    def _on_recheck(self) -> None:
        """Handle re-check button click."""
        self._recheck_selected_item()

    def _recheck_selected_item(self) -> None:
        """Re-check the selected item."""
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            return

        # Get the entry from the item name cell (column 1)
        row = selected_rows[0].row()
        name_item = self._table.item(row, 1)
        if not name_item:
            return

        entry = name_item.data(Qt.ItemDataRole.UserRole)
        if entry and entry.get("item_text"):
            self.item_selected.emit(entry["item_text"])
            self.accept()

    def _on_clear(self) -> None:
        """Clear the history."""
        self._history.clear()
        self._table.setRowCount(0)
        self._recheck_btn.setEnabled(False)

    def get_selected_item_text(self) -> Optional[str]:
        """Get the item text of the selected row."""
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        name_item = self._table.item(row, 1)
        if name_item:
            entry = name_item.data(Qt.ItemDataRole.UserRole)
            if entry:
                return entry.get("item_text")
        return None
