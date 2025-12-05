"""
Unit tests for AI client implementations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from data_sources.ai import (
    create_ai_client,
    AIResponse,
    BaseAIClient,
    SUPPORTED_PROVIDERS,
    get_provider_display_name,
)
from data_sources.ai.gemini_client import GeminiClient
from data_sources.ai.claude_client import ClaudeClient
from data_sources.ai.openai_client import OpenAIClient


class TestAIResponse:
    """Tests for AIResponse dataclass."""

    def test_create_response(self):
        """Test creating an AIResponse."""
        response = AIResponse(
            content="Test content",
            model="test-model",
            tokens_used=100,
            provider="test-provider",
        )
        assert response.content == "Test content"
        assert response.model == "test-model"
        assert response.tokens_used == 100
        assert response.provider == "test-provider"

    def test_default_values(self):
        """Test default values."""
        response = AIResponse(content="Test", model="model")
        assert response.tokens_used == 0
        assert response.provider == ""

    def test_immutable(self):
        """Test that AIResponse is immutable (frozen)."""
        response = AIResponse(content="Test", model="model")
        with pytest.raises(AttributeError):
            response.content = "Changed"


class TestProviderDisplayName:
    """Tests for get_provider_display_name function."""

    def test_gemini_display_name(self):
        """Test Gemini display name."""
        assert get_provider_display_name("gemini") == "Google Gemini"

    def test_claude_display_name(self):
        """Test Claude display name."""
        assert get_provider_display_name("claude") == "Anthropic Claude"

    def test_openai_display_name(self):
        """Test OpenAI display name."""
        assert get_provider_display_name("openai") == "OpenAI"

    def test_unknown_provider(self):
        """Test unknown provider returns title-cased version."""
        assert get_provider_display_name("unknown") == "Unknown"


class TestCreateAIClient:
    """Tests for create_ai_client factory function."""

    def test_create_gemini_client(self):
        """Test creating Gemini client."""
        client = create_ai_client("gemini", "test-key")
        assert isinstance(client, GeminiClient)

    def test_create_claude_client(self):
        """Test creating Claude client."""
        client = create_ai_client("claude", "test-key")
        assert isinstance(client, ClaudeClient)

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        client = create_ai_client("openai", "test-key")
        assert isinstance(client, OpenAIClient)

    def test_unknown_provider_returns_none(self):
        """Test unknown provider returns None."""
        client = create_ai_client("unknown", "test-key")
        assert client is None

    def test_empty_provider_returns_none(self):
        """Test empty provider returns None."""
        client = create_ai_client("", "test-key")
        assert client is None

    def test_custom_timeout(self):
        """Test custom timeout is passed."""
        client = create_ai_client("gemini", "test-key", timeout=60)
        assert client._timeout == 60

    def test_custom_max_tokens(self):
        """Test custom max_tokens is passed."""
        client = create_ai_client("gemini", "test-key", max_tokens=1000)
        assert client._max_tokens == 1000


class TestSupportedProviders:
    """Tests for SUPPORTED_PROVIDERS constant."""

    def test_contains_expected_providers(self):
        """Test that all expected providers are listed."""
        assert "gemini" in SUPPORTED_PROVIDERS
        assert "claude" in SUPPORTED_PROVIDERS
        assert "openai" in SUPPORTED_PROVIDERS

    def test_provider_count(self):
        """Test the number of supported providers."""
        assert len(SUPPORTED_PROVIDERS) == 3


class TestBaseAIClient:
    """Tests for BaseAIClient abstract class."""

    def test_is_configured_with_key(self):
        """Test is_configured returns True when key provided."""
        client = GeminiClient("test-key")
        assert client.is_configured() is True

    def test_is_not_configured_without_key(self):
        """Test is_configured returns False without key."""
        client = GeminiClient("")
        assert client.is_configured() is False

    def test_is_not_configured_with_none_key(self):
        """Test is_configured returns False with None key."""
        client = GeminiClient(None)
        assert client.is_configured() is False


class TestGeminiClient:
    """Tests for GeminiClient."""

    def test_init(self):
        """Test initialization."""
        client = GeminiClient("test-key", timeout=45, max_tokens=800)
        assert client._api_key == "test-key"
        assert client._timeout == 45
        assert client._max_tokens == 800

    def test_default_model(self):
        """Test default model is set."""
        client = GeminiClient("test-key")
        assert "gemini" in client._model.lower()

    def test_complete_success(self):
        """Test successful completion."""
        client = GeminiClient("test-key")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "AI response text"}]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 150
            }
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("Test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "AI response text"
        assert response.tokens_used == 150
        assert response.provider == "gemini"

    def test_complete_api_error(self):
        """Test API error handling."""
        client = GeminiClient("test-key")

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("Test prompt")

        assert result.is_err()
        # Error message mentions API key or Gemini
        assert "gemini" in result.error.lower() or "api key" in result.error.lower()


class TestClaudeClient:
    """Tests for ClaudeClient."""

    def test_init(self):
        """Test initialization."""
        client = ClaudeClient("test-key", timeout=45, max_tokens=800)
        assert client._api_key == "test-key"
        assert client._timeout == 45
        assert client._max_tokens == 800

    def test_default_model(self):
        """Test default model is set."""
        client = ClaudeClient("test-key")
        assert "claude" in client._model.lower()

    def test_complete_success(self):
        """Test successful completion."""
        client = ClaudeClient("test-key")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Claude response text"}],
            "model": "claude-3-haiku",
            "usage": {
                "input_tokens": 50,
                "output_tokens": 100
            }
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("Test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "Claude response text"
        assert response.tokens_used == 150
        assert response.provider == "claude"

    def test_complete_with_system_prompt(self):
        """Test completion with system prompt."""
        client = ClaudeClient("test-key")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response"}],
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            result = client.complete("User prompt", system_prompt="You are helpful")

            assert result.is_ok()
            # Verify system prompt was included in request
            call_args = mock_post.call_args
            assert call_args[1]["json"]["system"] == "You are helpful"


class TestOpenAIClient:
    """Tests for OpenAIClient."""

    def test_init(self):
        """Test initialization."""
        client = OpenAIClient("test-key", timeout=45, max_tokens=800)
        assert client._api_key == "test-key"
        assert client._timeout == 45
        assert client._max_tokens == 800

    def test_default_model(self):
        """Test default model is set."""
        client = OpenAIClient("test-key")
        assert "gpt" in client._model.lower()

    def test_complete_success(self):
        """Test successful completion."""
        client = OpenAIClient("test-key")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "OpenAI response text"}
            }],
            "model": "gpt-4o-mini",
            "usage": {
                "total_tokens": 200
            }
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("Test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "OpenAI response text"
        assert response.tokens_used == 200
        assert response.provider == "openai"

    def test_complete_with_system_prompt(self):
        """Test completion with system prompt."""
        client = OpenAIClient("test-key")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"total_tokens": 50}
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            result = client.complete("User prompt", system_prompt="System instructions")

            assert result.is_ok()
            # Verify system message was included
            call_args = mock_post.call_args
            messages = call_args[1]["json"]["messages"]
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "System instructions"
