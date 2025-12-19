"""
Daytrader Screen - Economy analysis, sales tracking, and trading.

This screen consolidates economy-related features:
- Sales tracking and dashboard
- Loot tracking
- Market analysis (price rankings, history)
- Stash viewer
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QFrame,
    QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui_qt.screens.base_screen import BaseScreen

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class QuickStatsPanel(QFrame):
    """
    Quick stats panel showing economy summary.

    Displays key metrics like total revenue, items sold today, etc.
    """

    def __init__(self, ctx: Optional["AppContext"] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Quick Stats")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        # Stats will be populated from database
        self._revenue_label = QLabel("Revenue: -")
        layout.addWidget(self._revenue_label)

        self._sold_today_label = QLabel("Sold Today: -")
        layout.addWidget(self._sold_today_label)

        self._sold_week_label = QLabel("Sold This Week: -")
        layout.addWidget(self._sold_week_label)

        self._avg_price_label = QLabel("Avg Price: -")
        layout.addWidget(self._avg_price_label)

        layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh Stats")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

    def refresh(self) -> None:
        """Refresh stats from database."""
        if not self.ctx or not hasattr(self.ctx, 'db'):
            return

        try:
            db = self.ctx.db

            # Get sales stats (methods may not exist on interface)
            total_sales = getattr(db, 'get_total_sales', lambda: 0)() or 0
            today_sales = getattr(db, 'get_sales_today', lambda: 0)() or 0
            week_sales = getattr(db, 'get_sales_this_week', lambda: 0)() or 0

            self._revenue_label.setText(f"Total Revenue: {total_sales:,.0f}c")
            self._sold_today_label.setText(f"Sold Today: {today_sales}")
            self._sold_week_label.setText(f"This Week: {week_sales}")

        except Exception as e:
            logger.debug(f"Failed to refresh stats: {e}")


class QuickActionsPanel(QFrame):
    """
    Quick actions panel for economy operations.
    """

    record_sale_clicked = pyqtSignal()
    snapshot_clicked = pyqtSignal()
    refresh_stash_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Quick Actions")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        # Record Sale
        record_btn = QPushButton("Record Sale")
        record_btn.setToolTip("Manually record a sale")
        record_btn.clicked.connect(self.record_sale_clicked.emit)
        layout.addWidget(record_btn)

        # Economy Snapshot
        snapshot_btn = QPushButton("Economy Snapshot")
        snapshot_btn.setToolTip("Collect current economy data")
        snapshot_btn.clicked.connect(self.snapshot_clicked.emit)
        layout.addWidget(snapshot_btn)

        # Refresh Stash
        stash_btn = QPushButton("Refresh Stash")
        stash_btn.setToolTip("Fetch latest stash data")
        stash_btn.clicked.connect(self.refresh_stash_clicked.emit)
        layout.addWidget(stash_btn)

        layout.addStretch()


class DaytraderScreen(BaseScreen):
    """
    Daytrader screen for economy and trading.

    Layout:
    +------------------------------------------+
    | +-------------+ +------------------------+ |
    | | Quick Stats | | [Sales][Loot][Market][Stash] |
    | | - Revenue   | +------------------------+ |
    | | - Today     | | Active Tab Content     | |
    | | - Week      | |                        | |
    | +-------------+ |                        | |
    | +-------------+ |                        | |
    | | Quick Actions| |                        | |
    | | - Record Sale| |                        | |
    | | - Snapshot   | |                        | |
    | +-------------+ +------------------------+ |
    +------------------------------------------+
    """

    # Signals for parent window
    record_sale_requested = pyqtSignal()
    economy_snapshot_requested = pyqtSignal()
    refresh_stash_requested = pyqtSignal()

    def __init__(
        self,
        ctx: "AppContext",
        on_status: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the Daytrader screen."""
        super().__init__(ctx, on_status, parent)
        self._stats_panel: Optional[QuickStatsPanel] = None
        self._actions_panel: Optional[QuickActionsPanel] = None
        self._tab_widget: Optional[QTabWidget] = None

        self._create_ui()

    def _create_ui(self) -> None:
        """Create the Daytrader UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ========== LEFT SIDE: Stats + Actions ==========
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Quick Stats Panel
        self._stats_panel = QuickStatsPanel(ctx=self.ctx, parent=self)
        left_layout.addWidget(self._stats_panel, stretch=1)

        # Quick Actions Panel
        self._actions_panel = QuickActionsPanel(parent=self)
        self._actions_panel.record_sale_clicked.connect(self.record_sale_requested.emit)
        self._actions_panel.snapshot_clicked.connect(self.economy_snapshot_requested.emit)
        self._actions_panel.refresh_stash_clicked.connect(self.refresh_stash_requested.emit)
        left_layout.addWidget(self._actions_panel, stretch=1)

        left_widget.setMinimumWidth(180)
        left_widget.setMaximumWidth(250)
        main_splitter.addWidget(left_widget)

        # ========== RIGHT SIDE: Tab Widget ==========
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Sales Tab
        sales_tab = self._create_sales_tab()
        self._tab_widget.addTab(sales_tab, "Sales")

        # Loot Tab
        loot_tab = self._create_loot_tab()
        self._tab_widget.addTab(loot_tab, "Loot")

        # Market Tab
        market_tab = self._create_market_tab()
        self._tab_widget.addTab(market_tab, "Market")

        # Stash Tab
        stash_tab = self._create_stash_tab()
        self._tab_widget.addTab(stash_tab, "Stash")

        main_splitter.addWidget(self._tab_widget)

        # Set splitter sizes
        main_splitter.setSizes([200, 1000])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

        layout.addWidget(main_splitter)

    def _create_sales_tab(self) -> QWidget:
        """Create the Sales tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Embed RecentSalesWindow content
        try:
            from gui_qt.windows.recent_sales_window import RecentSalesWindow
            # Create as widget (not dialog)
            sales_widget = RecentSalesWindow(self.ctx, parent=widget)
            sales_widget.setWindowFlags(Qt.WindowType.Widget)
            layout.addWidget(sales_widget)
        except Exception as e:
            logger.warning(f"Failed to create sales widget: {e}")
            placeholder = QLabel("Sales tracking\n\nRecord and view your sales history.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: palette(mid);")
            layout.addWidget(placeholder)

        return widget

    def _create_loot_tab(self) -> QWidget:
        """Create the Loot tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Placeholder - LootDashboardWindow needs controller
        placeholder = QLabel(
            "Loot Tracking\n\n"
            "Track items from your gaming sessions.\n"
            "Start loot tracking from the Economy menu."
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: palette(mid);")
        layout.addWidget(placeholder)

        return widget

    def _create_market_tab(self) -> QWidget:
        """Create the Market tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Embed PriceRankingsPanel (compact version)
        try:
            from gui_qt.widgets.price_rankings_panel import PriceRankingsPanel
            rankings_panel = PriceRankingsPanel(ctx=self.ctx, parent=widget)
            layout.addWidget(rankings_panel)
        except Exception as e:
            logger.warning(f"Failed to create rankings panel: {e}")
            placeholder = QLabel("Market Analysis\n\nView price rankings and trends.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: palette(mid);")
            layout.addWidget(placeholder)

        return widget

    def _create_stash_tab(self) -> QWidget:
        """Create the Stash tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Embed StashViewerWindow content
        try:
            from gui_qt.windows.stash_viewer_window import StashViewerWindow
            stash_widget = StashViewerWindow(self.ctx, parent=widget)
            stash_widget.setWindowFlags(Qt.WindowType.Widget)
            layout.addWidget(stash_widget)
        except Exception as e:
            logger.warning(f"Failed to create stash widget: {e}")
            placeholder = QLabel(
                "Stash Viewer\n\n"
                "View and manage your stash tabs.\n"
                "Configure stash API access in Settings."
            )
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: palette(mid);")
            layout.addWidget(placeholder)

        return widget

    @property
    def screen_name(self) -> str:
        """Return the screen display name."""
        return "Daytrader"

    def on_enter(self) -> None:
        """Called when entering this screen."""
        self.set_status("Daytrader - Economy analysis and trading")
        # Refresh stats
        if self._stats_panel:
            self._stats_panel.refresh()

    def on_leave(self) -> None:
        """Called when leaving this screen."""
        pass

    def refresh(self) -> None:
        """Refresh screen data."""
        if self._stats_panel:
            self._stats_panel.refresh()
