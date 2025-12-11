"""
Constants and mappings for price rankings.

Contains category definitions, API type mappings, equipment slots,
and category groupings.
"""
from typing import Dict, List, Tuple, Union

# Cache expiry in days
CACHE_EXPIRY_DAYS = 1

# Time constants
SECONDS_PER_DAY = 86400

# Category definitions with display names
CATEGORIES: Dict[str, str] = {
    # Currency
    "currency": "Currency",

    # Uniques by slot
    "unique_weapons": "Unique Weapons",
    "unique_armour": "Unique Armour",
    "unique_accessories": "Unique Accessories",
    "unique_flasks": "Unique Flasks",
    "unique_jewels": "Unique Jewels",

    # Other item types
    "fragments": "Fragments",
    "divination_cards": "Divination Cards",
    "essences": "Essences",
    "fossils": "Fossils",
    "scarabs": "Scarabs",
    "oils": "Oils",
    "incubators": "Incubators",
    "vials": "Vials",
}

# Map categories to poe.ninja API types
CATEGORY_TO_API_TYPE: Dict[str, str] = {
    "currency": "Currency",
    "unique_weapons": "UniqueWeapon",
    "unique_armour": "UniqueArmour",
    "unique_accessories": "UniqueAccessory",
    "unique_flasks": "UniqueFlask",
    "unique_jewels": "UniqueJewel",
    "fragments": "Fragment",
    "divination_cards": "DivinationCard",
    "essences": "Essence",
    "fossils": "Fossil",
    "scarabs": "Scarab",
    "oils": "Oil",
    "incubators": "Incubator",
    "vials": "Vial",
}

# Equipment slots for unique items
# Each slot maps to (API type, item type filter(s))
EQUIPMENT_SLOTS: Dict[str, Tuple[str, Union[str, List[str]]]] = {
    # Armour slots
    "helmet": ("UniqueArmour", "Helmet"),
    "body_armour": ("UniqueArmour", "Body Armour"),
    "gloves": ("UniqueArmour", "Gloves"),
    "boots": ("UniqueArmour", "Boots"),
    "shield": ("UniqueArmour", "Shield"),
    "quiver": ("UniqueArmour", "Quiver"),
    # Accessory slots
    "amulet": ("UniqueAccessory", "Amulet"),
    "ring": ("UniqueAccessory", "Ring"),
    "belt": ("UniqueAccessory", "Belt"),
    # Weapon slots (grouped)
    "one_handed_weapon": ("UniqueWeapon", ["One Handed Sword", "One Handed Axe", "One Handed Mace", "Claw", "Dagger", "Wand"]),
    "two_handed_weapon": ("UniqueWeapon", ["Two Handed Sword", "Two Handed Axe", "Two Handed Mace", "Staff", "Bow"]),
    # Individual weapon types
    "sword": ("UniqueWeapon", ["One Handed Sword", "Two Handed Sword"]),
    "axe": ("UniqueWeapon", ["One Handed Axe", "Two Handed Axe"]),
    "mace": ("UniqueWeapon", ["One Handed Mace", "Two Handed Mace"]),
    "bow": ("UniqueWeapon", "Bow"),
    "staff": ("UniqueWeapon", "Staff"),
    "wand": ("UniqueWeapon", "Wand"),
    "claw": ("UniqueWeapon", "Claw"),
    "dagger": ("UniqueWeapon", "Dagger"),
}

# Display names for equipment slots
SLOT_DISPLAY_NAMES: Dict[str, str] = {
    "helmet": "Helmets",
    "body_armour": "Body Armours",
    "gloves": "Gloves",
    "boots": "Boots",
    "shield": "Shields",
    "quiver": "Quivers",
    "amulet": "Amulets",
    "ring": "Rings",
    "belt": "Belts",
    "one_handed_weapon": "One-Handed Weapons",
    "two_handed_weapon": "Two-Handed Weapons",
    "sword": "Swords",
    "axe": "Axes",
    "mace": "Maces",
    "bow": "Bows",
    "staff": "Staves",
    "wand": "Wands",
    "claw": "Claws",
    "dagger": "Daggers",
}

# Category groupings for filtering
UNIQUE_CATEGORIES: List[str] = [
    "unique_weapons",
    "unique_armour",
    "unique_accessories",
    "unique_flasks",
    "unique_jewels",
]

# Aliases for clarity
EQUIPMENT_CATEGORIES: List[str] = UNIQUE_CATEGORIES

CONSUMABLE_CATEGORIES: List[str] = [
    "currency",
    "fragments",
    "essences",
    "fossils",
    "scarabs",
    "oils",
    "incubators",
    "vials",
]

CARD_CATEGORIES: List[str] = ["divination_cards"]

# Map categories to rarity for display coloring
CATEGORY_TO_RARITY: Dict[str, str] = {
    # Unique items
    "unique_weapons": "unique",
    "unique_armour": "unique",
    "unique_accessories": "unique",
    "unique_flasks": "unique",
    "unique_jewels": "unique",
    # Currency and consumables
    "currency": "currency",
    "fragments": "currency",
    "essences": "currency",
    "fossils": "currency",
    "scarabs": "currency",
    "oils": "currency",
    "incubators": "currency",
    "vials": "currency",
    # Cards
    "divination_cards": "divination",
}


def get_rarity_for_category(category: str) -> str:
    """
    Get the item rarity for a category.

    Args:
        category: Category key (e.g., "unique_weapons", "currency")

    Returns:
        Rarity string for display coloring
    """
    # Check if it's a slot category (all slots are unique items)
    if category.startswith("slot_"):
        return "unique"

    return CATEGORY_TO_RARITY.get(category, "normal")
