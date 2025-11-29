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

import json
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
    APP_STYLESHEET, COLORS, Theme, get_theme_manager, get_app_stylesheet,
    THEME_CATEGORIES, THEME_DISPLAY_NAMES, POE_CURRENCY_COLORS
)
from gui_qt.menus.menu_builder import (
    MenuBuilder, MenuConfig, MenuItem, MenuSection, SubMenu, create_resources_menu
)
from gui_qt.shortcuts import get_shortcut_manager, get_shortcuts_help_text
from gui_qt.widgets.results_table import ResultsTableWidget
from gui_qt.widgets.item_inspector import ItemInspectorWidget
from gui_qt.widgets.rare_evaluation_panel import RareEvaluationPanelWidget
from gui_qt.widgets.toast_notification import ToastManager
from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget
from gui_qt.widgets.session_tabs import SessionTabWidget, SessionPanel
from gui_qt.workers import RankingsPopulationWorker
from core.build_stat_calculator import BuildStats
from core.constants import HISTORY_MAX_ENTRIES
from core.history import HistoryEntry

if TYPE_CHECKING:
    from core.app_context import AppContext


# Sample items for Dev menu (abbreviated for brevity - full versions below)
SAMPLE_ITEMS: Dict[str, List[str]] = {
    "map": [
        """Rarity: Normal
Cemetery Map
--------
Map Tier: 5
--------
Travel to this Map by using it in a personal Map Device.
""",
    ],
    "currency": [
        """Rarity: Currency
Chaos Orb
--------
Stack Size: 1/10
--------
Reforges a rare item with new random modifiers
""",
        """Rarity: Currency
Divine Orb
--------
Stack Size: 1/10
--------
Randomises the numeric values of the random modifiers on an item
""",
    ],
    "unique": [
        """Rarity: Unique
Tabula Rasa
Simple Robe
--------
Sockets: W-W-W-W-W-W
--------
Item Level: 68
--------
Item has no Level requirement
""",
        """Rarity: Unique
Headhunter
Leather Belt
--------
Requires Level 40
--------
+40 to maximum Life
+50 to Strength
+20% to Fire Resistance
When you Kill a Rare monster, you gain its Modifiers for 20 seconds
""",
    ],
    "rare": [
        """Rarity: Rare
Gale Gyre
Opal Ring
--------
Requires Level 80
--------
Item Level: 84
--------
+29% to Fire and Lightning Resistances
+16% to all Elemental Resistances
+55 to Maximum Life
+38% to Global Critical Strike Multiplier
""",
    ],
    "gem": [
        """Rarity: Gem
Vaal Grace
--------
Level: 21
Quality: +23%
--------
Casts an aura that grants evasion to you and nearby allies.
""",
    ],
    "divination": [
        """Rarity: Divination Card
The Doctor
--------
Stack Size: 1/8
--------
Headhunter
Leather Belt
""",
    ],
}


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

        # Child windows (cached references)
        self._recent_sales_window = None
        self._sales_dashboard_window = None
        self._stash_viewer_window = None
        self._pob_character_window = None
        self._rare_eval_config_window = None
        self._price_rankings_window = None
        self._build_comparison_dialog = None
        self._bis_search_dialog = None
        self._loadout_selector_dialog = None
        self._item_comparison_dialog = None

        # PoB integration
        self._character_manager = None
        self._upgrade_checker = None

        # Rare item evaluator
        self._rare_evaluator = None
        self._init_rare_evaluator()

        # Initialize PoB character manager
        self._init_character_manager()

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

        # Initialize theme from config and apply stylesheet
        self._init_theme()

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
                MenuItem("Find &BiS Item...", handler=self._show_bis_search,
                         shortcut="Ctrl+I"),
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
        from gui_qt.styles import Theme

        theme_manager = get_theme_manager()
        current = theme_manager.current_theme

        # Get all themes in order
        all_themes = list(Theme)
        try:
            current_idx = all_themes.index(current)
            next_idx = (current_idx + 1) % len(all_themes)
            next_theme = all_themes[next_idx]
        except ValueError:
            next_theme = Theme.DARK

        self._set_theme(next_theme)

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
        """Perform price check for a specific session."""
        panel = self.session_tabs.get_panel(session_index)
        if not panel:
            self._set_status("No active session")
            return

        self._check_in_progress = True
        panel.check_btn.setEnabled(False)
        self._set_status("Checking price...")

        # Run price check
        try:
            parsed = self.ctx.parser.parse(item_text)
            if not parsed:
                self._set_status("Could not parse item text")
                self._check_in_progress = False
                panel.check_btn.setEnabled(True)
                return

            # Update item inspector
            panel.item_inspector.set_item(parsed)

            # Clear the paste window - item is now shown in inspector
            panel.input_text.clear()

            # Get price results (pass item text, not parsed object)
            results = self.ctx.price_service.check_item(item_text)

            # Convert to display format (results are dicts from check_item)
            all_results = []
            for result in results:
                # Handle explanation - could be dict or object
                explanation = result.get("explanation")
                if explanation:
                    if isinstance(explanation, dict):
                        explanation_str = json.dumps(explanation)
                    elif hasattr(explanation, "__dict__"):
                        explanation_str = json.dumps(explanation.__dict__)
                    else:
                        explanation_str = str(explanation)
                else:
                    explanation_str = ""

                # Convert numeric values safely
                try:
                    chaos_val = float(result.get("chaos_value") or 0)
                except (ValueError, TypeError):
                    chaos_val = 0.0
                try:
                    divine_val = float(result.get("divine_value") or 0)
                except (ValueError, TypeError):
                    divine_val = 0.0
                try:
                    listing_count = int(result.get("listing_count") or 0)
                except (ValueError, TypeError):
                    listing_count = 0

                row = {
                    "item_name": result.get("item_name") or parsed.name or "",
                    "variant": result.get("variant") or "",
                    "links": result.get("links") or "",
                    "chaos_value": chaos_val,
                    "divine_value": divine_val,
                    "listing_count": listing_count,
                    "source": result.get("source") or "",
                    "upgrade": "",
                    "price_explanation": explanation_str,
                    "_item": parsed,  # Store for tooltip preview
                }

                # Check for upgrade potential
                if self._upgrade_checker and hasattr(parsed, 'slot'):
                    is_upgrade = self._upgrade_checker.is_upgrade(parsed)
                    if is_upgrade:
                        row["upgrade"] = "Yes"

                all_results.append(row)

            # Update session panel with results (handles table and filters)
            panel.set_results(all_results)
            self._update_summary()

            # Evaluate rare items
            if parsed.rarity == "Rare" and self._rare_evaluator:
                try:
                    evaluation = self._rare_evaluator.evaluate(parsed)
                    panel.rare_eval_panel.set_evaluation(evaluation)
                    panel.rare_eval_panel.setVisible(True)
                except Exception as e:
                    self.logger.warning(f"Rare evaluation failed: {e}")
                    panel.rare_eval_panel.setVisible(False)
            else:
                panel.rare_eval_panel.setVisible(False)

            # Add to history (store full item text for re-checking)
            self._history.append(
                HistoryEntry.from_price_check(item_text, parsed, results)
            )

            self._set_status(f"Found {len(results)} price result(s)")
            # Show toast for notable results
            if results:
                best_price = max((r.get("chaos_value", 0) or 0) for r in results)
                if best_price >= 100:
                    self._toast_manager.success(f"High value item: {best_price:.0f}c")
                elif best_price >= 10:
                    self._toast_manager.info(f"Found {len(results)} result(s)")

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

    def _init_theme(self) -> None:
        """Initialize theme and accent color from config and apply stylesheet."""
        theme_manager = get_theme_manager()

        # Load theme from config
        saved_theme = self.ctx.config.theme if hasattr(self.ctx, 'config') else "dark"
        try:
            theme = Theme(saved_theme)
        except ValueError:
            theme = Theme.DARK

        # Set theme (this also updates colors)
        theme_manager.set_theme(theme)

        # Load accent color from config
        saved_accent = self.ctx.config.accent_color if hasattr(self.ctx, 'config') else None
        if saved_accent is not None:
            theme_manager.set_accent_color(saved_accent)

        # Apply stylesheet
        self.setStyleSheet(theme_manager.get_stylesheet())

        # Update menu checkmarks
        self._update_theme_menu_checks(theme)
        self._update_accent_menu_checks(saved_accent)

        # Register callback for future theme changes
        theme_manager.register_callback(self._on_theme_changed)

    def _set_theme(self, theme: Theme) -> None:
        """Set the application theme."""
        theme_manager = get_theme_manager()
        theme_manager.set_theme(theme)

        # Save to config
        if hasattr(self.ctx, 'config'):
            self.ctx.config.theme = theme.value

        # Apply stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(theme_manager.get_stylesheet())
        self.setStyleSheet(theme_manager.get_stylesheet())

        # Update menu checkmarks
        self._update_theme_menu_checks(theme)

        display_name = THEME_DISPLAY_NAMES.get(theme, theme.value)
        self._set_status(f"Theme changed to: {display_name}")

    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        theme_manager = get_theme_manager()
        new_theme = theme_manager.toggle_theme()

        # Save to config
        if hasattr(self.ctx, 'config'):
            self.ctx.config.theme = new_theme.value

        # Apply stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(theme_manager.get_stylesheet())
        self.setStyleSheet(theme_manager.get_stylesheet())

        # Update menu checkmarks
        self._update_theme_menu_checks(new_theme)

        display_name = THEME_DISPLAY_NAMES.get(new_theme, new_theme.value)
        self._set_status(f"Theme toggled to: {display_name}")

    def _update_theme_menu_checks(self, current_theme: Theme) -> None:
        """Update the checkmarks in the theme menu."""
        for theme, action in self._theme_actions.items():
            action.setChecked(theme == current_theme)

    def _set_accent_color(self, accent_key: Optional[str]) -> None:
        """Set the application accent color."""
        theme_manager = get_theme_manager()
        theme_manager.set_accent_color(accent_key)

        # Save to config
        if hasattr(self.ctx, 'config'):
            self.ctx.config.accent_color = accent_key

        # Apply stylesheet (accent affects the stylesheet)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(theme_manager.get_stylesheet())
        self.setStyleSheet(theme_manager.get_stylesheet())

        # Update menu checkmarks
        self._update_accent_menu_checks(accent_key)

        # Get display name
        if accent_key is None:
            display_name = "Theme Default"
        else:
            display_name = POE_CURRENCY_COLORS.get(accent_key, {}).get("name", accent_key)
        self._set_status(f"Accent color changed to: {display_name}")

    def _update_accent_menu_checks(self, current_accent: Optional[str]) -> None:
        """Update the checkmarks in the accent menu."""
        for accent_key, action in self._accent_actions.items():
            action.setChecked(accent_key == current_accent)

    def _on_theme_changed(self, theme: Theme) -> None:
        """Handle theme change callback from ThemeManager."""
        # Update stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_manager().get_stylesheet())
        self.setStyleSheet(get_theme_manager().get_stylesheet())

        # Update menu checkmarks
        self._update_theme_menu_checks(theme)

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

        if self._recent_sales_window is None or not self._recent_sales_window.isVisible():
            self._recent_sales_window = RecentSalesWindow(self.ctx, self)

        self._recent_sales_window.show()
        self._recent_sales_window.raise_()

    def _show_sales_dashboard(self) -> None:
        """Show sales dashboard window."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        if self._sales_dashboard_window is None or not self._sales_dashboard_window.isVisible():
            self._sales_dashboard_window = SalesDashboardWindow(self.ctx, self)

        self._sales_dashboard_window.show()
        self._sales_dashboard_window.raise_()

    def _show_stash_viewer(self) -> None:
        """Show stash viewer window."""
        from gui_qt.windows.stash_viewer_window import StashViewerWindow

        if self._stash_viewer_window is None or not self._stash_viewer_window.isVisible():
            self._stash_viewer_window = StashViewerWindow(self.ctx, self)

        self._stash_viewer_window.show()
        self._stash_viewer_window.raise_()

    def _show_pob_characters(self) -> None:
        """Show PoB character manager window."""
        from gui_qt.windows.pob_character_window import PoBCharacterWindow

        if self._character_manager is None:
            QMessageBox.warning(
                self, "PoB Characters",
                "Character manager not initialized."
            )
            return

        if self._pob_character_window is None or not self._pob_character_window.isVisible():
            self._pob_character_window = PoBCharacterWindow(
                self._character_manager,
                self,
                on_profile_selected=self._on_pob_profile_selected,
                on_price_check=self._on_pob_price_check,
            )

        self._pob_character_window.show()
        self._pob_character_window.raise_()
        self._pob_character_window.activateWindow()

    def _on_pob_profile_selected(self, profile_name: str) -> None:
        """Handle PoB profile selection."""
        try:
            from core.pob_integration import UpgradeChecker
            profile = self._character_manager.get_profile(profile_name)
            if profile and profile.build:
                self._upgrade_checker = UpgradeChecker(profile.build)
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

        if self._rare_eval_config_window is None or not self._rare_eval_config_window.isVisible():
            self._rare_eval_config_window = RareEvalConfigWindow(
                data_dir,
                self,
                on_save=self._reload_rare_evaluator,
            )

        self._rare_eval_config_window.show()
        self._rare_eval_config_window.raise_()

    def _reload_rare_evaluator(self) -> None:
        """Reload the rare item evaluator."""
        self._init_rare_evaluator()
        self._set_status("Rare evaluation settings reloaded")

    def _show_price_rankings(self) -> None:
        """Show price rankings window."""
        from gui_qt.windows.price_rankings_window import PriceRankingsWindow

        if self._price_rankings_window is None or not self._price_rankings_window.isVisible():
            self._price_rankings_window = PriceRankingsWindow(self.ctx, self)

        self._price_rankings_window.show()
        self._price_rankings_window.raise_()

    def _show_build_comparison(self) -> None:
        """Show build comparison dialog."""
        from gui_qt.dialogs.build_comparison_dialog import BuildComparisonDialog

        if self._build_comparison_dialog is None or not self._build_comparison_dialog.isVisible():
            self._build_comparison_dialog = BuildComparisonDialog(
                self,
                character_manager=self._character_manager,
            )

        self._build_comparison_dialog.show()
        self._build_comparison_dialog.raise_()

    def _show_loadout_selector(self) -> None:
        """Show loadout selector dialog for browsing PoB loadouts."""
        from gui_qt.dialogs.loadout_selector_dialog import LoadoutSelectorDialog

        if self._loadout_selector_dialog is None or not self._loadout_selector_dialog.isVisible():
            self._loadout_selector_dialog = LoadoutSelectorDialog(self)
            self._loadout_selector_dialog.loadout_selected.connect(self._on_loadout_selected)

        self._loadout_selector_dialog.show()
        self._loadout_selector_dialog.raise_()

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

        if self._bis_search_dialog is None or not self._bis_search_dialog.isVisible():
            self._bis_search_dialog = BiSSearchDialog(
                self,
                character_manager=self._character_manager,
            )

        self._bis_search_dialog.show()
        self._bis_search_dialog.raise_()

    def _show_item_comparison(self) -> None:
        """Show item comparison dialog."""
        from gui_qt.dialogs.item_comparison_dialog import ItemComparisonDialog

        if self._item_comparison_dialog is None or not self._item_comparison_dialog.isVisible():
            self._item_comparison_dialog = ItemComparisonDialog(self, self.ctx)

        self._item_comparison_dialog.show()
        self._item_comparison_dialog.raise_()

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
        """Show keyboard shortcuts in a scrollable dialog."""
        text = get_shortcuts_help_text()

        # Use a larger dialog for the full shortcuts list
        dialog = QDialog(self)
        dialog.setWindowTitle("Keyboard Shortcuts")
        dialog.setMinimumSize(450, 500)

        layout = QVBoxLayout(dialog)

        from PyQt6.QtWidgets import QTextEdit
        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setPlainText(text)
        text_widget.setStyleSheet(
            f"background-color: {COLORS['background']}; "
            f"color: {COLORS['text']}; "
            f"font-family: monospace; "
            f"font-size: 12px;"
        )
        layout.addWidget(text_widget)

        # Hint about command palette
        hint_label = QLabel("Tip: Press Ctrl+Shift+P to open Command Palette for quick access to all actions")
        hint_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; padding: 8px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def _show_tips(self) -> None:
        """Show usage tips."""
        text = """Usage Tips:

1. Copy items from the game using Ctrl+C while hovering over them.

2. Paste the item text into the input box and click Check Price.

3. Right-click results for more options like recording sales.

4. Use the filter to narrow down results.

5. Import PoB builds to check for upgrade opportunities.

6. Configure rare item evaluation weights for your build.
"""
        QMessageBox.information(self, "Usage Tips", text)

    def _show_about(self) -> None:
        """Show about dialog with logo."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt
        from gui_qt.styles import get_app_banner_pixmap, apply_window_icon

        dialog = QDialog(self)
        dialog.setWindowTitle("About PoE Price Checker")
        dialog.setFixedSize(400, 400)
        apply_window_icon(dialog)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)

        # Logo
        banner = get_app_banner_pixmap(180)
        if banner:
            logo_label = QLabel()
            logo_label.setPixmap(banner)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

        # Title
        title_label = QLabel("<h2 style='color: #3498db;'>PoE Price Checker</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Version
        version_label = QLabel("Version 1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(version_label)

        # Description
        desc_label = QLabel(
            "A tool for checking Path of Exile item prices.\n\n"
            "Features:\n"
            "• Multi-source pricing (poe.ninja, poe.watch, Trade API)\n"
            "• PoB build integration for upgrade checking\n"
            "• BiS item search with affix tier analysis\n"
            "• Rare item evaluation system"
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def closeEvent(self, event) -> None:
        """Handle window close - clean up application resources."""
        self.logger.info("Closing application...")

        # Stop any running background workers
        if self._rankings_worker and self._rankings_worker.isRunning():
            self._rankings_worker.quit()
            self._rankings_worker.wait(2000)

        # Close child windows
        for win in [
            self._recent_sales_window,
            self._sales_dashboard_window,
            self._stash_viewer_window,
            self._pob_character_window,
            self._rare_eval_config_window,
            self._price_rankings_window,
        ]:
            if win:
                win.close()

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
