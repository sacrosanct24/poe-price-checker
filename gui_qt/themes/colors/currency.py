"""
PoE currency accent colors for user customization.
"""

from typing import Dict

POE_CURRENCY_COLORS: Dict[str, Dict[str, str]] = {
    "chaos": {
        "name": "Chaos Orb",
        "accent": "#c8a656",           # Gold
        "accent_hover": "#d8b666",
        "accent_blue": "#3ba4d8",
    },
    "divine": {
        "name": "Divine Orb",
        "accent": "#3ba4d8",           # Blue
        "accent_hover": "#5bc4f8",
        "accent_blue": "#c8a656",      # Swap for contrast
    },
    "exalt": {
        "name": "Exalted Orb",
        "accent": "#a89090",           # Silver/gray
        "accent_hover": "#c8b0b0",
        "accent_blue": "#3ba4d8",
    },
    "mirror": {
        "name": "Mirror of Kalandra",
        "accent": "#50c8ff",           # Cyan/mirror blue
        "accent_hover": "#70e8ff",
        "accent_blue": "#c8a656",
    },
    "alchemy": {
        "name": "Orb of Alchemy",
        "accent": "#ffcc00",           # Yellow
        "accent_hover": "#ffdd44",
        "accent_blue": "#3ba4d8",
    },
    "annul": {
        "name": "Orb of Annulment",
        "accent": "#ffffff",           # White
        "accent_hover": "#e0e0ff",
        "accent_blue": "#3ba4d8",
    },
    "vaal": {
        "name": "Vaal Orb",
        "accent": "#d04040",           # Red
        "accent_hover": "#e06060",
        "accent_blue": "#50c8ff",
    },
    "ancient": {
        "name": "Ancient Orb",
        "accent": "#ff8855",           # Orange
        "accent_hover": "#ffaa77",
        "accent_blue": "#3ba4d8",
    },
    "awakener": {
        "name": "Awakener's Orb",
        "accent": "#9060d0",           # Purple
        "accent_hover": "#b080f0",
        "accent_blue": "#50c8ff",
    },
    "hinekora": {
        "name": "Hinekora's Lock",
        "accent": "#40d080",           # Green
        "accent_hover": "#60f0a0",
        "accent_blue": "#3ba4d8",
    },
}
