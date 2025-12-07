"""
Integration tests for AI provider connectivity.

Run with: pytest tests/integration/test_ai_connectivity.py -v -s

These tests make real API calls to verify connectivity with configured providers.
They will be skipped if the corresponding API key is not configured.
"""

import pytest
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import Config
from data_sources.ai import create_ai_client, SUPPORTED_PROVIDERS, is_local_provider


# Simple test prompt
TEST_PROMPT = "Say 'hello' in one word."


@pytest.fixture(scope="module")
def config():
    """Load the user's config for API keys."""
    return Config()


class TestAIConnectivity:
    """Test connectivity to all configured AI providers."""

    def test_gemini_connectivity(self, config):
        """Test Gemini API connectivity."""
        api_key = config.get_ai_api_key("gemini")
        if not api_key:
            pytest.skip("Gemini API key not configured")

        client = create_ai_client("gemini", api_key)
        assert client is not None
        assert client.is_configured()

        result = client.complete(TEST_PROMPT)
        client.close()

        assert result.is_ok(), f"Gemini failed: {result.error if hasattr(result, 'error') else 'unknown'}"
        response = result.unwrap()
        assert response.content, "Empty response from Gemini"
        assert response.provider == "gemini"
        print(f"\n[OK] Gemini: '{response.content.strip()}' ({response.tokens_used} tokens)")

    def test_claude_connectivity(self, config):
        """Test Claude API connectivity."""
        api_key = config.get_ai_api_key("claude")
        if not api_key:
            pytest.skip("Claude API key not configured")

        client = create_ai_client("claude", api_key)
        assert client is not None
        assert client.is_configured()

        result = client.complete(TEST_PROMPT)
        client.close()

        assert result.is_ok(), f"Claude failed: {result.error if hasattr(result, 'error') else 'unknown'}"
        response = result.unwrap()
        assert response.content, "Empty response from Claude"
        assert response.provider == "claude"
        print(f"\n[OK] Claude: '{response.content.strip()}' ({response.tokens_used} tokens)")

    def test_openai_connectivity(self, config):
        """Test OpenAI API connectivity."""
        api_key = config.get_ai_api_key("openai")
        if not api_key:
            pytest.skip("OpenAI API key not configured")

        client = create_ai_client("openai", api_key)
        assert client is not None
        assert client.is_configured()

        result = client.complete(TEST_PROMPT)
        client.close()

        assert result.is_ok(), f"OpenAI failed: {result.error if hasattr(result, 'error') else 'unknown'}"
        response = result.unwrap()
        assert response.content, "Empty response from OpenAI"
        assert response.provider == "openai"
        print(f"\n[OK] OpenAI: '{response.content.strip()}' ({response.tokens_used} tokens)")

    def test_groq_connectivity(self, config):
        """Test Groq API connectivity."""
        api_key = config.get_ai_api_key("groq")
        if not api_key:
            pytest.skip("Groq API key not configured")

        client = create_ai_client("groq", api_key)
        assert client is not None
        assert client.is_configured()

        result = client.complete(TEST_PROMPT)
        client.close()

        assert result.is_ok(), f"Groq failed: {result.error if hasattr(result, 'error') else 'unknown'}"
        response = result.unwrap()
        assert response.content, "Empty response from Groq"
        assert response.provider == "groq"
        print(f"\n[OK] Groq: '{response.content.strip()}' ({response.tokens_used} tokens)")

    def test_xai_connectivity(self, config):
        """Test xAI Grok API connectivity."""
        api_key = config.get_ai_api_key("xai")
        if not api_key:
            pytest.skip("xAI API key not configured")

        client = create_ai_client("xai", api_key)
        assert client is not None
        assert client.is_configured()

        result = client.complete(TEST_PROMPT)
        client.close()

        assert result.is_ok(), f"xAI failed: {result.error if hasattr(result, 'error') else 'unknown'}"
        response = result.unwrap()
        assert response.content, "Empty response from xAI"
        assert response.provider == "xai"
        print(f"\n[OK] xAI: '{response.content.strip()}' ({response.tokens_used} tokens)")

    def test_ollama_connectivity(self, config):
        """Test Ollama local connectivity."""
        client = create_ai_client(
            "ollama",
            api_key="",
            ollama_host=config.ollama_host,
            ollama_model=config.ollama_model,
        )
        assert client is not None

        if not client.is_configured():
            pytest.skip("Ollama server not running")

        # Use longer timeout for large models
        client._timeout = 180

        result = client.complete(TEST_PROMPT)
        client.close()

        assert result.is_ok(), f"Ollama failed: {result.error if hasattr(result, 'error') else 'unknown'}"
        response = result.unwrap()
        assert response.content, "Empty response from Ollama"
        assert response.provider == "ollama"
        print(f"\n[OK] Ollama ({config.ollama_model}): '{response.content.strip()[:50]}' ({response.tokens_used} tokens)")


class TestAllConfiguredProviders:
    """Summary test that checks all configured providers."""

    def test_all_configured_providers(self, config):
        """Test all providers that have keys configured."""
        results = {}

        for provider in SUPPORTED_PROVIDERS:
            if is_local_provider(provider):
                # Ollama - check if server is running
                client = create_ai_client(
                    provider,
                    api_key="",
                    ollama_host=config.ollama_host,
                    ollama_model=config.ollama_model,
                )
                if client and client.is_configured():
                    client._timeout = 180  # Longer timeout for large models
                    result = client.complete(TEST_PROMPT)
                    client.close()
                    if result.is_ok():
                        results[provider] = ("OK", result.unwrap().content.strip()[:30])
                    else:
                        results[provider] = ("FAIL", str(result.error)[:50])
                else:
                    results[provider] = ("SKIP", "Server not running")
            else:
                # Cloud provider - check if key is configured
                api_key = config.get_ai_api_key(provider)
                if api_key:
                    client = create_ai_client(provider, api_key)
                    if client:
                        result = client.complete(TEST_PROMPT)
                        client.close()
                        if result.is_ok():
                            results[provider] = ("OK", result.unwrap().content.strip()[:30])
                        else:
                            results[provider] = ("FAIL", str(result.error)[:50])
                else:
                    results[provider] = ("SKIP", "No API key")

        # Print summary
        print("\n" + "=" * 60)
        print("AI Provider Connectivity Summary")
        print("=" * 60)

        passed = 0
        failed = 0
        skipped = 0

        for provider, (status, message) in results.items():
            print(f"  [{status:4}] {provider:10} : {message}")
            if status == "OK":
                passed += 1
            elif status == "FAIL":
                failed += 1
            else:
                skipped += 1

        print("=" * 60)
        print(f"  Passed: {passed}, Failed: {failed}, Skipped: {skipped}")
        print("=" * 60)

        # Fail if any configured provider failed
        assert failed == 0, f"{failed} provider(s) failed connectivity test"


if __name__ == "__main__":
    # Allow running directly: python tests/integration/test_ai_connectivity.py
    pytest.main([__file__, "-v", "-s"])
