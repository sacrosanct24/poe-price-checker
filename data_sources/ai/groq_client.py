"""
Groq AI client implementation.

Uses the Groq API for extremely fast inference on open models.
Free tier available with generous limits.

Supported models:
- llama-3.3-70b-versatile (best quality)
- llama-3.1-8b-instant (fastest)
- mixtral-8x7b-32768 (good balance)
- gemma2-9b-it (compact)
"""

from __future__ import annotations

from typing import Optional
import requests
import logging

from core.result import Result, Ok, Err
from data_sources.ai.base_ai_client import BaseAIClient, AIResponse

logger = logging.getLogger(__name__)

# Groq API endpoint (OpenAI-compatible)
GROQ_API_BASE = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Available models with descriptions
GROQ_MODELS = {
    "llama-3.3-70b-versatile": "Llama 3.3 70B - Best quality, good speed",
    "llama-3.1-8b-instant": "Llama 3.1 8B - Fastest responses",
    "mixtral-8x7b-32768": "Mixtral 8x7B - Good balance, 32k context",
    "gemma2-9b-it": "Gemma 2 9B - Compact and capable",
}


class GroqClient(BaseAIClient):
    """Groq API client for fast LLM inference.

    Groq offers extremely fast inference (500+ tokens/sec) on open models.
    Free tier includes 6000 requests/day with no credit card required.

    Example:
        >>> client = GroqClient(api_key="your-api-key")
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
        """Initialize Groq client.

        Args:
            api_key: Groq API key (get from console.groq.com).
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
            model: Model to use (default: llama-3.3-70b-versatile).
        """
        # Ensure the API key is clean of any whitespace/newlines from copy-pasting
        api_key = api_key.strip()

        super().__init__(api_key, timeout, max_tokens)
        self._model = model
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    @property
    def provider_name(self) -> str:
        return "groq"

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Result[AIResponse, str]:
        """Send a prompt to Groq and get a response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction for context.

        Returns:
            Result containing AIResponse on success, error message on failure.
        """
        if not self.is_configured():
            return Err("Groq API key not configured")

        self._log_request(prompt)

        try:
            # Build messages
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
            url = f"{GROQ_API_BASE}/chat/completions"
            response = self._session.post(
                url,
                json=payload,
                timeout=self._timeout,
            )

            # Handle errors
            if response.status_code == 401:
                self._log_error("Invalid API key")
                return Err("Invalid Groq API key")

            if response.status_code == 429:
                self._log_error("Rate limit exceeded")
                return Err("Groq rate limit exceeded. Please try again later.")

            if response.status_code >= 500:
                self._log_error(f"Server error: {response.status_code}")
                return Err(f"Groq server error ({response.status_code})")

            if not response.ok:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text[:200])
                self._log_error(f"HTTP {response.status_code}: {error_msg}")
                return Err(f"Groq error: {error_msg}")

            # Parse response
            data = response.json()

            choices = data.get("choices", [])
            if not choices:
                self._log_error("No choices in response")
                return Err("Groq returned no response")

            message = choices[0].get("message", {})
            text = message.get("content", "")
            if not text:
                self._log_error("Empty content in response")
                return Err("Groq returned empty response")

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
            return Err(f"Groq request timed out after {self._timeout}s")
        except requests.RequestException as e:
            self._log_error(f"Request failed: {e}")
            return Err(f"Groq request failed: {e}")
        except (KeyError, ValueError) as e:
            self._log_error(f"Failed to parse response: {e}")
            return Err(f"Failed to parse Groq response: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
