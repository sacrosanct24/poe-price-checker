"""
Archetype Matcher.

Scores items against build archetypes to determine which builds
would benefit from an item.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from core.build_archetypes.archetype_models import (
    ArchetypeMatch,
    BuildArchetype,
    CrossBuildAnalysis,
)
from core.build_archetypes.archetype_database import (
    ArchetypeDatabase,
    get_archetype_database,
)

if TYPE_CHECKING:
    from core.item_parser import ParsedItem

logger = logging.getLogger(__name__)


# =============================================================================
# STAT NORMALIZATION
# =============================================================================

# Mapping from common mod text patterns to normalized stat names
STAT_PATTERNS: Dict[str, List[str]] = {
    # Life
    "maximum_life": [
        r"\+(\d+) to maximum life",
        r"(\d+)% increased maximum life",
    ],
    "life_regeneration_rate": [
        r"(\d+\.?\d*) life regenerated per second",
        r"(\d+\.?\d*)% of life regenerated per second",
        r"regenerate (\d+\.?\d*)% of life per second",
    ],
    "life_leech": [
        r"(\d+\.?\d*)% of .* damage leeched as life",
        r"(\d+\.?\d*)% of physical attack damage leeched as life",
    ],

    # Energy Shield
    "maximum_energy_shield": [
        r"\+(\d+) to maximum energy shield",
        r"(\d+)% increased maximum energy shield",
    ],
    "energy_shield_recharge": [
        r"(\d+)% faster start of energy shield recharge",
        r"(\d+)% increased energy shield recharge rate",
    ],
    "energy_shield_regeneration": [
        r"regenerate (\d+\.?\d*)% of energy shield per second",
    ],

    # Resistances
    "fire_resistance": [
        r"\+(\d+)% to fire resistance",
    ],
    "cold_resistance": [
        r"\+(\d+)% to cold resistance",
    ],
    "lightning_resistance": [
        r"\+(\d+)% to lightning resistance",
    ],
    "chaos_resistance": [
        r"\+(\d+)% to chaos resistance",
    ],
    "maximum_fire_resistance": [
        r"\+(\d+)% to maximum fire resistance",
    ],

    # Damage - General
    "physical_damage": [
        r"(\d+)% increased physical damage",
        r"adds (\d+) to (\d+) physical damage",
    ],
    "elemental_damage": [
        r"(\d+)% increased elemental damage",
    ],
    "elemental_damage_with_attacks": [
        r"(\d+)% increased elemental damage with attack skills",
    ],
    "spell_damage": [
        r"(\d+)% increased spell damage",
    ],
    "damage_over_time": [
        r"(\d+)% increased damage over time",
    ],

    # Damage - Fire
    "fire_damage": [
        r"(\d+)% increased fire damage",
        r"adds (\d+) to (\d+) fire damage",
    ],
    "burning_damage": [
        r"(\d+)% increased burning damage",
    ],
    "fire_damage_over_time_multiplier": [
        r"\+(\d+)% to fire damage over time multiplier",
    ],

    # Damage - Cold
    "cold_damage": [
        r"(\d+)% increased cold damage",
        r"adds (\d+) to (\d+) cold damage",
    ],
    "cold_damage_over_time_multiplier": [
        r"\+(\d+)% to cold damage over time multiplier",
    ],

    # Damage - Lightning
    "lightning_damage": [
        r"(\d+)% increased lightning damage",
        r"adds (\d+) to (\d+) lightning damage",
    ],
    "added_lightning_damage": [
        r"adds (\d+) to (\d+) lightning damage to attacks",
    ],
    "shock_effect": [
        r"(\d+)% increased effect of shock",
    ],

    # Damage - Chaos
    "chaos_damage": [
        r"(\d+)% increased chaos damage",
        r"adds (\d+) to (\d+) chaos damage",
    ],
    "chaos_damage_over_time_multiplier": [
        r"\+(\d+)% to chaos damage over time multiplier",
    ],
    "poison_damage": [
        r"(\d+)% increased damage with poison",
        r"(\d+)% increased poison damage",
    ],

    # Damage - Physical DoT
    "bleed_damage": [
        r"(\d+)% increased damage with bleeding",
        r"(\d+)% increased bleeding damage",
    ],
    "physical_damage_over_time_multiplier": [
        r"\+(\d+)% to physical damage over time multiplier",
    ],

    # Critical
    "critical_strike_chance": [
        r"(\d+)% increased critical strike chance",
        r"\+(\d+\.?\d*)% to critical strike chance",
        r"(\d+)% increased global critical strike chance",
    ],
    "critical_strike_chance_for_spells": [
        r"(\d+)% increased critical strike chance for spells",
        r"\+(\d+\.?\d*)% to spell critical strike chance",
    ],
    "critical_strike_multiplier": [
        r"\+(\d+)% to critical strike multiplier",
        r"\+(\d+)% to global critical strike multiplier",
    ],

    # Speed
    "attack_speed": [
        r"(\d+)% increased attack speed",
    ],
    "cast_speed": [
        r"(\d+)% increased cast speed",
    ],

    # Minion
    "minion_damage": [
        r"minions deal (\d+)% increased damage",
        r"(\d+)% increased minion damage",
    ],
    "minion_life": [
        r"minions have (\d+)% increased maximum life",
    ],
    "minion_attack_speed": [
        r"minions have (\d+)% increased attack speed",
    ],
    "minion_cast_speed": [
        r"minions have (\d+)% increased cast speed",
    ],
    "minion_spell_damage": [
        r"minions deal (\d+)% increased spell damage",
    ],

    # Trap/Mine/Totem
    "trap_damage": [
        r"(\d+)% increased trap damage",
    ],
    "mine_damage": [
        r"(\d+)% increased mine damage",
    ],
    "totem_damage": [
        r"(\d+)% increased totem damage",
    ],
    "trap_throwing_speed": [
        r"(\d+)% increased trap throwing speed",
    ],
    "totem_life": [
        r"totems have (\d+)% increased maximum life",
    ],

    # Defense
    "armour": [
        r"\+(\d+) to armour",
        r"(\d+)% increased armour",
    ],
    "evasion_rating": [
        r"\+(\d+) to evasion rating",
        r"(\d+)% increased evasion rating",
    ],
    "block_chance": [
        r"\+(\d+)% chance to block",
        r"(\d+)% additional block chance",
    ],
    "spell_block_chance": [
        r"\+(\d+)% chance to block spell damage",
    ],

    # Attributes
    "strength": [
        r"\+(\d+) to strength",
        r"\+(\d+) to all attributes",
    ],
    "dexterity": [
        r"\+(\d+) to dexterity",
        r"\+(\d+) to all attributes",
    ],
    "intelligence": [
        r"\+(\d+) to intelligence",
        r"\+(\d+) to all attributes",
    ],

    # Utility
    "mana": [
        r"\+(\d+) to maximum mana",
    ],
    "mana_regeneration": [
        r"(\d+)% increased mana regeneration rate",
    ],
    "cooldown_recovery": [
        r"(\d+)% increased cooldown recovery rate",
    ],
    "area_of_effect": [
        r"(\d+)% increased area of effect",
    ],
    "projectile_speed": [
        r"(\d+)% increased projectile speed",
    ],
    "accuracy_rating": [
        r"\+(\d+) to accuracy rating",
        r"(\d+)% increased accuracy rating",
    ],

    # Aura/Support
    "aura_effect": [
        r"(\d+)% increased effect of non-curse auras",
        r"auras from your skills have (\d+)% increased effect",
    ],
    "mana_reservation_efficiency": [
        r"(\d+)% increased mana reservation efficiency",
    ],

    # Flask
    "flask_effect": [
        r"(\d+)% increased flask effect",
    ],
    "flask_charges_gained": [
        r"(\d+)% increased flask charges gained",
    ],
}


def extract_item_stats(item: "ParsedItem") -> Dict[str, float]:
    """
    Extract normalized stats from a parsed item.

    Returns a dictionary of stat_name -> value for stats found on the item.
    """
    stats: Dict[str, float] = {}

    # Get all mods from the item
    # Handle both ParsedItem attribute names (explicits vs explicit_mods)
    all_mods: List[str] = []

    # Explicit mods (check both attribute names)
    if hasattr(item, 'explicit_mods') and item.explicit_mods:
        all_mods.extend(item.explicit_mods)
    elif hasattr(item, 'explicits') and item.explicits:
        all_mods.extend(item.explicits)

    # Implicit mods (check both attribute names)
    if hasattr(item, 'implicit_mods') and item.implicit_mods:
        all_mods.extend(item.implicit_mods)
    elif hasattr(item, 'implicits') and item.implicits:
        all_mods.extend(item.implicits)

    # Crafted mods
    if hasattr(item, 'crafted_mods') and item.crafted_mods:
        all_mods.extend(item.crafted_mods)
    elif hasattr(item, 'crafted') and item.crafted:
        all_mods.extend(item.crafted)

    # Fractured mods
    if hasattr(item, 'fractured_mods') and item.fractured_mods:
        all_mods.extend(item.fractured_mods)
    elif hasattr(item, 'fractured') and item.fractured:
        all_mods.extend(item.fractured)

    # Process each mod against patterns
    for mod in all_mods:
        mod_lower = mod.lower()
        for stat_name, patterns in STAT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, mod_lower)
                if match:
                    # Extract the value (first captured group)
                    try:
                        value = float(match.group(1))
                        # Accumulate if stat already found (e.g., from multiple sources)
                        stats[stat_name] = stats.get(stat_name, 0) + value
                    except (ValueError, IndexError):
                        pass
                    break

    return stats


def extract_item_stats_from_dict(item_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract normalized stats from item data dictionary.

    Alternative to extract_item_stats for when working with dict data.
    """
    stats: Dict[str, float] = {}

    # Get all mods from the item dict
    all_mods: List[str] = []
    for key in ['explicit_mods', 'implicit_mods', 'crafted_mods', 'fractured_mods']:
        mods = item_data.get(key, [])
        if isinstance(mods, list):
            all_mods.extend(mods)

    # Process each mod against patterns
    for mod in all_mods:
        if not isinstance(mod, str):
            continue
        mod_lower = mod.lower()
        for stat_name, patterns in STAT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, mod_lower)
                if match:
                    try:
                        value = float(match.group(1))
                        stats[stat_name] = stats.get(stat_name, 0) + value
                    except (ValueError, IndexError):
                        pass
                    break

    return stats


# =============================================================================
# ARCHETYPE MATCHER
# =============================================================================

class ArchetypeMatcher:
    """
    Matches items against build archetypes to find suitable builds.

    Scores each item against all archetypes and returns matches
    sorted by relevance.
    """

    # Scoring thresholds
    EXCELLENT_MATCH = 80.0
    GOOD_MATCH = 60.0
    MODERATE_MATCH = 40.0

    def __init__(self, database: Optional[ArchetypeDatabase] = None):
        """Initialize with optional custom database."""
        self._database = database or get_archetype_database()

    def match_item(
        self,
        item: "ParsedItem",
        min_score: float = 0.0,
    ) -> CrossBuildAnalysis:
        """
        Match a parsed item against all archetypes.

        Args:
            item: Parsed item to analyze
            min_score: Minimum score to include in results

        Returns:
            CrossBuildAnalysis with all matches
        """
        item_stats = extract_item_stats(item)
        item_name = getattr(item, 'name', 'Unknown Item')
        return self._analyze_stats(item_name, item_stats, min_score)

    def match_item_dict(
        self,
        item_data: Dict[str, Any],
        min_score: float = 0.0,
    ) -> CrossBuildAnalysis:
        """
        Match item data dictionary against all archetypes.

        Args:
            item_data: Item data as dictionary
            min_score: Minimum score to include in results

        Returns:
            CrossBuildAnalysis with all matches
        """
        item_stats = extract_item_stats_from_dict(item_data)
        item_name = item_data.get('name', 'Unknown Item')
        return self._analyze_stats(item_name, item_stats, min_score)

    def match_stats(
        self,
        stats: Dict[str, float],
        item_name: str = "Item",
        min_score: float = 0.0,
    ) -> CrossBuildAnalysis:
        """
        Match pre-extracted stats against all archetypes.

        Args:
            stats: Dictionary of stat_name -> value
            item_name: Name for the analysis
            min_score: Minimum score to include in results

        Returns:
            CrossBuildAnalysis with all matches
        """
        return self._analyze_stats(item_name, stats, min_score)

    def _analyze_stats(
        self,
        item_name: str,
        stats: Dict[str, float],
        min_score: float,
    ) -> CrossBuildAnalysis:
        """Internal method to analyze stats against archetypes."""
        matches: List[ArchetypeMatch] = []

        for archetype in self._database.get_all():
            match = self._score_against_archetype(stats, archetype)
            if match.score >= min_score:
                matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        return CrossBuildAnalysis(
            item_name=item_name,
            matches=matches,
        )

    def _score_against_archetype(
        self,
        stats: Dict[str, float],
        archetype: BuildArchetype,
    ) -> ArchetypeMatch:
        """
        Score item stats against a specific archetype.

        Scoring algorithm:
        1. Check for required stats (missing = 0 score)
        2. Sum weighted scores for matching stats
        3. Normalize to 0-100 scale
        """
        matching_stats: List[str] = []
        missing_required: List[str] = []
        reasons: List[str] = []
        total_score = 0.0
        max_possible_score = 0.0

        # Check required stats first
        for req_stat in archetype.required_stats:
            if req_stat not in stats or stats[req_stat] <= 0:
                missing_required.append(req_stat)

        # If missing required stats, score is severely penalized
        if missing_required:
            return ArchetypeMatch(
                archetype=archetype,
                score=0.0,
                matching_stats=[],
                missing_required=missing_required,
                reasons=[f"Missing required: {', '.join(missing_required)}"],
            )

        # Score each key stat
        for key_stat in archetype.key_stats:
            stat_name = key_stat.stat_name
            weight = key_stat.weight
            max_possible_score += weight * 10  # Max 10 points per stat, weighted

            if stat_name in stats:
                value = stats[stat_name]

                # Score based on value relative to thresholds
                if key_stat.ideal_value and key_stat.ideal_value > 0:
                    # Score as percentage of ideal
                    score_pct = min(value / key_stat.ideal_value, 1.5)  # Cap at 150%
                    stat_score = score_pct * 10 * weight
                elif key_stat.min_threshold and key_stat.min_threshold > 0:
                    # Score as percentage above threshold
                    if value >= key_stat.min_threshold:
                        stat_score = 10 * weight
                    else:
                        stat_score = (value / key_stat.min_threshold) * 10 * weight
                else:
                    # Default scoring: assume 100 is "good", scale linearly
                    score_pct = min(value / 100, 1.5)
                    stat_score = score_pct * 10 * weight

                total_score += stat_score
                matching_stats.append(stat_name)

                # Add reason if significant contribution
                if stat_score >= 5:
                    reasons.append(f"+{stat_name.replace('_', ' ').title()}")

        # Also check stat_weights dict
        for stat_name, weight in archetype.stat_weights.items():
            # Skip if already counted in key_stats
            if any(ks.stat_name == stat_name for ks in archetype.key_stats):
                continue

            max_possible_score += weight * 10

            if stat_name in stats:
                value = stats[stat_name]
                score_pct = min(value / 100, 1.5)
                stat_score = score_pct * 10 * weight
                total_score += stat_score
                matching_stats.append(stat_name)

        # Normalize to 0-100 scale
        if max_possible_score > 0:
            normalized_score = (total_score / max_possible_score) * 100
        else:
            normalized_score = 0.0

        # Cap at 100
        normalized_score = min(normalized_score, 100.0)

        return ArchetypeMatch(
            archetype=archetype,
            score=normalized_score,
            matching_stats=matching_stats,
            missing_required=missing_required,
            reasons=reasons[:4],  # Top 4 reasons
        )

    def get_builds_for_stat(self, stat_name: str) -> List[BuildArchetype]:
        """
        Get all builds that value a specific stat.

        Useful for understanding why an item might be valuable.
        """
        builds = []
        for archetype in self._database.get_all():
            if archetype.get_stat_weight(stat_name) > 0:
                builds.append(archetype)

        # Sort by weight for this stat
        builds.sort(
            key=lambda a: a.get_stat_weight(stat_name),
            reverse=True,
        )
        return builds


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_matcher: Optional[ArchetypeMatcher] = None


def get_archetype_matcher() -> ArchetypeMatcher:
    """Get the global archetype matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = ArchetypeMatcher()
    return _matcher


def analyze_item_for_builds(
    item: "ParsedItem",
    min_score: float = 40.0,
) -> CrossBuildAnalysis:
    """
    Convenience function to analyze an item for build matches.

    Args:
        item: Parsed item to analyze
        min_score: Minimum score to include (default 40)

    Returns:
        CrossBuildAnalysis with matches
    """
    return get_archetype_matcher().match_item(item, min_score)


def get_top_builds_for_item(
    item: "ParsedItem",
    limit: int = 3,
) -> List[ArchetypeMatch]:
    """
    Get the top N builds that want this item.

    Args:
        item: Parsed item to analyze
        limit: Maximum matches to return

    Returns:
        List of top ArchetypeMatch results
    """
    analysis = get_archetype_matcher().match_item(item)
    return analysis.get_top_matches(limit)
