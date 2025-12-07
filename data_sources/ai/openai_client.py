"""
OpenAI AI client implementation.

Uses the OpenAI Chat Completions API for text generation.
Requires an OpenAI API key.
"""

from __future__ import annotations

from typing import Optional
import requests
import logging

from core.result import Result, Ok, Err
from data_sources.ai.base_ai_client import BaseAIClient, AIResponse

logger = logging.getLogger(__name__)

# OpenAI API endpoint
OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIClient(BaseAIClient):
    """OpenAI API client.

    Uses GPT-4o-mini by default (fast and cost-effective).

    Example:
        >>> client = OpenAIClient(api_key="your-api-key")
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
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key.
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
            model: Model to use (default: gpt-4o-mini).
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
        return "openai"

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Result[AIResponse, str]:
        """Send a prompt to OpenAI and get a response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction for context.

        Returns:
            Result containing AIResponse on success, error message on failure.
        """
        if not self.is_configured():
            return Err("OpenAI API key not configured")

        self._log_request(prompt)

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Build request payload
            payload = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": messages,
                "temperature": 0.7,
            }

            # Make request
            url = f"{OPENAI_API_BASE}/chat/completions"
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
                return Err(f"OpenAI error: {error_msg}")

            if response.status_code == 401:
                self._log_error("Invalid API key")
                return Err("Invalid OpenAI API key")

            if response.status_code == 429:
                self._log_error("Rate limit exceeded")
                return Err("OpenAI rate limit exceeded. Please try again later.")

            if response.status_code >= 500:
                self._log_error(f"Server error: {response.status_code}")
                return Err(f"OpenAI server error ({response.status_code})")

            if not response.ok:
                self._log_error(f"HTTP {response.status_code}: {response.text[:200]}")
                return Err(f"OpenAI request failed: HTTP {response.status_code}")

            # Parse response
            data = response.json()

            # Extract text from response
            choices = data.get("choices", [])
            if not choices:
                self._log_error("No choices in response")
                return Err("OpenAI returned no response")

            message = choices[0].get("message", {})
            text = message.get("content", "")

            if not text:
                self._log_error("Empty content in response")
                return Err("OpenAI returned empty response")

            # Get token usage
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)

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
            return Err(f"OpenAI request timed out after {self._timeout}s")
        except requests.RequestException as e:
            self._log_error(f"Request failed: {e}")
            return Err(f"OpenAI request failed: {e}")
        except (KeyError, ValueError) as e:
            self._log_error(f"Failed to parse response: {e}")
            return Err(f"Failed to parse OpenAI response: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
