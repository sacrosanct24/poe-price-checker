"""
Menu bar mixin for declarative menu creation.

Extracts menu bar creation methods from main_window.py
to reduce coupling and improve maintainability.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenuBar

if TYPE_CHECKING:
    from gui_qt.main_window import PriceCheckerWindow


class MenuBarMixin:
    """
    Mixin providing menu bar creation functionality.

    This mixin expects the following attributes on self:
    - logger: Logger instance
    - _view_menu_controller: ViewMenuController (set by this mixin)
    - _theme_actions, _accent_actions, _column_actions: Action dicts (set by this mixin)
    - Various action methods like _open_log_file, _show_settings, etc.
    """

    def _create_menu_bar(self: "PriceCheckerWindow") -> None:
        """Create the application menu bar using declarative MenuBuilder."""
        from gui_qt.menus.menu_builder import (
            MenuBuilder, MenuConfig, MenuItem, MenuSection, create_resources_menu
        )

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
                    MenuItem("Export &Data...", handler=self._show_export_dialog,
                             shortcut="Ctrl+Shift+E"),
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
                MenuItem("My &Builds...", handler=self._show_build_manager,
                         shortcut="Ctrl+B"),
                MenuItem("&Compare Build Trees...", handler=self._show_build_comparison),
                MenuSection([
                    MenuItem("&Item Planning Hub...", handler=self._show_item_planning_hub,
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

    def _create_view_menu(self: "PriceCheckerWindow", menubar: QMenuBar) -> None:
        """Create View menu with dynamic theme/accent/column submenus."""
        from gui_qt.controllers import ViewMenuController

        self._view_menu_controller = ViewMenuController(
            on_history=self._show_history,
            on_stash_viewer=self._show_stash_viewer,
            on_set_theme=self._set_theme,
            on_toggle_theme=self._toggle_theme,
            on_set_accent=self._set_accent_color,
            on_toggle_column=self._toggle_column,
            parent=self,
            logger=self.logger,
            on_price_alerts=self._show_price_alerts_dialog,
        )
        self._theme_actions, self._accent_actions, self._column_actions = \
            self._view_menu_controller.create_view_menu(menubar)

    def _create_dev_menu(self: "PriceCheckerWindow", menubar: QMenuBar) -> None:
        """Create Dev menu with dynamic sample items."""
        from gui_qt.sample_items import SAMPLE_ITEMS

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
