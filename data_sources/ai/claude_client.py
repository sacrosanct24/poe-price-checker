"""
Anthropic Claude AI client implementation.

Uses the Claude Messages API for text generation.
Requires an Anthropic API key.
"""

from __future__ import annotations

from typing import Optional
import requests
import logging

from core.result import Result, Ok, Err
from data_sources.ai.base_ai_client import BaseAIClient, AIResponse

logger = logging.getLogger(__name__)

# Claude API endpoint
CLAUDE_API_BASE = "https://api.anthropic.com/v1"
DEFAULT_MODEL = "claude-3-haiku-20240307"
API_VERSION = "2023-06-01"


class ClaudeClient(BaseAIClient):
    """Anthropic Claude API client.

    Uses Claude 3 Haiku by default (fastest and most cost-effective).

    Example:
        >>> client = ClaudeClient(api_key="your-api-key")
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
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key.
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
            model: Model to use (default: claude-3-haiku).
        """
        super().__init__(api_key, timeout, max_tokens)
        self._model = model
        self._session = requests.Session()
        self._session.headers.update({
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        })

    @property
    def provider_name(self) -> str:
        return "claude"

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Result[AIResponse, str]:
        """Send a prompt to Claude and get a response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction for context.

        Returns:
            Result containing AIResponse on success, error message on failure.
        """
        if not self.is_configured():
            return Err("Claude API key not configured")

        self._log_request(prompt)

        try:
            # Build request payload
            payload = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            }

            if system_prompt:
                payload["system"] = system_prompt

            # Make request
            url = f"{CLAUDE_API_BASE}/messages"
            response = self._session.post(
                url,
                json=payload,
                timeout=self._timeout,
            )

            # Handle errors
            if response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Bad request")
                self._log_error(f"Bad request: {error_msg}")
                return Err(f"Claude error: {error_msg}")

            if response.status_code == 401:
                self._log_error("Invalid API key")
                return Err("Invalid Claude API key")

            if response.status_code == 429:
                self._log_error("Rate limit exceeded")
                return Err("Claude rate limit exceeded. Please try again later.")

            if response.status_code >= 500:
                self._log_error(f"Server error: {response.status_code}")
                return Err(f"Claude server error ({response.status_code})")

            if not response.ok:
                self._log_error(f"HTTP {response.status_code}: {response.text[:200]}")
                return Err(f"Claude request failed: HTTP {response.status_code}")

            # Parse response
            data = response.json()

            # Extract text from response
            content_blocks = data.get("content", [])
            if not content_blocks:
                self._log_error("No content in response")
                return Err("Claude returned no response")

            # Get text from first text block
            text = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text = block.get("text", "")
                    break

            if not text:
                self._log_error("Empty text in response")
                return Err("Claude returned empty text")

            # Get token usage
            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens

            ai_response = AIResponse(
                content=text,
                model=data.get("model", self._model),
                tokens_used=total_tokens,
                provider=self.provider_name,
            )

            self._log_response(ai_response)
            return Ok(ai_response)

        except requests.Timeout:
            self._log_error("Request timed out")
            return Err(f"Claude request timed out after {self._timeout}s")
        except requests.RequestException as e:
            self._log_error(f"Request failed: {e}")
            return Err(f"Claude request failed: {e}")
        except (KeyError, ValueError) as e:
            self._log_error(f"Failed to parse response: {e}")
            return Err(f"Failed to parse Claude response: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
