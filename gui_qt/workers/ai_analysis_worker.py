"""
AI Analysis Worker for background item analysis.

Runs AI API calls in a background thread to avoid blocking the UI.
Supports both standard item analysis and upgrade analysis with build context.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from gui_qt.workers.base_worker import BaseThreadWorker
from data_sources.ai import create_ai_client, AIResponse
from core.ai_prompt_builder import AIPromptBuilder, PromptContext
from core.result import Result

if TYPE_CHECKING:
    from core.build_summarizer import BuildSummary

logger = logging.getLogger(__name__)


class AIAnalysisWorker(BaseThreadWorker):
    """Worker that performs AI item analysis in a background thread.

    Signals:
        result: Emitted with AIResponse on success
        error: Emitted with (message, traceback) on failure
        status: Emitted with status message for progress updates

    Example:
        worker = AIAnalysisWorker(
            provider="gemini",
            api_key="...",
            item_text="Rarity: Unique...",
            price_results=[{"chaos_value": 100}],
        )
        worker.result.connect(self._on_ai_result)
        worker.error.connect(self._on_ai_error)
        worker.start()
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        item_text: str,
        price_results: List[Dict[str, Any]],
        timeout: int = 30,
        max_tokens: int = 500,
        league: str = "",
        build_name: str = "",
        custom_prompt: str = "",
        build_summary: Optional["BuildSummary"] = None,
        raw_prompt: bool = False,
        ollama_host: str = "",
        ollama_model: str = "",
        parent: Optional[Any] = None,
    ):
        """Initialize the AI analysis worker.

        Args:
            provider: AI provider name (gemini, claude, openai, groq, ollama).
            api_key: API key for the provider (not needed for ollama).
            item_text: The raw item text to analyze (or complete prompt if raw_prompt=True).
            price_results: List of price check results for context.
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
            league: Current league name for context.
            build_name: Player's build name for context.
            custom_prompt: Optional custom prompt template.
            build_summary: Optional BuildSummary for detailed build context.
            raw_prompt: If True, use item_text directly as the prompt without wrapping.
            ollama_host: Ollama server URL (for ollama provider).
            ollama_model: Ollama model name (for ollama provider).
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._provider = provider
        self._api_key = api_key
        self._item_text = item_text
        self._price_results = price_results
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._league = league
        self._build_name = build_name
        self._custom_prompt = custom_prompt
        self._build_summary = build_summary
        self._raw_prompt = raw_prompt
        self._ollama_host = ollama_host
        self._ollama_model = ollama_model
        self._prompt_builder = AIPromptBuilder()

    def _execute(self) -> AIResponse:
        """Execute the AI analysis.

        Returns:
            AIResponse with the analysis result.

        Raises:
            ValueError: If analysis fails.
        """
        self.emit_status("Creating AI client...")

        # Check cancellation
        if self.is_cancelled:
            raise InterruptedError("Analysis cancelled")

        # Create client
        client = create_ai_client(
            provider=self._provider,
            api_key=self._api_key,
            timeout=self._timeout,
            max_tokens=self._max_tokens,
            ollama_host=self._ollama_host,
            ollama_model=self._ollama_model,
        )

        if not client:
            raise ValueError(f"Unknown AI provider: {self._provider}")

        if not client.is_configured():
            raise ValueError(f"AI provider {self._provider} is not configured")

        try:
            # Build prompt
            self.emit_status("Building prompt...")

            if self.is_cancelled:
                raise InterruptedError("Analysis cancelled")

            # If raw_prompt is True, use the item_text directly as the prompt
            # This is used for upgrade analysis where the complete prompt is pre-built
            if self._raw_prompt:
                prompt = self._item_text
            else:
                context = PromptContext(
                    item_text=self._item_text,
                    price_results=self._price_results,
                    league=self._league,
                    build_name=self._build_name,
                    build_summary=self._build_summary,
                )

                prompt = self._prompt_builder.build_item_analysis_prompt(
                    context,
                    custom_template=self._custom_prompt if self._custom_prompt else None,
                )

            system_prompt = self._prompt_builder.get_system_prompt()

            # Send to AI
            self.emit_status(f"Asking {self._provider.title()}...")

            if self.is_cancelled:
                raise InterruptedError("Analysis cancelled")

            result: Result[AIResponse, str] = client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
            )

            if self.is_cancelled:
                raise InterruptedError("Analysis cancelled")

            if result.is_err():
                raise ValueError(result.error)

            self.emit_status("Analysis complete")
            return result.unwrap()

        finally:
            # Clean up client
            if hasattr(client, 'close'):
                client.close()
