"""Defaults for ML collection."""

from __future__ import annotations

ML_COLLECTION_CONFIG = {
    "enabled": True,
    "game_id": "poe1",
    "league": "Keepers",
    "frequency_minutes": 30,
    "base_types": {
        "boots": [
            "Titan Greaves",
            "Dragonscale Boots",
            "Sorcerer Boots",
            "Two-Toned Boots (Armour/Energy Shield)",
            "Two-Toned Boots (Evasion/Energy Shield)",
            "Fugitive Boots",
        ],
        "rings": [
            "Amethyst Ring",
            "Two-Stone Ring",
            "Vermillion Ring",
            "Prismatic Ring",
        ],
    },
    "max_listings_per_base": 100,
    "log_level": "INFO",
}
