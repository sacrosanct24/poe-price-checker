"""
Background services mixin for worker threads and service management.

Extracts background service initialization and callbacks from main_window.py
to reduce coupling and improve maintainability.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui_qt.main_window import PriceCheckerWindow


class BackgroundServicesMixin:
    """
    Mixin providing background service management.

    This mixin expects the following attributes on self:
    - ctx: AppContext instance
    - logger: Logger instance
    - _rankings_worker: Optional[RankingsPopulationWorker]
    - summary_label: QLabel for status display
    - _toast_manager: ToastManager instance
    """

    def _start_rankings_population(self: "PriceCheckerWindow") -> None:
        """Start background task to populate price rankings if needed."""
        from gui_qt.workers import RankingsPopulationWorker

        try:
            self._rankings_worker = RankingsPopulationWorker(self)
            self._rankings_worker.status.connect(self._on_rankings_progress)
            self._rankings_worker.result.connect(self._on_rankings_finished)
            self._rankings_worker.error.connect(self._on_rankings_error)
            self._rankings_worker.start()
        except Exception as e:
            self.logger.warning(f"Failed to start rankings population: {e}")

    def _on_rankings_progress(self: "PriceCheckerWindow", message: str) -> None:
        """Handle rankings population progress."""
        self.logger.info(f"Rankings: {message}")

    def _on_rankings_finished(self: "PriceCheckerWindow", count: int) -> None:
        """Handle rankings population completion."""
        if count > 0:
            self.logger.info(f"Rankings: Populated {count} categories")
        self._rankings_worker = None

    def _on_rankings_error(self: "PriceCheckerWindow", error: str, traceback: str) -> None:
        """Handle rankings population error."""
        self.logger.warning(f"Rankings population failed: {error}")
        self.logger.debug(f"Traceback:\n{traceback}")
        self._rankings_worker = None

    def _start_price_refresh_service(self: "PriceCheckerWindow") -> None:
        """Start the background price refresh service."""
        from gui_qt.services import get_price_refresh_service

        try:
            service = get_price_refresh_service(self.ctx)
            if service:
                # Connect status updates to the summary label
                service.status_update.connect(self._on_price_refresh_status)
                service.price_changed.connect(self._on_price_changed)
                service.start()
                self.logger.info("Background price refresh service started")
        except Exception as e:
            self.logger.warning(f"Failed to start price refresh service: {e}")

    def _on_price_refresh_status(self: "PriceCheckerWindow", message: str) -> None:
        """Handle price refresh status update."""
        self.logger.debug(f"Price refresh: {message}")
        # Update summary label with last refresh time
        if "refreshed at" in message.lower():
            self.summary_label.setToolTip(message)

    def _on_price_changed(
        self: "PriceCheckerWindow", item_name: str, old_price: float, new_price: float
    ) -> None:
        """Handle significant price change notification."""
        direction = "up" if new_price > old_price else "down"
        change_pct = abs(new_price - old_price) / old_price * 100 if old_price > 0 else 0
        self.logger.info(
            f"Price alert: {item_name} went {direction} "
            f"({old_price:.1f}c -> {new_price:.1f}c, {change_pct:.1f}%)"
        )
        # Show toast notification for significant changes
        if hasattr(self, '_toast_manager') and self._toast_manager:
            self._toast_manager.info(
                f"{item_name}: {old_price:.0f}c -> {new_price:.0f}c ({direction} {change_pct:.0f}%)"
            )

    def _start_clipboard_service(self: "PriceCheckerWindow") -> None:
        """Start the global hotkey clipboard service."""
        from gui_qt.services import init_clipboard_service, get_clipboard_service

        try:
            service = init_clipboard_service(self.ctx, self)
            if service:
                # Connect signals
                service.hotkey_triggered.connect(self._on_global_hotkey_price_check)
                service.no_item_in_clipboard.connect(self._on_hotkey_no_item)
                service.status_changed.connect(self._on_clipboard_service_status)

                # Start the service
                if service.start():
                    self.logger.info(
                        f"Clipboard service started (hotkey: {service.current_hotkey})"
                    )
                else:
                    self.logger.warning("Clipboard service failed to start")
        except Exception as e:
            self.logger.warning(f"Failed to start clipboard service: {e}")

    def _stop_clipboard_service(self: "PriceCheckerWindow") -> None:
        """Stop the global hotkey clipboard service."""
        from gui_qt.services import shutdown_clipboard_service

        try:
            shutdown_clipboard_service()
        except Exception as e:
            self.logger.warning(f"Error stopping clipboard service: {e}")

    def _on_global_hotkey_price_check(self: "PriceCheckerWindow", item_text: str) -> None:
        """Handle global hotkey trigger with PoE item in clipboard."""
        self.logger.info("Global hotkey triggered - checking price")

        # Bring window to front if minimized
        if self.isMinimized():
            self.showNormal()
        self.activateWindow()
        self.raise_()

        # Set the item text in the input and trigger price check
        panel = self._get_current_session_panel()
        if panel:
            panel.input_text.setPlainText(item_text)
            self._on_check_price()

    def _on_hotkey_no_item(self: "PriceCheckerWindow") -> None:
        """Handle global hotkey trigger when no PoE item in clipboard."""
        if hasattr(self, '_toast_manager') and self._toast_manager:
            self._toast_manager.warning("No PoE item in clipboard")

    def _on_clipboard_service_status(self: "PriceCheckerWindow", status: str) -> None:
        """Handle clipboard service status change."""
        self.logger.debug(f"Clipboard service status: {status}")
        if status == "unavailable":
            if hasattr(self, '_toast_manager') and self._toast_manager:
                self._toast_manager.warning(
                    "Global hotkeys unavailable - install 'keyboard' module"
                )
