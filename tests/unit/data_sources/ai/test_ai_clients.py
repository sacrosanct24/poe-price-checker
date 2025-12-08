"""Tests for AI client implementations (Gemini, Claude, OpenAI, Groq, Ollama)."""

import pytest
from unittest.mock import MagicMock, patch, Mock
import requests

from core.result import Ok, Err
from data_sources.ai.base_ai_client import BaseAIClient, AIResponse
from data_sources.ai.gemini_client import GeminiClient, DEFAULT_MODEL as GEMINI_DEFAULT_MODEL
from data_sources.ai.claude_client import ClaudeClient, DEFAULT_MODEL as CLAUDE_DEFAULT_MODEL
from data_sources.ai.openai_client import OpenAIClient, DEFAULT_MODEL as OPENAI_DEFAULT_MODEL
from data_sources.ai.groq_client import GroqClient, DEFAULT_MODEL as GROQ_DEFAULT_MODEL
from data_sources.ai.ollama_client import OllamaClient, DEFAULT_MODEL as OLLAMA_DEFAULT_MODEL


# =============================================================================
# AIResponse Tests
# =============================================================================


class TestAIResponse:
    """Tests for AIResponse dataclass."""

    def test_create_response(self):
        """Can create AIResponse with all fields."""
        response = AIResponse(
            content="This is a test response",
            model="test-model",
            tokens_used=100,
            provider="test-provider",
        )
        assert response.content == "This is a test response"
        assert response.model == "test-model"
        assert response.tokens_used == 100
        assert response.provider == "test-provider"

    def test_response_defaults(self):
        """AIResponse has correct defaults."""
        response = AIResponse(content="test", model="model")
        assert response.tokens_used == 0
        assert response.provider == ""

    def test_response_is_frozen(self):
        """AIResponse is immutable."""
        response = AIResponse(content="test", model="model")
        with pytest.raises(AttributeError):
            response.content = "changed"


# =============================================================================
# BaseAIClient Tests
# =============================================================================


class TestBaseAIClient:
    """Tests for BaseAIClient base class."""

    def test_is_configured_with_key(self):
        """is_configured returns True with valid API key."""
        # Create a concrete implementation for testing
        class TestClient(BaseAIClient):
            @property
            def provider_name(self) -> str:
                return "test"

            def complete(self, prompt, system_prompt=None):
                return Ok(AIResponse(content="", model=""))

        client = TestClient(api_key="valid-key")
        assert client.is_configured() is True

    def test_is_configured_without_key(self):
        """is_configured returns False without API key."""
        class TestClient(BaseAIClient):
            @property
            def provider_name(self) -> str:
                return "test"

            def complete(self, prompt, system_prompt=None):
                return Ok(AIResponse(content="", model=""))

        client = TestClient(api_key="")
        assert client.is_configured() is False

    def test_is_configured_whitespace_key(self):
        """is_configured returns False with whitespace-only key."""
        class TestClient(BaseAIClient):
            @property
            def provider_name(self) -> str:
                return "test"

            def complete(self, prompt, system_prompt=None):
                return Ok(AIResponse(content="", model=""))

        client = TestClient(api_key="   ")
        assert client.is_configured() is False


# =============================================================================
# GeminiClient Tests
# =============================================================================


class TestGeminiClientInit:
    """Tests for GeminiClient initialization."""

    def test_init_with_key(self):
        """Can initialize with API key."""
        client = GeminiClient(api_key="test-key")
        assert client.is_configured() is True

    def test_init_default_model(self):
        """Uses default model if not specified."""
        client = GeminiClient(api_key="test-key")
        assert client._model == GEMINI_DEFAULT_MODEL

    def test_init_custom_model(self):
        """Can specify custom model."""
        client = GeminiClient(api_key="test-key", model="gemini-pro")
        assert client._model == "gemini-pro"

    def test_provider_name(self):
        """Provider name is 'gemini'."""
        client = GeminiClient(api_key="test-key")
        assert client.provider_name == "gemini"


class TestGeminiClientComplete:
    """Tests for GeminiClient.complete() method."""

    def test_complete_not_configured(self):
        """Returns error if not configured."""
        client = GeminiClient(api_key="")
        result = client.complete("test prompt")

        assert result.is_err()
        assert "not configured" in result.error

    def test_complete_success(self):
        """Successful completion returns AIResponse."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "This is the response"}]}}
            ],
            "usageMetadata": {"totalTokenCount": 50},
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "This is the response"
        assert response.tokens_used == 50
        assert response.provider == "gemini"

    def test_complete_with_system_prompt(self):
        """Can include system prompt."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "Response"}]}}
            ],
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            client.complete("prompt", system_prompt="You are a helper")

            # Verify system instruction was included
            call_args = mock_post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert "systemInstruction" in payload

    def test_complete_400_error(self):
        """Handles 400 bad request error."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Bad request message"}
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "Bad request" in result.error

    def test_complete_401_error(self):
        """Handles 401 unauthorized error."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "Invalid" in result.error and "API key" in result.error

    def test_complete_429_rate_limit(self):
        """Handles 429 rate limit error."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "rate limit" in result.error.lower()

    def test_complete_500_error(self):
        """Handles 500 server error."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "server error" in result.error.lower()

    def test_complete_timeout(self):
        """Handles request timeout."""
        client = GeminiClient(api_key="test-key", timeout=5)

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_complete_network_error(self):
        """Handles network errors."""
        client = GeminiClient(api_key="test-key")

        with patch.object(client._session, 'post', side_effect=requests.RequestException("Network error")):
            result = client.complete("test")

        assert result.is_err()
        assert "failed" in result.error.lower()

    def test_complete_empty_response(self):
        """Handles empty response from API."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"candidates": []}

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "no response" in result.error.lower()

    def test_close(self):
        """close() closes the session."""
        client = GeminiClient(api_key="test-key")
        with patch.object(client._session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()


# =============================================================================
# ClaudeClient Tests
# =============================================================================


class TestClaudeClientInit:
    """Tests for ClaudeClient initialization."""

    def test_init_with_key(self):
        """Can initialize with API key."""
        client = ClaudeClient(api_key="test-key")
        assert client.is_configured() is True

    def test_init_default_model(self):
        """Uses default model if not specified."""
        client = ClaudeClient(api_key="test-key")
        assert client._model == CLAUDE_DEFAULT_MODEL

    def test_init_custom_model(self):
        """Can specify custom model."""
        client = ClaudeClient(api_key="test-key", model="claude-3-opus-20240229")
        assert client._model == "claude-3-opus-20240229"

    def test_provider_name(self):
        """Provider name is 'claude'."""
        client = ClaudeClient(api_key="test-key")
        assert client.provider_name == "claude"

    def test_session_headers(self):
        """Session has correct headers."""
        client = ClaudeClient(api_key="test-api-key")
        assert client._session.headers["x-api-key"] == "test-api-key"
        assert "anthropic-version" in client._session.headers


class TestClaudeClientComplete:
    """Tests for ClaudeClient.complete() method."""

    def test_complete_not_configured(self):
        """Returns error if not configured."""
        client = ClaudeClient(api_key="")
        result = client.complete("test prompt")

        assert result.is_err()
        assert "not configured" in result.error

    def test_complete_success(self):
        """Successful completion returns AIResponse."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "This is Claude's response"}],
            "model": "claude-3-haiku-20240307",
            "usage": {"input_tokens": 20, "output_tokens": 30},
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "This is Claude's response"
        assert response.tokens_used == 50  # 20 + 30
        assert response.provider == "claude"

    def test_complete_with_system_prompt(self):
        """Can include system prompt."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response"}],
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            client.complete("prompt", system_prompt="You are a helper")

            call_args = mock_post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload.get("system") == "You are a helper"

    def test_complete_400_error(self):
        """Handles 400 bad request error."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Bad request"}
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "error" in result.error.lower()

    def test_complete_401_error(self):
        """Handles 401 unauthorized error."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "Invalid" in result.error

    def test_complete_429_rate_limit(self):
        """Handles 429 rate limit error."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "rate limit" in result.error.lower()

    def test_complete_500_error(self):
        """Handles 500 server error."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "server error" in result.error.lower()

    def test_complete_timeout(self):
        """Handles request timeout."""
        client = ClaudeClient(api_key="test-key", timeout=5)

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_complete_empty_content(self):
        """Handles empty content in response."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": []}

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "no response" in result.error.lower()

    def test_close(self):
        """close() closes the session."""
        client = ClaudeClient(api_key="test-key")
        with patch.object(client._session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()


# =============================================================================
# OpenAIClient Tests
# =============================================================================


class TestOpenAIClientInit:
    """Tests for OpenAIClient initialization."""

    def test_init_with_key(self):
        """Can initialize with API key."""
        client = OpenAIClient(api_key="test-key")
        assert client.is_configured() is True

    def test_init_default_model(self):
        """Uses default model if not specified."""
        client = OpenAIClient(api_key="test-key")
        assert client._model == OPENAI_DEFAULT_MODEL

    def test_init_custom_model(self):
        """Can specify custom model."""
        client = OpenAIClient(api_key="test-key", model="gpt-4")
        assert client._model == "gpt-4"

    def test_provider_name(self):
        """Provider name is 'openai'."""
        client = OpenAIClient(api_key="test-key")
        assert client.provider_name == "openai"

    def test_session_headers(self):
        """Session has correct headers."""
        client = OpenAIClient(api_key="test-api-key")
        assert "Bearer test-api-key" in client._session.headers["Authorization"]


class TestOpenAIClientComplete:
    """Tests for OpenAIClient.complete() method."""

    def test_complete_not_configured(self):
        """Returns error if not configured."""
        client = OpenAIClient(api_key="")
        result = client.complete("test prompt")

        assert result.is_err()
        assert "not configured" in result.error

    def test_complete_success(self):
        """Successful completion returns AIResponse."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is OpenAI's response"}}
            ],
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 75},
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "This is OpenAI's response"
        assert response.tokens_used == 75
        assert response.provider == "openai"

    def test_complete_with_system_prompt(self):
        """Can include system prompt."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}],
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            client.complete("prompt", system_prompt="You are a helper")

            call_args = mock_post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            messages = payload.get("messages", [])
            assert any(m.get("role") == "system" for m in messages)

    def test_complete_400_error(self):
        """Handles 400 bad request error."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Bad request"}
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "error" in result.error.lower()

    def test_complete_401_error(self):
        """Handles 401 unauthorized error."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "Invalid" in result.error

    def test_complete_429_rate_limit(self):
        """Handles 429 rate limit error."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "rate limit" in result.error.lower()

    def test_complete_500_error(self):
        """Handles 500 server error."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "server error" in result.error.lower()

    def test_complete_timeout(self):
        """Handles request timeout."""
        client = OpenAIClient(api_key="test-key", timeout=5)

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_complete_empty_choices(self):
        """Handles empty choices in response."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "no response" in result.error.lower()

    def test_close(self):
        """close() closes the session."""
        client = OpenAIClient(api_key="test-key")
        with patch.object(client._session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()


# =============================================================================
# Cross-Client Comparison Tests
# =============================================================================


class TestClientComparison:
    """Tests to ensure consistent behavior across all clients."""

    @pytest.fixture(params=[
        (GeminiClient, "gemini"),
        (ClaudeClient, "claude"),
        (OpenAIClient, "openai"),
        (GroqClient, "groq"),
    ])
    def client_class_and_name(self, request):
        """Parametrized fixture for all cloud client types."""
        return request.param

    def test_all_clients_have_provider_name(self, client_class_and_name):
        """All clients have correct provider_name."""
        client_class, expected_name = client_class_and_name
        client = client_class(api_key="test")
        assert client.provider_name == expected_name

    def test_all_clients_check_configuration(self, client_class_and_name):
        """All clients check configuration before completing."""
        client_class, _ = client_class_and_name
        client = client_class(api_key="")
        result = client.complete("test")
        assert result.is_err()
        assert "not configured" in result.error

    def test_all_clients_handle_timeout(self, client_class_and_name):
        """All clients handle timeout consistently."""
        client_class, _ = client_class_and_name
        client = client_class(api_key="test")

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_all_clients_have_close(self, client_class_and_name):
        """All clients have close() method."""
        client_class, _ = client_class_and_name
        client = client_class(api_key="test")
        assert hasattr(client, 'close')
        assert callable(client.close)


# =============================================================================
# GroqClient Tests
# =============================================================================


class TestGroqClientInit:
    """Tests for GroqClient initialization."""

    def test_init_with_key(self):
        """Can initialize with API key."""
        client = GroqClient(api_key="test-key")
        assert client.is_configured() is True

    def test_init_default_model(self):
        """Uses default model if not specified."""
        client = GroqClient(api_key="test-key")
        assert client._model == GROQ_DEFAULT_MODEL

    def test_init_custom_model(self):
        """Can specify custom model."""
        client = GroqClient(api_key="test-key", model="llama-3.1-8b-instant")
        assert client._model == "llama-3.1-8b-instant"

    def test_provider_name(self):
        """Provider name is 'groq'."""
        client = GroqClient(api_key="test-key")
        assert client.provider_name == "groq"

    def test_session_headers(self):
        """Session has correct headers."""
        client = GroqClient(api_key="test-api-key")
        assert "Bearer test-api-key" in client._session.headers["Authorization"]


class TestGroqClientComplete:
    """Tests for GroqClient.complete() method."""

    def test_complete_not_configured(self):
        """Returns error if not configured."""
        client = GroqClient(api_key="")
        result = client.complete("test prompt")

        assert result.is_err()
        assert "not configured" in result.error

    def test_complete_success(self):
        """Successful completion returns AIResponse."""
        client = GroqClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is Groq's response"}}
            ],
            "model": "llama-3.3-70b-versatile",
            "usage": {"total_tokens": 60},
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "This is Groq's response"
        assert response.tokens_used == 60
        assert response.provider == "groq"

    def test_complete_with_system_prompt(self):
        """Can include system prompt."""
        client = GroqClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}],
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            client.complete("prompt", system_prompt="You are a helper")

            call_args = mock_post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            messages = payload.get("messages", [])
            assert any(m.get("role") == "system" for m in messages)

    def test_complete_401_error(self):
        """Handles 401 unauthorized error."""
        client = GroqClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "Invalid" in result.error

    def test_complete_429_rate_limit(self):
        """Handles 429 rate limit error."""
        client = GroqClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "rate limit" in result.error.lower()

    def test_complete_timeout(self):
        """Handles request timeout."""
        client = GroqClient(api_key="test-key", timeout=5)

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_close(self):
        """close() closes the session."""
        client = GroqClient(api_key="test-key")
        with patch.object(client._session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()


# =============================================================================
# OllamaClient Tests
# =============================================================================


class TestOllamaClientInit:
    """Tests for OllamaClient initialization."""

    def test_init_without_key(self):
        """Can initialize without API key (local provider)."""
        client = OllamaClient()
        # is_configured depends on whether the server is running
        assert client._model == OLLAMA_DEFAULT_MODEL

    def test_init_custom_model(self):
        """Can specify custom model."""
        client = OllamaClient(model="mistral:7b")
        assert client._model == "mistral:7b"

    def test_init_custom_host(self):
        """Can specify custom host."""
        client = OllamaClient(host="http://192.168.1.100:11434")
        assert client._host == "http://192.168.1.100:11434"

    def test_provider_name(self):
        """Provider name is 'ollama'."""
        client = OllamaClient()
        assert client.provider_name == "ollama"


class TestOllamaClientIsConfigured:
    """Tests for OllamaClient.is_configured()."""

    def test_is_configured_server_running(self):
        """Returns True when server is running."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.ok = True

        with patch.object(client._session, 'get', return_value=mock_response):
            assert client.is_configured() is True

    def test_is_configured_server_not_running(self):
        """Returns False when server is not running."""
        client = OllamaClient()

        with patch.object(client._session, 'get', side_effect=requests.ConnectionError):
            assert client.is_configured() is False

    def test_is_configured_caches_result(self):
        """is_configured caches the availability check."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.ok = True

        with patch.object(client._session, 'get', return_value=mock_response) as mock_get:
            # First call checks server
            result1 = client.is_configured()
            # Second call uses cache
            result2 = client.is_configured()

            assert result1 is True
            assert result2 is True
            # Should only call once due to caching
            assert mock_get.call_count == 1


class TestOllamaClientComplete:
    """Tests for OllamaClient.complete() method."""

    def test_complete_not_available(self):
        """Returns error if server not available."""
        client = OllamaClient()
        client._available = False

        result = client.complete("test prompt")

        assert result.is_err()
        assert "not available" in result.error

    def test_complete_success(self):
        """Successful completion returns AIResponse."""
        client = OllamaClient()
        client._available = True

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This is Ollama's response",
            "eval_count": 40,
            "prompt_eval_count": 20,
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "This is Ollama's response"
        assert response.tokens_used == 60  # 40 + 20
        assert response.provider == "ollama"

    def test_complete_with_system_prompt(self):
        """Can include system prompt."""
        client = OllamaClient()
        client._available = True

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Response",
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            client.complete("prompt", system_prompt="You are a helper")

            call_args = mock_post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload.get("system") == "You are a helper"

    def test_complete_model_not_found(self):
        """Handles 404 model not found error."""
        client = OllamaClient(model="nonexistent:7b")
        client._available = True

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "not found" in result.error.lower()

    def test_complete_timeout(self):
        """Handles request timeout."""
        client = OllamaClient(timeout=30)
        client._available = True

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_complete_connection_error(self):
        """Handles connection errors."""
        client = OllamaClient()
        client._available = True

        with patch.object(client._session, 'post', side_effect=requests.ConnectionError("Disconnected")):
            result = client.complete("test")

        assert result.is_err()
        assert "connection failed" in result.error.lower()

    def test_close(self):
        """close() closes the session."""
        client = OllamaClient()
        with patch.object(client._session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()


class TestOllamaClientListModels:
    """Tests for OllamaClient.list_models()."""

    def test_list_models_success(self):
        """Successfully lists available models."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "mistral:7b"},
            ]
        }

        with patch.object(client._session, 'get', return_value=mock_response):
            result = client.list_models()

        assert result.is_ok()
        models = result.unwrap()
        assert "llama3.1:8b" in models
        assert "mistral:7b" in models

    def test_list_models_connection_error(self):
        """Handles connection error when listing models."""
        client = OllamaClient()

        with patch.object(client._session, 'get', side_effect=requests.ConnectionError):
            result = client.list_models()

        assert result.is_err()
        assert "Failed to connect" in result.error


# =============================================================================
# XAIClient Tests
# =============================================================================


from data_sources.ai.xai_client import XAIClient, DEFAULT_MODEL as XAI_DEFAULT_MODEL


class TestXAIClientInit:
    """Tests for XAIClient initialization."""

    def test_init_with_key(self):
        """Can initialize with API key."""
        client = XAIClient(api_key="test-key")
        assert client.is_configured() is True

    def test_init_default_model(self):
        """Uses default model if not specified."""
        client = XAIClient(api_key="test-key")
        assert client._model == XAI_DEFAULT_MODEL

    def test_init_custom_model(self):
        """Can specify custom model."""
        client = XAIClient(api_key="test-key", model="grok-3")
        assert client._model == "grok-3"

    def test_provider_name(self):
        """Provider name is 'xai'."""
        client = XAIClient(api_key="test-key")
        assert client.provider_name == "xai"

    def test_session_headers(self):
        """Session has correct headers."""
        client = XAIClient(api_key="test-api-key")
        assert "Bearer test-api-key" in client._session.headers["Authorization"]

    def test_api_key_strips_whitespace(self):
        """API key whitespace is stripped."""
        client = XAIClient(api_key="  test-key  ")
        # The key should be stripped for configuration check
        assert client.is_configured() is True


class TestXAIClientComplete:
    """Tests for XAIClient.complete() method."""

    def test_complete_not_configured(self):
        """Returns error if not configured."""
        client = XAIClient(api_key="")
        result = client.complete("test prompt")

        assert result.is_err()
        assert "not configured" in result.error

    def test_complete_success(self):
        """Successful completion returns AIResponse."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is xAI's response"}}
            ],
            "model": "grok-4-1-fast-reasoning",
            "usage": {"total_tokens": 80},
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test prompt")

        assert result.is_ok()
        response = result.unwrap()
        assert response.content == "This is xAI's response"
        assert response.tokens_used == 80
        assert response.provider == "xai"

    def test_complete_with_system_prompt(self):
        """Can include system prompt."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}],
        }

        with patch.object(client._session, 'post', return_value=mock_response) as mock_post:
            client.complete("prompt", system_prompt="You are a helper")

            call_args = mock_post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            messages = payload.get("messages", [])
            assert any(m.get("role") == "system" for m in messages)

    def test_complete_401_error(self):
        """Handles 401 unauthorized error."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "Invalid" in result.error

    def test_complete_429_rate_limit(self):
        """Handles 429 rate limit error."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "rate limit" in result.error.lower()

    def test_complete_500_error(self):
        """Handles 500 server error."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "server error" in result.error.lower()

    def test_complete_400_error(self):
        """Handles 400 bad request error."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Bad request"}
        }
        mock_response.text = "Bad request text"

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "error" in result.error.lower()

    def test_complete_timeout(self):
        """Handles request timeout."""
        client = XAIClient(api_key="test-key", timeout=5)

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_complete_network_error(self):
        """Handles network errors."""
        client = XAIClient(api_key="test-key")

        with patch.object(client._session, 'post', side_effect=requests.RequestException("Network error")):
            result = client.complete("test")

        assert result.is_err()
        assert "failed" in result.error.lower()

    def test_complete_empty_choices(self):
        """Handles empty choices in response."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "no response" in result.error.lower()

    def test_complete_empty_content(self):
        """Handles empty content in response."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}],
        }

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "empty response" in result.error.lower()

    def test_complete_parse_error(self):
        """Handles JSON parsing errors."""
        client = XAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch.object(client._session, 'post', return_value=mock_response):
            result = client.complete("test")

        assert result.is_err()
        assert "parse" in result.error.lower()

    def test_close(self):
        """close() closes the session."""
        client = XAIClient(api_key="test-key")
        with patch.object(client._session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()


# =============================================================================
# Factory Function Tests
# =============================================================================


from data_sources.ai import (
    create_ai_client,
    get_provider_display_name,
    is_local_provider,
    SUPPORTED_PROVIDERS,
)


class TestCreateAIClient:
    """Tests for create_ai_client factory function."""

    def test_create_gemini_client(self):
        """Creates GeminiClient for 'gemini' provider."""
        client = create_ai_client("gemini", api_key="test-key")
        assert client is not None
        assert isinstance(client, GeminiClient)
        assert client.provider_name == "gemini"

    def test_create_claude_client(self):
        """Creates ClaudeClient for 'claude' provider."""
        client = create_ai_client("claude", api_key="test-key")
        assert client is not None
        assert isinstance(client, ClaudeClient)
        assert client.provider_name == "claude"

    def test_create_openai_client(self):
        """Creates OpenAIClient for 'openai' provider."""
        client = create_ai_client("openai", api_key="test-key")
        assert client is not None
        assert isinstance(client, OpenAIClient)
        assert client.provider_name == "openai"

    def test_create_groq_client(self):
        """Creates GroqClient for 'groq' provider."""
        client = create_ai_client("groq", api_key="test-key")
        assert client is not None
        assert isinstance(client, GroqClient)
        assert client.provider_name == "groq"

    def test_create_xai_client(self):
        """Creates XAIClient for 'xai' provider."""
        client = create_ai_client("xai", api_key="test-key")
        assert client is not None
        assert isinstance(client, XAIClient)
        assert client.provider_name == "xai"

    def test_create_ollama_client(self):
        """Creates OllamaClient for 'ollama' provider."""
        client = create_ai_client("ollama")
        assert client is not None
        assert isinstance(client, OllamaClient)
        assert client.provider_name == "ollama"

    def test_create_ollama_with_custom_host(self):
        """Creates OllamaClient with custom host."""
        client = create_ai_client("ollama", ollama_host="http://192.168.1.100:11434")
        assert client is not None
        assert isinstance(client, OllamaClient)
        assert client._host == "http://192.168.1.100:11434"

    def test_create_ollama_with_custom_model(self):
        """Creates OllamaClient with custom model."""
        client = create_ai_client("ollama", ollama_model="mistral:7b")
        assert client is not None
        assert client._model == "mistral:7b"

    def test_unknown_provider_returns_none(self):
        """Returns None for unknown provider."""
        client = create_ai_client("unknown", api_key="test-key")
        assert client is None

    def test_empty_provider_returns_none(self):
        """Returns None for empty provider."""
        client = create_ai_client("", api_key="test-key")
        assert client is None

    def test_case_insensitive_provider(self):
        """Provider name is case-insensitive."""
        client1 = create_ai_client("GEMINI", api_key="test-key")
        client2 = create_ai_client("Gemini", api_key="test-key")
        client3 = create_ai_client("gemini", api_key="test-key")

        assert client1 is not None
        assert client2 is not None
        assert client3 is not None

    def test_provider_with_whitespace(self):
        """Provider name with whitespace is handled."""
        client = create_ai_client("  gemini  ", api_key="test-key")
        assert client is not None
        assert isinstance(client, GeminiClient)

    def test_custom_timeout(self):
        """Passes custom timeout to client."""
        client = create_ai_client("gemini", api_key="test-key", timeout=60)
        assert client is not None
        assert client._timeout == 60

    def test_custom_max_tokens(self):
        """Passes custom max_tokens to client."""
        client = create_ai_client("openai", api_key="test-key", max_tokens=1000)
        assert client is not None
        assert client._max_tokens == 1000


class TestGetProviderDisplayName:
    """Tests for get_provider_display_name function."""

    def test_gemini_display_name(self):
        """Returns correct display name for Gemini."""
        assert get_provider_display_name("gemini") == "Google Gemini"

    def test_claude_display_name(self):
        """Returns correct display name for Claude."""
        assert get_provider_display_name("claude") == "Anthropic Claude"

    def test_openai_display_name(self):
        """Returns correct display name for OpenAI."""
        assert get_provider_display_name("openai") == "OpenAI"

    def test_groq_display_name(self):
        """Returns correct display name for Groq."""
        assert get_provider_display_name("groq") == "Groq (Fast)"

    def test_xai_display_name(self):
        """Returns correct display name for xAI."""
        assert get_provider_display_name("xai") == "xAI Grok"

    def test_ollama_display_name(self):
        """Returns correct display name for Ollama."""
        assert get_provider_display_name("ollama") == "Ollama (Local)"

    def test_unknown_provider_titlecased(self):
        """Unknown provider returns titlecased name."""
        assert get_provider_display_name("unknown") == "Unknown"

    def test_case_insensitive(self):
        """Display name lookup is case-insensitive."""
        assert get_provider_display_name("GEMINI") == "Google Gemini"


class TestIsLocalProvider:
    """Tests for is_local_provider function."""

    def test_ollama_is_local(self):
        """Ollama is a local provider."""
        assert is_local_provider("ollama") is True

    def test_gemini_not_local(self):
        """Gemini is not a local provider."""
        assert is_local_provider("gemini") is False

    def test_claude_not_local(self):
        """Claude is not a local provider."""
        assert is_local_provider("claude") is False

    def test_openai_not_local(self):
        """OpenAI is not a local provider."""
        assert is_local_provider("openai") is False

    def test_groq_not_local(self):
        """Groq is not a local provider."""
        assert is_local_provider("groq") is False

    def test_xai_not_local(self):
        """xAI is not a local provider."""
        assert is_local_provider("xai") is False

    def test_case_insensitive(self):
        """Local provider check is case-insensitive."""
        assert is_local_provider("OLLAMA") is True


class TestSupportedProviders:
    """Tests for SUPPORTED_PROVIDERS constant."""

    def test_all_providers_included(self):
        """All expected providers are in the list."""
        expected = {"gemini", "claude", "openai", "groq", "xai", "ollama"}
        assert set(SUPPORTED_PROVIDERS) == expected

    def test_providers_count(self):
        """Correct number of providers."""
        assert len(SUPPORTED_PROVIDERS) == 6


# =============================================================================
# Extended Client Comparison Tests
# =============================================================================


class TestExtendedClientComparison:
    """Additional cross-client comparison tests including xAI."""

    @pytest.fixture(params=[
        (GeminiClient, "gemini"),
        (ClaudeClient, "claude"),
        (OpenAIClient, "openai"),
        (GroqClient, "groq"),
        (XAIClient, "xai"),
    ])
    def cloud_client_class_and_name(self, request):
        """Parametrized fixture for all cloud client types including xAI."""
        return request.param

    def test_all_cloud_clients_have_provider_name(self, cloud_client_class_and_name):
        """All cloud clients have correct provider_name."""
        client_class, expected_name = cloud_client_class_and_name
        client = client_class(api_key="test")
        assert client.provider_name == expected_name

    def test_all_cloud_clients_check_configuration(self, cloud_client_class_and_name):
        """All cloud clients check configuration before completing."""
        client_class, _ = cloud_client_class_and_name
        client = client_class(api_key="")
        result = client.complete("test")
        assert result.is_err()
        assert "not configured" in result.error

    def test_all_cloud_clients_handle_timeout(self, cloud_client_class_and_name):
        """All cloud clients handle timeout consistently."""
        client_class, _ = cloud_client_class_and_name
        client = client_class(api_key="test")

        with patch.object(client._session, 'post', side_effect=requests.Timeout):
            result = client.complete("test")

        assert result.is_err()
        assert "timed out" in result.error

    def test_all_cloud_clients_have_close(self, cloud_client_class_and_name):
        """All cloud clients have close() method."""
        client_class, _ = cloud_client_class_and_name
        client = client_class(api_key="test")
        assert hasattr(client, 'close')
        assert callable(client.close)
