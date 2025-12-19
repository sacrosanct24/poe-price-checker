"""
Focus Manager - Focus ring and tab order management.

Provides visible focus indicators and focus order management
following WCAG 2.2 requirements (2px minimum, 3:1 contrast).

Usage:
    from gui_qt.accessibility.focus_manager import (
        FocusManager,
        set_focus_order,
        apply_focus_style,
    )

    # Set explicit tab order
    set_focus_order([name_input, email_input, submit_button])

    # Apply focus styles to window
    apply_focus_style(main_window)

    # Use focus manager for complex scenarios
    manager = get_focus_manager()
    manager.push_focus_scope(dialog)  # For modal dialogs
    manager.pop_focus_scope()
"""

from typing import Optional, Callable
from weakref import WeakValueDictionary

from PyQt6.QtCore import Qt, QObject, QEvent, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QPaintEvent
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
    QDialog,
)


# WCAG 2.2 focus indicator requirements
FOCUS_RING_WIDTH = 2  # Minimum 2px
FOCUS_RING_OFFSET = 2  # Offset from widget edge
FOCUS_RING_COLOR = "#8b5cf6"  # Must have 3:1 contrast
FOCUS_RING_COLOR_ALT = "#f97316"  # Alternative high-contrast color


class FocusRing(QWidget):
    """
    Visible focus indicator overlay.

    Draws a focus ring around the currently focused widget.
    This ensures focus is always visible, even for widgets
    that don't have built-in focus styling.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        color: str = FOCUS_RING_COLOR,
        width: int = FOCUS_RING_WIDTH,
        offset: int = FOCUS_RING_OFFSET,
        radius: int = 4,
    ):
        """
        Initialize focus ring.

        Args:
            parent: Parent widget (usually main window)
            color: Ring color (hex)
            width: Ring width in pixels
            offset: Space between ring and widget
            radius: Corner radius
        """
        super().__init__(parent)

        self._color = QColor(color)
        self._width = width
        self._offset = offset
        self._radius = radius
        self._target: Optional[QWidget] = None

        # Make transparent and don't capture events
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.hide()

    def set_target(self, widget: Optional[QWidget]) -> None:
        """
        Set the widget to show focus ring around.

        Args:
            widget: Widget to highlight, or None to hide
        """
        self._target = widget

        if widget is None:
            self.hide()
            return

        # Calculate position relative to parent
        parent_widget = self.parentWidget()
        if parent_widget:
            # Get widget geometry in parent coordinates
            pos = widget.mapTo(parent_widget, widget.rect().topLeft())
            rect = widget.rect()

            # Expand for offset
            self.setGeometry(
                pos.x() - self._offset,
                pos.y() - self._offset,
                rect.width() + self._offset * 2,
                rect.height() + self._offset * 2,
            )

            self.raise_()
            self.show()
            self.update()

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the focus ring."""
        if self._target is None or event is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw ring (not filled)
        pen = QPen(self._color, self._width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Inset by half pen width for accurate drawing
        inset = self._width / 2
        rect = self.rect().adjusted(
            int(inset), int(inset),
            int(-inset), int(-inset)
        )

        painter.drawRoundedRect(rect, self._radius, self._radius)


class FocusManager(QObject):
    """
    Global focus management for the application.

    Handles:
    - Focus ring visibility
    - Focus scope for modal dialogs (focus trapping)
    - Tab order management
    - Focus restoration
    """

    def __init__(self, app: Optional[QApplication] = None):
        """
        Initialize focus manager.

        Args:
            app: QApplication instance (uses current if None)
        """
        super().__init__()

        instance = QApplication.instance()
        self._app: Optional[QApplication] = app or (instance if isinstance(instance, QApplication) else None)
        self._focus_ring: Optional[FocusRing] = None
        self._focus_scopes: list[QWidget] = []
        self._saved_focus: WeakValueDictionary = WeakValueDictionary()
        self._focus_ring_enabled = True

        # Install global event filter
        if self._app:
            self._app.installEventFilter(self)

    def enable_focus_ring(self, enabled: bool = True) -> None:
        """Enable or disable the global focus ring."""
        self._focus_ring_enabled = enabled
        if not enabled and self._focus_ring:
            self._focus_ring.hide()

    def push_focus_scope(self, scope: QWidget) -> None:
        """
        Push a new focus scope (e.g., for modal dialogs).

        Focus will be trapped within this scope until popped.

        Args:
            scope: Widget that defines the focus scope
        """
        # Save current focus
        current = self._app.focusWidget() if self._app else None
        if current and self._focus_scopes:
            # Associate saved focus with previous scope
            prev_scope = self._focus_scopes[-1]
            self._saved_focus[id(prev_scope)] = current

        self._focus_scopes.append(scope)

        # Focus first focusable widget in new scope
        self._focus_first_in_scope(scope)

    def pop_focus_scope(self) -> None:
        """
        Pop the current focus scope.

        Restores focus to the widget that had it before the scope was pushed.
        """
        if not self._focus_scopes:
            return

        self._focus_scopes.pop()

        # Restore focus if we have a saved widget
        if self._focus_scopes:
            prev_scope = self._focus_scopes[-1]
            saved = self._saved_focus.get(id(prev_scope))
            if saved:
                saved.setFocus()

    def _focus_first_in_scope(self, scope: QWidget) -> None:
        """Focus the first focusable widget in scope."""
        # Find first focusable widget
        for widget in scope.findChildren(QWidget):
            if self._is_focusable(widget):
                widget.setFocus()
                return

        # If no children, focus the scope itself if possible
        if self._is_focusable(scope):
            scope.setFocus()

    def _is_focusable(self, widget: QWidget) -> bool:
        """Check if a widget can receive focus."""
        return (
            widget.isEnabled()
            and widget.isVisible()
            and widget.focusPolicy() != Qt.FocusPolicy.NoFocus
        )

    def eventFilter(self, obj: Optional[QObject], event: Optional[QEvent]) -> bool:
        """Filter events to track focus changes."""
        if obj is None or event is None:
            return False
        if event.type() == QEvent.Type.FocusIn:
            if isinstance(obj, QWidget):
                self._on_focus_changed(obj)

        return super().eventFilter(obj, event)

    def _on_focus_changed(self, widget: QWidget) -> None:
        """Handle focus change to a widget."""
        if not self._focus_ring_enabled:
            return

        # Check if focus should be trapped in current scope
        if self._focus_scopes:
            current_scope = self._focus_scopes[-1]
            if not self._is_in_scope(widget, current_scope):
                # Focus escaped scope, redirect back
                self._focus_first_in_scope(current_scope)
                return

        # Update focus ring position
        self._update_focus_ring(widget)

    def _is_in_scope(self, widget: QWidget, scope: QWidget) -> bool:
        """Check if widget is within the focus scope."""
        current: Optional[QWidget] = widget
        while current:
            if current is scope:
                return True
            parent = current.parent()
            current = parent if isinstance(parent, QWidget) else None
        return False

    def _update_focus_ring(self, widget: QWidget) -> None:
        """Update focus ring to surround the focused widget."""
        # Find the top-level window
        window = widget.window()
        if window is None:
            return

        # Create or update focus ring
        if self._focus_ring is None or self._focus_ring.parent() != window:
            if self._focus_ring:
                self._focus_ring.deleteLater()
            self._focus_ring = FocusRing(window)

        self._focus_ring.set_target(widget)


# Global focus manager instance
_focus_manager: Optional[FocusManager] = None


def get_focus_manager() -> FocusManager:
    """
    Get the global focus manager instance.

    Returns:
        FocusManager singleton
    """
    global _focus_manager
    if _focus_manager is None:
        _focus_manager = FocusManager()
    return _focus_manager


def set_focus_order(widgets: list[QWidget]) -> None:
    """
    Set explicit tab order for a list of widgets.

    This ensures keyboard users can navigate in a logical order.

    Args:
        widgets: Widgets in desired tab order

    Example:
        set_focus_order([name_input, email_input, submit_button, cancel_button])
    """
    if len(widgets) < 2:
        return

    for i in range(len(widgets) - 1):
        QWidget.setTabOrder(widgets[i], widgets[i + 1])


def apply_focus_style(widget: QWidget) -> None:
    """
    Apply focus styling to a widget and its children.

    Adds CSS focus styles that meet WCAG 2.2 requirements.

    Args:
        widget: Widget (usually window) to style
    """
    focus_style = f"""
        *:focus {{
            outline: {FOCUS_RING_WIDTH}px solid {FOCUS_RING_COLOR};
            outline-offset: {FOCUS_RING_OFFSET}px;
        }}

        QPushButton:focus,
        QToolButton:focus {{
            border: {FOCUS_RING_WIDTH}px solid {FOCUS_RING_COLOR};
        }}

        QLineEdit:focus,
        QTextEdit:focus,
        QPlainTextEdit:focus,
        QSpinBox:focus,
        QComboBox:focus {{
            border: {FOCUS_RING_WIDTH}px solid {FOCUS_RING_COLOR};
        }}

        QTableView:focus,
        QTreeView:focus,
        QListView:focus {{
            border: {FOCUS_RING_WIDTH}px solid {FOCUS_RING_COLOR};
        }}

        QCheckBox:focus,
        QRadioButton:focus {{
            outline: {FOCUS_RING_WIDTH}px solid {FOCUS_RING_COLOR};
            outline-offset: 4px;
        }}

        QTabBar::tab:focus {{
            border-bottom: {FOCUS_RING_WIDTH}px solid {FOCUS_RING_COLOR};
        }}
    """

    current_style = widget.styleSheet()
    widget.setStyleSheet(current_style + focus_style)


class FocusStyleMixin:
    """
    Mixin to add focus styling capabilities to widgets.

    Example:
        class MyButton(QPushButton, FocusStyleMixin):
            def __init__(self):
                super().__init__()
                self.setup_focus_style()
    """

    _focus_color: str = FOCUS_RING_COLOR
    _focus_width: int = FOCUS_RING_WIDTH

    def setup_focus_style(
        self,
        color: str = FOCUS_RING_COLOR,
        width: int = FOCUS_RING_WIDTH,
    ) -> None:
        """
        Configure focus styling.

        Args:
            color: Focus ring color
            width: Focus ring width
        """
        self._focus_color = color
        self._focus_width = width

        if isinstance(self, QWidget):
            # Ensure widget can receive focus
            if self.focusPolicy() == Qt.FocusPolicy.NoFocus:
                self.setFocusPolicy(Qt.FocusPolicy.TabFocus)


class FocusTrap:
    """
    Context manager to trap focus within a widget.

    Use for modal dialogs or overlay panels.

    Example:
        with FocusTrap(dialog):
            dialog.exec()
    """

    def __init__(self, scope: QWidget):
        """
        Initialize focus trap.

        Args:
            scope: Widget to trap focus within
        """
        self._scope = scope
        self._manager = get_focus_manager()

    def __enter__(self):
        self._manager.push_focus_scope(self._scope)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._manager.pop_focus_scope()
        return False


def setup_dialog_focus(
    dialog: QDialog,
    primary_button: Optional[QWidget] = None,
    initial_focus: Optional[QWidget] = None,
) -> None:
    """
    Set up proper focus handling for a dialog.

    Args:
        dialog: Dialog to configure
        primary_button: Default button (receives Enter key)
        initial_focus: Widget to focus when dialog opens
    """
    from PyQt6.QtWidgets import QPushButton
    if primary_button and isinstance(primary_button, QPushButton):
        primary_button.setDefault(True)

    if initial_focus:
        # Focus initial widget after dialog shows
        QTimer.singleShot(0, lambda: initial_focus.setFocus())


def restore_focus_after(
    operation: Callable,
    fallback: Optional[QWidget] = None,
) -> None:
    """
    Execute an operation and restore focus afterward.

    Useful when an operation might steal focus.

    Args:
        operation: Callable to execute
        fallback: Widget to focus if original focus lost
    """
    app = QApplication.instance()
    original_focus = app.focusWidget() if app and isinstance(app, QApplication) else None

    operation()

    # Restore focus
    if original_focus and original_focus.isVisible():
        original_focus.setFocus()
    elif fallback:
        fallback.setFocus()
