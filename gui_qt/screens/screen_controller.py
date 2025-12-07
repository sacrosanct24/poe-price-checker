"""
Screen controller for managing screen transitions.

Handles switching between the 3 main screens and coordinating
lifecycle callbacks.
"""

from __future__ import annotations

from enum import IntEnum, auto
from typing import TYPE_CHECKING, Callable, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QStackedWidget

if TYPE_CHECKING:
    from gui_qt.screens.base_screen import BaseScreen


class ScreenType(IntEnum):
    """Enum representing the three main application screens."""

    ITEM_EVALUATOR = 0
    AI_ADVISOR = 1
    DAYTRADER = 2


class ScreenController(QObject):
    """
    Controller for managing screen transitions.

    Coordinates switching between screens, calling lifecycle methods,
    and updating the navigation bar state.

    Signals:
        screen_changed(ScreenType): Emitted when the active screen changes.
        screen_entering(ScreenType): Emitted before entering a screen.
        screen_leaving(ScreenType): Emitted before leaving a screen.

    Example:
        controller = ScreenController(stacked_widget)
        controller.register_screen(ScreenType.ITEM_EVALUATOR, evaluator_screen)
        controller.register_screen(ScreenType.AI_ADVISOR, advisor_screen)
        controller.register_screen(ScreenType.DAYTRADER, daytrader_screen)

        controller.switch_to(ScreenType.AI_ADVISOR)
    """

    screen_changed = pyqtSignal(int)  # ScreenType as int
    screen_entering = pyqtSignal(int)
    screen_leaving = pyqtSignal(int)

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        parent: Optional[QObject] = None,
    ):
        """
        Initialize the screen controller.

        Args:
            stacked_widget: The QStackedWidget containing screens.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._stacked_widget = stacked_widget
        self._screens: Dict[ScreenType, "BaseScreen"] = {}
        self._current_screen: Optional[ScreenType] = None
        self._on_status: Optional[Callable[[str], None]] = None

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set the status bar update callback."""
        self._on_status = callback

    def register_screen(
        self,
        screen_type: ScreenType,
        screen: "BaseScreen",
    ) -> None:
        """
        Register a screen with the controller.

        The screen will be added to the stacked widget at the
        index corresponding to its ScreenType.

        Args:
            screen_type: The type/index of the screen.
            screen: The screen widget.
        """
        self._screens[screen_type] = screen

        # Ensure the stacked widget has enough slots
        while self._stacked_widget.count() <= screen_type.value:
            # Add placeholder widgets if needed
            from PyQt6.QtWidgets import QWidget
            self._stacked_widget.addWidget(QWidget())

        # Replace the widget at the correct index
        old_widget = self._stacked_widget.widget(screen_type.value)
        if old_widget:
            self._stacked_widget.removeWidget(old_widget)
            old_widget.deleteLater()

        self._stacked_widget.insertWidget(screen_type.value, screen)

    def switch_to(self, screen_type: ScreenType) -> bool:
        """
        Switch to the specified screen.

        Calls on_leave() on the current screen and on_enter() on the
        new screen.

        Args:
            screen_type: The screen to switch to.

        Returns:
            True if switch was successful, False otherwise.
        """
        if screen_type not in self._screens:
            return False

        if self._current_screen == screen_type:
            return True  # Already on this screen

        # Leave current screen
        if self._current_screen is not None:
            current = self._screens.get(self._current_screen)
            if current:
                self.screen_leaving.emit(self._current_screen.value)
                current.on_leave()

        # Enter new screen
        new_screen = self._screens[screen_type]
        self.screen_entering.emit(screen_type.value)

        self._stacked_widget.setCurrentIndex(screen_type.value)
        self._current_screen = screen_type

        new_screen.on_enter()
        self.screen_changed.emit(screen_type.value)

        # Update status
        if self._on_status:
            self._on_status(f"{new_screen.screen_name}")

        return True

    def switch_to_evaluator(self) -> bool:
        """Switch to Item Evaluator screen."""
        return self.switch_to(ScreenType.ITEM_EVALUATOR)

    def switch_to_advisor(self) -> bool:
        """Switch to AI Advisor screen."""
        return self.switch_to(ScreenType.AI_ADVISOR)

    def switch_to_daytrader(self) -> bool:
        """Switch to Daytrader screen."""
        return self.switch_to(ScreenType.DAYTRADER)

    @property
    def current_screen(self) -> Optional[ScreenType]:
        """Get the currently active screen type."""
        return self._current_screen

    def get_screen(self, screen_type: ScreenType) -> Optional["BaseScreen"]:
        """Get a registered screen by type."""
        return self._screens.get(screen_type)

    def refresh_current(self) -> None:
        """Refresh the current screen."""
        if self._current_screen and self._current_screen in self._screens:
            self._screens[self._current_screen].refresh()
