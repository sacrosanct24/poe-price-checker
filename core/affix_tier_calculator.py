"""
Affix Tier Calculator

Calculates what affix tiers are achievable at a given item level,
and generates ideal rare item specs based on stat priorities.

Now supports RePoE data for accurate tier information from game files.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from core.build_priorities import BuildPriorities, AVAILABLE_STATS

if TYPE_CHECKING:
    from core.repoe_tier_provider import RePoETierProvider

logger = logging.getLogger(__name__)


# Item level requirements for affix tiers
# Format: {stat_type: [(tier, ilvl_required, min_value, max_value), ...]}
# Based on PoE game data - tiers are 1 (best) to higher numbers (worse)
AFFIX_TIER_DATA = {
    # === LIFE ===
    "life": [
        (1, 86, 100, 109),  # T1: ilvl 86+
        (2, 82, 90, 99),    # T2: ilvl 82+
        (3, 73, 80, 89),    # T3: ilvl 73+
        (4, 64, 70, 79),    # T4: ilvl 64+
        (5, 54, 60, 69),    # T5: ilvl 54+
        (6, 44, 50, 59),    # T6: ilvl 44+
        (7, 36, 40, 49),    # T7: ilvl 36+
    ],

    # === ENERGY SHIELD (flat) ===
    "energy_shield": [
        (1, 69, 56, 62),
        (2, 60, 43, 49),
        (3, 51, 32, 38),
        (4, 42, 24, 28),
        (5, 33, 17, 21),
    ],

    # === RESISTANCES ===
    "fire_resistance": [
        (1, 84, 46, 48),
        (2, 72, 43, 45),
        (3, 60, 36, 41),
        (4, 48, 30, 35),
        (5, 36, 24, 29),
        (6, 24, 18, 23),
        (7, 12, 12, 17),
    ],
    "cold_resistance": [
        (1, 84, 46, 48),
        (2, 72, 43, 45),
        (3, 60, 36, 41),
        (4, 48, 30, 35),
        (5, 36, 24, 29),
        (6, 24, 18, 23),
        (7, 12, 12, 17),
    ],
    "lightning_resistance": [
        (1, 84, 46, 48),
        (2, 72, 43, 45),
        (3, 60, 36, 41),
        (4, 48, 30, 35),
        (5, 36, 24, 29),
        (6, 24, 18, 23),
        (7, 12, 12, 17),
    ],
    "chaos_resistance": [
        (1, 81, 31, 35),
        (2, 65, 26, 30),
        (3, 56, 21, 25),
        (4, 44, 16, 20),
        (5, 30, 11, 15),
    ],

    # === ATTRIBUTES ===
    "strength": [
        (1, 82, 51, 55),
        (2, 74, 43, 50),
        (3, 60, 38, 42),
        (4, 44, 33, 37),
        (5, 33, 28, 32),
        (6, 22, 23, 27),
        (7, 11, 18, 22),
    ],
    "dexterity": [
        (1, 82, 51, 55),
        (2, 74, 43, 50),
        (3, 60, 38, 42),
        (4, 44, 33, 37),
        (5, 33, 28, 32),
        (6, 22, 23, 27),
        (7, 11, 18, 22),
    ],
    "intelligence": [
        (1, 82, 51, 55),
        (2, 74, 43, 50),
        (3, 60, 38, 42),
        (4, 44, 33, 37),
        (5, 33, 28, 32),
        (6, 22, 23, 27),
        (7, 11, 18, 22),
    ],
    "all_attributes": [
        (1, 85, 16, 20),
        (2, 68, 13, 15),
        (3, 44, 9, 12),
        (4, 22, 6, 8),
    ],

    # === MOVEMENT SPEED ===
    "movement_speed": [
        (1, 86, 35, 35),  # T1 35% (boots only, special)
        (2, 75, 30, 30),
        (3, 55, 25, 25),
        (4, 40, 20, 20),
        (5, 15, 15, 15),
        (6, 1, 10, 10),
    ],

    # === ATTACK SPEED ===
    "attack_speed": [
        (1, 76, 14, 16),
        (2, 60, 11, 13),
        (3, 45, 8, 10),
        (4, 30, 5, 7),
    ],

    # === CAST SPEED ===
    "cast_speed": [
        (1, 76, 14, 16),
        (2, 60, 11, 13),
        (3, 45, 8, 10),
        (4, 30, 5, 7),
    ],

    # === CRITICAL STRIKE ===
    "critical_strike_chance": [
        (1, 80, 38, 42),
        (2, 59, 33, 37),
        (3, 44, 28, 32),
        (4, 30, 23, 27),
    ],
    "critical_strike_multiplier": [
        (1, 82, 35, 38),
        (2, 64, 30, 34),
        (3, 44, 25, 29),
        (4, 27, 20, 24),
    ],

    # === MANA ===
    "mana": [
        (1, 81, 75, 79),
        (2, 73, 69, 74),
        (3, 65, 60, 68),
        (4, 56, 55, 59),
        (5, 47, 45, 54),
    ],

    # === ARMOUR/EVASION ===
    "armour": [
        (1, 84, 631, 750),
        (2, 72, 506, 630),
        (3, 60, 401, 505),
        (4, 46, 301, 400),
        (5, 30, 201, 300),
    ],
    "evasion": [
        (1, 84, 631, 750),
        (2, 72, 506, 630),
        (3, 60, 401, 505),
        (4, 46, 301, 400),
        (5, 30, 201, 300),
    ],

    # === SPELL SUPPRESSION ===
    "spell_suppression": [
        (1, 80, 19, 22),
        (2, 68, 15, 18),
        (3, 56, 11, 14),
        (4, 44, 7, 10),
    ],

    # === DAMAGE ===
    "physical_damage": [
        (1, 83, 25, 29),  # % increased
        (2, 64, 20, 24),
        (3, 46, 15, 19),
        (4, 28, 10, 14),
    ],
    "elemental_damage": [
        (1, 86, 37, 42),  # % increased
        (2, 68, 31, 36),
        (3, 50, 25, 30),
        (4, 35, 19, 24),
    ],
    "spell_damage": [
        (1, 80, 30, 35),
        (2, 64, 25, 29),
        (3, 46, 20, 24),
        (4, 30, 15, 19),
    ],

    # === REGEN ===
    "life_regeneration": [
        (1, 83, 7, 9),  # flat life regen per second
        (2, 74, 5, 6),
        (3, 62, 3, 4),
        (4, 46, 2, 2),
    ],
    "mana_regeneration": [
        (1, 79, 70, 79),  # % increased
        (2, 59, 60, 69),
        (3, 42, 50, 59),
        (4, 24, 40, 49),
    ],
}

# Slot-specific affix availability
# Which affixes can roll on which slots
SLOT_AVAILABLE_AFFIXES = {
    "Helmet": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength", "dexterity",
        "intelligence", "all_attributes", "armour", "evasion", "mana",
    ],
    "Body Armour": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength", "dexterity",
        "intelligence", "all_attributes", "armour", "evasion", "mana",
    ],
    "Gloves": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength", "dexterity",
        "intelligence", "all_attributes", "armour", "evasion",
        "attack_speed",
    ],
    "Boots": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength", "dexterity",
        "intelligence", "all_attributes", "armour", "evasion",
        "movement_speed",
    ],
    "Belt": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength",
        "armour",
    ],
    "Ring": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength", "dexterity",
        "intelligence", "all_attributes", "mana",
    ],
    "Amulet": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength", "dexterity",
        "intelligence", "all_attributes", "mana",
        "critical_strike_chance", "critical_strike_multiplier",
    ],
    "Shield": [
        "life", "energy_shield", "fire_resistance", "cold_resistance",
        "lightning_resistance", "chaos_resistance", "strength", "dexterity",
        "intelligence", "all_attributes", "armour", "evasion",
        "spell_suppression",
    ],
}


@dataclass
class AffixTier:
    """Represents a single affix tier with its requirements and values."""
    stat_type: str
    tier: int
    ilvl_required: int
    min_value: int
    max_value: int
    mod_name: str = ""  # The in-game mod name (e.g., "Prime", "of Tzteosh")

    @property
    def stat_name(self) -> str:
        return AVAILABLE_STATS.get(self.stat_type, self.stat_type)

    @property
    def display_range(self) -> str:
        if self.min_value == self.max_value:
            return str(self.min_value)
        return f"{self.min_value}-{self.max_value}"

    @property
    def full_display(self) -> str:
        """Display with mod name if available."""
        if self.mod_name:
            return f"{self.mod_name}: {self.display_range}"
        return self.display_range


@dataclass
class IdealRareSpec:
    """Specification for an ideal rare item."""
    slot: str
    target_ilvl: int
    affixes: List[AffixTier] = field(default_factory=list)
    notes: str = ""

    def get_total_value_for_stat(self, stat_type: str) -> Tuple[int, int]:
        """Get min/max total value for a stat across all affixes."""
        total_min = 0
        total_max = 0
        for affix in self.affixes:
            if affix.stat_type == stat_type:
                total_min += affix.min_value
                total_max += affix.max_value
        return total_min, total_max


class AffixTierCalculator:
    """
    Calculates achievable affix tiers based on item level.

    Can use either hardcoded tier data or RePoE data for accurate game values.
    """

    def __init__(self, use_repoe: bool = True):
        """
        Initialize the calculator.

        Args:
            use_repoe: If True, attempt to use RePoE data for accurate tiers.
                       Falls back to hardcoded data if RePoE unavailable.
        """
        self._slot_affixes = SLOT_AVAILABLE_AFFIXES
        self._repoe_provider: Optional["RePoETierProvider"] = None
        self._tier_data = AFFIX_TIER_DATA

        if use_repoe:
            try:
                from core.repoe_tier_provider import get_repoe_tier_provider
                self._repoe_provider = get_repoe_tier_provider()
                logger.info("AffixTierCalculator using RePoE data")
            except Exception as e:
                logger.warning(f"Failed to load RePoE provider, using hardcoded data: {e}")

    @property
    def using_repoe(self) -> bool:
        """Check if using RePoE data."""
        return self._repoe_provider is not None

    def get_best_tier_for_ilvl(
        self,
        stat_type: str,
        ilvl: int
    ) -> Optional[AffixTier]:
        """
        Get the best tier achievable for a stat at a given ilvl.

        Args:
            stat_type: Stat type key (e.g., "life", "fire_resistance")
            ilvl: Target item level

        Returns:
            AffixTier for the best achievable tier, or None if stat unknown
        """
        # Try RePoE first
        if self._repoe_provider:
            repoe_tier = self._repoe_provider.get_best_tier_for_ilvl(stat_type, ilvl)
            if repoe_tier:
                return AffixTier(
                    stat_type=stat_type,
                    tier=repoe_tier.tier_number,
                    ilvl_required=repoe_tier.ilvl_required,
                    min_value=repoe_tier.min_value,
                    max_value=repoe_tier.max_value,
                    mod_name=repoe_tier.mod_name,
                )

        # Fall back to hardcoded data
        tiers = self._tier_data.get(stat_type, [])
        if not tiers:
            return None

        # Find best tier where ilvl >= required
        for tier, ilvl_req, min_val, max_val in tiers:
            if ilvl >= ilvl_req:
                return AffixTier(
                    stat_type=stat_type,
                    tier=tier,
                    ilvl_required=ilvl_req,
                    min_value=min_val,
                    max_value=max_val,
                )

        # Return lowest tier if none match (shouldn't happen normally)
        last = tiers[-1]
        return AffixTier(
            stat_type=stat_type,
            tier=last[0],
            ilvl_required=last[1],
            min_value=last[2],
            max_value=last[3],
        )

    def get_all_tiers(self, stat_type: str) -> List[AffixTier]:
        """Get all tiers for a stat type."""
        # Try RePoE first
        if self._repoe_provider:
            repoe_tiers = self._repoe_provider.get_tiers_for_stat(stat_type)
            if repoe_tiers:
                return [
                    AffixTier(
                        stat_type=stat_type,
                        tier=t.tier_number,
                        ilvl_required=t.ilvl_required,
                        min_value=t.min_value,
                        max_value=t.max_value,
                        mod_name=t.mod_name,
                    )
                    for t in repoe_tiers
                ]

        # Fall back to hardcoded data
        tiers = self._tier_data.get(stat_type, [])
        return [
            AffixTier(
                stat_type=stat_type,
                tier=tier,
                ilvl_required=ilvl_req,
                min_value=min_val,
                max_value=max_val,
            )
            for tier, ilvl_req, min_val, max_val in tiers
        ]

    def can_slot_have_stat(self, slot: str, stat_type: str) -> bool:
        """Check if a slot can have a particular stat."""
        available = self._slot_affixes.get(slot, [])
        return stat_type in available

    def get_available_stats_for_slot(self, slot: str) -> List[str]:
        """Get all stats that can roll on a slot."""
        return self._slot_affixes.get(slot, [])

    def calculate_ideal_rare(
        self,
        slot: str,
        priorities: BuildPriorities,
        target_ilvl: int = 86,
        max_affixes: int = 6,  # 3 prefix + 3 suffix typical
    ) -> IdealRareSpec:
        """
        Calculate the ideal rare item spec based on priorities and ilvl.

        Args:
            slot: Equipment slot (e.g., "Helmet", "Boots")
            priorities: User's stat priorities
            target_ilvl: Target item level
            max_affixes: Maximum number of affixes to include

        Returns:
            IdealRareSpec with the best achievable affixes
        """
        spec = IdealRareSpec(slot=slot, target_ilvl=target_ilvl)
        available = self._slot_affixes.get(slot, [])

        if not available:
            spec.notes = f"Unknown slot: {slot}"
            return spec

        added_stats = set()

        # Add critical stats first
        for p in priorities.critical:
            if len(spec.affixes) >= max_affixes:
                break
            if p.stat_type in available and p.stat_type not in added_stats:
                tier = self.get_best_tier_for_ilvl(p.stat_type, target_ilvl)
                if tier:
                    spec.affixes.append(tier)
                    added_stats.add(p.stat_type)

        # Then important stats
        for p in priorities.important:
            if len(spec.affixes) >= max_affixes:
                break
            if p.stat_type in available and p.stat_type not in added_stats:
                tier = self.get_best_tier_for_ilvl(p.stat_type, target_ilvl)
                if tier:
                    spec.affixes.append(tier)
                    added_stats.add(p.stat_type)

        # Finally nice-to-have stats
        for p in priorities.nice_to_have:
            if len(spec.affixes) >= max_affixes:
                break
            if p.stat_type in available and p.stat_type not in added_stats:
                tier = self.get_best_tier_for_ilvl(p.stat_type, target_ilvl)
                if tier:
                    spec.affixes.append(tier)
                    added_stats.add(p.stat_type)

        # If we still have room, add build-type defaults
        if len(spec.affixes) < max_affixes:
            # Life for life builds, ES for ES builds
            if priorities.is_life_build and "life" not in added_stats:
                if "life" in available:
                    tier = self.get_best_tier_for_ilvl("life", target_ilvl)
                    if tier:
                        spec.affixes.append(tier)
                        added_stats.add("life")
            elif priorities.is_es_build and "energy_shield" not in added_stats:
                if "energy_shield" in available:
                    tier = self.get_best_tier_for_ilvl("energy_shield", target_ilvl)
                    if tier:
                        spec.affixes.append(tier)
                        added_stats.add("energy_shield")

        # Add movement speed on boots if not already included
        if slot == "Boots" and "movement_speed" not in added_stats:
            if len(spec.affixes) < max_affixes:
                tier = self.get_best_tier_for_ilvl("movement_speed", target_ilvl)
                if tier:
                    spec.affixes.append(tier)
                    added_stats.add("movement_speed")

        spec.notes = f"ilvl {target_ilvl}: {len(spec.affixes)} affixes"
        return spec

    def format_ideal_rare_summary(self, spec: IdealRareSpec, show_mod_names: bool = True) -> str:
        """Format an ideal rare spec as a human-readable summary."""
        lines = [f"=== Ideal {spec.slot} (ilvl {spec.target_ilvl}) ==="]

        for affix in spec.affixes:
            tier_str = f"T{affix.tier}"
            if show_mod_names and affix.mod_name:
                lines.append(
                    f"  {tier_str} {affix.stat_name} ({affix.mod_name}): {affix.display_range} "
                    f"(requires ilvl {affix.ilvl_required})"
                )
            else:
                lines.append(
                    f"  {tier_str} {affix.stat_name}: {affix.display_range} "
                    f"(requires ilvl {affix.ilvl_required})"
                )

        return "\n".join(lines)


# Testing
if __name__ == "__main__":
    from core.build_priorities import BuildPriorities, PriorityTier

    calc = AffixTierCalculator()

    # Test tier lookup
    print("=== Life Tiers ===")
    for tier in calc.get_all_tiers("life"):
        print(f"  T{tier.tier}: {tier.display_range} (ilvl {tier.ilvl_required}+)")

    print("\n=== Best Life at ilvl 75 ===")
    best = calc.get_best_tier_for_ilvl("life", 75)
    if best:
        print(f"  T{best.tier}: {best.display_range}")

    print("\n=== Ideal Rare Calculation ===")
    priorities = BuildPriorities()
    priorities.add_priority("life", PriorityTier.CRITICAL)
    priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)
    priorities.add_priority("cold_resistance", PriorityTier.IMPORTANT)
    priorities.add_priority("strength", PriorityTier.NICE_TO_HAVE)

    spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=83)
    print(calc.format_ideal_rare_summary(spec))

    print("\n=== Boots with Movement Speed ===")
    spec = calc.calculate_ideal_rare("Boots", priorities, target_ilvl=86)
    print(calc.format_ideal_rare_summary(spec))
