"""
Smart Trade Filters.

Generates build-optimized trade query filters based on:
1. Build archetype (life vs ES, crit vs non-crit, etc.)
2. Resistance and attribute gaps
3. Priority ordering (critical stats first)

This module works with the trade_stat_ids mapping to create filters
that find actually useful upgrades for a specific build.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.build_archetype import BuildArchetype, DefenseType, AttackType
from core.build_stat_calculator import BuildStats
from core.upgrade_calculator import UpgradeCalculator
from data_sources.pricing.trade_stat_ids import get_stat_id

logger = logging.getLogger(__name__)


@dataclass
class FilterPriority:
    """A filter with priority information."""
    stat_id: str
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    priority: int = 0  # Lower = higher priority
    reason: str = ""  # Why this filter was added
    is_critical: bool = False  # Must-have filter


@dataclass
class SmartFilterResult:
    """Result of smart filter generation."""
    filters: List[FilterPriority] = field(default_factory=list)
    archetype_summary: str = ""
    gap_summary: str = ""
    filter_reasons: List[str] = field(default_factory=list)

    def to_trade_filters(self, max_filters: int = 6) -> List[Dict[str, Any]]:
        """
        Convert to trade API filter format.

        Args:
            max_filters: Maximum number of filters to include

        Returns:
            List of filter dicts for trade API stats array
        """
        # Sort by priority (lower first), then take top N
        sorted_filters = sorted(self.filters, key=lambda f: f.priority)
        selected = sorted_filters[:max_filters]

        result = []
        for f in selected:
            filter_dict: Dict[str, Any] = {"id": f.stat_id}
            value_dict: Dict[str, Any] = {}

            if f.min_value is not None:
                value_dict["min"] = f.min_value
            if f.max_value is not None:
                value_dict["max"] = f.max_value

            if value_dict:
                filter_dict["value"] = value_dict

            result.append(filter_dict)

        return result


class SmartFilterBuilder:
    """
    Builds optimized trade filters based on build context.

    Uses archetype detection and gap analysis to create filters
    that find actually useful upgrades.
    """

    # Base priority levels
    PRIORITY_CRITICAL = 0      # Must-have (e.g., uncapped resistance)
    PRIORITY_HIGH = 10         # Very important for build
    PRIORITY_MEDIUM = 20       # Good to have
    PRIORITY_LOW = 30          # Nice bonus

    # Minimum values by archetype
    DEFENSE_MINIMUMS = {
        DefenseType.LIFE: {"life": 60, "energy_shield": None},
        DefenseType.ENERGY_SHIELD: {"life": None, "energy_shield": 40},
        DefenseType.HYBRID: {"life": 50, "energy_shield": 30},
        DefenseType.LOW_LIFE: {"life": None, "energy_shield": 50},
    }

    def __init__(
        self,
        archetype: Optional[BuildArchetype] = None,
        build_stats: Optional[BuildStats] = None,
    ):
        """
        Initialize builder with build context.

        Args:
            archetype: Detected build archetype
            build_stats: PoB-calculated build stats
        """
        self.archetype = archetype
        self.build_stats = build_stats
        self.upgrade_calculator = UpgradeCalculator(build_stats) if build_stats else None

    def build_filters(
        self,
        slot: Optional[str] = None,
        item_level: Optional[int] = None,
    ) -> SmartFilterResult:
        """
        Build smart filters for finding upgrades.

        Args:
            slot: Equipment slot (e.g., "Helmet", "Boots")
            item_level: Minimum item level to search for

        Returns:
            SmartFilterResult with prioritized filters
        """
        result = SmartFilterResult()

        if self.archetype:
            result.archetype_summary = self.archetype.get_summary()

        # 1. Add critical filters (gaps)
        self._add_gap_filters(result)

        # 2. Add archetype-based filters
        self._add_archetype_filters(result)

        # 3. Add slot-specific filters
        if slot:
            self._add_slot_filters(result, slot)

        # Build gap summary
        if self.upgrade_calculator:
            gaps = self.upgrade_calculator.calculate_resistance_gaps()
            if gaps.has_gaps():
                gap_parts = []
                if gaps.fire_gap > 0:
                    gap_parts.append(f"Fire: {int(gaps.fire_gap)}%")
                if gaps.cold_gap > 0:
                    gap_parts.append(f"Cold: {int(gaps.cold_gap)}%")
                if gaps.lightning_gap > 0:
                    gap_parts.append(f"Lightning: {int(gaps.lightning_gap)}%")
                if gaps.chaos_gap > 0:
                    gap_parts.append(f"Chaos: {int(gaps.chaos_gap)}%")
                result.gap_summary = f"Resistance gaps: {', '.join(gap_parts)}"

        return result

    def _add_gap_filters(self, result: SmartFilterResult) -> None:
        """Add filters for resistance/attribute gaps."""
        if not self.upgrade_calculator:
            return

        gaps = self.upgrade_calculator.calculate_resistance_gaps()

        # Fire resistance gap
        if gaps.fire_gap > 0:
            stat_id = self._get_stat_id("fire_resistance")
            if stat_id:
                min_val = min(int(gaps.fire_gap), 45)  # Cap at reasonable value
                result.filters.append(FilterPriority(
                    stat_id=stat_id,
                    min_value=min_val,
                    priority=self.PRIORITY_CRITICAL,
                    reason=f"Need {int(gaps.fire_gap)}% fire res to cap",
                    is_critical=True,
                ))
                result.filter_reasons.append(f"Fire res gap: {int(gaps.fire_gap)}%")

        # Cold resistance gap
        if gaps.cold_gap > 0:
            stat_id = self._get_stat_id("cold_resistance")
            if stat_id:
                min_val = min(int(gaps.cold_gap), 45)
                result.filters.append(FilterPriority(
                    stat_id=stat_id,
                    min_value=min_val,
                    priority=self.PRIORITY_CRITICAL,
                    reason=f"Need {int(gaps.cold_gap)}% cold res to cap",
                    is_critical=True,
                ))
                result.filter_reasons.append(f"Cold res gap: {int(gaps.cold_gap)}%")

        # Lightning resistance gap
        if gaps.lightning_gap > 0:
            stat_id = self._get_stat_id("lightning_resistance")
            if stat_id:
                min_val = min(int(gaps.lightning_gap), 45)
                result.filters.append(FilterPriority(
                    stat_id=stat_id,
                    min_value=min_val,
                    priority=self.PRIORITY_CRITICAL,
                    reason=f"Need {int(gaps.lightning_gap)}% lightning res to cap",
                    is_critical=True,
                ))
                result.filter_reasons.append(f"Lightning res gap: {int(gaps.lightning_gap)}%")

        # Chaos resistance gap (lower priority)
        if gaps.chaos_gap > 20:  # Only if significantly under
            stat_id = self._get_stat_id("chaos_resistance")
            if stat_id:
                min_val = min(int(gaps.chaos_gap * 0.5), 30)  # Less aggressive
                result.filters.append(FilterPriority(
                    stat_id=stat_id,
                    min_value=min_val,
                    priority=self.PRIORITY_HIGH,
                    reason=f"Chaos res at {int(75 - gaps.chaos_gap)}%, need more",
                    is_critical=False,
                ))
                result.filter_reasons.append(f"Chaos res gap: {int(gaps.chaos_gap)}%")

    def _add_archetype_filters(self, result: SmartFilterResult) -> None:
        """Add filters based on build archetype."""
        if not self.archetype:
            # Default to life-based generic filters
            self._add_default_filters(result)
            return

        # Defense type filters
        defense = self.archetype.defense_type

        if defense == DefenseType.LIFE:
            stat_id = self._get_stat_id("life")
            if stat_id:
                result.filters.append(FilterPriority(
                    stat_id=stat_id,
                    min_value=60,
                    priority=self.PRIORITY_HIGH,
                    reason="Life build - prioritize life",
                ))
                result.filter_reasons.append("Life build: filtering for +life")

        elif defense == DefenseType.ENERGY_SHIELD:
            stat_id = self._get_stat_id("energy_shield")
            if stat_id:
                result.filters.append(FilterPriority(
                    stat_id=stat_id,
                    min_value=40,
                    priority=self.PRIORITY_HIGH,
                    reason="ES build - prioritize ES",
                ))
                result.filter_reasons.append("ES build: filtering for +ES")

            # ES builds often need intelligence
            int_stat = self._get_stat_id("intelligence")
            if int_stat and self.archetype.needs_intelligence:
                result.filters.append(FilterPriority(
                    stat_id=int_stat,
                    min_value=30,
                    priority=self.PRIORITY_MEDIUM,
                    reason="ES build needs intelligence",
                ))

        elif defense == DefenseType.HYBRID:
            # Both life and ES valuable
            life_stat = self._get_stat_id("life")
            es_stat = self._get_stat_id("energy_shield")
            if life_stat:
                result.filters.append(FilterPriority(
                    stat_id=life_stat,
                    min_value=50,
                    priority=self.PRIORITY_HIGH,
                    reason="Hybrid build - need life",
                ))
            if es_stat:
                result.filters.append(FilterPriority(
                    stat_id=es_stat,
                    min_value=30,
                    priority=self.PRIORITY_HIGH,
                    reason="Hybrid build - need ES",
                ))
            result.filter_reasons.append("Hybrid build: filtering for +life and +ES")

        # Crit build filters
        if self.archetype.is_crit:
            crit_chance = self._get_stat_id("critical_strike_chance")
            crit_multi = self._get_stat_id("critical_strike_multiplier")

            if crit_multi:
                result.filters.append(FilterPriority(
                    stat_id=crit_multi,
                    min_value=20,
                    priority=self.PRIORITY_MEDIUM,
                    reason="Crit build - want crit multi",
                ))
                result.filter_reasons.append("Crit build: filtering for crit multi")

        # Attack type specific
        if self.archetype.attack_type == AttackType.ATTACK:
            as_stat = self._get_stat_id("attack_speed")
            if as_stat:
                result.filters.append(FilterPriority(
                    stat_id=as_stat,
                    min_value=8,
                    priority=self.PRIORITY_LOW,
                    reason="Attack build - attack speed useful",
                ))

        elif self.archetype.attack_type == AttackType.SPELL:
            cs_stat = self._get_stat_id("cast_speed")
            if cs_stat:
                result.filters.append(FilterPriority(
                    stat_id=cs_stat,
                    min_value=8,
                    priority=self.PRIORITY_LOW,
                    reason="Spell build - cast speed useful",
                ))

        # Attribute needs
        if self.archetype.needs_strength:
            str_stat = self._get_stat_id("strength")
            if str_stat:
                result.filters.append(FilterPriority(
                    stat_id=str_stat,
                    min_value=30,
                    priority=self.PRIORITY_MEDIUM,
                    reason="Build needs strength",
                ))
                result.filter_reasons.append("Needs strength for requirements")

        if self.archetype.needs_dexterity:
            dex_stat = self._get_stat_id("dexterity")
            if dex_stat:
                result.filters.append(FilterPriority(
                    stat_id=dex_stat,
                    min_value=30,
                    priority=self.PRIORITY_MEDIUM,
                    reason="Build needs dexterity",
                ))
                result.filter_reasons.append("Needs dexterity for requirements")

    def _add_slot_filters(self, result: SmartFilterResult, slot: str) -> None:
        """Add slot-specific filters."""
        slot_lower = slot.lower()

        # Boots always want movement speed
        if "boot" in slot_lower:
            ms_stat = self._get_stat_id("movement_speed")
            if ms_stat:
                result.filters.append(FilterPriority(
                    stat_id=ms_stat,
                    min_value=25,
                    priority=self.PRIORITY_HIGH,
                    reason="Boots - movement speed essential",
                ))
                result.filter_reasons.append("Boots: filtering for movement speed")

        # Gloves can have attack/cast speed
        elif "glove" in slot_lower:
            if self.archetype and self.archetype.attack_type == AttackType.ATTACK:
                as_stat = self._get_stat_id("attack_speed")
                if as_stat:
                    result.filters.append(FilterPriority(
                        stat_id=as_stat,
                        min_value=8,
                        priority=self.PRIORITY_MEDIUM,
                        reason="Gloves - attack speed for attacks",
                    ))

    def _add_default_filters(self, result: SmartFilterResult) -> None:
        """Add default filters when no archetype is available."""
        # Default to life + elemental resistance
        life_stat = self._get_stat_id("life")
        if life_stat:
            result.filters.append(FilterPriority(
                stat_id=life_stat,
                min_value=60,
                priority=self.PRIORITY_HIGH,
                reason="Default: life always valuable",
            ))

        ele_res = self._get_stat_id("resistances")
        if ele_res:
            result.filters.append(FilterPriority(
                stat_id=ele_res,
                min_value=60,  # ~2x T3 res
                priority=self.PRIORITY_HIGH,
                reason="Default: elemental resistance valuable",
            ))

        result.filter_reasons.append("No archetype: using generic life + res filters")

    def _get_stat_id(self, affix_type: str) -> Optional[str]:
        """Get trade API stat ID for an affix type."""
        mapping = get_stat_id(affix_type)
        if mapping:
            stat_id, _ = mapping
            return stat_id
        return None


def build_smart_filters(
    archetype: Optional[BuildArchetype] = None,
    build_stats: Optional[BuildStats] = None,
    slot: Optional[str] = None,
    max_filters: int = 6,
) -> Tuple[List[Dict[str, Any]], SmartFilterResult]:
    """
    Convenience function to build smart trade filters.

    Args:
        archetype: Build archetype
        build_stats: PoB build stats
        slot: Equipment slot
        max_filters: Maximum filters to include

    Returns:
        (trade_filters, result) where trade_filters is ready for the trade API
    """
    builder = SmartFilterBuilder(archetype, build_stats)
    result = builder.build_filters(slot=slot)
    filters = result.to_trade_filters(max_filters=max_filters)
    return filters, result


# Testing
if __name__ == "__main__":
    from core.build_archetype import detect_archetype

    # Test with sample build stats
    sample_stats = {
        "Life": 5000,
        "EnergyShield": 200,
        "CritChance": 60,
        "CritMultiplier": 400,
        "FireResistOverCap": -10,  # Under cap
        "ColdResistOverCap": 20,
        "LightningResistOverCap": 5,
        "ChaosResist": 20,  # Low chaos
        "Str": 200,
        "Dex": 150,
        "Int": 100,
    }

    build_stats = BuildStats.from_pob_stats(sample_stats)
    archetype = detect_archetype(sample_stats, "Cyclone")

    print("=== Build Archetype ===")
    print(archetype.get_summary())
    print()

    filters, result = build_smart_filters(
        archetype=archetype,
        build_stats=build_stats,
        slot="Boots",
        max_filters=6,
    )

    print("=== Smart Filters ===")
    print(f"Archetype: {result.archetype_summary}")
    print(f"Gaps: {result.gap_summary}")
    print()

    print("Filter reasons:")
    for reason in result.filter_reasons:
        print(f"  - {reason}")
    print()

    print("Trade API filters:")
    for f in filters:
        print(f"  {f}")
