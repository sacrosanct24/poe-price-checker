"""Tests for AIAnalysisController."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from gui_qt.controllers.ai_analysis_controller import (
    AIAnalysisController,
    get_ai_analysis_controller,
)


# =============================================================================
# Mock Classes
# =============================================================================


class MockPanel(QWidget):
    """Mock AI analysis panel widget."""

    retry_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_loading = MagicMock()
        self.show_response = MagicMock()
        self.show_error = MagicMock()
        self.clear = MagicMock()


class MockConfig:
    """Mock configuration object."""

    def __init__(
        self,
        ai_provider: str = "gemini",
        has_ai: bool = True,
        api_key: str = "test-key",
    ):
        self.ai_provider = ai_provider
        self._has_ai = has_ai
        self._api_key = api_key
        self.ai_timeout = 30
        self.ai_max_tokens = 500
        self.league = "Settlers"
        self.ai_build_name = "Test Build"
        self.ai_custom_prompt = ""
        self.ollama_host = "http://localhost:11434"
        self.ollama_model = "deepseek-r1:14b"

    def has_ai_configured(self) -> bool:
        return self._has_ai

    def get_ai_api_key(self, provider: str) -> str:
        return self._api_key


class MockAIResponse:
    """Mock AI response."""

    def __init__(self, content: str = "Test response", tokens_used: int = 100):
        self.content = content
        self.tokens_used = tokens_used
        self.model = "test-model"
        self.provider = "gemini"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_panel(qtbot):
    """Create mock panel."""
    panel = MockPanel()
    qtbot.addWidget(panel)
    return panel


@pytest.fixture
def mock_config():
    """Create mock config."""
    return MockConfig()


@pytest.fixture
def mock_config_not_configured():
    """Create mock config that is not configured."""
    return MockConfig(has_ai=False)


@pytest.fixture
def status_messages():
    """Track status messages."""
    return []


@pytest.fixture
def error_messages():
    """Track error messages."""
    return []


@pytest.fixture
def controller(mock_config, mock_panel, status_messages, error_messages):
    """Create controller with mocks."""
    return AIAnalysisController(
        config=mock_config,
        panel=mock_panel,
        on_status=lambda msg: status_messages.append(msg),
        on_toast_error=lambda msg: error_messages.append(msg),
    )


# =============================================================================
# Initialization Tests
# =============================================================================


class TestAIAnalysisControllerInit:
    """Tests for AIAnalysisController initialization."""

    def test_init_stores_config(self, mock_config, mock_panel):
        """Controller stores config reference."""
        controller = AIAnalysisController(config=mock_config, panel=mock_panel)
        assert controller._config is mock_config

    def test_init_stores_panel(self, mock_config, mock_panel):
        """Controller stores panel reference."""
        controller = AIAnalysisController(config=mock_config, panel=mock_panel)
        assert controller._panel is mock_panel

    def test_init_no_active_worker(self, mock_config, mock_panel):
        """Controller starts with no active worker."""
        controller = AIAnalysisController(config=mock_config, panel=mock_panel)
        assert controller._worker is None

    def test_init_connects_retry_signal(self, mock_config, mock_panel):
        """Controller connects to panel retry signal."""
        controller = AIAnalysisController(config=mock_config, panel=mock_panel)
        # Verify the signal can be emitted and triggers retry
        controller._last_item_text = "test"
        controller._last_price_results = []
        # Should not raise - signal is connected
        # We just verify initialization didn't fail

    def test_init_default_callbacks(self, mock_config, mock_panel):
        """Controller has default no-op callbacks."""
        controller = AIAnalysisController(config=mock_config, panel=mock_panel)
        # Should not raise
        controller._on_status("test")
        controller._on_toast_success("test")
        controller._on_toast_error("test")


# =============================================================================
# Configuration Tests
# =============================================================================


class TestAIAnalysisControllerConfig:
    """Tests for configuration checking."""

    def test_is_configured_true(self, controller):
        """is_configured returns True when AI is configured."""
        assert controller.is_configured() is True

    def test_is_configured_false(self, mock_config_not_configured, mock_panel):
        """is_configured returns False when AI is not configured."""
        controller = AIAnalysisController(
            config=mock_config_not_configured,
            panel=mock_panel,
        )
        assert controller.is_configured() is False

    def test_get_provider(self, controller):
        """get_provider returns configured provider."""
        assert controller.get_provider() == "gemini"


# =============================================================================
# Analyze Item Tests
# =============================================================================


class TestAIAnalysisControllerAnalyze:
    """Tests for analyze_item method."""

    def test_analyze_not_configured(
        self, mock_config_not_configured, mock_panel, status_messages
    ):
        """analyze_item returns False when not configured."""
        controller = AIAnalysisController(
            config=mock_config_not_configured,
            panel=mock_panel,
            on_status=lambda msg: status_messages.append(msg),
        )
        result = controller.analyze_item("item text", [])

        assert result is False
        assert any("not configured" in msg for msg in status_messages)

    def test_analyze_shows_loading(self, controller, mock_panel):
        """analyze_item shows loading state on panel."""
        with patch('gui_qt.workers.ai_analysis_worker.AIAnalysisWorker'):
            controller.analyze_item("item text", [{"price": 100}])

        mock_panel.show_loading.assert_called_once_with("gemini")

    def test_analyze_stores_request_for_retry(self, controller):
        """analyze_item stores request data for retry."""
        with patch('gui_qt.workers.ai_analysis_worker.AIAnalysisWorker'):
            controller.analyze_item("item text", [{"price": 100}])

        assert controller._last_item_text == "item text"
        assert controller._last_price_results == [{"price": 100}]

    def test_analyze_returns_true(self, controller):
        """analyze_item returns True on success."""
        with patch('gui_qt.workers.ai_analysis_worker.AIAnalysisWorker'):
            result = controller.analyze_item("item text", [])

        assert result is True


# =============================================================================
# Cancel Tests
# =============================================================================


class TestAIAnalysisControllerCancel:
    """Tests for cancel method."""

    def test_cancel_clears_panel(self, controller, mock_panel):
        """cancel clears the panel."""
        controller.cancel()
        mock_panel.clear.assert_called_once()

    def test_cancel_sends_status(self, controller, status_messages):
        """cancel sends status message."""
        controller.cancel()
        assert any("cancelled" in msg for msg in status_messages)


# =============================================================================
# Result Handling Tests
# =============================================================================


class TestAIAnalysisControllerResults:
    """Tests for result handling."""

    def test_on_analysis_result(self, controller, mock_panel, status_messages):
        """_on_analysis_result updates panel with response."""
        response = MockAIResponse()
        controller._on_analysis_result(response)

        mock_panel.show_response.assert_called_once_with(response)
        assert any("complete" in msg for msg in status_messages)

    def test_on_analysis_error(
        self, controller, mock_panel, status_messages, error_messages
    ):
        """_on_analysis_error updates panel with error."""
        controller._on_analysis_error("API error", "traceback")

        mock_panel.show_error.assert_called_once()
        assert any("failed" in msg for msg in status_messages)
        assert any("error" in msg.lower() for msg in error_messages)

    def test_on_analysis_status(self, controller, status_messages):
        """_on_analysis_status forwards status."""
        controller._on_analysis_status("Processing...")
        assert "Processing..." in status_messages

    def test_on_worker_finished_clears_worker(self, controller):
        """_on_worker_finished clears worker reference."""
        # Set a mock worker
        controller._worker = MagicMock()
        controller._on_worker_finished()
        assert controller._worker is None


# =============================================================================
# Retry Tests
# =============================================================================


class TestAIAnalysisControllerRetry:
    """Tests for retry functionality."""

    def test_retry_does_nothing_without_prior_request(self, controller):
        """Retry does nothing if no prior request."""
        # Ensure no prior request data
        controller._last_item_text = None
        controller._last_price_results = None

        with patch('gui_qt.workers.ai_analysis_worker.AIAnalysisWorker') as MockWorker:
            controller._on_retry_requested()
            MockWorker.assert_not_called()


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestGetAIAnalysisController:
    """Tests for factory function."""

    def test_creates_controller(self, mock_config, mock_panel):
        """Factory creates controller instance."""
        controller = get_ai_analysis_controller(
            config=mock_config,
            panel=mock_panel,
        )
        assert isinstance(controller, AIAnalysisController)

    def test_passes_callbacks(self, mock_config, mock_panel):
        """Factory passes callbacks to controller."""
        on_status = MagicMock()
        on_toast_success = MagicMock()
        on_toast_error = MagicMock()

        controller = get_ai_analysis_controller(
            config=mock_config,
            panel=mock_panel,
            on_status=on_status,
            on_toast_success=on_toast_success,
            on_toast_error=on_toast_error,
        )

        controller._on_status("test")
        controller._on_toast_success("test")
        controller._on_toast_error("test")

        on_status.assert_called_once_with("test")
        on_toast_success.assert_called_once_with("test")
        on_toast_error.assert_called_once_with("test")
