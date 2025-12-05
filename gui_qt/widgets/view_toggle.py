"""
View Toggle - Widget to switch between table and card views.

Provides a toggle control with icons for switching between
different result display modes.

Usage:
    from gui_qt.widgets.view_toggle import ViewToggle, ViewMode

    toggle = ViewToggle()
    toggle.view_changed.connect(on_view_changed)

    # Get/set current mode
    current = toggle.current_view()
    toggle.set_view(ViewMode.CARDS)
"""

from enum import Enum
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QFrame,
    QToolTip,
)

from gui_qt.styles import COLORS
from gui_qt.design_system import Spacing, BorderRadius, Duration


class ViewMode(Enum):
    """Available view modes for results display."""
    TABLE = "table"
    CARDS = "cards"


class ViewToggleButton(QPushButton):
    """
    Individual toggle button for a view mode.

    Shows an icon representing the view mode with
    active/inactive styling.
    """

    def __init__(
        self,
        mode: ViewMode,
        icon_char: str,
        tooltip: str,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize toggle button.

        Args:
            mode: The view mode this button represents
            icon_char: Unicode character for the icon
            tooltip: Tooltip text
            parent: Parent widget
        """
        super().__init__(parent)

        self._mode = mode
        self._icon_char = icon_char

        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setFixedSize(32, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

        self._apply_style()

    @property
    def mode(self) -> ViewMode:
        """Get the view mode."""
        return self._mode

    def _apply_style(self) -> None:
        """Apply button styling."""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: {BorderRadius.SM}px;
                font-family: "Segoe UI Symbol", "Segoe UI", sans-serif;
                font-size: 14px;
                color: {COLORS['text_secondary']};
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_variant']};
                color: {COLORS['text']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: {COLORS['on_primary']};
            }}
            QPushButton:checked:hover {{
                background-color: {COLORS['primary_hover']};
            }}
            QPushButton:focus {{
                outline: 2px solid {COLORS['focus_ring']};
                outline-offset: 2px;
            }}
        """)

    def paintEvent(self, event) -> None:
        """Custom paint for icon."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw icon
        font = painter.font()
        font.setPixelSize(14)
        painter.setFont(font)

        rect = self.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._icon_char)


class ViewToggle(QFrame):
    """
    Toggle control for switching between view modes.

    Provides a grouped button set for selecting table or card view
    with visual feedback and keyboard accessibility.
    """

    view_changed = pyqtSignal(ViewMode)  # Emits when view mode changes

    # View mode configurations
    VIEW_CONFIGS = {
        ViewMode.TABLE: {
            "icon": "\u2630",  # Hamburger menu / list icon
            "tooltip": "Table View (Ctrl+Shift+T)\nDense data for comparison and sorting",
        },
        ViewMode.CARDS: {
            "icon": "\u25A6",  # Grid / cards icon
            "tooltip": "Card View (Ctrl+Shift+C)\nVisual cards for browsing",
        },
    }

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize view toggle."""
        super().__init__(parent)

        self._current_mode = ViewMode.TABLE
        self._buttons: dict[ViewMode, ViewToggleButton] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the toggle UI."""
        self.setObjectName("viewToggle")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Button group for mutual exclusion
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        # Create buttons for each view mode
        for mode in ViewMode:
            config = self.VIEW_CONFIGS[mode]
            button = ViewToggleButton(
                mode=mode,
                icon_char=config["icon"],
                tooltip=config["tooltip"],
                parent=self,
            )
            button.toggled.connect(
                lambda checked, m=mode: self._on_button_toggled(m, checked)
            )

            self._button_group.addButton(button)
            self._buttons[mode] = button
            layout.addWidget(button)

        # Set initial state
        self._buttons[ViewMode.TABLE].setChecked(True)

        # Container styling
        self.setStyleSheet(f"""
            QFrame#viewToggle {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {BorderRadius.SM}px;
            }}
        """)

    def _on_button_toggled(self, mode: ViewMode, checked: bool) -> None:
        """Handle button toggle."""
        if checked and mode != self._current_mode:
            self._current_mode = mode
            self.view_changed.emit(mode)

    def current_view(self) -> ViewMode:
        """Get the current view mode."""
        return self._current_mode

    def set_view(self, mode: ViewMode) -> None:
        """
        Set the current view mode.

        Args:
            mode: View mode to switch to
        """
        if mode in self._buttons:
            self._buttons[mode].setChecked(True)

    def toggle_view(self) -> ViewMode:
        """
        Toggle between view modes.

        Returns:
            The new view mode after toggling
        """
        if self._current_mode == ViewMode.TABLE:
            self.set_view(ViewMode.CARDS)
        else:
            self.set_view(ViewMode.TABLE)
        return self._current_mode


class ResultsViewSwitcher(QWidget):
    """
    Container widget that manages switching between table and card views.

    Holds both view widgets and shows/hides them based on the selected mode.
    """

    view_changed = pyqtSignal(ViewMode)  # Emits when view changes
    row_selected = pyqtSignal(dict)  # Emits when a row/card is selected
    rows_selected = pyqtSignal(list)  # Emits when multiple items selected

    def __init__(
        self,
        table_widget: QWidget,
        cards_widget: QWidget,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize view switcher.

        Args:
            table_widget: The table view widget
            cards_widget: The cards view widget
            parent: Parent widget
        """
        super().__init__(parent)

        self._table = table_widget
        self._cards = cards_widget
        self._current_mode = ViewMode.TABLE

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the switcher UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add both widgets
        layout.addWidget(self._table)
        layout.addWidget(self._cards)

        # Initial state - show table, hide cards
        self._table.show()
        self._cards.hide()

    def set_view(self, mode: ViewMode) -> None:
        """
        Switch to the specified view mode.

        Args:
            mode: View mode to switch to
        """
        if mode == self._current_mode:
            return

        self._current_mode = mode

        if mode == ViewMode.TABLE:
            self._cards.hide()
            self._table.show()
        else:
            self._table.hide()
            self._cards.show()

        self.view_changed.emit(mode)

    def current_view(self) -> ViewMode:
        """Get the current view mode."""
        return self._current_mode

    def table_widget(self) -> QWidget:
        """Get the table widget."""
        return self._table

    def cards_widget(self) -> QWidget:
        """Get the cards widget."""
        return self._cards

    def set_data(self, data: list) -> None:
        """
        Set data on both views.

        Args:
            data: List of item data dictionaries
        """
        # Set on table (if it has set_data method)
        if hasattr(self._table, 'set_data'):
            self._table.set_data(data)

        # Set on cards
        if hasattr(self._cards, 'set_data'):
            self._cards.set_data(data)

    def get_selected_rows(self) -> list:
        """Get selected items from the current view."""
        if self._current_mode == ViewMode.TABLE:
            if hasattr(self._table, 'get_selected_rows'):
                return self._table.get_selected_rows()
        else:
            if hasattr(self._cards, 'get_selected_data'):
                return self._cards.get_selected_data()
        return []

    def select_all(self) -> None:
        """Select all items in current view."""
        if self._current_mode == ViewMode.TABLE:
            if hasattr(self._table, 'select_all'):
                self._table.select_all()
        else:
            if hasattr(self._cards, 'select_all'):
                self._cards.select_all()

    def clear_selection(self) -> None:
        """Clear selection in current view."""
        if self._current_mode == ViewMode.TABLE:
            if hasattr(self._table, 'clear_selection'):
                self._table.clear_selection()
        else:
            if hasattr(self._cards, 'clear_selection'):
                self._cards.clear_selection()
