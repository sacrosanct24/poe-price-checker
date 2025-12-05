"""
Design System - Centralized design tokens and utilities.

This package provides the foundation for consistent UI/UX across the application
following Material Design 3 and WCAG 2.2 guidelines.

Modules:
    tokens: Core design tokens (spacing, colors, elevation)
    typography: Font scale system and text styles
    spacing: Layout spacing utilities and helpers
    animations: Animation presets and timing functions
"""

from gui_qt.design_system.tokens import (
    Spacing,
    Elevation,
    BorderRadius,
    Duration,
    Easing,
    Breakpoints,
)
from gui_qt.design_system.typography import (
    Typography,
    FontSize,
    FontWeight,
    LineHeight,
    get_font_style,
)
from gui_qt.design_system.spacing import (
    spacing,
    margin,
    padding,
    gap,
    SpacingHelper,
)
from gui_qt.design_system.animations import (
    AnimationPreset,
    SpringParameters,
    spring_curve,
    get_animation_duration,
    should_reduce_motion,
)

__all__ = [
    # Tokens
    "Spacing",
    "Elevation",
    "BorderRadius",
    "Duration",
    "Easing",
    "Breakpoints",
    # Typography
    "Typography",
    "FontSize",
    "FontWeight",
    "LineHeight",
    "get_font_style",
    # Spacing
    "spacing",
    "margin",
    "padding",
    "gap",
    "SpacingHelper",
    # Animations
    "AnimationPreset",
    "SpringParameters",
    "spring_curve",
    "get_animation_duration",
    "should_reduce_motion",
]
