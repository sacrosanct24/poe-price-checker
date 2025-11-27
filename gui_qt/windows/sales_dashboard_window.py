"""
gui_qt.windows.sales_dashboard_window

PyQt6 window for sales analytics dashboard.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QPushButton,
    QTableView,
    QAbstractItemView,
    QFormLayout,
)

from gui_qt.styles import apply_window_icon

if TYPE_CHECKING:
    from core.app_context import AppContext


class DailyStatsModel(QAbstractTableModel):
    """Table model for daily sales statistics."""

    COLUMNS = [
        ("date", "Date", 120),
        ("count", "Sales", 80),
        ("total_chaos", "Total (c)", 100),
        ("avg_chaos", "Average (c)", 100),
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
            if col_key in ("total_chaos", "avg_chaos"):
                try:
                    return f"{float(value):.1f}" if value else "0.0"
                except (ValueError, TypeError):
                    return "0.0"
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("count", "total_chaos", "avg_chaos"):
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


class SalesDashboardWindow(QDialog):
    """Window for sales analytics dashboard."""

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ctx = ctx

        self.setWindowTitle("Sales Dashboard")
        self.setMinimumSize(450, 400)
        self.resize(650, 550)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_data()

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Controls
        controls = QHBoxLayout()

        controls.addWidget(QLabel("Days:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(7, 365)
        self.days_spin.setValue(30)
        self.days_spin.valueChanged.connect(self._load_data)
        controls.addWidget(self.days_spin)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_data)
        controls.addWidget(self.refresh_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Summary stats
        summary_group = QGroupBox("Summary")
        summary_layout = QFormLayout(summary_group)

        self.total_sales_label = QLabel("-")
        summary_layout.addRow("Total Sales:", self.total_sales_label)

        self.total_chaos_label = QLabel("-")
        summary_layout.addRow("Total Chaos:", self.total_chaos_label)

        self.avg_chaos_label = QLabel("-")
        summary_layout.addRow("Average Price:", self.avg_chaos_label)

        self.most_sold_label = QLabel("-")
        summary_layout.addRow("Most Sold:", self.most_sold_label)

        layout.addWidget(summary_group)

        # Daily breakdown
        daily_group = QGroupBox("Daily Breakdown")
        daily_layout = QVBoxLayout(daily_group)

        self._model = DailyStatsModel(self)
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        # Column widths
        header = self.table.horizontalHeader()
        for i, (_, _, width) in enumerate(DailyStatsModel.COLUMNS):
            self.table.setColumnWidth(i, width)
        header.setStretchLastSection(True)

        daily_layout.addWidget(self.table)
        layout.addWidget(daily_group, stretch=1)

    def _load_data(self) -> None:
        """Load dashboard data."""
        try:
            days = self.days_spin.value()
            sales = self.ctx.db.get_recent_sales(limit=9999)

            # Filter by date range
            cutoff = datetime.now() - timedelta(days=days)
            filtered_sales = []
            for sale in sales:
                sold_at = sale.get("sold_at")
                if sold_at:
                    if isinstance(sold_at, str):
                        try:
                            sold_at = datetime.fromisoformat(sold_at)
                        except ValueError:
                            continue
                    if sold_at >= cutoff:
                        filtered_sales.append(sale)

            # Calculate summary stats
            total_sales = len(filtered_sales)
            total_chaos = sum(s.get("chaos_value", 0) or 0 for s in filtered_sales)
            avg_chaos = total_chaos / total_sales if total_sales > 0 else 0

            self.total_sales_label.setText(str(total_sales))
            self.total_chaos_label.setText(f"{total_chaos:.1f}c")
            self.avg_chaos_label.setText(f"{avg_chaos:.1f}c")

            # Find most sold item
            item_counts: Dict[str, int] = {}
            for sale in filtered_sales:
                item_name = sale.get("item_name", "Unknown")
                item_counts[item_name] = item_counts.get(item_name, 0) + 1

            if item_counts:
                most_sold = max(item_counts.items(), key=lambda x: x[1])
                self.most_sold_label.setText(f"{most_sold[0]} ({most_sold[1]}x)")
            else:
                self.most_sold_label.setText("-")

            # Calculate daily stats
            daily_stats: Dict[str, Dict[str, Any]] = {}
            for sale in filtered_sales:
                sold_at = sale.get("sold_at")
                if sold_at:
                    if isinstance(sold_at, str):
                        try:
                            sold_at = datetime.fromisoformat(sold_at)
                        except ValueError:
                            continue
                    date_str = sold_at.strftime("%Y-%m-%d")

                    if date_str not in daily_stats:
                        daily_stats[date_str] = {
                            "date": date_str,
                            "count": 0,
                            "total_chaos": 0,
                        }

                    daily_stats[date_str]["count"] += 1
                    daily_stats[date_str]["total_chaos"] += sale.get("chaos_value", 0) or 0

            # Calculate averages and sort
            daily_list = []
            for date_str, stats in sorted(daily_stats.items(), reverse=True):
                stats["avg_chaos"] = stats["total_chaos"] / stats["count"] if stats["count"] > 0 else 0
                daily_list.append(stats)

            self._model.set_data(daily_list)

        except Exception:
            self.total_sales_label.setText("Error")
            self.total_chaos_label.setText("-")
            self.avg_chaos_label.setText("-")
            self.most_sold_label.setText("-")
            self._model.set_data([])
