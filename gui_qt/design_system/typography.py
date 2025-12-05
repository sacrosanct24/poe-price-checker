"""
Typography System - Font scale and text style utilities.

Provides a systematic approach to typography following Material Design 3
type scale with accessibility considerations (WCAG 2.2).

Usage:
    from gui_qt.design_system import Typography, get_font_style

    # Apply text style
    label.setStyleSheet(get_font_style("body_large"))

    # Get font family
    font = QFont(Typography.FONT_FAMILY, Typography.SIZES["base"])
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Final


class FontSize(IntEnum):
    """
    Font size scale (pixels).

    Based on Material Design 3 type scale, adapted for desktop.
    Follows a modular scale (ratio ~1.2) for visual harmony.

    Guidelines:
        XS (11px): Captions, fine print, timestamps
        SM (13px): Secondary text, labels, help text
        BASE (15px): Body text, primary content
        LG (18px): Section headings, emphasized text
        XL (22px): Page titles, dialog headers
        XXL (28px): Hero text, splash screens
        DISPLAY (34px): Display text (rare)
    """

    XS = 11     # Captions, timestamps
    SM = 13     # Labels, secondary text
    BASE = 15   # Body text (default)
    LG = 18     # Section headers
    XL = 22     # Page titles
    XXL = 28    # Hero text
    DISPLAY = 34  # Display (rare)


class FontWeight(IntEnum):
    """
    Font weight values.

    Use these instead of magic numbers for consistent weight hierarchy.

    Guidelines:
        LIGHT (300): De-emphasized text
        REGULAR (400): Body text
        MEDIUM (500): Emphasized labels
        SEMIBOLD (600): Headings, buttons
        BOLD (700): Strong emphasis
    """

    LIGHT = 300
    REGULAR = 400
    MEDIUM = 500
    SEMIBOLD = 600
    BOLD = 700


class LineHeight:
    """
    Line height multipliers for different contexts.

    Guidelines:
        TIGHT (1.2): Headings, single-line
        NORMAL (1.4): Labels, short text
        RELAXED (1.5): Body text, readable paragraphs
        LOOSE (1.75): Long-form content
    """

    TIGHT: Final[float] = 1.2
    NORMAL: Final[float] = 1.4
    RELAXED: Final[float] = 1.5
    LOOSE: Final[float] = 1.75


class Typography:
    """
    Central typography configuration.

    This class contains all typography constants and provides
    the foundation for consistent text styling.
    """

    # Primary font stack (system fonts for performance)
    FONT_FAMILY: Final[str] = '"Segoe UI", "SF Pro Display", "Roboto", "Helvetica Neue", sans-serif'

    # Monospace font for code/data
    FONT_MONO: Final[str] = '"Cascadia Code", "SF Mono", "Consolas", "Monaco", monospace'

    # Font sizes (convenience access)
    SIZES: Final[dict[str, int]] = {
        "xs": FontSize.XS,
        "sm": FontSize.SM,
        "base": FontSize.BASE,
        "lg": FontSize.LG,
        "xl": FontSize.XL,
        "xxl": FontSize.XXL,
        "display": FontSize.DISPLAY,
    }

    # Font weights
    WEIGHTS: Final[dict[str, int]] = {
        "light": FontWeight.LIGHT,
        "regular": FontWeight.REGULAR,
        "medium": FontWeight.MEDIUM,
        "semibold": FontWeight.SEMIBOLD,
        "bold": FontWeight.BOLD,
    }

    # Line heights
    LINE_HEIGHTS: Final[dict[str, float]] = {
        "tight": LineHeight.TIGHT,
        "normal": LineHeight.NORMAL,
        "relaxed": LineHeight.RELAXED,
        "loose": LineHeight.LOOSE,
    }

    # Letter spacing (em units)
    LETTER_SPACING: Final[dict[str, float]] = {
        "tight": -0.02,   # Headings
        "normal": 0.0,    # Body
        "wide": 0.02,     # All caps, labels
        "wider": 0.05,    # Sparse text
    }


@dataclass(frozen=True, slots=True)
class TextStyle:
    """
    Complete text style definition.

    Combines font size, weight, line height, and letter spacing
    into a single immutable style definition.
    """

    size: int
    weight: int
    line_height: float
    letter_spacing: float = 0.0
    font_family: str = Typography.FONT_FAMILY


# Pre-defined text styles following Material Design 3 type scale
TEXT_STYLES: Final[dict[str, TextStyle]] = {
    # Display styles (hero text)
    "display_large": TextStyle(
        size=57, weight=FontWeight.REGULAR,
        line_height=LineHeight.TIGHT, letter_spacing=-0.02
    ),
    "display_medium": TextStyle(
        size=45, weight=FontWeight.REGULAR,
        line_height=LineHeight.TIGHT, letter_spacing=-0.02
    ),
    "display_small": TextStyle(
        size=FontSize.DISPLAY, weight=FontWeight.REGULAR,
        line_height=LineHeight.TIGHT, letter_spacing=-0.01
    ),

    # Headline styles (page titles)
    "headline_large": TextStyle(
        size=FontSize.XXL, weight=FontWeight.SEMIBOLD,
        line_height=LineHeight.TIGHT
    ),
    "headline_medium": TextStyle(
        size=FontSize.XL, weight=FontWeight.SEMIBOLD,
        line_height=LineHeight.TIGHT
    ),
    "headline_small": TextStyle(
        size=FontSize.LG, weight=FontWeight.SEMIBOLD,
        line_height=LineHeight.NORMAL
    ),

    # Title styles (section headers)
    "title_large": TextStyle(
        size=FontSize.XL, weight=FontWeight.MEDIUM,
        line_height=LineHeight.NORMAL
    ),
    "title_medium": TextStyle(
        size=FontSize.LG, weight=FontWeight.MEDIUM,
        line_height=LineHeight.NORMAL
    ),
    "title_small": TextStyle(
        size=FontSize.BASE, weight=FontWeight.MEDIUM,
        line_height=LineHeight.NORMAL
    ),

    # Body styles (content)
    "body_large": TextStyle(
        size=FontSize.BASE, weight=FontWeight.REGULAR,
        line_height=LineHeight.RELAXED
    ),
    "body_medium": TextStyle(
        size=FontSize.SM, weight=FontWeight.REGULAR,
        line_height=LineHeight.RELAXED
    ),
    "body_small": TextStyle(
        size=FontSize.XS, weight=FontWeight.REGULAR,
        line_height=LineHeight.NORMAL
    ),

    # Label styles (UI elements)
    "label_large": TextStyle(
        size=FontSize.BASE, weight=FontWeight.MEDIUM,
        line_height=LineHeight.NORMAL
    ),
    "label_medium": TextStyle(
        size=FontSize.SM, weight=FontWeight.MEDIUM,
        line_height=LineHeight.NORMAL
    ),
    "label_small": TextStyle(
        size=FontSize.XS, weight=FontWeight.MEDIUM,
        line_height=LineHeight.NORMAL, letter_spacing=0.02
    ),

    # Legacy/convenience aliases
    "caption": TextStyle(
        size=FontSize.XS, weight=FontWeight.REGULAR,
        line_height=LineHeight.NORMAL
    ),
    "button": TextStyle(
        size=FontSize.SM, weight=FontWeight.MEDIUM,
        line_height=LineHeight.TIGHT, letter_spacing=0.01
    ),
    "overline": TextStyle(
        size=FontSize.XS, weight=FontWeight.MEDIUM,
        line_height=LineHeight.NORMAL, letter_spacing=0.05
    ),
}


def get_font_style(style_name: str, color: str | None = None) -> str:
    """
    Generate QSS font style string for a named text style.

    Args:
        style_name: Name of the text style (e.g., "body_large", "headline_medium")
        color: Optional color to include in the style

    Returns:
        QSS-compatible style string

    Example:
        label.setStyleSheet(get_font_style("headline_small", "#ffffff"))
    """
    style = TEXT_STYLES.get(style_name)
    if not style:
        style = TEXT_STYLES["body_medium"]  # Fallback

    parts = [
        f"font-family: {style.font_family};",
        f"font-size: {style.size}px;",
        f"font-weight: {style.weight};",
    ]

    if style.letter_spacing != 0:
        # Convert em to pixels (approximate)
        px_spacing = round(style.size * style.letter_spacing, 1)
        parts.append(f"letter-spacing: {px_spacing}px;")

    if color:
        parts.append(f"color: {color};")

    return " ".join(parts)


def get_line_height_px(style_name: str) -> int:
    """
    Get line height in pixels for a text style.

    Useful for calculating widget heights.

    Args:
        style_name: Name of the text style

    Returns:
        Line height in pixels
    """
    style = TEXT_STYLES.get(style_name, TEXT_STYLES["body_medium"])
    return round(style.size * style.line_height)


def get_scaled_size(base_size: int, scale_factor: float) -> int:
    """
    Scale font size by a factor (for accessibility).

    Args:
        base_size: Base font size in pixels
        scale_factor: Multiplier (e.g., 1.25 for 125%)

    Returns:
        Scaled size in pixels (minimum 10px)
    """
    return max(10, round(base_size * scale_factor))


# Minimum readable font size (WCAG guidance)
MIN_READABLE_SIZE: Final[int] = 10

# Large text threshold (WCAG 2.2)
# Text is "large" if >= 18pt (24px) regular or >= 14pt (19px) bold
LARGE_TEXT_REGULAR: Final[int] = 24
LARGE_TEXT_BOLD: Final[int] = 19
