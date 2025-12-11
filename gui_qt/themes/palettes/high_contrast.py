"""
High contrast theme palettes for accessibility.
"""

from typing import Dict

# High Contrast Dark
HIGH_CONTRAST_DARK_THEME: Dict[str, str] = {
    "background": "#000000",
    "surface": "#1a1a1a",
    "surface_alt": "#0d0d0d",
    "surface_hover": "#333333",
    "border": "#ffffff",
    "text": "#ffffff",
    "text_secondary": "#cccccc",
    "accent": "#ffff00",          # Bright yellow
    "accent_blue": "#00ffff",     # Cyan
    "accent_hover": "#ffff80",
    "button_hover": "#333333",
    "button_disabled_bg": "#1a1a1a",
    "button_disabled_text": "#666666",
    "alternate_row": "#1a1a1a",
}

# High Contrast Light
HIGH_CONTRAST_LIGHT_THEME: Dict[str, str] = {
    "background": "#ffffff",
    "surface": "#ffffff",
    "surface_alt": "#f0f0f0",
    "surface_hover": "#e0e0e0",
    "border": "#000000",
    "text": "#000000",
    "text_secondary": "#333333",
    "accent": "#0000cc",          # Dark blue
    "accent_blue": "#000099",
    "accent_hover": "#0000ff",
    "button_hover": "#e0e0e0",
    "button_disabled_bg": "#f0f0f0",
    "button_disabled_text": "#666666",
    "alternate_row": "#f5f5f5",
}
