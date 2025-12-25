"""Defaults for ML collection."""

from __future__ import annotations

ML_COLLECTION_CONFIG = {
    "enabled": True,
    "game_id": "poe1",
    "league": "Keepers",
    "frequency_minutes": 30,
    "base_types": {
        "boots": [
            "Two-Toned Boots",
            "Sorcerer Boots",
            "Titan Greaves",
            "Dragonscale Boots",
            "Slink Boots",
        ],
        "rings": [
            "Amethyst Ring",
            "Two-Stone Ring",
            "Vermillion Ring",
            "Prismatic Ring",
            "Diamond Ring",
        ],
    },
    "max_listings_per_base": 100,
    "log_level": "INFO",
}
