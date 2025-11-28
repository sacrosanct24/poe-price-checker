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

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
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

from gui_qt.styles import APP_STYLESHEET, COLORS
from gui_qt.widgets.results_table import ResultsTableWidget
from gui_qt.widgets.item_inspector import ItemInspectorWidget
from gui_qt.widgets.rare_evaluation_panel import RareEvaluationPanelWidget
from core.build_stat_calculator import BuildStats

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


class PriceCheckWorker(QObject):
    """Worker for running price checks in a background thread."""

    finished = pyqtSignal(object)  # Emits result or exception
    error = pyqtSignal(str)

    def __init__(self, ctx: "AppContext", item_text: str):
        super().__init__()
        self.ctx = ctx
        self.item_text = item_text

    def run(self):
        """Run the price check."""
        try:
            # Parse item
            parsed = self.ctx.parser.parse(self.item_text)
            if not parsed:
                self.error.emit("Could not parse item text")
                return

            # Get price (pass item text, not parsed object)
            results = self.ctx.price_service.check_item(self.item_text)
            self.finished.emit((parsed, results))
        except Exception as e:
            self.error.emit(str(e))


class RankingsPopulationWorker(QThread):
    """Background worker to populate price rankings on startup."""

    finished = pyqtSignal(int)  # Emits number of categories populated
    progress = pyqtSignal(str)  # Emits status message
    error = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._league: Optional[str] = None

    def run(self):
        """Check and populate rankings if needed."""
        try:
            from core.price_rankings import (
                PriceRankingCache,
                Top20Calculator,
                PriceRankingHistory,
            )
            from data_sources.pricing.poe_ninja import PoeNinjaAPI

            self.progress.emit("Checking price rankings cache...")

            # Detect current league
            api = PoeNinjaAPI()
            league = api.detect_current_league()
            self._league = league

            # Check if cache is valid
            cache = PriceRankingCache(league=league)

            if cache.is_cache_valid():
                age = cache.get_cache_age_days()
                self.progress.emit(f"Rankings cache valid ({age:.1f} days old)")
                self.finished.emit(0)
                return

            # Need to populate
            self.progress.emit(f"Fetching Top 20 rankings for {league}...")

            calculator = Top20Calculator(cache, poe_ninja_api=api)
            rankings = calculator.refresh_all(force=False)

            # Save to history database
            self.progress.emit("Saving rankings to database...")
            history = PriceRankingHistory()
            history.save_all_snapshots(rankings, league)
            history.close()

            self.progress.emit(f"Populated {len(rankings)} categories")
            self.finished.emit(len(rankings))

        except Exception as e:
            logging.getLogger(__name__).exception("Failed to populate rankings")
            self.error.emit(str(e))


class PriceCheckerWindow(QMainWindow):
    """Main window for the PoE Price Checker application."""

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ctx = ctx
        self.logger = logging.getLogger(__name__)

        # State
        self._all_results: List[Dict[str, Any]] = []
        self._check_in_progress = False
        # Bounded history to prevent unbounded memory growth (keeps last 100 checks)
        self._history: Deque[Dict[str, Any]] = deque(maxlen=100)

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

        # Apply stylesheet
        self.setStyleSheet(APP_STYLESHEET)

        self._set_status("Ready")

        # Start background rankings population check
        self._start_rankings_population()

        # Initialize build stats for item inspector from active PoB profile
        self._update_build_stats_for_inspector()

    def _start_rankings_population(self) -> None:
        """Start background task to populate price rankings if needed."""
        try:
            self._rankings_worker = RankingsPopulationWorker(self)
            self._rankings_worker.progress.connect(self._on_rankings_progress)
            self._rankings_worker.finished.connect(self._on_rankings_finished)
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

    def _on_rankings_error(self, error: str) -> None:
        """Handle rankings population error."""
        self.logger.warning(f"Rankings population failed: {error}")
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
            else:
                self.logger.info(f"No build stats available")
                self.item_inspector.set_build_stats(None)
        except Exception as e:
            self.logger.warning(f"Failed to update build stats: {e}")

    # -------------------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_log_action = QAction("Open &Log File", self)
        open_log_action.triggered.connect(self._open_log_file)
        file_menu.addAction(open_log_action)

        open_config_action = QAction("Open &Config Folder", self)
        open_config_action.triggered.connect(self._open_config_folder)
        file_menu.addAction(open_config_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Results (TSV)...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_results)
        file_menu.addAction(export_action)

        copy_all_action = QAction("Copy &All as TSV", self)
        copy_all_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_all_action.triggered.connect(self._copy_all_as_tsv)
        file_menu.addAction(copy_all_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Build menu (PoB and build-related features)
        build_menu = menubar.addMenu("&Build")

        pob_action = QAction("&PoB Characters", self)
        pob_action.setShortcut(QKeySequence("Ctrl+B"))
        pob_action.triggered.connect(self._show_pob_characters)
        build_menu.addAction(pob_action)

        compare_build_action = QAction("&Compare Build Trees...", self)
        compare_build_action.triggered.connect(self._show_build_comparison)
        build_menu.addAction(compare_build_action)

        loadout_action = QAction("Browse &Loadouts...", self)
        loadout_action.triggered.connect(self._show_loadout_selector)
        build_menu.addAction(loadout_action)

        bis_search_action = QAction("Find &BiS Item...", self)
        bis_search_action.setShortcut(QKeySequence("Ctrl+I"))
        bis_search_action.triggered.connect(self._show_bis_search)
        build_menu.addAction(bis_search_action)

        build_menu.addSeparator()

        rare_eval_action = QAction("Rare Item &Settings...", self)
        rare_eval_action.triggered.connect(self._show_rare_eval_config)
        build_menu.addAction(rare_eval_action)

        # Prices menu (price and sales related)
        prices_menu = menubar.addMenu("&Prices")

        price_rankings_action = QAction("&Top 20 Rankings", self)
        price_rankings_action.triggered.connect(self._show_price_rankings)
        prices_menu.addAction(price_rankings_action)

        prices_menu.addSeparator()

        recent_sales_action = QAction("&Recent Sales", self)
        recent_sales_action.triggered.connect(self._show_recent_sales)
        prices_menu.addAction(recent_sales_action)

        dashboard_action = QAction("Sales &Dashboard", self)
        dashboard_action.triggered.connect(self._show_sales_dashboard)
        prices_menu.addAction(dashboard_action)

        prices_menu.addSeparator()

        sources_action = QAction("Data &Sources Info", self)
        sources_action.triggered.connect(self._show_data_sources)
        prices_menu.addAction(sources_action)

        # View menu (display options)
        view_menu = menubar.addMenu("&View")

        history_action = QAction("Session &History", self)
        history_action.triggered.connect(self._show_history)
        view_menu.addAction(history_action)

        stash_action = QAction("&Stash Viewer", self)
        stash_action.triggered.connect(self._show_stash_viewer)
        view_menu.addAction(stash_action)

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

        # Resources menu
        resources_menu = menubar.addMenu("&Resources")
        self._create_resources_menu(resources_menu)

        # Dev menu
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

        # Help menu
        help_menu = menubar.addMenu("&Help")

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        tips_action = QAction("Usage &Tips", self)
        tips_action.triggered.connect(self._show_tips)
        help_menu.addAction(tips_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_resources_menu(self, menu: QMenu) -> None:
        """Create the Resources menu with PoE1/PoE2 submenus."""
        import webbrowser

        def open_url(url: str):
            """Open URL in default browser."""
            def handler():
                webbrowser.open(url)
            return handler

        # PoE1 submenu
        poe1_menu = menu.addMenu("Path of Exile &1")

        # PoE1 - Official
        poe1_official = poe1_menu.addMenu("Official")
        action = QAction("Official Website", self)
        action.triggered.connect(open_url("https://www.pathofexile.com/"))
        poe1_official.addAction(action)
        action = QAction("Official Trade", self)
        action.triggered.connect(open_url("https://www.pathofexile.com/trade/search/Keepers"))
        poe1_official.addAction(action)
        action = QAction("Passive Skill Tree", self)
        action.triggered.connect(open_url("https://www.pathofexile.com/passive-skill-tree"))
        poe1_official.addAction(action)

        # PoE1 - Wiki & Database
        poe1_wiki = poe1_menu.addMenu("Wiki && Database")
        action = QAction("Community Wiki", self)
        action.triggered.connect(open_url("https://www.poewiki.net/wiki/Path_of_Exile_Wiki"))
        poe1_wiki.addAction(action)
        action = QAction("PoE DB", self)
        action.triggered.connect(open_url("https://poedb.tw/us/"))
        poe1_wiki.addAction(action)

        # PoE1 - Build Planning
        poe1_planning = poe1_menu.addMenu("Build Planning")
        action = QAction("Path of Building (Desktop)", self)
        action.triggered.connect(open_url("https://pathofbuilding.community/"))
        poe1_planning.addAction(action)
        action = QAction("Path of Building (Web)", self)
        action.triggered.connect(open_url("https://pob.cool/"))
        poe1_planning.addAction(action)
        action = QAction("PoE Planner", self)
        action.triggered.connect(open_url("https://poeplanner.com/"))
        poe1_planning.addAction(action)
        action = QAction("Path of Pathing (Atlas)", self)
        action.triggered.connect(open_url("https://www.pathofpathing.com/"))
        poe1_planning.addAction(action)

        # PoE1 - Build Guides
        poe1_guides = poe1_menu.addMenu("Build Guides")
        action = QAction("Maxroll", self)
        action.triggered.connect(open_url("https://maxroll.gg/poe"))
        poe1_guides.addAction(action)
        action = QAction("Mobalytics", self)
        action.triggered.connect(open_url("https://mobalytics.gg/poe"))
        poe1_guides.addAction(action)
        action = QAction("PoE Builds", self)
        action.triggered.connect(open_url("https://www.poebuilds.cc/"))
        poe1_guides.addAction(action)
        action = QAction("Pohx (Righteous Fire)", self)
        action.triggered.connect(open_url("https://pohx.net/"))
        poe1_guides.addAction(action)

        # PoE1 - Economy & Trading
        poe1_economy = poe1_menu.addMenu("Economy && Trading")
        action = QAction("Wealthy Exile", self)
        action.triggered.connect(open_url("https://wealthyexile.com/"))
        poe1_economy.addAction(action)
        action = QAction("Map Trade", self)
        action.triggered.connect(open_url("https://poemap.trade/"))
        poe1_economy.addAction(action)
        action = QAction("poe.how Economy Guide", self)
        action.triggered.connect(open_url("https://poe.how/economy"))
        poe1_economy.addAction(action)

        # PoE1 - Tools
        poe1_tools = poe1_menu.addMenu("Tools")
        action = QAction("FilterBlade (Loot Filters)", self)
        action.triggered.connect(open_url("https://www.filterblade.xyz/?game=Poe1"))
        poe1_tools.addAction(action)

        # PoE1 - Community
        poe1_menu.addSeparator()
        action = QAction("Reddit", self)
        action.triggered.connect(open_url("https://www.reddit.com/r/pathofexile/"))
        poe1_menu.addAction(action)

        # PoE2 submenu
        poe2_menu = menu.addMenu("Path of Exile &2")

        # PoE2 - Official
        poe2_official = poe2_menu.addMenu("Official")
        action = QAction("Official Website", self)
        action.triggered.connect(open_url("https://pathofexile2.com/"))
        poe2_official.addAction(action)
        action = QAction("Official Trade", self)
        action.triggered.connect(open_url("https://www.pathofexile.com/trade2/search/poe2/Rise%20of%20the%20Abyssal"))
        poe2_official.addAction(action)

        # PoE2 - Wiki & Database
        poe2_wiki = poe2_menu.addMenu("Wiki && Database")
        action = QAction("Community Wiki", self)
        action.triggered.connect(open_url("https://www.poe2wiki.net/wiki/Path_of_Exile_2_Wiki"))
        poe2_wiki.addAction(action)
        action = QAction("PoE2 DB", self)
        action.triggered.connect(open_url("https://poe2db.tw/"))
        poe2_wiki.addAction(action)

        # PoE2 - Build Planning
        poe2_planning = poe2_menu.addMenu("Build Planning")
        action = QAction("Path of Building PoE2 (GitHub)", self)
        action.triggered.connect(open_url("https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2"))
        poe2_planning.addAction(action)

        # PoE2 - Build Guides
        poe2_guides = poe2_menu.addMenu("Build Guides")
        action = QAction("Maxroll", self)
        action.triggered.connect(open_url("https://maxroll.gg/poe2"))
        poe2_guides.addAction(action)
        action = QAction("Mobalytics", self)
        action.triggered.connect(open_url("https://mobalytics.gg/poe-2"))
        poe2_guides.addAction(action)

        # PoE2 - Tools
        poe2_tools = poe2_menu.addMenu("Tools")
        action = QAction("FilterBlade (Loot Filters)", self)
        action.triggered.connect(open_url("https://www.filterblade.xyz/?game=Poe2"))
        poe2_tools.addAction(action)

        # PoE2 - Community
        poe2_menu.addSeparator()
        action = QAction("Reddit", self)
        action.triggered.connect(open_url("https://www.reddit.com/r/PathOfExile2/"))
        poe2_menu.addAction(action)
        action = QAction("Reddit Builds", self)
        action.triggered.connect(open_url("https://www.reddit.com/r/pathofexile2builds/"))
        poe2_menu.addAction(action)

        # Separator before shared resources
        menu.addSeparator()

        # Shared resources (both games)
        action = QAction("poe.ninja (Economy)", self)
        action.triggered.connect(open_url("https://poe.ninja/"))
        menu.addAction(action)

        action = QAction("PoB Archives (Meta Builds)", self)
        action.triggered.connect(open_url("https://pobarchives.com/"))
        menu.addAction(action)

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

        # ========== LEFT SIDE: PoB Panel ==========
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

        pob_group.setMinimumWidth(250)
        pob_group.setMaximumWidth(400)
        main_splitter.addWidget(pob_group)

        # ========== RIGHT SIDE: Price Check Panel ==========
        right_panel = QWidget()
        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Top area: input + item inspector (horizontal split)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Input area
        input_group = QGroupBox("Item Input")
        input_layout = QVBoxLayout(input_group)

        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText(
            "Paste item text here (Ctrl+C from game, then Ctrl+V here)...\n\n"
            "Or select an item from PoB Equipment panel on the left."
        )
        self.input_text.setMinimumHeight(100)
        input_layout.addWidget(self.input_text)

        # Button row
        btn_layout = QHBoxLayout()

        self.check_btn = QPushButton("Check Price")
        self.check_btn.clicked.connect(self._on_check_price)
        self.check_btn.setMinimumWidth(120)
        btn_layout.addWidget(self.check_btn)

        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)

        top_splitter.addWidget(input_group)

        # Right: Item inspector
        inspector_group = QGroupBox("Item Inspector")
        inspector_layout = QVBoxLayout(inspector_group)
        self.item_inspector = ItemInspectorWidget()
        inspector_layout.addWidget(self.item_inspector)
        top_splitter.addWidget(inspector_group)

        # Give Item Inspector more space (it shows build-effective values)
        top_splitter.setSizes([300, 500])
        layout.addWidget(top_splitter)

        # Middle: Results area
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        # Filter row
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Type to filter results...")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_input)

        filter_layout.addWidget(QLabel("Source:"))
        self.source_filter = QComboBox()
        self.source_filter.addItem("All sources")
        self.source_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.source_filter)

        results_layout.addLayout(filter_layout)

        # Results table
        self.results_table = ResultsTableWidget()
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_results_context_menu)
        self.results_table.row_selected.connect(self._on_result_selected)
        results_layout.addWidget(self.results_table)

        layout.addWidget(results_group, stretch=1)

        # Bottom: Rare evaluation panel (hidden by default)
        self.rare_eval_panel = RareEvaluationPanelWidget()
        self.rare_eval_panel.setVisible(False)
        layout.addWidget(self.rare_eval_panel)

        # Add right panel to main splitter
        main_splitter.addWidget(right_panel)

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

    def _set_status(self, message: str) -> None:
        """Set the status bar message."""
        self.status_bar.showMessage(message)

    def _update_summary(self) -> None:
        """Update the summary label."""
        count = len(self._all_results)
        if count == 0:
            self.summary_label.setText("No results")
        else:
            # Ensure chaos_value is numeric
            total_chaos = 0.0
            for r in self._all_results:
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
        """Setup keyboard shortcuts."""
        # Ctrl+Enter to check price
        check_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        check_shortcut.activated.connect(self._on_check_price)

        # Escape to clear input
        clear_shortcut = QShortcut(QKeySequence("Escape"), self)
        clear_shortcut.activated.connect(self._clear_input)

        # Ctrl+V to paste and check
        paste_check_shortcut = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        paste_check_shortcut.activated.connect(self._paste_and_check)

    # -------------------------------------------------------------------------
    # Price Checking
    # -------------------------------------------------------------------------

    def _on_check_price(self) -> None:
        """Handle Check Price button click."""
        if self._check_in_progress:
            return

        item_text = self.input_text.toPlainText().strip()
        if not item_text:
            self._set_status("No item text to check")
            return

        self._check_in_progress = True
        self.check_btn.setEnabled(False)
        self._set_status("Checking price...")

        # Run price check
        try:
            parsed = self.ctx.parser.parse(item_text)
            if not parsed:
                self._set_status("Could not parse item text")
                self._check_in_progress = False
                self.check_btn.setEnabled(True)
                return

            # Update item inspector
            self.item_inspector.set_item(parsed)

            # Clear the paste window - item is now shown in inspector
            self.input_text.clear()

            # Get price results (pass item text, not parsed object)
            results = self.ctx.price_service.check_item(item_text)

            # Convert to display format (results are dicts from check_item)
            self._all_results = []
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
                }

                # Check for upgrade potential
                if self._upgrade_checker and hasattr(parsed, 'slot'):
                    is_upgrade = self._upgrade_checker.is_upgrade(parsed)
                    if is_upgrade:
                        row["upgrade"] = "Yes"

                self._all_results.append(row)

            # Update display
            self.results_table.set_data(self._all_results)
            self._update_summary()

            # Update sources filter
            sources = set(r.get("source", "") for r in self._all_results)
            self.source_filter.clear()
            self.source_filter.addItem("All sources")
            for source in sorted(sources):
                if source:
                    self.source_filter.addItem(source)

            # Evaluate rare items
            if parsed.rarity == "Rare" and self._rare_evaluator:
                try:
                    evaluation = self._rare_evaluator.evaluate(parsed)
                    self.rare_eval_panel.set_evaluation(evaluation)
                    self.rare_eval_panel.setVisible(True)
                except Exception as e:
                    self.logger.warning(f"Rare evaluation failed: {e}")
                    self.rare_eval_panel.setVisible(False)
            else:
                self.rare_eval_panel.setVisible(False)

            # Add to history
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "item": parsed.name or item_text[:50],
                "results_count": len(results),
            })

            self._set_status(f"Found {len(results)} price result(s)")

        except Exception as e:
            self.logger.exception("Price check failed")
            self._set_status(f"Error: {e}")
        finally:
            self._check_in_progress = False
            self.check_btn.setEnabled(True)

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
    # Results Filtering
    # -------------------------------------------------------------------------

    def _apply_filter(self) -> None:
        """Apply text and source filters to results."""
        text_filter = self.filter_input.text().lower()
        source_filter = self.source_filter.currentText()

        filtered = []
        for row in self._all_results:
            # Source filter
            if source_filter != "All sources":
                if row.get("source", "") != source_filter:
                    continue

            # Text filter
            if text_filter:
                searchable = " ".join(str(v).lower() for v in row.values())
                if text_filter not in searchable:
                    continue

            filtered.append(row)

        self.results_table.set_data(filtered)

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
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to record sale: {e}")

    # -------------------------------------------------------------------------
    # Column Visibility
    # -------------------------------------------------------------------------

    def _toggle_column(self, column: str, visible: bool) -> None:
        """Toggle column visibility."""
        self.results_table.set_column_visible(column, visible)

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
        if not self._all_results:
            QMessageBox.information(self, "Export", "No results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "", "TSV Files (*.tsv);;All Files (*)"
        )

        if path:
            try:
                self.results_table.export_tsv(path)
                self._set_status(f"Exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def _copy_all_as_tsv(self) -> None:
        """Copy all results as TSV."""
        tsv = self.results_table.to_tsv(include_header=True)
        QApplication.clipboard().setText(tsv)
        self._set_status("All results copied as TSV")

    def _show_history(self) -> None:
        """Show session history dialog."""
        if not self._history:
            QMessageBox.information(self, "Session History", "No items checked this session.")
            return

        text = "Session History:\n\n"
        for entry in self._history[-20:]:  # Last 20
            text += f"{entry['timestamp']}: {entry['item']} ({entry['results_count']} results)\n"

        QMessageBox.information(self, "Session History", text)

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
        """Show keyboard shortcuts."""
        text = """Keyboard Shortcuts:

Ctrl+Enter - Check price
Ctrl+Shift+V - Paste and check
Ctrl+B - Open PoB Characters
Ctrl+I - Find BiS Item
Ctrl+E - Export results
Ctrl+Shift+C - Copy all as TSV
Escape - Clear input
Alt+F4 - Exit
"""
        QMessageBox.information(self, "Keyboard Shortcuts", text)

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
