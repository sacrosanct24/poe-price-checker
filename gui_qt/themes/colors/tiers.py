"""
Mod tier colors for affix tier highlighting.
"""

from typing import Dict

# Standard tier colors
TIER_COLORS: Dict[str, str] = {
    "t1": "#ffcc00",              # T1 - Gold (best tier)
    "t2": "#66bbff",              # T2 - Blue
    "t3": "#ffffff",              # T3 - White
    "t4": "#aaaaaa",              # T4 - Light gray
    "t5": "#888888",              # T5+ - Gray (lower tiers)
    "crafted": "#b4b4ff",         # Crafted mods - Light purple
    "implicit": "#8888ff",        # Implicit mods - Magic blue
}

# Colorblind-safe tier colors
TIER_COLORS_COLORBLIND: Dict[str, str] = {
    "t1": "#e69f00",              # T1 - Orange (universally visible)
    "t2": "#56b4e9",              # T2 - Sky blue
    "t3": "#f0e442",              # T3 - Yellow
    "t4": "#cc79a7",              # T4 - Pink
    "t5": "#999999",              # T5+ - Gray
    "crafted": "#009e73",         # Crafted - Bluish green
    "implicit": "#0072b2",        # Implicit - Blue
}


def get_tier_color(tier: int, is_colorblind: bool = False) -> str:
    """
    Get the color for a given affix tier.

    Args:
        tier: Tier number (1 = best, 5+ = lowest)
        is_colorblind: Whether to use colorblind-friendly colors

    Returns:
        Hex color string
    """
    colors = TIER_COLORS_COLORBLIND if is_colorblind else TIER_COLORS

    if tier == 1:
        return colors["t1"]
    elif tier == 2:
        return colors["t2"]
    elif tier == 3:
        return colors["t3"]
    elif tier == 4:
        return colors["t4"]
    else:
        return colors["t5"]
