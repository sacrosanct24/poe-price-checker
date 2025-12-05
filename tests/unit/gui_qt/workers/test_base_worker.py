"""Tests for BaseWorker and BaseThreadWorker classes.

Unit tests that verify the worker logic without requiring actual thread execution.
Thread integration is tested via careful signal/slot testing without relying on
cross-thread communication which can be unstable in CI headless environments.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from PyQt6.QtCore import QThread, QObject

from gui_qt.workers.base_worker import BaseWorker, BaseThreadWorker


# Concrete implementation for testing BaseWorker
class ConcreteTestWorker(BaseWorker):
    """Concrete worker for testing."""

    def __init__(self, return_value="success", should_raise=None):
        super().__init__()
        self.return_value = return_value
        self.should_raise = should_raise
        self.execute_called = False

    def _execute(self):
        """Execute test work."""
        self.execute_called = True
        if self.should_raise:
            raise self.should_raise
        return self.return_value


# Concrete implementation for testing BaseThreadWorker
class ConcreteTestThreadWorker(BaseThreadWorker):
    """Concrete thread worker for testing."""

    def __init__(self, return_value="success", should_raise=None):
        super().__init__()
        self.return_value = return_value
        self.should_raise = should_raise
        self.execute_called = False

    def _execute(self):
        """Execute test work."""
        self.execute_called = True
        if self.should_raise:
            raise self.should_raise
        return self.return_value


class TestBaseWorkerInitialization:
    """Tests for BaseWorker initialization."""

    def test_init_with_no_parent(self):
        """Worker can be initialized without parent."""
        worker = ConcreteTestWorker()
        assert worker is not None
        assert not worker.is_cancelled

    def test_init_with_parent(self):
        """Worker can be initialized with parent."""
        parent = QObject()
        worker = ConcreteTestWorker()
        worker.setParent(parent)
        assert worker.parent() is parent

    def test_initial_cancelled_state(self):
        """Worker starts with cancelled=False."""
        worker = ConcreteTestWorker()
        assert worker._cancelled is False
        assert worker.is_cancelled is False

    def test_has_required_signals(self):
        """Worker has all required signals defined."""
        worker = ConcreteTestWorker()
        assert hasattr(worker, 'finished')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'progress')


class TestBaseWorkerCancellation:
    """Tests for BaseWorker cancellation."""

    def test_cancel_sets_flag(self):
        """cancel() sets the cancelled flag."""
        worker = ConcreteTestWorker()
        assert not worker.is_cancelled

        worker.cancel()

        assert worker.is_cancelled
        assert worker._cancelled is True

    def test_cancel_multiple_times(self):
        """Calling cancel() multiple times is safe."""
        worker = ConcreteTestWorker()

        worker.cancel()
        worker.cancel()
        worker.cancel()

        assert worker.is_cancelled

    def test_run_cancelled_before_start(self):
        """Worker doesn't execute if cancelled before run()."""
        worker = ConcreteTestWorker()
        worker.cancel()

        worker.run()

        assert not worker.execute_called

    def test_run_respects_pre_cancellation(self):
        """run() checks cancellation before executing."""
        worker = ConcreteTestWorker()
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        worker.cancel()
        worker.run()

        assert not worker.execute_called
        finished_spy.assert_not_called()


class TestBaseWorkerSignals:
    """Tests for BaseWorker signal emission."""

    def test_finished_signal_on_success(self, qtbot):
        """finished signal emitted with result on success."""
        worker = ConcreteTestWorker(return_value="test_result")

        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        assert blocker.args[0] == "test_result"

    def test_error_signal_on_exception(self, qtbot):
        """error signal emitted with message and traceback on exception."""
        worker = ConcreteTestWorker(should_raise=ValueError("Test error"))

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, traceback = blocker.args
        assert "Test error" in error_msg
        assert "ValueError" in traceback
        assert "Test error" in traceback

    def test_progress_signal_emission(self, qtbot):
        """progress signal can be emitted."""
        worker = ConcreteTestWorker()

        with qtbot.waitSignal(worker.progress, timeout=1000) as blocker:
            worker.emit_progress(50, 100)

        assert blocker.args == [50, 100]

    def test_finished_not_emitted_when_cancelled_during_execute(self, qtbot):
        """finished signal not emitted if cancelled flag set during execution."""

        class CancelDuringExecuteWorker(BaseWorker):
            def _execute(self):
                self._cancelled = True  # Simulate mid-execution cancellation
                return "should_not_emit"

        worker = CancelDuringExecuteWorker()
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        worker.run()

        # Signal should not be emitted since cancelled=True after _execute
        finished_spy.assert_not_called()

    def test_execute_called_even_when_cancelled_during(self):
        """_execute is called but result not emitted if cancelled during."""

        class TrackingWorker(BaseWorker):
            def __init__(self):
                super().__init__()
                self.executed = False

            def _execute(self):
                self.executed = True
                self._cancelled = True
                return "result"

        worker = TrackingWorker()
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        worker.run()

        assert worker.executed
        finished_spy.assert_not_called()


class TestBaseWorkerRunLogic:
    """Tests for BaseWorker.run() method logic without threads."""

    def test_run_calls_execute(self):
        """run() calls _execute() method."""
        worker = ConcreteTestWorker()

        worker.run()

        assert worker.execute_called

    def test_run_emits_finished_with_return_value(self):
        """run() emits finished signal with _execute return value."""
        worker = ConcreteTestWorker(return_value={"key": "value"})
        results = []
        worker.finished.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        assert results[0] == {"key": "value"}

    def test_run_emits_error_on_exception(self):
        """run() emits error signal when _execute raises."""
        worker = ConcreteTestWorker(should_raise=RuntimeError("Test failure"))
        errors = []
        worker.error.connect(lambda msg, tb: errors.append((msg, tb)))

        worker.run()

        assert len(errors) == 1
        assert "Test failure" in errors[0][0]
        assert "RuntimeError" in errors[0][1]

    def test_run_does_not_emit_finished_on_error(self):
        """run() does not emit finished when _execute raises."""
        worker = ConcreteTestWorker(should_raise=ValueError("Error"))
        finished_called = []
        worker.finished.connect(lambda r: finished_called.append(r))

        worker.run()

        assert len(finished_called) == 0


class TestBaseWorkerThreadCompatibility:
    """Tests verifying BaseWorker is compatible with QThread usage pattern.

    These tests verify the API contract without starting real threads.
    """

    def test_can_move_to_thread(self):
        """Worker can be moved to a QThread."""
        worker = ConcreteTestWorker()
        thread = QThread()

        worker.moveToThread(thread)

        assert worker.thread() is thread

        # Cleanup without starting
        thread.deleteLater()

    def test_run_can_be_connected_to_thread_started(self):
        """Worker.run can be connected to QThread.started signal."""
        worker = ConcreteTestWorker()
        thread = QThread()

        # This should not raise
        thread.started.connect(worker.run)

        # Cleanup
        thread.started.disconnect(worker.run)
        thread.deleteLater()

    def test_worker_signals_can_connect_to_slots(self):
        """Worker signals can be connected to arbitrary slots."""
        worker = ConcreteTestWorker()
        mock_handler = MagicMock()

        # All signals should be connectable
        worker.finished.connect(mock_handler)
        worker.error.connect(mock_handler)
        worker.progress.connect(mock_handler)

        # Emit and verify
        worker.finished.emit("result")
        worker.error.emit("msg", "tb")
        worker.progress.emit(1, 10)

        assert mock_handler.call_count == 3


class TestBaseWorkerErrorHandling:
    """Tests for BaseWorker error handling."""

    def test_handles_value_error(self, qtbot):
        """Handles ValueError correctly."""
        worker = ConcreteTestWorker(should_raise=ValueError("Invalid value"))

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        assert "Invalid value" in blocker.args[0]

    def test_handles_runtime_error(self, qtbot):
        """Handles RuntimeError correctly."""
        worker = ConcreteTestWorker(should_raise=RuntimeError("Runtime problem"))

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        assert "Runtime problem" in blocker.args[0]

    def test_handles_generic_exception(self, qtbot):
        """Handles generic Exception correctly."""
        worker = ConcreteTestWorker(should_raise=Exception("Generic error"))

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        assert "Generic error" in blocker.args[0]

    def test_traceback_includes_exception_type(self, qtbot):
        """Error traceback includes exception type."""
        worker = ConcreteTestWorker(should_raise=KeyError("missing_key"))

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        _, traceback = blocker.args
        assert "KeyError" in traceback


class TestBaseThreadWorkerInitialization:
    """Tests for BaseThreadWorker initialization."""

    def test_init_with_no_parent(self):
        """Thread worker can be initialized without parent."""
        worker = ConcreteTestThreadWorker()
        assert worker is not None
        assert not worker.is_cancelled

    def test_inherits_from_qthread(self):
        """BaseThreadWorker inherits from QThread."""
        worker = ConcreteTestThreadWorker()
        assert isinstance(worker, QThread)

    def test_initial_state(self):
        """Thread worker has correct initial state."""
        worker = ConcreteTestThreadWorker()
        assert not worker.is_cancelled
        assert not worker.isRunning()

    def test_has_required_signals(self):
        """Thread worker has all required signals defined."""
        worker = ConcreteTestThreadWorker()
        assert hasattr(worker, 'result')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'status')


class TestBaseThreadWorkerCancellation:
    """Tests for BaseThreadWorker cancellation."""

    def test_cancel_sets_flag(self):
        """cancel() sets the cancelled flag."""
        worker = ConcreteTestThreadWorker()

        worker.cancel()

        assert worker.is_cancelled

    def test_run_cancelled_before_start(self):
        """Worker doesn't execute if cancelled before run()."""
        worker = ConcreteTestThreadWorker()
        worker.cancel()

        # Call run() directly to test the logic (not via start())
        worker.run()

        assert not worker.execute_called


class TestBaseThreadWorkerRunLogic:
    """Tests for BaseThreadWorker.run() method logic.

    These test run() directly without starting the thread, verifying
    the business logic is correct.
    """

    def test_run_calls_execute(self):
        """run() calls _execute() method."""
        worker = ConcreteTestThreadWorker()

        worker.run()

        assert worker.execute_called

    def test_run_emits_result_with_return_value(self):
        """run() emits result signal with _execute return value."""
        worker = ConcreteTestThreadWorker(return_value="thread_result")
        results = []
        worker.result.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        assert results[0] == "thread_result"

    def test_run_emits_error_on_exception(self):
        """run() emits error signal when _execute raises."""
        worker = ConcreteTestThreadWorker(should_raise=ValueError("Thread error"))
        errors = []
        worker.error.connect(lambda msg, tb: errors.append((msg, tb)))

        worker.run()

        assert len(errors) == 1
        assert "Thread error" in errors[0][0]

    def test_run_respects_cancellation(self):
        """run() checks cancellation before executing."""
        worker = ConcreteTestThreadWorker()
        worker.cancel()
        result_spy = MagicMock()
        worker.result.connect(result_spy)

        worker.run()

        assert not worker.execute_called
        result_spy.assert_not_called()

    def test_cancelled_during_execute_no_result_emitted(self):
        """result not emitted if cancelled during _execute."""

        class CancelDuringWorker(BaseThreadWorker):
            def _execute(self):
                self._cancelled = True
                return "should_not_emit"

        worker = CancelDuringWorker()
        result_spy = MagicMock()
        worker.result.connect(result_spy)

        worker.run()

        result_spy.assert_not_called()


class TestBaseThreadWorkerStatusEmission:
    """Tests for BaseThreadWorker status signal."""

    def test_emit_status_sends_message(self, qtbot):
        """emit_status sends message correctly."""
        worker = ConcreteTestThreadWorker()

        with qtbot.waitSignal(worker.status, timeout=1000) as blocker:
            worker.emit_status("Processing...")

        assert blocker.args[0] == "Processing..."

    def test_emit_status_empty_string(self, qtbot):
        """emit_status handles empty string."""
        worker = ConcreteTestThreadWorker()

        with qtbot.waitSignal(worker.status, timeout=1000) as blocker:
            worker.emit_status("")

        assert blocker.args[0] == ""

    def test_multiple_status_updates(self):
        """Can emit multiple status updates."""
        worker = ConcreteTestThreadWorker()
        statuses = []
        worker.status.connect(lambda msg: statuses.append(msg))

        worker.emit_status("Step 1")
        worker.emit_status("Step 2")
        worker.emit_status("Step 3")

        assert statuses == ["Step 1", "Step 2", "Step 3"]


class TestBaseThreadWorkerErrorHandling:
    """Tests for BaseThreadWorker error handling."""

    def test_handles_exception(self):
        """Handles exception raised in run()."""
        worker = ConcreteTestThreadWorker(should_raise=RuntimeError("Worker crash"))
        errors = []
        worker.error.connect(lambda msg, tb: errors.append((msg, tb)))

        worker.run()

        assert len(errors) == 1
        assert "Worker crash" in errors[0][0]
        assert "RuntimeError" in errors[0][1]


class TestProgressEmission:
    """Tests for progress emission convenience method."""

    def test_emit_progress_with_values(self, qtbot):
        """emit_progress sends correct current and total."""
        worker = ConcreteTestWorker()

        with qtbot.waitSignal(worker.progress, timeout=1000) as blocker:
            worker.emit_progress(25, 100)

        assert blocker.args[0] == 25
        assert blocker.args[1] == 100

    def test_emit_progress_zero_values(self, qtbot):
        """emit_progress handles zero values."""
        worker = ConcreteTestWorker()

        with qtbot.waitSignal(worker.progress, timeout=1000) as blocker:
            worker.emit_progress(0, 0)

        assert blocker.args == [0, 0]

    def test_emit_progress_negative_values(self, qtbot):
        """emit_progress accepts negative values (no validation)."""
        worker = ConcreteTestWorker()

        with qtbot.waitSignal(worker.progress, timeout=1000) as blocker:
            worker.emit_progress(-1, 100)

        assert blocker.args[0] == -1


class TestReturnValueTypes:
    """Tests for various return value types."""

    def test_returns_string(self):
        """Worker can return string."""
        worker = ConcreteTestWorker(return_value="test string")
        results = []
        worker.finished.connect(results.append)

        worker.run()

        assert results[0] == "test string"

    def test_returns_dict(self):
        """Worker can return dict."""
        result_dict = {"key": "value", "number": 42}
        worker = ConcreteTestWorker(return_value=result_dict)
        results = []
        worker.finished.connect(results.append)

        worker.run()

        assert results[0] == result_dict

    def test_returns_list(self):
        """Worker can return list."""
        result_list = [1, 2, 3, "four"]
        worker = ConcreteTestWorker(return_value=result_list)
        results = []
        worker.finished.connect(results.append)

        worker.run()

        assert results[0] == result_list

    def test_returns_none(self):
        """Worker can return None."""
        worker = ConcreteTestWorker(return_value=None)
        results = []
        worker.finished.connect(results.append)

        worker.run()

        assert results[0] is None

    def test_returns_custom_object(self):
        """Worker can return custom object."""

        class CustomResult:
            def __init__(self):
                self.value = 123

        result_obj = CustomResult()
        worker = ConcreteTestWorker(return_value=result_obj)
        results = []
        worker.finished.connect(results.append)

        worker.run()

        assert results[0].value == 123
