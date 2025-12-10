"""
Animation System - Spring physics and transition utilities.

Provides Material Design 3 expressive motion with spring-like animations
that bounce, stretch, and respond organically.

Usage:
    from gui_qt.design_system import (
        AnimationPreset,
        spring_curve,
        get_animation_duration,
    )

    # Create spring animation
    animation = QPropertyAnimation(widget, b"geometry")
    animation.setDuration(AnimationPreset.EXPAND.duration)
    animation.setEasingCurve(spring_curve(AnimationPreset.EXPAND))

    # Check for reduced motion preference
    if should_reduce_motion():
        animation.setDuration(0)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final

from PyQt6.QtCore import QEasingCurve

from gui_qt.design_system.tokens import Duration


@dataclass(frozen=True, slots=True)
class SpringParameters:
    """
    Spring animation parameters.

    These parameters define the physics of spring-based animations:
    - stiffness: How "tight" the spring is (higher = faster)
    - damping: How quickly oscillation stops (higher = less bounce)
    - mass: Affects momentum (higher = slower, more momentum)
    """

    stiffness: float  # Spring constant (100-500 typical)
    damping: float    # Friction (10-30 typical)
    mass: float = 1.0 # Mass (usually 1.0)
    velocity: float = 0.0  # Initial velocity

    @property
    def damping_ratio(self) -> float:
        """Calculate damping ratio (< 1 = bouncy, 1 = critical, > 1 = overdamped)."""
        import math
        return self.damping / (2 * math.sqrt(self.stiffness * self.mass))

    @property
    def is_bouncy(self) -> bool:
        """Whether this spring will bounce (underdamped)."""
        return self.damping_ratio < 1.0


class AnimationPreset(Enum):
    """
    Pre-configured animation presets for common scenarios.

    Each preset defines duration, spring parameters, and easing.
    """

    # Micro-interactions (very quick feedback)
    PRESS = ("press", Duration.FASTEST, SpringParameters(400, 30))
    RELEASE = ("release", Duration.FAST, SpringParameters(300, 25))

    # Hover states
    HOVER_IN = ("hover_in", Duration.FAST, SpringParameters(350, 28))
    HOVER_OUT = ("hover_out", Duration.FAST, SpringParameters(300, 30))

    # Content transitions
    FADE_IN = ("fade_in", Duration.NORMAL, SpringParameters(250, 22))
    FADE_OUT = ("fade_out", Duration.FAST, SpringParameters(300, 28))

    # Panel animations
    EXPAND = ("expand", Duration.SLOW, SpringParameters(200, 18))
    COLLAPSE = ("collapse", Duration.NORMAL, SpringParameters(250, 22))
    SLIDE_IN = ("slide_in", Duration.SLOW, SpringParameters(180, 16))
    SLIDE_OUT = ("slide_out", Duration.NORMAL, SpringParameters(220, 20))

    # Dialog/Modal
    DIALOG_ENTER = ("dialog_enter", Duration.SLOWER, SpringParameters(180, 15))
    DIALOG_EXIT = ("dialog_exit", Duration.NORMAL, SpringParameters(250, 25))

    # Toast/Notification
    TOAST_IN = ("toast_in", Duration.SLOW, SpringParameters(200, 17))
    TOAST_OUT = ("toast_out", Duration.NORMAL, SpringParameters(280, 24))

    # List items
    LIST_ITEM_ADD = ("list_add", Duration.NORMAL, SpringParameters(220, 19))
    LIST_ITEM_REMOVE = ("list_remove", Duration.FAST, SpringParameters(280, 26))

    # Scale animations
    SCALE_UP = ("scale_up", Duration.NORMAL, SpringParameters(240, 20))
    SCALE_DOWN = ("scale_down", Duration.FAST, SpringParameters(300, 26))

    # Page transitions
    PAGE_ENTER = ("page_enter", Duration.SLOWER, SpringParameters(160, 14))
    PAGE_EXIT = ("page_exit", Duration.SLOW, SpringParameters(200, 20))

    # Bouncy feedback
    BOUNCE = ("bounce", Duration.SLOWER, SpringParameters(300, 10))
    WIGGLE = ("wiggle", Duration.SLOW, SpringParameters(350, 12))

    def __init__(self, name: str, duration: int, spring: SpringParameters):
        self._name = name
        self._duration = duration
        self._spring = spring

    @property
    def duration(self) -> int:
        """Animation duration in milliseconds."""
        return self._duration

    @property
    def spring(self) -> SpringParameters:
        """Spring parameters for physics-based animation."""
        return self._spring


def spring_curve(preset: AnimationPreset) -> QEasingCurve:
    """
    Create a Qt easing curve that approximates spring motion.

    Qt doesn't have built-in spring curves, so we approximate
    using bezier curves tuned to match spring behavior.

    Args:
        preset: Animation preset to get curve for

    Returns:
        QEasingCurve approximating spring motion
    """
    spring = preset.spring

    if spring.is_bouncy:
        # Bouncy spring - use OutBack or OutElastic
        if spring.damping_ratio < 0.5:
            # Very bouncy
            curve = QEasingCurve(QEasingCurve.Type.OutElastic)
            curve.setAmplitude(1.0 + (0.5 - spring.damping_ratio))
            curve.setPeriod(0.3 + spring.damping_ratio * 0.2)
        else:
            # Slightly bouncy
            curve = QEasingCurve(QEasingCurve.Type.OutBack)
            overshoot = 1.0 + (1.0 - spring.damping_ratio) * 1.5
            curve.setOvershoot(overshoot)
    else:
        # Overdamped or critical - use OutCubic or OutQuart
        if spring.stiffness > 300:
            curve = QEasingCurve(QEasingCurve.Type.OutQuart)
        else:
            curve = QEasingCurve(QEasingCurve.Type.OutCubic)

    return curve


def get_standard_curve(type_name: str = "decelerate") -> QEasingCurve:
    """
    Get a standard Material Design 3 easing curve.

    Args:
        type_name: Curve type
            - "standard": General purpose
            - "decelerate": For entering elements
            - "accelerate": For exiting elements
            - "emphasized": For important transitions

    Returns:
        QEasingCurve
    """
    curves = {
        "standard": QEasingCurve.Type.OutCubic,
        "decelerate": QEasingCurve.Type.OutQuart,
        "accelerate": QEasingCurve.Type.InCubic,
        "emphasized": QEasingCurve.Type.InOutCubic,
        "linear": QEasingCurve.Type.Linear,
    }
    return QEasingCurve(curves.get(type_name, QEasingCurve.Type.OutCubic))


def get_animation_duration(
    preset: AnimationPreset | None = None,
    base_duration: int | None = None,
    reduce_motion: bool | None = None,
) -> int:
    """
    Get animation duration with reduced motion support.

    Args:
        preset: Animation preset (optional)
        base_duration: Override duration in ms (optional)
        reduce_motion: Override reduced motion preference (optional)

    Returns:
        Duration in milliseconds (0 if reduced motion enabled)
    """
    if reduce_motion is None:
        reduce_motion = should_reduce_motion()

    if reduce_motion:
        return 0

    if base_duration is not None:
        return base_duration

    if preset is not None:
        return preset.duration

    return Duration.NORMAL


def should_reduce_motion() -> bool:
    """
    Check if reduced motion is preferred.

    Checks:
    1. Application config setting (user preference)
    2. OS-level reduced motion preference (future)

    Returns:
        True if animations should be minimized/disabled
    """
    # Check app config first
    try:
        from core.config import Config
        config = Config()
        if hasattr(config, 'reduce_animations') and config.reduce_animations:
            return True
    except (ImportError, AttributeError):
        pass

    # In the future, could check OS settings:
    # - Windows: UISettings.AnimationsEnabled
    # - macOS: NSWorkspace.accessibilityDisplayShouldReduceMotion
    # - Linux: GTK settings

    return False


def create_property_animation(
    target,
    property_name: bytes,
    start_value,
    end_value,
    preset: AnimationPreset = AnimationPreset.FADE_IN,
    *,
    reduce_motion: bool | None = None,
):
    """
    Create a configured QPropertyAnimation with spring physics.

    Args:
        target: Target QObject
        property_name: Property to animate (e.g., b"geometry", b"opacity")
        start_value: Starting value
        end_value: Ending value
        preset: Animation preset
        reduce_motion: Override reduced motion preference

    Returns:
        Configured QPropertyAnimation

    Example:
        anim = create_property_animation(
            widget, b"pos",
            QPoint(0, -100), QPoint(0, 0),
            AnimationPreset.SLIDE_IN
        )
        anim.start()
    """
    from PyQt6.QtCore import QPropertyAnimation

    animation = QPropertyAnimation(target, property_name)
    duration = get_animation_duration(preset, reduce_motion=reduce_motion)

    animation.setDuration(duration)
    animation.setStartValue(start_value)
    animation.setEndValue(end_value)

    if duration > 0:
        animation.setEasingCurve(spring_curve(preset))

    return animation


# Animation group utilities

def create_sequential_group(*animations):
    """
    Create a sequential animation group.

    Args:
        *animations: Animations to run in sequence

    Returns:
        QSequentialAnimationGroup
    """
    from PyQt6.QtCore import QSequentialAnimationGroup

    group = QSequentialAnimationGroup()
    for anim in animations:
        group.addAnimation(anim)
    return group


def create_parallel_group(*animations):
    """
    Create a parallel animation group.

    Args:
        *animations: Animations to run simultaneously

    Returns:
        QParallelAnimationGroup
    """
    from PyQt6.QtCore import QParallelAnimationGroup

    group = QParallelAnimationGroup()
    for anim in animations:
        group.addAnimation(anim)
    return group


# Common animation patterns

class AnimationMixin:
    """
    Mixin class providing common animation methods.

    Add to widgets to get convenient animation support:

        class MyWidget(QWidget, AnimationMixin):
            def show_with_animation(self):
                self.fade_in()
    """

    def fade_in(self, duration: int | None = None):
        """Fade in the widget."""
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation

        effect = QGraphicsOpacityEffect(self)  # type: ignore[arg-type]
        self.setGraphicsEffect(effect)  # type: ignore[attr-defined]

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration or get_animation_duration(AnimationPreset.FADE_IN))
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(spring_curve(AnimationPreset.FADE_IN))
        anim.start()

        # Store reference to prevent garbage collection
        self._fade_animation = anim
        return anim

    def fade_out(self, duration: int | None = None, delete_on_finish: bool = False):
        """Fade out the widget."""
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation

        effect = self.graphicsEffect()  # type: ignore[attr-defined]
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self)  # type: ignore[arg-type]
            self.setGraphicsEffect(effect)  # type: ignore[attr-defined]

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration or get_animation_duration(AnimationPreset.FADE_OUT))
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(spring_curve(AnimationPreset.FADE_OUT))

        if delete_on_finish:
            anim.finished.connect(self.deleteLater)  # type: ignore[attr-defined]

        anim.start()
        self._fade_animation = anim
        return anim


# Constants for common values
SPRING_GENTLE: Final[SpringParameters] = SpringParameters(100, 15)
SPRING_DEFAULT: Final[SpringParameters] = SpringParameters(200, 20)
SPRING_BOUNCY: Final[SpringParameters] = SpringParameters(300, 10)
SPRING_STIFF: Final[SpringParameters] = SpringParameters(400, 30)
