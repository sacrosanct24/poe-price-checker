"""
Base worker class for PyQt6 background tasks.

Provides standardized signals, cancellation support, and error handling
for all background workers in the application.
"""

from abc import abstractmethod
from typing import Any, Optional
import logging
import traceback

from PyQt6.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class BaseWorker(QObject):
    """
    Abstract base class for QObject-based workers.

    Use this when you need to run work on a QThread that you manage separately.
    Subclasses must implement _execute() to perform the actual work.

    Signals:
        finished: Emitted with result when work completes successfully
        error: Emitted with (message, traceback_str) on failure
        progress: Emitted with (current, total) for progress updates

    Example:
        class MyWorker(BaseWorker):
            def __init__(self, data):
                super().__init__()
                self.data = data

            def _execute(self):
                # Do work here
                return processed_data

        worker = MyWorker(data)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda r: print(f"Done: {r}"))
        thread.start()
    """

    finished = pyqtSignal(object)  # Emits result on success
    error = pyqtSignal(str, str)   # Emits (message, traceback) on failure
    progress = pyqtSignal(int, int)  # Emits (current, total) for progress

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        """Check if the worker has been cancelled."""
        return self._cancelled

    def cancel(self) -> None:
        """
        Request cancellation of the worker.

        Subclasses should check is_cancelled periodically in _execute()
        for long-running operations.
        """
        self._cancelled = True
        logger.debug(f"{self.__class__.__name__} cancellation requested")

    @abstractmethod
    def _execute(self) -> Any:
        """
        Override to implement the actual work.

        Returns:
            The result to emit via the finished signal

        Raises:
            Exception: Any exception will be caught and emitted via error signal
        """

    def run(self) -> None:
        """
        Execute the worker task with standardized error handling.

        This method is typically connected to QThread.started signal.
        """
        if self._cancelled:
            logger.debug(f"{self.__class__.__name__} was cancelled before starting")
            return

        try:
            result = self._execute()
            if not self._cancelled:
                self.finished.emit(result)
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            logger.exception(f"{self.__class__.__name__} failed: {error_msg}")
            self.error.emit(error_msg, tb)

    def emit_progress(self, current: int, total: int) -> None:
        """
        Convenience method to emit progress updates.

        Args:
            current: Current progress value
            total: Total expected value
        """
        self.progress.emit(current, total)


class BaseThreadWorker(QThread):
    """
    Abstract base class for QThread-based workers.

    Use this when you want a self-contained worker that manages its own thread.
    Subclasses must implement _execute() to perform the actual work.

    Signals:
        result: Emitted with result when work completes successfully
        error: Emitted with (message, traceback_str) on failure
        progress: Emitted with status message for progress updates

    Example:
        class MyWorker(BaseThreadWorker):
            def _execute(self):
                self.emit_status("Starting...")
                # Do work
                return result

        worker = MyWorker()
        worker.result.connect(lambda r: print(f"Done: {r}"))
        worker.start()
    """

    result = pyqtSignal(object)     # Emits result on success
    error = pyqtSignal(str, str)    # Emits (message, traceback) on failure
    status = pyqtSignal(str)        # Emits status message for progress

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        """Check if the worker has been cancelled."""
        return self._cancelled

    def cancel(self) -> None:
        """Request cancellation of the worker."""
        self._cancelled = True
        logger.debug(f"{self.__class__.__name__} cancellation requested")

    @abstractmethod
    def _execute(self) -> Any:
        """
        Override to implement the actual work.

        Returns:
            The result to emit via the result signal
        """

    def run(self) -> None:
        """Execute the worker task with standardized error handling."""
        if self._cancelled:
            return

        try:
            res = self._execute()
            if not self._cancelled:
                self.result.emit(res)
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            logger.exception(f"{self.__class__.__name__} failed: {error_msg}")
            self.error.emit(error_msg, tb)

    def emit_status(self, message: str) -> None:
        """Convenience method to emit status updates."""
        self.status.emit(message)
