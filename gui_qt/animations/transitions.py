"""
Transitions - Page and panel transition effects.

Provides smooth transitions for switching between views,
expanding/collapsing panels, and page navigation.

Usage:
    from gui_qt.animations.transitions import (
        SlideTransition,
        FadeTransition,
        create_page_transition,
    )

    # Slide between pages
    transition = SlideTransition(
        old_widget, new_widget,
        direction=TransitionDirection.LEFT,
    )
    transition.start()
"""

from enum import Enum
from typing import Optional, Callable

from PyQt6.QtCore import (
    Qt,
    QObject,
    QTimer,
    QPoint,
    QRect,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
    QEasingCurve,
    pyqtSignal,
)
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect

from gui_qt.design_system import Duration, should_reduce_motion


class TransitionDirection(Enum):
    """Direction for slide transitions."""
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class SlideTransition(QObject):
    """
    Slide transition between two widgets.

    Slides one widget out while sliding another in.
    """

    finished = pyqtSignal()

    def __init__(
        self,
        old_widget: QWidget,
        new_widget: QWidget,
        *,
        direction: TransitionDirection = TransitionDirection.LEFT,
        duration: int = Duration.SLOW,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize slide transition.

        Args:
            old_widget: Widget to slide out
            new_widget: Widget to slide in
            direction: Slide direction
            duration: Animation duration in ms
            on_complete: Callback when transition completes
        """
        super().__init__()

        self._old_widget = old_widget
        self._new_widget = new_widget
        self._direction = direction
        self._duration = duration
        self._on_complete = on_complete

        self._animation_group: Optional[QParallelAnimationGroup] = None

    def start(self) -> None:
        """Start the transition."""
        if should_reduce_motion():
            self._old_widget.hide()
            self._new_widget.show()
            self._finish()
            return

        # Get dimensions
        parent = self._old_widget.parentWidget()
        if not parent:
            self._old_widget.hide()
            self._new_widget.show()
            self._finish()
            return

        rect = parent.rect()
        width = rect.width()
        height = rect.height()

        # Calculate offsets based on direction
        if self._direction == TransitionDirection.LEFT:
            old_end = QPoint(-width, 0)
            new_start = QPoint(width, 0)
        elif self._direction == TransitionDirection.RIGHT:
            old_end = QPoint(width, 0)
            new_start = QPoint(-width, 0)
        elif self._direction == TransitionDirection.UP:
            old_end = QPoint(0, -height)
            new_start = QPoint(0, height)
        else:  # DOWN
            old_end = QPoint(0, height)
            new_start = QPoint(0, -height)

        # Set up new widget position
        self._new_widget.move(new_start)
        self._new_widget.show()

        # Create animations
        old_anim = QPropertyAnimation(self._old_widget, b"pos")
        old_anim.setDuration(self._duration)
        old_anim.setStartValue(self._old_widget.pos())
        old_anim.setEndValue(old_end)
        old_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        new_anim = QPropertyAnimation(self._new_widget, b"pos")
        new_anim.setDuration(self._duration)
        new_anim.setStartValue(new_start)
        new_anim.setEndValue(QPoint(0, 0))
        new_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Run in parallel
        self._animation_group = QParallelAnimationGroup()
        self._animation_group.addAnimation(old_anim)
        self._animation_group.addAnimation(new_anim)
        self._animation_group.finished.connect(self._on_animation_complete)
        self._animation_group.start()

    def _on_animation_complete(self) -> None:
        """Handle animation completion."""
        self._old_widget.hide()
        self._finish()

    def _finish(self) -> None:
        """Complete the transition."""
        self.finished.emit()
        if self._on_complete:
            self._on_complete()


class FadeTransition(QObject):
    """
    Fade transition between two widgets.

    Fades one widget out while fading another in (cross-fade).
    """

    finished = pyqtSignal()

    def __init__(
        self,
        old_widget: QWidget,
        new_widget: QWidget,
        *,
        duration: int = Duration.NORMAL,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize fade transition.

        Args:
            old_widget: Widget to fade out
            new_widget: Widget to fade in
            duration: Animation duration in ms
            on_complete: Callback when transition completes
        """
        super().__init__()

        self._old_widget = old_widget
        self._new_widget = new_widget
        self._duration = duration
        self._on_complete = on_complete

        self._animation_group: Optional[QParallelAnimationGroup] = None

    def start(self) -> None:
        """Start the transition."""
        if should_reduce_motion():
            self._old_widget.hide()
            self._new_widget.show()
            self._finish()
            return

        # Set up opacity effects
        old_effect = QGraphicsOpacityEffect(self._old_widget)
        self._old_widget.setGraphicsEffect(old_effect)

        new_effect = QGraphicsOpacityEffect(self._new_widget)
        self._new_widget.setGraphicsEffect(new_effect)
        new_effect.setOpacity(0.0)
        self._new_widget.show()

        # Create animations
        old_anim = QPropertyAnimation(old_effect, b"opacity")
        old_anim.setDuration(self._duration)
        old_anim.setStartValue(1.0)
        old_anim.setEndValue(0.0)
        old_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        new_anim = QPropertyAnimation(new_effect, b"opacity")
        new_anim.setDuration(self._duration)
        new_anim.setStartValue(0.0)
        new_anim.setEndValue(1.0)
        new_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Run in parallel
        self._animation_group = QParallelAnimationGroup()
        self._animation_group.addAnimation(old_anim)
        self._animation_group.addAnimation(new_anim)
        self._animation_group.finished.connect(self._on_animation_complete)
        self._animation_group.start()

        # Store references
        self._old_effect = old_effect
        self._new_effect = new_effect

    def _on_animation_complete(self) -> None:
        """Handle animation completion."""
        self._old_widget.hide()
        # Remove opacity effects
        self._old_widget.setGraphicsEffect(None)
        self._new_widget.setGraphicsEffect(None)
        self._finish()

    def _finish(self) -> None:
        """Complete the transition."""
        self.finished.emit()
        if self._on_complete:
            self._on_complete()


class ScaleTransition(QObject):
    """
    Scale transition for showing/hiding widgets.

    Scales widget in/out with optional fade.
    """

    finished = pyqtSignal()

    def __init__(
        self,
        widget: QWidget,
        *,
        show: bool = True,
        duration: int = Duration.NORMAL,
        from_scale: float = 0.8,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize scale transition.

        Args:
            widget: Widget to animate
            show: True to show (scale in), False to hide (scale out)
            duration: Animation duration in ms
            from_scale: Starting/ending scale factor
            on_complete: Callback when transition completes
        """
        super().__init__()

        self._widget = widget
        self._show = show
        self._duration = duration
        self._from_scale = from_scale
        self._on_complete = on_complete

    def start(self) -> None:
        """Start the transition."""
        if should_reduce_motion():
            if self._show:
                self._widget.show()
            else:
                self._widget.hide()
            self._finish()
            return

        # For scale animation, we animate geometry
        original_geometry = self._widget.geometry()
        center = original_geometry.center()

        # Calculate scaled geometry
        scaled_width = int(original_geometry.width() * self._from_scale)
        scaled_height = int(original_geometry.height() * self._from_scale)
        scaled_rect = QRect(
            center.x() - scaled_width // 2,
            center.y() - scaled_height // 2,
            scaled_width,
            scaled_height,
        )

        # Set up opacity effect
        effect = QGraphicsOpacityEffect(self._widget)
        self._widget.setGraphicsEffect(effect)

        if self._show:
            # Scale in
            self._widget.setGeometry(scaled_rect)
            effect.setOpacity(0.0)
            self._widget.show()

            geom_anim = QPropertyAnimation(self._widget, b"geometry")
            geom_anim.setDuration(self._duration)
            geom_anim.setStartValue(scaled_rect)
            geom_anim.setEndValue(original_geometry)
            geom_anim.setEasingCurve(QEasingCurve.Type.OutBack)

            opacity_anim = QPropertyAnimation(effect, b"opacity")
            opacity_anim.setDuration(self._duration)
            opacity_anim.setStartValue(0.0)
            opacity_anim.setEndValue(1.0)
        else:
            # Scale out
            effect.setOpacity(1.0)

            geom_anim = QPropertyAnimation(self._widget, b"geometry")
            geom_anim.setDuration(self._duration)
            geom_anim.setStartValue(original_geometry)
            geom_anim.setEndValue(scaled_rect)
            geom_anim.setEasingCurve(QEasingCurve.Type.InBack)

            opacity_anim = QPropertyAnimation(effect, b"opacity")
            opacity_anim.setDuration(self._duration)
            opacity_anim.setStartValue(1.0)
            opacity_anim.setEndValue(0.0)

        # Run in parallel
        self._animation_group = QParallelAnimationGroup()
        self._animation_group.addAnimation(geom_anim)
        self._animation_group.addAnimation(opacity_anim)
        self._animation_group.finished.connect(self._on_animation_complete)
        self._animation_group.start()

        # Store references
        self._effect = effect
        self._original_geometry = original_geometry

    def _on_animation_complete(self) -> None:
        """Handle animation completion."""
        if not self._show:
            self._widget.hide()
            self._widget.setGeometry(self._original_geometry)
        self._widget.setGraphicsEffect(None)
        self._finish()

    def _finish(self) -> None:
        """Complete the transition."""
        self.finished.emit()
        if self._on_complete:
            self._on_complete()


class ExpandCollapseTransition(QObject):
    """
    Expand/collapse transition for panels.

    Smoothly expands or collapses a panel vertically.
    """

    finished = pyqtSignal()

    def __init__(
        self,
        widget: QWidget,
        *,
        expand: bool = True,
        target_height: int = 0,
        duration: int = Duration.SLOW,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize expand/collapse transition.

        Args:
            widget: Widget to animate
            expand: True to expand, False to collapse
            target_height: Target height when expanded (0 = current height)
            duration: Animation duration in ms
            on_complete: Callback when transition completes
        """
        super().__init__()

        self._widget = widget
        self._expand = expand
        self._target_height = target_height or widget.sizeHint().height()
        self._duration = duration
        self._on_complete = on_complete

    def start(self) -> None:
        """Start the transition."""
        if should_reduce_motion():
            if self._expand:
                self._widget.setFixedHeight(self._target_height)
                self._widget.show()
            else:
                self._widget.setFixedHeight(0)
                self._widget.hide()
            self._finish()
            return

        if self._expand:
            self._widget.setFixedHeight(0)
            self._widget.show()
            start_height = 0
            end_height = self._target_height
        else:
            start_height = self._widget.height()
            end_height = 0

        # Create height animation
        anim = QPropertyAnimation(self._widget, b"maximumHeight")
        anim.setDuration(self._duration)
        anim.setStartValue(start_height)
        anim.setEndValue(end_height)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._on_animation_complete)
        anim.start()

        self._animation = anim

    def _on_animation_complete(self) -> None:
        """Handle animation completion."""
        if not self._expand:
            self._widget.hide()
        # Reset to allow natural sizing
        self._widget.setMaximumHeight(16777215)  # Qt default max
        self._finish()

    def _finish(self) -> None:
        """Complete the transition."""
        self.finished.emit()
        if self._on_complete:
            self._on_complete()


def create_page_transition(
    container: QWidget,
    old_page: QWidget,
    new_page: QWidget,
    *,
    transition_type: str = "slide",
    direction: TransitionDirection = TransitionDirection.LEFT,
    duration: int = Duration.SLOW,
    on_complete: Optional[Callable[[], None]] = None,
) -> QObject:
    """
    Create a page transition effect.

    Convenience function for common transition patterns.

    Args:
        container: Container widget holding pages
        old_page: Page being transitioned from
        new_page: Page being transitioned to
        transition_type: "slide", "fade", or "scale"
        direction: Direction for slide transitions
        duration: Animation duration
        on_complete: Callback when complete

    Returns:
        Transition object (call .start() to begin)
    """
    if transition_type == "slide":
        return SlideTransition(
            old_page, new_page,
            direction=direction,
            duration=duration,
            on_complete=on_complete,
        )
    elif transition_type == "fade":
        return FadeTransition(
            old_page, new_page,
            duration=duration,
            on_complete=on_complete,
        )
    elif transition_type == "scale":
        # For scale, we need sequential: scale out old, scale in new
        group = QSequentialAnimationGroup()

        scale_out = ScaleTransition(old_page, show=False, duration=duration // 2)
        scale_in = ScaleTransition(new_page, show=True, duration=duration // 2)

        # Manual sequencing
        def do_scale_in():
            new_page.show()
            scale_in.start()
            scale_in.finished.connect(on_complete or (lambda: None))

        scale_out.finished.connect(do_scale_in)
        return scale_out

    else:
        # Default to fade
        return FadeTransition(
            old_page, new_page,
            duration=duration,
            on_complete=on_complete,
        )
