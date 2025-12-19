"""
Base screen class for application screens.

All screens (Item Evaluator, AI Advisor, Daytrader) inherit from this
base class which provides common functionality.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from core.app_context import AppContext


class BaseScreen(QWidget):
    """
    Abstract base class for application screens.

    Provides common functionality for all screens including:
    - Status updates via callback
    - Context access
    - Lifecycle methods (on_enter, on_leave)

    Signals:
        status_message(str): Emitted when screen wants to update status bar.

    Example:
        class MyScreen(BaseScreen):
            def __init__(self, ctx, on_status):
                super().__init__(ctx, on_status)
                self._create_ui()

            def _create_ui(self):
                layout = QVBoxLayout(self)
                # Add widgets...

            def on_enter(self):
                self.refresh()

            def on_leave(self):
                pass  # Cleanup if needed
    """

    status_message = pyqtSignal(str)

    def __init__(
        self,
        ctx: "AppContext",
        on_status: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize the base screen.

        Args:
            ctx: Application context providing access to services.
            on_status: Callback for status bar updates.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._on_status = on_status

        # Connect signal to callback if provided
        if on_status:
            self.status_message.connect(on_status)

    def set_status(self, message: str) -> None:
        """
        Update the status bar message.

        Args:
            message: Status message to display.
        """
        self.status_message.emit(message)
        if self._on_status:
            self._on_status(message)

    @abstractmethod
    def on_enter(self) -> None:
        """
        Called when the screen becomes visible.

        Override to refresh data or update UI when entering the screen.
        """
        pass

    @abstractmethod
    def on_leave(self) -> None:
        """
        Called when leaving this screen for another.

        Override to save state or cleanup resources.
        """
        pass

    def refresh(self) -> None:
        """
        Refresh the screen data.

        Override to implement data refresh logic.
        Default implementation does nothing.
        """
        pass

    @property
    def screen_name(self) -> str:
        """
        Return the display name of this screen.

        Override to provide a meaningful name.
        """
        return self.__class__.__name__
