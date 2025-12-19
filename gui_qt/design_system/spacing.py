"""
Spacing Utilities - Helper functions for consistent layout spacing.

Provides convenience functions and classes for applying spacing tokens
to Qt layouts and widgets.

Usage:
    from gui_qt.design_system import spacing, margin, padding, SpacingHelper

    # Quick spacing values
    layout.setSpacing(spacing(2))  # Returns 8 (2 * 4px base unit)

    # Margin helper
    layout.setContentsMargins(*margin("md"))  # Returns (12, 12, 12, 12)

    # SpacingHelper for complex layouts
    helper = SpacingHelper()
    helper.apply_card_spacing(card_layout)
"""

from typing import Final, Literal

from gui_qt.design_system.tokens import Spacing


# Base spacing unit (4px per Material Design 3)
BASE_UNIT: Final[int] = 4


def spacing(multiplier: int = 1) -> int:
    """
    Calculate spacing value from base unit multiplier.

    Args:
        multiplier: Number of base units (4px each)

    Returns:
        Spacing in pixels

    Examples:
        spacing(1)  # 4px
        spacing(2)  # 8px
        spacing(4)  # 16px
    """
    return BASE_UNIT * multiplier


def margin(
    size: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md"
) -> tuple[int, int, int, int]:
    """
    Get uniform margins for layout.

    Args:
        size: Named size or explicit pixel value

    Returns:
        Tuple of (left, top, right, bottom) margins

    Example:
        layout.setContentsMargins(*margin("lg"))
    """
    if isinstance(size, int):
        return (size, size, size, size)

    value = _get_spacing_value(size)
    return (value, value, value, value)


def margin_xy(
    x: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md",
    y: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md",
) -> tuple[int, int, int, int]:
    """
    Get asymmetric margins (horizontal/vertical).

    Args:
        x: Horizontal margin (left + right)
        y: Vertical margin (top + bottom)

    Returns:
        Tuple of (left, top, right, bottom) margins
    """
    h = _get_spacing_value(x) if isinstance(x, str) else x
    v = _get_spacing_value(y) if isinstance(y, str) else y
    return (h, v, h, v)


def margin_ltrb(
    left: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md",
    top: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md",
    right: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md",
    bottom: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md",
) -> tuple[int, int, int, int]:
    """
    Get explicit margins for each side.

    Args:
        left, top, right, bottom: Individual margins

    Returns:
        Tuple of margins
    """
    left_val = _get_spacing_value(left) if isinstance(left, str) else left
    t = _get_spacing_value(top) if isinstance(top, str) else top
    r = _get_spacing_value(right) if isinstance(right, str) else right
    b = _get_spacing_value(bottom) if isinstance(bottom, str) else bottom
    return (left_val, t, r, b)


def padding(
    size: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "md"
) -> tuple[int, int, int, int]:
    """
    Get uniform padding (alias for margin).

    Args:
        size: Named size or explicit pixel value

    Returns:
        Tuple of (left, top, right, bottom) padding
    """
    return margin(size)


def gap(
    size: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"] | int = "sm"
) -> int:
    """
    Get gap/spacing value for layouts.

    Args:
        size: Named size or explicit pixel value

    Returns:
        Gap in pixels

    Example:
        layout.setSpacing(gap("md"))
    """
    if isinstance(size, int):
        return size
    return _get_spacing_value(size)


def _get_spacing_value(
    name: Literal["none", "xs", "sm", "md", "lg", "xl", "xxl"]
) -> int:
    """Get spacing value from name."""
    mapping = {
        "none": Spacing.NONE,
        "xs": Spacing.XS,
        "sm": Spacing.SM,
        "md": Spacing.MD,
        "lg": Spacing.LG,
        "xl": Spacing.XL,
        "xxl": Spacing.XXL,
    }
    return mapping.get(name, Spacing.MD)


class SpacingHelper:
    """
    Helper class for applying consistent spacing patterns.

    Provides pre-configured spacing for common layout scenarios.

    Example:
        helper = SpacingHelper()
        helper.apply_dialog_spacing(dialog_layout)
        helper.apply_card_spacing(card_layout)
    """

    def __init__(self, scale: float = 1.0):
        """
        Initialize spacing helper.

        Args:
            scale: Scale factor for accessibility (1.0 = normal)
        """
        self._scale = scale

    def _scaled(self, value: int) -> int:
        """Apply scale factor to spacing value."""
        return round(value * self._scale)

    def apply_page_spacing(self, layout) -> None:
        """
        Apply page-level spacing.

        Use for main content areas with generous breathing room.
        """
        m = self._scaled(Spacing.XL)
        s = self._scaled(Spacing.LG)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(s)

    def apply_section_spacing(self, layout) -> None:
        """
        Apply section-level spacing.

        Use for groups within a page.
        """
        m = self._scaled(Spacing.LG)
        s = self._scaled(Spacing.MD)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(s)

    def apply_card_spacing(self, layout) -> None:
        """
        Apply card/panel spacing.

        Use for contained elements like cards, panels, or group boxes.
        """
        m = self._scaled(Spacing.MD)
        s = self._scaled(Spacing.SM)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(s)

    def apply_form_spacing(self, layout) -> None:
        """
        Apply form spacing.

        Use for input forms with labels and fields.
        """
        m = self._scaled(Spacing.MD)
        s = self._scaled(Spacing.SM)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(s)

    def apply_dialog_spacing(self, layout) -> None:
        """
        Apply dialog spacing.

        Use for dialog content layouts.
        """
        m = self._scaled(Spacing.LG)
        s = self._scaled(Spacing.MD)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(s)

    def apply_button_row_spacing(self, layout) -> None:
        """
        Apply button row spacing.

        Use for horizontal button groups (OK/Cancel).
        """
        layout.setContentsMargins(0, self._scaled(Spacing.MD), 0, 0)
        layout.setSpacing(self._scaled(Spacing.SM))

    def apply_toolbar_spacing(self, layout) -> None:
        """
        Apply toolbar spacing.

        Use for compact horizontal tool bars.
        """
        m = self._scaled(Spacing.XS)
        s = self._scaled(Spacing.XS)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(s)

    def apply_list_spacing(self, layout) -> None:
        """
        Apply list item spacing.

        Use for vertical lists of similar items.
        """
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._scaled(Spacing.XS))

    def apply_compact_spacing(self, layout) -> None:
        """
        Apply compact spacing.

        Use when space is limited.
        """
        m = self._scaled(Spacing.XS)
        s = self._scaled(Spacing.XS)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(s)

    def apply_zero_spacing(self, layout) -> None:
        """
        Remove all spacing.

        Use for layouts that manage spacing themselves.
        """
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)


# Default spacing helper instance
_default_helper: SpacingHelper | None = None


def get_spacing_helper(scale: float = 1.0) -> SpacingHelper:
    """
    Get or create a spacing helper with the given scale.

    Args:
        scale: Scale factor (1.0 = normal)

    Returns:
        SpacingHelper instance
    """
    global _default_helper
    if scale != 1.0:
        return SpacingHelper(scale)
    if _default_helper is None:
        _default_helper = SpacingHelper(scale)
    return _default_helper


# Convenience constants for common patterns
MARGIN_PAGE: Final[tuple[int, int, int, int]] = margin("xl")
MARGIN_SECTION: Final[tuple[int, int, int, int]] = margin("lg")
MARGIN_CARD: Final[tuple[int, int, int, int]] = margin("md")
MARGIN_FORM: Final[tuple[int, int, int, int]] = margin("md")
MARGIN_COMPACT: Final[tuple[int, int, int, int]] = margin("xs")
MARGIN_NONE: Final[tuple[int, int, int, int]] = margin("none")

GAP_TIGHT: Final[int] = gap("xs")
GAP_NORMAL: Final[int] = gap("sm")
GAP_RELAXED: Final[int] = gap("md")
GAP_SPACIOUS: Final[int] = gap("lg")
