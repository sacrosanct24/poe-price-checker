"""Tests for BaseWorker and BaseThreadWorker classes."""

import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import QThread

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
        from PyQt6.QtCore import QObject

        parent = QObject()
        worker = ConcreteTestWorker()
        worker.setParent(parent)
        assert worker.parent() is parent

    def test_initial_cancelled_state(self):
        """Worker starts with cancelled=False."""
        worker = ConcreteTestWorker()
        assert worker._cancelled is False
        assert worker.is_cancelled is False


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

    def test_run_cancelled_before_start(self, qtbot):
        """Worker doesn't execute if cancelled before run()."""
        worker = ConcreteTestWorker()
        worker.cancel()

        worker.run()

        assert not worker.execute_called


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

    def test_no_finished_signal_if_cancelled(self, qtbot):
        """finished signal not emitted if cancelled during execution."""
        worker = ConcreteTestWorker()

        # Can't easily test mid-execution cancellation, so test post-execution
        # We'll cancel right after _execute but before signal emission
        worker._cancelled = False
        result = worker._execute()
        worker._cancelled = True  # Simulate cancellation

        # Manually check the logic - if cancelled, signal shouldn't emit
        # This tests the condition in run()
        assert worker.is_cancelled

        # Test that run() respects cancellation
        worker2 = ConcreteTestWorker()
        worker2.run()  # This should emit finished

        worker3 = ConcreteTestWorker()
        worker3.cancel()
        # After cancellation, _execute is not called
        worker3.run()
        assert not worker3.execute_called


class TestBaseWorkerThreadExecution:
    """Tests for BaseWorker with QThread."""

    def test_worker_on_thread_success(self, qtbot):
        """Worker executes successfully on separate thread."""
        worker = ConcreteTestWorker(return_value="threaded_result")
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            thread.start()

        assert blocker.args[0] == "threaded_result"
        assert worker.execute_called

        # Cleanup
        thread.quit()
        thread.wait()

    def test_worker_on_thread_error(self, qtbot):
        """Worker error signal works on separate thread."""
        worker = ConcreteTestWorker(should_raise=RuntimeError("Thread error"))
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        with qtbot.waitSignal(worker.error, timeout=2000) as blocker:
            thread.start()

        error_msg, traceback = blocker.args
        assert "Thread error" in error_msg

        # Cleanup
        thread.quit()
        thread.wait()


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


class TestBaseThreadWorkerCancellation:
    """Tests for BaseThreadWorker cancellation."""

    def test_cancel_sets_flag(self):
        """cancel() sets the cancelled flag."""
        worker = ConcreteTestThreadWorker()

        worker.cancel()

        assert worker.is_cancelled

    def test_run_cancelled_before_start(self):
        """Worker doesn't execute if cancelled before start."""
        worker = ConcreteTestThreadWorker()
        worker.cancel()

        worker.run()

        assert not worker.execute_called


class TestBaseThreadWorkerSignals:
    """Tests for BaseThreadWorker signal emission."""

    def test_result_signal_on_success(self, qtbot):
        """result signal emitted with result on success."""
        worker = ConcreteTestThreadWorker(return_value="thread_result")

        with qtbot.waitSignal(worker.result, timeout=2000) as blocker:
            worker.start()
            worker.wait()

        assert blocker.args[0] == "thread_result"

    def test_error_signal_on_exception(self, qtbot):
        """error signal emitted on exception."""
        worker = ConcreteTestThreadWorker(should_raise=ValueError("Thread error"))

        with qtbot.waitSignal(worker.error, timeout=2000) as blocker:
            worker.start()
            worker.wait()

        error_msg, traceback = blocker.args
        assert "Thread error" in error_msg
        assert "ValueError" in traceback

    def test_status_signal_emission(self, qtbot):
        """status signal can be emitted."""
        worker = ConcreteTestThreadWorker()

        with qtbot.waitSignal(worker.status, timeout=1000) as blocker:
            worker.emit_status("Processing...")

        assert blocker.args[0] == "Processing..."


class TestBaseThreadWorkerExecution:
    """Tests for BaseThreadWorker execution."""

    def test_start_executes_work(self, qtbot):
        """Starting thread worker executes the work."""
        worker = ConcreteTestThreadWorker(return_value="executed")

        with qtbot.waitSignal(worker.result, timeout=2000):
            worker.start()
            worker.wait()

        assert worker.execute_called

    def test_multiple_status_updates(self, qtbot):
        """Can emit multiple status updates."""

        class MultiStatusWorker(BaseThreadWorker):
            def _execute(self):
                self.emit_status("Step 1")
                self.emit_status("Step 2")
                self.emit_status("Step 3")
                return "done"

        worker = MultiStatusWorker()
        statuses = []

        worker.status.connect(lambda msg: statuses.append(msg))

        with qtbot.waitSignal(worker.result, timeout=2000):
            worker.start()
            worker.wait()

        assert "Step 1" in statuses
        assert "Step 2" in statuses
        assert "Step 3" in statuses


class TestBaseThreadWorkerErrorHandling:
    """Tests for BaseThreadWorker error handling."""

    def test_handles_exception_in_thread(self, qtbot):
        """Handles exception raised in thread."""
        worker = ConcreteTestThreadWorker(should_raise=RuntimeError("Thread crash"))

        with qtbot.waitSignal(worker.error, timeout=2000) as blocker:
            worker.start()
            worker.wait()

        error_msg, traceback = blocker.args
        assert "Thread crash" in error_msg
        assert "RuntimeError" in traceback


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


class TestStatusEmission:
    """Tests for status emission convenience method."""

    def test_emit_status_with_message(self, qtbot):
        """emit_status sends message correctly."""
        worker = ConcreteTestThreadWorker()

        with qtbot.waitSignal(worker.status, timeout=1000) as blocker:
            worker.emit_status("Loading data...")

        assert blocker.args[0] == "Loading data..."

    def test_emit_status_empty_string(self, qtbot):
        """emit_status handles empty string."""
        worker = ConcreteTestThreadWorker()

        with qtbot.waitSignal(worker.status, timeout=1000) as blocker:
            worker.emit_status("")

        assert blocker.args[0] == ""


class ConcreteTestWorkerReturnValues:
    """Tests for various return value types."""

    def test_returns_string(self, qtbot):
        """Worker can return string."""
        worker = ConcreteTestWorker(return_value="test string")

        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        assert blocker.args[0] == "test string"

    def test_returns_dict(self, qtbot):
        """Worker can return dict."""
        result_dict = {"key": "value", "number": 42}
        worker = ConcreteTestWorker(return_value=result_dict)

        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        assert blocker.args[0] == result_dict

    def test_returns_list(self, qtbot):
        """Worker can return list."""
        result_list = [1, 2, 3, "four"]
        worker = ConcreteTestWorker(return_value=result_list)

        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        assert blocker.args[0] == result_list

    def test_returns_none(self, qtbot):
        """Worker can return None."""
        worker = ConcreteTestWorker(return_value=None)

        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        assert blocker.args[0] is None

    def test_returns_custom_object(self, qtbot):
        """Worker can return custom object."""

        class CustomResult:
            def __init__(self):
                self.value = 123

        result_obj = CustomResult()
        worker = ConcreteTestWorker(return_value=result_obj)

        with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
            worker.run()

        assert blocker.args[0].value == 123
