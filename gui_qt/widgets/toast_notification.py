"""
gui_qt.widgets.toast_notification

Non-blocking toast notifications for status updates.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, List

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QGraphicsOpacityEffect,
)

from gui_qt.styles import COLORS


class ToastType(Enum):
    """Types of toast notifications with associated styling."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# Toast type colors
TOAST_COLORS = {
    ToastType.INFO: {
        "bg": "#2d4a6a",
        "border": "#4a7ba8",
        "text": "#e0e0e0",
        "icon": "i",
    },
    ToastType.SUCCESS: {
        "bg": "#2d5a3d",
        "border": "#4CAF50",
        "text": "#e0e0e0",
        "icon": "+",
    },
    ToastType.WARNING: {
        "bg": "#5a4a2d",
        "border": "#FFA726",
        "text": "#e0e0e0",
        "icon": "!",
    },
    ToastType.ERROR: {
        "bg": "#5a2d2d",
        "border": "#F44336",
        "text": "#e0e0e0",
        "icon": "x",
    },
}


class ToastNotification(QFrame):
    """A single toast notification that auto-dismisses."""

    def __init__(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration_ms: int = 3000,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._message = message
        self._toast_type = toast_type
        self._duration_ms = duration_ms

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedHeight(40)

        self._setup_ui()
        self._apply_style()

        # Opacity effect for fade animation
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)

    def _setup_ui(self) -> None:
        """Setup the toast UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(8)

        # Icon
        colors = TOAST_COLORS[self._toast_type]
        icon_label = QLabel(colors["icon"])
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            font-weight: bold;
            font-size: 14px;
            color: {colors["border"]};
        """)
        layout.addWidget(icon_label)

        # Message
        message_label = QLabel(self._message)
        message_label.setStyleSheet(f"color: {colors['text']}; font-size: 12px;")
        layout.addWidget(message_label, 1)

        # Close button
        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._fade_out)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {colors["text"]};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        layout.addWidget(close_btn)

    def _apply_style(self) -> None:
        """Apply toast styling based on type."""
        colors = TOAST_COLORS[self._toast_type]
        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: {colors["bg"]};
                border: 1px solid {colors["border"]};
                border-radius: 4px;
            }}
        """)

    def show_toast(self) -> None:
        """Show the toast with fade-in animation."""
        self.show()
        self._fade_in()
        if self._duration_ms > 0:
            self._dismiss_timer.start(self._duration_ms)

    def _fade_in(self) -> None:
        """Fade in animation."""
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _fade_out(self) -> None:
        """Fade out animation then close."""
        self._dismiss_timer.stop()
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self._on_fade_out_finished)
        self._anim.start()

    def _on_fade_out_finished(self) -> None:
        """Called when fade out completes."""
        self.close()
        self.deleteLater()


class ToastManager:
    """
    Manages toast notifications for a parent widget.

    Toasts are stacked from bottom-right corner upward.
    """

    # Spacing between toasts
    TOAST_SPACING = 8
    MARGIN_RIGHT = 20
    MARGIN_BOTTOM = 20
    MAX_TOASTS = 5

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._toasts: List[ToastNotification] = []

    def show_toast(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration_ms: int = 3000,
    ) -> ToastNotification:
        """
        Show a toast notification.

        Args:
            message: The message to display
            toast_type: Type of toast (info, success, warning, error)
            duration_ms: Auto-dismiss duration (0 = never auto-dismiss)

        Returns:
            The created toast notification
        """
        # Limit max toasts
        while len(self._toasts) >= self.MAX_TOASTS:
            oldest = self._toasts.pop(0)
            oldest._fade_out()

        toast = ToastNotification(message, toast_type, duration_ms, self._parent)
        toast.destroyed.connect(lambda: self._remove_toast(toast))
        self._toasts.append(toast)

        # Position and show
        self._position_toasts()
        toast.show_toast()

        return toast

    def _remove_toast(self, toast: ToastNotification) -> None:
        """Remove a toast from the managed list."""
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._position_toasts()

    def _position_toasts(self) -> None:
        """Position all toasts from bottom-right corner."""
        if not self._parent:
            return

        parent_rect = self._parent.rect()
        y_offset = self.MARGIN_BOTTOM

        for toast in reversed(self._toasts):
            toast_width = min(400, parent_rect.width() - 2 * self.MARGIN_RIGHT)
            toast.setFixedWidth(toast_width)

            x = parent_rect.width() - toast_width - self.MARGIN_RIGHT
            y = parent_rect.height() - y_offset - toast.height()

            toast.move(x, y)
            y_offset += toast.height() + self.TOAST_SPACING

    def info(self, message: str, duration_ms: int = 3000) -> ToastNotification:
        """Show an info toast."""
        return self.show_toast(message, ToastType.INFO, duration_ms)

    def success(self, message: str, duration_ms: int = 3000) -> ToastNotification:
        """Show a success toast."""
        return self.show_toast(message, ToastType.SUCCESS, duration_ms)

    def warning(self, message: str, duration_ms: int = 4000) -> ToastNotification:
        """Show a warning toast."""
        return self.show_toast(message, ToastType.WARNING, duration_ms)

    def error(self, message: str, duration_ms: int = 5000) -> ToastNotification:
        """Show an error toast."""
        return self.show_toast(message, ToastType.ERROR, duration_ms)

    def clear_all(self) -> None:
        """Clear all toasts."""
        for toast in list(self._toasts):
            toast._fade_out()
