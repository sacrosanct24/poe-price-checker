"""
Stash Viewer Window.

Displays stash tabs from Path of Exile with item valuations.
Features:
- League selector
- Tab list with values (like in-game stash)
- Item list sorted by value
- Minimum value filter
- POESESSID configuration
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QPushButton,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QTableView,
    QAbstractItemView,
    QProgressBar,
    QFormLayout,
    QMessageBox,
    QTextBrowser,
    QApplication,
    QMenu,
)

from gui_qt.styles import COLORS, apply_window_icon, get_rarity_color
from gui_qt.widgets.item_context_menu import ItemContext, ItemContextMenuManager
from core.stash_valuator import (
    StashValuator,
    ValuationResult,
    PricedItem,
    PriceSource,
)
from core.quick_verdict import QuickVerdictCalculator, Verdict, VerdictResult
from core.stash_storage import get_stash_storage, StashStorageService
from core.stash_diff_engine import StashDiffEngine, StashDiff
from data_sources.poe_stash_api import PoEStashClient, StashSnapshot, get_available_leagues

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class FetchWorker(QThread):
    """Background worker for fetching and valuating stash."""

    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(object, object)  # (ValuationResult, StashSnapshot)
    error = pyqtSignal(str)
    rate_limited = pyqtSignal(int, int)  # wait_seconds, attempt

    def __init__(
        self,
        poesessid: str,
        account_name: str,
        league: str,
        max_tabs: Optional[int] = None,
    ):
        super().__init__()
        self.poesessid = poesessid
        self.account_name = account_name
        self.league = league
        self.max_tabs = max_tabs

    def run(self):
        """Fetch and valuate stash in background."""
        try:
            valuator = StashValuator()

            # Load prices
            self.progress.emit(0, 0, "Loading prices from poe.ninja...")

            def price_progress(cur, total, name):
                self.progress.emit(cur, total, f"Loading {name}...")

            valuator.load_prices(self.league, progress_callback=price_progress)

            # Connect to PoE
            self.progress.emit(0, 0, "Connecting to Path of Exile...")

            def rate_limit_callback(wait_seconds: int, attempt: int):
                """Called when rate limited - emit signal to update UI."""
                self.rate_limited.emit(wait_seconds, attempt)

            client = PoEStashClient(
                self.poesessid,
                rate_limit_callback=rate_limit_callback,
            )

            if not client.verify_session():
                self.error.emit("Invalid POESESSID - session verification failed")
                return

            # Fetch stash
            def stash_progress(cur, total):
                self.progress.emit(cur, total, f"Fetching tab {cur}/{total}...")

            snapshot = client.fetch_all_stashes(
                self.account_name,
                self.league,
                max_tabs=self.max_tabs,
                progress_callback=stash_progress,
            )

            # Valuate
            def val_progress(cur, total, name):
                self.progress.emit(cur, total, f"Pricing {name}...")

            result = valuator.valuate_snapshot(snapshot, progress_callback=val_progress)

            # Emit both result and snapshot for storage
            self.finished.emit(result, snapshot)

        except Exception as e:
            logger.exception("Stash fetch failed")
            self.error.emit(str(e))


class ItemTableModel(QAbstractTableModel):
    """Table model for priced items."""

    COLUMNS = [
        ("verdict", "📊", 45),  # Verdict emoji column
        ("display_name", "Item", 250),
        ("stack_size", "Qty", 50),
        ("unit_price", "Unit", 70),
        ("total_price", "Total", 80),
        ("rarity", "Rarity", 80),
        ("price_source", "Source", 80),
    ]

    # Verdict colors
    VERDICT_COLORS = {
        Verdict.KEEP: QColor("#22bb22"),    # Green
        Verdict.VENDOR: QColor("#bb2222"),  # Red
        Verdict.MAYBE: QColor("#bbbb22"),   # Yellow
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._items: List[PricedItem] = []
        self._min_value: float = 0.0
        self._search_text: str = ""
        self._verdict_calculator = QuickVerdictCalculator()
        self._verdict_cache: dict = {}  # Cache verdicts by item id

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._filtered_items())

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def _filtered_items(self) -> List[PricedItem]:
        """Get items filtered by minimum value and search text."""
        items = [i for i in self._items if i.total_price >= self._min_value]
        if self._search_text:
            search_lower = self._search_text.lower()
            items = [i for i in items if search_lower in i.display_name.lower()]
        return items

    def _get_verdict(self, item: PricedItem) -> VerdictResult:
        """Get verdict for an item, using cache if available."""
        # Create a cache key from item identity
        cache_key = (item.name, item.type_line, item.tab_name, item.stack_size)
        if cache_key in self._verdict_cache:
            return self._verdict_cache[cache_key]

        # For items evaluated by RareItemEvaluator, use their eval_tier directly
        # This ensures consistency between the two evaluation systems
        if item.price_source == PriceSource.RARE_EVALUATED and item.eval_tier:
            tier = item.eval_tier.lower()
            if tier == "excellent":
                verdict = VerdictResult(
                    verdict=Verdict.KEEP,
                    explanation="Excellent rare - high-value affixes",
                    detailed_reasons=[item.eval_summary] if item.eval_summary else [],
                    estimated_value=item.total_price if item.total_price > 0 else None,
                    confidence="high",
                )
            elif tier == "good":
                verdict = VerdictResult(
                    verdict=Verdict.MAYBE,
                    explanation="Good rare - worth checking",
                    detailed_reasons=[item.eval_summary] if item.eval_summary else [],
                    estimated_value=item.total_price if item.total_price > 0 else None,
                    confidence="medium",
                )
            else:  # average, vendor, etc.
                verdict = VerdictResult(
                    verdict=Verdict.VENDOR,
                    explanation=f"Rare evaluated as {tier}",
                    detailed_reasons=[item.eval_summary] if item.eval_summary else [],
                    estimated_value=item.total_price if item.total_price > 0 else None,
                    confidence="medium",
                )
            self._verdict_cache[cache_key] = verdict
            return verdict

        # Create a simple object for the calculator
        class ItemAdapter:
            """Adapter to make PricedItem work with QuickVerdictCalculator."""
            def __init__(self, priced_item: PricedItem):
                self.rarity = priced_item.rarity
                self.name = priced_item.name
                self.base_type = priced_item.base_type
                self.item_class = priced_item.item_class
                self.sockets = len(priced_item.sockets.replace("-", "").replace(" ", ""))
                self.links = priced_item.links
                self.item_level = priced_item.ilvl
                self.corrupted = priced_item.corrupted

                # Extract from raw_item if available
                raw = priced_item.raw_item or {}
                self.explicits = raw.get("explicitMods", [])
                self.implicits = raw.get("implicitMods", [])
                self.influences = list(raw.get("influences", {}).keys()) if raw.get("influences") else []
                self.is_fractured = raw.get("fractured", False)
                self.is_synthesised = raw.get("synthesised", False)

        adapter = ItemAdapter(item)
        # Use total_price as chaos value if available
        price = item.total_price if item.total_price > 0 else None
        verdict = self._verdict_calculator.calculate(adapter, price_chaos=price)

        self._verdict_cache[cache_key] = verdict
        return verdict

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        items = self._filtered_items()
        if not index.isValid() or not (0 <= index.row() < len(items)):
            return None

        item = items[index.row()]
        col_key = self.COLUMNS[index.column()][0]

        if role == Qt.ItemDataRole.DisplayRole:
            if col_key == "verdict":
                verdict = self._get_verdict(item)
                return verdict.emoji
            elif col_key == "display_name":
                return item.display_name
            elif col_key == "stack_size":
                return str(item.stack_size) if item.stack_size > 1 else ""
            elif col_key == "unit_price":
                if item.unit_price >= 1:
                    return f"{item.unit_price:.1f}c"
                elif item.unit_price > 0:
                    return f"{item.unit_price:.2f}c"
                return ""
            elif col_key == "total_price":
                return item.display_price
            elif col_key == "rarity":
                return item.rarity
            elif col_key == "price_source":
                if item.price_source == PriceSource.POE_NINJA:
                    return "poe.ninja"
                elif item.price_source == PriceSource.POE_PRICES:
                    return "poeprices"
                elif item.price_source == PriceSource.RARE_EVALUATED:
                    return "eval"
                return ""
            return ""

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_key == "verdict":
                verdict = self._get_verdict(item)
                tooltip = f"{verdict.verdict.value.upper()}: {verdict.explanation}"
                if verdict.detailed_reasons:
                    tooltip += "\n\n" + "\n".join(f"• {r}" for r in verdict.detailed_reasons[:5])
                if verdict.has_meta_bonus:
                    tooltip += f"\n\n🔥 Meta bonus: +{verdict.meta_bonus_applied:.0f}"
                return tooltip
            return None

        elif role == Qt.ItemDataRole.ForegroundRole:
            # Color verdict column by verdict type
            if col_key == "verdict":
                verdict = self._get_verdict(item)
                return self.VERDICT_COLORS.get(verdict.verdict, QColor(COLORS["text"]))
            # Color by rarity
            rarity_colors = {
                "Unique": QColor(COLORS["unique"]),
                "Rare": QColor(COLORS["rare"]),
                "Magic": QColor(COLORS["magic"]),
                "Currency": QColor(COLORS["currency"]),
                "Gem": QColor(COLORS["gem"]),
                "Divination": QColor(COLORS["divination"]),
            }
            if col_key == "display_name":
                return rarity_colors.get(item.rarity, QColor(COLORS["text"]))
            # Color by value
            if col_key == "total_price":
                if item.total_price >= 100:
                    return QColor(COLORS["high_value"])
                elif item.total_price >= 10:
                    return QColor(COLORS["medium_value"])
            return None

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key == "verdict":
                return Qt.AlignmentFlag.AlignCenter
            if col_key in ("stack_size", "unit_price", "total_price"):
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

    def set_items(self, items: List[PricedItem]) -> None:
        """Set items to display."""
        self.beginResetModel()
        self._items = items
        self._verdict_cache.clear()  # Clear cache when items change
        self.endResetModel()

    def set_meta_weights(self, meta_weights: dict) -> None:
        """Set meta weights for verdict calculation."""
        self._verdict_calculator.set_meta_weights(meta_weights)
        self._verdict_cache.clear()  # Clear cache to recalculate with new weights
        # Refresh display
        self.beginResetModel()
        self.endResetModel()

    def set_min_value(self, min_value: float) -> None:
        """Set minimum value filter."""
        self.beginResetModel()
        self._min_value = min_value
        self.endResetModel()

    def set_search_text(self, text: str) -> None:
        """Set search text filter."""
        self.beginResetModel()
        self._search_text = text.strip()
        self.endResetModel()

    def get_item(self, row: int) -> Optional[PricedItem]:
        """Get item at row."""
        items = self._filtered_items()
        if 0 <= row < len(items):
            return items[row]
        return None


class StashItemDetailsDialog(QDialog):
    """Dialog showing stash item details with copy functionality."""

    def __init__(self, item: PricedItem, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.item = item

        self.setWindowTitle("Item Details")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.resize(450, 400)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Item header
        name_color = get_rarity_color(self.item.rarity.lower())
        header_html = f'''
        <div style="text-align: center;">
            <p style="font-size: 16px; font-weight: bold; color: {name_color}; margin: 4px;">
                {self.item.display_name}
            </p>
            <p style="color: {COLORS["text_secondary"]}; margin: 2px;">
                {self.item.rarity} • {self.item.item_class}
            </p>
        </div>
        '''

        header_browser = QTextBrowser()
        header_browser.setMaximumHeight(80)
        header_browser.setHtml(header_html)
        header_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(header_browser)

        # Price info
        price_html = f'''
        <table style="width: 100%;">
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Stack Size:</td>
                <td style="text-align: right;">{self.item.stack_size}</td>
            </tr>
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Unit Price:</td>
                <td style="text-align: right; color: {COLORS["currency"]};">
                    {self.item.unit_price:.2f}c
                </td>
            </tr>
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Total Value:</td>
                <td style="text-align: right; font-weight: bold; color: {COLORS["high_value"]};">
                    {self.item.display_price}
                </td>
            </tr>
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Price Source:</td>
                <td style="text-align: right;">
                    {"poe.ninja" if self.item.price_source == PriceSource.POE_NINJA else "poeprices" if self.item.price_source == PriceSource.POE_PRICES else "unknown"}
                </td>
            </tr>
        </table>
        '''

        price_browser = QTextBrowser()
        price_browser.setMaximumHeight(120)
        price_browser.setHtml(price_html)
        price_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        layout.addWidget(price_browser)

        # Tab info
        if self.item.tab_name:
            tab_label = QLabel(f"Found in: {self.item.tab_name}")
            tab_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(tab_label)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()

        copy_name_btn = QPushButton("Copy Name")
        copy_name_btn.clicked.connect(self._copy_name)
        btn_row.addWidget(copy_name_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _copy_name(self) -> None:
        """Copy item name to clipboard."""
        QApplication.clipboard().setText(self.item.display_name)
        QMessageBox.information(self, "Copied", "Item name copied to clipboard.")


class StashViewerWindow(QDialog):
    """Window for viewing and valuating stash tabs."""

    # Signals for item actions
    ai_analysis_requested = pyqtSignal(str, list)  # item_text, price_results
    price_check_requested = pyqtSignal(str)  # item_text

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ctx = ctx
        self._worker: Optional[FetchWorker] = None
        self._result: Optional[ValuationResult] = None
        self._current_snapshot: Optional[StashSnapshot] = None
        self._ai_configured_callback: Optional[Callable[[], bool]] = None

        # Storage service for persistence
        self._storage: StashStorageService = get_stash_storage(ctx.db)

        # Diff engine for detecting changes
        self._diff_engine = StashDiffEngine()

        # Context menu manager for item actions
        self._context_menu_manager = ItemContextMenuManager(self)
        self._context_menu_manager.set_options(
            show_inspect=True,
            show_price_check=False,  # Stash items don't have item text for price check
            show_ai=True,
            show_copy=True,
        )
        self._context_menu_manager.ai_analysis_requested.connect(self.ai_analysis_requested.emit)
        self._context_menu_manager.inspect_requested.connect(self._on_inspect_item_context)

        self.setWindowTitle("Stash Viewer")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_settings()
        self._load_cached_stash()

    def set_ai_configured_callback(self, callback: Callable[[], bool]) -> None:
        """Set callback to check if AI is configured.

        Args:
            callback: Function returning True if AI is ready to use.
        """
        self._ai_configured_callback = callback
        self._context_menu_manager.set_ai_configured_callback(callback)

    def set_meta_weights(self, meta_weights: dict) -> None:
        """Set meta weights for Quick Verdict calculation.

        Args:
            meta_weights: Meta weight data from RareItemEvaluator.meta_weights
        """
        self._item_model.set_meta_weights(meta_weights)

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Top toolbar
        toolbar = QHBoxLayout()

        # League selector
        toolbar.addWidget(QLabel("League:"))
        self.league_combo = QComboBox()
        self.league_combo.setMinimumWidth(140)
        self._update_league_combo()
        toolbar.addWidget(self.league_combo)

        # Include Standard checkbox
        self.include_standard_cb = QCheckBox("Include Standard")
        self.include_standard_cb.setChecked(False)
        self.include_standard_cb.stateChanged.connect(self._on_include_standard_changed)
        toolbar.addWidget(self.include_standard_cb)

        toolbar.addSpacing(20)

        # Account info (read-only display)
        toolbar.addWidget(QLabel("Account:"))
        self.account_label = QLabel("-")
        self.account_label.setStyleSheet(f"color: {COLORS['accent']};")
        toolbar.addWidget(self.account_label)

        toolbar.addStretch()

        # Total value display
        self.total_label = QLabel("Total: -")
        self.total_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {COLORS['high_value']};"
        )
        toolbar.addWidget(self.total_label)

        toolbar.addSpacing(20)

        # Grid View button
        self.grid_view_btn = QPushButton("Grid View")
        self.grid_view_btn.setToolTip("View stash as visual grid with heatmap")
        self.grid_view_btn.clicked.connect(self._show_grid_view)
        self.grid_view_btn.setEnabled(False)  # Enabled after fetch
        toolbar.addWidget(self.grid_view_btn)

        # Settings button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self._show_settings)
        toolbar.addWidget(self.settings_btn)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_stash)
        toolbar.addWidget(self.refresh_btn)

        layout.addLayout(toolbar)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.status_label)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Tab list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Stash Tabs"))

        self.tab_list = QListWidget()
        self.tab_list.setAlternatingRowColors(True)
        self.tab_list.currentRowChanged.connect(self._on_tab_selected)
        left_layout.addWidget(self.tab_list)

        splitter.addWidget(left_panel)

        # Right panel - Item table
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Filter row
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Min Value:"))
        self.min_value_spin = QSpinBox()
        self.min_value_spin.setRange(0, 10000)
        self.min_value_spin.setValue(1)
        self.min_value_spin.setSuffix(" c")
        self.min_value_spin.valueChanged.connect(self._on_min_value_changed)
        filter_row.addWidget(self.min_value_spin)

        filter_row.addSpacing(10)

        filter_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter items...")
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_row.addWidget(self.search_input)

        filter_row.addStretch()

        self.item_count_label = QLabel("0 items")
        filter_row.addWidget(self.item_count_label)

        right_layout.addLayout(filter_row)

        # Item table
        self._item_model = ItemTableModel(self)
        self.item_table = QTableView()
        self.item_table.setModel(self._item_model)
        self.item_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.item_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.item_table.setAlternatingRowColors(True)
        self.item_table.setSortingEnabled(True)
        self.item_table.doubleClicked.connect(self._on_item_double_click)

        # Context menu for items
        self.item_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.item_table.customContextMenuRequested.connect(self._show_item_context_menu)

        # Column widths
        header = self.item_table.horizontalHeader()
        for i, (_, _, width) in enumerate(ItemTableModel.COLUMNS):
            self.item_table.setColumnWidth(i, width)
        header.setStretchLastSection(True)

        right_layout.addWidget(self.item_table)

        splitter.addWidget(right_panel)

        # Set splitter sizes (30% tabs, 70% items)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

        # Bottom info
        bottom_row = QHBoxLayout()
        self.last_fetch_label = QLabel("")
        self.last_fetch_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        bottom_row.addWidget(self.last_fetch_label)

        bottom_row.addStretch()

        self.priced_label = QLabel("")
        self.priced_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        bottom_row.addWidget(self.priced_label)

        layout.addLayout(bottom_row)

    def _load_settings(self) -> None:
        """Load settings from config."""
        if self.ctx.config.account_name:
            self.account_label.setText(self.ctx.config.account_name)

        # Show last fetch time
        last_fetch = self.ctx.config.stash_last_fetch
        if last_fetch:
            self.last_fetch_label.setText(f"Last fetched: {last_fetch}")

    def _load_cached_stash(self) -> None:
        """Load the most recent cached stash snapshot on startup."""
        if not self.ctx.config.account_name:
            return

        league = self.league_combo.currentText()
        if not league:
            return

        try:
            stored = self._storage.load_latest_snapshot(
                self.ctx.config.account_name,
                league,
            )

            if stored:
                # Reconstruct valuation result
                result = self._storage.reconstruct_valuation(stored)
                if result:
                    self._result = result
                    self._display_valuation_result(result)

                    # Also reconstruct snapshot for diff engine
                    snapshot = self._storage.reconstruct_snapshot(stored)
                    if snapshot:
                        self._current_snapshot = snapshot
                        self._diff_engine.set_before_snapshot(snapshot)

                    # Update last fetch display
                    fetch_time = stored.fetched_at.strftime("%Y-%m-%d %H:%M")
                    self.last_fetch_label.setText(f"Last fetched: {fetch_time} (cached)")
                    self.status_label.setText("Loaded from cache - click Refresh to update")

                    logger.info(
                        f"Loaded cached stash: {stored.total_items} items, "
                        f"{stored.total_chaos_value:.0f}c"
                    )

        except Exception as e:
            logger.warning(f"Failed to load cached stash: {e}")

    def _update_league_combo(self) -> None:
        """Update league combo based on include_standard checkbox."""
        current = self.league_combo.currentText()
        include_standard = (
            hasattr(self, 'include_standard_cb') and
            self.include_standard_cb.isChecked()
        )

        self.league_combo.clear()
        for league in get_available_leagues(include_standard=include_standard):
            self.league_combo.addItem(league)

        # Try to restore previous selection
        if current:
            idx = self.league_combo.findText(current)
            if idx >= 0:
                self.league_combo.setCurrentIndex(idx)

    def _on_include_standard_changed(self, state: int) -> None:
        """Handle include standard checkbox change."""
        self._update_league_combo()

    def _show_grid_view(self) -> None:
        """Show stash grid visualization dialog."""
        if not self._result:
            QMessageBox.warning(
                self,
                "No Data",
                "Please fetch stash data first using the Refresh button."
            )
            return

        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog
        dialog = StashGridDialog(self._result, self)
        dialog.exec()

    def _show_settings(self) -> None:
        """Show settings dialog for POESESSID."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Stash Settings")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Instructions
        info_label = QLabel(
            "To access your stash, you need your POESESSID cookie.\n\n"
            "To get it:\n"
            "1. Log into pathofexile.com\n"
            "2. Press F12 to open Developer Tools\n"
            "3. Go to Application > Cookies\n"
            "4. Find and copy the POESESSID value\n\n"
            "WARNING: Keep your POESESSID private!"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(info_label)

        # Form
        form = QFormLayout()

        self._account_input = QLineEdit()
        self._account_input.setText(self.ctx.config.account_name)
        self._account_input.setPlaceholderText("Your PoE account name")
        form.addRow("Account Name:", self._account_input)

        self._session_input = QLineEdit()
        self._session_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._session_input.setText(self.ctx.config.poesessid)
        self._session_input.setPlaceholderText("POESESSID cookie value")
        form.addRow("POESESSID:", self._session_input)

        layout.addLayout(form)

        # Test button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(lambda: self._test_connection(dialog))
        layout.addWidget(test_btn)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self._save_settings(dialog))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _test_connection(self, dialog: QDialog) -> None:
        """Test the POESESSID connection."""
        poesessid = self._session_input.text().strip()
        if not poesessid:
            QMessageBox.warning(dialog, "Error", "Please enter a POESESSID")
            return

        try:
            client = PoEStashClient(poesessid)
            if client.verify_session():
                chars = client.get_characters()
                char_names = [c.get("name", "?") for c in chars[:3]]
                QMessageBox.information(
                    dialog,
                    "Success",
                    f"Connection successful!\n\nCharacters: {', '.join(char_names)}..."
                )
            else:
                QMessageBox.warning(
                    dialog,
                    "Failed",
                    "Connection failed - POESESSID may be invalid or expired"
                )
        except Exception as e:
            QMessageBox.critical(dialog, "Error", f"Connection test failed:\n{e}")

    def _save_settings(self, dialog: QDialog) -> None:
        """Save settings and close dialog."""
        account = self._account_input.text().strip()
        poesessid = self._session_input.text().strip()

        if account:
            self.ctx.config.account_name = account
            self.account_label.setText(account)

        if poesessid:
            self.ctx.config.poesessid = poesessid

        dialog.accept()

    def _refresh_stash(self) -> None:
        """Fetch and valuate stash."""
        if not self.ctx.config.has_stash_credentials():
            QMessageBox.warning(
                self,
                "Configuration Required",
                "Please configure your account name and POESESSID in Settings."
            )
            self._show_settings()
            return

        if self._worker and self._worker.isRunning():
            return  # Already running

        league = self.league_combo.currentText()
        poesessid = self.ctx.config.poesessid
        account_name = self.ctx.config.account_name

        # Update UI
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.setText("Starting...")

        # Create worker
        self._worker = FetchWorker(poesessid, account_name, league)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_fetch_complete)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.rate_limited.connect(self._on_rate_limited)
        self._worker.start()

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Handle progress updates."""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setMaximum(0)  # Indeterminate
        self.status_label.setText(message)

    def _on_rate_limited(self, wait_seconds: int, attempt: int) -> None:
        """Handle rate limit notification - update UI to show wait status."""
        self.progress_bar.setMaximum(0)  # Indeterminate mode during wait
        self.status_label.setText(
            f"Rate limited by GGG. Waiting {wait_seconds}s before retry "
            f"(attempt {attempt}/3)..."
        )

    def _on_fetch_complete(
        self,
        result: ValuationResult,
        snapshot: StashSnapshot,
    ) -> None:
        """Handle fetch completion - save to storage and display."""
        self._result = result
        self.refresh_btn.setEnabled(True)
        self.grid_view_btn.setEnabled(True)  # Enable grid view
        self.progress_bar.hide()

        # Compute diff if we have a previous snapshot
        diff: Optional[StashDiff] = None
        if self._diff_engine.has_before_snapshot:
            diff = self._diff_engine.compute_diff(snapshot)
            if diff.has_changes:
                self.status_label.setText(f"Changes: {diff.get_summary()}")
                logger.info(f"Stash diff: {diff.get_summary()}")
            else:
                self.status_label.setText("No changes since last fetch")
        else:
            self.status_label.setText("")

        # Update current snapshot and diff engine
        self._current_snapshot = snapshot
        self._diff_engine.set_before_snapshot(snapshot)

        # Save to storage
        try:
            self._storage.save_snapshot(snapshot, result)
            # Clean up old snapshots (keep last 5)
            self._storage.delete_old_snapshots(
                snapshot.account_name,
                snapshot.league,
                keep_count=5,
            )
        except Exception as e:
            logger.error(f"Failed to save stash snapshot: {e}")

        # Update last fetch time
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.ctx.config.stash_last_fetch = now
        self.last_fetch_label.setText(f"Last fetched: {now}")

        # Display the result
        self._display_valuation_result(result)

    def _display_valuation_result(self, result: ValuationResult) -> None:
        """Display a valuation result in the UI."""
        # Enable grid view if we have data
        self.grid_view_btn.setEnabled(True)

        # Update totals
        self.total_label.setText(f"Total: {result.display_total}")
        self.priced_label.setText(
            f"{result.priced_items}/{result.total_items} priced"
        )

        # Populate tab list
        self.tab_list.clear()
        for tab in result.tabs:
            item_text = f"{tab.name}  ({tab.display_value})"
            list_item = QListWidgetItem(item_text)

            # Color by value
            if tab.total_value >= 1000:
                list_item.setForeground(QColor(COLORS["high_value"]))
            elif tab.total_value >= 100:
                list_item.setForeground(QColor(COLORS["medium_value"]))

            self.tab_list.addItem(list_item)

        # Select first tab
        if result.tabs:
            self.tab_list.setCurrentRow(0)

    def _on_fetch_error(self, error: str) -> None:
        """Handle fetch error."""
        self.refresh_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"Error: {error}")

        QMessageBox.critical(self, "Fetch Error", f"Failed to fetch stash:\n\n{error}")

    def _on_tab_selected(self, row: int) -> None:
        """Handle tab selection."""
        if not self._result or row < 0 or row >= len(self._result.tabs):
            self._item_model.set_items([])
            return

        tab = self._result.tabs[row]
        self._item_model.set_items(tab.items)
        self._update_item_count()

    def _on_min_value_changed(self, value: int) -> None:
        """Handle min value filter change."""
        self._item_model.set_min_value(float(value))
        self._update_item_count()

    def _on_search_changed(self, text: str) -> None:
        """Handle search filter change."""
        self._item_model.set_search_text(text)
        self._update_item_count()

    def _update_item_count(self) -> None:
        """Update item count label."""
        count = self._item_model.rowCount()
        self.item_count_label.setText(f"{count} items")

    def _on_item_double_click(self, index: QModelIndex) -> None:
        """Handle item double-click - show item details dialog."""
        item = self._item_model.get_item(index.row())
        if item:
            dialog = StashItemDetailsDialog(item, self)
            dialog.exec()

    def _show_item_context_menu(self, position) -> None:
        """Show context menu for stash items."""
        index = self.item_table.indexAt(position)
        if not index.isValid():
            return

        item = self._item_model.get_item(index.row())
        if not item:
            return

        # Build item context from PricedItem
        item_context = ItemContext(
            item_name=item.display_name,
            item_text="",  # Stash items don't have raw text
            chaos_value=float(item.total_price),
            divine_value=0,  # Convert if needed
            source="poe.ninja" if item.price_source == PriceSource.POE_NINJA else "poeprices",
            extra_data={"priced_item": item},
        )

        # Build and show menu with custom actions
        menu = self._context_menu_manager.build_menu(item_context, self.item_table)

        # Add stash-specific actions
        menu.addSeparator()
        details_action = menu.addAction("View Details...")
        details_action.triggered.connect(
            lambda: self._show_item_details(item)
        )

        menu.exec(self.item_table.viewport().mapToGlobal(position))

    def _show_item_details(self, item: PricedItem) -> None:
        """Show details dialog for a stash item."""
        dialog = StashItemDetailsDialog(item, self)
        dialog.exec()

    def _on_inspect_item_context(self, context: ItemContext) -> None:
        """Handle inspect request from context menu."""
        priced_item = context.extra_data.get("priced_item")
        if priced_item:
            self._show_item_details(priced_item)

    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        super().closeEvent(event)
