"""
gui_qt.sample_items - Sample item data for the Dev menu.

Contains example item texts for testing price checking functionality.
"""

from typing import Dict, List

SAMPLE_ITEMS: Dict[str, List[str]] = {
    "map": [
        """Rarity: Normal
Cemetery Map
--------
Map Tier: 5
--------
Travel to this Map by using it in a personal Map Device.
""",
    ],
    "currency": [
        """Rarity: Currency
Chaos Orb
--------
Stack Size: 1/10
--------
Reforges a rare item with new random modifiers
""",
        """Rarity: Currency
Divine Orb
--------
Stack Size: 1/10
--------
Randomises the numeric values of the random modifiers on an item
""",
    ],
    "unique": [
        """Rarity: Unique
Tabula Rasa
Simple Robe
--------
Sockets: W-W-W-W-W-W
--------
Item Level: 68
--------
Item has no Level requirement
""",
        """Rarity: Unique
Headhunter
Leather Belt
--------
Requires Level 40
--------
+40 to maximum Life
+50 to Strength
+20% to Fire Resistance
When you Kill a Rare monster, you gain its Modifiers for 20 seconds
""",
    ],
    "rare": [
        """Rarity: Rare
Gale Gyre
Opal Ring
--------
Requires Level 80
--------
Item Level: 84
--------
+29% to Fire and Lightning Resistances
+16% to all Elemental Resistances
+55 to Maximum Life
+38% to Global Critical Strike Multiplier
""",
    ],
    "gem": [
        """Rarity: Gem
Vaal Grace
--------
Level: 21
Quality: +23%
--------
Casts an aura that grants evasion to you and nearby allies.
""",
    ],
    "divination": [
        """Rarity: Divination Card
The Doctor
--------
Stack Size: 1/8
--------
Headhunter
Leather Belt
""",
    ],
}
