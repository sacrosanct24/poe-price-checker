"""
gui_qt.themes - Theme system and color definitions for PoE Price Checker.

Supports multiple themes including:
- Dark and Light base themes
- High contrast options
- Colorblind-friendly themes (Deuteranopia, Protanopia, Tritanopia)
- Popular color schemes (Solarized, Dracula, Nord, Monokai)

Usage:
    from gui_qt.themes import Theme, get_theme_manager, COLORS

    # Get the theme manager
    manager = get_theme_manager()
    manager.set_theme(Theme.DARK)

    # Access colors
    bg_color = COLORS["background"]

    # Get stylesheet
    stylesheet = manager.get_stylesheet()
"""

# Color constants
from gui_qt.themes.colors import (
    POE_CURRENCY_COLORS,
    RARITY_COLORS,
    RARITY_COLORS_COLORBLIND,
    STAT_COLORS,
    STAT_COLORS_COLORBLIND,
    STATUS_COLORS,
    STATUS_COLORS_COLORBLIND,
    TIER_COLORS,
    TIER_COLORS_COLORBLIND,
    VALUE_COLORS,
    VALUE_COLORS_COLORBLIND,
    get_tier_color,
)

# Icons and pixmaps
from gui_qt.themes.icons import (
    apply_window_icon,
    get_app_banner_pixmap,
    get_app_icon,
    get_theme_icon_pixmap,
)

# Theme palettes
from gui_qt.themes.palettes import (
    COLORBLIND_DEUTERANOPIA_THEME,
    COLORBLIND_PROTANOPIA_THEME,
    COLORBLIND_TRITANOPIA_THEME,
    DARK_THEME,
    DRACULA_THEME,
    GRUVBOX_DARK_THEME,
    HIGH_CONTRAST_DARK_THEME,
    HIGH_CONTRAST_LIGHT_THEME,
    LIGHT_THEME,
    MONOKAI_THEME,
    NORD_THEME,
    SOLARIZED_DARK_THEME,
    SOLARIZED_LIGHT_THEME,
)

# Theme enumeration and metadata
from gui_qt.themes.theme_enum import (
    COLORBLIND_THEMES,
    THEME_BANNER_MAP,
    THEME_CATEGORIES,
    THEME_DISPLAY_NAMES,
    Theme,
)

# Theme manager
from gui_qt.themes.theme_manager import THEME_COLORS, ThemeManager, get_theme_manager


class _ColorsProxy(dict):
    """Proxy for COLORS that delegates to theme manager."""

    def __getitem__(self, key):
        return get_theme_manager().colors.get(key, "#ffffff")

    def get(self, key, default=None):
        return get_theme_manager().colors.get(key, default)

    def __contains__(self, key):
        return key in get_theme_manager().colors

    def keys(self):
        return get_theme_manager().colors.keys()

    def values(self):
        return get_theme_manager().colors.values()

    def items(self):
        return get_theme_manager().colors.items()


# Legacy COLORS dict - now a proxy to theme manager
COLORS = _ColorsProxy()


def get_app_stylesheet() -> str:
    """Get the application stylesheet for current theme."""
    return get_theme_manager().get_stylesheet()


# For backwards compatibility, APP_STYLESHEET as a string (dark theme)
APP_STYLESHEET = get_theme_manager().get_stylesheet()


def get_rarity_color(rarity: str) -> str:
    """Get the color for an item rarity."""
    rarity_lower = rarity.lower()
    return get_theme_manager().colors.get(rarity_lower, get_theme_manager().colors["text"])


def get_value_color(chaos_value: float) -> str:
    """Get the color based on chaos value."""
    c = get_theme_manager().colors
    if chaos_value >= 100:
        return c.get("high_value", "#22dd22")
    elif chaos_value >= 10:
        return c.get("medium_value", "#dddd22")
    else:
        return c.get("low_value", "#888888")


__all__ = [
    # Theme enum and metadata
    "Theme",
    "THEME_DISPLAY_NAMES",
    "THEME_CATEGORIES",
    "COLORBLIND_THEMES",
    "THEME_BANNER_MAP",
    "THEME_COLORS",
    # Color constants
    "RARITY_COLORS",
    "RARITY_COLORS_COLORBLIND",
    "VALUE_COLORS",
    "VALUE_COLORS_COLORBLIND",
    "STAT_COLORS",
    "STAT_COLORS_COLORBLIND",
    "STATUS_COLORS",
    "STATUS_COLORS_COLORBLIND",
    "POE_CURRENCY_COLORS",
    "TIER_COLORS",
    "TIER_COLORS_COLORBLIND",
    "get_tier_color",
    # Theme palettes
    "DARK_THEME",
    "LIGHT_THEME",
    "HIGH_CONTRAST_DARK_THEME",
    "HIGH_CONTRAST_LIGHT_THEME",
    "SOLARIZED_DARK_THEME",
    "SOLARIZED_LIGHT_THEME",
    "DRACULA_THEME",
    "NORD_THEME",
    "MONOKAI_THEME",
    "GRUVBOX_DARK_THEME",
    "COLORBLIND_DEUTERANOPIA_THEME",
    "COLORBLIND_PROTANOPIA_THEME",
    "COLORBLIND_TRITANOPIA_THEME",
    # Theme manager
    "ThemeManager",
    "get_theme_manager",
    # Icons
    "get_app_icon",
    "get_app_banner_pixmap",
    "get_theme_icon_pixmap",
    "apply_window_icon",
    # Legacy compatibility
    "COLORS",
    "APP_STYLESHEET",
    "get_app_stylesheet",
    "get_rarity_color",
    "get_value_color",
    # Internal (for tests)
    "_ColorsProxy",
]
