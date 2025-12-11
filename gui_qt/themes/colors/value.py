"""
Value indicator colors for item pricing.
"""

from typing import Dict

# Standard value colors
VALUE_COLORS: Dict[str, str] = {
    "high_value": "#22dd22",      # High value items (green)
    "medium_value": "#dddd22",    # Medium value items (yellow)
    "low_value": "#888888",       # Low value items (gray)
}

# Colorblind-safe value colors
VALUE_COLORS_COLORBLIND: Dict[str, str] = {
    "high_value": "#0072b2",      # Blue (instead of green)
    "medium_value": "#e69f00",    # Orange (instead of yellow)
    "low_value": "#999999",       # Gray
}
