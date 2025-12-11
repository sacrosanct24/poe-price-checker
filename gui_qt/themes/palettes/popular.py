"""
Popular color scheme theme palettes (Solarized, Dracula, Nord, etc.).
"""

from typing import Dict

# Solarized Dark
SOLARIZED_DARK_THEME: Dict[str, str] = {
    "background": "#002b36",
    "surface": "#073642",
    "surface_alt": "#002b36",
    "surface_hover": "#094959",
    "border": "#586e75",
    "text": "#839496",
    "text_secondary": "#657b83",
    "accent": "#b58900",          # Yellow
    "accent_blue": "#268bd2",     # Blue
    "accent_hover": "#cb4b16",    # Orange
    "button_hover": "#094959",
    "button_disabled_bg": "#002b36",
    "button_disabled_text": "#586e75",
    "alternate_row": "#073642",
}

# Solarized Light
SOLARIZED_LIGHT_THEME: Dict[str, str] = {
    "background": "#fdf6e3",
    "surface": "#eee8d5",
    "surface_alt": "#fdf6e3",
    "surface_hover": "#e4ddc8",
    "border": "#93a1a1",
    "text": "#657b83",
    "text_secondary": "#839496",
    "accent": "#b58900",
    "accent_blue": "#268bd2",
    "accent_hover": "#cb4b16",
    "button_hover": "#e4ddc8",
    "button_disabled_bg": "#fdf6e3",
    "button_disabled_text": "#93a1a1",
    "alternate_row": "#eee8d5",
}

# Dracula
DRACULA_THEME: Dict[str, str] = {
    "background": "#282a36",
    "surface": "#44475a",
    "surface_alt": "#343746",
    "surface_hover": "#555970",
    "border": "#6272a4",
    "text": "#f8f8f2",
    "text_secondary": "#6272a4",
    "accent": "#ff79c6",          # Pink
    "accent_blue": "#8be9fd",     # Cyan
    "accent_hover": "#ff92d0",
    "button_hover": "#555970",
    "button_disabled_bg": "#343746",
    "button_disabled_text": "#6272a4",
    "alternate_row": "#343746",
}

# Nord
NORD_THEME: Dict[str, str] = {
    "background": "#2e3440",
    "surface": "#3b4252",
    "surface_alt": "#2e3440",
    "surface_hover": "#434c5e",
    "border": "#4c566a",
    "text": "#eceff4",
    "text_secondary": "#d8dee9",
    "accent": "#88c0d0",          # Frost
    "accent_blue": "#81a1c1",     # Storm
    "accent_hover": "#8fbcbb",
    "button_hover": "#434c5e",
    "button_disabled_bg": "#2e3440",
    "button_disabled_text": "#4c566a",
    "alternate_row": "#3b4252",
}

# Monokai
MONOKAI_THEME: Dict[str, str] = {
    "background": "#272822",
    "surface": "#3e3d32",
    "surface_alt": "#272822",
    "surface_hover": "#49483e",
    "border": "#75715e",
    "text": "#f8f8f2",
    "text_secondary": "#75715e",
    "accent": "#f92672",          # Pink
    "accent_blue": "#66d9ef",     # Cyan
    "accent_hover": "#fd5ff0",
    "button_hover": "#49483e",
    "button_disabled_bg": "#272822",
    "button_disabled_text": "#75715e",
    "alternate_row": "#3e3d32",
}

# Gruvbox Dark
GRUVBOX_DARK_THEME: Dict[str, str] = {
    "background": "#282828",
    "surface": "#3c3836",
    "surface_alt": "#282828",
    "surface_hover": "#504945",
    "border": "#665c54",
    "text": "#ebdbb2",
    "text_secondary": "#a89984",
    "accent": "#fabd2f",          # Yellow
    "accent_blue": "#83a598",     # Aqua
    "accent_hover": "#fe8019",    # Orange
    "button_hover": "#504945",
    "button_disabled_bg": "#282828",
    "button_disabled_text": "#665c54",
    "alternate_row": "#3c3836",
}
