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
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, QObject
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenuBar,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QMenu,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QDialog,
)

from gui_qt.styles import (
    COLORS, Theme, get_theme_manager,
    THEME_CATEGORIES, THEME_DISPLAY_NAMES, POE_CURRENCY_COLORS
)
from gui_qt.menus.menu_builder import (
    MenuBuilder, MenuConfig, MenuItem, MenuSection, SubMenu, create_resources_menu
)
from gui_qt.shortcuts import get_shortcut_manager
from gui_qt.sample_items import SAMPLE_ITEMS
from gui_qt.dialogs.help_dialogs import (
    show_shortcuts_dialog, show_tips_dialog, show_about_dialog
)
from gui_qt.widgets.results_table import ResultsTableWidget
from gui_qt.widgets.item_inspector import ItemInspectorWidget
from gui_qt.widgets.rare_evaluation_panel import RareEvaluationPanelWidget
from gui_qt.widgets.toast_notification import ToastManager
from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget
from gui_qt.widgets.session_tabs import SessionTabWidget, SessionPanel
from gui_qt.workers import RankingsPopulationWorker
from gui_qt.services import get_window_manager
from gui_qt.controllers import PriceCheckController, ThemeController
from core.build_stat_calculator import BuildStats
from core.constants import HISTORY_MAX_ENTRIES
from core.history import HistoryEntry

if TYPE_CHECKING:
    from core.app_context import AppContext


class PriceCheckerWindow(QMainWindow):
    """Main window for the PoE Price Checker application."""

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ctx = ctx
        self.logger = logging.getLogger(__name__)

        # State
        self._check_in_progress = False
        # Bounded history to prevent unbounded memory growth
        self._history: Deque[HistoryEntry] = deque(maxlen=HISTORY_MAX_ENTRIES)

        # Window manager for child window lifecycle
        self._window_manager = get_window_manager()
        self._window_manager.set_main_window(self)

        # PoB integration
        self._character_manager = None
        self._upgrade_checker = None

        # Rare item evaluator
        self._rare_evaluator = None
        self._init_rare_evaluator()

        # Initialize PoB character manager
        self._init_character_manager()

        # Price check controller
        self._price_controller = PriceCheckController(
            parser=ctx.parser,
            price_service=ctx.price_service,
            rare_evaluator=self._rare_evaluator,
            upgrade_checker=self._upgrade_checker,
        )

        # Theme controller (initialized after menu bar creation)
        self._theme_controller: Optional[ThemeController] = None

        # Rankings population worker
        self._rankings_worker: Optional[RankingsPopulationWorker] = None

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

        self._set_status("Ready")

        # Start background rankings population check
        self._start_rankings_population()

        # Initialize build stats for item inspector from active PoB profile
        self._update_build_stats_for_inspector()

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

    def _init_character_manager(self) -> None:
        """Initialize the PoB character manager."""
        try:
            from core.pob_integration import CharacterManager
            storage_path = Path(__file__).parent.parent / "data" / "characters.json"
            self._character_manager = CharacterManager(storage_path=storage_path)
        except Exception as e:
            self.logger.warning(f"Failed to initialize character manager: {e}")

    def _update_build_stats_for_inspector(self) -> None:
        """Update the item inspector with build stats from the active PoB profile."""
        from core.dps_impact_calculator import DPSStats

        self.logger.info("Updating build stats for item inspector")
        if not self._character_manager:
            self.logger.info("No character manager available")
            return

        try:
            profile = self._character_manager.get_active_profile()
            self.logger.info(f"Active profile: {profile.name if profile else None}")
            if profile and profile.build and profile.build.stats:
                self.logger.info(f"Profile has {len(profile.build.stats)} build stats")
                build_stats = BuildStats.from_pob_stats(profile.build.stats)
                self.item_inspector.set_build_stats(build_stats)
                self.logger.info(
                    f"Set build stats: life={build_stats.total_life}, life_inc={build_stats.life_inc}%"
                )

                # Also set DPS stats for damage impact calculations
                dps_stats = DPSStats.from_pob_stats(profile.build.stats)
                self.item_inspector.set_dps_stats(dps_stats)
                if dps_stats.combined_dps > 0:
                    self.logger.info(
                        f"Set DPS stats: {dps_stats.combined_dps:.0f} DPS, "
                        f"type={dps_stats.primary_damage_type.value}"
                    )
            else:
                self.logger.info(f"No build stats available")
                self.item_inspector.set_build_stats(None)
                self.item_inspector.set_dps_stats(None)
        except Exception as e:
            self.logger.warning(f"Failed to update build stats: {e}")

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
        'filter_input', 'source_filter', 'rare_eval_panel', 'check_btn'
    })

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
            self._update_build_stats_for_session(panel)

    def _on_session_check_price(self, item_text: str, session_index: int) -> None:
        """Handle check price request from a session tab."""
        if self._check_in_progress:
            return
        self._do_price_check(item_text, session_index)

    def _update_build_stats_for_session(self, panel: SessionPanel) -> None:
        """Update build stats for a specific session panel's inspector."""
        from core.dps_impact_calculator import DPSStats

        if not self._character_manager:
            return

        try:
            profile = self._character_manager.get_active_profile()
            if profile and profile.build and profile.build.stats:
                build_stats = BuildStats.from_pob_stats(profile.build.stats)
                panel.item_inspector.set_build_stats(build_stats)

                dps_stats = DPSStats.from_pob_stats(profile.build.stats)
                panel.item_inspector.set_dps_stats(dps_stats)
            else:
                panel.item_inspector.set_build_stats(None)
                panel.item_inspector.set_dps_stats(None)
        except Exception as e:
            self.logger.warning(f"Failed to update build stats for session: {e}")

    # -------------------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        """Create the application menu bar using declarative MenuBuilder."""
        menubar = self.menuBar()
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
                    MenuItem("E&xit", handler=self.close, shortcut="Alt+F4"),
                ]),
            ]),
            MenuConfig("&Build", [
                MenuItem("&PoB Characters", handler=self._show_pob_characters,
                         shortcut="Ctrl+B"),
                MenuItem("&Compare Build Trees...", handler=self._show_build_comparison),
                MenuItem("Browse &Loadouts...", handler=self._show_loadout_selector),
                MenuItem("Build &Library...", handler=self._show_build_library,
                         shortcut="Ctrl+Alt+B"),
                MenuItem("Find &BiS Item...", handler=self._show_bis_search,
                         shortcut="Ctrl+I"),
                MenuItem("&Upgrade Finder...", handler=self._show_upgrade_finder,
                         shortcut="Ctrl+U"),
                MenuItem("Compare &Items...", handler=self._show_item_comparison,
                         shortcut="Ctrl+Shift+I"),
                MenuSection([
                    MenuItem("Rare Item &Settings...", handler=self._show_rare_eval_config),
                ]),
            ]),
            MenuConfig("&Prices", [
                MenuItem("&Top 20 Rankings", handler=self._show_price_rankings),
                MenuSection([
                    MenuItem("&Recent Sales", handler=self._show_recent_sales),
                    MenuItem("Sales &Dashboard", handler=self._show_sales_dashboard),
                ]),
                MenuSection([
                    MenuItem("Data &Sources Info", handler=self._show_data_sources),
                ]),
            ]),
        ]
        builder.build(menubar, static_menus)

        # View menu - dynamic content (themes, accents, columns)
        self._create_view_menu(menubar)

        # Resources menu - use declarative config
        resources_menu = menubar.addMenu("&Resources")
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
        view_menu = menubar.addMenu("&View")

        history_action = QAction("Session &History", self)
        history_action.triggered.connect(self._show_history)
        view_menu.addAction(history_action)

        stash_action = QAction("&Stash Viewer", self)
        stash_action.triggered.connect(self._show_stash_viewer)
        view_menu.addAction(stash_action)

        view_menu.addSeparator()

        # Theme submenu with categories
        self._theme_menu = view_menu.addMenu("&Theme")
        self._theme_actions: Dict[Theme, QAction] = {}

        for category, themes in THEME_CATEGORIES.items():
            if category != "Standard":
                self._theme_menu.addSeparator()
                label_action = QAction(f"[ {category} ]", self)
                label_action.setEnabled(False)
                self._theme_menu.addAction(label_action)

            for theme in themes:
                display_name = THEME_DISPLAY_NAMES.get(theme, theme.value)
                action = QAction(display_name, self)
                action.setCheckable(True)
                action.triggered.connect(lambda checked, t=theme: self._set_theme(t))
                self._theme_menu.addAction(action)
                self._theme_actions[theme] = action

        view_menu.addSeparator()
        toggle_theme_action = QAction("&Quick Toggle Dark/Light", self)
        toggle_theme_action.setShortcut(QKeySequence("Ctrl+T"))
        toggle_theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(toggle_theme_action)

        # Accent Color submenu
        self._accent_menu = view_menu.addMenu("&Accent Color")
        self._accent_actions: Dict[Optional[str], QAction] = {}

        default_action = QAction("Theme Default", self)
        default_action.setCheckable(True)
        default_action.triggered.connect(lambda: self._set_accent_color(None))
        self._accent_menu.addAction(default_action)
        self._accent_actions[None] = default_action

        self._accent_menu.addSeparator()

        for key, data in POE_CURRENCY_COLORS.items():
            action = QAction(data["name"], self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, k=key: self._set_accent_color(k))
            self._accent_menu.addAction(action)
            self._accent_actions[key] = action

        view_menu.addSeparator()

        # Column visibility submenu
        columns_menu = view_menu.addMenu("&Columns")
        self._column_actions: Dict[str, QAction] = {}
        for col in ["item_name", "variant", "links", "chaos_value", "divine_value",
                    "listing_count", "source", "upgrade"]:
            action = QAction(col.replace("_", " ").title(), self)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda checked, c=col: self._toggle_column(c, checked))
            columns_menu.addAction(action)
            self._column_actions[col] = action

    def _create_dev_menu(self, menubar: QMenuBar) -> None:
        """Create Dev menu with dynamic sample items."""
        dev_menu = menubar.addMenu("&Dev")

        paste_menu = dev_menu.addMenu("Paste &Sample")
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
        """Create the main content area with integrated PoB panel."""
        central = QWidget()
        self.setCentralWidget(central)

        # Main horizontal splitter: PoB panel (left) | Price check (right)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ========== LEFT SIDE: PoB Panel + Pinned Items ==========
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setMinimumWidth(250)
        left_splitter.setMaximumWidth(400)

        # PoB Equipment panel
        pob_group = QGroupBox("PoB Equipment")
        pob_layout = QVBoxLayout(pob_group)
        pob_layout.setContentsMargins(4, 4, 4, 4)

        # Create embedded PoB panel
        from gui_qt.widgets.pob_panel import PoBPanel
        self.pob_panel = PoBPanel(self._character_manager, parent=self)
        self.pob_panel.price_check_requested.connect(self._on_pob_price_check)
        # Update build stats when profile changes
        self.pob_panel.profile_combo.currentTextChanged.connect(
            self._on_pob_profile_changed
        )
        pob_layout.addWidget(self.pob_panel)
        left_splitter.addWidget(pob_group)

        # Pinned Items panel
        pinned_group = QGroupBox("Pinned Items")
        pinned_layout = QVBoxLayout(pinned_group)
        pinned_layout.setContentsMargins(4, 4, 4, 4)

        self.pinned_items_widget = PinnedItemsWidget()
        self.pinned_items_widget.item_inspected.connect(self._on_pinned_item_inspected)
        pinned_layout.addWidget(self.pinned_items_widget)
        left_splitter.addWidget(pinned_group)

        # Set initial splitter sizes (PoB: 60%, Pinned: 40%)
        left_splitter.setSizes([400, 250])

        main_splitter.addWidget(left_splitter)

        # ========== RIGHT SIDE: Session Tabs (multiple price-checking sessions) ==========
        self.session_tabs = SessionTabWidget()
        self.session_tabs.check_price_requested.connect(self._on_session_check_price)
        self.session_tabs.row_selected.connect(self._on_result_selected)
        self.session_tabs.pin_requested.connect(self._on_pin_items_requested)
        self.session_tabs.compare_requested.connect(self._on_compare_items_requested)

        # Connect context menu for results table in each session
        self.session_tabs.currentChanged.connect(self._on_session_changed)

        # Add right panel to main splitter
        main_splitter.addWidget(self.session_tabs)

        # Set initial splitter sizes (PoB panel: 300, Price check: rest)
        main_splitter.setSizes([300, 1100])

        # Add main splitter to central layout
        main_layout.addWidget(main_splitter)

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
                    pass
            self.summary_label.setText(f"{count} items | {total_chaos:.1f}c total")

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
        manager.register("exit", self.close)

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
        manager.register("show_build_library", self._show_build_library)
        manager.register("show_build_comparison", self._show_build_comparison)
        manager.register("show_item_comparison", self._show_item_comparison)
        manager.register("show_rare_eval_config", self._show_rare_eval_config)

        # Navigation
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
                self._set_status(result.error)
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

            # Add to history
            self._history.append(
                HistoryEntry.from_price_check(item_text, data.parsed_item, data.results)
            )

            # Update status and show toast
            self._set_status(self._price_controller.get_price_summary(data))
            show_toast, toast_type, message = self._price_controller.should_show_toast(data)
            if show_toast:
                if toast_type == "success":
                    self._toast_manager.success(message)
                else:
                    self._toast_manager.info(message)

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
        text = clipboard.text()
        if text:
            self.input_text.setPlainText(text)
            self._on_check_price()

    # -------------------------------------------------------------------------
    # Results Context Menu
    # -------------------------------------------------------------------------

    def _show_results_context_menu(self, pos) -> None:
        """Show context menu for results table."""
        menu = QMenu(self)

        selected = self.results_table.get_selected_row()
        if selected:
            copy_action = menu.addAction("Copy Row")
            copy_action.triggered.connect(self._copy_selected_row)

            copy_tsv_action = menu.addAction("Copy as TSV")
            copy_tsv_action.triggered.connect(self._copy_row_as_tsv)

            menu.addSeparator()

            explain_action = menu.addAction("Why This Price?")
            explain_action.triggered.connect(self._explain_price)

            menu.addSeparator()

            record_sale_action = menu.addAction("Record Sale...")
            record_sale_action.triggered.connect(self._record_sale)

        menu.exec(self.results_table.mapToGlobal(pos))

    def _on_result_selected(self, row_data: Dict[str, Any]) -> None:
        """Handle result row selection."""
        # Could update item inspector or show details
        pass

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
                    parsed_items,
                    build_stats=self._current_build_stats,
                    parent=self
                )
                dialog.exec()
            except ImportError:
                self._toast_manager.error("Comparison dialog not available")
        else:
            self._toast_manager.warning("Not enough valid items to compare")

    def _copy_selected_row(self) -> None:
        """Copy selected row to clipboard."""
        row = self.results_table.get_selected_row()
        if row:
            text = " | ".join(f"{k}: {v}" for k, v in row.items() if k != "price_explanation")
            QApplication.clipboard().setText(text)
            self._set_status("Row copied to clipboard")

    def _copy_row_as_tsv(self) -> None:
        """Copy selected row as TSV."""
        row = self.results_table.get_selected_row()
        if row:
            values = [str(row.get(col, "")) for col in self.results_table.columns
                     if col != "price_explanation"]
            QApplication.clipboard().setText("\t".join(values))
            self._set_status("Row copied as TSV")

    def _explain_price(self) -> None:
        """Show price explanation dialog."""
        from core.price_service import PriceExplanation

        row = self.results_table.get_selected_row()
        if not row:
            return

        explanation_json = row.get("price_explanation", "")
        if not explanation_json or explanation_json == "{}":
            # Show basic info even without explanation
            item_name = row.get("item_name", "Unknown")
            source = row.get("source", "Unknown")
            chaos = row.get("chaos_value", 0)
            divine = row.get("divine_value", 0)

            text = f"Item: {item_name}\n"
            text += f"Source: {source}\n"
            text += f"Price: {chaos:.1f}c"
            if divine:
                text += f" ({divine:.2f} divine)"
            text += "\n\nNo detailed explanation available for this price."

            QMessageBox.information(self, "Price Explanation", text)
            return

        try:
            explanation = PriceExplanation.from_json(explanation_json)
            lines = explanation.to_summary_lines()

            if not lines:
                lines = ["No explanation details available."]

            # Build header
            item_name = row.get("item_name", "Unknown")
            chaos = row.get("chaos_value", 0)
            divine = row.get("divine_value", 0)

            header = f"Item: {item_name}\n"
            header += f"Price: {chaos:.1f}c"
            if divine:
                header += f" ({divine:.2f} divine)"
            header += "\n" + "─" * 40 + "\n"

            text = header + "\n".join(lines)

            # Use a dialog with more room for text
            dialog = QDialog(self)
            dialog.setWindowTitle("Price Explanation")
            dialog.setMinimumSize(450, 350)

            layout = QVBoxLayout(dialog)

            # Text display
            from PyQt6.QtWidgets import QTextEdit
            text_widget = QTextEdit()
            text_widget.setReadOnly(True)
            text_widget.setPlainText(text)
            text_widget.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
            layout.addWidget(text_widget)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.exec()

        except Exception as e:
            QMessageBox.information(
                self, "Price Explanation",
                f"Could not parse price explanation: {e}"
            )

    def _record_sale(self) -> None:
        """Record a sale for the selected item."""
        row = self.results_table.get_selected_row()
        if not row:
            return

        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(
            self,
            item_name=row.get("item_name", ""),
            suggested_price=row.get("chaos_value", 0),
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            price, notes = dialog.get_values()
            try:
                self.ctx.db.record_sale(
                    item_name=row.get("item_name", ""),
                    chaos_value=price,
                    source=row.get("source", ""),
                    notes=notes,
                )
                self._set_status(f"Sale recorded: {row.get('item_name', '')} for {price}c")
                self._toast_manager.success(f"Sale recorded: {price:.0f}c")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to record sale: {e}")

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
        self._theme_controller.set_theme(theme, self)

    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        self._theme_controller.toggle_theme(self)

    def _set_accent_color(self, accent_key: Optional[str]) -> None:
        """Set the application accent color."""
        self._theme_controller.set_accent_color(accent_key, self)

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
        QApplication.clipboard().setText(tsv)
        self._set_status("All results copied as TSV")

    def _show_history(self) -> None:
        """Show session history dialog with re-check capability."""
        if not self._history:
            QMessageBox.information(self, "Recent Items", "No items checked this session.")
            return

        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        dialog = RecentItemsDialog(list(self._history), self)
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
        from gui_qt.windows.recent_sales_window import RecentSalesWindow
        self._window_manager.show_window("recent_sales", RecentSalesWindow, ctx=self.ctx)

    def _show_sales_dashboard(self) -> None:
        """Show sales dashboard window."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow
        self._window_manager.show_window("sales_dashboard", SalesDashboardWindow, ctx=self.ctx)

    def _show_stash_viewer(self) -> None:
        """Show stash viewer window."""
        from gui_qt.windows.stash_viewer_window import StashViewerWindow
        self._window_manager.show_window("stash_viewer", StashViewerWindow, ctx=self.ctx)

    def _show_pob_characters(self) -> None:
        """Show PoB character manager window."""
        from gui_qt.windows.pob_character_window import PoBCharacterWindow

        if self._character_manager is None:
            QMessageBox.warning(
                self, "PoB Characters",
                "Character manager not initialized."
            )
            return

        # Register factory for complex initialization
        if "pob_characters" not in self._window_manager._factories:
            self._window_manager.register_factory(
                "pob_characters",
                lambda: PoBCharacterWindow(
                    self._character_manager,
                    self,
                    on_profile_selected=self._on_pob_profile_selected,
                    on_price_check=self._on_pob_price_check,
                )
            )

        window = self._window_manager.show_window("pob_characters")
        if window:
            window.activateWindow()

    def _on_pob_profile_selected(self, profile_name: str) -> None:
        """Handle PoB profile selection."""
        try:
            from core.pob_integration import UpgradeChecker
            profile = self._character_manager.get_profile(profile_name)
            if profile and profile.build:
                self._upgrade_checker = UpgradeChecker(profile.build)
                # Update the controller with new upgrade checker
                self._price_controller.set_upgrade_checker(self._upgrade_checker)
                self._set_status(f"Upgrade checking enabled for: {profile_name}")
        except Exception as e:
            self.logger.warning(f"Failed to setup upgrade checker: {e}")

    def _on_pob_price_check(self, item_text: str) -> None:
        """Handle price check request from PoB window."""
        # Populate the input text
        self.input_text.setPlainText(item_text)

        # Bring main window to front (Windows requires extra steps)
        self._bring_to_front()

        # Auto-run the price check after a brief delay to let UI update
        QTimer.singleShot(100, self._on_check_price)

    def _on_pob_profile_changed(self, profile_name: str) -> None:
        """Handle PoB profile selection change - update build stats for inspector."""
        if not profile_name or profile_name.startswith("("):
            # Invalid selection (empty or placeholder like "(No profiles)")
            self.item_inspector.set_build_stats(None)
            return

        # Set the active profile in the character manager
        if self._character_manager:
            self._character_manager.set_active_profile(profile_name)

        # Update build stats for the item inspector
        self._update_build_stats_for_inspector()

    def _bring_to_front(self) -> None:
        """Aggressively bring this window to front on Windows."""
        # Save current state
        old_state = self.windowState()

        # Method 1: Show normal first
        self.showNormal()

        # Method 2: Temporarily set always on top, then remove it
        from PyQt6.QtCore import Qt
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

        # Method 3: Standard Qt activation
        self.raise_()
        self.activateWindow()

        # Method 4: Try Windows API if available
        try:
            import ctypes
            hwnd = int(self.winId())
            # SW_RESTORE = 9, brings window to foreground
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except (AttributeError, OSError) as e:
            # AttributeError: ctypes.windll not available on non-Windows
            # OSError: Windows API call failed
            self.logger.debug(f"Windows API bring_to_front failed (expected on non-Windows): {e}")

        # Restore maximized state if needed
        if old_state & Qt.WindowState.WindowMaximized:
            self.showMaximized()

    def _show_rare_eval_config(self) -> None:
        """Show rare evaluation config window."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        data_dir = Path(__file__).parent.parent / "data"

        # Register factory for complex initialization
        if "rare_eval_config" not in self._window_manager._factories:
            self._window_manager.register_factory(
                "rare_eval_config",
                lambda: RareEvalConfigWindow(
                    data_dir,
                    self,
                    on_save=self._reload_rare_evaluator,
                )
            )

        self._window_manager.show_window("rare_eval_config")

    def _reload_rare_evaluator(self) -> None:
        """Reload the rare item evaluator."""
        self._init_rare_evaluator()
        # Update the controller with new evaluator
        self._price_controller.set_rare_evaluator(self._rare_evaluator)
        self._set_status("Rare evaluation settings reloaded")

    def _show_price_rankings(self) -> None:
        """Show price rankings window."""
        from gui_qt.windows.price_rankings_window import PriceRankingsWindow

        # Register factory for signal connection
        if "price_rankings" not in self._window_manager._factories:
            def create_price_rankings():
                window = PriceRankingsWindow(ctx=self.ctx, parent=self)
                window.priceCheckRequested.connect(self._on_ranking_price_check)
                return window

            self._window_manager.register_factory("price_rankings", create_price_rankings)

        self._window_manager.show_window("price_rankings")

    def _on_ranking_price_check(self, item_name: str) -> None:
        """Handle price check request from rankings window."""
        # Set the item text in the input field and trigger price check
        self._input_text.setText(item_name)
        self._on_price_check()

    def _show_build_comparison(self) -> None:
        """Show build comparison dialog."""
        from gui_qt.dialogs.build_comparison_dialog import BuildComparisonDialog

        # Register factory for complex initialization
        if "build_comparison" not in self._window_manager._factories:
            self._window_manager.register_factory(
                "build_comparison",
                lambda: BuildComparisonDialog(
                    self,
                    character_manager=self._character_manager,
                )
            )

        self._window_manager.show_window("build_comparison")

    def _show_loadout_selector(self) -> None:
        """Show loadout selector dialog for browsing PoB loadouts."""
        from gui_qt.dialogs.loadout_selector_dialog import LoadoutSelectorDialog

        # Register factory for signal connection
        if "loadout_selector" not in self._window_manager._factories:
            def create_loadout_selector():
                dialog = LoadoutSelectorDialog(self)
                dialog.loadout_selected.connect(self._on_loadout_selected)
                return dialog

            self._window_manager.register_factory("loadout_selector", create_loadout_selector)

        self._window_manager.show_window("loadout_selector")

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
        from gui_qt.dialogs.bis_search_dialog import BiSSearchDialog

        # Register factory for complex initialization
        if "bis_search" not in self._window_manager._factories:
            self._window_manager.register_factory(
                "bis_search",
                lambda: BiSSearchDialog(
                    self,
                    character_manager=self._character_manager,
                )
            )

        self._window_manager.show_window("bis_search")

    def _show_upgrade_finder(self) -> None:
        """Show upgrade finder dialog."""
        from gui_qt.dialogs.upgrade_finder_dialog import UpgradeFinderDialog

        # Register factory for complex initialization
        if "upgrade_finder" not in self._window_manager._factories:
            self._window_manager.register_factory(
                "upgrade_finder",
                lambda: UpgradeFinderDialog(
                    self,
                    character_manager=self._character_manager,
                )
            )

        self._window_manager.show_window("upgrade_finder")

    def _show_build_library(self) -> None:
        """Show build library dialog."""
        from gui_qt.dialogs.build_library_dialog import BuildLibraryDialog

        # Register factory for complex initialization
        if "build_library" not in self._window_manager._factories:
            self._window_manager.register_factory(
                "build_library",
                lambda: BuildLibraryDialog(
                    self,
                    character_manager=self._character_manager,
                )
            )

        self._window_manager.show_window("build_library")

    def _show_item_comparison(self) -> None:
        """Show item comparison dialog."""
        from gui_qt.dialogs.item_comparison_dialog import ItemComparisonDialog
        self._window_manager.show_window("item_comparison", ItemComparisonDialog, ctx=self.ctx)

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
                self.ctx.db.wipe()
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

        # Stop any running background workers
        if self._rankings_worker and self._rankings_worker.isRunning():
            self._rankings_worker.quit()
            self._rankings_worker.wait(2000)

        # Close all managed child windows
        closed_count = self._window_manager.close_all()
        self.logger.debug(f"Closed {closed_count} child windows")

        # Clean up AppContext resources (database, API sessions)
        if self.ctx:
            self.ctx.close()

        self.logger.info("Application closed")
        super().closeEvent(event)


def run(ctx: "AppContext") -> None:
    """Run the PyQt6 application."""
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

    window = PriceCheckerWindow(ctx)
    window.showMaximized()

    sys.exit(app.exec())
