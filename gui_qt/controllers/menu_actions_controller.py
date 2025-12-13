"""
Menu actions controller for handling menu bar action callbacks.

Extracts menu action handlers from main_window.py to reduce coupling
and improve testability.
"""
from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMessageBox,
    QWidget,
)

if TYPE_CHECKING:
    from core.app_context import AppContext
    from gui_qt.services.window_manager import WindowManager
    from gui_qt.controllers.navigation_controller import NavigationController
    from gui_qt.controllers.loot_tracking_controller import LootTrackingController
    from gui_qt.services.history_manager import HistoryManager


logger = logging.getLogger(__name__)


class MenuActionsController:
    """
    Controller for menu bar action handlers.

    Encapsulates file, view, economy, build, dev, and help menu actions.
    """

    def __init__(
        self,
        ctx: "AppContext",
        parent: QWidget,
        window_manager: "WindowManager",
        nav_controller: "NavigationController",
        history_manager: "HistoryManager",
        on_status: Callable[[str], None],
        get_input_text: Callable[[], str],
        set_input_text: Callable[[str], None],
        on_check_price: Callable[[], None],
        get_results_table: Callable[[], Any],
        get_session_panel: Callable[[], Any],
    ):
        """
        Initialize the menu actions controller.

        Args:
            ctx: Application context
            parent: Parent widget for dialogs
            window_manager: Window manager service
            nav_controller: Navigation controller
            history_manager: History manager service
            on_status: Callback to set status message
            get_input_text: Callback to get input text
            set_input_text: Callback to set input text
            on_check_price: Callback to trigger price check
            get_results_table: Callback to get results table widget
            get_session_panel: Callback to get current session panel
        """
        self.ctx = ctx
        self._parent = parent
        self._window_manager = window_manager
        self._nav_controller = nav_controller
        self._history_manager = history_manager
        self._on_status = on_status
        self._get_input_text = get_input_text
        self._set_input_text = set_input_text
        self._on_check_price = on_check_price
        self._get_results_table = get_results_table
        self._get_session_panel = get_session_panel

        # Lazy-initialized controllers
        self._loot_controller: Optional["LootTrackingController"] = None

    # -------------------------------------------------------------------------
    # File Menu Actions
    # -------------------------------------------------------------------------

    def open_log_file(self) -> None:
        """Open the log file in the default viewer."""
        log_path = Path(__file__).parent.parent.parent / "logs" / "price_checker.log"
        if log_path.exists():
            os.startfile(str(log_path))
        else:
            QMessageBox.information(self._parent, "Log File", "No log file found.")

    def open_config_folder(self) -> None:
        """Open the config folder."""
        config_path = Path(__file__).parent.parent.parent / "data"
        if config_path.exists():
            os.startfile(str(config_path))
        else:
            QMessageBox.information(
                self._parent, "Config Folder", "Config folder not found."
            )

    def export_results(self) -> None:
        """Export results to TSV file."""
        panel = self._get_session_panel()
        if not panel or not panel._all_results:
            QMessageBox.information(self._parent, "Export", "No results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Export Results", "", "TSV Files (*.tsv);;All Files (*)"
        )

        if path:
            try:
                panel.results_table.export_tsv(path)
                self._on_status(f"Exported to {path}")
            except Exception as e:
                QMessageBox.critical(
                    self._parent, "Export Error", f"Failed to export: {e}"
                )

    def copy_all_as_tsv(self) -> None:
        """Copy all results as TSV."""
        results_table = self._get_results_table()
        if results_table:
            tsv = results_table.to_tsv(include_header=True)
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(tsv)
            self._on_status("All results copied as TSV")

    def show_settings(self, apply_thresholds_callback: Callable[[], None]) -> None:
        """Show settings dialog."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.ctx.config, parent=self._parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            apply_thresholds_callback()
            self._on_status("Settings saved")

    def show_export_dialog(self) -> None:
        """Show export data dialog."""
        from gui_qt.dialogs.export_dialog import ExportDialog

        dialog = ExportDialog(self.ctx, parent=self._parent)
        dialog.exec()

    # -------------------------------------------------------------------------
    # View Menu Actions
    # -------------------------------------------------------------------------

    def show_history(self) -> None:
        """Show session history dialog with re-check capability."""
        if self._history_manager.is_empty():
            QMessageBox.information(
                self._parent, "Recent Items", "No items checked this session."
            )
            return

        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog
        from gui_qt.services.history_manager import HistoryEntry
        from typing import cast, Union

        history_entries = cast(
            "List[Union[HistoryEntry, Dict[str, Any]]]",
            self._history_manager.get_entries(),
        )
        dialog = RecentItemsDialog(history_entries, self._parent)
        dialog.item_selected.connect(self._recheck_item_from_history)
        dialog.exec()

    def _recheck_item_from_history(self, item_text: str) -> None:
        """Re-check an item from history."""
        if item_text:
            self._set_input_text(item_text)
            self._on_check_price()

    def show_stash_viewer(self) -> None:
        """Show stash viewer window."""
        self._nav_controller.show_stash_viewer()

    # -------------------------------------------------------------------------
    # Economy Menu Actions
    # -------------------------------------------------------------------------

    def show_data_sources(self) -> None:
        """Show data sources dialog."""
        text = "Data Sources:\n\n"
        text += "- poe.ninja: Real-time economy data\n"
        text += "- poe.watch: Alternative price source\n"
        text += "- Trade API: Official trade site data\n"

        QMessageBox.information(self._parent, "Data Sources", text)

    def show_recent_sales(self) -> None:
        """Show recent sales window."""
        self._nav_controller.show_recent_sales()

    def show_sales_dashboard(self) -> None:
        """Show sales dashboard window."""
        self._nav_controller.show_sales_dashboard()

    def show_loot_dashboard(self) -> None:
        """Show loot tracking dashboard window."""
        from gui_qt.controllers.loot_tracking_controller import LootTrackingController

        # Lazily initialize loot tracking controller
        if not self._loot_controller:
            self._loot_controller = LootTrackingController(self.ctx, parent=self._parent)
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

    def collect_economy_snapshot(self) -> None:
        """Collect economy snapshot from poe.ninja for current league."""
        from core.economy import LeagueEconomyService

        league = self.ctx.config.league or "Keepers"
        self._on_status(f"Collecting economy snapshot for {league}...")

        try:
            service = LeagueEconomyService(self.ctx.db)
            snapshot = service.fetch_and_store_snapshot(league)

            if snapshot:
                self._on_status(
                    f"Economy snapshot saved: {league} - "
                    f"Divine={snapshot.divine_to_chaos:.0f}c"
                )
            else:
                self._on_status(f"No economy data available for {league}")
        except Exception as e:
            logger.error(f"Failed to collect economy snapshot: {e}")
            self._on_status(f"Error collecting snapshot: {e}")

    def show_price_history(self) -> None:
        """Show price history analytics window."""
        from gui_qt.windows.price_history_window import PriceHistoryWindow

        window = PriceHistoryWindow(ctx=self.ctx, parent=self._parent)
        window.exec()

    # -------------------------------------------------------------------------
    # Build Menu Actions
    # -------------------------------------------------------------------------

    def show_pob_characters(self) -> None:
        """Show PoB character manager window (deprecated - use show_build_manager)."""
        self._nav_controller.show_pob_characters()

    def show_build_manager(self) -> None:
        """Show unified Build Manager window."""
        self._nav_controller.show_build_manager()

    def show_rare_eval_config(self) -> None:
        """Show rare evaluation config window."""
        self._nav_controller.show_rare_eval_config()

    def show_price_rankings(self) -> None:
        """Show price rankings window."""
        self._nav_controller.show_price_rankings()

    def show_build_comparison(self) -> None:
        """Show build comparison dialog."""
        self._nav_controller.show_build_comparison()

    def show_bis_search(self) -> None:
        """Show BiS item search dialog."""
        self._nav_controller.show_bis_search()

    def show_upgrade_finder(self) -> None:
        """Show upgrade finder dialog."""
        self._nav_controller.show_upgrade_finder()

    def show_item_planning_hub(self, initial_tab: str = "upgrade_finder") -> None:
        """Show the unified Item Planning Hub dialog."""
        self._nav_controller.show_item_planning_hub(initial_tab)

    def show_build_library(self) -> None:
        """Show build library dialog."""
        self._nav_controller.show_build_library()

    def show_local_builds_import(
        self, on_build_imported: Callable[[str, dict], None]
    ) -> None:
        """Show dialog to import local PoB builds."""
        from gui_qt.dialogs.local_builds_dialog import LocalBuildsDialog

        dialog = LocalBuildsDialog(self._parent)
        dialog.build_imported.connect(on_build_imported)
        dialog.exec()

    def show_item_comparison(self) -> None:
        """Show item comparison dialog."""
        self._nav_controller.show_item_comparison()

    # -------------------------------------------------------------------------
    # Dev Menu Actions
    # -------------------------------------------------------------------------

    def paste_sample(self, item_type: str) -> None:
        """Paste a sample item of the given type."""
        from gui_qt.sample_items import SAMPLE_ITEMS

        samples = SAMPLE_ITEMS.get(item_type, [])
        if samples:
            sample = random.choice(samples)
            self._set_input_text(sample)
            self._on_status(f"Pasted sample {item_type}")

    def wipe_database(self) -> None:
        """Wipe the database after confirmation."""
        result = QMessageBox.warning(
            self._parent,
            "Wipe Database",
            "Are you sure you want to delete all recorded sales?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            try:
                self.ctx.db.wipe_all_data()
                self._on_status("Database wiped")
            except Exception as e:
                QMessageBox.critical(
                    self._parent, "Error", f"Failed to wipe database: {e}"
                )

    # -------------------------------------------------------------------------
    # Help Menu Actions
    # -------------------------------------------------------------------------

    def show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        from gui_qt.dialogs.help_dialogs import show_shortcuts_dialog

        show_shortcuts_dialog(self._parent)

    def show_tips(self) -> None:
        """Show usage tips dialog."""
        from gui_qt.dialogs.help_dialogs import show_tips_dialog

        show_tips_dialog(self._parent)

    def show_about(self) -> None:
        """Show about dialog."""
        from gui_qt.dialogs.help_dialogs import show_about_dialog

        show_about_dialog(self._parent)
