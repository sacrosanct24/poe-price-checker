"""
BiS (Best-in-Slot) Item Calculator.

Analyzes build stats to determine optimal affix priorities for each equipment slot,
then generates trade search queries to find upgrades.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.build_stat_calculator import BuildStats
from core.build_priorities import BuildPriorities, AVAILABLE_STATS
from data_sources.pricing.trade_stat_ids import AFFIX_TO_STAT_ID

logger = logging.getLogger(__name__)


# Equipment slot definitions with their possible stats
EQUIPMENT_SLOTS = {
    "Helmet": {
        "base_types": ["Helmet", "Crown", "Mask", "Hood", "Cap", "Coif", "Casque", "Bascinet", "Burgonet", "Circlet"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "armour", "evasion", "mana"],
    },
    "Body Armour": {
        "base_types": ["Body Armour", "Robe", "Vest", "Plate", "Garb", "Tunic", "Brigandine", "Regalia", "Coat"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "armour", "evasion", "mana"],
    },
    "Gloves": {
        "base_types": ["Gloves", "Gauntlets", "Mitts"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "armour", "evasion", "attack_speed"],
    },
    "Boots": {
        "base_types": ["Boots", "Greaves", "Shoes", "Slippers"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "movement_speed", "armour", "evasion"],
    },
    "Belt": {
        "base_types": ["Belt", "Sash", "Stygian Vise"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "flask_charges", "armour"],
    },
    "Ring": {
        "base_types": ["Ring"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "mana", "added_physical_damage"],
    },
    "Amulet": {
        "base_types": ["Amulet"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "mana", "critical_strike_multiplier"],
    },
    "Shield": {
        "base_types": ["Shield", "Buckler", "Kite Shield", "Spirit Shield"],
        "can_have": ["life", "energy_shield", "resistances", "attributes", "armour", "evasion", "spell_suppression"],
    },
}


@dataclass
class StatRequirement:
    """A stat requirement for BiS item search."""
    stat_type: str  # e.g., "life", "fire_resistance"
    stat_id: str    # Trade API stat ID
    min_value: int  # Minimum value to search for
    priority: int   # 1 = highest priority
    reason: str     # Why this stat is needed


@dataclass
class BiSRequirements:
    """Best-in-Slot requirements for a specific equipment slot."""
    slot: str
    required_stats: List[StatRequirement] = field(default_factory=list)
    desired_stats: List[StatRequirement] = field(default_factory=list)
    min_item_level: int = 75
    max_results: int = 20


class BiSCalculator:
    """
    Calculate BiS item requirements based on build stats.

    Analyzes what stats the build needs most and generates
    trade search requirements for each equipment slot.
    """

    # Resistance thresholds
    OVERCAP_THRESHOLD = 30  # Below this is considered "needs more"
    CHAOS_RES_TARGET = 40   # Target chaos res (not always needed)

    # Priority tiers
    PRIORITY_CRITICAL = 1   # Must have (life for life builds, capping res)
    PRIORITY_HIGH = 2       # Very important
    PRIORITY_MEDIUM = 3     # Nice to have
    PRIORITY_LOW = 4        # Optional optimization

    def __init__(self, build_stats: BuildStats):
        """
        Initialize calculator with build stats.

        Args:
            build_stats: BuildStats from PoB profile
        """
        self.stats = build_stats
        self._analyze_build()

    def _analyze_build(self) -> None:
        """Analyze build to determine priorities."""
        # Determine if life or ES build
        self.is_life_build = self.stats.total_life > self.stats.total_es * 2
        self.is_es_build = self.stats.total_es > self.stats.total_life

        # Check resistance gaps
        self.needs_fire_res = self.stats.fire_overcap < self.OVERCAP_THRESHOLD
        self.needs_cold_res = self.stats.cold_overcap < self.OVERCAP_THRESHOLD
        self.needs_lightning_res = self.stats.lightning_overcap < self.OVERCAP_THRESHOLD
        self.needs_chaos_res = self.stats.chaos_res < self.CHAOS_RES_TARGET

        # Check if build is attribute-starved
        self.needs_strength = self.stats.strength < 100
        self.needs_dexterity = self.stats.dexterity < 100
        self.needs_intelligence = self.stats.intelligence < 100

        logger.info(
            "Build analysis: life=%s, ES=%s, needs_res=[F:%s,C:%s,L:%s,Ch:%s]",
            self.is_life_build, self.is_es_build,
            self.needs_fire_res, self.needs_cold_res,
            self.needs_lightning_res, self.needs_chaos_res
        )

    def calculate_requirements(
        self,
        slot: str,
        custom_priorities: Optional[BuildPriorities] = None
    ) -> BiSRequirements:
        """
        Calculate BiS requirements for a specific equipment slot.

        Args:
            slot: Equipment slot name (e.g., "Helmet", "Boots")
            custom_priorities: Optional user-defined stat priorities

        Returns:
            BiSRequirements with prioritized stat requirements
        """
        if slot not in EQUIPMENT_SLOTS:
            raise ValueError(f"Unknown equipment slot: {slot}")

        slot_info = EQUIPMENT_SLOTS[slot]
        can_have = slot_info["can_have"]

        requirements = BiSRequirements(slot=slot)

        # If custom priorities are provided, use them instead of auto-detection
        if custom_priorities:
            return self._calculate_from_priorities(slot, can_have, custom_priorities)

        # === REQUIRED STATS (Critical for build) ===

        # Life/ES based on build type
        if self.is_life_build and "life" in can_have:
            requirements.required_stats.append(self._make_stat(
                "life", min_value=70, priority=self.PRIORITY_CRITICAL,
                reason="Life build - max life is essential"
            ))
        elif self.is_es_build and "energy_shield" in can_have:
            requirements.required_stats.append(self._make_stat(
                "energy_shield", min_value=50, priority=self.PRIORITY_CRITICAL,
                reason="ES build - energy shield is essential"
            ))

        # Movement speed for boots
        if slot == "Boots" and "movement_speed" in can_have:
            requirements.required_stats.append(self._make_stat(
                "movement_speed", min_value=25, priority=self.PRIORITY_HIGH,
                reason="Movement speed is critical for boots"
            ))

        # === DESIRED STATS (Based on build gaps) ===

        # Resistances if needed
        if self.needs_fire_res and "resistances" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "fire_resistance", min_value=30, priority=self.PRIORITY_HIGH,
                reason=f"Fire res below overcap threshold ({int(self.stats.fire_overcap)}% overcap)"
            ))

        if self.needs_cold_res and "resistances" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "cold_resistance", min_value=30, priority=self.PRIORITY_HIGH,
                reason=f"Cold res below overcap threshold ({int(self.stats.cold_overcap)}% overcap)"
            ))

        if self.needs_lightning_res and "resistances" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "lightning_resistance", min_value=30, priority=self.PRIORITY_HIGH,
                reason=f"Lightning res below overcap threshold ({int(self.stats.lightning_overcap)}% overcap)"
            ))

        if self.needs_chaos_res and "resistances" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "chaos_resistance", min_value=20, priority=self.PRIORITY_MEDIUM,
                reason=f"Chaos res below target ({int(self.stats.chaos_res)}%)"
            ))

        # Attributes if needed
        if self.needs_strength and "attributes" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "strength", min_value=30, priority=self.PRIORITY_MEDIUM,
                reason=f"Build needs more strength ({int(self.stats.strength)})"
            ))

        if self.needs_dexterity and "attributes" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "dexterity", min_value=30, priority=self.PRIORITY_MEDIUM,
                reason=f"Build needs more dexterity ({int(self.stats.dexterity)})"
            ))

        if self.needs_intelligence and "attributes" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "intelligence", min_value=30, priority=self.PRIORITY_MEDIUM,
                reason=f"Build needs more intelligence ({int(self.stats.intelligence)})"
            ))

        # Slot-specific desired stats
        if slot == "Gloves" and "attack_speed" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "attack_speed", min_value=8, priority=self.PRIORITY_MEDIUM,
                reason="Attack speed is valuable on gloves"
            ))

        if slot == "Amulet" and "critical_strike_multiplier" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "critical_strike_multiplier", min_value=20, priority=self.PRIORITY_MEDIUM,
                reason="Crit multi is valuable on amulets"
            ))

        if slot == "Shield" and "spell_suppression" in can_have:
            requirements.desired_stats.append(self._make_stat(
                "spell_suppression", min_value=10, priority=self.PRIORITY_MEDIUM,
                reason="Spell suppression provides defense"
            ))

        # Sort by priority
        requirements.required_stats.sort(key=lambda x: x.priority)
        requirements.desired_stats.sort(key=lambda x: x.priority)

        return requirements

    def _make_stat(
        self,
        stat_type: str,
        min_value: int,
        priority: int,
        reason: str
    ) -> StatRequirement:
        """Create a StatRequirement with proper trade stat ID."""
        stat_mapping = AFFIX_TO_STAT_ID.get(stat_type)

        if stat_mapping:
            stat_id = stat_mapping[0]
        else:
            # Fallback for unmapped stats
            stat_id = f"pseudo.pseudo_total_{stat_type}"
            logger.warning(f"No stat mapping for {stat_type}, using fallback: {stat_id}")

        return StatRequirement(
            stat_type=stat_type,
            stat_id=stat_id,
            min_value=min_value,
            priority=priority,
            reason=reason,
        )

    def _calculate_from_priorities(
        self,
        slot: str,
        can_have: List[str],
        priorities: BuildPriorities
    ) -> BiSRequirements:
        """
        Calculate requirements from user-defined priorities.

        Args:
            slot: Equipment slot name
            can_have: List of stat types this slot can have
            priorities: User-defined BuildPriorities

        Returns:
            BiSRequirements based on user priorities
        """
        requirements = BiSRequirements(slot=slot)

        # Map stat_type to can_have categories
        stat_to_category = {
            "life": "life",
            "energy_shield": "energy_shield",
            "armour": "armour",
            "evasion": "evasion",
            "spell_suppression": "spell_suppression",
            "fire_resistance": "resistances",
            "cold_resistance": "resistances",
            "lightning_resistance": "resistances",
            "chaos_resistance": "resistances",
            "all_resistances": "resistances",
            "strength": "attributes",
            "dexterity": "attributes",
            "intelligence": "attributes",
            "all_attributes": "attributes",
            "attack_speed": "attack_speed",
            "cast_speed": "cast_speed",
            "critical_strike_chance": "critical_strike_chance",
            "critical_strike_multiplier": "critical_strike_multiplier",
            "movement_speed": "movement_speed",
            "mana": "mana",
        }

        def can_have_stat(stat_type: str) -> bool:
            """Check if this slot can have this stat."""
            category = stat_to_category.get(stat_type, stat_type)
            return category in can_have

        # Add critical priorities as required stats
        for p in priorities.critical:
            if can_have_stat(p.stat_type):
                min_val = p.min_value or self._default_min_value(p.stat_type)
                stat_name = AVAILABLE_STATS.get(p.stat_type, p.stat_type)
                requirements.required_stats.append(self._make_stat(
                    p.stat_type, min_value=min_val, priority=self.PRIORITY_CRITICAL,
                    reason=f"Critical: {p.notes}" if p.notes else f"Critical: {stat_name}"
                ))

        # Add important priorities as high-priority desired stats
        for p in priorities.important:
            if can_have_stat(p.stat_type):
                min_val = p.min_value or self._default_min_value(p.stat_type)
                stat_name = AVAILABLE_STATS.get(p.stat_type, p.stat_type)
                requirements.desired_stats.append(self._make_stat(
                    p.stat_type, min_value=min_val, priority=self.PRIORITY_HIGH,
                    reason=f"Important: {p.notes}" if p.notes else f"Important: {stat_name}"
                ))

        # Add nice-to-have as medium-priority desired stats
        for p in priorities.nice_to_have:
            if can_have_stat(p.stat_type):
                min_val = p.min_value or self._default_min_value(p.stat_type)
                stat_name = AVAILABLE_STATS.get(p.stat_type, p.stat_type)
                requirements.desired_stats.append(self._make_stat(
                    p.stat_type, min_value=min_val, priority=self.PRIORITY_MEDIUM,
                    reason=f"Nice: {p.notes}" if p.notes else f"Nice to have: {stat_name}"
                ))

        # If no critical stats were added, fall back to build-type defaults
        if not requirements.required_stats:
            if priorities.is_life_build and "life" in can_have:
                requirements.required_stats.append(self._make_stat(
                    "life", min_value=70, priority=self.PRIORITY_CRITICAL,
                    reason="Life build - max life is essential"
                ))
            elif priorities.is_es_build and "energy_shield" in can_have:
                requirements.required_stats.append(self._make_stat(
                    "energy_shield", min_value=50, priority=self.PRIORITY_CRITICAL,
                    reason="ES build - energy shield is essential"
                ))

        # Sort by priority
        requirements.required_stats.sort(key=lambda x: x.priority)
        requirements.desired_stats.sort(key=lambda x: x.priority)

        return requirements

    def _default_min_value(self, stat_type: str) -> int:
        """Get default minimum value for a stat type."""
        defaults = {
            "life": 70,
            "energy_shield": 50,
            "fire_resistance": 30,
            "cold_resistance": 30,
            "lightning_resistance": 30,
            "chaos_resistance": 20,
            "all_resistances": 20,
            "strength": 30,
            "dexterity": 30,
            "intelligence": 30,
            "all_attributes": 20,
            "movement_speed": 25,
            "attack_speed": 8,
            "cast_speed": 8,
            "critical_strike_chance": 30,
            "critical_strike_multiplier": 20,
            "armour": 200,
            "evasion": 200,
            "spell_suppression": 10,
            "mana": 50,
        }
        return defaults.get(stat_type, 20)

    def get_all_slot_requirements(self) -> Dict[str, BiSRequirements]:
        """Get BiS requirements for all equipment slots."""
        return {
            slot: self.calculate_requirements(slot)
            for slot in EQUIPMENT_SLOTS
        }

    def get_build_analysis_summary(self) -> str:
        """Get a human-readable summary of build analysis."""
        lines = ["Build Analysis:"]

        # Build type
        if self.is_life_build:
            lines.append(f"  Type: Life build ({int(self.stats.total_life)} life)")
        elif self.is_es_build:
            lines.append(f"  Type: ES build ({int(self.stats.total_es)} ES)")
        else:
            lines.append(f"  Type: Hybrid ({int(self.stats.total_life)} life, {int(self.stats.total_es)} ES)")

        # Resistances
        res_issues = []
        if self.needs_fire_res:
            res_issues.append(f"Fire ({int(self.stats.fire_overcap)}% overcap)")
        if self.needs_cold_res:
            res_issues.append(f"Cold ({int(self.stats.cold_overcap)}% overcap)")
        if self.needs_lightning_res:
            res_issues.append(f"Lightning ({int(self.stats.lightning_overcap)}% overcap)")
        if self.needs_chaos_res:
            res_issues.append(f"Chaos ({int(self.stats.chaos_res)}%)")

        if res_issues:
            lines.append(f"  Needs Res: {', '.join(res_issues)}")
        else:
            lines.append("  Resistances: Good")

        # Attributes
        attr_issues = []
        if self.needs_strength:
            attr_issues.append(f"Str ({int(self.stats.strength)})")
        if self.needs_dexterity:
            attr_issues.append(f"Dex ({int(self.stats.dexterity)})")
        if self.needs_intelligence:
            attr_issues.append(f"Int ({int(self.stats.intelligence)})")

        if attr_issues:
            lines.append(f"  Needs Attr: {', '.join(attr_issues)}")

        return "\n".join(lines)


def build_trade_query(requirements: BiSRequirements, league: str = "Standard") -> Dict:
    """
    Build a trade API query from BiS requirements.

    Args:
        requirements: BiSRequirements for a slot
        league: League name

    Returns:
        Trade API query dict
    """
    # Start with basic query structure
    stats_filter: Dict[str, Any] = {"type": "and", "filters": []}
    query: Dict[str, Any] = {
        "query": {
            "status": {"option": "online"},
            "stats": [stats_filter],
        },
        "sort": {"price": "asc"},
    }

    # Add stat filters from required stats (first 2)
    stat_filters: List[Dict[str, Any]] = []
    for stat in requirements.required_stats[:2]:
        stat_filters.append({
            "id": stat.stat_id,
            "value": {"min": stat.min_value},
        })

    # Add stat filters from desired stats (up to 2 more)
    remaining_slots = 4 - len(stat_filters)
    for stat in requirements.desired_stats[:remaining_slots]:
        stat_filters.append({
            "id": stat.stat_id,
            "value": {"min": stat.min_value},
        })

    stats_filter["filters"] = stat_filters

    return query


def get_trade_url(query: Dict, league: str = "Standard") -> str:
    """
    Generate a pathofexile.com/trade URL for a query.

    Args:
        query: Trade API query dict
        league: League name

    Returns:
        URL string that opens the search on the trade site
    """
    import json
    import urllib.parse

    # Base URL
    base = f"https://www.pathofexile.com/trade/search/{urllib.parse.quote(league)}"

    # Encode query as JSON (for future POST implementation)
    _query_json = json.dumps(query, separators=(',', ':'))

    # The trade site doesn't directly accept query JSON in URL
    # Instead, we'd need to POST and get a search ID
    # For now, return the base URL - the dialog will handle opening searches
    return base


# Testing
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Sample build stats
    sample_stats = {
        "Spec:LifeInc": 158.0,
        "Life": 5637.0,
        "Spec:EnergyShieldInc": 22.0,
        "EnergyShield": 113.0,
        "FireResist": 90.0,
        "FireResistOverCap": 15.0,  # Below threshold
        "ColdResist": 90.0,
        "ColdResistOverCap": 50.0,
        "LightningResist": 90.0,
        "LightningResistOverCap": 45.0,
        "ChaosResist": 30.0,  # Below target
        "Str": 332.0,
        "Dex": 80.0,  # Below 100
        "Int": 144.0,
    }

    build_stats = BuildStats.from_pob_stats(sample_stats)
    calculator = BiSCalculator(build_stats)

    print(calculator.get_build_analysis_summary())
    print()

    print("=== BiS Requirements by Slot ===")
    for slot, reqs in calculator.get_all_slot_requirements().items():
        print(f"\n{slot}:")
        if reqs.required_stats:
            print("  Required:")
            for stat in reqs.required_stats:
                print(f"    - {stat.stat_type}: min {stat.min_value} ({stat.reason})")
        if reqs.desired_stats:
            print("  Desired:")
            for stat in reqs.desired_stats[:3]:  # Show top 3
                print(f"    - {stat.stat_type}: min {stat.min_value} ({stat.reason})")
