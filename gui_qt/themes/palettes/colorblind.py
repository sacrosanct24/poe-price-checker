"""
Colorblind-friendly theme palettes.
"""

from typing import Dict

# Colorblind: Deuteranopia (red-green, most common ~6% of males)
COLORBLIND_DEUTERANOPIA_THEME: Dict[str, str] = {
    "background": "#1e2029",
    "surface": "#2a2d38",
    "surface_alt": "#252830",
    "surface_hover": "#3a3e4a",
    "border": "#404552",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#56b4e9",          # Sky blue (safe)
    "accent_blue": "#0072b2",     # Blue
    "accent_hover": "#7bc8f0",
    "button_hover": "#3a3e4a",
    "button_disabled_bg": "#1e2029",
    "button_disabled_text": "#666666",
    "alternate_row": "#252830",
}

# Colorblind: Protanopia (red-blind)
COLORBLIND_PROTANOPIA_THEME: Dict[str, str] = {
    "background": "#1e2029",
    "surface": "#2a2d38",
    "surface_alt": "#252830",
    "surface_hover": "#3a3e4a",
    "border": "#404552",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#e69f00",          # Orange (safe)
    "accent_blue": "#56b4e9",     # Sky blue
    "accent_hover": "#f0b020",
    "button_hover": "#3a3e4a",
    "button_disabled_bg": "#1e2029",
    "button_disabled_text": "#666666",
    "alternate_row": "#252830",
}

# Colorblind: Tritanopia (blue-yellow)
COLORBLIND_TRITANOPIA_THEME: Dict[str, str] = {
    "background": "#1e2029",
    "surface": "#2a2d38",
    "surface_alt": "#252830",
    "surface_hover": "#3a3e4a",
    "border": "#404552",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#d55e00",          # Vermillion (safe)
    "accent_blue": "#cc79a7",     # Pink
    "accent_hover": "#e87830",
    "button_hover": "#3a3e4a",
    "button_disabled_bg": "#1e2029",
    "button_disabled_text": "#666666",
    "alternate_row": "#252830",
}
