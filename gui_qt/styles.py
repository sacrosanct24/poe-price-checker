"""
gui_qt.styles - Theme system and color definitions for PoE Price Checker.

COMPATIBILITY SHIM: This module re-exports from gui_qt.themes for backward compatibility.
New code should import directly from gui_qt.themes.

Supports multiple themes including:
- Dark and Light base themes
- High contrast options
- Colorblind-friendly themes (Deuteranopia, Protanopia, Tritanopia)
- Popular color schemes (Solarized, Dracula, Nord, Monokai)
"""

# Re-export everything from the new themes package for backward compatibility
from gui_qt.themes import (
    # Theme enum and metadata
    Theme,
    THEME_DISPLAY_NAMES,
    THEME_CATEGORIES,
    COLORBLIND_THEMES,
    THEME_BANNER_MAP,
    THEME_COLORS,
    # Color constants
    RARITY_COLORS,
    RARITY_COLORS_COLORBLIND,
    VALUE_COLORS,
    VALUE_COLORS_COLORBLIND,
    STAT_COLORS,
    STAT_COLORS_COLORBLIND,
    STATUS_COLORS,
    STATUS_COLORS_COLORBLIND,
    POE_CURRENCY_COLORS,
    TIER_COLORS,
    TIER_COLORS_COLORBLIND,
    get_tier_color,
    # Theme palettes
    DARK_THEME,
    LIGHT_THEME,
    HIGH_CONTRAST_DARK_THEME,
    HIGH_CONTRAST_LIGHT_THEME,
    SOLARIZED_DARK_THEME,
    SOLARIZED_LIGHT_THEME,
    DRACULA_THEME,
    NORD_THEME,
    MONOKAI_THEME,
    GRUVBOX_DARK_THEME,
    COLORBLIND_DEUTERANOPIA_THEME,
    COLORBLIND_PROTANOPIA_THEME,
    COLORBLIND_TRITANOPIA_THEME,
    # Theme manager
    ThemeManager,
    get_theme_manager,
    # Icons
    get_app_icon,
    get_app_banner_pixmap,
    get_theme_icon_pixmap,
    apply_window_icon,
    # Legacy compatibility
    COLORS,
    APP_STYLESHEET,
    get_app_stylesheet,
    get_rarity_color,
    get_value_color,
)

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
]
