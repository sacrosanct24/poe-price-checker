"""
gui_qt.controllers.navigation_controller - Manages window/dialog navigation.

Extracts the repetitive _show_* methods from main_window.py into a
centralized navigation controller that handles:
- Dialog/window imports
- WindowManager factory registration
- Window showing and activation

Usage:
    nav = NavigationController(window_manager, ctx, callbacks)
    nav.show_recent_sales()
    nav.show_pob_characters()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from gui_qt.services.window_manager import WindowManager
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class NavigationController:
    """
    Centralized controller for showing windows and dialogs.

    Reduces main_window.py complexity by extracting all _show_* methods
    into a single controller with consistent patterns.
    """

    def __init__(
        self,
        window_manager: "WindowManager",
        ctx: "AppContext",
        main_window: Any,
        character_manager: Optional[Any] = None,
        callbacks: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize the navigation controller.

        Args:
            window_manager: WindowManager for window lifecycle.
            ctx: Application context with config, db, etc.
            main_window: Reference to the main window for parenting.
            character_manager: PoB character manager (optional).
            callbacks: Dict of callback functions for various events.
        """
        self._wm = window_manager
        self._ctx = ctx
        self._main_window = main_window
        self._character_manager = character_manager
        self._callbacks = callbacks or {}

    def set_character_manager(self, manager: Any) -> None:
        """Set the character manager (may be initialized later)."""
        self._character_manager = manager

    def set_callback(self, name: str, callback: Callable) -> None:
        """Register a callback by name."""
        self._callbacks[name] = callback

    # -------------------------------------------------------------------------
    # Price Windows
    # -------------------------------------------------------------------------

    def show_recent_sales(self) -> None:
        """Show recent sales window."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        if "recent_sales" not in self._wm._factories:
            def create_recent_sales():
                window = RecentSalesWindow(ctx=self._ctx, parent=self._main_window)
                # Wire up AI callbacks
                if "ai_configured" in self._callbacks:
                    window.set_ai_configured_callback(self._callbacks["ai_configured"])
                if "on_ai_analysis" in self._callbacks:
                    window.ai_analysis_requested.connect(self._callbacks["on_ai_analysis"])
                if "on_price_check" in self._callbacks:
                    window.price_check_requested.connect(self._callbacks["on_price_check"])
                return window

            self._wm.register_factory("recent_sales", create_recent_sales)

        self._wm.show_window("recent_sales")

    def show_sales_dashboard(self) -> None:
        """Show sales dashboard window."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow
        self._wm.show_window("sales_dashboard", SalesDashboardWindow, ctx=self._ctx)

    def show_price_rankings(self) -> None:
        """Show price rankings window."""
        from gui_qt.windows.price_rankings_window import PriceRankingsWindow

        if "price_rankings" not in self._wm._factories:
            def create_price_rankings():
                window = PriceRankingsWindow(ctx=self._ctx, parent=self._main_window)
                if "on_ranking_price_check" in self._callbacks:
                    window.priceCheckRequested.connect(
                        self._callbacks["on_ranking_price_check"]
                    )
                # Wire up AI callbacks
                if "ai_configured" in self._callbacks:
                    window.set_ai_configured_callback(self._callbacks["ai_configured"])
                if "on_ai_analysis" in self._callbacks:
                    window.ai_analysis_requested.connect(self._callbacks["on_ai_analysis"])
                return window

            self._wm.register_factory("price_rankings", create_price_rankings)

        self._wm.show_window("price_rankings")

    # -------------------------------------------------------------------------
    # Build Windows
    # -------------------------------------------------------------------------

    def show_pob_characters(self) -> Optional[Any]:
        """Show PoB character manager window."""
        from PyQt6.QtWidgets import QMessageBox
        from gui_qt.windows.pob_character_window import PoBCharacterWindow

        if self._character_manager is None:
            QMessageBox.warning(
                self._main_window,
                "PoB Characters",
                "Character manager not initialized."
            )
            return None

        if "pob_characters" not in self._wm._factories:
            self._wm.register_factory(
                "pob_characters",
                lambda: PoBCharacterWindow(
                    self._character_manager,
                    self._main_window,
                    on_profile_selected=self._callbacks.get("on_pob_profile_selected"),
                    on_price_check=self._callbacks.get("on_pob_price_check"),
                )
            )

        window = self._wm.show_window("pob_characters")
        if window:
            window.activateWindow()
        return window

    def show_build_comparison(self) -> None:
        """Show build comparison dialog."""
        from gui_qt.dialogs.build_comparison_dialog import BuildComparisonDialog

        if "build_comparison" not in self._wm._factories:
            self._wm.register_factory(
                "build_comparison",
                lambda: BuildComparisonDialog(
                    self._main_window,
                    character_manager=self._character_manager,
                )
            )

        self._wm.show_window("build_comparison")

    def show_loadout_selector(self) -> None:
        """Show loadout selector dialog for browsing PoB loadouts."""
        from gui_qt.dialogs.loadout_selector_dialog import LoadoutSelectorDialog

        if "loadout_selector" not in self._wm._factories:
            def create_loadout_selector():
                dialog = LoadoutSelectorDialog(self._main_window)
                if "on_loadout_selected" in self._callbacks:
                    dialog.loadout_selected.connect(
                        self._callbacks["on_loadout_selected"]
                    )
                return dialog

            self._wm.register_factory("loadout_selector", create_loadout_selector)

        self._wm.show_window("loadout_selector")

    def show_bis_search(self) -> None:
        """Show BiS item search dialog."""
        from gui_qt.dialogs.bis_search_dialog import BiSSearchDialog

        if "bis_search" not in self._wm._factories:
            self._wm.register_factory(
                "bis_search",
                lambda: BiSSearchDialog(
                    self._main_window,
                    character_manager=self._character_manager,
                )
            )

        self._wm.show_window("bis_search")

    def show_upgrade_finder(self) -> None:
        """Show upgrade finder dialog."""
        from gui_qt.dialogs.upgrade_finder_dialog import UpgradeFinderDialog

        if "upgrade_finder" not in self._wm._factories:
            self._wm.register_factory(
                "upgrade_finder",
                lambda: UpgradeFinderDialog(
                    self._main_window,
                    character_manager=self._character_manager,
                )
            )

        self._wm.show_window("upgrade_finder")

    def show_build_library(self) -> None:
        """Show build library dialog."""
        from gui_qt.dialogs.build_library_dialog import BuildLibraryDialog

        if "build_library" not in self._wm._factories:
            self._wm.register_factory(
                "build_library",
                lambda: BuildLibraryDialog(
                    self._main_window,
                    character_manager=self._character_manager,
                )
            )

        self._wm.show_window("build_library")

    def show_item_comparison(self) -> None:
        """Show item comparison dialog."""
        from gui_qt.dialogs.item_comparison_dialog import ItemComparisonDialog
        self._wm.show_window("item_comparison", ItemComparisonDialog, ctx=self._ctx)

    def show_rare_eval_config(self, on_save: Optional[Callable] = None) -> None:
        """Show rare evaluation config window."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        data_dir = Path(__file__).parent.parent.parent / "data"

        if "rare_eval_config" not in self._wm._factories:
            save_callback = on_save or self._callbacks.get("on_reload_rare_evaluator")
            self._wm.register_factory(
                "rare_eval_config",
                lambda: RareEvalConfigWindow(
                    data_dir,
                    self._main_window,
                    on_save=save_callback,
                )
            )

        self._wm.show_window("rare_eval_config")

    # -------------------------------------------------------------------------
    # Viewer Windows
    # -------------------------------------------------------------------------

    def show_stash_viewer(self) -> None:
        """Show stash viewer window."""
        from gui_qt.windows.stash_viewer_window import StashViewerWindow

        if "stash_viewer" not in self._wm._factories:
            def create_stash_viewer():
                window = StashViewerWindow(ctx=self._ctx, parent=self._main_window)
                # Wire up AI callbacks
                if "ai_configured" in self._callbacks:
                    window.set_ai_configured_callback(self._callbacks["ai_configured"])
                if "on_ai_analysis" in self._callbacks:
                    window.ai_analysis_requested.connect(self._callbacks["on_ai_analysis"])
                return window

            self._wm.register_factory("stash_viewer", create_stash_viewer)

        self._wm.show_window("stash_viewer")

    def show_upgrade_advisor(
        self,
        slot: Optional[str] = None,
        on_upgrade_analysis: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Show AI upgrade advisor window.

        Args:
            slot: Optional slot to pre-select and analyze.
            on_upgrade_analysis: Callback for handling upgrade analysis requests.
        """
        from gui_qt.windows.upgrade_advisor_window import UpgradeAdvisorWindow

        if "upgrade_advisor" not in self._wm._factories:
            def create_upgrade_advisor():
                window = UpgradeAdvisorWindow(
                    config=self._ctx.config,
                    character_manager=self._character_manager,
                    parent=self._main_window,
                    on_status=self._callbacks.get("on_status"),
                )
                # Set database for caching
                if hasattr(self._ctx, 'db') and self._ctx.db:
                    window.set_database(self._ctx.db)
                # Wire up AI configured callback
                if "ai_configured" in self._callbacks:
                    window.set_ai_configured_callback(self._callbacks["ai_configured"])
                # Wire up upgrade analysis signal
                if "on_upgrade_analysis" in self._callbacks:
                    window.upgrade_analysis_requested.connect(
                        self._callbacks["on_upgrade_analysis"]
                    )
                return window

            self._wm.register_factory("upgrade_advisor", create_upgrade_advisor)

        window = self._wm.show_window("upgrade_advisor")

        # If a slot was specified, trigger analysis for it
        if slot and window:
            # Use getattr since window is typed as QWidget but may have analyze_slot method
            analyze_method = getattr(window, "analyze_slot", None)
            if analyze_method:
                analyze_method(slot)


def get_navigation_controller(
    window_manager: "WindowManager",
    ctx: "AppContext",
    main_window: Any,
    character_manager: Optional[Any] = None,
    callbacks: Optional[Dict[str, Callable]] = None,
) -> NavigationController:
    """
    Factory function to create a NavigationController.

    Args:
        window_manager: WindowManager for window lifecycle.
        ctx: Application context.
        main_window: Reference to main window.
        character_manager: PoB character manager (optional).
        callbacks: Dict of callback functions.

    Returns:
        Configured NavigationController instance.
    """
    return NavigationController(
        window_manager=window_manager,
        ctx=ctx,
        main_window=main_window,
        character_manager=character_manager,
        callbacks=callbacks,
    )
