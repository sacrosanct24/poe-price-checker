"""
Base dark and light theme palettes.
"""

from typing import Dict

# Default Dark Theme (PoE-inspired)
DARK_THEME: Dict[str, str] = {
    "background": "#1a1a1e",
    "surface": "#2a2a30",
    "surface_alt": "#252530",
    "surface_hover": "#3a3a42",
    "border": "#3a3a45",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#c8a656",          # Chaos orb gold
    "accent_blue": "#3ba4d8",     # Divine orb blue
    "accent_hover": "#d8b666",
    "button_hover": "#3d3d3d",
    "button_disabled_bg": "#1a1a1a",
    "button_disabled_text": "#666666",
    "alternate_row": "#252525",
}

# Default Light Theme
LIGHT_THEME: Dict[str, str] = {
    "background": "#f5f5f7",
    "surface": "#ffffff",
    "surface_alt": "#f0f0f2",
    "surface_hover": "#e8e8ec",
    "border": "#d0d0d5",
    "text": "#1a1a1e",
    "text_secondary": "#606068",
    "accent": "#996515",
    "accent_blue": "#2080b0",
    "accent_hover": "#b87a20",
    "button_hover": "#e0e0e5",
    "button_disabled_bg": "#f0f0f0",
    "button_disabled_text": "#a0a0a0",
    "alternate_row": "#f8f8fa",
}
