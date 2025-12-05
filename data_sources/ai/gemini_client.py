"""
Google Gemini AI client implementation.

Uses the Gemini REST API for text generation.
Free tier available with rate limits.
"""

from __future__ import annotations

from typing import Optional
import requests
import logging

from core.result import Result, Ok, Err
from data_sources.ai.base_ai_client import BaseAIClient, AIResponse

logger = logging.getLogger(__name__)

# Gemini API endpoint
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-1.5-flash"


class GeminiClient(BaseAIClient):
    """Google Gemini API client.

    Uses Gemini 1.5 Flash by default (free tier available).

    Example:
        >>> client = GeminiClient(api_key="your-api-key")
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
        """Initialize Gemini client.

        Args:
            api_key: Google AI Studio API key.
            timeout: Request timeout in seconds.
            max_tokens: Maximum tokens in response.
            model: Model to use (default: gemini-1.5-flash).
        """
        super().__init__(api_key, timeout, max_tokens)
        self._model = model
        self._session = requests.Session()

    @property
    def provider_name(self) -> str:
        return "gemini"

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Result[AIResponse, str]:
        """Send a prompt to Gemini and get a response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction for context.

        Returns:
            Result containing AIResponse on success, error message on failure.
        """
        if not self.is_configured():
            return Err("Gemini API key not configured")

        self._log_request(prompt)

        try:
            # Build request payload
            contents = []

            # Add system instruction if provided
            system_instruction = None
            if system_prompt:
                system_instruction = {"parts": [{"text": system_prompt}]}

            # Add user prompt
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": self._max_tokens,
                    "temperature": 0.7,
                },
            }

            if system_instruction:
                payload["systemInstruction"] = system_instruction

            # Make request
            url = f"{GEMINI_API_BASE}/models/{self._model}:generateContent"
            response = self._session.post(
                url,
                params={"key": self._api_key},
                json=payload,
                timeout=self._timeout,
            )

            # Handle errors
            if response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Bad request")
                self._log_error(f"Bad request: {error_msg}")
                return Err(f"Gemini error: {error_msg}")

            if response.status_code == 401:
                self._log_error("Invalid API key")
                return Err("Invalid Gemini API key")

            if response.status_code == 429:
                self._log_error("Rate limit exceeded")
                return Err("Gemini rate limit exceeded. Please try again later.")

            if response.status_code >= 500:
                self._log_error(f"Server error: {response.status_code}")
                return Err(f"Gemini server error ({response.status_code})")

            if not response.ok:
                self._log_error(f"HTTP {response.status_code}: {response.text[:200]}")
                return Err(f"Gemini request failed: HTTP {response.status_code}")

            # Parse response
            data = response.json()

            # Extract text from response
            candidates = data.get("candidates", [])
            if not candidates:
                self._log_error("No candidates in response")
                return Err("Gemini returned no response")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                self._log_error("No parts in response")
                return Err("Gemini returned empty response")

            text = parts[0].get("text", "")
            if not text:
                self._log_error("Empty text in response")
                return Err("Gemini returned empty text")

            # Get token usage if available
            usage = data.get("usageMetadata", {})
            total_tokens = usage.get("totalTokenCount", 0)

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
            return Err(f"Gemini request timed out after {self._timeout}s")
        except requests.RequestException as e:
            self._log_error(f"Request failed: {e}")
            return Err(f"Gemini request failed: {e}")
        except (KeyError, ValueError) as e:
            self._log_error(f"Failed to parse response: {e}")
            return Err(f"Failed to parse Gemini response: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
