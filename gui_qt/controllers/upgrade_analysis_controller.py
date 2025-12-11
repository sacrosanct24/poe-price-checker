"""
Upgrade Analysis Controller.

Handles AI-powered upgrade analysis orchestration for the main window.
Manages the flow between UpgradeAdvisorWindow, AIAdvisorScreen,
and full-screen UpgradeAdvisorView.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
    from core.app_context import AppContext
    from core.config import Config
    from gui_qt.controllers.ai_analysis_controller import AIAnalysisController
    from gui_qt.controllers.pob_controller import PoBController
    from gui_qt.services.window_manager import WindowManager
    from gui_qt.views.upgrade_advisor_view import UpgradeAdvisorView
    from gui_qt.screens import AIAdvisorScreen
    from PyQt6.QtWidgets import QStackedWidget


class UpgradeAnalysisController:
    """
    Orchestrates upgrade analysis across different UI contexts.

    This controller handles:
    - Upgrade analysis requests from UpgradeAdvisorWindow
    - Upgrade analysis requests from AIAdvisorScreen
    - Upgrade analysis requests from full-screen UpgradeAdvisorView
    - Provider validation and temporary provider switching
    """

    def __init__(
        self,
        ctx: "AppContext",
        pob_controller: "PoBController",
        window_manager: "WindowManager",
        get_ai_controller: Callable[[], Optional["AIAnalysisController"]],
        init_ai_controller: Callable[[], None],
        on_status: Callable[[str], None],
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the upgrade analysis controller.

        Args:
            ctx: Application context with config and database.
            pob_controller: PoB controller for character manager access.
            window_manager: Window manager for accessing child windows.
            get_ai_controller: Callback to get the current AI controller.
            init_ai_controller: Callback to initialize AI controller if needed.
            on_status: Callback to set status bar message.
            logger: Optional logger instance.
        """
        self.ctx = ctx
        self._pob_controller = pob_controller
        self._window_manager = window_manager
        self._get_ai_controller = get_ai_controller
        self._init_ai_controller = init_ai_controller
        self._on_status = on_status
        self._logger = logger or logging.getLogger(__name__)

        # References to views (set externally after creation)
        self._ai_advisor_screen: Optional["AIAdvisorScreen"] = None
        self._upgrade_advisor_view: Optional["UpgradeAdvisorView"] = None
        self._stacked_widget: Optional["QStackedWidget"] = None

    def set_ai_advisor_screen(self, screen: Optional["AIAdvisorScreen"]) -> None:
        """Set the AI Advisor screen reference."""
        self._ai_advisor_screen = screen

    def set_upgrade_advisor_view(self, view: Optional["UpgradeAdvisorView"]) -> None:
        """Set the full-screen upgrade advisor view reference."""
        self._upgrade_advisor_view = view

    def set_stacked_widget(self, widget: "QStackedWidget") -> None:
        """Set the stacked widget for view switching."""
        self._stacked_widget = widget

    def _validate_provider(
        self,
        selected_provider: Optional[str],
        on_error: Callable[[str, str], None],
        slot: str,
    ) -> bool:
        """
        Validate that the selected AI provider is configured.

        Args:
            selected_provider: The AI provider name.
            on_error: Callback to show error (slot, message).
            slot: The equipment slot being analyzed.

        Returns:
            True if provider is valid and configured, False otherwise.
        """
        if not selected_provider:
            self._on_status("No AI provider selected")
            on_error(slot, "No AI provider selected")
            return False

        # Check if the provider has an API key (unless it's a local provider)
        from data_sources.ai import is_local_provider
        if not is_local_provider(selected_provider):
            api_key = self.ctx.config.get_ai_api_key(selected_provider)
            if not api_key:
                self._on_status(f"No API key configured for {selected_provider}")
                on_error(
                    slot,
                    f"No API key configured for {selected_provider}.\n"
                    f"Add your API key in Settings > AI."
                )
                return False

        return True

    def _setup_ai_controller(self) -> Optional["AIAnalysisController"]:
        """
        Get or initialize the AI controller with required dependencies.

        Returns:
            The AI controller, or None if initialization failed.
        """
        ai_controller = self._get_ai_controller()
        if not ai_controller:
            self._init_ai_controller()
            ai_controller = self._get_ai_controller()

        if not ai_controller:
            return None

        # Set up the AI controller with database for stash access
        ai_controller.set_database(self.ctx.db)
        char_manager = self._pob_controller.character_manager
        if char_manager:
            ai_controller.set_character_manager(char_manager)

        return ai_controller

    def _perform_analysis(
        self,
        ai_controller: "AIAnalysisController",
        slot: str,
        include_stash: bool,
        selected_provider: str,
        on_result: Callable[[str, str, str], None],
        on_error: Callable[[str, str], None],
    ) -> bool:
        """
        Perform the upgrade analysis.

        Args:
            ai_controller: The AI controller to use.
            slot: Equipment slot to analyze.
            include_stash: Whether to include stash items.
            selected_provider: The AI provider being used.
            on_result: Callback for successful result (slot, content, provider).
            on_error: Callback for errors (slot, message).

        Returns:
            True if analysis started successfully, False otherwise.
        """
        # Get account name from config (only needed if include_stash is True)
        account_name = None
        if include_stash:
            account_name = self.ctx.config.data.get("stash", {}).get("account_name", "")

        # Temporarily set the config provider to the selected one
        original_provider = self.ctx.config.ai_provider
        self.ctx.config.ai_provider = selected_provider

        try:
            success = ai_controller.analyze_upgrade(
                slot=slot,
                account_name=account_name,
                include_stash=include_stash,
            )
        finally:
            # Restore original provider (worker has captured the selected one)
            self.ctx.config.ai_provider = original_provider

        if success:
            # Connect to get results back
            def handle_result(response):
                on_result(slot, response.content, selected_provider)

            def handle_error(error_msg, traceback):
                on_error(slot, error_msg)

            # Connect signals for this specific request
            if ai_controller._worker:
                ai_controller._worker.result.connect(handle_result)
                ai_controller._worker.error.connect(handle_error)
            return True
        else:
            on_error(slot, "Failed to start analysis")
            return False

    def handle_upgrade_analysis_from_window(
        self,
        slot: str,
        item_text: str,
    ) -> None:
        """
        Handle upgrade analysis request from the Upgrade Advisor window.

        Args:
            slot: Equipment slot to analyze.
            item_text: Item text (currently unused but kept for interface).
        """
        from gui_qt.windows.upgrade_advisor_window import UpgradeAdvisorWindow

        # Get the window to check its selected provider
        window_widget = self._window_manager.get_window("upgrade_advisor")
        if not window_widget or not isinstance(window_widget, UpgradeAdvisorWindow):
            return
        window = window_widget

        selected_provider = window.get_selected_provider()
        if not self._validate_provider(
            selected_provider,
            window.show_analysis_error,
            slot,
        ):
            return

        ai_controller = self._setup_ai_controller()
        if not ai_controller:
            window.show_analysis_error(slot, "Failed to initialize AI controller")
            return

        self._perform_analysis(
            ai_controller=ai_controller,
            slot=slot,
            include_stash=True,  # Window always includes stash
            selected_provider=selected_provider,  # type: ignore
            on_result=window.show_analysis_result,
            on_error=window.show_analysis_error,
        )

    def handle_upgrade_analysis_from_ai_advisor(
        self,
        slot: str,
        include_stash: bool,
    ) -> None:
        """
        Handle upgrade analysis request from the AI Advisor screen.

        Args:
            slot: Equipment slot to analyze.
            include_stash: Whether to include stash items in analysis.
        """
        if not self._ai_advisor_screen:
            return

        # Get the screen's upgrade advisor to check provider
        upgrade_advisor = self._ai_advisor_screen.get_upgrade_advisor()
        if not upgrade_advisor:
            return

        selected_provider = upgrade_advisor.get_selected_provider()
        if not self._validate_provider(
            selected_provider,
            self._ai_advisor_screen.show_analysis_error,
            slot,
        ):
            return

        ai_controller = self._setup_ai_controller()
        if not ai_controller:
            self._ai_advisor_screen.show_analysis_error(
                slot, "Failed to initialize AI"
            )
            return

        self._perform_analysis(
            ai_controller=ai_controller,
            slot=slot,
            include_stash=include_stash,
            selected_provider=selected_provider,  # type: ignore
            on_result=self._ai_advisor_screen.show_analysis_result,
            on_error=self._ai_advisor_screen.show_analysis_error,
        )

    def handle_upgrade_analysis_from_fullscreen(
        self,
        slot: str,
        include_stash: bool,
    ) -> None:
        """
        Handle upgrade analysis request from the full-screen advisor view.

        Args:
            slot: Equipment slot to analyze.
            include_stash: Whether to include stash items in analysis.
        """
        if not self._upgrade_advisor_view:
            return

        selected_provider = self._upgrade_advisor_view.get_selected_provider()
        if not self._validate_provider(
            selected_provider,
            self._upgrade_advisor_view.show_analysis_error,
            slot,
        ):
            return

        ai_controller = self._setup_ai_controller()
        if not ai_controller:
            self._upgrade_advisor_view.show_analysis_error(
                slot, "Failed to initialize AI"
            )
            return

        self._perform_analysis(
            ai_controller=ai_controller,
            slot=slot,
            include_stash=include_stash,
            selected_provider=selected_provider,  # type: ignore
            on_result=self._upgrade_advisor_view.show_analysis_result,
            on_error=self._upgrade_advisor_view.show_analysis_error,
        )

    def show_upgrade_advisor_fullscreen(
        self,
        slot: Optional[str] = None,
        create_view_callback: Optional[Callable[[], "UpgradeAdvisorView"]] = None,
    ) -> None:
        """
        Switch to the full-screen upgrade advisor view.

        Args:
            slot: Optional equipment slot to pre-select.
            create_view_callback: Callback to create the view if not exists.
        """
        if not self._stacked_widget:
            self._logger.warning("No stacked widget set for upgrade advisor")
            return

        # Lazy-load the upgrade advisor view
        if self._upgrade_advisor_view is None and create_view_callback:
            self._upgrade_advisor_view = create_view_callback()
            # Add to stacked widget
            self._stacked_widget.addWidget(self._upgrade_advisor_view)

        if not self._upgrade_advisor_view:
            self._logger.warning("Upgrade advisor view not available")
            return

        # Refresh the view data
        self._upgrade_advisor_view.refresh()

        # Pre-select slot if specified
        if slot:
            self._upgrade_advisor_view.select_slot(slot)

        # Find the index of the upgrade advisor view
        view_index = self._stacked_widget.indexOf(self._upgrade_advisor_view)
        if view_index >= 0:
            self._stacked_widget.setCurrentIndex(view_index)
            self._on_status("Upgrade Advisor - Select a slot to analyze")

    def close_upgrade_advisor(self) -> None:
        """Return to the main view from the upgrade advisor."""
        if self._stacked_widget:
            self._stacked_widget.setCurrentIndex(0)
            self._on_status("Ready")
