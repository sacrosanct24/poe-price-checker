"""
Compact price rankings panel for sidebar embedding.

Displays Top 20 price rankings in a collapsible sidebar panel.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QColor, QBrush, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableView,
    QAbstractItemView,
    QHeaderView,
    QFrame,
)

from gui_qt.styles import RARITY_COLORS

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class CompactRankingsModel(QAbstractTableModel):
    """Compact table model for sidebar rankings display."""

    COLUMNS = [
        ("icon", "", 26),  # Icon column
        ("rank", "#", 18),  # Very compact rank
        ("name", "Item", 120),  # Stretches to fill
        ("chaos_value", "Price", 55),
    ]

    ICON_SIZE = 24  # Smaller icons for sidebar

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._icon_cache: Optional[Any] = None

    def _get_icon_cache(self):
        """Lazy-load icon cache."""
        if self._icon_cache is None:
            try:
                from gui_qt.windows.price_rankings_window import get_icon_cache
                self._icon_cache = get_icon_cache()
            except ImportError:
                pass
        return self._icon_cache

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
            if col_key == "icon":
                return None  # Icon handled by DecorationRole
            if col_key == "chaos_value":
                try:
                    return f"{float(value):,.0f}c" if value else ""
                except (ValueError, TypeError):
                    return ""
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.DecorationRole:
            if col_key == "icon":
                icon_url = row_data.get("icon", "")
                if icon_url:
                    cache = self._get_icon_cache()
                    if cache:
                        pixmap = cache.get_icon(
                            icon_url,
                            callback=lambda p: self._on_icon_loaded(index.row())
                        )
                        if pixmap:
                            scaled = pixmap.scaled(
                                self.ICON_SIZE, self.ICON_SIZE,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation
                            )
                            return scaled
                return None

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("chaos_value", "rank"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            elif col_key == "icon":
                return Qt.AlignmentFlag.AlignCenter

        elif role == Qt.ItemDataRole.ForegroundRole:
            rarity = row_data.get("rarity", "normal")
            if rarity and rarity in RARITY_COLORS:
                return QBrush(QColor(RARITY_COLORS[rarity]))

        elif role == Qt.ItemDataRole.ToolTipRole:
            divine = row_data.get("divine_value", 0)
            if divine:
                return f"{row_data.get('name', '')} - {divine:.2f} divine"
            return row_data.get("name", "")

        elif role == Qt.ItemDataRole.SizeHintRole:
            if col_key == "icon":
                return QSize(self.ICON_SIZE + 4, self.ICON_SIZE + 4)

        return None

    def _on_icon_loaded(self, row: int) -> None:
        """Called when an icon finishes downloading."""
        if 0 <= row < len(self._data):
            index = self.index(row, 0)  # Icon is column 0
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])

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

    def set_data(self, items: List[Any]) -> None:
        """Set the table data from RankedItem list."""
        self.beginResetModel()
        self._data = []
        for item in items[:20]:  # Limit to top 20
            self._data.append({
                "icon": getattr(item, "icon", "") or "",
                "rank": item.rank,
                "name": item.name,
                "chaos_value": item.chaos_value,
                "divine_value": getattr(item, "divine_value", 0),
                "rarity": getattr(item, "rarity", "normal") or "normal",
            })
        self.endResetModel()

    def get_item_name(self, row: int) -> Optional[str]:
        """Get item name for a row."""
        if 0 <= row < len(self._data):
            return self._data[row].get("name")
        return None


class PriceRankingsPanel(QFrame):
    """
    Collapsible price rankings panel for sidebar.

    Signals:
        price_check_requested(str): Emitted when user wants to price check an item.
        visibility_changed(bool): Emitted when panel is shown/hidden.
    """

    price_check_requested = pyqtSignal(str)
    visibility_changed = pyqtSignal(bool)

    # Common categories for quick access
    QUICK_CATEGORIES = [
        ("currency", "Currency"),
        ("divination_cards", "Div Cards"),
        ("unique_weapons", "Unique Weapons"),
        ("unique_armour", "Unique Armour"),
        ("unique_accessories", "Unique Accessories"),
        ("scarabs", "Scarabs"),
        ("fragments", "Fragments"),
    ]

    def __init__(
        self,
        ctx: Optional["AppContext"] = None,
        parent: Optional[QWidget] = None,
        auto_load: bool = True,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self._is_loading = False
        self._cached_rankings: Dict[str, Any] = {}

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

        # Auto-load initial data after a short delay (allow UI to render first)
        if auto_load:
            QTimer.singleShot(500, self.load_initial_data)

    def _setup_ui(self) -> None:
        """Create the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header with toggle
        header = QHBoxLayout()
        header.setSpacing(4)

        self._title = QLabel("Top 20 Rankings")
        self._title.setStyleSheet("font-weight: bold;")
        header.addWidget(self._title)

        header.addStretch()

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedSize(24, 24)
        self._refresh_btn.setToolTip("Refresh rankings")
        self._refresh_btn.clicked.connect(self._on_refresh)
        header.addWidget(self._refresh_btn)

        layout.addLayout(header)

        # Category selector
        self._category_combo = QComboBox()
        self._category_combo.setMaximumHeight(26)
        for key, name in self.QUICK_CATEGORIES:
            self._category_combo.addItem(name, key)
        self._category_combo.currentIndexChanged.connect(self._on_category_changed)
        layout.addWidget(self._category_combo)

        # Status label
        self._status = QLabel("")
        self._status.setStyleSheet("color: palette(mid); font-size: 11px;")
        layout.addWidget(self._status)

        # Rankings table
        self._table = QTableView()
        self._model = CompactRankingsModel(self)
        self._table.setModel(self._model)

        # Configure table for compact display
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Remove focus rectangle

        # Hide vertical header (row numbers)
        v_header = self._table.verticalHeader()
        if v_header:
            v_header.setVisible(False)
            v_header.setDefaultSectionSize(CompactRankingsModel.ICON_SIZE + 4)

        # Hide horizontal header (column labels) for compact look
        h_header = self._table.horizontalHeader()
        if h_header:
            h_header.setVisible(False)
            for i, (_, _, width) in enumerate(CompactRankingsModel.COLUMNS):
                h_header.resizeSection(i, width)
            h_header.setStretchLastSection(False)
            h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Name column stretches

        # Double-click to price check
        self._table.doubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self._table, 1)

    def _on_category_changed(self, index: int) -> None:
        """Handle category selection change."""
        category = self._category_combo.currentData()
        if category:
            self._load_category(category)

    def _on_refresh(self) -> None:
        """Refresh current category."""
        category = self._category_combo.currentData()
        if category:
            self._load_category(category, force=True)

    def _load_category(self, category: str, force: bool = False) -> None:
        """Load rankings for a category."""
        if self._is_loading:
            return

        # Check cache first
        if not force and category in self._cached_rankings:
            self._display_rankings(self._cached_rankings[category])
            return

        self._is_loading = True
        self._status.setText("Loading...")
        self._refresh_btn.setEnabled(False)

        try:
            from core.price_rankings import PriceRankingCache, Top20Calculator
            from data_sources.pricing.poe_ninja import PoeNinjaAPI

            league = "Standard"
            if self.ctx and hasattr(self.ctx, 'config'):
                league = self.ctx.config.league or "Standard"

            api = PoeNinjaAPI(league=league)
            cache = PriceRankingCache(league=league)
            calculator = Top20Calculator(cache, poe_ninja_api=api)

            ranking = calculator.refresh_category(category, force=force)

            if ranking:
                self._cached_rankings[category] = ranking
                self._display_rankings(ranking)
            else:
                self._status.setText("No data available")
                self._model.set_data([])

        except Exception as e:
            logger.warning(f"Failed to load rankings for {category}: {e}")
            self._status.setText(f"Error: {str(e)[:30]}")
        finally:
            self._is_loading = False
            self._refresh_btn.setEnabled(True)

    def _display_rankings(self, ranking) -> None:
        """Display ranking data in the table."""
        if ranking and hasattr(ranking, 'items'):
            self._model.set_data(ranking.items)
            self._status.setText(f"{len(ranking.items)} items")
        else:
            self._model.set_data([])
            self._status.setText("No items")

    def _on_item_double_clicked(self, index: QModelIndex) -> None:
        """Handle double-click on item row."""
        item_name = self._model.get_item_name(index.row())
        if item_name:
            self.price_check_requested.emit(item_name)

    def refresh(self) -> None:
        """Refresh the current category data."""
        self._on_refresh()

    def load_initial_data(self) -> None:
        """Load initial category data."""
        # Load first category by default
        if self._category_combo.count() > 0:
            self._on_category_changed(0)
