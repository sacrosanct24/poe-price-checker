"""
gui_qt.controllers.ai_analysis_controller - AI item analysis controller.

Coordinates AI analysis requests:
- Context menu integration
- Worker lifecycle management
- Panel updates

Usage:
    controller = AIAnalysisController(config=config, panel=ai_panel)
    controller.analyze_item(item_text, price_results)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from core.config import Config
    from gui_qt.widgets.ai_analysis_panel import AIAnalysisPanelWidget
    from gui_qt.workers.ai_analysis_worker import AIAnalysisWorker
    from data_sources.ai import AIResponse

logger = logging.getLogger(__name__)


class AIAnalysisController:
    """
    Controller for AI item analysis operations.

    Handles:
    - Starting AI analysis via worker
    - Cancelling ongoing analysis
    - Updating panel with results/errors
    - Managing worker lifecycle
    """

    def __init__(
        self,
        config: "Config",
        panel: "AIAnalysisPanelWidget",
        on_status: Optional[Callable[[str], None]] = None,
        on_toast_success: Optional[Callable[[str], None]] = None,
        on_toast_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the AI analysis controller.

        Args:
            config: Application configuration with AI settings.
            panel: The AI analysis panel widget to update.
            on_status: Callback for status bar messages.
            on_toast_success: Callback for success toast notifications.
            on_toast_error: Callback for error toast notifications.
        """
        self._config = config
        self._panel = panel
        self._on_status = on_status or (lambda msg: None)
        self._on_toast_success = on_toast_success or (lambda msg: None)
        self._on_toast_error = on_toast_error or (lambda msg: None)

        # Current worker reference
        self._worker: Optional["AIAnalysisWorker"] = None

        # Store last request for retry
        self._last_item_text: Optional[str] = None
        self._last_price_results: Optional[List[Dict[str, Any]]] = None

        # Connect panel retry signal
        self._panel.retry_requested.connect(self._on_retry_requested)

    def is_configured(self) -> bool:
        """Check if AI is properly configured.

        Returns:
            True if a provider is selected and has an API key.
        """
        return self._config.has_ai_configured()

    def get_provider(self) -> str:
        """Get the current AI provider name.

        Returns:
            Provider name, or empty string if not configured.
        """
        return self._config.ai_provider

    def analyze_item(
        self,
        item_text: str,
        price_results: List[Dict[str, Any]],
    ) -> bool:
        """Start AI analysis of an item.

        Args:
            item_text: The raw item text to analyze.
            price_results: List of price check results for context.

        Returns:
            True if analysis was started, False if not configured.
        """
        if not self.is_configured():
            logger.warning("AI analysis requested but not configured")
            self._on_status("AI not configured - check Settings > AI")
            return False

        # Cancel any existing analysis
        self._cancel_current()

        # Store for retry
        self._last_item_text = item_text
        self._last_price_results = price_results

        # Get config values
        provider = self._config.ai_provider
        api_key = self._config.get_ai_api_key(provider)
        timeout = self._config.ai_timeout
        max_tokens = self._config.ai_max_tokens
        league = self._config.league
        build_name = self._config.ai_build_name
        custom_prompt = self._config.ai_custom_prompt

        # Show loading state
        self._panel.show_loading(provider)
        self._on_status(f"Starting AI analysis ({provider})...")

        # Create and start worker
        from gui_qt.workers.ai_analysis_worker import AIAnalysisWorker

        self._worker = AIAnalysisWorker(
            provider=provider,
            api_key=api_key,
            item_text=item_text,
            price_results=price_results,
            timeout=timeout,
            max_tokens=max_tokens,
            league=league,
            build_name=build_name,
            custom_prompt=custom_prompt,
        )

        # Connect signals
        self._worker.result.connect(self._on_analysis_result)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.status.connect(self._on_analysis_status)
        self._worker.finished.connect(self._on_worker_finished)

        # Start worker
        self._worker.start()

        logger.info(f"Started AI analysis with {provider}")
        return True

    def cancel(self) -> None:
        """Cancel any ongoing analysis."""
        self._cancel_current()
        self._panel.clear()
        self._panel.setVisible(False)
        self._on_status("AI analysis cancelled")

    def _cancel_current(self) -> None:
        """Cancel the current worker if running."""
        if self._worker is not None:
            logger.debug("Cancelling existing AI worker")
            self._worker.cancel()
            self._worker.wait(1000)  # Wait up to 1 second
            self._worker = None

    def _on_analysis_result(self, response: "AIResponse") -> None:
        """Handle successful analysis result.

        Args:
            response: The AIResponse from the worker.
        """
        logger.info(f"AI analysis complete: {response.tokens_used} tokens")
        self._panel.show_response(response)
        self._on_status("AI analysis complete")

    def _on_analysis_error(self, error_msg: str, traceback: str) -> None:
        """Handle analysis error.

        Args:
            error_msg: Error message.
            traceback: Error traceback string.
        """
        logger.error(f"AI analysis failed: {error_msg}")
        provider = self._config.ai_provider
        self._panel.show_error(error_msg, provider)
        self._on_status(f"AI analysis failed: {error_msg}")
        self._on_toast_error(f"AI error: {error_msg}")

    def _on_analysis_status(self, status: str) -> None:
        """Handle status updates from worker.

        Args:
            status: Status message.
        """
        self._on_status(status)

    def _on_worker_finished(self) -> None:
        """Handle worker finished signal."""
        self._worker = None

    def _on_retry_requested(self) -> None:
        """Handle retry button click from panel."""
        if self._last_item_text is not None and self._last_price_results is not None:
            self.analyze_item(self._last_item_text, self._last_price_results)


def get_ai_analysis_controller(
    config: "Config",
    panel: "AIAnalysisPanelWidget",
    on_status: Optional[Callable[[str], None]] = None,
    on_toast_success: Optional[Callable[[str], None]] = None,
    on_toast_error: Optional[Callable[[str], None]] = None,
) -> AIAnalysisController:
    """
    Factory function to create an AIAnalysisController.

    Args:
        config: Application configuration.
        panel: AI analysis panel widget.
        on_status: Status callback.
        on_toast_success: Success toast callback.
        on_toast_error: Error toast callback.

    Returns:
        Configured AIAnalysisController instance.
    """
    return AIAnalysisController(
        config=config,
        panel=panel,
        on_status=on_status,
        on_toast_success=on_toast_success,
        on_toast_error=on_toast_error,
    )
