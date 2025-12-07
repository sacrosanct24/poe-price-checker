"""
Main navigation bar widget for switching between screens.

Displays 3 large pill buttons for Item Evaluator, AI Advisor, and Daytrader.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QSizePolicy,
)

from gui_qt.screens.screen_controller import ScreenType


class MainNavigationBar(QWidget):
    """
    Navigation bar with 3 pill buttons for screen switching.

    Displays prominent buttons for the three main screens:
    - Item Evaluator
    - AI Advisor
    - Daytrader

    Signals:
        screen_selected(int): Emitted with ScreenType value when a button is clicked.

    Example:
        nav_bar = MainNavigationBar()
        nav_bar.screen_selected.connect(on_screen_change)
        nav_bar.set_active_screen(ScreenType.ITEM_EVALUATOR)
    """

    screen_selected = pyqtSignal(int)  # ScreenType as int

    # Button labels
    SCREEN_LABELS = {
        ScreenType.ITEM_EVALUATOR: "Item Evaluator",
        ScreenType.AI_ADVISOR: "AI Advisor",
        ScreenType.DAYTRADER: "Daytrader",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the navigation bar."""
        super().__init__(parent)

        self._buttons: dict[ScreenType, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._create_ui()
        self._apply_styles()

    def _create_ui(self) -> None:
        """Create the navigation bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Add stretch before buttons to center them
        layout.addStretch(1)

        # Create pill buttons for each screen
        for screen_type in ScreenType:
            btn = QPushButton(self.SCREEN_LABELS[screen_type])
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(140)
            btn.setMinimumHeight(36)

            # Store screen type in button property
            btn.setProperty("screen_type", screen_type.value)

            # Connect click
            btn.clicked.connect(lambda checked, st=screen_type: self._on_button_clicked(st))

            self._buttons[screen_type] = btn
            self._button_group.addButton(btn, screen_type.value)
            layout.addWidget(btn)

        # Add stretch after buttons to center them
        layout.addStretch(1)

        # Set first button as checked by default
        self._buttons[ScreenType.ITEM_EVALUATOR].setChecked(True)

    def _apply_styles(self) -> None:
        """Apply pill button styling."""
        self.setStyleSheet("""
            MainNavigationBar {
                background-color: palette(window);
                border-bottom: 1px solid palette(mid);
            }

            MainNavigationBar QPushButton {
                border: 2px solid palette(mid);
                border-radius: 18px;
                padding: 6px 20px;
                font-size: 13px;
                font-weight: 500;
                background-color: palette(button);
                color: palette(button-text);
            }

            MainNavigationBar QPushButton:hover {
                background-color: palette(light);
                border-color: palette(highlight);
            }

            MainNavigationBar QPushButton:checked {
                background-color: palette(highlight);
                color: palette(highlighted-text);
                border-color: palette(highlight);
            }

            MainNavigationBar QPushButton:checked:hover {
                background-color: palette(highlight);
            }
        """)

    def _on_button_clicked(self, screen_type: ScreenType) -> None:
        """Handle button click."""
        self.screen_selected.emit(screen_type.value)

    def set_active_screen(self, screen_type: ScreenType) -> None:
        """
        Set the active screen button.

        Args:
            screen_type: The screen to mark as active.
        """
        if screen_type in self._buttons:
            self._buttons[screen_type].setChecked(True)

    def get_active_screen(self) -> Optional[ScreenType]:
        """Get the currently active screen type."""
        checked = self._button_group.checkedId()
        if checked >= 0:
            return ScreenType(checked)
        return None
