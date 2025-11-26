"""
gui_qt.widgets.results_table

PyQt6 table widget for displaying price check results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (
    QTableView,
    QWidget,
    QAbstractItemView,
)

from gui_qt.styles import COLORS


class ResultsTableModel(QAbstractTableModel):
    """Table model for price check results."""

    # Column definitions: (key, display_name, default_width)
    COLUMNS = [
        ("item_name", "Item Name", 180),
        ("variant", "Variant", 100),
        ("links", "Links", 60),
        ("chaos_value", "Chaos", 80),
        ("divine_value", "Divine", 80),
        ("listing_count", "Listings", 70),
        ("source", "Source", 100),
        ("upgrade", "Upgrade", 70),
        ("price_explanation", "Explanation", 0),  # Hidden
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._hidden_columns: set[str] = {"price_explanation"}

    @property
    def columns(self) -> List[str]:
        """Return list of column keys."""
        return [col[0] for col in self.COLUMNS]

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
            # Format numeric values
            if col_key in ("chaos_value", "divine_value"):
                try:
                    return f"{float(value):.1f}" if value else ""
                except (ValueError, TypeError):
                    return str(value) if value else ""
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.ForegroundRole:
            # Color based on value
            chaos_val = row_data.get("chaos_value", 0)
            try:
                chaos_val = float(chaos_val) if chaos_val else 0
            except (ValueError, TypeError):
                chaos_val = 0

            if chaos_val >= 100:
                return QBrush(QColor(COLORS["high_value"]))
            elif chaos_val >= 10:
                return QBrush(QColor(COLORS["medium_value"]))

            # Upgrade indicator
            if col_key == "upgrade" and value:
                return QBrush(QColor(COLORS["upgrade"]))

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight upgrade rows
            if row_data.get("upgrade"):
                return QBrush(QColor("#2a3a2a"))  # Dark green tint

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("chaos_value", "divine_value", "listing_count", "links"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.UserRole:
            # Return full row data for selection handling
            return row_data

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
            else:
                return str(section + 1)
        return None

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Set the table data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def get_row(self, row: int) -> Optional[Dict[str, Any]]:
        """Get data for a specific row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Sort by column."""
        if not self._data:
            return

        col_key = self.COLUMNS[column][0]
        reverse = order == Qt.SortOrder.DescendingOrder

        def sort_key(row: Dict[str, Any]) -> Any:
            val = row.get(col_key, "")
            # Try numeric sort
            try:
                return float(val) if val else 0
            except (ValueError, TypeError):
                return str(val).lower()

        self.beginResetModel()
        self._data.sort(key=sort_key, reverse=reverse)
        self.endResetModel()


class ResultsTableWidget(QTableView):
    """Table widget for displaying price check results."""

    row_selected = pyqtSignal(dict)  # Emits selected row data

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Setup model
        self._model = ResultsTableModel(self)
        self.setModel(self._model)

        # Configure view
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setShowGrid(False)

        # Configure header
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setSortIndicatorShown(True)

        # Set column widths
        for i, (key, name, width) in enumerate(ResultsTableModel.COLUMNS):
            if width > 0:
                self.setColumnWidth(i, width)
            else:
                self.setColumnHidden(i, True)

        # Connect selection
        self.selectionModel().currentRowChanged.connect(self._on_row_changed)

    @property
    def columns(self) -> List[str]:
        """Return list of column keys."""
        return self._model.columns

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Set the table data."""
        self._model.set_data(data)

    def get_selected_row(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected row data."""
        indexes = self.selectionModel().selectedRows()
        if indexes:
            return self._model.get_row(indexes[0].row())
        return None

    def set_column_visible(self, column: str, visible: bool) -> None:
        """Show or hide a column."""
        for i, (key, _, _) in enumerate(ResultsTableModel.COLUMNS):
            if key == column:
                self.setColumnHidden(i, not visible)
                break

    def _on_row_changed(self, current: QModelIndex, previous: QModelIndex) -> None:
        """Handle row selection change."""
        if current.isValid():
            row_data = self._model.get_row(current.row())
            if row_data:
                self.row_selected.emit(row_data)

    def to_tsv(self, include_header: bool = True) -> str:
        """Export table data as TSV string."""
        lines = []

        # Get visible columns
        visible_cols = []
        for i, (key, name, _) in enumerate(ResultsTableModel.COLUMNS):
            if not self.isColumnHidden(i):
                visible_cols.append((i, key, name))

        if include_header:
            header = "\t".join(name for _, _, name in visible_cols)
            lines.append(header)

        for row in range(self._model.rowCount()):
            values = []
            for col_idx, key, _ in visible_cols:
                index = self._model.index(row, col_idx)
                value = self._model.data(index, Qt.ItemDataRole.DisplayRole)
                values.append(str(value) if value else "")
            lines.append("\t".join(values))

        return "\n".join(lines)

    def export_tsv(self, path: str | Path) -> None:
        """Export table data to TSV file."""
        tsv = self.to_tsv(include_header=True)
        Path(path).write_text(tsv, encoding="utf-8")
