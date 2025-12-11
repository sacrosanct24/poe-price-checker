"""
Theme enumeration and display metadata.
"""

from enum import Enum
from typing import Dict, List


class Theme(Enum):
    """Available application themes."""
    # Base themes
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"

    # High contrast
    HIGH_CONTRAST_DARK = "high_contrast_dark"
    HIGH_CONTRAST_LIGHT = "high_contrast_light"

    # Popular color schemes
    SOLARIZED_DARK = "solarized_dark"
    SOLARIZED_LIGHT = "solarized_light"
    DRACULA = "dracula"
    NORD = "nord"
    MONOKAI = "monokai"
    GRUVBOX_DARK = "gruvbox_dark"

    # Colorblind-friendly themes
    COLORBLIND_DEUTERANOPIA = "colorblind_deuteranopia"  # Red-green (most common)
    COLORBLIND_PROTANOPIA = "colorblind_protanopia"      # Red-blind
    COLORBLIND_TRITANOPIA = "colorblind_tritanopia"      # Blue-yellow


# Theme display names for UI
THEME_DISPLAY_NAMES: Dict[Theme, str] = {
    Theme.DARK: "Dark",
    Theme.LIGHT: "Light",
    Theme.SYSTEM: "System Default",
    Theme.HIGH_CONTRAST_DARK: "High Contrast Dark",
    Theme.HIGH_CONTRAST_LIGHT: "High Contrast Light",
    Theme.SOLARIZED_DARK: "Solarized Dark",
    Theme.SOLARIZED_LIGHT: "Solarized Light",
    Theme.DRACULA: "Dracula",
    Theme.NORD: "Nord",
    Theme.MONOKAI: "Monokai",
    Theme.GRUVBOX_DARK: "Gruvbox Dark",
    Theme.COLORBLIND_DEUTERANOPIA: "Colorblind: Deuteranopia",
    Theme.COLORBLIND_PROTANOPIA: "Colorblind: Protanopia",
    Theme.COLORBLIND_TRITANOPIA: "Colorblind: Tritanopia",
}

# Theme categories for menu organization
THEME_CATEGORIES: Dict[str, List[Theme]] = {
    "Standard": [Theme.DARK, Theme.LIGHT, Theme.SYSTEM],
    "High Contrast": [Theme.HIGH_CONTRAST_DARK, Theme.HIGH_CONTRAST_LIGHT],
    "Color Schemes": [
        Theme.SOLARIZED_DARK, Theme.SOLARIZED_LIGHT, Theme.DRACULA,
        Theme.NORD, Theme.MONOKAI, Theme.GRUVBOX_DARK
    ],
    "Accessibility": [
        Theme.COLORBLIND_DEUTERANOPIA, Theme.COLORBLIND_PROTANOPIA,
        Theme.COLORBLIND_TRITANOPIA
    ],
}

# Themes that should use colorblind-safe colors
COLORBLIND_THEMES = {
    Theme.COLORBLIND_DEUTERANOPIA,
    Theme.COLORBLIND_PROTANOPIA,
    Theme.COLORBLIND_TRITANOPIA,
}

# Map themes to banner asset folders
THEME_BANNER_MAP: Dict[Theme, str] = {
    Theme.DARK: "default",
    Theme.LIGHT: "glow_free",
    Theme.SYSTEM: "default",
    Theme.HIGH_CONTRAST_DARK: "high_contrast",
    Theme.HIGH_CONTRAST_LIGHT: "high_contrast",
    Theme.SOLARIZED_DARK: "minimalist_dark_alt",
    Theme.SOLARIZED_LIGHT: "glow_free",
    Theme.DRACULA: "ultra_dark_cyan",
    Theme.NORD: "minimalist_dark",
    Theme.MONOKAI: "default",
    Theme.GRUVBOX_DARK: "default",
    Theme.COLORBLIND_DEUTERANOPIA: "minimalist_dark",
    Theme.COLORBLIND_PROTANOPIA: "minimalist_dark",
    Theme.COLORBLIND_TRITANOPIA: "minimalist_dark",
}
