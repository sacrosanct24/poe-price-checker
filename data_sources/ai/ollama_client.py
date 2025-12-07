"""
Ollama AI client implementation.

Connects to a local Ollama instance for running open-source LLMs.
No API key required - runs entirely locally.

Recommended models:
- llama3.1:8b (good balance of speed/quality)
- mistral:7b (fast, capable)
- phi3:medium (strong reasoning)
- qwen2.5:14b (excellent quality)
- llama3.1:70b (near GPT-4 quality, needs 48GB+ RAM)
"""

from __future__ import annotations

from typing import Optional
import requests
import logging

from core.result import Result, Ok, Err
from data_sources.ai.base_ai_client import BaseAIClient, AIResponse

logger = logging.getLogger(__name__)

# Default Ollama endpoint (can be overridden)
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "deepseek-r1:14b"

# Recommended models with descriptions
OLLAMA_MODELS = {
    "deepseek-r1:8b": "DeepSeek R1 8B - Best reasoning, 8GB RAM",
    "deepseek-r1:14b": "DeepSeek R1 14B - Excellent reasoning, 16GB RAM",
    "deepseek-r1:32b": "DeepSeek R1 32B - Strong reasoning, 32GB RAM",
    "deepseek-r1:70b": "DeepSeek R1 70B - Near GPT-4, 64GB+ RAM",
    "qwen2.5:14b": "Qwen 2.5 14B - Fast & capable, 16GB RAM",
    "qwen2.5:32b": "Qwen 2.5 32B - Great quality, 32GB RAM",
    "qwen2.5:72b": "Qwen 2.5 72B - Excellent, 64GB+ RAM",
    "llama3.3:70b": "Llama 3.3 70B - Meta's best, 64GB+ RAM",
    "gemma3:27b": "Gemma 3 27B - Google's best local, 32GB RAM",
    "mistral:7b": "Mistral 7B - Fast and capable, 8GB RAM",
}


class OllamaClient(BaseAIClient):
    """Ollama client for local LLM inference.

    Connects to a local Ollama instance. No API key required.
    Great for privacy, no rate limits, and can use RAG.

    Example:
        >>> client = OllamaClient()  # No API key needed
        >>> if client.is_configured():  # Checks if Ollama is running
        ...     result = client.complete("Tell me about this item")
        ...     if result.is_ok():
        ...         print(result.unwrap().content)

    To install Ollama:
        1. Download from https://ollama.ai
        2. Run: ollama pull llama3.1:8b
        3. Ollama server starts automatically
    """

    def __init__(
        self,
        api_key: str = "",  # Not used, kept for interface compatibility
        timeout: int = 120,  # Longer timeout for local inference
        max_tokens: int = 500,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_OLLAMA_HOST,
    ):
        """Initialize Ollama client.

        Args:
            api_key: Ignored (Ollama doesn't require auth).
            timeout: Request timeout in seconds (default 120 for local).
            max_tokens: Maximum tokens in response.
            model: Model to use (default: llama3.1:8b).
            host: Ollama server URL (default: http://localhost:11434).
        """
        super().__init__(api_key, timeout, max_tokens)
        self._model = model
        self._host = host.rstrip("/")
        self._session = requests.Session()
        self._available: Optional[bool] = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_configured(self) -> bool:
        """Check if Ollama is available and running.

        Returns:
            True if Ollama server is responding.
        """
        if self._available is not None:
            return self._available

        try:
            response = self._session.get(
                f"{self._host}/api/tags",
                timeout=5,
            )
            self._available = response.ok
            if self._available:
                logger.debug("Ollama server is available")
            return self._available
        except requests.RequestException:
            self._available = False
            logger.debug("Ollama server not available")
            return False

    def list_models(self) -> Result[list[str], str]:
        """List available models on the Ollama server.

        Returns:
            Result containing list of model names, or error message.
        """
        try:
            response = self._session.get(
                f"{self._host}/api/tags",
                timeout=10,
            )
            if not response.ok:
                return Err(f"Failed to list models: HTTP {response.status_code}")

            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return Ok(models)
        except requests.RequestException as e:
            return Err(f"Failed to connect to Ollama: {e}")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Result[AIResponse, str]:
        """Send a prompt to Ollama and get a response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction for context.

        Returns:
            Result containing AIResponse on success, error message on failure.
        """
        if not self.is_configured():
            return Err(
                "Ollama not available. Please ensure Ollama is installed and running.\n"
                "Install from: https://ollama.ai"
            )

        self._log_request(prompt)

        try:
            # Build payload
            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": False,  # Get full response at once
                "options": {
                    "num_predict": self._max_tokens,
                    "temperature": 0.7,
                },
            }

            if system_prompt:
                payload["system"] = system_prompt

            # Make request
            url = f"{self._host}/api/generate"
            response = self._session.post(
                url,
                json=payload,
                timeout=self._timeout,
            )

            # Handle errors
            if response.status_code == 404:
                self._log_error(f"Model not found: {self._model}")
                return Err(
                    f"Model '{self._model}' not found. "
                    f"Run: ollama pull {self._model}"
                )

            if not response.ok:
                error_text = response.text[:200]
                self._log_error(f"HTTP {response.status_code}: {error_text}")
                return Err(f"Ollama error: {error_text}")

            # Parse response
            data = response.json()

            text = data.get("response", "")
            if not text:
                self._log_error("Empty response")
                return Err("Ollama returned empty response")

            # Get token counts
            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)
            total_tokens = eval_count + prompt_eval_count

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
            return Err(
                f"Ollama request timed out after {self._timeout}s. "
                "Local inference may need more time."
            )
        except requests.RequestException as e:
            self._log_error(f"Request failed: {e}")
            return Err(f"Ollama connection failed: {e}")
        except (KeyError, ValueError) as e:
            self._log_error(f"Failed to parse response: {e}")
            return Err(f"Failed to parse Ollama response: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
