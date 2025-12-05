"""Tests for PriceCheckWorker."""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass
from PyQt6.QtCore import QThread

from gui_qt.workers.price_check_worker import PriceCheckWorker


@dataclass
class MockParsedItem:
    """Mock parsed item for testing."""

    name: str = "Test Item"
    rarity: str = "Unique"
    item_level: int = 70


@pytest.fixture
def mock_parser():
    """Create mock item parser."""
    parser = MagicMock()
    parser.parse.return_value = MockParsedItem()
    return parser


@pytest.fixture
def mock_price_service():
    """Create mock price service."""
    service = MagicMock()
    service.check_item.return_value = [
        {"item_name": "Test Item", "chaos_value": 100, "source": "poe.ninja"},
        {"item_name": "Test Item", "chaos_value": 95, "source": "poe.watch"},
    ]
    return service


@pytest.fixture
def mock_context(mock_parser, mock_price_service):
    """Create mock application context."""
    ctx = MagicMock()
    ctx.parser = mock_parser
    ctx.price_service = mock_price_service
    return ctx


@pytest.fixture
def worker(mock_context):
    """Create PriceCheckWorker with mocked context."""
    return PriceCheckWorker(mock_context, "Sample item text")


class TestPriceCheckWorkerInitialization:
    """Tests for PriceCheckWorker initialization."""

    def test_init_with_context_and_text(self, mock_context):
        """Worker initializes with context and item text."""
        worker = PriceCheckWorker(mock_context, "Test item")

        assert worker.ctx is mock_context
        assert worker.item_text == "Test item"
        assert not worker.is_cancelled

    def test_init_with_empty_text(self, mock_context):
        """Worker can be initialized with empty text."""
        worker = PriceCheckWorker(mock_context, "")

        assert worker.item_text == ""

    def test_init_with_multiline_text(self, mock_context):
        """Worker can handle multiline item text."""
        item_text = """Rarity: Unique
Item Name
--------
Some property
"""
        worker = PriceCheckWorker(mock_context, item_text)

        assert worker.item_text == item_text


class TestPriceCheckWorkerExecution:
    """Tests for PriceCheckWorker execution."""

    def test_execute_success(self, worker, mock_parser, mock_price_service):
        """_execute returns parsed item and results."""
        parsed, results = worker._execute()

        assert parsed is not None
        assert isinstance(parsed, MockParsedItem)
        assert len(results) == 2
        assert results[0]["chaos_value"] == 100
        assert results[1]["chaos_value"] == 95

    def test_execute_calls_parser(self, worker, mock_parser):
        """_execute calls parser with item text."""
        worker._execute()

        mock_parser.parse.assert_called_once_with("Sample item text")

    def test_execute_calls_price_service(self, worker, mock_price_service):
        """_execute calls price service with item text."""
        worker._execute()

        mock_price_service.check_item.assert_called_once_with("Sample item text")

    def test_execute_returns_tuple(self, worker):
        """_execute returns tuple of (parsed, results)."""
        result = worker._execute()

        assert isinstance(result, tuple)
        assert len(result) == 2


class TestPriceCheckWorkerSignals:
    """Tests for PriceCheckWorker signal emission."""

    def test_finished_signal_on_success(self, worker, qtbot):
        """finished signal emitted with results on success."""
        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        parsed, results = blocker.args[0]
        assert parsed.name == "Test Item"
        assert len(results) == 2

    def test_error_signal_on_parse_failure(self, worker, mock_parser, qtbot):
        """error signal emitted when parsing fails."""
        mock_parser.parse.return_value = None

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, traceback = blocker.args
        assert "Could not parse" in error_msg

    def test_error_signal_on_price_service_failure(
        self, worker, mock_price_service, qtbot
    ):
        """error signal emitted when price service fails."""
        mock_price_service.check_item.side_effect = Exception("API error")

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, _ = blocker.args
        assert "API error" in error_msg


class TestPriceCheckWorkerThreadCompatibility:
    """Tests verifying PriceCheckWorker is compatible with QThread usage pattern.

    These tests verify the API contract without starting real threads to avoid
    CI instability on different platforms (especially macOS). The actual business
    logic is tested in other test classes that call run() directly.
    """

    def test_can_move_to_thread(self, worker):
        """Worker can be moved to a QThread."""
        thread = QThread()
        worker.moveToThread(thread)
        assert worker.thread() is thread
        thread.deleteLater()

    def test_run_method_can_be_connected_to_started_signal(self, worker):
        """Worker's run method can be connected to thread.started signal."""
        thread = QThread()
        worker.moveToThread(thread)
        # Verify the connection is valid (would raise if incompatible)
        thread.started.connect(worker.run)
        thread.deleteLater()

    def test_worker_run_emits_finished_signal(self, worker, qtbot):
        """Worker emits finished signal when run() completes (called directly)."""
        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        parsed, results = blocker.args[0]
        assert parsed is not None
        assert len(results) == 2

    def test_worker_run_emits_error_signal_on_failure(self, worker, mock_parser, qtbot):
        """Worker emits error signal when run() fails (called directly)."""
        mock_parser.parse.side_effect = RuntimeError("Parse crash")

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, _ = blocker.args
        assert "Parse crash" in error_msg


class TestPriceCheckWorkerCancellation:
    """Tests for PriceCheckWorker cancellation."""

    def test_cancel_before_execution(self, worker):
        """Worker can be cancelled before execution."""
        worker.cancel()

        assert worker.is_cancelled
        worker.run()  # Should not execute

    def test_cancel_during_execution(self, worker, mock_parser, qtbot):
        """Worker checks cancellation before price check."""

        def cancel_worker(text):
            """Parser that cancels worker."""
            worker.cancel()
            return MockParsedItem()

        mock_parser.parse.side_effect = cancel_worker

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, _ = blocker.args
        assert "cancelled" in error_msg.lower()

    def test_cancellation_flag_check(self, worker, mock_parser):
        """Worker checks is_cancelled before expensive operation."""
        # Set up parser to return valid result
        mock_parser.parse.return_value = MockParsedItem()

        # Cancel before price check
        worker._cancelled = True

        # Should raise InterruptedError
        with pytest.raises(InterruptedError, match="cancelled"):
            worker._execute()


class TestPriceCheckWorkerErrorHandling:
    """Tests for PriceCheckWorker error handling."""

    def test_parse_returns_none(self, worker, mock_parser):
        """Raises ValueError when parser returns None."""
        mock_parser.parse.return_value = None

        with pytest.raises(ValueError, match="Could not parse"):
            worker._execute()

    def test_parser_raises_exception(self, worker, mock_parser):
        """Exception from parser propagates."""
        mock_parser.parse.side_effect = ValueError("Invalid format")

        with pytest.raises(ValueError, match="Invalid format"):
            worker._execute()

    def test_price_service_raises_exception(self, worker, mock_price_service):
        """Exception from price service propagates."""
        mock_price_service.check_item.side_effect = RuntimeError("API down")

        with pytest.raises(RuntimeError, match="API down"):
            worker._execute()

    def test_interrupted_error_on_cancellation(self, worker, mock_parser):
        """Raises InterruptedError when cancelled."""
        mock_parser.parse.return_value = MockParsedItem()
        worker.cancel()

        with pytest.raises(InterruptedError):
            worker._execute()


class TestPriceCheckWorkerWithRealData:
    """Tests with realistic data scenarios."""

    def test_unique_item_price_check(self, mock_context):
        """Price check for unique item."""
        item_text = """Rarity: Unique
Tabula Rasa
Simple Robe
--------
Sockets: W-W-W-W-W-W
"""
        mock_context.parser.parse.return_value = MockParsedItem(
            name="Tabula Rasa", rarity="Unique"
        )
        mock_context.price_service.check_item.return_value = [
            {"item_name": "Tabula Rasa", "chaos_value": 15, "source": "poe.ninja"}
        ]

        worker = PriceCheckWorker(mock_context, item_text)
        parsed, results = worker._execute()

        assert parsed.name == "Tabula Rasa"
        assert len(results) == 1
        assert results[0]["chaos_value"] == 15

    def test_rare_item_price_check(self, mock_context):
        """Price check for rare item."""
        item_text = """Rarity: Rare
Dragon Ring
Gold Ring
--------
+25 to maximum Life
"""
        mock_context.parser.parse.return_value = MockParsedItem(
            name="Dragon Ring", rarity="Rare"
        )
        mock_context.price_service.check_item.return_value = []

        worker = PriceCheckWorker(mock_context, item_text)
        parsed, results = worker._execute()

        assert parsed.name == "Dragon Ring"
        assert results == []

    def test_currency_item_price_check(self, mock_context):
        """Price check for currency item."""
        item_text = "Chaos Orb"
        mock_context.parser.parse.return_value = MockParsedItem(
            name="Chaos Orb", rarity="Currency"
        )
        mock_context.price_service.check_item.return_value = [
            {"item_name": "Chaos Orb", "chaos_value": 1.0, "source": "poe.ninja"}
        ]

        worker = PriceCheckWorker(mock_context, item_text)
        parsed, results = worker._execute()

        assert parsed.name == "Chaos Orb"
        assert results[0]["chaos_value"] == 1.0


class TestPriceCheckWorkerResultTypes:
    """Tests for different result types."""

    def test_empty_results(self, worker, mock_price_service):
        """Handles empty price results."""
        mock_price_service.check_item.return_value = []

        parsed, results = worker._execute()

        assert parsed is not None
        assert results == []

    def test_single_result(self, worker, mock_price_service):
        """Handles single price result."""
        mock_price_service.check_item.return_value = [
            {"item_name": "Test", "chaos_value": 50}
        ]

        parsed, results = worker._execute()

        assert len(results) == 1
        assert results[0]["chaos_value"] == 50

    def test_multiple_results(self, worker, mock_price_service):
        """Handles multiple price results from different sources."""
        mock_price_service.check_item.return_value = [
            {"source": "poe.ninja", "chaos_value": 100},
            {"source": "poe.watch", "chaos_value": 95},
            {"source": "trade", "chaos_value": 98},
        ]

        parsed, results = worker._execute()

        assert len(results) == 3
        assert all("chaos_value" in r for r in results)


class TestPriceCheckWorkerEdgeCases:
    """Tests for edge cases."""

    def test_whitespace_only_item_text(self, mock_context):
        """Handles whitespace-only item text."""
        worker = PriceCheckWorker(mock_context, "   \n   \t   ")

        # Parser should handle this
        mock_context.parser.parse.return_value = None

        with pytest.raises(ValueError, match="Could not parse"):
            worker._execute()

    def test_very_long_item_text(self, mock_context):
        """Handles very long item text."""
        long_text = "Item\n" + "--------\n" + "Property\n" * 1000
        worker = PriceCheckWorker(mock_context, long_text)

        mock_context.parser.parse.return_value = MockParsedItem()
        mock_context.price_service.check_item.return_value = []

        parsed, results = worker._execute()

        assert parsed is not None
        mock_context.parser.parse.assert_called_once_with(long_text)

    def test_special_characters_in_text(self, mock_context):
        """Handles special characters in item text."""
        special_text = """Rarity: Unique
Item with "quotes" and 'apostrophes'
--------
+25% to <placeholder>
"""
        worker = PriceCheckWorker(mock_context, special_text)

        mock_context.parser.parse.return_value = MockParsedItem()
        mock_context.price_service.check_item.return_value = []

        parsed, results = worker._execute()

        assert parsed is not None


class TestPriceCheckWorkerIntegration:
    """Integration-style tests for complete workflows.

    Tests call run() directly to test full workflow including signal emission.
    Real QThread usage is tested via API compatibility in ThreadCompatibility tests.
    """

    def test_complete_workflow(self, mock_context, qtbot):
        """Complete workflow from start to finish."""
        item_text = "Test Item"
        worker = PriceCheckWorker(mock_context, item_text)

        # Track results
        results_received = []

        def on_finished(result):
            results_received.append(result)

        worker.finished.connect(on_finished)

        # Execute directly (tests business logic, not thread mechanics)
        with qtbot.waitSignal(worker.finished, timeout=1000):
            worker.run()

        # Verify
        assert len(results_received) == 1
        parsed, results = results_received[0]
        assert parsed.name == "Test Item"
        assert len(results) == 2

    def test_error_workflow(self, mock_context, mock_parser, qtbot):
        """Complete error workflow from start to finish."""
        mock_parser.parse.side_effect = Exception("Parse failed")

        worker = PriceCheckWorker(mock_context, "Bad item")

        errors_received = []

        def on_error(msg, tb):
            errors_received.append((msg, tb))

        worker.error.connect(on_error)

        # Execute directly (tests business logic, not thread mechanics)
        with qtbot.waitSignal(worker.error, timeout=1000):
            worker.run()

        assert len(errors_received) == 1
        assert "Parse failed" in errors_received[0][0]
