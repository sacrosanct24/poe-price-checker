"""
PoE2 Trade API stat IDs and affix tier data.

Based on data extracted from Exiled Exchange 2 project.
PoE2 uses /api/trade2/ endpoints and has different stat IDs.

Key differences from PoE1:
- Trade API endpoint is /api/trade2/search/<league>
- Different stat ID format (e.g., "explicit.stat_XXXXXXXXX")
- Different tier structure (up to 13 tiers for some mods)
- New item types: Focus, Crossbow, Flail, Warstaff, Spear, Trap
- Rune sockets instead of gem sockets for equipment
"""

from typing import Dict, List, Optional, Tuple

# =============================================================================
# PoE2 STAT ID MAPPINGS
# =============================================================================
# Format: (stat_id, is_pseudo)
# These are from the PoE2 trade API and Exiled Exchange 2 data

POE2_AFFIX_TO_STAT_ID: Dict[str, Tuple[str, bool]] = {
    # === Defensive Stats ===
    "life": ("pseudo.pseudo_total_life", True),
    "energy_shield": ("pseudo.pseudo_total_energy_shield", True),
    "armour": ("explicit.stat_809229260", False),  # +# to Armour
    "evasion": ("explicit.stat_2106365538", False),  # +# to Evasion Rating
    "stun_threshold": ("explicit.stat_3616637267", False),  # +# to Stun Threshold

    # === Resistances ===
    "resistances": ("pseudo.pseudo_total_elemental_resistance", True),
    "fire_resistance": ("pseudo.pseudo_total_fire_resistance", True),
    "cold_resistance": ("pseudo.pseudo_total_cold_resistance", True),
    "lightning_resistance": ("pseudo.pseudo_total_lightning_resistance", True),
    "chaos_resistance": ("pseudo.pseudo_total_chaos_resistance", True),
    "all_elemental_resistances": ("explicit.stat_2901986750", False),

    # === Attributes ===
    "strength": ("pseudo.pseudo_total_strength", True),
    "dexterity": ("pseudo.pseudo_total_dexterity", True),
    "intelligence": ("pseudo.pseudo_total_intelligence", True),
    "all_attributes": ("pseudo.pseudo_total_all_attributes", True),

    # === Movement ===
    "movement_speed": ("explicit.stat_2250533757", False),

    # === Offensive Stats ===
    "attack_speed": ("pseudo.pseudo_total_attack_speed", True),
    "cast_speed": ("pseudo.pseudo_total_cast_speed", True),
    "critical_strike_chance": ("pseudo.pseudo_global_critical_strike_chance", True),
    "critical_strike_multiplier": ("pseudo.pseudo_global_critical_strike_multiplier", True),

    # === Physical Damage ===
    "added_physical_damage": ("explicit.stat_960081730", False),  # Adds # to # Physical Damage
    "added_physical_to_attacks": ("explicit.stat_3032590688", False),

    # === Elemental Damage ===
    "added_fire_damage": ("explicit.stat_1573130764", False),
    "added_cold_damage": ("explicit.stat_2387423236", False),
    "added_lightning_damage": ("explicit.stat_3336890334", False),

    # === Mana ===
    "mana": ("pseudo.pseudo_total_mana", True),
    "mana_regeneration": ("pseudo.pseudo_increased_mana_regen", True),

    # === Spirit (PoE2-specific) ===
    "spirit": ("explicit.stat_3981240776", False),
}

# =============================================================================
# PoE2 AFFIX TIER DATA
# =============================================================================
# Format: {mod_display: {item_type: max_tier}}
# From Exiled Exchange 2 tiers.json

POE2_AFFIX_TIERS: Dict[str, Dict[str, int]] = {
    # === Attributes ===
    "+# to Strength": {
        "spear": 8, "boots": 8, "mace": 8, "focus": 8, "shield": 8,
        "amulet": 8, "sword": 8, "ring": 8, "helmet": 8, "belt": 9,
        "flail": 8, "crossbow": 8, "gloves": 8, "body_armour": 8, "sceptre": 8, "axe": 8
    },
    "+# to Dexterity": {
        "spear": 8, "boots": 8, "quiver": 8, "focus": 8, "bow": 8,
        "trap": 8, "warstaff": 8, "shield": 8, "dagger": 8, "amulet": 8,
        "sword": 8, "claw": 8, "ring": 8, "helmet": 8, "gloves": 9,
        "crossbow": 8, "body_armour": 8
    },
    "+# to Intelligence": {
        "amulet": 8, "ring": 8, "wand": 8, "helmet": 9, "staff": 8,
        "flail": 8, "boots": 8, "focus": 8, "trap": 8, "gloves": 8,
        "sceptre": 8, "body_armour": 8, "warstaff": 8, "shield": 8, "dagger": 8
    },
    "+# to all Attributes": {"amulet": 9, "ring": 4},

    # === Resistances ===
    "+#% to Fire Resistance": {
        "amulet": 8, "ring": 8, "helmet": 8, "belt": 8, "boots": 8,
        "focus": 8, "gloves": 8, "body_armour": 8, "shield": 8
    },
    "+#% to Cold Resistance": {
        "amulet": 8, "ring": 8, "helmet": 8, "belt": 8, "boots": 8,
        "focus": 8, "gloves": 8, "body_armour": 8, "shield": 8
    },
    "+#% to Lightning Resistance": {
        "amulet": 8, "ring": 8, "helmet": 8, "belt": 8, "boots": 8,
        "focus": 8, "gloves": 8, "body_armour": 8, "shield": 8
    },
    "+#% to all Elemental Resistances": {"amulet": 6, "ring": 5, "shield": 6},
    "+#% to Chaos Resistance": {
        "amulet": 6, "ring": 6, "helmet": 6, "belt": 6, "boots": 6,
        "focus": 6, "gloves": 6, "body_armour": 6, "shield": 6
    },

    # === Life/Mana/ES ===
    "+# to maximum Life": {
        "amulet": 9, "ring": 8, "helmet": 10, "belt": 10, "boots": 9,
        "gloves": 9, "body_armour": 13, "shield": 11
    },
    "#% increased maximum Life": {"amulet": 3},
    "+# to maximum Mana": {
        "amulet": 13, "ring": 12, "wand": 11, "helmet": 10, "belt": 9,
        "boots": 9, "focus": 11, "trap": 11, "gloves": 9, "sceptre": 11, "staff": 11
    },
    "#% increased maximum Mana": {"amulet": 3},
    "+# to maximum Energy Shield": {
        "amulet": 10, "focus": 10, "gloves": 7, "body_armour": 11,
        "helmet": 8, "shield": 10, "boots": 7
    },

    # === Armour/Evasion/ES ===
    "+# to Armour": {
        "belt": 10, "focus": 11, "gloves": 7, "body_armour": 11,
        "helmet": 8, "shield": 10, "boots": 7
    },
    "+# to Evasion Rating": {
        "ring": 9, "focus": 11, "gloves": 7, "body_armour": 11,
        "helmet": 8, "shield": 10, "boots": 7
    },
    "#% increased Armour": {
        "amulet": 7, "jewel": 1, "helmet": 8, "boots": 8,
        "focus": 8, "gloves": 8, "body_armour": 8, "shield": 8
    },
    "#% increased Evasion Rating": {
        "amulet": 7, "jewel": 1, "helmet": 8, "boots": 8,
        "focus": 8, "gloves": 8, "body_armour": 8, "shield": 8
    },
    "#% increased maximum Energy Shield": {"amulet": 7, "jewel": 1},
    "#% increased Energy Shield": {
        "helmet": 8, "boots": 8, "focus": 8, "gloves": 8,
        "body_armour": 8, "shield": 8
    },

    # === Movement Speed ===
    "#% increased Movement Speed": {"boots": 6, "jewel": 1},

    # === Stun Threshold ===
    "+# to Stun Threshold": {"body_armour": 10, "belt": 10, "shield": 10, "boots": 11},

    # === Damage ===
    "Adds # to # Physical Damage to Attacks": {"quiver": 9, "gloves": 9, "ring": 9},
    "Adds # to # Fire damage to Attacks": {"quiver": 9, "gloves": 9, "ring": 9},
    "Adds # to # Cold damage to Attacks": {"quiver": 9, "gloves": 9, "ring": 9},
    "Adds # to # Lightning damage to Attacks": {"quiver": 9, "gloves": 9, "ring": 9},
    "Adds # to # Physical Damage": {
        "bow": 9, "one_hand_weapon": 9, "two_hand_weapon": 9
    },
    "Adds # to # Fire Damage": {
        "sword": 10, "spear": 10, "claw": 10, "flail": 10, "mace": 10,
        "bow": 10, "dagger": 10, "axe": 10, "crossbow": 10, "warstaff": 10
    },
    "Adds # to # Cold Damage": {
        "sword": 10, "spear": 10, "claw": 10, "flail": 10, "mace": 10,
        "bow": 10, "dagger": 10, "axe": 10, "crossbow": 10, "warstaff": 10
    },
    "Adds # to # Lightning Damage": {
        "sword": 10, "spear": 10, "claw": 10, "flail": 10, "mace": 10,
        "bow": 10, "dagger": 10, "axe": 10, "crossbow": 10, "warstaff": 10
    },
}

# =============================================================================
# PoE2 ITEM TYPES
# =============================================================================
# PoE2 has new item types not in PoE1

POE2_ITEM_TYPES = {
    # Armour
    "helmet", "body_armour", "gloves", "boots", "shield", "focus",

    # Accessories
    "amulet", "ring", "belt", "quiver", "charm",

    # One-handed weapons
    "sword", "axe", "mace", "dagger", "claw", "sceptre", "wand", "flail",

    # Two-handed weapons
    "bow", "staff", "warstaff", "crossbow", "spear",

    # Other
    "trap", "jewel",
}

# =============================================================================
# PoE2-SPECIFIC SLOT MAPPINGS
# =============================================================================
# Maps our slot names to PoE2 item types

POE2_SLOT_TO_TYPE: Dict[str, str] = {
    "Helmet": "helmet",
    "Body Armour": "body_armour",
    "Gloves": "gloves",
    "Boots": "boots",
    "Shield": "shield",
    "Focus": "focus",
    "Belt": "belt",
    "Amulet": "amulet",
    "Ring 1": "ring",
    "Ring 2": "ring",
    "Weapon 1": "one_hand_weapon",
    "Weapon 2": "one_hand_weapon",
    "Quiver": "quiver",
}

# =============================================================================
# MINIMUM VALUE THRESHOLDS FOR PoE2
# =============================================================================
# These are adjusted for PoE2's tier structure (more tiers = different values)

POE2_AFFIX_MIN_VALUES: Dict[str, int] = {
    # Defensive (adjusted for PoE2's higher tier counts)
    "life": 80,  # T3+ life (PoE2 has 13 tiers on body armour)
    "energy_shield": 50,
    "armour": 100,
    "evasion": 100,
    "stun_threshold": 50,

    # Resistances
    "resistances": 30,
    "fire_resistance": 30,
    "cold_resistance": 30,
    "lightning_resistance": 30,
    "chaos_resistance": 15,
    "all_elemental_resistances": 10,

    # Attributes
    "strength": 35,
    "dexterity": 35,
    "intelligence": 35,
    "all_attributes": 10,

    # Movement
    "movement_speed": 20,

    # Offensive
    "attack_speed": 8,
    "cast_speed": 8,
    "critical_strike_chance": 25,
    "critical_strike_multiplier": 20,

    # Damage
    "added_physical_damage": 8,
    "added_fire_damage": 10,
    "added_cold_damage": 10,
    "added_lightning_damage": 10,

    # Mana/Spirit
    "mana": 40,
    "mana_regeneration": 20,
    "spirit": 20,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_poe2_stat_id(affix_type: str) -> Optional[Tuple[str, bool]]:
    """
    Get PoE2 trade API stat ID for an affix type.

    Args:
        affix_type: Affix type (e.g., "life", "resistances")

    Returns:
        (stat_id, is_pseudo) tuple, or None if not mapped
    """
    return POE2_AFFIX_TO_STAT_ID.get(affix_type)


def get_poe2_min_value(affix_type: str, actual_value: Optional[float] = None) -> Optional[int]:
    """
    Get minimum value threshold for PoE2 trade filtering.

    Args:
        affix_type: Affix type
        actual_value: Actual rolled value on the item

    Returns:
        Minimum value for filtering
    """
    if actual_value is not None and actual_value > 0:
        return int(actual_value * 0.8)
    return POE2_AFFIX_MIN_VALUES.get(affix_type)


def get_max_tier_for_slot(mod_display: str, slot: str) -> Optional[int]:
    """
    Get the maximum tier count for a mod on a specific slot.

    Args:
        mod_display: The mod display text (e.g., "+# to maximum Life")
        slot: The equipment slot (e.g., "body_armour")

    Returns:
        Maximum tier number, or None if not available
    """
    tier_data = POE2_AFFIX_TIERS.get(mod_display, {})
    return tier_data.get(slot)


def build_poe2_stat_filters(
    matched_affixes: list,
    max_filters: int = 4
) -> List[dict]:
    """
    Build PoE2 trade API stat filters from matched affixes.

    Args:
        matched_affixes: List of AffixMatch objects
        max_filters: Maximum number of filters

    Returns:
        List of filter dicts for trade API stats array
    """
    filters = []

    sorted_affixes = sorted(
        matched_affixes,
        key=lambda m: (
            0 if getattr(m, 'tier', 'tier3') == 'tier1' else
            1 if getattr(m, 'tier', 'tier3') == 'tier2' else 2,
            -getattr(m, 'weight', 0)
        )
    )

    for match in sorted_affixes[:max_filters]:
        affix_type = getattr(match, 'affix_type', None)
        if not affix_type:
            continue

        stat_mapping = get_poe2_stat_id(affix_type)
        if not stat_mapping:
            continue

        stat_id, _ = stat_mapping
        actual_value = getattr(match, 'value', None)
        min_value = get_poe2_min_value(affix_type, actual_value)

        if min_value is None:
            continue

        filters.append({
            "id": stat_id,
            "value": {"min": min_value}
        })

    return filters


# =============================================================================
# PSEUDO STAT AGGREGATIONS
# =============================================================================
# What underlying stats make up each pseudo stat

POE2_PSEUDO_COMPONENTS: Dict[str, List[str]] = {
    "pseudo_total_elemental_resistance": [
        "stat_2901986750",  # fire res
        "stat_3372524247",  # cold res
        "stat_4220027924",  # lightning res
        "stat_1671376347",  # all ele res (counts 3x)
    ],
    "pseudo_total_resistance": [
        "stat_2901986750",  # fire res
        "stat_3372524247",  # cold res
        "stat_4220027924",  # lightning res
        "stat_1671376347",  # all ele res
        "stat_2923486259",  # chaos res
    ],
    "pseudo_total_all_attributes": [
        "stat_4080418644",  # strength
        "stat_3261801346",  # dexterity
        "stat_328541901",   # intelligence
    ],
    "pseudo_total_life": ["stat_3299347043"],
    "pseudo_total_mana": ["stat_1050105434"],
    "pseudo_total_energy_shield": [
        "stat_4052037485",
        "stat_3489782002",
    ],
}
