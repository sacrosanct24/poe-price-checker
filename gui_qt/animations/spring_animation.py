"""
Spring Animation - Physics-based spring animations.

Implements Material Design 3 expressive motion with spring physics
that creates organic, bouncy animations.

Usage:
    from gui_qt.animations.spring_animation import SpringAnimation

    # Animate widget position
    anim = SpringAnimation(widget, "pos")
    anim.animate_to(QPoint(100, 200))

    # Custom spring parameters
    anim = SpringAnimation(
        widget, "geometry",
        stiffness=300,
        damping=15,
    )
"""

import math
from typing import Optional, Any, Callable
from dataclasses import dataclass

from PyQt6.QtCore import (
    Qt,
    QObject,
    QTimer,
    QPoint,
    QPointF,
    QSize,
    QRect,
    QRectF,
    pyqtSignal,
)
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect

from gui_qt.design_system import Duration, should_reduce_motion


@dataclass
class SpringConfig:
    """
    Spring physics configuration.

    Attributes:
        stiffness: Spring constant (higher = faster, snappier)
        damping: Friction (higher = less bounce)
        mass: Object mass (higher = more momentum)
        velocity: Initial velocity
    """
    stiffness: float = 200.0
    damping: float = 20.0
    mass: float = 1.0
    velocity: float = 0.0

    @property
    def damping_ratio(self) -> float:
        """Calculate damping ratio (< 1 = bouncy, 1 = critical, > 1 = overdamped)."""
        return self.damping / (2 * math.sqrt(self.stiffness * self.mass))

    @property
    def is_bouncy(self) -> bool:
        """Whether this spring will bounce."""
        return self.damping_ratio < 1.0


# Pre-configured spring presets
SPRING_GENTLE = SpringConfig(100, 15, 1.0)
SPRING_DEFAULT = SpringConfig(200, 20, 1.0)
SPRING_BOUNCY = SpringConfig(300, 10, 1.0)
SPRING_STIFF = SpringConfig(400, 30, 1.0)
SPRING_SNAPPY = SpringConfig(500, 35, 1.0)


class SpringAnimation(QObject):
    """
    Spring physics-based animation.

    Simulates spring motion for smooth, organic animations
    following Material Design 3 guidelines.
    """

    # Emitted when animation completes
    finished = pyqtSignal()

    # Emitted on each frame with current value
    value_changed = pyqtSignal(object)

    # Simulation parameters
    FRAME_RATE = 60  # FPS
    FRAME_TIME = 1000 // FRAME_RATE  # ms per frame
    VELOCITY_THRESHOLD = 0.01  # Stop when velocity is this low
    POSITION_THRESHOLD = 0.1  # Stop when this close to target

    def __init__(
        self,
        target: QWidget,
        property_name: str,
        *,
        stiffness: float = 200.0,
        damping: float = 20.0,
        mass: float = 1.0,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize spring animation.

        Args:
            target: Widget to animate
            property_name: Property to animate ("pos", "size", "geometry", "opacity")
            stiffness: Spring stiffness (100-500 typical)
            damping: Damping coefficient (10-40 typical)
            mass: Mass (usually 1.0)
            on_complete: Callback when animation finishes
        """
        super().__init__()

        self._target = target
        self._property_name = property_name
        self._config = SpringConfig(stiffness, damping, mass)
        self._on_complete = on_complete

        self._current_value: Any = None
        self._target_value: Any = None
        self._velocity: Any = None

        self._timer: Optional[QTimer] = None
        self._running = False

        # For opacity, we need a graphics effect
        self._opacity_effect: Optional[QGraphicsOpacityEffect] = None

    def set_config(self, config: SpringConfig) -> None:
        """Set spring configuration."""
        self._config = config

    def animate_to(self, target_value: Any, immediate: bool = False) -> None:
        """
        Animate to target value.

        Args:
            target_value: Target value to animate to
            immediate: If True, skip animation (for reduced motion)
        """
        if should_reduce_motion() or immediate:
            self._set_value(target_value)
            self.finished.emit()
            if self._on_complete:
                self._on_complete()
            return

        # Get current value
        self._current_value = self._get_current_value()
        self._target_value = target_value

        # Initialize velocity if needed
        if self._velocity is None:
            self._velocity = self._create_zero_value()

        # Start simulation
        self._start_simulation()

    def stop(self) -> None:
        """Stop the animation."""
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._running = False

    def is_running(self) -> bool:
        """Check if animation is running."""
        return self._running

    def _start_simulation(self) -> None:
        """Start the spring simulation."""
        self.stop()

        self._running = True
        self._timer = QTimer()
        self._timer.timeout.connect(self._step)
        self._timer.start(self.FRAME_TIME)

    def _step(self) -> None:
        """Perform one simulation step."""
        if not self._running:
            return

        # Calculate spring force
        dt = self.FRAME_TIME / 1000.0  # Convert to seconds

        # Update based on value type
        if isinstance(self._current_value, (int, float)):
            self._step_scalar(dt)
        elif isinstance(self._current_value, (QPoint, QPointF)):
            self._step_point(dt)
        elif isinstance(self._current_value, QSize):
            self._step_size(dt)
        elif isinstance(self._current_value, (QRect, QRectF)):
            self._step_rect(dt)
        else:
            # Unknown type, just set directly
            self._set_value(self._target_value)
            self._finish()
            return

        # Apply value
        self._set_value(self._current_value)
        self.value_changed.emit(self._current_value)

        # Check if settled
        if self._is_settled():
            self._set_value(self._target_value)
            self._finish()

    def _step_scalar(self, dt: float) -> None:
        """Step simulation for scalar value."""
        force = self._spring_force(
            self._current_value,
            self._target_value,
            self._velocity,
        )
        self._velocity += force * dt
        self._current_value += self._velocity * dt

    def _step_point(self, dt: float) -> None:
        """Step simulation for point value."""
        # X component
        force_x = self._spring_force(
            self._current_value.x(),
            self._target_value.x(),
            self._velocity.x() if isinstance(self._velocity, (QPoint, QPointF)) else 0,
        )
        # Y component
        force_y = self._spring_force(
            self._current_value.y(),
            self._target_value.y(),
            self._velocity.y() if isinstance(self._velocity, (QPoint, QPointF)) else 0,
        )

        # Update velocity
        if isinstance(self._velocity, QPointF):
            self._velocity = QPointF(
                self._velocity.x() + force_x * dt,
                self._velocity.y() + force_y * dt,
            )
        else:
            self._velocity = QPoint(
                int(self._velocity.x() + force_x * dt),
                int(self._velocity.y() + force_y * dt),
            )

        # Update position
        if isinstance(self._current_value, QPointF):
            self._current_value = QPointF(
                self._current_value.x() + self._velocity.x() * dt,
                self._current_value.y() + self._velocity.y() * dt,
            )
        else:
            self._current_value = QPoint(
                int(self._current_value.x() + self._velocity.x() * dt),
                int(self._current_value.y() + self._velocity.y() * dt),
            )

    def _step_size(self, dt: float) -> None:
        """Step simulation for size value."""
        force_w = self._spring_force(
            self._current_value.width(),
            self._target_value.width(),
            self._velocity.width() if isinstance(self._velocity, QSize) else 0,
        )
        force_h = self._spring_force(
            self._current_value.height(),
            self._target_value.height(),
            self._velocity.height() if isinstance(self._velocity, QSize) else 0,
        )

        self._velocity = QSize(
            int(self._velocity.width() + force_w * dt),
            int(self._velocity.height() + force_h * dt),
        )
        self._current_value = QSize(
            int(self._current_value.width() + self._velocity.width() * dt),
            int(self._current_value.height() + self._velocity.height() * dt),
        )

    def _step_rect(self, dt: float) -> None:
        """Step simulation for rect value."""
        # Animate all four components
        components = ['x', 'y', 'width', 'height']
        new_values = []
        new_velocities = []

        for comp in components:
            current = getattr(self._current_value, comp)()
            target = getattr(self._target_value, comp)()
            vel = getattr(self._velocity, comp)() if isinstance(self._velocity, (QRect, QRectF)) else 0

            force = self._spring_force(current, target, vel)
            new_vel = vel + force * dt
            new_val = current + new_vel * dt

            new_velocities.append(new_vel)
            new_values.append(new_val)

        if isinstance(self._current_value, QRectF):
            self._velocity = QRectF(*new_velocities)
            self._current_value = QRectF(*new_values)
        else:
            self._velocity = QRect(*[int(v) for v in new_velocities])
            self._current_value = QRect(*[int(v) for v in new_values])

    def _spring_force(self, current: float, target: float, velocity: float) -> float:
        """Calculate spring force using Hooke's law with damping."""
        displacement = target - current
        spring_force = self._config.stiffness * displacement
        damping_force = self._config.damping * velocity
        return (spring_force - damping_force) / self._config.mass

    def _is_settled(self) -> bool:
        """Check if spring has settled at target."""
        if isinstance(self._current_value, (int, float)):
            pos_settled = abs(self._current_value - self._target_value) < self.POSITION_THRESHOLD
            vel_settled = abs(self._velocity) < self.VELOCITY_THRESHOLD
            return pos_settled and vel_settled

        elif isinstance(self._current_value, (QPoint, QPointF)):
            dx = abs(self._current_value.x() - self._target_value.x())
            dy = abs(self._current_value.y() - self._target_value.y())
            pos_settled = dx < self.POSITION_THRESHOLD and dy < self.POSITION_THRESHOLD

            vx = abs(self._velocity.x()) if isinstance(self._velocity, (QPoint, QPointF)) else 0
            vy = abs(self._velocity.y()) if isinstance(self._velocity, (QPoint, QPointF)) else 0
            vel_settled = vx < self.VELOCITY_THRESHOLD and vy < self.VELOCITY_THRESHOLD

            return pos_settled and vel_settled

        elif isinstance(self._current_value, QSize):
            dw = abs(self._current_value.width() - self._target_value.width())
            dh = abs(self._current_value.height() - self._target_value.height())
            return dw < self.POSITION_THRESHOLD and dh < self.POSITION_THRESHOLD

        elif isinstance(self._current_value, (QRect, QRectF)):
            dx = abs(self._current_value.x() - self._target_value.x())
            dy = abs(self._current_value.y() - self._target_value.y())
            dw = abs(self._current_value.width() - self._target_value.width())
            dh = abs(self._current_value.height() - self._target_value.height())
            return all(d < self.POSITION_THRESHOLD for d in [dx, dy, dw, dh])

        return True

    def _get_current_value(self) -> Any:
        """Get current value from target widget."""
        if self._property_name == "pos":
            return self._target.pos()
        elif self._property_name == "size":
            return self._target.size()
        elif self._property_name == "geometry":
            return self._target.geometry()
        elif self._property_name == "opacity":
            if not self._opacity_effect:
                self._opacity_effect = QGraphicsOpacityEffect(self._target)
                self._target.setGraphicsEffect(self._opacity_effect)
            return self._opacity_effect.opacity()
        else:
            return getattr(self._target, self._property_name)()

    def _set_value(self, value: Any) -> None:
        """Set value on target widget."""
        if self._property_name == "pos":
            if isinstance(value, QPointF):
                value = value.toPoint()
            self._target.move(value)
        elif self._property_name == "size":
            self._target.resize(value)
        elif self._property_name == "geometry":
            if isinstance(value, QRectF):
                value = value.toRect()
            self._target.setGeometry(value)
        elif self._property_name == "opacity":
            if not self._opacity_effect:
                self._opacity_effect = QGraphicsOpacityEffect(self._target)
                self._target.setGraphicsEffect(self._opacity_effect)
            self._opacity_effect.setOpacity(value)
        else:
            setter = getattr(self._target, f"set{self._property_name.capitalize()}", None)
            if setter:
                setter(value)

    def _create_zero_value(self) -> Any:
        """Create a zero value matching the current value type."""
        if isinstance(self._current_value, (int, float)):
            return 0.0
        elif isinstance(self._current_value, QPoint):
            return QPoint(0, 0)
        elif isinstance(self._current_value, QPointF):
            return QPointF(0, 0)
        elif isinstance(self._current_value, QSize):
            return QSize(0, 0)
        elif isinstance(self._current_value, QRect):
            return QRect(0, 0, 0, 0)
        elif isinstance(self._current_value, QRectF):
            return QRectF(0, 0, 0, 0)
        return 0

    def _finish(self) -> None:
        """Finish the animation."""
        self.stop()
        self.finished.emit()
        if self._on_complete:
            self._on_complete()


def spring_animate(
    widget: QWidget,
    property_name: str,
    target_value: Any,
    *,
    stiffness: float = 200.0,
    damping: float = 20.0,
    on_complete: Optional[Callable[[], None]] = None,
) -> SpringAnimation:
    """
    Convenience function to animate a widget property.

    Args:
        widget: Widget to animate
        property_name: Property to animate
        target_value: Target value
        stiffness: Spring stiffness
        damping: Damping coefficient
        on_complete: Completion callback

    Returns:
        SpringAnimation instance
    """
    anim = SpringAnimation(
        widget, property_name,
        stiffness=stiffness,
        damping=damping,
        on_complete=on_complete,
    )
    anim.animate_to(target_value)
    return anim


def animate_widget(
    widget: QWidget,
    *,
    pos: Optional[QPoint] = None,
    size: Optional[QSize] = None,
    opacity: Optional[float] = None,
    config: SpringConfig = SPRING_DEFAULT,
) -> list[SpringAnimation]:
    """
    Animate multiple widget properties simultaneously.

    Args:
        widget: Widget to animate
        pos: Target position (optional)
        size: Target size (optional)
        opacity: Target opacity 0.0-1.0 (optional)
        config: Spring configuration

    Returns:
        List of SpringAnimation instances
    """
    animations = []

    if pos is not None:
        anim = SpringAnimation(
            widget, "pos",
            stiffness=config.stiffness,
            damping=config.damping,
            mass=config.mass,
        )
        anim.animate_to(pos)
        animations.append(anim)

    if size is not None:
        anim = SpringAnimation(
            widget, "size",
            stiffness=config.stiffness,
            damping=config.damping,
            mass=config.mass,
        )
        anim.animate_to(size)
        animations.append(anim)

    if opacity is not None:
        anim = SpringAnimation(
            widget, "opacity",
            stiffness=config.stiffness,
            damping=config.damping,
            mass=config.mass,
        )
        anim.animate_to(opacity)
        animations.append(anim)

    return animations
