"""
Base AI client interface for LLM providers.

Provides abstract base class for AI providers (Gemini, Claude, OpenAI).
All implementations return Result types for consistent error handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

from core.result import Result

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIResponse:
    """Response from an AI provider.

    Attributes:
        content: The generated text response.
        model: The model that generated the response.
        tokens_used: Number of tokens consumed (if available).
        provider: The provider name (e.g., "gemini", "claude", "openai").
    """

    content: str
    model: str
    tokens_used: int = 0
    provider: str = ""


class BaseAIClient(ABC):
    """Abstract base class for AI provider clients.

    Subclasses must implement:
        - complete(): Send a prompt and get a response
        - is_configured(): Check if the client has valid credentials

    Example:
        >>> client = GeminiClient(api_key="...")
        >>> if client.is_configured():
        ...     result = client.complete("Tell me about this item")
        ...     if result.is_ok():
        ...         print(result.unwrap().content)
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        max_tokens: int = 500,
    ):
        """Initialize the AI client.

        Args:
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
        """
        self._api_key = api_key
        self._timeout = timeout
        self._max_tokens = max_tokens

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'gemini', 'claude', 'openai')."""
        pass

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Result[AIResponse, str]:
        """Send a prompt and get a completion response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.

        Returns:
            Result containing AIResponse on success, error message on failure.
        """
        pass

    def is_configured(self) -> bool:
        """Check if the client has valid credentials.

        Returns:
            True if api_key is set and non-empty.
        """
        return bool(self._api_key and self._api_key.strip())

    def _log_request(self, prompt_preview: str) -> None:
        """Log request details at debug level."""
        preview = prompt_preview[:100] + "..." if len(prompt_preview) > 100 else prompt_preview
        logger.debug(f"[{self.provider_name}] Sending prompt: {preview}")

    def _log_response(self, response: AIResponse) -> None:
        """Log response details at debug level."""
        logger.debug(
            f"[{self.provider_name}] Response received: "
            f"model={response.model}, tokens={response.tokens_used}"
        )

    def _log_error(self, error: str) -> None:
        """Log error at warning level."""
        logger.warning(f"[{self.provider_name}] Error: {error}")
