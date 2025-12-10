"""
Feedback Animations - Button press, success/error states.

Provides micro-interaction feedback for user actions following
Material Design 3 expressive motion guidelines.

Usage:
    from gui_qt.animations.feedback import (
        ButtonFeedback,
        SuccessFeedback,
        RippleEffect,
    )

    # Add button feedback
    feedback = ButtonFeedback(button)
    button.pressed.connect(feedback.on_press)
    button.released.connect(feedback.on_release)

    # Show success feedback
    SuccessFeedback(widget).show()
"""

from typing import Optional, Callable

from PyQt6.QtCore import (
    Qt,
    QObject,
    QTimer,
    QPoint,
    QRect,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QEasingCurve,
    pyqtSignal,
)
from PyQt6.QtCore import pyqtProperty  # type: ignore[import-not-found,attr-defined]
from PyQt6.QtGui import QPainter, QColor, QPaintEvent, QRadialGradient
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect, QPushButton

from gui_qt.design_system import Duration, BorderRadius, should_reduce_motion


class PressEffect(QObject):
    """
    Press/release scale effect for buttons.

    Scales button slightly down on press, back up on release.
    """

    def __init__(
        self,
        widget: QWidget,
        *,
        press_scale: float = 0.95,
        duration: int = Duration.FAST,
    ):
        """
        Initialize press effect.

        Args:
            widget: Widget to apply effect to
            press_scale: Scale factor when pressed (0.95 = 95%)
            duration: Animation duration
        """
        super().__init__(widget)

        self._widget = widget
        self._press_scale = press_scale
        self._duration = duration
        self._original_geometry: Optional[QRect] = None
        self._animation: Optional[QPropertyAnimation] = None

    def on_press(self) -> None:
        """Handle press event."""
        if should_reduce_motion():
            return

        self._original_geometry = self._widget.geometry()
        center = self._original_geometry.center()

        # Calculate scaled geometry
        new_width = int(self._original_geometry.width() * self._press_scale)
        new_height = int(self._original_geometry.height() * self._press_scale)
        scaled_rect = QRect(
            center.x() - new_width // 2,
            center.y() - new_height // 2,
            new_width,
            new_height,
        )

        # Animate to scaled size
        self._animation = QPropertyAnimation(self._widget, b"geometry")
        self._animation.setDuration(self._duration)
        self._animation.setStartValue(self._original_geometry)
        self._animation.setEndValue(scaled_rect)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    def on_release(self) -> None:
        """Handle release event."""
        if should_reduce_motion() or not self._original_geometry:
            return

        # Animate back to original size (with slight overshoot for bounce)
        self._animation = QPropertyAnimation(self._widget, b"geometry")
        self._animation.setDuration(self._duration)
        self._animation.setStartValue(self._widget.geometry())
        self._animation.setEndValue(self._original_geometry)
        self._animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self._animation.start()


class RippleEffect(QWidget):
    """
    Material Design ripple effect.

    Shows expanding circle from click point.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        color: str = "#8b5cf6",
        duration: int = Duration.SLOW,
    ):
        """
        Initialize ripple effect.

        Args:
            parent: Widget to add ripple to
            color: Ripple color
            duration: Ripple animation duration
        """
        super().__init__(parent)

        self._color = QColor(color)
        self._duration = duration
        self._ripple_radius = 0.0
        self._ripple_opacity = 0.3
        self._ripple_center = QPoint(0, 0)

        # Match parent size
        self.setGeometry(parent.rect())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

    def _get_ripple_radius(self) -> float:
        return self._ripple_radius

    def _set_ripple_radius(self, value: float) -> None:
        self._ripple_radius = value
        self.update()

    ripple_radius = pyqtProperty(float, _get_ripple_radius, _set_ripple_radius)

    def _get_ripple_opacity(self) -> float:
        return self._ripple_opacity

    def _set_ripple_opacity(self, value: float) -> None:
        self._ripple_opacity = value
        self.update()

    ripple_opacity = pyqtProperty(float, _get_ripple_opacity, _set_ripple_opacity)

    def trigger(self, click_pos: QPoint) -> None:
        """
        Trigger ripple at position.

        Args:
            click_pos: Position where click occurred
        """
        if should_reduce_motion():
            return

        self._ripple_center = click_pos
        self._ripple_radius = 0
        self._ripple_opacity = 0.3

        # Calculate max radius (diagonal of widget)
        max_radius = (self.width() ** 2 + self.height() ** 2) ** 0.5

        self.show()
        self.raise_()

        # Radius animation
        radius_anim = QPropertyAnimation(self, b"ripple_radius")
        radius_anim.setDuration(self._duration)
        radius_anim.setStartValue(0.0)
        radius_anim.setEndValue(max_radius)
        radius_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Opacity animation (fade out)
        opacity_anim = QPropertyAnimation(self, b"ripple_opacity")
        opacity_anim.setDuration(self._duration)
        opacity_anim.setStartValue(0.3)
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Run in parallel
        group = QParallelAnimationGroup(self)
        group.addAnimation(radius_anim)
        group.addAnimation(opacity_anim)
        group.finished.connect(self.hide)
        group.start()

        self._animation_group = group

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the ripple."""
        if event is None or self._ripple_radius <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw radial gradient for soft edge
        gradient = QRadialGradient(
            self._ripple_center.x(),
            self._ripple_center.y(),
            self._ripple_radius,
        )

        center_color = QColor(self._color)
        center_color.setAlphaF(self._ripple_opacity)
        edge_color = QColor(self._color)
        edge_color.setAlphaF(0.0)

        gradient.setColorAt(0.0, center_color)
        gradient.setColorAt(0.7, center_color)
        gradient.setColorAt(1.0, edge_color)

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            self._ripple_center,
            int(self._ripple_radius),
            int(self._ripple_radius),
        )

    def resizeEvent(self, event) -> None:
        """Resize with parent."""
        super().resizeEvent(event)
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            self.setGeometry(parent.rect())


class ButtonFeedback(QObject):
    """
    Combined button feedback effects.

    Includes press scale and optional ripple effect.
    """

    def __init__(
        self,
        button: QPushButton,
        *,
        enable_press: bool = True,
        enable_ripple: bool = True,
        ripple_color: str = "#8b5cf6",
    ):
        """
        Initialize button feedback.

        Args:
            button: Button to add feedback to
            enable_press: Enable press scale effect
            enable_ripple: Enable ripple effect
            ripple_color: Color for ripple effect
        """
        super().__init__(button)

        self._button = button
        self._press_effect: Optional[PressEffect] = None
        self._ripple_effect: Optional[RippleEffect] = None

        if enable_press:
            self._press_effect = PressEffect(button)

        if enable_ripple:
            self._ripple_effect = RippleEffect(button, color=ripple_color)

        # Connect signals
        button.pressed.connect(self.on_press)
        button.released.connect(self.on_release)

    def on_press(self) -> None:
        """Handle button press."""
        if self._press_effect:
            self._press_effect.on_press()

        if self._ripple_effect:
            # Trigger ripple from center
            center = self._button.rect().center()
            self._ripple_effect.trigger(center)

    def on_release(self) -> None:
        """Handle button release."""
        if self._press_effect:
            self._press_effect.on_release()


class SuccessFeedback(QWidget):
    """
    Success feedback animation.

    Shows a brief green flash/pulse to indicate success.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        color: str = "#22c55e",
        duration: int = Duration.SLOW,
    ):
        """
        Initialize success feedback.

        Args:
            parent: Widget to show feedback on
            color: Success color
            duration: Animation duration
        """
        super().__init__(parent)

        self._color = QColor(color)
        self._duration = duration
        self._opacity = 0.0

        self.setGeometry(parent.rect())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    opacity = pyqtProperty(float, _get_opacity, _set_opacity)

    def show_feedback(self) -> None:
        """Show the success feedback."""
        if should_reduce_motion():
            return

        self._opacity = 0.0
        self.show()
        self.raise_()

        # Pulse animation: fade in then out
        anim = QPropertyAnimation(self, b"opacity")
        anim.setDuration(self._duration)
        anim.setKeyValueAt(0.0, 0.0)
        anim.setKeyValueAt(0.3, 0.3)  # Peak
        anim.setKeyValueAt(1.0, 0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self.hide)
        anim.start()

        self._animation = anim

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the feedback overlay."""
        if event is None or self._opacity <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        painter.fillRect(self.rect(), color)

    def resizeEvent(self, event) -> None:
        """Resize with parent."""
        super().resizeEvent(event)
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            self.setGeometry(parent.rect())


class ErrorFeedback(QWidget):
    """
    Error feedback animation.

    Shows a brief red flash and optional shake to indicate error.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        color: str = "#ef4444",
        duration: int = Duration.SLOW,
        shake: bool = True,
    ):
        """
        Initialize error feedback.

        Args:
            parent: Widget to show feedback on
            color: Error color
            duration: Animation duration
            shake: Whether to include shake animation
        """
        super().__init__(parent)

        self._target = parent
        self._color = QColor(color)
        self._duration = duration
        self._shake = shake
        self._opacity = 0.0

        self.setGeometry(parent.rect())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    opacity = pyqtProperty(float, _get_opacity, _set_opacity)

    def show_feedback(self) -> None:
        """Show the error feedback."""
        if should_reduce_motion():
            return

        self._opacity = 0.0
        self.show()
        self.raise_()

        # Flash animation
        flash_anim = QPropertyAnimation(self, b"opacity")
        flash_anim.setDuration(self._duration)
        flash_anim.setKeyValueAt(0.0, 0.0)
        flash_anim.setKeyValueAt(0.3, 0.3)
        flash_anim.setKeyValueAt(1.0, 0.0)
        flash_anim.finished.connect(self.hide)
        flash_anim.start()

        self._flash_animation = flash_anim

        # Shake animation
        if self._shake:
            self._do_shake()

    def _do_shake(self) -> None:
        """Perform shake animation on parent."""
        original_pos = self._target.pos()
        shake_distance = 5

        anim = QPropertyAnimation(self._target, b"pos")
        anim.setDuration(self._duration)

        # Shake keyframes
        anim.setKeyValueAt(0.0, original_pos)
        anim.setKeyValueAt(0.1, QPoint(original_pos.x() - shake_distance, original_pos.y()))
        anim.setKeyValueAt(0.2, QPoint(original_pos.x() + shake_distance, original_pos.y()))
        anim.setKeyValueAt(0.3, QPoint(original_pos.x() - shake_distance, original_pos.y()))
        anim.setKeyValueAt(0.4, QPoint(original_pos.x() + shake_distance, original_pos.y()))
        anim.setKeyValueAt(0.5, QPoint(original_pos.x() - shake_distance // 2, original_pos.y()))
        anim.setKeyValueAt(0.6, QPoint(original_pos.x() + shake_distance // 2, original_pos.y()))
        anim.setKeyValueAt(1.0, original_pos)

        anim.setEasingCurve(QEasingCurve.Type.Linear)
        anim.start()

        self._shake_animation = anim

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the feedback overlay."""
        if event is None or self._opacity <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(self._color)
        color.setAlphaF(self._opacity)

        painter.fillRect(self.rect(), color)

    def resizeEvent(self, event) -> None:
        """Resize with parent."""
        super().resizeEvent(event)
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            self.setGeometry(parent.rect())


class HoverGlow(QWidget):
    """
    Hover glow effect.

    Shows a soft glow around widget on hover.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        color: str = "#8b5cf6",
        glow_size: int = 8,
    ):
        """
        Initialize hover glow.

        Args:
            parent: Widget to add glow to
            color: Glow color
            glow_size: Size of glow in pixels
        """
        super().__init__(parent)

        self._color = QColor(color)
        self._glow_size = glow_size
        self._opacity = 0.0

        # Position behind parent, slightly larger
        self._update_geometry()
        self.lower()

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Install event filter on parent
        parent.installEventFilter(self)

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    opacity = pyqtProperty(float, _get_opacity, _set_opacity)

    def _update_geometry(self) -> None:
        """Update geometry to surround parent."""
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            parent_rect = parent.rect()
            self.setGeometry(
                -self._glow_size,
                -self._glow_size,
                parent_rect.width() + self._glow_size * 2,
                parent_rect.height() + self._glow_size * 2,
            )

    def eventFilter(self, obj: Optional[QObject], event) -> bool:
        """Handle parent hover events."""
        from PyQt6.QtCore import QEvent

        if obj is None or event is None:
            return False
        if obj == self.parent():
            if event.type() == QEvent.Type.Enter:
                self._animate_in()
            elif event.type() == QEvent.Type.Leave:
                self._animate_out()
            elif event.type() == QEvent.Type.Resize:
                self._update_geometry()

        return super().eventFilter(obj, event)

    def _animate_in(self) -> None:
        """Animate glow in."""
        if should_reduce_motion():
            self._opacity = 0.5
            self.update()
            return

        anim = QPropertyAnimation(self, b"opacity")
        anim.setDuration(Duration.FAST)
        anim.setStartValue(self._opacity)
        anim.setEndValue(0.5)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

        self._animation = anim

    def _animate_out(self) -> None:
        """Animate glow out."""
        if should_reduce_motion():
            self._opacity = 0.0
            self.update()
            return

        anim = QPropertyAnimation(self, b"opacity")
        anim.setDuration(Duration.FAST)
        anim.setStartValue(self._opacity)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

        self._animation = anim

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the glow."""
        if event is None or self._opacity <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw glow using radial gradients at corners
        color = QColor(self._color)
        color.setAlphaF(self._opacity * 0.3)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)

        # Draw rounded rectangle with blur effect (approximated)
        rect = self.rect().adjusted(
            self._glow_size // 2,
            self._glow_size // 2,
            -self._glow_size // 2,
            -self._glow_size // 2,
        )
        painter.drawRoundedRect(rect, BorderRadius.MD, BorderRadius.MD)
