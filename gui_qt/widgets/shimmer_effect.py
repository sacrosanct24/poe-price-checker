"""
Shimmer Effect - Loading shimmer animation for widgets.

Adds a Material Design 3 style shimmer effect to any widget to indicate
loading state. The shimmer creates a wave of light that moves across
the widget surface.

Usage:
    from gui_qt.widgets.shimmer_effect import ShimmerEffect, ShimmerMixin

    # Add shimmer to existing widget
    shimmer = ShimmerEffect(my_widget)
    shimmer.start()
    # Later...
    shimmer.stop()

    # Or use mixin for built-in support
    class MyWidget(QWidget, ShimmerMixin):
        def start_loading(self):
            self.start_shimmer()

        def stop_loading(self):
            self.stop_shimmer()
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty  # type: ignore[attr-defined]
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPaintEvent
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect

from gui_qt.design_system import Duration, should_reduce_motion


class ShimmerEffect(QWidget):
    """
    Transparent overlay that adds shimmer effect to any widget.

    The shimmer is a diagonal gradient that sweeps across the widget,
    creating a loading animation effect.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        color: str = "#ffffff",
        opacity: float = 0.1,
        angle: float = -20.0,
        speed: int = Duration.SKELETON,
    ):
        """
        Initialize shimmer effect.

        Args:
            parent: Widget to apply shimmer to
            color: Shimmer highlight color
            opacity: Maximum shimmer opacity (0.0 to 1.0)
            angle: Shimmer angle in degrees (-45 to 45 typical)
            speed: One shimmer cycle duration in ms
        """
        super().__init__(parent)

        self._color = QColor(color)
        self._opacity = opacity
        self._angle = angle
        self._speed = speed
        self._offset = 0.0  # -1.0 to 2.0 for full sweep

        # Match parent size
        self.setGeometry(parent.rect())

        # Transparent for mouse events
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._animation: Optional[QPropertyAnimation] = None
        self.hide()

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = pyqtProperty(float, _get_offset, _set_offset)

    def start(self) -> None:
        """Start the shimmer animation."""
        if should_reduce_motion():
            # Show static highlight instead of animation
            self._offset = 0.5
            self.show()
            self.update()
            return

        self.show()
        self.raise_()

        # Create smooth sweep animation
        self._animation = QPropertyAnimation(self, b"offset")
        self._animation.setDuration(self._speed)
        self._animation.setStartValue(-0.3)
        self._animation.setEndValue(1.3)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._animation.start()

    def stop(self) -> None:
        """Stop the shimmer animation."""
        if self._animation:
            self._animation.stop()
            self._animation = None
        self.hide()

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the shimmer gradient."""
        if event is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Create gradient at angle
        # Calculate start and end points based on angle
        import math
        angle_rad = math.radians(self._angle)

        # Gradient width (shimmer band width)
        shimmer_width = 0.3

        # Position shimmer based on offset
        center_x = width * self._offset
        center_y = height / 2

        # Gradient perpendicular to shimmer direction
        dx = math.cos(angle_rad) * width
        dy = math.sin(angle_rad) * width

        gradient = QLinearGradient(
            center_x - dx / 2, center_y - dy / 2,
            center_x + dx / 2, center_y + dy / 2,
        )

        # Transparent -> highlight -> transparent
        transparent = QColor(self._color)
        transparent.setAlphaF(0.0)

        highlight = QColor(self._color)
        highlight.setAlphaF(self._opacity)

        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(0.5 - shimmer_width / 2, transparent)
        gradient.setColorAt(0.5, highlight)
        gradient.setColorAt(0.5 + shimmer_width / 2, transparent)
        gradient.setColorAt(1.0, transparent)

        painter.fillRect(self.rect(), gradient)

    def resizeEvent(self, event) -> None:
        """Resize with parent."""
        super().resizeEvent(event)
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            self.setGeometry(parent.rect())


class ShimmerMixin:
    """
    Mixin to add shimmer capability to any widget.

    Example:
        class LoadingCard(QWidget, ShimmerMixin):
            def __init__(self):
                super().__init__()
                # ... widget setup ...

            def load_data(self):
                self.start_shimmer()
                # ... fetch data ...
                self.stop_shimmer()
    """

    _shimmer_effect: Optional[ShimmerEffect] = None

    def start_shimmer(
        self,
        color: str = "#ffffff",
        opacity: float = 0.1,
    ) -> None:
        """
        Start shimmer effect on this widget.

        Args:
            color: Shimmer highlight color
            opacity: Maximum shimmer opacity
        """
        if self._shimmer_effect is None:
            self._shimmer_effect = ShimmerEffect(
                self,  # type: ignore[arg-type]
                color=color,
                opacity=opacity,
            )
        self._shimmer_effect.start()

    def stop_shimmer(self) -> None:
        """Stop shimmer effect on this widget."""
        if self._shimmer_effect:
            self._shimmer_effect.stop()

    def is_shimmering(self) -> bool:
        """Check if shimmer is currently active."""
        return self._shimmer_effect is not None and self._shimmer_effect.isVisible()


class PulseEffect(QWidget):
    """
    Pulsing opacity effect for loading states.

    Alternative to shimmer for simpler loading indication.
    The widget pulses between two opacity levels.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        min_opacity: float = 0.4,
        max_opacity: float = 1.0,
        duration: int = Duration.SKELETON,
    ):
        """
        Initialize pulse effect.

        Args:
            parent: Widget to apply pulse to
            min_opacity: Minimum opacity during pulse
            max_opacity: Maximum opacity during pulse
            duration: One pulse cycle duration in ms
        """
        super().__init__(parent)

        self._min_opacity = min_opacity
        self._max_opacity = max_opacity
        self._duration = duration

        # Apply opacity effect to parent
        self._opacity_effect = QGraphicsOpacityEffect(parent)
        parent.setGraphicsEffect(self._opacity_effect)

        self._animation: Optional[QPropertyAnimation] = None
        self.hide()  # This widget doesn't need to be visible

    def start(self) -> None:
        """Start the pulse animation."""
        if should_reduce_motion():
            self._opacity_effect.setOpacity((self._min_opacity + self._max_opacity) / 2)
            return

        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(self._duration // 2)
        self._animation.setStartValue(self._max_opacity)
        self._animation.setEndValue(self._min_opacity)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        # Reverse direction each loop for smooth back-and-forth
        self._animation.finished.connect(self._reverse_direction)
        self._animation.start()

    def _reverse_direction(self) -> None:
        """Reverse animation direction."""
        if self._animation:
            start = self._animation.startValue()
            end = self._animation.endValue()
            self._animation.setStartValue(end)
            self._animation.setEndValue(start)

    def stop(self) -> None:
        """Stop the pulse animation and restore full opacity."""
        if self._animation:
            self._animation.stop()
            self._animation = None
        self._opacity_effect.setOpacity(1.0)


class SkeletonShimmer(QWidget):
    """
    Pre-styled skeleton block with built-in shimmer.

    Convenience class combining skeleton appearance with shimmer animation.
    Use for quick placeholder elements.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        width: int | None = None,
        height: int = 16,
        radius: int = 4,
        color: str = "#3a3a45",
        highlight_color: str = "#4a4a55",
    ):
        """
        Initialize skeleton shimmer.

        Args:
            parent: Parent widget
            width: Fixed width (None for expanding)
            height: Fixed height
            radius: Border radius
            color: Base skeleton color
            highlight_color: Shimmer highlight color
        """
        super().__init__(parent)

        self._radius = radius
        self._base_color = QColor(color)
        self._highlight_color = QColor(highlight_color)
        self._offset = 0.0

        if width:
            self.setFixedSize(width, height)
        else:
            self.setFixedHeight(height)

        self._animation: Optional[QPropertyAnimation] = None
        self.start()

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = pyqtProperty(float, _get_offset, _set_offset)

    def start(self) -> None:
        """Start shimmer animation."""
        if should_reduce_motion():
            self._offset = 0.5
            self.update()
            return

        self._animation = QPropertyAnimation(self, b"offset")
        self._animation.setDuration(Duration.SKELETON)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._animation.start()

    def stop(self) -> None:
        """Stop shimmer animation."""
        if self._animation:
            self._animation.stop()
            self._animation = None

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint skeleton with shimmer."""
        if event is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Create shimmer gradient
        gradient = QLinearGradient(0, 0, rect.width(), 0)

        shimmer_pos = self._offset
        shimmer_width = 0.3

        gradient.setColorAt(0, self._base_color)
        gradient.setColorAt(max(0, shimmer_pos - shimmer_width), self._base_color)
        gradient.setColorAt(shimmer_pos, self._highlight_color)
        gradient.setColorAt(min(1, shimmer_pos + shimmer_width), self._base_color)
        gradient.setColorAt(1, self._base_color)

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self._radius, self._radius)

    def hideEvent(self, event) -> None:
        """Stop animation when hidden."""
        super().hideEvent(event)
        self.stop()

    def showEvent(self, event) -> None:
        """Restart animation when shown."""
        super().showEvent(event)
        self.start()
