"""
gui_qt.main_window

PyQt6 GUI for the PoE Price Checker.

- Paste or type item text into the input box.
- Click "Check Price" (or press Ctrl+Enter) to run a price check.
- View results in the table.
- Right-click a result row to open in browser, copy it, or view details.
- File menu: open log file, open config folder, export TSV, exit.
- View menu: session history, data sources, column visibility, recent sales, sales dashboard.
- Dev menu: paste sample items of various types (map, currency, unique, etc.).
- Help menu: shortcuts, usage tips, about.
"""

from __future__ import annotations

import logging
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING, cast

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMenuBar,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QStackedWidget,
    QGroupBox,
    QLabel,
    QPushButton,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QDialog,
)

from gui_qt.styles import Theme
from gui_qt.menus.menu_builder import (
    MenuBuilder, MenuConfig, MenuItem, MenuSection, create_resources_menu
)
from gui_qt.shortcuts import get_shortcut_manager
from gui_qt.sample_items import SAMPLE_ITEMS
from gui_qt.dialogs.help_dialogs import (
    show_shortcuts_dialog, show_tips_dialog, show_about_dialog
)
from gui_qt.widgets.toast_notification import ToastManager
from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget
from gui_qt.widgets.price_rankings_panel import PriceRankingsPanel
from gui_qt.widgets.session_tabs import SessionTabWidget, SessionPanel
from gui_qt.workers import RankingsPopulationWorker
from gui_qt.services import get_window_manager, get_history_manager
from gui_qt.controllers import (
    PriceCheckController,
    ThemeController,
    NavigationController,
    ResultsContextController,
    TrayController,
    PoBController,
    ViewMenuController,
)
from gui_qt.controllers.ai_analysis_controller import AIAnalysisController
from gui_qt.controllers.loot_tracking_controller import LootTrackingController
from gui_qt.widgets.main_navigation_bar import MainNavigationBar
from gui_qt.screens import ScreenController, ScreenType, AIAdvisorScreen, DaytraderScreen
from core.build_stat_calculator import BuildStats

if TYPE_CHECKING:
    from core.app_context import AppContext
    from core.rare_item_evaluator import RareItemEvaluator
    from gui_qt.views.upgrade_advisor_view import UpgradeAdvisorView
    from gui_qt.screens import AIAdvisorScreen as AIAdvisorScreenType


class PriceCheckerWindow(QMainWindow):
    """Main window for the PoE Price Checker application."""

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ctx = ctx
        self.logger = logging.getLogger(__name__)

        # State
        self._check_in_progress = False
        self._upgrade_advisor_view: Optional["UpgradeAdvisorView"] = None  # Lazy-loaded

        # Screen navigation
        self._nav_bar: Optional[MainNavigationBar] = None
        self._screen_controller: Optional[ScreenController] = None
        self._ai_advisor_screen: Optional["AIAdvisorScreenType"] = None  # AI Advisor screen

        # History manager for session history
        self._history_manager = get_history_manager()

        # Window manager for child window lifecycle
        self._window_manager = get_window_manager()
        self._window_manager.set_main_window(self)

        # Rare item evaluator
        self._rare_evaluator: Optional["RareItemEvaluator"] = None
        self._init_rare_evaluator()

        # PoB integration controller
        self._pob_controller = PoBController(
            ctx=ctx,
            logger=self.logger,
            on_status=self._set_status,
        )
        self._pob_controller.initialize()

        # Price check controller
        self._price_controller = PriceCheckController(
            parser=ctx.parser,
            price_service=ctx.price_service,
            rare_evaluator=self._rare_evaluator,
            upgrade_checker=self._pob_controller.upgrade_checker,
        )

        # Theme controller (initialized after menu bar creation)
        self._theme_controller: Optional[ThemeController] = None

        # Rankings population worker
        self._rankings_worker: Optional[RankingsPopulationWorker] = None

        # Tray controller for system tray functionality
        self._tray_controller: Optional[TrayController] = None

        # Navigation controller for window/dialog management
        # Note: AI callbacks added after UI is created via _register_ai_callbacks
        self._nav_controller = NavigationController(
            window_manager=self._window_manager,
            ctx=ctx,
            main_window=self,
            character_manager=self._pob_controller.character_manager,
            callbacks={
                "on_pob_profile_selected": self._on_pob_profile_selected,
                "on_pob_price_check": self._on_pob_price_check,
                "on_loadout_selected": self._on_loadout_selected,
                "on_ranking_price_check": self._on_ranking_price_check,
                "on_reload_rare_evaluator": self._reload_rare_evaluator,
            },
        )

        # Results context menu controller (initialized after toast manager is created)
        self._results_context_controller: Optional[ResultsContextController] = None

        # AI analysis controller (initialized after UI is created)
        self._ai_controller: Optional[AIAnalysisController] = None

        # View menu controller
        self._view_menu_controller: Optional[ViewMenuController] = None

        # Loot tracking controller
        self._loot_controller: Optional[LootTrackingController] = None

        # Setup UI
        self.setWindowTitle("PoE Price Checker")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 900)

        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        self._setup_shortcuts()

        # Initialize theme controller and apply theme
        self._init_theme_controller()

        # Initialize system tray
        self._init_system_tray()

        self._set_status("Ready")

        # Start background rankings population check
        self._start_rankings_population()

        # Initialize build stats for item inspector from active PoB profile
        self._pob_controller.update_inspector_stats(self.item_inspector)

    def _start_rankings_population(self) -> None:
        """Start background task to populate price rankings if needed."""
        try:
            self._rankings_worker = RankingsPopulationWorker(self)
            self._rankings_worker.status.connect(self._on_rankings_progress)
            self._rankings_worker.result.connect(self._on_rankings_finished)
            self._rankings_worker.error.connect(self._on_rankings_error)
            self._rankings_worker.start()
        except Exception as e:
            self.logger.warning(f"Failed to start rankings population: {e}")

    def _on_rankings_progress(self, message: str) -> None:
        """Handle rankings population progress."""
        self.logger.info(f"Rankings: {message}")

    def _on_rankings_finished(self, count: int) -> None:
        """Handle rankings population completion."""
        if count > 0:
            self.logger.info(f"Rankings: Populated {count} categories")
        self._rankings_worker = None

    def _on_rankings_error(self, error: str, traceback: str) -> None:
        """Handle rankings population error."""
        self.logger.warning(f"Rankings population failed: {error}")
        self.logger.debug(f"Traceback:\n{traceback}")
        self._rankings_worker = None

    def _init_rare_evaluator(self) -> None:
        """Initialize the rare item evaluator."""
        try:
            from core.rare_item_evaluator import RareItemEvaluator
            data_dir = Path(__file__).parent.parent / "data"
            self._rare_evaluator = RareItemEvaluator(data_dir=data_dir)
        except Exception as e:
            self.logger.warning(f"Failed to initialize rare evaluator: {e}")


    # -------------------------------------------------------------------------
    # Session Tab Widget Delegation
    # -------------------------------------------------------------------------
    # These widget attributes are delegated to the current session panel.
    # Uses __getattr__ to avoid repetitive property definitions.
    #
    # Delegated attributes:
    #   input_text: QPlainTextEdit - Item text input area
    #   item_inspector: ItemInspectorWidget - Parsed item display
    #   results_table: ResultsTableWidget - Price results grid
    #   filter_input: QLineEdit - Results filter text field
    #   source_filter: QComboBox - Data source dropdown
    #   rare_eval_panel: RareEvaluationPanelWidget - Rare item analysis
    #   check_btn: QPushButton - Price check trigger button
    # -------------------------------------------------------------------------

    _DELEGATED_ATTRS: frozenset = frozenset({
        'input_text', 'item_inspector', 'results_table',
        'filter_input', 'source_filter', 'rare_eval_panel', 'ai_panel', 'check_btn'
    })

    @property
    def _current_build_stats(self) -> Optional[BuildStats]:
        """Get current build stats from the active PoB profile."""
        stats = self._pob_controller.get_build_stats()
        if stats:
            build_stats: BuildStats = stats[0]  # (BuildStats, DPSStats) tuple
            return build_stats
        return None

    def __getattr__(self, name: str) -> Any:
        """Delegate widget access to the current session panel."""
        if name in PriceCheckerWindow._DELEGATED_ATTRS:
            # Avoid infinite recursion by checking __dict__ directly
            if 'session_tabs' in self.__dict__:
                panel = self.session_tabs.get_current_panel()
                if panel:
                    return getattr(panel, name)
            return None  # Match original behavior - return None when no panel
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def _on_session_changed(self, index: int) -> None:
        """Handle session tab change - connect context menu."""
        panel = self.session_tabs.get_panel(index)
        if panel:
            # Connect context menu for the new session's results table
            panel.results_table.customContextMenuRequested.connect(
                self._show_results_context_menu
            )
            # Update build stats for the new session's inspector
            self._pob_controller.update_inspector_stats(panel.item_inspector)
            # Update AI controller with the new session's panel
            self._update_ai_controller_panel()

    def _on_session_check_price(self, item_text: str, session_index: int) -> None:
        """Handle check price request from a session tab."""
        if self._check_in_progress:
            return
        self._do_price_check(item_text, session_index)

    def _on_verdict_stats_changed(self, stats) -> None:
        """Handle verdict statistics change - save to database."""
        try:
            from datetime import datetime
            from core.quick_verdict import VerdictStatistics

            # Get current league and game version from config
            league = self.ctx.config.league or "Standard"
            game_version = self.ctx.config.current_game.value
            session_date = datetime.now().strftime("%Y-%m-%d")

            # Convert VerdictStatistics to dict if needed
            if isinstance(stats, VerdictStatistics):
                stats_dict = stats.to_dict()
            else:
                stats_dict = stats

            # Save to database
            self.ctx.db.save_verdict_statistics(
                league=league,
                game_version=game_version,
                session_date=session_date,
                stats=stats_dict,
            )
            self.logger.debug(f"Saved verdict stats: {stats_dict}")
        except Exception as e:
            self.logger.warning(f"Failed to save verdict statistics: {e}")

    # -------------------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        """Create the application menu bar using declarative MenuBuilder."""
        menubar = self.menuBar()
        if not menubar:
            return
        builder = MenuBuilder(self)

        # Define static menus declaratively
        static_menus = [
            MenuConfig("&File", [
                MenuItem("Open &Log File", handler=self._open_log_file),
                MenuItem("Open &Config Folder", handler=self._open_config_folder),
                MenuSection([
                    MenuItem("&Export Results (TSV)...", handler=self._export_results,
                             shortcut="Ctrl+E"),
                    MenuItem("Copy &All as TSV", handler=self._copy_all_as_tsv,
                             shortcut="Ctrl+Shift+C"),
                ]),
                MenuSection([
                    MenuItem("&Settings...", handler=self._show_settings,
                             shortcut="Ctrl+,"),
                ]),
                MenuSection([
                    MenuItem("E&xit", handler=self.close, shortcut="Alt+F4"),
                ]),
            ]),
            MenuConfig("&Navigate", [
                MenuItem("&Item Evaluator", handler=self._switch_to_evaluator,
                         shortcut="Ctrl+1"),
                MenuItem("&AI Advisor", handler=self._switch_to_advisor,
                         shortcut="Ctrl+2"),
                MenuItem("&Daytrader", handler=self._switch_to_daytrader,
                         shortcut="Ctrl+3"),
            ]),
            MenuConfig("&Build", [
                MenuSection([
                    MenuItem("Go to &AI Advisor Screen", handler=self._switch_to_advisor),
                ]),
                MenuItem("&PoB Characters", handler=self._show_pob_characters,
                         shortcut="Ctrl+B"),
                MenuItem("&Compare Build Trees...", handler=self._show_build_comparison),
                MenuItem("Build &Library...", handler=self._show_build_library,
                         shortcut="Ctrl+Alt+B"),
                MenuSection([
                    MenuItem("Find &BiS Item...", handler=self._show_bis_search,
                             shortcut="Ctrl+I"),
                    MenuItem("&Upgrade Finder...", handler=self._show_upgrade_finder,
                             shortcut="Ctrl+U"),
                    MenuItem("Compare &Items...", handler=self._show_item_comparison,
                             shortcut="Ctrl+Shift+I"),
                ]),
                MenuSection([
                    MenuItem("Rare Item &Settings...", handler=self._show_rare_eval_config),
                ]),
            ]),
            MenuConfig("&Economy", [
                MenuSection([
                    MenuItem("Go to &Daytrader Screen", handler=self._switch_to_daytrader),
                ]),
                MenuSection([
                    MenuItem("&Top 20 Rankings", handler=self._show_price_rankings),
                    MenuItem("Data &Sources Info", handler=self._show_data_sources),
                ], label="Pricing"),
                MenuSection([
                    MenuItem("&Recent Sales", handler=self._show_recent_sales),
                    MenuItem("Sales &Dashboard", handler=self._show_sales_dashboard),
                    MenuItem("&Loot Tracking...", handler=self._show_loot_dashboard),
                ], label="Sales & Loot"),
                MenuSection([
                    MenuItem("Price &History...", handler=self._show_price_history),
                    MenuItem("Collect Economy &Snapshot", handler=self._collect_economy_snapshot),
                ], label="Historical Data"),
            ]),
        ]
        builder.build(menubar, static_menus)

        # View menu - dynamic content (themes, accents, columns)
        self._create_view_menu(menubar)

        # Resources menu - use declarative config
        resources_menu = menubar.addMenu("&Resources")
        if resources_menu:
            builder._populate_menu(resources_menu, create_resources_menu())

        # Dev menu - dynamic content (sample items)
        self._create_dev_menu(menubar)

        # Help menu - static
        help_config = [
            MenuConfig("&Help", [
                MenuItem("&Keyboard Shortcuts", handler=self._show_shortcuts),
                MenuItem("Usage &Tips", handler=self._show_tips),
                MenuSection([
                    MenuItem("&About", handler=self._show_about),
                ]),
            ])
        ]
        builder.build(menubar, help_config)

    def _create_view_menu(self, menubar: QMenuBar) -> None:
        """Create View menu with dynamic theme/accent/column submenus."""
        self._view_menu_controller = ViewMenuController(
            on_history=self._show_history,
            on_stash_viewer=self._show_stash_viewer,
            on_set_theme=self._set_theme,
            on_toggle_theme=self._toggle_theme,
            on_set_accent=self._set_accent_color,
            on_toggle_column=self._toggle_column,
            parent=self,
            logger=self.logger,
        )
        self._theme_actions, self._accent_actions, self._column_actions = \
            self._view_menu_controller.create_view_menu(menubar)

    def _create_dev_menu(self, menubar: QMenuBar) -> None:
        """Create Dev menu with dynamic sample items."""
        dev_menu = menubar.addMenu("&Dev")
        if not dev_menu:
            return

        paste_menu = dev_menu.addMenu("Paste &Sample")
        if paste_menu:
            for item_type in SAMPLE_ITEMS.keys():
                action = QAction(item_type.title(), self)
                action.triggered.connect(lambda checked, t=item_type: self._paste_sample(t))
                paste_menu.addAction(action)

        dev_menu.addSeparator()

        clear_db_action = QAction("&Wipe Database...", self)
        clear_db_action.triggered.connect(self._wipe_database)
        dev_menu.addAction(clear_db_action)

    # -------------------------------------------------------------------------
    # Central Widget
    # -------------------------------------------------------------------------

    def _create_central_widget(self) -> None:
        """Create the main content area with navigation bar and screens."""
        # Container for navigation bar + stacked screens
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Top navigation bar (large pill buttons)
        self._nav_bar = MainNavigationBar()
        self._nav_bar.screen_selected.connect(self._on_screen_selected)
        container_layout.addWidget(self._nav_bar)

        # QStackedWidget for screens
        self._stacked_widget = QStackedWidget()
        container_layout.addWidget(self._stacked_widget)

        self.setCentralWidget(container)

        # Index 0: Item Evaluator (current main view)
        main_view = QWidget()
        self._stacked_widget.addWidget(main_view)

        # Initialize screen controller (placeholder screens added after main view setup)
        self._screen_controller = ScreenController(self._stacked_widget, parent=self)
        self._screen_controller.set_status_callback(self._set_status)

        # Main horizontal splitter: PoB panel (left) | Price check (right)
        main_layout = QHBoxLayout(main_view)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ========== LEFT SIDE: Price Rankings + Pinned Items ==========
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setMinimumWidth(250)
        left_splitter.setMaximumWidth(400)

        # Price Rankings panel (collapsible)
        rankings_group = QGroupBox("Price Rankings")
        rankings_layout = QVBoxLayout(rankings_group)
        rankings_layout.setContentsMargins(4, 4, 4, 4)

        self._rankings_panel = PriceRankingsPanel(ctx=self.ctx, parent=self)
        self._rankings_panel.price_check_requested.connect(self._on_ranking_price_check)
        rankings_layout.addWidget(self._rankings_panel)
        left_splitter.addWidget(rankings_group)

        # Pinned Items panel
        pinned_group = QGroupBox("Pinned Items")
        pinned_layout = QVBoxLayout(pinned_group)
        pinned_layout.setContentsMargins(4, 4, 4, 4)

        self.pinned_items_widget = PinnedItemsWidget()
        self.pinned_items_widget.item_inspected.connect(self._on_pinned_item_inspected)
        self.pinned_items_widget.ai_analysis_requested.connect(self._on_ai_analysis_requested)
        self.pinned_items_widget.price_check_requested.connect(self._on_pob_price_check)
        pinned_layout.addWidget(self.pinned_items_widget)
        left_splitter.addWidget(pinned_group)

        # Set initial splitter sizes (Rankings: 60%, Pinned: 40%)
        left_splitter.setSizes([400, 250])

        # Create PoB panel (hidden - will be moved to AI Advisor in Phase 3)
        # For now, keep it initialized but not visible for backward compatibility
        from gui_qt.widgets.pob_panel import PoBPanel
        self.pob_panel = PoBPanel(self._pob_controller.character_manager, parent=self)
        self.pob_panel.price_check_requested.connect(self._on_pob_price_check)
        self.pob_panel.ai_analysis_requested.connect(self._on_ai_analysis_requested)
        self.pob_panel.upgrade_analysis_requested.connect(self._on_upgrade_analysis_requested)
        self.pob_panel.profile_combo.currentTextChanged.connect(self._on_pob_profile_changed)
        self.pob_panel.hide()  # Hidden - will be added to AI Advisor screen

        main_splitter.addWidget(left_splitter)

        # ========== RIGHT SIDE: Session Tabs (multiple price-checking sessions) ==========
        self.session_tabs = SessionTabWidget()
        self.session_tabs.check_price_requested.connect(self._on_session_check_price)
        self.session_tabs.row_selected.connect(self._on_result_selected)
        self.session_tabs.pin_requested.connect(self._on_pin_items_requested)
        self.session_tabs.compare_requested.connect(self._on_compare_items_requested)
        self.session_tabs.ai_analysis_requested.connect(self._on_ai_analysis_requested)
        self.session_tabs.update_meta_requested.connect(self._on_update_meta_requested)
        self.session_tabs.verdict_stats_changed.connect(self._on_verdict_stats_changed)

        # Pass the rare evaluator to session tabs for meta info display
        if self._rare_evaluator:
            self.session_tabs.set_rare_evaluator(self._rare_evaluator)

        # Set verdict thresholds from config
        self._apply_verdict_thresholds()

        # Load saved verdict statistics for today
        self._load_verdict_statistics()

        # Set AI configured callback for all results tables
        self.session_tabs.set_ai_configured_callback(self._is_ai_configured)

        # Connect context menu for results table in each session
        self.session_tabs.currentChanged.connect(self._on_session_changed)

        # Add right panel to main splitter
        main_splitter.addWidget(self.session_tabs)

        # Set initial splitter sizes (PoB panel: 300, Price check: rest)
        main_splitter.setSizes([300, 1100])

        # Add main splitter to central layout
        main_layout.addWidget(main_splitter)

        # Create and register screens for other tabs
        # Note: Item Evaluator (index 0) is the main_view we just created

        # AI Advisor screen with PoB panel and upgrade advisor
        ai_advisor_screen = AIAdvisorScreen(
            ctx=self.ctx,
            character_manager=self._pob_controller.character_manager,
            on_status=self._set_status,
        )
        # Connect AI Advisor signals
        ai_advisor_screen.upgrade_analysis_requested.connect(
            self._on_ai_advisor_upgrade_requested
        )
        ai_advisor_screen.compare_builds_requested.connect(self._show_build_comparison)
        ai_advisor_screen.bis_search_requested.connect(self._show_bis_search)
        ai_advisor_screen.library_requested.connect(self._show_build_library)
        ai_advisor_screen.upgrade_finder_requested.connect(self._show_upgrade_finder)
        ai_advisor_screen.item_compare_requested.connect(self._show_item_comparison)
        ai_advisor_screen.price_check_requested.connect(self._on_pob_price_check)
        self._ai_advisor_screen = ai_advisor_screen

        # Daytrader screen with economy/trading features
        daytrader_screen = DaytraderScreen(ctx=self.ctx, on_status=self._set_status)
        daytrader_screen.record_sale_requested.connect(self._show_recent_sales)
        daytrader_screen.economy_snapshot_requested.connect(self._collect_economy_snapshot)
        daytrader_screen.refresh_stash_requested.connect(self._show_stash_viewer)

        self._screen_controller.register_screen(ScreenType.AI_ADVISOR, ai_advisor_screen)
        self._screen_controller.register_screen(ScreenType.DAYTRADER, daytrader_screen)

    def _on_screen_selected(self, screen_type_value: int) -> None:
        """Handle screen selection from navigation bar.

        Args:
            screen_type_value: The ScreenType value (0, 1, or 2).
        """
        screen_type = ScreenType(screen_type_value)

        # Special handling for Item Evaluator - it's the main view at index 0
        if screen_type == ScreenType.ITEM_EVALUATOR:
            # Switch to main view (index 0)
            self._stacked_widget.setCurrentIndex(0)
            self._set_status("Item Evaluator - Ready")
            return

        # For other screens, use the screen controller
        if self._screen_controller:
            self._screen_controller.switch_to(screen_type)

    def _switch_to_evaluator(self) -> None:
        """Switch to Item Evaluator screen (Ctrl+1)."""
        self._on_screen_selected(ScreenType.ITEM_EVALUATOR.value)
        if self._nav_bar:
            self._nav_bar.set_active_screen(ScreenType.ITEM_EVALUATOR)

    def _switch_to_advisor(self) -> None:
        """Switch to AI Advisor screen (Ctrl+2)."""
        self._on_screen_selected(ScreenType.AI_ADVISOR.value)
        if self._nav_bar:
            self._nav_bar.set_active_screen(ScreenType.AI_ADVISOR)

    def _switch_to_daytrader(self) -> None:
        """Switch to Daytrader screen (Ctrl+3)."""
        self._on_screen_selected(ScreenType.DAYTRADER.value)
        if self._nav_bar:
            self._nav_bar.set_active_screen(ScreenType.DAYTRADER)

    # -------------------------------------------------------------------------
    # Status Bar
    # -------------------------------------------------------------------------

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Summary label (right side)
        self.summary_label = QLabel()
        self.status_bar.addPermanentWidget(self.summary_label)

        # Toast notification manager
        self._toast_manager = ToastManager(self)

        # Initialize AI analysis controller (needs panel from current session)
        # Note: AI controller will be updated for each session on tab change
        self._init_ai_controller()

        # Initialize results context controller now that toast manager exists
        self._results_context_controller = ResultsContextController(
            ctx=self.ctx,
            parent=self,
            on_status=self._set_status,
            on_toast_success=self._toast_success,
            on_toast_error=self._toast_error,
            on_ai_analysis=self._on_ai_analysis_requested,
            ai_configured=self._is_ai_configured,
        )

    def _set_status(self, message: str) -> None:
        """Set the status bar message."""
        self.status_bar.showMessage(message)

    def _update_summary(self) -> None:
        """Update the summary label with current session's results."""
        panel = self.session_tabs.get_current_panel()
        if not panel:
            self.summary_label.setText("No results")
            return

        count = len(panel._all_results)
        if count == 0:
            self.summary_label.setText("No results")
        else:
            # Ensure chaos_value is numeric
            total_chaos = 0.0
            for r in panel._all_results:
                val = r.get("chaos_value", 0)
                try:
                    total_chaos += float(val) if val else 0.0
                except (ValueError, TypeError):
                    pass  # Skip non-numeric values
            self.summary_label.setText(f"{count} items | {total_chaos:.1f}c total")

    # -------------------------------------------------------------------------
    # AI Analysis
    # -------------------------------------------------------------------------

    def _toast_success(self, msg: str) -> None:
        """Show success toast notification (wrapper for type compatibility)."""
        self._toast_manager.success(msg)

    def _toast_error(self, msg: str) -> None:
        """Show error toast notification (wrapper for type compatibility)."""
        self._toast_manager.error(msg)

    def _init_ai_controller(self) -> None:
        """Initialize the AI analysis controller for the current session panel."""
        panel = self.session_tabs.get_current_panel()
        if panel:
            self._ai_controller = AIAnalysisController(
                config=self.ctx.config,
                panel=panel.ai_panel,
                on_status=self._set_status,
                on_toast_success=self._toast_success,
                on_toast_error=self._toast_error,
            )

        # Register AI callbacks with navigation controller for child windows
        self._nav_controller.set_callback("ai_configured", self._is_ai_configured)
        self._nav_controller.set_callback("on_ai_analysis", self._on_ai_analysis_requested)
        self._nav_controller.set_callback("on_price_check", self._on_pob_price_check)
        self._nav_controller.set_callback("on_upgrade_analysis", self._on_upgrade_analysis_from_window)
        self._nav_controller.set_callback("on_status", self._set_status)

        # Set AI configured callback for PoB panel and pinned items
        self.pob_panel.set_ai_configured_callback(self._is_ai_configured)
        # Pinned items widget uses the context menu manager set during creation
        from gui_qt.widgets.item_context_menu import ItemContextMenuManager
        pinned_menu_manager = ItemContextMenuManager(self.pinned_items_widget)
        pinned_menu_manager.set_ai_configured_callback(self._is_ai_configured)
        pinned_menu_manager.ai_analysis_requested.connect(self._on_ai_analysis_requested)
        pinned_menu_manager.price_check_requested.connect(self._on_pob_price_check)
        pinned_menu_manager.inspect_requested.connect(
            lambda ctx: self._on_pinned_item_inspected({"item_name": ctx.item_name, "_item": ctx.parsed_item})
        )
        self.pinned_items_widget.set_context_menu_manager(pinned_menu_manager)

    def _update_ai_controller_panel(self) -> None:
        """Update AI controller with the current session's panel."""
        panel = self.session_tabs.get_current_panel()
        if panel and self._ai_controller:
            # Create a new controller with the new panel
            self._ai_controller = AIAnalysisController(
                config=self.ctx.config,
                panel=panel.ai_panel,
                on_status=self._set_status,
                on_toast_success=self._toast_success,
                on_toast_error=self._toast_error,
            )

    def _is_ai_configured(self) -> bool:
        """Check if AI is configured."""
        if self._ai_controller:
            return self._ai_controller.is_configured()
        return self.ctx.config.has_ai_configured()

    def _on_ai_analysis_requested(self, item_text: str, price_results: List[Dict[str, Any]]) -> None:
        """Handle AI analysis request from context menu."""
        if not self._ai_controller:
            self._init_ai_controller()

        if self._ai_controller:
            self._ai_controller.analyze_item(item_text, price_results)

    def _on_upgrade_analysis_requested(self, slot: str, item_text: str) -> None:
        """Handle upgrade analysis request from PoB panel context menu.

        Opens the full-screen Upgrade Advisor view and selects the slot.
        """
        self._show_upgrade_advisor_fullscreen(slot=slot)

    def _on_upgrade_analysis_from_window(self, slot: str, item_text: str) -> None:
        """Handle upgrade analysis request from the Upgrade Advisor window.

        Performs AI analysis and sends results back to the window.
        """
        from gui_qt.windows.upgrade_advisor_window import UpgradeAdvisorWindow

        # Get the window to check its selected provider
        window_widget = self._window_manager.get_window("upgrade_advisor")
        if not window_widget or not isinstance(window_widget, UpgradeAdvisorWindow):
            return
        window = window_widget

        # Check if the window's selected provider is configured
        selected_provider = window.get_selected_provider()
        if not selected_provider:
            self._set_status("No AI provider selected")
            window.show_analysis_error(slot, "No AI provider selected")
            return

        # Check if the provider has an API key (unless it's a local provider)
        from data_sources.ai import is_local_provider
        if not is_local_provider(selected_provider):
            api_key = self.ctx.config.get_ai_api_key(selected_provider)
            if not api_key:
                self._set_status(f"No API key configured for {selected_provider}")
                window.show_analysis_error(
                    slot,
                    f"No API key configured for {selected_provider}.\n"
                    f"Add your API key in Settings > AI."
                )
                return

        # Temporarily set the config provider to the selected one
        original_provider = self.ctx.config.ai_provider
        self.ctx.config.ai_provider = selected_provider

        if not self._ai_controller:
            self._init_ai_controller()

        if not self._ai_controller:
            window.show_analysis_error(slot, "Failed to initialize AI controller")
            return

        # Set up the AI controller with database for stash access
        self._ai_controller.set_database(self.ctx.db)
        char_manager = self._pob_controller.character_manager
        if char_manager:
            self._ai_controller.set_character_manager(char_manager)

        # Get account name from config
        account_name = self.ctx.config.data.get("stash", {}).get("account_name", "")

        # Perform analysis - the controller will handle the async work
        try:
            success = self._ai_controller.analyze_upgrade(slot=slot, account_name=account_name)
        finally:
            # Restore original provider (worker has captured the selected one)
            self.ctx.config.ai_provider = original_provider

        if success:
            # Connect to get results back (use a one-time connection)
            def on_result(response):
                from gui_qt.windows.upgrade_advisor_window import UpgradeAdvisorWindow
                w = self._window_manager.get_window("upgrade_advisor")
                if w and isinstance(w, UpgradeAdvisorWindow):
                    w.show_analysis_result(slot, response.content, selected_provider)

            def on_error(error_msg, traceback):
                from gui_qt.windows.upgrade_advisor_window import UpgradeAdvisorWindow
                w = self._window_manager.get_window("upgrade_advisor")
                if w and isinstance(w, UpgradeAdvisorWindow):
                    w.show_analysis_error(slot, error_msg)

            # Reconnect signals for this specific request
            if self._ai_controller._worker:
                self._ai_controller._worker.result.connect(on_result)
                self._ai_controller._worker.error.connect(on_error)
        else:
            window.show_analysis_error(slot, "Failed to start analysis")

    def _show_upgrade_advisor(self, slot: Optional[str] = None) -> None:
        """Show the AI Upgrade Advisor in full-screen mode."""
        self._show_upgrade_advisor_fullscreen(slot)

    def _show_upgrade_advisor_fullscreen(self, slot: Optional[str] = None) -> None:
        """
        Switch to the full-screen upgrade advisor view.

        Args:
            slot: Optional equipment slot to pre-select.
        """
        # Lazy-load the upgrade advisor view
        if self._upgrade_advisor_view is None:
            from gui_qt.views.upgrade_advisor_view import UpgradeAdvisorView

            self._upgrade_advisor_view = UpgradeAdvisorView(
                ctx=self.ctx,
                character_manager=self._pob_controller.character_manager,
                on_close=self._close_upgrade_advisor,
                on_status=self._set_status,
                parent=None,
            )
            # Connect signals
            self._upgrade_advisor_view.close_requested.connect(
                self._close_upgrade_advisor
            )
            self._upgrade_advisor_view.upgrade_analysis_requested.connect(
                self._on_upgrade_analysis_from_advisor
            )

            # Add to stacked widget (index 1)
            self._stacked_widget.addWidget(self._upgrade_advisor_view)

        # Refresh the view data
        self._upgrade_advisor_view.refresh()

        # Pre-select slot if specified
        if slot:
            self._upgrade_advisor_view.select_slot(slot)

        # Switch to advisor view
        self._stacked_widget.setCurrentIndex(1)
        self._set_status("Upgrade Advisor - Select a slot to analyze")

    def _close_upgrade_advisor(self) -> None:
        """Return to the main view from the upgrade advisor."""
        self._stacked_widget.setCurrentIndex(0)
        self._set_status("Ready")

    def _on_ai_advisor_upgrade_requested(self, slot: str, include_stash: bool) -> None:
        """Handle upgrade analysis request from the AI Advisor screen.

        Routes the request through the existing upgrade analysis flow.
        """
        if not self._ai_advisor_screen:
            return

        # Get the screen's upgrade advisor to check provider
        upgrade_advisor = self._ai_advisor_screen.get_upgrade_advisor()
        if not upgrade_advisor:
            return

        selected_provider = upgrade_advisor.get_selected_provider()
        if not selected_provider:
            self._set_status("No AI provider selected")
            self._ai_advisor_screen.show_analysis_error(slot, "No AI provider selected")
            return

        # Check API key for non-local providers
        from data_sources.ai import is_local_provider
        if not is_local_provider(selected_provider):
            api_key = self.ctx.config.get_ai_api_key(selected_provider)
            if not api_key:
                self._set_status(f"No API key configured for {selected_provider}")
                self._ai_advisor_screen.show_analysis_error(
                    slot,
                    f"No API key configured for {selected_provider}.\n"
                    f"Add your API key in Settings > AI."
                )
                return

        # Temporarily set provider and perform analysis
        original_provider = self.ctx.config.ai_provider
        self.ctx.config.ai_provider = selected_provider

        if not self._ai_controller:
            self._init_ai_controller()

        if not self._ai_controller:
            self._ai_advisor_screen.show_analysis_error(slot, "Failed to initialize AI")
            return

        self._ai_controller.set_database(self.ctx.db)
        char_manager = self._pob_controller.character_manager
        if char_manager:
            self._ai_controller.set_character_manager(char_manager)

        account_name = None
        if include_stash:
            account_name = self.ctx.config.data.get("stash", {}).get("account_name", "")

        try:
            success = self._ai_controller.analyze_upgrade(
                slot=slot,
                account_name=account_name,
                include_stash=include_stash,
            )
        finally:
            self.ctx.config.ai_provider = original_provider

        if success:
            def on_result(response):
                if self._ai_advisor_screen:
                    self._ai_advisor_screen.show_analysis_result(
                        slot, response.content, selected_provider
                    )

            def on_error(error_msg, traceback):
                if self._ai_advisor_screen:
                    self._ai_advisor_screen.show_analysis_error(slot, error_msg)

            if self._ai_controller and self._ai_controller._worker:
                self._ai_controller._worker.result.connect(on_result)
                self._ai_controller._worker.error.connect(on_error)
        else:
            self._ai_advisor_screen.show_analysis_error(slot, "Failed to start analysis")

    def _on_upgrade_analysis_from_advisor(self, slot: str, include_stash: bool) -> None:
        """Handle upgrade analysis request from the full-screen advisor view.

        Performs AI analysis and sends results back to the view.
        """
        if not self._upgrade_advisor_view:
            return

        # Get the view's selected provider
        selected_provider = self._upgrade_advisor_view.get_selected_provider()
        if not selected_provider:
            self._set_status("No AI provider selected")
            self._upgrade_advisor_view.show_analysis_error(slot, "No AI provider selected")
            return

        # Check if the provider has an API key (unless it's a local provider)
        from data_sources.ai import is_local_provider
        if not is_local_provider(selected_provider):
            api_key = self.ctx.config.get_ai_api_key(selected_provider)
            if not api_key:
                self._set_status(f"No API key configured for {selected_provider}")
                self._upgrade_advisor_view.show_analysis_error(
                    slot,
                    f"No API key configured for {selected_provider}.\n"
                    f"Add your API key in Settings > AI."
                )
                return

        # Temporarily set the config provider to the selected one
        original_provider = self.ctx.config.ai_provider
        self.ctx.config.ai_provider = selected_provider

        if not self._ai_controller:
            self._init_ai_controller()

        if not self._ai_controller:
            self._upgrade_advisor_view.show_analysis_error(slot, "Failed to initialize AI")
            return

        # Set up the AI controller with database for stash access
        self._ai_controller.set_database(self.ctx.db)
        char_manager = self._pob_controller.character_manager
        if char_manager:
            self._ai_controller.set_character_manager(char_manager)

        # Get account name from config (only needed if include_stash is True)
        account_name = None
        if include_stash:
            account_name = self.ctx.config.data.get("stash", {}).get("account_name", "")

        # Perform analysis - the controller will handle the async work
        try:
            success = self._ai_controller.analyze_upgrade(
                slot=slot,
                account_name=account_name,
                include_stash=include_stash,
            )
        finally:
            # Restore original provider (worker has captured the selected one)
            self.ctx.config.ai_provider = original_provider

        if success:
            # Connect to get results back (use a one-time connection)
            def on_result(response):
                if self._upgrade_advisor_view:
                    self._upgrade_advisor_view.show_analysis_result(
                        slot, response.content, selected_provider
                    )

            def on_error(error_msg, traceback):
                if self._upgrade_advisor_view:
                    self._upgrade_advisor_view.show_analysis_error(slot, error_msg)

            # Reconnect signals for this specific request
            if self._ai_controller and self._ai_controller._worker:
                self._ai_controller._worker.result.connect(on_result)
                self._ai_controller._worker.error.connect(on_error)
        else:
            self._upgrade_advisor_view.show_analysis_error(slot, "Failed to start analysis")

    # -------------------------------------------------------------------------
    # Shortcuts
    # -------------------------------------------------------------------------

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts using the ShortcutManager."""
        manager = get_shortcut_manager()
        manager.set_window(self)

        # Register all action callbacks
        # General
        manager.register("show_shortcuts", self._show_shortcuts)
        manager.register("show_command_palette", self._show_command_palette)
        manager.register("show_tips", self._show_tips)
        manager.register("exit", lambda: (self.close(), None)[-1])

        # Price Checking
        manager.register("check_price", self._on_check_price)
        manager.register("paste_and_check", self._paste_and_check)
        manager.register("clear_input", self._clear_input)
        manager.register("focus_input", self._focus_input)
        manager.register("focus_filter", self._focus_filter)

        # Build & PoB
        manager.register("show_pob_characters", self._show_pob_characters)
        manager.register("show_bis_search", self._show_bis_search)
        manager.register("show_upgrade_finder", self._show_upgrade_finder)
        manager.register("show_upgrade_advisor", self._show_upgrade_advisor)
        manager.register("show_build_library", self._show_build_library)
        manager.register("show_build_comparison", self._show_build_comparison)
        manager.register("show_item_comparison", self._show_item_comparison)
        manager.register("show_rare_eval_config", self._show_rare_eval_config)

        # Navigation - Screen switching
        manager.register("switch_to_evaluator", self._switch_to_evaluator)
        manager.register("switch_to_advisor", self._switch_to_advisor)
        manager.register("switch_to_daytrader", self._switch_to_daytrader)
        manager.register("show_history", self._show_history)
        manager.register("show_stash_viewer", self._show_stash_viewer)
        manager.register("show_recent_sales", self._show_recent_sales)
        manager.register("show_sales_dashboard", self._show_sales_dashboard)
        manager.register("show_price_rankings", self._show_price_rankings)

        # View & Theme
        manager.register("toggle_theme", self._toggle_theme)
        manager.register("cycle_theme", self._cycle_theme)
        manager.register("toggle_rare_panel", self._toggle_rare_panel)

        # Data & Export
        manager.register("export_results", self._export_results)
        manager.register("copy_all_tsv", self._copy_all_as_tsv)
        manager.register("open_log_file", self._open_log_file)
        manager.register("open_config_folder", self._open_config_folder)
        manager.register("show_data_sources", self._show_data_sources)

        # Register all shortcuts with Qt
        manager.register_all()

    def _focus_input(self) -> None:
        """Focus the item input text area."""
        self.input_text.setFocus()

    def _focus_filter(self) -> None:
        """Focus the results filter input."""
        self.filter_input.setFocus()
        self.filter_input.selectAll()

    def _toggle_rare_panel(self) -> None:
        """Toggle the rare evaluation panel visibility."""
        self.rare_eval_panel.setVisible(not self.rare_eval_panel.isVisible())

    def _cycle_theme(self) -> None:
        """Cycle through all available themes."""
        if self._theme_controller:
            self._theme_controller.cycle_theme(self)

    def _show_command_palette(self) -> None:
        """Show the command palette for quick access to all actions."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        manager = get_shortcut_manager()
        actions = manager.get_action_for_palette()

        dialog = CommandPaletteDialog(
            actions=actions,
            on_action=self._execute_palette_action,
            parent=self,
        )

        # Center dialog over main window
        dialog.move(
            self.x() + (self.width() - dialog.width()) // 2,
            self.y() + 100,
        )

        dialog.exec()

    def _execute_palette_action(self, action_id: str) -> None:
        """Execute an action from the command palette."""
        manager = get_shortcut_manager()
        if not manager.trigger(action_id):
            self._set_status(f"Action not available: {action_id}")

    # -------------------------------------------------------------------------
    # Price Checking
    # -------------------------------------------------------------------------

    def _on_check_price(self) -> None:
        """Handle Check Price button click (keyboard shortcut)."""
        if self._check_in_progress:
            return

        item_text = self.input_text.toPlainText().strip()
        if not item_text:
            self._set_status("No item text to check")
            return

        # Use the current session tab index
        current_index = self.session_tabs.currentIndex()
        self._do_price_check(item_text, current_index)

    def _do_price_check(self, item_text: str, session_index: int) -> None:
        """Perform price check for a specific session using PriceCheckController."""
        panel = self.session_tabs.get_panel(session_index)
        if not panel:
            self._set_status("No active session")
            return

        self._check_in_progress = True
        panel.check_btn.setEnabled(False)
        self._set_status("Checking price...")

        try:
            # Use the controller for price checking
            result = self._price_controller.check_price(item_text)

            if result.is_err():
                self._set_status(result.error or "Unknown error")
                return

            # Unwrap the successful result
            data = result.unwrap()

            # Update item inspector
            panel.item_inspector.set_item(data.parsed_item)

            # Clear the paste window - item is now shown in inspector
            panel.input_text.clear()

            # Update session panel with formatted results
            panel.set_results(data.formatted_rows)
            self._update_summary()

            # Handle rare item evaluation panel
            if data.is_rare and data.evaluation:
                panel.rare_eval_panel.set_evaluation(data.evaluation)
                panel.rare_eval_panel.setVisible(True)
            else:
                panel.rare_eval_panel.setVisible(False)

            # Update quick verdict panel (casual player summary)
            # Get best price from results for verdict calculation
            best_price = None
            if data.formatted_rows:
                # Use chaos_value from first result as estimate
                first_row = data.formatted_rows[0]
                best_price = first_row.get("chaos_value")
                if best_price is not None:
                    try:
                        best_price = float(best_price)
                    except (ValueError, TypeError):
                        best_price = None

            # Calculate verdict with parsed item and price
            verdict_result = panel.quick_verdict_panel.update_verdict(
                data.parsed_item,
                price_chaos=best_price
            )
            panel.quick_verdict_panel.setVisible(True)

            # Record verdict in session statistics
            panel.record_verdict(verdict_result)

            # Add to history
            self._history_manager.add_entry(item_text, data.parsed_item, data.results)

            # Update status and show toast
            self._set_status(self._price_controller.get_price_summary(data))
            show_toast, toast_type, message = self._price_controller.should_show_toast(data)
            if show_toast:
                if toast_type == "success":
                    self._toast_manager.success(message)
                else:
                    self._toast_manager.info(message)

            # Show system tray notification for high-value items
            if self._tray_controller:
                self._tray_controller.maybe_show_alert(data)

        except Exception as e:
            self.logger.exception("Price check failed")
            self._set_status(f"Error: {e}")
            self._toast_manager.error(f"Price check failed: {e}")
        finally:
            self._check_in_progress = False
            panel.check_btn.setEnabled(True)

    def _clear_input(self) -> None:
        """Clear the input text."""
        self.input_text.clear()
        self.item_inspector.clear()

    def _paste_and_check(self) -> None:
        """Paste from clipboard and immediately check price."""
        clipboard = QApplication.clipboard()
        if clipboard:
            text = clipboard.text()
            if text:
                self.input_text.setPlainText(text)
                self._on_check_price()

    # -------------------------------------------------------------------------
    # Results Context Menu
    # -------------------------------------------------------------------------

    def _show_results_context_menu(self, pos) -> None:
        """Show context menu for results table."""
        if self._results_context_controller:
            self._results_context_controller.show_context_menu(pos, self.results_table)

    def _on_result_selected(self, row_data: Dict[str, Any]) -> None:
        """Handle result row selection."""
        # Could update item inspector or show details

    def _on_pin_items_requested(self, items: List[Dict[str, Any]]) -> None:
        """Handle request to pin items from results table."""
        pinned_count = self.pinned_items_widget.pin_items(items)
        if pinned_count > 0:
            self._toast_manager.success(f"Pinned {pinned_count} item(s)")
        elif len(items) > 0:
            self._toast_manager.warning("Items already pinned or limit reached")

    def _on_pinned_item_inspected(self, item_data: Dict[str, Any]) -> None:
        """Handle request to inspect a pinned item."""
        # Update item inspector with the pinned item
        item = item_data.get("_item")
        if item:
            self.item_inspector.set_item(item, self._current_build_stats)
        else:
            # Just show the item name in status
            item_name = item_data.get("item_name", "Unknown")
            self._set_status(f"Inspecting: {item_name}")

    def _on_compare_items_requested(self, items: List[Dict[str, Any]]) -> None:
        """Handle request to compare items from results table."""
        if len(items) < 2 or len(items) > 3:
            self._toast_manager.warning("Select 2-3 items to compare")
            return

        # Extract ParsedItems from row data
        parsed_items = []
        for item_data in items:
            item = item_data.get("_item")
            if item:
                parsed_items.append(item)

        if len(parsed_items) >= 2:
            try:
                from gui_qt.dialogs.item_comparison_dialog import ItemComparisonDialog
                dialog = ItemComparisonDialog(
                    parent=self,
                    app_context=self.ctx,
                )
                dialog.exec()
            except ImportError:
                self._toast_manager.error("Comparison dialog not available")
        else:
            self._toast_manager.warning("Not enough valid items to compare")

    # -------------------------------------------------------------------------
    # Column Visibility
    # -------------------------------------------------------------------------

    def _toggle_column(self, column: str, visible: bool) -> None:
        """Toggle column visibility."""
        self.results_table.set_column_visible(column, visible)

    # -------------------------------------------------------------------------
    # Theme Management
    # -------------------------------------------------------------------------

    def _init_theme_controller(self) -> None:
        """Initialize the theme controller and apply theme from config."""
        config = self.ctx.config if hasattr(self.ctx, 'config') else None
        self._theme_controller = ThemeController(
            config=config,
            on_status=self._set_status,
        )
        self._theme_controller.set_theme_actions(self._theme_actions)
        self._theme_controller.set_accent_actions(self._accent_actions)
        self._theme_controller.initialize(self)

    def _set_theme(self, theme: Theme) -> None:
        """Set the application theme."""
        if self._theme_controller:
            self._theme_controller.set_theme(theme, self)

    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        if self._theme_controller:
            self._theme_controller.toggle_theme(self)

    def _set_accent_color(self, accent_key: Optional[str]) -> None:
        """Set the application accent color."""
        if self._theme_controller:
            self._theme_controller.set_accent_color(accent_key, self)

    # -------------------------------------------------------------------------
    # System Tray
    # -------------------------------------------------------------------------

    def _init_system_tray(self) -> None:
        """Initialize the system tray controller."""
        self._tray_controller = TrayController(
            parent=self,
            ctx=self.ctx,
            on_settings=self._show_settings,
            on_cleanup=self._cleanup_before_close,
        )
        self._tray_controller.initialize()

    def changeEvent(self, event) -> None:
        """Handle window state changes (minimize to tray)."""
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.WindowStateChange:
            # Check if window was minimized
            if self.isMinimized() and self._tray_controller and self._tray_controller.handle_minimize():
                event.ignore()
                return

        super().changeEvent(event)

    def _show_settings(self) -> None:
        """Show settings dialog."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.ctx.config, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply updated verdict thresholds
            self._apply_verdict_thresholds()
            self._set_status("Settings saved")

    def _apply_verdict_thresholds(self) -> None:
        """Apply verdict thresholds from config to session tabs."""
        if hasattr(self, 'session_tabs'):
            vendor = self.ctx.config.verdict_vendor_threshold
            keep = self.ctx.config.verdict_keep_threshold
            self.session_tabs.set_verdict_thresholds(vendor, keep)

    def _load_verdict_statistics(self) -> None:
        """Load saved verdict statistics from database for today's session."""
        try:
            from datetime import datetime
            from core.quick_verdict import VerdictStatistics

            # Get current league and game version from config
            league = self.ctx.config.league or "Standard"
            game_version = self.ctx.config.current_game.value
            session_date = datetime.now().strftime("%Y-%m-%d")

            # Try to load today's stats from database
            saved_stats = self.ctx.db.get_verdict_statistics(
                league=league,
                game_version=game_version,
                session_date=session_date,
            )

            if saved_stats:
                # Convert dict to VerdictStatistics
                stats = VerdictStatistics.from_dict(saved_stats)
                self.session_tabs.set_current_verdict_stats(stats)
                self.logger.info(
                    f"Loaded verdict stats for {league} ({session_date}): "
                    f"{stats.total_count} items"
                )
        except Exception as e:
            self.logger.warning(f"Failed to load verdict statistics: {e}")

    def _cleanup_before_close(self) -> None:
        """Clean up resources before closing."""
        # Stop rankings worker
        if self._rankings_worker:
            self._rankings_worker.quit()
            self._rankings_worker.wait(1000)

        # Stop loot tracking
        if self._loot_controller:
            self._loot_controller.cleanup()

        # Close all managed windows
        self._window_manager.close_all()

        # Cleanup tray
        if self._tray_controller:
            self._tray_controller.cleanup()

        # Close app context resources
        if hasattr(self.ctx, "close"):
            self.ctx.close()

    # -------------------------------------------------------------------------
    # Menu Actions
    # -------------------------------------------------------------------------

    def _open_log_file(self) -> None:
        """Open the log file in the default viewer."""
        log_path = Path(__file__).parent.parent / "logs" / "price_checker.log"
        if log_path.exists():
            os.startfile(str(log_path))
        else:
            QMessageBox.information(self, "Log File", "No log file found.")

    def _open_config_folder(self) -> None:
        """Open the config folder."""
        config_path = Path(__file__).parent.parent / "data"
        if config_path.exists():
            os.startfile(str(config_path))
        else:
            QMessageBox.information(self, "Config Folder", "Config folder not found.")

    def _export_results(self) -> None:
        """Export results to TSV file."""
        panel = self.session_tabs.get_current_panel()
        if not panel or not panel._all_results:
            QMessageBox.information(self, "Export", "No results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "", "TSV Files (*.tsv);;All Files (*)"
        )

        if path:
            try:
                panel.results_table.export_tsv(path)
                self._set_status(f"Exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def _copy_all_as_tsv(self) -> None:
        """Copy all results as TSV."""
        tsv = self.results_table.to_tsv(include_header=True)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(tsv)
        self._set_status("All results copied as TSV")

    def _show_history(self) -> None:
        """Show session history dialog with re-check capability."""
        if self._history_manager.is_empty():
            QMessageBox.information(self, "Recent Items", "No items checked this session.")
            return

        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog
        from gui_qt.services.history_manager import HistoryEntry
        from typing import cast, Union

        # Cast to satisfy type checker - list[HistoryEntry] is compatible with List[Union[...]]
        history_entries = cast(
            "List[Union[HistoryEntry, Dict[str, Any]]]",
            self._history_manager.get_entries()
        )
        dialog = RecentItemsDialog(history_entries, self)
        dialog.item_selected.connect(self._recheck_item_from_history)
        dialog.exec()

    def _recheck_item_from_history(self, item_text: str) -> None:
        """Re-check an item from history."""
        if item_text:
            self.input_text.setPlainText(item_text)
            self._on_check_price()

    def _show_data_sources(self) -> None:
        """Show data sources dialog."""
        text = "Data Sources:\n\n"
        text += "- poe.ninja: Real-time economy data\n"
        text += "- poe.watch: Alternative price source\n"
        text += "- Trade API: Official trade site data\n"

        QMessageBox.information(self, "Data Sources", text)

    def _show_recent_sales(self) -> None:
        """Show recent sales window."""
        self._nav_controller.show_recent_sales()

    def _show_sales_dashboard(self) -> None:
        """Show sales dashboard window."""
        self._nav_controller.show_sales_dashboard()

    def _show_loot_dashboard(self) -> None:
        """Show loot tracking dashboard window."""
        # Lazily initialize loot tracking controller
        if not self._loot_controller:
            self._loot_controller = LootTrackingController(self.ctx, parent=self)
            # Auto-start monitoring if configured
            if self.ctx.config.loot_tracking_enabled:
                self._loot_controller.start_monitoring()

        from gui_qt.windows.loot_dashboard_window import LootDashboardWindow

        self._window_manager.show_window(
            "loot_dashboard",
            LootDashboardWindow,
            ctx=self.ctx,
            controller=self._loot_controller,
        )

    def _show_stash_viewer(self) -> None:
        """Show stash viewer window."""
        self._nav_controller.show_stash_viewer()

    def _collect_economy_snapshot(self) -> None:
        """Collect economy snapshot from poe.ninja for current league."""
        from core.economy import LeagueEconomyService

        league = self.ctx.config.league or "Keepers"
        self._set_status(f"Collecting economy snapshot for {league}...")

        try:
            service = LeagueEconomyService(self.ctx.db)
            snapshot = service.fetch_and_store_snapshot(league)

            if snapshot:
                self._set_status(
                    f"Economy snapshot saved: {league} - "
                    f"Divine={snapshot.divine_to_chaos:.0f}c"
                )
            else:
                self._set_status(f"No economy data available for {league}")
        except Exception as e:
            self.logger.error(f"Failed to collect economy snapshot: {e}")
            self._set_status(f"Error collecting snapshot: {e}")

    def _show_price_history(self) -> None:
        """Show price history analytics window."""
        from gui_qt.windows.price_history_window import PriceHistoryWindow

        window = PriceHistoryWindow(ctx=self.ctx, parent=self)
        window.exec()

    def _show_pob_characters(self) -> None:
        """Show PoB character manager window."""
        self._nav_controller.show_pob_characters()

    def _on_pob_profile_selected(self, profile_name: str) -> None:
        """Handle PoB profile selection."""
        self._pob_controller.on_profile_selected(profile_name, self._price_controller)

    def _on_pob_price_check(self, item_text: str) -> None:
        """Handle price check request from PoB window."""
        self._pob_controller.handle_pob_price_check(
            item_text=item_text,
            input_text_widget=self.input_text,
            main_window=self,
            check_callback=self._on_check_price,
        )

    def _on_pob_profile_changed(self, profile_name: str) -> None:
        """Handle PoB profile selection change - update build stats for inspector."""
        self._pob_controller.on_profile_changed(profile_name, self.item_inspector)

    def _show_rare_eval_config(self) -> None:
        """Show rare evaluation config window."""
        self._nav_controller.show_rare_eval_config()

    def _reload_rare_evaluator(self) -> None:
        """Reload the rare item evaluator."""
        self._init_rare_evaluator()
        # Update the controller with new evaluator
        self._price_controller.set_rare_evaluator(self._rare_evaluator)
        # Update session tabs with new evaluator for meta info display
        if hasattr(self, 'session_tabs'):
            self.session_tabs.set_rare_evaluator(self._rare_evaluator)
        self._set_status("Rare evaluation settings reloaded")

    def _on_update_meta_requested(self) -> None:
        """Handle meta weights update request from rare evaluation panel."""
        self._set_status("Updating meta weights...")
        try:
            # Reload the evaluator to refresh meta weights
            self._reload_rare_evaluator()
            self._set_status("Meta weights updated successfully")
        except Exception as e:
            self.logger.error(f"Failed to update meta weights: {e}")
            self._set_status(f"Failed to update meta weights: {e}")

    def _show_price_rankings(self) -> None:
        """Show price rankings window."""
        self._nav_controller.show_price_rankings()

    def _on_ranking_price_check(self, item_name: str) -> None:
        """Handle price check request from rankings window."""
        # Set the item text in the input field and trigger price check
        self.input_text.setPlainText(item_name)
        self._on_check_price()

    def _show_build_comparison(self) -> None:
        """Show build comparison dialog."""
        self._nav_controller.show_build_comparison()

    def _on_loadout_selected(self, config: dict) -> None:
        """Handle loadout selection from the selector dialog."""
        # Could be used to apply selected tree spec, skill set, or item set
        tree_spec = config.get("tree_spec")
        skill_set = config.get("skill_set")
        item_set = config.get("item_set")

        parts = []
        if tree_spec:
            parts.append(f"Tree: {tree_spec.get('title', 'Unknown')}")
        if skill_set:
            parts.append(f"Skills: {skill_set.get('title', 'Unknown')}")
        if item_set:
            parts.append(f"Items: {item_set.get('title', 'Unknown')}")

        if parts:
            self._set_status(f"Selected loadout: {', '.join(parts)}")

    def _show_bis_search(self) -> None:
        """Show BiS item search dialog."""
        self._nav_controller.show_bis_search()

    def _show_upgrade_finder(self) -> None:
        """Show upgrade finder dialog."""
        self._nav_controller.show_upgrade_finder()

    def _show_build_library(self) -> None:
        """Show build library dialog."""
        self._nav_controller.show_build_library()

    def _show_local_builds_import(self) -> None:
        """Show dialog to import local PoB builds."""
        from gui_qt.dialogs.local_builds_dialog import LocalBuildsDialog

        dialog = LocalBuildsDialog(self)
        dialog.build_imported.connect(self._on_local_build_imported)
        dialog.exec()

    def _on_local_build_imported(self, name: str, build_data: dict) -> None:
        """Handle local build import completion."""
        self._set_status(f"Imported build: {name}")

        # Refresh PoB panel if it exists
        if hasattr(self, 'pob_panel') and self.pob_panel:
            self.pob_panel.refresh()

        # Update the active profile in the controller
        self._pob_controller.on_profile_selected(name, self._price_controller)

    def _show_item_comparison(self) -> None:
        """Show item comparison dialog."""
        self._nav_controller.show_item_comparison()

    def _paste_sample(self, item_type: str) -> None:
        """Paste a sample item of the given type."""
        samples = SAMPLE_ITEMS.get(item_type, [])
        if samples:
            sample = random.choice(samples)
            self.input_text.setPlainText(sample)
            self._set_status(f"Pasted sample {item_type}")

    def _wipe_database(self) -> None:
        """Wipe the database after confirmation."""
        result = QMessageBox.warning(
            self,
            "Wipe Database",
            "Are you sure you want to delete all recorded sales?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            try:
                self.ctx.db.wipe_all_data()
                self._set_status("Database wiped")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to wipe database: {e}")

    def _show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        show_shortcuts_dialog(self)

    def _show_tips(self) -> None:
        """Show usage tips dialog."""
        show_tips_dialog(self)

    def _show_about(self) -> None:
        """Show about dialog."""
        show_about_dialog(self)

    def closeEvent(self, event) -> None:
        """Handle window close - clean up application resources."""
        self.logger.info("Closing application...")
        self._cleanup_before_close()
        self.logger.info("Application closed")
        super().closeEvent(event)


def run(ctx: "AppContext") -> None:
    """Run the PyQt6 application.

    Note: This function is kept for backward compatibility.
    The preferred entry point is now main.py which handles
    the loading screen and QApplication setup.
    """
    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        # Set Windows AppUserModelID for proper taskbar icon grouping
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "sacrosanct.poe-price-checker.1.0"
                )
            except Exception:
                pass  # Not critical if this fails

        app = QApplication(sys.argv)
        app.setStyle("Fusion")  # Consistent cross-platform look

        # Set application icon
        icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        else:
            # Fallback to PNG
            png_path = Path(__file__).parent.parent / "assets" / "icon.png"
            if png_path.exists():
                app.setWindowIcon(QIcon(str(png_path)))

    # Show loading screen
    from gui_qt.widgets.loading_screen import LoadingScreen
    loading = LoadingScreen()
    loading.set_version("1.5.0")
    loading.show()
    loading.set_status("Creating main window...")
    loading.set_progress(85)
    app.processEvents()

    # Create main window (this does the heavy initialization)
    window = PriceCheckerWindow(ctx)

    # Finish loading and show main window
    loading.set_status("Ready!")
    loading.set_progress(100)
    app.processEvents()

    # Close loading screen and show main window
    loading.close()
    window.showMaximized()

    sys.exit(app.exec())
