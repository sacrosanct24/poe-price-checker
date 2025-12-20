"""Tests for AIAnalysisWorker."""

from unittest.mock import MagicMock, patch

from gui_qt.workers.ai_analysis_worker import AIAnalysisWorker


class TestAIAnalysisWorkerInit:
    """Tests for worker initialization."""

    def test_basic_init(self):
        """Worker initializes with basic parameters."""
        worker = AIAnalysisWorker(
            provider="gemini",
            api_key="test-key",
            item_text="Rarity: Unique\nHeadhunter",
            price_results=[{"chaos_value": 50000}],
        )

        assert worker._provider == "gemini"
        assert worker._api_key == "test-key"
        assert worker._item_text == "Rarity: Unique\nHeadhunter"
        assert worker._raw_prompt is False  # Default

    def test_raw_prompt_init(self):
        """Worker accepts raw_prompt parameter."""
        complete_prompt = "Analyze this upgrade: BEST, BETTER, GOOD..."

        worker = AIAnalysisWorker(
            provider="gemini",
            api_key="test-key",
            item_text=complete_prompt,
            price_results=[],
            raw_prompt=True,
        )

        assert worker._raw_prompt is True
        assert worker._item_text == complete_prompt


class TestRawPromptMode:
    """Tests for raw_prompt mode execution."""

    @patch("gui_qt.workers.ai_analysis_worker.create_ai_client")
    def test_raw_prompt_skips_prompt_builder(self, mock_create_client):
        """When raw_prompt=True, item_text is used directly as prompt."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_response = MagicMock()
        mock_response.content = "Analysis result"
        mock_result = MagicMock()
        mock_result.is_err.return_value = False
        mock_result.unwrap.return_value = mock_response
        mock_client.complete.return_value = mock_result
        mock_create_client.return_value = mock_client

        complete_prompt = "You are analyzing upgrades. BEST: Item A, BETTER: Item B"

        worker = AIAnalysisWorker(
            provider="gemini",
            api_key="test-key",
            item_text=complete_prompt,
            price_results=[],
            raw_prompt=True,
        )

        # Execute
        worker._execute()

        # Verify the prompt was used directly
        call_args = mock_client.complete.call_args
        assert call_args[1]["prompt"] == complete_prompt

    @patch("gui_qt.workers.ai_analysis_worker.create_ai_client")
    def test_normal_mode_uses_prompt_builder(self, mock_create_client):
        """When raw_prompt=False, prompt builder wraps item_text."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_response = MagicMock()
        mock_response.content = "Analysis result"
        mock_result = MagicMock()
        mock_result.is_err.return_value = False
        mock_result.unwrap.return_value = mock_response
        mock_client.complete.return_value = mock_result
        mock_create_client.return_value = mock_client

        item_text = "Rarity: Unique\nHeadhunter"

        worker = AIAnalysisWorker(
            provider="gemini",
            api_key="test-key",
            item_text=item_text,
            price_results=[{"chaos_value": 50000}],
            raw_prompt=False,
        )

        # Execute
        worker._execute()

        # Verify the prompt was built (not raw item_text)
        call_args = mock_client.complete.call_args
        prompt = call_args[1]["prompt"]
        # Built prompt should be longer and contain more context
        assert len(prompt) > len(item_text)
        assert item_text in prompt
