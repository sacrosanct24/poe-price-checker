"""
AI client module for LLM provider integrations.

Provides a factory function to create AI clients for different providers.

Usage:
    from data_sources.ai import create_ai_client, AIResponse

    client = create_ai_client("gemini", api_key="your-key")
    if client and client.is_configured():
        result = client.complete("Tell me about this item")
        if result.is_ok():
            response = result.unwrap()
            print(response.content)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Literal
import logging

from data_sources.ai.base_ai_client import BaseAIClient, AIResponse
from data_sources.ai.gemini_client import GeminiClient
from data_sources.ai.claude_client import ClaudeClient
from data_sources.ai.openai_client import OpenAIClient
from data_sources.ai.groq_client import GroqClient
from data_sources.ai.xai_client import XAIClient
from data_sources.ai.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# Supported provider names
AIProvider = Literal["gemini", "claude", "openai", "groq", "xai", "ollama"]

# Provider name to client class mapping
_PROVIDER_CLASSES: dict[str, type[BaseAIClient]] = {
    "gemini": GeminiClient,
    "claude": ClaudeClient,
    "openai": OpenAIClient,
    "groq": GroqClient,
    "xai": XAIClient,
    "ollama": OllamaClient,
}

# List of supported providers for UI display
SUPPORTED_PROVIDERS: list[str] = list(_PROVIDER_CLASSES.keys())


def create_ai_client(
    provider: str,
    api_key: str = "",
    timeout: int = 30,
    max_tokens: int = 500,
    ollama_host: str = "",
    ollama_model: str = "",
) -> Optional[BaseAIClient]:
    """Create an AI client for the specified provider.

    Args:
        provider: Provider name ("gemini", "claude", "openai", "groq", "ollama").
        api_key: API key for the provider (not needed for ollama).
        timeout: Request timeout in seconds.
        max_tokens: Maximum tokens in response.
        ollama_host: Ollama server URL (optional, for ollama provider).
        ollama_model: Ollama model name (optional, for ollama provider).

    Returns:
        An AI client instance, or None if provider is invalid/empty.

    Example:
        >>> client = create_ai_client("gemini", "your-api-key")
        >>> if client:
        ...     result = client.complete("Hello!")
    """
    if not provider:
        logger.debug("No AI provider specified")
        return None

    provider_lower = provider.lower().strip()
    client_class = _PROVIDER_CLASSES.get(provider_lower)

    if not client_class:
        logger.warning(f"Unknown AI provider: {provider}")
        return None

    logger.info(f"Creating AI client for provider: {provider_lower}")

    # Special handling for Ollama
    if provider_lower == "ollama":
        ollama_kwargs: Dict[str, Any] = {
            "timeout": timeout,
            "max_tokens": max_tokens,
        }
        if ollama_host:
            ollama_kwargs["host"] = ollama_host
        if ollama_model:
            ollama_kwargs["model"] = ollama_model
        return OllamaClient(**ollama_kwargs)

    return client_class(
        api_key=api_key,
        timeout=timeout,
        max_tokens=max_tokens,
    )


def get_provider_display_name(provider: str) -> str:
    """Get display name for a provider.

    Args:
        provider: Provider identifier.

    Returns:
        Human-readable provider name.
    """
    names = {
        "gemini": "Google Gemini",
        "claude": "Anthropic Claude",
        "openai": "OpenAI",
        "groq": "Groq (Fast)",
        "xai": "xAI Grok",
        "ollama": "Ollama (Local)",
    }
    return names.get(provider.lower(), provider.title())


def is_local_provider(provider: str) -> bool:
    """Check if a provider runs locally (no API key required).

    Args:
        provider: Provider identifier.

    Returns:
        True if provider runs locally.
    """
    return provider.lower() in ("ollama",)


__all__ = [
    "AIResponse",
    "AIProvider",
    "BaseAIClient",
    "ClaudeClient",
    "GeminiClient",
    "GroqClient",
    "OllamaClient",
    "OpenAIClient",
    "XAIClient",
    "SUPPORTED_PROVIDERS",
    "create_ai_client",
    "get_provider_display_name",
    "is_local_provider",
]
