"""
Status and stat colors for build panels and item states.
"""

from typing import Dict

# Stat colors for build panel
STAT_COLORS: Dict[str, str] = {
    "life": "#e85050",            # Life red
    "es": "#7888ff",              # Energy shield blue
    "mana": "#5080d0",            # Mana blue
}

STAT_COLORS_COLORBLIND: Dict[str, str] = {
    "life": "#d55e00",            # Vermillion (instead of red)
    "es": "#56b4e9",              # Sky blue
    "mana": "#0072b2",            # Blue
}

# Status colors for item states
STATUS_COLORS: Dict[str, str] = {
    "upgrade": "#3ba4d8",         # Upgrade indicator (divine blue)
    "fractured": "#a29162",       # Fractured items
    "synthesised": "#6a1b9a",     # Synthesised items
    "corrupted": "#d20000",       # Corrupted items
    "crafted": "#b4b4ff",         # Crafted mods (light blue)
}

STATUS_COLORS_COLORBLIND: Dict[str, str] = {
    "upgrade": "#56b4e9",         # Sky blue
    "fractured": "#cc79a7",       # Pink
    "synthesised": "#0072b2",     # Blue
    "corrupted": "#d55e00",       # Vermillion (instead of red)
    "crafted": "#009e73",         # Bluish green
}
