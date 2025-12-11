"""
gui_qt.windows.price_history_window

PyQt6 window for historical economy data analysis.
Shows currency statistics and top unique items over a league's lifetime.
All values are in chaos orb equivalents.

Uses pre-aggregated summary tables for fast queries when available.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QPushButton,
    QTableView,
    QAbstractItemView,
    QSplitter,
    QMessageBox,
)

from gui_qt.styles import apply_window_icon

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)

# Common currencies to track (in order of typical importance)
TRACKED_CURRENCIES = [
    "Divine Orb",
    "Exalted Orb",
    "Orb of Annulment",
    "Ancient Orb",
    "Orb of Fusing",
    "Gemcutter's Prism",
    "Orb of Regret",
    "Orb of Alchemy",
    "Orb of Alteration",
    "Jeweller's Orb",
]

# Short names for currency display
CURRENCY_SHORT_NAMES = {
    "Divine Orb": "Divine",
    "Exalted Orb": "Exalt",
    "Orb of Annulment": "Annul",
    "Ancient Orb": "Ancient",
    "Orb of Fusing": "Fusing",
    "Gemcutter's Prism": "GCP",
    "Orb of Regret": "Regret",
    "Orb of Alchemy": "Alch",
    "Orb of Alteration": "Alt",
    "Jeweller's Orb": "Jeweller",
}


class CurrencySummaryModel(QAbstractTableModel):
    """Table model for currency summary statistics."""

    COLUMNS = [
        ("currency", "Currency", 100),
        ("avg_value", "Avg", 70),
        ("min_value", "Min", 70),
        ("max_value", "Max", 70),
        ("start_value", "Start", 70),
        ("end_value", "End", 70),
        ("data_points", "Days", 60),
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
            if col_key == "currency":
                # Use short name
                full_name = row_data.get("currency_name", str(value))
                return CURRENCY_SHORT_NAMES.get(full_name, full_name)
            elif col_key == "data_points":
                return str(value) if value else "0"
            else:
                # Format numeric values
                try:
                    val = float(value) if value else 0
                    if val >= 1000:
                        return f"{val:,.0f}"
                    elif val >= 10:
                        return f"{val:.1f}"
                    else:
                        return f"{val:.2f}"
                except (ValueError, TypeError):
                    return "-"

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key != "currency":
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


class TopItemsModel(QAbstractTableModel):
    """Table model for top unique items by value."""

    COLUMNS = [
        ("rank", "#", 40),
        ("item_name", "Item", 200),
        ("avg_value", "Avg (c)", 80),
        ("min_value", "Min (c)", 80),
        ("max_value", "Max (c)", 80),
        ("data_points", "Days", 60),
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
            if col_key == "rank":
                # Use stored rank or row index
                return str(row_data.get("rank", index.row() + 1))
            elif col_key == "item_name":
                return str(value)
            elif col_key in ("avg_value", "min_value", "max_value"):
                try:
                    val = float(value) if value else 0
                    if val >= 1000:
                        return f"{val:,.0f}"
                    else:
                        return f"{val:.1f}"
                except (ValueError, TypeError):
                    return "-"
            elif col_key == "data_points":
                return str(value) if value else "0"
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("rank", "avg_value", "min_value", "max_value", "data_points"):
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


class PriceHistoryWindow(QDialog):
    """Window for historical economy data analysis."""

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ctx = ctx
        self._economy_service = None
        self._setup_ui()
        self._load_leagues()

    def _get_economy_service(self):
        """Get or create the economy service."""
        if self._economy_service is None:
            from core.economy import LeagueEconomyService
            self._economy_service = LeagueEconomyService(self.ctx.db)
        return self._economy_service

    def _setup_ui(self) -> None:
        """Set up the window UI."""
        self.setWindowTitle("Price History - Economy Analysis")
        self.setMinimumSize(900, 600)
        apply_window_icon(self)

        layout = QVBoxLayout(self)

        # League selector row
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("League:"))
        self._league_combo = QComboBox()
        self._league_combo.setMinimumWidth(200)
        self._league_combo.currentTextChanged.connect(self._on_league_changed)
        selector_layout.addWidget(self._league_combo)

        # Aggregate button
        self._aggregate_btn = QPushButton("Aggregate Data")
        self._aggregate_btn.setToolTip(
            "Pre-compute summary statistics for faster queries.\n"
            "Run this once per league after importing data."
        )
        self._aggregate_btn.clicked.connect(self._on_aggregate_clicked)
        selector_layout.addWidget(self._aggregate_btn)

        selector_layout.addStretch()

        # Stats label
        self._stats_label = QLabel("")
        selector_layout.addWidget(self._stats_label)

        layout.addLayout(selector_layout)

        # Splitter for two panels
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Currency summary group
        currency_group = QGroupBox("Currency Statistics (Chaos Equivalent)")
        currency_layout = QVBoxLayout(currency_group)

        self._currency_model = CurrencySummaryModel(self)
        self._currency_table = QTableView()
        self._currency_table.setModel(self._currency_model)
        self._currency_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._currency_table.setAlternatingRowColors(True)

        # Set column widths
        for i, (_, _, width) in enumerate(CurrencySummaryModel.COLUMNS):
            self._currency_table.setColumnWidth(i, width)
        currency_header = self._currency_table.horizontalHeader()
        if currency_header:
            currency_header.setStretchLastSection(True)

        currency_layout.addWidget(self._currency_table)
        splitter.addWidget(currency_group)

        # Top uniques group
        uniques_group = QGroupBox("Top 10 Unique Items (by Average Value)")
        uniques_layout = QVBoxLayout(uniques_group)

        self._uniques_model = TopItemsModel(self)
        self._uniques_table = QTableView()
        self._uniques_table.setModel(self._uniques_model)
        self._uniques_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._uniques_table.setAlternatingRowColors(True)

        # Set column widths
        for i, (_, _, width) in enumerate(TopItemsModel.COLUMNS):
            self._uniques_table.setColumnWidth(i, width)
        uniques_header = self._uniques_table.horizontalHeader()
        if uniques_header:
            uniques_header.setStretchLastSection(True)

        uniques_layout.addWidget(self._uniques_table)
        splitter.addWidget(uniques_group)

        # Set initial splitter sizes (60% currency, 40% uniques)
        splitter.setSizes([360, 240])

        layout.addWidget(splitter)

    def _load_leagues(self) -> None:
        """Load available leagues from database."""
        try:
            cursor = self.ctx.db.conn.execute("""
                SELECT DISTINCT league FROM league_economy_rates
                ORDER BY league
            """)
            leagues = [row[0] for row in cursor.fetchall()]

            self._league_combo.clear()
            self._league_combo.addItems(leagues)

            # Select current league if available
            current = self.ctx.config.league or "Settlers"
            idx = self._league_combo.findText(current)
            if idx >= 0:
                self._league_combo.setCurrentIndex(idx)
            elif leagues:
                self._league_combo.setCurrentIndex(0)

        except Exception as e:
            logger.error(f"Failed to load leagues: {e}")

    def _on_league_changed(self, league: str) -> None:
        """Handle league selection change."""
        if not league:
            return
        self._load_currency_data(league)
        self._load_uniques_data(league)
        self._update_aggregate_button(league)

    def _update_aggregate_button(self, league: str) -> None:
        """Update aggregate button state based on league status."""
        service = self._get_economy_service()
        if service.is_league_aggregated(league):
            self._aggregate_btn.setText("Re-aggregate")
            self._aggregate_btn.setToolTip("League data already aggregated. Click to refresh.")
        else:
            self._aggregate_btn.setText("Aggregate Data")
            self._aggregate_btn.setToolTip(
                "Pre-compute summary statistics for faster queries.\n"
                "Run this once per league after importing data."
            )

    def _on_aggregate_clicked(self) -> None:
        """Handle aggregate button click."""
        league = self._league_combo.currentText()
        if not league:
            return

        self._stats_label.setText("Aggregating...")
        self._aggregate_btn.setEnabled(False)

        try:
            service = self._get_economy_service()
            success = service.aggregate_league(league, is_finalized=True)

            if success:
                self._stats_label.setText("Aggregation complete!")
                # Reload data from summary tables
                self._load_currency_data(league)
                self._load_uniques_data(league)
                self._update_aggregate_button(league)
            else:
                self._stats_label.setText("Aggregation failed")
                QMessageBox.warning(
                    self,
                    "Aggregation Failed",
                    "Failed to aggregate league data. Check the log for details."
                )

        except Exception as e:
            logger.error(f"Failed to aggregate: {e}")
            self._stats_label.setText(f"Error: {e}")

        finally:
            self._aggregate_btn.setEnabled(True)

    def _load_currency_data(self, league: str) -> None:
        """Load currency data for the selected league."""
        try:
            service = self._get_economy_service()

            # Try summary table first
            if service.is_league_aggregated(league):
                summaries = service.get_currency_summary(league, TRACKED_CURRENCIES)
                if summaries:
                    # Convert to display format
                    rows = []
                    for s in summaries:
                        rows.append({
                            "currency_name": s.get("currency_name"),
                            "currency": s.get("currency_name"),
                            "avg_value": s.get("avg_value"),
                            "min_value": s.get("min_value"),
                            "max_value": s.get("max_value"),
                            "start_value": s.get("start_value"),
                            "end_value": s.get("end_value"),
                            "data_points": s.get("data_points"),
                        })

                    # Sort by TRACKED_CURRENCIES order
                    currency_order = {c: i for i, c in enumerate(TRACKED_CURRENCIES)}
                    rows.sort(key=lambda r: currency_order.get(r["currency_name"], 999))

                    self._currency_model.set_data(rows)

                    # Update stats from league summary
                    league_summary = service.get_league_summary(league)
                    if league_summary:
                        first = league_summary.get("first_date", "?")[:10]
                        last = league_summary.get("last_date", "?")[:10]
                        self._stats_label.setText(f"Aggregated ({first} to {last})")
                    return

            # Fall back to raw query
            self._load_currency_data_raw(league)

        except Exception as e:
            logger.error(f"Failed to load currency data: {e}")
            self._currency_model.set_data([])

    def _load_currency_data_raw(self, league: str) -> None:
        """Load currency data from raw tables (slower)."""
        rows = []
        for currency in TRACKED_CURRENCIES:
            cursor = self.ctx.db.conn.execute("""
                SELECT
                    MIN(chaos_value) as min_val,
                    MAX(chaos_value) as max_val,
                    AVG(chaos_value) as avg_val,
                    COUNT(*) as data_points
                FROM league_economy_rates
                WHERE league = ? AND currency_name = ?
            """, (league, currency))
            result = cursor.fetchone()

            if result and result[0] is not None:
                # Get start value
                start_cursor = self.ctx.db.conn.execute("""
                    SELECT chaos_value FROM league_economy_rates
                    WHERE league = ? AND currency_name = ?
                    ORDER BY rate_date ASC LIMIT 1
                """, (league, currency))
                start = start_cursor.fetchone()

                # Get end value
                end_cursor = self.ctx.db.conn.execute("""
                    SELECT chaos_value FROM league_economy_rates
                    WHERE league = ? AND currency_name = ?
                    ORDER BY rate_date DESC LIMIT 1
                """, (league, currency))
                end = end_cursor.fetchone()

                rows.append({
                    "currency_name": currency,
                    "currency": currency,
                    "avg_value": result[2],
                    "min_value": result[0],
                    "max_value": result[1],
                    "start_value": start[0] if start else None,
                    "end_value": end[0] if end else None,
                    "data_points": result[3],
                })

        self._currency_model.set_data(rows)

        # Update stats
        if rows:
            cursor = self.ctx.db.conn.execute("""
                SELECT MIN(rate_date), MAX(rate_date)
                FROM league_economy_rates WHERE league = ?
            """, (league,))
            dates = cursor.fetchone()
            if dates and dates[0]:
                self._stats_label.setText(
                    f"Raw data ({dates[0][:10]} to {dates[1][:10]})"
                )
        else:
            self._stats_label.setText("No data")

    def _load_uniques_data(self, league: str) -> None:
        """Load top unique items for the selected league."""
        try:
            service = self._get_economy_service()

            # Try summary table first
            if service.is_league_aggregated(league):
                items = service.get_top_items_summary(league, limit=10)
                if items:
                    self._uniques_model.set_data(items)
                    return

            # Fall back to raw query
            self._load_uniques_data_raw(league)

        except Exception as e:
            logger.error(f"Failed to load uniques data: {e}")
            self._uniques_model.set_data([])

    def _load_uniques_data_raw(self, league: str) -> None:
        """Load uniques data from raw tables (slower)."""
        cursor = self.ctx.db.conn.execute("""
            SELECT
                item_name,
                AVG(chaos_value) as avg_value,
                MIN(chaos_value) as min_value,
                MAX(chaos_value) as max_value,
                COUNT(*) as data_points
            FROM league_economy_items
            WHERE league = ?
            GROUP BY item_name
            HAVING COUNT(*) >= 10
            ORDER BY avg_value DESC
            LIMIT 10
        """, (league,))

        rows = []
        for idx, row in enumerate(cursor.fetchall()):
            rows.append({
                "rank": idx + 1,
                "item_name": row[0],
                "avg_value": row[1],
                "min_value": row[2],
                "max_value": row[3],
                "data_points": row[4],
            })

        self._uniques_model.set_data(rows)
