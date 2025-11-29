"""
Mod Tier Detector

Detects the tier of a mod by parsing its text and matching against known tier data.
Used by the Item Inspector to color-code mods by tier quality.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List

from core.affix_tier_calculator import AFFIX_TIER_DATA

logger = logging.getLogger(__name__)


@dataclass
class ModTierResult:
    """Result of mod tier detection."""
    mod_text: str
    stat_type: Optional[str] = None
    tier: Optional[int] = None
    value: Optional[int] = None
    is_crafted: bool = False
    is_implicit: bool = False

    @property
    def tier_label(self) -> str:
        """Get tier label like 'T1', 'T2', etc."""
        if self.tier is None:
            return ""
        return f"T{self.tier}"


# Mod patterns: (regex pattern, stat_type, value_group_index)
# value_group_index is which capture group contains the value (1-indexed)
MOD_PATTERNS: List[Tuple[str, str, int]] = [
    # Life
    (r"\+(\d+) to [Mm]aximum [Ll]ife", "life", 1),
    (r"\+(\d+) to [Ll]ife", "life", 1),

    # Energy Shield
    (r"\+(\d+) to [Mm]aximum [Ee]nergy [Ss]hield", "energy_shield", 1),

    # Resistances
    (r"\+(\d+)% to [Ff]ire [Rr]esistance", "fire_resistance", 1),
    (r"\+(\d+)% to [Cc]old [Rr]esistance", "cold_resistance", 1),
    (r"\+(\d+)% to [Ll]ightning [Rr]esistance", "lightning_resistance", 1),
    (r"\+(\d+)% to [Cc]haos [Rr]esistance", "chaos_resistance", 1),
    (r"\+(\d+)% to all [Ee]lemental [Rr]esistances", "all_ele_res", 1),

    # Attributes
    (r"\+(\d+) to [Ss]trength", "strength", 1),
    (r"\+(\d+) to [Dd]exterity", "dexterity", 1),
    (r"\+(\d+) to [Ii]ntelligence", "intelligence", 1),
    (r"\+(\d+) to all [Aa]ttributes", "all_attributes", 1),

    # Movement Speed (boots)
    (r"(\d+)% increased [Mm]ovement [Ss]peed", "movement_speed", 1),

    # Attack/Cast Speed
    (r"(\d+)% increased [Aa]ttack [Ss]peed", "attack_speed", 1),
    (r"(\d+)% increased [Cc]ast [Ss]peed", "cast_speed", 1),

    # Crit
    (r"(\d+)% increased [Gg]lobal [Cc]ritical [Ss]trike [Cc]hance", "critical_strike_chance", 1),
    (r"\+(\d+)% to [Gg]lobal [Cc]ritical [Ss]trike [Mm]ultiplier", "critical_strike_multiplier", 1),

    # Mana
    (r"\+(\d+) to [Mm]aximum [Mm]ana", "mana", 1),

    # Armour/Evasion (flat)
    (r"\+(\d+) to [Aa]rmour", "armour", 1),
    (r"\+(\d+) to [Ee]vasion [Rr]ating", "evasion", 1),

    # Spell Suppression
    (r"\+(\d+)% chance to [Ss]uppress [Ss]pell [Dd]amage", "spell_suppression", 1),

    # Life Regen
    (r"[Rr]egenerate (\d+\.?\d*) [Ll]ife per second", "life_regeneration", 1),

    # Mana Regen
    (r"(\d+)% increased [Mm]ana [Rr]egeneration [Rr]ate", "mana_regeneration", 1),

    # Damage
    (r"(\d+)% increased [Pp]hysical [Dd]amage", "physical_damage", 1),
    (r"(\d+)% increased [Ee]lemental [Dd]amage", "elemental_damage", 1),
    (r"(\d+)% increased [Ss]pell [Dd]amage", "spell_damage", 1),
]


def detect_mod_tier(mod_text: str, is_implicit: bool = False) -> ModTierResult:
    """
    Detect the tier of a mod from its text.

    Args:
        mod_text: The mod text to analyze
        is_implicit: Whether this is an implicit mod

    Returns:
        ModTierResult with detected tier information
    """
    result = ModTierResult(
        mod_text=mod_text,
        is_implicit=is_implicit,
        is_crafted="(crafted)" in mod_text.lower(),
    )

    # Try each pattern
    for pattern, stat_type, value_group in MOD_PATTERNS:
        match = re.search(pattern, mod_text)
        if match:
            try:
                # Extract the value
                value_str = match.group(value_group)
                # Handle decimal values (like life regen)
                value = int(float(value_str))
                result.value = value
                result.stat_type = stat_type

                # Look up the tier
                tier = _get_tier_for_value(stat_type, value)
                result.tier = tier
                break
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse mod value: {e}")
                continue

    return result


def _get_tier_for_value(stat_type: str, value: int) -> Optional[int]:
    """
    Get the tier for a stat value.

    Args:
        stat_type: Type of stat (e.g., "life", "fire_resistance")
        value: The numeric value of the mod

    Returns:
        Tier number (1 = best) or None if can't determine
    """
    tier_data = AFFIX_TIER_DATA.get(stat_type)
    if not tier_data:
        return None

    # Tier data format: [(tier, ilvl_req, min_val, max_val), ...]
    # Tiers are sorted best (1) to worst
    for tier, ilvl_req, min_val, max_val in tier_data:
        if min_val <= value <= max_val:
            return tier

    # Value is outside known ranges - estimate based on proximity
    # If value is higher than T1 max, it's T1 (or T0/elevated)
    if tier_data and value > tier_data[0][3]:
        return 1

    # If value is lower than worst tier min, return the worst tier
    if tier_data and value < tier_data[-1][2]:
        return len(tier_data)

    return None


def detect_mod_tiers(mods: List[str], are_implicit: bool = False) -> List[ModTierResult]:
    """
    Detect tiers for a list of mods.

    Args:
        mods: List of mod text strings
        are_implicit: Whether these are implicit mods

    Returns:
        List of ModTierResult objects
    """
    return [detect_mod_tier(mod, is_implicit=are_implicit) for mod in mods]


# Convenience function to get tier color suggestion
def get_mod_display_info(mod_text: str, is_implicit: bool = False) -> Tuple[str, Optional[int], str]:
    """
    Get display information for a mod.

    Args:
        mod_text: The mod text
        is_implicit: Whether this is an implicit mod

    Returns:
        Tuple of (tier_label, tier_number, stat_type)
    """
    result = detect_mod_tier(mod_text, is_implicit)
    return (result.tier_label, result.tier, result.stat_type or "")


# Testing
if __name__ == "__main__":
    test_mods = [
        "+92 to Maximum Life",
        "+45% to Fire Resistance",
        "+30% to Cold Resistance",
        "+55 to Strength",
        "35% increased Movement Speed",
        "+12% to Chaos Resistance",
        "14% increased Attack Speed",
        "+100 to Maximum Life",  # T1
        "+80 to Maximum Life",   # T3
        "Some mod with no tier data",
        "+50 to Dexterity (crafted)",
    ]

    print("=== Mod Tier Detection ===\n")
    for mod in test_mods:
        result = detect_mod_tier(mod)
        tier_str = result.tier_label if result.tier else "???"
        crafted = " [CRAFTED]" if result.is_crafted else ""
        print(f"  {tier_str:4} | {mod}{crafted}")
        if result.stat_type:
            print(f"       → {result.stat_type}: {result.value}")
        print()
