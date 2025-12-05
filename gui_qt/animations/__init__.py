"""
Animations Package - Material Design 3 expressive motion system.

This package provides animation utilities for creating smooth, organic
motion following Material Design 3 guidelines with spring physics.

Modules:
    spring_animation: Spring-based physics animations
    transitions: Page/panel transition effects
    feedback: Button press, success/error states

Usage:
    from gui_qt.animations import (
        SpringAnimation,
        SlideTransition,
        ButtonFeedback,
        animate_widget,
    )

    # Create spring animation
    anim = SpringAnimation(widget, "geometry")
    anim.animate_to(target_rect)

    # Add button feedback
    feedback = ButtonFeedback(button)
    feedback.on_press()
"""

from gui_qt.animations.spring_animation import (
    SpringAnimation,
    spring_animate,
    animate_widget,
)
from gui_qt.animations.transitions import (
    SlideTransition,
    FadeTransition,
    ScaleTransition,
    TransitionDirection,
    create_page_transition,
)
from gui_qt.animations.feedback import (
    ButtonFeedback,
    SuccessFeedback,
    ErrorFeedback,
    RippleEffect,
    PressEffect,
)

__all__ = [
    # Spring animations
    "SpringAnimation",
    "spring_animate",
    "animate_widget",
    # Transitions
    "SlideTransition",
    "FadeTransition",
    "ScaleTransition",
    "TransitionDirection",
    "create_page_transition",
    # Feedback
    "ButtonFeedback",
    "SuccessFeedback",
    "ErrorFeedback",
    "RippleEffect",
    "PressEffect",
]
