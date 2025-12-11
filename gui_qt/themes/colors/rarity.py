"""
PoE item rarity colors (consistent across themes, with colorblind variants).
"""

from typing import Dict

# Standard rarity colors
RARITY_COLORS: Dict[str, str] = {
    "unique": "#af6025",      # Unique items (orange-brown)
    "rare": "#ffff77",        # Rare items (yellow)
    "magic": "#8888ff",       # Magic items (blue)
    "normal": "#c8c8c8",      # Normal items (white/gray)
    "currency": "#aa9e82",    # Currency items (tan)
    "gem": "#1ba29b",         # Gems (teal)
    "divination": "#0ebaff",  # Divination cards (light blue)
    "prophecy": "#b54bff",    # Prophecy (purple)
}

# Colorblind-safe rarity colors (uses distinguishable colors)
RARITY_COLORS_COLORBLIND: Dict[str, str] = {
    "unique": "#e69f00",      # Orange (universally visible)
    "rare": "#f0e442",        # Yellow
    "magic": "#56b4e9",       # Sky blue
    "normal": "#999999",      # Gray
    "currency": "#cc79a7",    # Pink/mauve
    "gem": "#009e73",         # Bluish green
    "divination": "#0072b2",  # Blue
    "prophecy": "#d55e00",    # Vermillion
}
