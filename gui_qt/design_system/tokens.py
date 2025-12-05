"""
Design Tokens - Core design constants following Material Design 3.

These tokens provide the foundation for consistent spacing, elevation,
border radius, animation timing, and responsive breakpoints.

Usage:
    from gui_qt.design_system import Spacing, Duration, Easing

    # Apply consistent spacing
    layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
    layout.setSpacing(Spacing.SM)

    # Animation timing
    animation.setDuration(Duration.NORMAL)
"""

from enum import IntEnum
from typing import Final


class Spacing(IntEnum):
    """
    Spacing scale following 4px base unit (Material Design 3).

    Use these constants instead of magic numbers for consistent layouts.
    The scale is designed for 4px increments for pixel-perfect alignment.

    Guidelines:
        NONE (0px): No spacing
        XS (4px): Between tightly related elements (icon + label)
        SM (8px): Between elements in a group (form fields)
        MD (12px): Between sections within a component
        LG (16px): Between components in a container
        XL (24px): Between major sections
        XXL (32px): Page margins, hero areas
        XXXL (48px): Maximum spacing, splash screens
    """

    NONE = 0
    XS = 4      # Tight - icon/label pairs
    SM = 8      # Normal - form fields, list items
    MD = 12     # Relaxed - sections within component
    LG = 16     # Spacious - between components
    XL = 24     # Extra - major sections
    XXL = 32    # Maximum - page margins
    XXXL = 48   # Hero - splash screens, empty states


class Elevation(IntEnum):
    """
    Elevation levels for layered surfaces (Material Design 3).

    In dark mode, elevation is communicated through lighter surface colors
    rather than shadows. Each level corresponds to a surface tone.

    Guidelines:
        LEVEL_0: Base surface (main background)
        LEVEL_1: Cards, sheets (subtle lift)
        LEVEL_2: Navigation drawers, modals
        LEVEL_3: Dialogs, menus
        LEVEL_4: Tooltips, snackbars
        LEVEL_5: Maximum elevation (rare)
    """

    LEVEL_0 = 0   # Base surface
    LEVEL_1 = 1   # Cards, raised buttons
    LEVEL_2 = 2   # Navigation, sheets
    LEVEL_3 = 3   # Dialogs, search bars
    LEVEL_4 = 4   # Menus, tooltips
    LEVEL_5 = 5   # Maximum (rarely used)


# Surface overlay opacity per elevation level (Material Design 3 dark theme)
ELEVATION_OVERLAY_OPACITY: Final[dict[int, float]] = {
    Elevation.LEVEL_0: 0.0,
    Elevation.LEVEL_1: 0.05,
    Elevation.LEVEL_2: 0.08,
    Elevation.LEVEL_3: 0.11,
    Elevation.LEVEL_4: 0.12,
    Elevation.LEVEL_5: 0.14,
}


class BorderRadius(IntEnum):
    """
    Border radius scale for consistent rounding.

    Guidelines:
        NONE (0px): Sharp corners (data tables)
        XS (2px): Subtle rounding (inputs, small buttons)
        SM (4px): Default for most components
        MD (8px): Cards, dialogs
        LG (12px): Large cards, modals
        XL (16px): Prominent surfaces
        PILL (9999px): Fully rounded (pills, chips)
    """

    NONE = 0
    XS = 2      # Subtle - inputs, badges
    SM = 4      # Default - buttons, chips
    MD = 8      # Cards, panels
    LG = 12     # Large cards, dialogs
    XL = 16     # Prominent - hero cards
    PILL = 9999 # Fully rounded - pills, avatars


class Duration(IntEnum):
    """
    Animation duration presets (milliseconds).

    Based on Material Design 3 motion guidelines:
    - Shorter durations for small elements
    - Longer durations for complex transitions
    - User preference for reduced motion should be respected

    Guidelines:
        INSTANT (0ms): No animation
        FASTEST (50ms): Micro feedback (button press)
        FAST (100ms): Quick transitions (hover states)
        NORMAL (200ms): Standard transitions
        SLOW (300ms): Expanding content
        SLOWER (400ms): Complex transitions (page changes)
        SLOWEST (500ms): Large-scale motion
        SKELETON (1500ms): Loading shimmer cycle
    """

    INSTANT = 0
    FASTEST = 50    # Micro feedback
    FAST = 100      # Hover states
    NORMAL = 200    # Standard transitions
    SLOW = 300      # Content reveal
    SLOWER = 400    # Complex transitions
    SLOWEST = 500   # Large-scale motion
    SKELETON = 1500 # Shimmer animation cycle


class Easing:
    """
    Easing curves for animations (CSS/Qt bezier format).

    Material Design 3 uses "expressive" motion with spring-like physics.
    These curves provide organic, natural-feeling animations.

    Standard: Default for most transitions
    Emphasized: For important state changes (dialogs appearing)
    Decelerate: For entering elements (slide in)
    Accelerate: For exiting elements (slide out)
    """

    # Standard easing - most transitions
    STANDARD: Final[str] = "cubic-bezier(0.2, 0.0, 0, 1.0)"
    STANDARD_DECELERATE: Final[str] = "cubic-bezier(0, 0, 0, 1)"
    STANDARD_ACCELERATE: Final[str] = "cubic-bezier(0.3, 0, 1, 1)"

    # Emphasized easing - important transitions
    EMPHASIZED: Final[str] = "cubic-bezier(0.2, 0.0, 0, 1.0)"
    EMPHASIZED_DECELERATE: Final[str] = "cubic-bezier(0.05, 0.7, 0.1, 1.0)"
    EMPHASIZED_ACCELERATE: Final[str] = "cubic-bezier(0.3, 0.0, 0.8, 0.15)"

    # Spring parameters for QPropertyAnimation
    # (stiffness, damping, mass) - approximated for Qt
    SPRING_GENTLE: Final[tuple[float, float, float]] = (100.0, 15.0, 1.0)
    SPRING_DEFAULT: Final[tuple[float, float, float]] = (200.0, 20.0, 1.0)
    SPRING_BOUNCY: Final[tuple[float, float, float]] = (300.0, 10.0, 1.0)
    SPRING_STIFF: Final[tuple[float, float, float]] = (400.0, 30.0, 1.0)


class Breakpoints(IntEnum):
    """
    Responsive breakpoints for adaptive layouts.

    While this is a desktop app, these help with:
    - Multi-monitor support (different DPI)
    - Window resize handling
    - Compact vs comfortable layouts

    Guidelines:
        COMPACT: Small windows, sidebars collapsed
        MEDIUM: Standard desktop window
        EXPANDED: Large/multi-monitor layouts
    """

    COMPACT = 600   # Mobile-like, very narrow
    MEDIUM = 840    # Tablet, narrow desktop
    EXPANDED = 1200 # Standard desktop
    LARGE = 1600    # Wide desktop
    XLARGE = 1920   # Full HD and above


# Minimum touch target size (WCAG 2.2 Level AAA)
MIN_TOUCH_TARGET: Final[int] = 44

# Minimum contrast ratios (WCAG 2.2)
CONTRAST_RATIO_AA_NORMAL: Final[float] = 4.5
CONTRAST_RATIO_AA_LARGE: Final[float] = 3.0
CONTRAST_RATIO_AAA_NORMAL: Final[float] = 7.0
CONTRAST_RATIO_AAA_LARGE: Final[float] = 4.5

# Focus indicator requirements (WCAG 2.2)
FOCUS_INDICATOR_MIN_WIDTH: Final[int] = 2
FOCUS_INDICATOR_MIN_CONTRAST: Final[float] = 3.0


def get_elevation_color(base_color: str, level: Elevation) -> str:
    """
    Calculate surface color with elevation overlay.

    In Material Design 3 dark theme, elevation is shown by
    adding a white overlay to the surface color.

    Args:
        base_color: Base surface color (hex format)
        level: Elevation level

    Returns:
        Color with elevation overlay applied (hex format)
    """
    if level == Elevation.LEVEL_0:
        return base_color

    # Parse base color
    base = base_color.lstrip("#")
    r, g, b = int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16)

    # Apply white overlay based on elevation
    opacity = ELEVATION_OVERLAY_OPACITY.get(level, 0.0)
    r = min(255, int(r + (255 - r) * opacity))
    g = min(255, int(g + (255 - g) * opacity))
    b = min(255, int(b + (255 - b) * opacity))

    return f"#{r:02x}{g:02x}{b:02x}"
