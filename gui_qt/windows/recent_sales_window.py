"""
gui_qt.windows.recent_sales_window

PyQt6 window for displaying recent sales.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QPushButton,
    QTableView,
    QAbstractItemView,
)

from gui_qt.styles import apply_window_icon

if TYPE_CHECKING:
    from core.app_context import AppContext


class SalesTableModel(QAbstractTableModel):
    """Table model for recent sales."""

    COLUMNS = [
        ("sold_at", "Date", 150),
        ("item_name", "Item", 200),
        ("source", "Source", 100),
        ("chaos_value", "Price (c)", 80),
        ("notes", "Notes", 150),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row_data = self._data[index.row()]
        col_key = self.COLUMNS[index.column()][0]
        value = row_data.get(col_key, "")

        if role == Qt.ItemDataRole.DisplayRole:
            if col_key == "sold_at" and value:
                # Format datetime
                try:
                    if isinstance(value, str):
                        dt = datetime.fromisoformat(value)
                    else:
                        dt = value
                    return dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    return str(value)
            elif col_key == "chaos_value":
                try:
                    return f"{float(value):.1f}" if value else ""
                except (ValueError, TypeError):
                    return str(value)
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key == "chaos_value":
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.COLUMNS[section][1]
        return None

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Set the table data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def get_sources(self) -> List[str]:
        """Get unique source values."""
        return sorted(set(row.get("source", "") for row in self._data if row.get("source")))


class RecentSalesWindow(QDialog):
    """Window for displaying recent sales."""

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ctx = ctx

        self.setWindowTitle("Recent Sales")
        self.setMinimumSize(500, 400)
        self.resize(800, 550)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._all_sales: List[Dict[str, Any]] = []

        self._create_widgets()
        self._load_sales()

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_sales)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addWidget(QLabel("Limit:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 500)
        self.limit_spin.setValue(100)
        self.limit_spin.valueChanged.connect(self._load_sales)
        toolbar.addWidget(self.limit_spin)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Filter row
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Filter:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search...")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_input)

        filter_row.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("All sources")
        self.source_combo.currentTextChanged.connect(self._apply_filter)
        filter_row.addWidget(self.source_combo)

        layout.addLayout(filter_row)

        # Table
        self._model = SalesTableModel(self)
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        # Column widths
        header = self.table.horizontalHeader()
        for i, (_, _, width) in enumerate(SalesTableModel.COLUMNS):
            self.table.setColumnWidth(i, width)
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

        # Summary
        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

    def _load_sales(self) -> None:
        """Load sales from database."""
        try:
            limit = self.limit_spin.value()
            self._all_sales = self.ctx.db.get_recent_sales(limit=limit)

            # Update source filter
            self.source_combo.clear()
            self.source_combo.addItem("All sources")
            sources = set(s.get("source", "") for s in self._all_sales if s.get("source"))
            for source in sorted(sources):
                self.source_combo.addItem(source)

            self._apply_filter()
        except Exception as e:
            self._all_sales = []
            self._model.set_data([])
            self.summary_label.setText(f"Error loading sales: {e}")

    def _apply_filter(self) -> None:
        """Apply filters to sales."""
        text_filter = self.filter_input.text().lower()
        source_filter = self.source_combo.currentText()

        filtered = []
        for sale in self._all_sales:
            # Source filter
            if source_filter != "All sources":
                if sale.get("source", "") != source_filter:
                    continue

            # Text filter
            if text_filter:
                searchable = " ".join(str(v).lower() for v in sale.values())
                if text_filter not in searchable:
                    continue

            filtered.append(sale)

        self._model.set_data(filtered)

        # Update summary
        total_chaos = sum(s.get("chaos_value", 0) or 0 for s in filtered)
        self.summary_label.setText(
            f"{len(filtered)} sales | Total: {total_chaos:.1f}c"
        )
