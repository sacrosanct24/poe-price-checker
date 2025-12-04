"""
PoE2 Game Data Module.

Comprehensive data for Path of Exile 2 including:
- Rune definitions and tiers
- Charm modifiers
- Base item types
- Pseudo stat aggregation
- Goodness score calculations

Data sources:
- Path of Building PoE2 (authoritative game data)
- Exiled Exchange 2 (trade integration patterns)
- Awakened PoE Trade (pseudo stat logic)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Mapping, Optional, Tuple, Union


# =============================================================================
# ENUMS
# =============================================================================

class RuneTier(Enum):
    """Rune power tiers."""
    LESSER = 0
    NORMAL = 15
    GREATER = 30
    HERITAGE = 50  # Named legendary runes
    SOUL_CORE = 50  # Soul cores


class ModifierType(Enum):
    """Types of item modifiers."""
    PSEUDO = "pseudo"
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    CRAFTED = "crafted"
    ENCHANT = "enchant"
    RUNE = "rune"
    FRACTURED = "fractured"
    CORRUPTED = "corrupted"
    SANCTUM = "sanctum"


class DamageType(Enum):
    """Damage types in PoE2."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Rune:
    """Represents a PoE2 rune."""
    name: str
    tier: RuneTier
    stat: str
    value: str
    slots: List[str]  # Which equipment slots it can be socketed in
    stat_id: Optional[str] = None


@dataclass
class CharmMod:
    """Represents a charm modifier."""
    affix: str
    stat: str
    tier: int
    min_value: int
    max_value: int
    level_req: int
    group: str
    trade_hash: Optional[str] = None


@dataclass
class BaseItem:
    """Represents a PoE2 base item type."""
    name: str
    item_type: str
    sub_type: str
    level_req: int
    str_req: int = 0
    dex_req: int = 0
    int_req: int = 0
    armour: int = 0
    evasion: int = 0
    energy_shield: int = 0
    movement_penalty: float = 0.0
    socket_limit: int = 4
    implicit: Optional[str] = None


# =============================================================================
# POE2 RUNE DATA
# =============================================================================

POE2_RUNES: Dict[str, Rune] = {
    # === Elemental Damage Runes ===
    "Lesser Desert Rune": Rune(
        name="Lesser Desert Rune",
        tier=RuneTier.LESSER,
        stat="Adds Fire Damage",
        value="5 to 9",
        slots=["weapon", "gloves", "ring"]
    ),
    "Desert Rune": Rune(
        name="Desert Rune",
        tier=RuneTier.NORMAL,
        stat="Adds Fire Damage",
        value="12 to 20",
        slots=["weapon", "gloves", "ring"]
    ),
    "Greater Desert Rune": Rune(
        name="Greater Desert Rune",
        tier=RuneTier.GREATER,
        stat="Adds Fire Damage",
        value="23 to 34",
        slots=["weapon", "gloves", "ring"]
    ),
    "Lesser Glacial Rune": Rune(
        name="Lesser Glacial Rune",
        tier=RuneTier.LESSER,
        stat="Adds Cold Damage",
        value="5 to 9",
        slots=["weapon", "gloves", "ring"]
    ),
    "Glacial Rune": Rune(
        name="Glacial Rune",
        tier=RuneTier.NORMAL,
        stat="Adds Cold Damage",
        value="12 to 20",
        slots=["weapon", "gloves", "ring"]
    ),
    "Greater Glacial Rune": Rune(
        name="Greater Glacial Rune",
        tier=RuneTier.GREATER,
        stat="Adds Cold Damage",
        value="23 to 34",
        slots=["weapon", "gloves", "ring"]
    ),
    "Lesser Storm Rune": Rune(
        name="Lesser Storm Rune",
        tier=RuneTier.LESSER,
        stat="Adds Lightning Damage",
        value="1 to 18",
        slots=["weapon", "gloves", "ring"]
    ),
    "Storm Rune": Rune(
        name="Storm Rune",
        tier=RuneTier.NORMAL,
        stat="Adds Lightning Damage",
        value="2 to 38",
        slots=["weapon", "gloves", "ring"]
    ),
    "Greater Storm Rune": Rune(
        name="Greater Storm Rune",
        tier=RuneTier.GREATER,
        stat="Adds Lightning Damage",
        value="4 to 57",
        slots=["weapon", "gloves", "ring"]
    ),

    # === Defense Runes ===
    "Lesser Iron Rune": Rune(
        name="Lesser Iron Rune",
        tier=RuneTier.LESSER,
        stat="increased Armour",
        value="15%",
        slots=["helmet", "body_armour", "gloves", "boots", "shield"]
    ),
    "Iron Rune": Rune(
        name="Iron Rune",
        tier=RuneTier.NORMAL,
        stat="increased Armour",
        value="25%",
        slots=["helmet", "body_armour", "gloves", "boots", "shield"]
    ),
    "Greater Iron Rune": Rune(
        name="Greater Iron Rune",
        tier=RuneTier.GREATER,
        stat="increased Armour",
        value="35%",
        slots=["helmet", "body_armour", "gloves", "boots", "shield"]
    ),

    # === Life/Mana Runes ===
    "Lesser Body Rune": Rune(
        name="Lesser Body Rune",
        tier=RuneTier.LESSER,
        stat="to maximum Life",
        value="+20",
        slots=["helmet", "body_armour", "belt", "ring", "amulet"]
    ),
    "Body Rune": Rune(
        name="Body Rune",
        tier=RuneTier.NORMAL,
        stat="to maximum Life",
        value="+35",
        slots=["helmet", "body_armour", "belt", "ring", "amulet"]
    ),
    "Greater Body Rune": Rune(
        name="Greater Body Rune",
        tier=RuneTier.GREATER,
        stat="to maximum Life",
        value="+50",
        slots=["helmet", "body_armour", "belt", "ring", "amulet"]
    ),
    "Lesser Mind Rune": Rune(
        name="Lesser Mind Rune",
        tier=RuneTier.LESSER,
        stat="to maximum Mana",
        value="+15",
        slots=["helmet", "ring", "amulet"]
    ),
    "Mind Rune": Rune(
        name="Mind Rune",
        tier=RuneTier.NORMAL,
        stat="to maximum Mana",
        value="+25",
        slots=["helmet", "ring", "amulet"]
    ),
    "Greater Mind Rune": Rune(
        name="Greater Mind Rune",
        tier=RuneTier.GREATER,
        stat="to maximum Mana",
        value="+40",
        slots=["helmet", "ring", "amulet"]
    ),

    # === Movement Speed Runes ===
    "Lesser Stone Rune": Rune(
        name="Lesser Stone Rune",
        tier=RuneTier.LESSER,
        stat="increased Movement Speed",
        value="5%",
        slots=["boots"]
    ),
    "Stone Rune": Rune(
        name="Stone Rune",
        tier=RuneTier.NORMAL,
        stat="increased Movement Speed",
        value="10%",
        slots=["boots"]
    ),
    "Greater Stone Rune": Rune(
        name="Greater Stone Rune",
        tier=RuneTier.GREATER,
        stat="increased Movement Speed",
        value="15%",
        slots=["boots"]
    ),

    # === Heritage Runes (Named Legendary) ===
    "Thane Myrk's Rune of Summer": Rune(
        name="Thane Myrk's Rune of Summer",
        tier=RuneTier.HERITAGE,
        stat="Adds Fire Damage",
        value="23 to 34",
        slots=["weapon"]
    ),
    "Countess Seske's Rune of Archery": Rune(
        name="Countess Seske's Rune of Archery",
        tier=RuneTier.HERITAGE,
        stat="Bow Attacks fire an additional Arrow",
        value="1",
        slots=["bow", "quiver"]
    ),

    # === Talisman Runes ===
    "Serpent Talisman": Rune(
        name="Serpent Talisman",
        tier=RuneTier.HERITAGE,
        stat="Allies in your Presence deal increased Damage",
        value="30%",
        slots=["amulet"]
    ),
    "Wolf Talisman": Rune(
        name="Wolf Talisman",
        tier=RuneTier.HERITAGE,
        stat="Allies in your Presence have increased Attack Speed",
        value="15%",
        slots=["amulet"]
    ),
    "Bear Talisman": Rune(
        name="Bear Talisman",
        tier=RuneTier.HERITAGE,
        stat="Allies in your Presence have increased maximum Life",
        value="10%",
        slots=["amulet"]
    ),

    # === Soul Cores ===
    "Soul Core of Hayoxi": Rune(
        name="Soul Core of Hayoxi",
        tier=RuneTier.SOUL_CORE,
        stat="of Armour also applies to Cold Damage",
        value="30%",
        slots=["helmet", "body_armour", "gloves", "boots"]
    ),
    "Soul Core of Zalatl": Rune(
        name="Soul Core of Zalatl",
        tier=RuneTier.SOUL_CORE,
        stat="of Evasion Rating also applies to Fire Damage",
        value="30%",
        slots=["helmet", "body_armour", "gloves", "boots"]
    ),
    "Soul Core of Atmohua": Rune(
        name="Soul Core of Atmohua",
        tier=RuneTier.SOUL_CORE,
        stat="of Energy Shield also applies to Lightning Damage",
        value="30%",
        slots=["helmet", "body_armour", "gloves", "boots"]
    ),
}


# =============================================================================
# POE2 CHARM MODIFIERS
# =============================================================================

POE2_CHARM_MODS: List[CharmMod] = [
    # Duration modifiers
    CharmMod(
        affix="Investigator's",
        stat="increased Charm Effect Duration",
        tier=1, min_value=16, max_value=20,
        level_req=1, group="CharmIncreasedDuration"
    ),
    CharmMod(
        affix="Detective's",
        stat="increased Charm Effect Duration",
        tier=2, min_value=21, max_value=25,
        level_req=20, group="CharmIncreasedDuration"
    ),
    CharmMod(
        affix="Inspector's",
        stat="increased Charm Effect Duration",
        tier=3, min_value=26, max_value=30,
        level_req=40, group="CharmIncreasedDuration"
    ),

    # Life recovery
    CharmMod(
        affix="Herbal",
        stat="Life recovered on Charm use",
        tier=1, min_value=30, max_value=50,
        level_req=1, group="CharmLifeRecovery"
    ),
    CharmMod(
        affix="Medicinal",
        stat="Life recovered on Charm use",
        tier=2, min_value=60, max_value=80,
        level_req=20, group="CharmLifeRecovery"
    ),
    CharmMod(
        affix="Restorative",
        stat="Life recovered on Charm use",
        tier=3, min_value=90, max_value=120,
        level_req=40, group="CharmLifeRecovery"
    ),

    # Mana recovery
    CharmMod(
        affix="Azure",
        stat="Mana recovered on Charm use",
        tier=1, min_value=15, max_value=25,
        level_req=1, group="CharmManaRecovery"
    ),
    CharmMod(
        affix="Cobalt",
        stat="Mana recovered on Charm use",
        tier=2, min_value=30, max_value=40,
        level_req=20, group="CharmManaRecovery"
    ),
    CharmMod(
        affix="Sapphire",
        stat="Mana recovered on Charm use",
        tier=3, min_value=45, max_value=60,
        level_req=40, group="CharmManaRecovery"
    ),
]


# =============================================================================
# POE2 BASE ITEM TYPES
# =============================================================================

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
    "trap", "jewel", "soulcore", "traptool",
}

POE2_NEW_ITEM_TYPES = {
    "focus",      # Off-hand caster item
    "crossbow",   # New ranged weapon
    "flail",      # New melee weapon
    "spear",      # New melee weapon
    "warstaff",   # Combat staff
    "charm",      # Consumable buff item
    "soulcore",   # Special socket item
    "traptool",   # Trap equipment
}


# =============================================================================
# PSEUDO STAT AGGREGATION RULES
# =============================================================================
# Based on Awakened PoE Trade patterns

@dataclass
class PseudoRule:
    """Rule for aggregating stats into pseudo totals."""
    pseudo_stat: str
    sources: List[Tuple[str, float]]  # (stat_pattern, multiplier)
    requires: Optional[str] = None  # Required base stat


PSEUDO_STAT_RULES: List[PseudoRule] = [
    # Total Elemental Resistance
    PseudoRule(
        pseudo_stat="pseudo_total_elemental_resistance",
        sources=[
            ("to Fire Resistance", 1.0),
            ("to Cold Resistance", 1.0),
            ("to Lightning Resistance", 1.0),
            ("to all Elemental Resistances", 3.0),  # Counts 3x
        ]
    ),

    # Total Resistance (includes chaos)
    PseudoRule(
        pseudo_stat="pseudo_total_resistance",
        sources=[
            ("to Fire Resistance", 1.0),
            ("to Cold Resistance", 1.0),
            ("to Lightning Resistance", 1.0),
            ("to Chaos Resistance", 1.0),
            ("to all Elemental Resistances", 3.0),
        ]
    ),

    # Total Life
    PseudoRule(
        pseudo_stat="pseudo_total_life",
        sources=[
            ("to maximum Life", 1.0),
            ("to Strength", 0.5),  # 2 Str = 1 Life
        ],
        requires="to maximum Life"
    ),

    # Total Mana
    PseudoRule(
        pseudo_stat="pseudo_total_mana",
        sources=[
            ("to maximum Mana", 1.0),
            ("to Intelligence", 0.5),  # 2 Int = 1 Mana
        ],
        requires="to maximum Mana"
    ),

    # Total Energy Shield
    PseudoRule(
        pseudo_stat="pseudo_total_energy_shield",
        sources=[
            ("to maximum Energy Shield", 1.0),
            ("increased maximum Energy Shield", 1.0),
        ]
    ),

    # Total Attributes
    PseudoRule(
        pseudo_stat="pseudo_total_all_attributes",
        sources=[
            ("to Strength", 1.0),
            ("to Dexterity", 1.0),
            ("to Intelligence", 1.0),
            ("to all Attributes", 3.0),
        ]
    ),

    # Individual Attributes
    PseudoRule(
        pseudo_stat="pseudo_total_strength",
        sources=[
            ("to Strength", 1.0),
            ("to all Attributes", 1.0),
        ]
    ),
    PseudoRule(
        pseudo_stat="pseudo_total_dexterity",
        sources=[
            ("to Dexterity", 1.0),
            ("to all Attributes", 1.0),
        ]
    ),
    PseudoRule(
        pseudo_stat="pseudo_total_intelligence",
        sources=[
            ("to Intelligence", 1.0),
            ("to all Attributes", 1.0),
        ]
    ),

    # Attack/Cast Speed
    PseudoRule(
        pseudo_stat="pseudo_total_attack_speed",
        sources=[
            ("increased Attack Speed", 1.0),
        ]
    ),
    PseudoRule(
        pseudo_stat="pseudo_total_cast_speed",
        sources=[
            ("increased Cast Speed", 1.0),
        ]
    ),
]


# =============================================================================
# GOODNESS SCORE CALCULATION
# =============================================================================

def calculate_goodness_score(
    actual_value: float,
    min_value: float,
    max_value: float
) -> float:
    """
    Calculate the "goodness" of a mod roll.

    Based on Awakened PoE Trade formula:
    goodness = (actual - min) / (max - min)

    Args:
        actual_value: The rolled value on the item
        min_value: Minimum possible value for this mod tier
        max_value: Maximum possible value for this mod tier

    Returns:
        Float between 0.0 (worst roll) and 1.0 (perfect roll)
        Returns 1.0 if min == max (fixed value)
    """
    if max_value == min_value:
        return 1.0  # Fixed value, always "perfect"

    if actual_value < min_value:
        return 0.0
    if actual_value > max_value:
        return 1.0

    return (actual_value - min_value) / (max_value - min_value)


def get_roll_quality_label(goodness: float) -> str:
    """
    Get a human-readable label for a roll's quality.

    Args:
        goodness: Goodness score from 0.0 to 1.0

    Returns:
        Quality label string
    """
    if goodness >= 0.95:
        return "Perfect"
    elif goodness >= 0.80:
        return "Excellent"
    elif goodness >= 0.60:
        return "Good"
    elif goodness >= 0.40:
        return "Average"
    elif goodness >= 0.20:
        return "Below Average"
    else:
        return "Low"


def calculate_filter_range(
    actual_value: float,
    min_value: float,
    max_value: float,
    search_range_percent: float = 0.2
) -> Tuple[float, float]:
    """
    Calculate trade filter min/max values based on roll.

    Uses the Awakened PoE Trade pattern of centering around
    the actual value with a configurable range.

    Args:
        actual_value: The rolled value
        min_value: Min possible for tier
        max_value: Max possible for tier
        search_range_percent: How much variance to allow (default 20%)

    Returns:
        (filter_min, filter_max) tuple
    """
    value_range = max_value - min_value
    offset = value_range * search_range_percent

    filter_min = max(min_value, actual_value - offset)
    filter_max = min(max_value, actual_value + offset)

    return (filter_min, filter_max)


# =============================================================================
# STAT DIFFERENTIAL CALCULATION
# =============================================================================

def calculate_stat_differential(
    base_stat: float,
    modified_stat: float,
    stat_weight: float = 1.0
) -> float:
    """
    Calculate the weighted stat differential for trade query priority.

    Based on PoB-PoE2 TradeQueryGenerator pattern:
    Tests each mod by calculating stat difference it produces.

    Args:
        base_stat: Baseline stat value (without the mod)
        modified_stat: Stat value with the mod applied
        stat_weight: User-configured weight multiplier

    Returns:
        Weighted differential value
    """
    differential = modified_stat - base_stat
    return differential * stat_weight


def prioritize_mods_by_differential(
    mod_differentials: Dict[str, float],
    max_filters: int = 35
) -> List[str]:
    """
    Sort and limit mods by their stat differential.

    Based on PoB pattern: sort by mean stat differential,
    apply maximum filter limit (35 mods).

    Args:
        mod_differentials: Dict of mod_id -> differential value
        max_filters: Maximum number of filters (default 35)

    Returns:
        List of mod IDs sorted by importance, limited to max_filters
    """
    sorted_mods = sorted(
        mod_differentials.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )

    return [mod_id for mod_id, _ in sorted_mods[:max_filters]]


# =============================================================================
# PSEUDO STAT CALCULATION
# =============================================================================

def calculate_pseudo_stat(
    rule: PseudoRule,
    item_mods: Mapping[str, Union[int, float]]
) -> Optional[float]:
    """
    Calculate a pseudo stat total from item mods.

    Args:
        rule: The pseudo stat aggregation rule
        item_mods: Dict of stat_pattern -> value from item

    Returns:
        Total pseudo stat value, or None if requirements not met
    """
    # Check requirements
    if rule.requires:
        if not any(rule.requires in mod for mod in item_mods.keys()):
            return None

    total = 0.0
    for stat_pattern, multiplier in rule.sources:
        for mod_text, value in item_mods.items():
            if stat_pattern in mod_text:
                total += value * multiplier

    return total if total > 0 else None


def calculate_all_pseudo_stats(
    item_mods: Mapping[str, Union[int, float]]
) -> Dict[str, float]:
    """
    Calculate all pseudo stats for an item.

    Args:
        item_mods: Dict of stat_pattern -> value from item

    Returns:
        Dict of pseudo_stat_id -> calculated total
    """
    results = {}

    for rule in PSEUDO_STAT_RULES:
        value = calculate_pseudo_stat(rule, item_mods)
        if value is not None:
            results[rule.pseudo_stat] = value

    return results


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_rune_by_name(name: str) -> Optional[Rune]:
    """Get a rune by its name."""
    return POE2_RUNES.get(name)


def get_runes_for_slot(slot: str) -> List[Rune]:
    """Get all runes that can be socketed in a specific slot."""
    return [
        rune for rune in POE2_RUNES.values()
        if slot in rune.slots
    ]


def get_runes_by_tier(tier: RuneTier) -> List[Rune]:
    """Get all runes of a specific tier."""
    return [
        rune for rune in POE2_RUNES.values()
        if rune.tier == tier
    ]


def get_charm_mods_by_group(group: str) -> List[CharmMod]:
    """Get all charm mods in a specific group."""
    return [
        mod for mod in POE2_CHARM_MODS
        if mod.group == group
    ]


def is_poe2_item_type(item_type: str) -> bool:
    """Check if an item type exists in PoE2."""
    return item_type.lower() in POE2_ITEM_TYPES


def is_poe2_exclusive_type(item_type: str) -> bool:
    """Check if an item type is new to PoE2 (doesn't exist in PoE1)."""
    return item_type.lower() in POE2_NEW_ITEM_TYPES


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== PoE2 Data Module Test ===\n")

    # Test goodness score
    print("Goodness Score Tests:")
    print(f"  Roll 95 in range 80-100: {calculate_goodness_score(95, 80, 100):.2f}")
    print(f"  Roll 80 in range 80-100: {calculate_goodness_score(80, 80, 100):.2f}")
    print(f"  Roll 100 in range 80-100: {calculate_goodness_score(100, 80, 100):.2f}")
    print(f"  Quality label for 0.85: {get_roll_quality_label(0.85)}")

    # Test filter range
    print("\nFilter Range Test:")
    fmin, fmax = calculate_filter_range(95, 80, 100, 0.2)
    print(f"  Roll 95, range 80-100, 20% variance: {fmin:.1f} - {fmax:.1f}")

    # Test pseudo stats
    print("\nPseudo Stat Test:")
    test_mods = {
        "+45% to Fire Resistance": 45,
        "+40% to Cold Resistance": 40,
        "+35% to Lightning Resistance": 35,
        "+80 to maximum Life": 80,
        "+25 to Strength": 25,
    }
    pseudo = calculate_all_pseudo_stats(test_mods)
    for stat, value in pseudo.items():
        print(f"  {stat}: {value}")

    # Test runes
    print("\nRune Data Test:")
    print(f"  Total runes: {len(POE2_RUNES)}")
    boot_runes = get_runes_for_slot("boots")
    print(f"  Runes for boots: {len(boot_runes)}")

    # Test charm mods
    print("\nCharm Mods Test:")
    print(f"  Total charm mods: {len(POE2_CHARM_MODS)}")
    duration_mods = get_charm_mods_by_group("CharmIncreasedDuration")
    print(f"  Duration mods: {len(duration_mods)}")

    print("\n=== All tests passed! ===")
