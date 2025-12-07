"""
xAI Grok AI client implementation.

Uses the xAI API (OpenAI-compatible) for text generation.
Requires an xAI API key from https://console.x.ai

Supported models:
- grok-3 (latest flagship model)
- grok-3-mini (fast and efficient)
- grok-2 (previous generation)
"""

from __future__ import annotations

from typing import Optional
import requests
import logging

from core.result import Result, Ok, Err
from data_sources.ai.base_ai_client import BaseAIClient, AIResponse

logger = logging.getLogger(__name__)

# xAI API endpoint (OpenAI-compatible)
XAI_API_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4-1-fast-reasoning"

# Available models with descriptions
XAI_MODELS = {
    "grok-4-1-fast-reasoning": "Grok 4.1 - With chain-of-thought reasoning",
    "grok-4-1-fast-non-reasoning": "Grok 4.1 Fast - Direct responses, faster",
    "grok-3": "Grok 3 - Previous flagship model",
    "grok-3-mini": "Grok 3 Mini - Fast and efficient",
}


class XAIClient(BaseAIClient):
    """xAI Grok API client.

    Uses Grok 4.1 with reasoning by default.

    Example:
        >>> client = XAIClient(api_key="your-api-key")
        >>> result = client.complete("Tell me about this item")
        >>> if result.is_ok():
        ...     print(result.unwrap().content)
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        max_tokens: int = 500,
        model: str = DEFAULT_MODEL,
    ):
        """Initialize xAI client.

        Args:
            api_key: xAI API key (get from console.x.ai).
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
            model: Model to use (default: grok-4-1-fast-reasoning).
        """
        # Strip whitespace from API key (common copy-paste issue)
        api_key = api_key.strip() if api_key else ""

        super().__init__(api_key, timeout, max_tokens)
        self._model = model
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        })

    @property
    def provider_name(self) -> str:
        return "xai"

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Result[AIResponse, str]:
        """Send a prompt to xAI Grok and get a response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction for context.

        Returns:
            Result containing AIResponse on success, error message on failure.
        """
        if not self.is_configured():
            return Err("xAI API key not configured")

        self._log_request(prompt)

        try:
            # Build messages (OpenAI-compatible format)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self._model,
                "messages": messages,
                "max_tokens": self._max_tokens,
                "temperature": 0.7,
            }

            # Make request
            url = f"{XAI_API_BASE}/chat/completions"
            response = self._session.post(
                url,
                json=payload,
                timeout=self._timeout,
            )

            # Handle errors
            if response.status_code == 401:
                self._log_error("Invalid API key")
                return Err("Invalid xAI API key")

            if response.status_code == 429:
                self._log_error("Rate limit exceeded")
                return Err("xAI rate limit exceeded. Please try again later.")

            if response.status_code >= 500:
                self._log_error(f"Server error: {response.status_code}")
                return Err(f"xAI server error ({response.status_code})")

            if not response.ok:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text[:200])
                self._log_error(f"HTTP {response.status_code}: {error_msg}")
                return Err(f"xAI error: {error_msg}")

            # Parse response
            data = response.json()

            choices = data.get("choices", [])
            if not choices:
                self._log_error("No choices in response")
                return Err("xAI returned no response")

            message = choices[0].get("message", {})
            text = message.get("content", "")
            if not text:
                self._log_error("Empty content in response")
                return Err("xAI returned empty response")

            # Get token usage
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)

            ai_response = AIResponse(
                content=text,
                model=self._model,
                tokens_used=total_tokens,
                provider=self.provider_name,
            )

            self._log_response(ai_response)
            return Ok(ai_response)

        except requests.Timeout:
            self._log_error("Request timed out")
            return Err(f"xAI request timed out after {self._timeout}s")
        except requests.RequestException as e:
            self._log_error(f"Request failed: {e}")
            return Err(f"xAI request failed: {e}")
        except (KeyError, ValueError) as e:
            self._log_error(f"Failed to parse response: {e}")
            return Err(f"Failed to parse xAI response: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
