"""
gui_qt.windows.price_rankings_window

PyQt6 window for displaying Top 20 price rankings by category.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QThread, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QColor, QBrush, QPixmap, QImage
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableView,
    QAbstractItemView,
    QTabWidget,
    QProgressBar,
    QCheckBox,
    QMessageBox,
    QMenu,
)

from gui_qt.styles import COLORS, RARITY_COLORS, apply_window_icon
from gui_qt.widgets.item_context_menu import ItemContext, ItemContextMenuManager

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)

# Icon cache directory
ICON_CACHE_DIR = Path.home() / ".poe_price_checker" / "icon_cache"


class IconCache:
    """Cache for item icons downloaded from PoE APIs."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or ICON_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache of loaded pixmaps
        self._pixmaps: Dict[str, QPixmap] = {}

        # Network manager for downloading icons
        self._network_manager = QNetworkAccessManager()
        self._pending_downloads: Dict[str, List[Callable[[QPixmap], None]]] = {}

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to cache filename."""
        # Use hash of URL for filename (not for security, just cache key)
        url_hash = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()
        return f"{url_hash}.png"

    def get_icon(self, url: str, callback: Optional[Callable[[QPixmap], None]] = None) -> Optional[QPixmap]:
        """
        Get icon from cache or start download.

        Args:
            url: Icon URL
            callback: Optional callback to call when icon is ready (for async loading)

        Returns:
            QPixmap if cached, None if downloading
        """
        if not url:
            return None

        # Check in-memory cache
        if url in self._pixmaps:
            return self._pixmaps[url]

        # Check disk cache
        cache_file = self.cache_dir / self._url_to_filename(url)
        if cache_file.exists():
            pixmap = QPixmap(str(cache_file))
            if not pixmap.isNull():
                self._pixmaps[url] = pixmap
                return pixmap

        # Start download if callback provided
        if callback:
            self._download_icon(url, callback)

        return None

    def _download_icon(self, url: str, callback: Callable[[QPixmap], None]) -> None:
        """Download icon and call callback when ready."""
        # Add to pending callbacks
        if url in self._pending_downloads:
            self._pending_downloads[url].append(callback)
            return

        self._pending_downloads[url] = [callback]

        # Start download
        request = QNetworkRequest(QUrl(url))
        reply = self._network_manager.get(request)
        if reply:
            reply.finished.connect(lambda: self._on_download_finished(url, reply))

    def _on_download_finished(self, url: str, reply: QNetworkReply) -> None:
        """Handle download completion."""
        callbacks = self._pending_downloads.pop(url, [])

        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            image = QImage()
            if image.loadFromData(data):
                pixmap = QPixmap.fromImage(image)

                # Save to disk cache
                cache_file = self.cache_dir / self._url_to_filename(url)
                pixmap.save(str(cache_file), "PNG")

                # Store in memory cache
                self._pixmaps[url] = pixmap

                # Call callbacks
                for cb in callbacks:
                    try:
                        cb(pixmap)
                    except Exception as e:
                        logger.debug(f"Icon callback failed: {e}")
        else:
            logger.debug(f"Failed to download icon: {url} - {reply.errorString()}")

        reply.deleteLater()


# Global icon cache instance
_icon_cache: Optional[IconCache] = None


def get_icon_cache() -> IconCache:
    """Get or create the global icon cache."""
    global _icon_cache
    if _icon_cache is None:
        _icon_cache = IconCache()
    return _icon_cache


# Trend colors (colorblind-safe)
TREND_COLORS = {
    "up": "#4CAF50",  # Green
    "down": "#F44336",  # Red
    "stable": "#9E9E9E",  # Gray
}


class RankingsTableModel(QAbstractTableModel):
    """Table model for price rankings with icon support."""

    COLUMNS = [
        ("icon", "", 40),  # Icon column
        ("rank", "#", 35),
        ("name", "Item", 220),
        ("base_type", "Base Type", 140),
        ("chaos_value", "Chaos", 75),
        ("divine_value", "Divine", 70),
        ("trend_7d", "7d Trend", 75),
    ]

    ICON_SIZE = 32  # Icon size in pixels

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._icon_cache = get_icon_cache()
        self._trend_calculator = None
        self._league = "Standard"
        self._category = ""

    @property
    def trend_calculator(self):
        """Lazy-load trend calculator."""
        if self._trend_calculator is None:
            try:
                from core.price_trend_calculator import get_trend_calculator
                self._trend_calculator = get_trend_calculator()
            except Exception as e:
                logger.warning(f"Failed to load trend calculator: {e}")
        return self._trend_calculator

    def set_context(self, league: str, category: str) -> None:
        """Set the league and category for trend calculations."""
        self._league = league
        self._category = category

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
            elif col_key == "chaos_value":
                try:
                    return f"{float(value):,.0f}c" if value else ""
                except (ValueError, TypeError):
                    return ""
            elif col_key == "divine_value":
                try:
                    return f"{float(value):.2f}" if value else ""
                except (ValueError, TypeError):
                    return ""
            elif col_key == "base_type":
                return str(value) if value else ""
            elif col_key == "trend_7d":
                trend = row_data.get("_trend")
                if trend:
                    return trend.display_text
                return ""
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.DecorationRole:
            if col_key == "icon":
                icon_url = row_data.get("icon", "")
                if icon_url:
                    # Try to get from cache, start download if not available
                    pixmap = self._icon_cache.get_icon(
                        icon_url,
                        callback=lambda p: self._on_icon_loaded(index.row())
                    )
                    if pixmap:
                        # Scale to consistent size
                        scaled = pixmap.scaled(
                            self.ICON_SIZE, self.ICON_SIZE,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        return scaled
                return None

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("chaos_value", "divine_value", "rank", "trend_7d"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            elif col_key == "icon":
                return Qt.AlignmentFlag.AlignCenter

        elif role == Qt.ItemDataRole.ForegroundRole:
            # Trend column coloring
            if col_key == "trend_7d":
                trend = row_data.get("_trend")
                if trend:
                    color = TREND_COLORS.get(trend.trend, TREND_COLORS["stable"])
                    return QBrush(QColor(color))

            # Color items by their actual rarity
            rarity = row_data.get("rarity", "normal")
            if rarity and rarity in RARITY_COLORS:
                return QBrush(QColor(RARITY_COLORS[rarity]))

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_key == "trend_7d":
                trend = row_data.get("_trend")
                if trend:
                    return trend.tooltip
                return "No trend data available"

        elif role == Qt.ItemDataRole.SizeHintRole:
            if col_key == "icon":
                return QSize(self.ICON_SIZE + 4, self.ICON_SIZE + 4)

        return None

    def _on_icon_loaded(self, row: int) -> None:
        """Called when an icon finishes downloading."""
        if 0 <= row < len(self._data):
            # Emit dataChanged to trigger repaint of icon cell
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

    def set_data(self, items: List[Any], calculate_trends: bool = True) -> None:
        """Set the table data from RankedItem list.

        Args:
            items: List of RankedItem objects
            calculate_trends: Whether to calculate price trends (default True)
        """
        self.beginResetModel()
        self._data = []
        for item in items:
            row = {
                "icon": item.icon or "",
                "rank": item.rank,
                "name": item.name,
                "base_type": item.base_type or "",
                "chaos_value": item.chaos_value,
                "divine_value": item.divine_value,
                "rarity": item.rarity or "normal",
            }

            # Calculate trend if enabled
            if calculate_trends and self.trend_calculator and item.name:
                try:
                    trend = self.trend_calculator.get_trend(
                        item.name,
                        self._league,
                        days=7,
                        category=self._category or None
                    )
                    row["_trend"] = trend
                except Exception as e:
                    logger.debug(f"Failed to get trend for {item.name}: {e}")

            self._data.append(row)
        self.endResetModel()


class FetchWorker(QThread):
    """Background worker for fetching price data."""

    finished = pyqtSignal(dict)  # Emits rankings dict
    error = pyqtSignal(str)  # Emits error message
    progress = pyqtSignal(str)  # Emits status message

    def __init__(
        self,
        league: str,
        category: Optional[str] = None,
        slot: Optional[str] = None,
        all_slots: bool = False,
        force_refresh: bool = False,
    ):
        super().__init__()
        self.league = league
        self.category = category
        self.slot = slot
        self.all_slots = all_slots
        self.force_refresh = force_refresh

    def run(self):
        try:
            from core.price_rankings import (
                PriceRankingCache,
                Top20Calculator,
                PriceRankingHistory,
            )
            from data_sources.pricing.poe_ninja import PoeNinjaAPI

            self.progress.emit("Initializing...")

            api = PoeNinjaAPI(league=self.league)
            cache = PriceRankingCache(league=self.league)
            calculator = Top20Calculator(cache, poe_ninja_api=api)

            if self.slot:
                # Single equipment slot
                display_name = PriceRankingCache.SLOT_DISPLAY_NAMES.get(self.slot, self.slot)
                self.progress.emit(f"Fetching {display_name}...")
                ranking = calculator.refresh_slot(self.slot, force=self.force_refresh)
                rankings = {f"slot_{self.slot}": ranking} if ranking else {}
            elif self.all_slots:
                # All equipment slots
                self.progress.emit("Fetching all equipment slots...")
                rankings = calculator.refresh_all_slots(force=self.force_refresh)
            elif self.category:
                self.progress.emit(f"Fetching {self.category}...")
                ranking = calculator.refresh_category(self.category, force=self.force_refresh)
                rankings = {self.category: ranking} if ranking else {}
            else:
                self.progress.emit("Fetching all categories...")
                rankings = calculator.refresh_all(force=self.force_refresh)

            # Save to history database
            self.progress.emit("Saving to database...")
            history = PriceRankingHistory()
            history.save_all_snapshots(rankings, self.league)
            history.close()

            self.finished.emit(rankings)

        except Exception as e:
            logger.exception("Failed to fetch rankings")
            self.error.emit(str(e))


class PriceRankingsWindow(QDialog):
    """Window for viewing Top 20 price rankings."""

    # Signal emitted when user wants to price check an item from rankings
    priceCheckRequested = pyqtSignal(str)  # Emits item name
    ai_analysis_requested = pyqtSignal(str, list)  # item_text, price_results

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ctx = ctx
        self._worker: Optional[FetchWorker] = None
        self._rankings: Dict[str, Any] = {}

        # Context menu manager
        self._context_menu_manager = ItemContextMenuManager(self)
        self._context_menu_manager.set_options(
            show_inspect=False,  # Rankings items are just names
            show_price_check=True,
            show_ai=True,
            show_copy=True,
        )
        self._context_menu_manager.ai_analysis_requested.connect(self.ai_analysis_requested.emit)
        self._context_menu_manager.price_check_requested.connect(self.priceCheckRequested.emit)

        self.setWindowTitle("Price Rankings - Top 20")
        self.setMinimumSize(700, 500)
        self.resize(1000, 800)
        apply_window_icon(self)

        self._setup_ui()
        self._load_initial_data()

    def set_ai_configured_callback(self, callback: Callable[[], bool]) -> None:
        """Set callback to check if AI is configured.

        Args:
            callback: Function returning True if AI is ready to use.
        """
        self._context_menu_manager.set_ai_configured_callback(callback)

    def _setup_ui(self) -> None:
        """Create the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Controls bar
        controls = QHBoxLayout()

        # League selector
        controls.addWidget(QLabel("League:"))
        self.league_combo = QComboBox()
        self.league_combo.setMinimumWidth(150)
        self.league_combo.currentTextChanged.connect(self._on_league_changed)
        controls.addWidget(self.league_combo)

        # Category filter
        controls.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(180)
        self.category_combo.addItem("All Categories", "")
        self._add_category_items()
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        controls.addWidget(self.category_combo)

        controls.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._on_refresh)
        controls.addWidget(self.refresh_btn)

        # Force refresh checkbox
        self.force_refresh_cb = QCheckBox("Force API refresh")
        controls.addWidget(self.force_refresh_cb)

        layout.addLayout(controls)

        # Status bar
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.status_label)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Tab widget for categories
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.West)
        layout.addWidget(self.tab_widget)

        # Category tables (will be populated dynamically)
        self._category_tables: Dict[str, QTableView] = {}
        self._category_models: Dict[str, RankingsTableModel] = {}

    def _add_category_items(self) -> None:
        """Add category items to combo box."""
        from core.price_rankings import PriceRankingCache

        # Add groups first
        self.category_combo.addItem("── Groups ──", "")
        self.category_combo.addItem("  Uniques (all types)", "group:uniques")
        self.category_combo.addItem("  Consumables", "group:consumables")
        self.category_combo.addItem("  Divination Cards", "group:cards")
        self.category_combo.addItem("  All Equipment Slots", "group:slots")

        self.category_combo.addItem("── Categories ──", "")
        for key, name in PriceRankingCache.CATEGORIES.items():
            self.category_combo.addItem(f"  {name}", key)

        # Add equipment slots
        self.category_combo.addItem("── Equipment Slots ──", "")
        for key, name in PriceRankingCache.SLOT_DISPLAY_NAMES.items():
            self.category_combo.addItem(f"  {name}", f"slot:{key}")

    def _load_initial_data(self) -> None:
        """Load initial league list and data."""
        # Populate leagues
        try:
            from data_sources.pricing.poe_ninja import PoeNinjaAPI
            api = PoeNinjaAPI()
            leagues = api.get_current_leagues()

            # Add temp leagues first
            temp_leagues = [lg for lg in leagues if lg['name'] not in ['Standard', 'Hardcore']]
            for league in temp_leagues:
                self.league_combo.addItem(league['displayName'], league['name'])

            # Then permanent leagues
            self.league_combo.addItem("Standard", "Standard")
            self.league_combo.addItem("Hardcore", "Hardcore")

        except Exception as e:
            logger.warning(f"Failed to fetch leagues: {e}")
            self.league_combo.addItem("Standard", "Standard")

        # Trigger initial load
        self._on_refresh()

    def _on_league_changed(self, text: str) -> None:
        """Handle league selection change."""
        self._on_refresh()

    def _on_category_changed(self, index: int) -> None:
        """Handle category filter change."""
        category = self.category_combo.currentData()

        # If specific category selected, switch to that tab
        if category and not category.startswith("group:"):
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i).lower().replace(" ", "_") == category:
                    self.tab_widget.setCurrentIndex(i)
                    break

    def _on_refresh(self) -> None:
        """Fetch fresh data."""
        if self._worker and self._worker.isRunning():
            return

        league = self.league_combo.currentData() or "Standard"
        category_data = self.category_combo.currentData()

        # Determine what to fetch
        category = None
        slot = None
        all_slots = False

        if category_data:
            if category_data.startswith("slot:"):
                # Single equipment slot
                slot = category_data.split(":")[1]
            elif category_data == "group:slots":
                # All equipment slots
                all_slots = True
            elif not category_data.startswith("group:"):
                # Regular category
                category = category_data

        force_refresh = self.force_refresh_cb.isChecked()

        # Show progress
        self.progress_bar.show()
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("Fetching data...")

        # Start worker
        self._worker = FetchWorker(
            league,
            category=category,
            slot=slot,
            all_slots=all_slots,
            force_refresh=force_refresh,
        )
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.progress.connect(self._on_fetch_progress)
        self._worker.start()

    def _on_fetch_progress(self, message: str) -> None:
        """Update progress message."""
        self.status_label.setText(message)

    def _on_fetch_finished(self, rankings: Dict[str, Any]) -> None:
        """Handle successful data fetch."""
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)

        self._rankings = rankings
        self._update_tabs()

        # Update status
        total_items = sum(len(r.items) for r in rankings.values() if r)
        self.status_label.setText(
            f"Loaded {len(rankings)} categories, {total_items} items"
        )

    def _on_fetch_error(self, error: str) -> None:
        """Handle fetch error."""
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(f"Error: {error}")

        QMessageBox.warning(
            self,
            "Fetch Error",
            f"Failed to fetch price rankings:\n\n{error}"
        )

    def _update_tabs(self) -> None:
        """Update tab widget with rankings data."""
        from core.price_rankings import PriceRankingCache

        # Clear existing tabs
        self.tab_widget.clear()
        self._category_tables.clear()
        self._category_models.clear()

        # Filter categories based on selection
        category_filter = self.category_combo.currentData()

        # Build allowed set based on filter
        allowed = None  # None means show all from current results
        if category_filter and category_filter.startswith("group:"):
            group = category_filter.split(":")[1]
            from core.price_rankings import UNIQUE_CATEGORIES, CONSUMABLE_CATEGORIES, CARD_CATEGORIES
            if group == "uniques":
                allowed = set(UNIQUE_CATEGORIES)
            elif group == "consumables":
                allowed = set(CONSUMABLE_CATEGORIES)
            elif group == "cards":
                allowed = set(CARD_CATEGORIES)
            elif group == "slots":
                # All slot keys start with "slot_"
                allowed = {k for k in self._rankings.keys() if k.startswith("slot_")}
        elif category_filter and category_filter.startswith("slot:"):
            # Single slot
            slot_name = category_filter.split(":")[1]
            allowed = {f"slot_{slot_name}"}
        elif category_filter:
            allowed = {category_filter}

        # Create tabs for each ranking
        for category, ranking in self._rankings.items():
            if allowed is not None and category not in allowed:
                continue
            if not ranking:
                continue

            # Create table
            table = QTableView()
            model = RankingsTableModel(table)
            model.set_data(ranking.items)
            table.setModel(model)

            # Configure table
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            table.setAlternatingRowColors(True)
            v_header = table.verticalHeader()
            if v_header:
                v_header.setVisible(False)

            # Enable context menu
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(
                lambda pos, t=table, m=model: self._show_context_menu(pos, t, m)
            )

            # Set row height for icons
            v_header = table.verticalHeader()
            if v_header:
                v_header.setDefaultSectionSize(RankingsTableModel.ICON_SIZE + 6)

            # Set column widths
            h_header = table.horizontalHeader()
            if h_header:
                for i, (_, _, width) in enumerate(RankingsTableModel.COLUMNS):
                    h_header.resizeSection(i, width)
                h_header.setStretchLastSection(True)

            # Enable icon column to resize properly
            table.setIconSize(QSize(RankingsTableModel.ICON_SIZE, RankingsTableModel.ICON_SIZE))

            # Store references
            self._category_tables[category] = table
            self._category_models[category] = model

            # Add tab - use display_name from ranking or look up from categories/slots
            if ranking.display_name:
                display_name = ranking.display_name
            elif category.startswith("slot_"):
                slot_key = category[5:]  # Remove "slot_" prefix
                display_name = PriceRankingCache.SLOT_DISPLAY_NAMES.get(slot_key, slot_key.title())
            else:
                display_name = PriceRankingCache.CATEGORIES.get(category, category)
            self.tab_widget.addTab(table, display_name)

    def _show_context_menu(
        self,
        pos,
        table: QTableView,
        model: RankingsTableModel,
    ) -> None:
        """Show context menu for right-click on table row."""
        index = table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        if row < 0 or row >= len(model._data):
            return

        item_data = model._data[row]
        item_name = item_data.get("name", "")
        if not item_name:
            return

        # Get price data
        chaos_value = item_data.get("chaos_value", 0) or 0
        divine_value = item_data.get("divine_value", 0) or 0

        # Build item context
        item_context = ItemContext(
            item_name=item_name,
            item_text=item_name,  # Use name as item text for rankings
            chaos_value=float(chaos_value) if chaos_value else 0,
            divine_value=float(divine_value) if divine_value else 0,
            source="poe.ninja",
        )

        # Show context menu
        viewport = table.viewport()
        if viewport:
            self._context_menu_manager.show_menu(
                viewport.mapToGlobal(pos),
                item_context,
                table,
            )

    def _on_price_check_item(self, item_name: str) -> None:
        """Handle price check request from context menu."""
        logger.info(f"Price check requested for: {item_name}")
        self.priceCheckRequested.emit(item_name)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            logger.debug(f"Copied to clipboard: {text}")

    def closeEvent(self, event) -> None:
        """Clean up when window closes."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)
        super().closeEvent(event)
