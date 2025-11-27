"""
Upgrade Impact Calculator.

Calculates the real impact of item upgrades on a build by:
1. Extracting stats from item mods
2. Comparing against current gear
3. Applying build scaling to show effective impact
4. Tracking resistance and attribute gaps
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.build_stat_calculator import BuildStats, BuildStatCalculator

logger = logging.getLogger(__name__)


@dataclass
class ItemStats:
    """Extracted stats from an item's mods."""
    # Defense
    flat_life: float = 0.0
    percent_life: float = 0.0
    flat_es: float = 0.0
    percent_es: float = 0.0
    flat_armour: float = 0.0
    percent_armour: float = 0.0
    flat_evasion: float = 0.0
    percent_evasion: float = 0.0

    # Resistances
    fire_res: float = 0.0
    cold_res: float = 0.0
    lightning_res: float = 0.0
    chaos_res: float = 0.0

    # Attributes
    strength: float = 0.0
    dexterity: float = 0.0
    intelligence: float = 0.0

    # Offensive (basic)
    attack_speed: float = 0.0
    cast_speed: float = 0.0
    crit_chance: float = 0.0
    crit_multi: float = 0.0

    # Utility
    movement_speed: float = 0.0

    def total_ele_res(self) -> float:
        """Total elemental resistance."""
        return self.fire_res + self.cold_res + self.lightning_res

    def total_all_res(self) -> float:
        """Total all resistance including chaos."""
        return self.total_ele_res() + self.chaos_res

    def total_attributes(self) -> float:
        """Total attributes."""
        return self.strength + self.dexterity + self.intelligence


@dataclass
class UpgradeImpact:
    """Calculated impact of an upgrade."""
    # Raw deltas
    life_delta: float = 0.0
    es_delta: float = 0.0
    armour_delta: float = 0.0
    evasion_delta: float = 0.0
    fire_res_delta: float = 0.0
    cold_res_delta: float = 0.0
    lightning_res_delta: float = 0.0
    chaos_res_delta: float = 0.0
    strength_delta: float = 0.0
    dexterity_delta: float = 0.0
    intelligence_delta: float = 0.0

    # Effective deltas (after scaling)
    effective_life_delta: float = 0.0
    effective_es_delta: float = 0.0
    effective_armour_delta: float = 0.0

    # Gap coverage
    fire_res_gap_covered: float = 0.0  # % of gap covered
    cold_res_gap_covered: float = 0.0
    lightning_res_gap_covered: float = 0.0
    chaos_res_gap_covered: float = 0.0

    # Summary
    is_upgrade: bool = False
    is_sidegrade: bool = False
    is_downgrade: bool = False
    upgrade_score: float = 0.0  # Positive = upgrade, negative = downgrade

    # Details for display
    improvements: List[str] = field(default_factory=list)
    losses: List[str] = field(default_factory=list)

    def get_summary(self) -> str:
        """Get a human-readable summary of the upgrade."""
        parts = []

        if self.effective_life_delta != 0:
            sign = "+" if self.effective_life_delta > 0 else ""
            parts.append(f"{sign}{int(self.effective_life_delta)} effective life")

        if self.effective_es_delta != 0:
            sign = "+" if self.effective_es_delta > 0 else ""
            parts.append(f"{sign}{int(self.effective_es_delta)} effective ES")

        total_res = (self.fire_res_delta + self.cold_res_delta +
                     self.lightning_res_delta + self.chaos_res_delta)
        if total_res != 0:
            sign = "+" if total_res > 0 else ""
            parts.append(f"{sign}{int(total_res)}% total res")

        total_attr = self.strength_delta + self.dexterity_delta + self.intelligence_delta
        if total_attr != 0:
            sign = "+" if total_attr > 0 else ""
            parts.append(f"{sign}{int(total_attr)} attributes")

        if not parts:
            return "No significant change"

        return ", ".join(parts)


@dataclass
class ResistanceGaps:
    """Tracks resistance gaps to cap."""
    fire_gap: float = 0.0  # How much below cap
    cold_gap: float = 0.0
    lightning_gap: float = 0.0
    chaos_gap: float = 0.0  # Gap to 75% (or build's target)

    def total_ele_gap(self) -> float:
        """Total elemental resistance gap."""
        return self.fire_gap + self.cold_gap + self.lightning_gap

    def has_gaps(self) -> bool:
        """Check if any resistance gaps exist."""
        return (self.fire_gap > 0 or self.cold_gap > 0 or
                self.lightning_gap > 0 or self.chaos_gap > 0)


class ItemStatExtractor:
    """Extracts stats from item mod lists."""

    # Patterns for mod extraction
    # NOTE: Order matters! Compound patterns must come before simple ones
    # because re.search finds partial matches
    PATTERNS = {
        # Life
        "flat_life": r"\+(\d+) to maximum Life",
        "percent_life": r"(\d+)% increased maximum Life",

        # Energy Shield
        "flat_es": r"\+(\d+) to maximum Energy Shield",
        "percent_es": r"(\d+)% increased maximum Energy Shield",

        # Armour
        "flat_armour": r"\+(\d+) to Armour",
        "percent_armour": r"(\d+)% increased Armour",

        # Evasion
        "flat_evasion": r"\+(\d+) to Evasion Rating",
        "percent_evasion": r"(\d+)% increased Evasion Rating",

        # Resistances
        "all_ele_res": r"\+(\d+)%? to all Elemental Resistances",
        "fire_res": r"\+(\d+)%? to Fire Resistance",
        "cold_res": r"\+(\d+)%? to Cold Resistance",
        "lightning_res": r"\+(\d+)%? to Lightning Resistance",
        "chaos_res": r"\+(\d+)%? to Chaos Resistance",

        # Attributes - compound patterns FIRST
        "all_attributes": r"\+(\d+) to all Attributes",
        "str_dex": r"\+(\d+) to Strength and Dexterity",
        "str_int": r"\+(\d+) to Strength and Intelligence",
        "dex_int": r"\+(\d+) to Dexterity and Intelligence",
        "strength": r"\+(\d+) to Strength$",
        "dexterity": r"\+(\d+) to Dexterity$",
        "intelligence": r"\+(\d+) to Intelligence$",

        # Offensive
        "attack_speed": r"(\d+)% increased Attack Speed",
        "cast_speed": r"(\d+)% increased Cast Speed",
        "crit_chance": r"(\d+)% increased (?:Global )?Critical Strike Chance",
        "crit_multi": r"\+(\d+)% to (?:Global )?Critical Strike Multiplier",

        # Utility
        "movement_speed": r"(\d+)% increased Movement Speed",
    }

    def extract(self, mods: List[str]) -> ItemStats:
        """Extract stats from a list of item mods."""
        stats = ItemStats()

        for mod in mods:
            self._extract_mod(mod, stats)

        return stats

    def _extract_mod(self, mod: str, stats: ItemStats) -> None:
        """Extract values from a single mod."""
        for stat_name, pattern in self.PATTERNS.items():
            match = re.search(pattern, mod, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                self._apply_value(stats, stat_name, value)
                return  # Only match once per mod

    def _apply_value(self, stats: ItemStats, stat_name: str, value: float) -> None:
        """Apply an extracted value to the stats object."""
        # Handle compound stats first (before simple direct mappings)
        if stat_name == "all_ele_res":
            # All ele res adds to each
            stats.fire_res += value
            stats.cold_res += value
            stats.lightning_res += value

        elif stat_name == "all_attributes":
            stats.strength += value
            stats.dexterity += value
            stats.intelligence += value

        elif stat_name == "str_dex":
            stats.strength += value
            stats.dexterity += value

        elif stat_name == "str_int":
            stats.strength += value
            stats.intelligence += value

        elif stat_name == "dex_int":
            stats.dexterity += value
            stats.intelligence += value

        else:
            # Direct single-stat mappings
            if hasattr(stats, stat_name):
                setattr(stats, stat_name, getattr(stats, stat_name) + value)


class UpgradeCalculator:
    """
    Calculates upgrade impact between items.

    Takes two items (current and new) and calculates the effective
    impact of switching, considering build scaling and stat gaps.
    """

    def __init__(self, build_stats: Optional[BuildStats] = None):
        """
        Initialize calculator with build stats.

        Args:
            build_stats: BuildStats object with PoB-calculated values
        """
        self.build_stats = build_stats or BuildStats()
        self.extractor = ItemStatExtractor()
        self.stat_calculator = BuildStatCalculator(build_stats)

    def calculate_resistance_gaps(self) -> ResistanceGaps:
        """Calculate current resistance gaps based on build stats."""
        bs = self.build_stats

        # Assume 75% cap for elemental, use overcap to determine gap
        # Negative overcap = gap to cap
        gaps = ResistanceGaps(
            fire_gap=max(0, -bs.fire_overcap),
            cold_gap=max(0, -bs.cold_overcap),
            lightning_gap=max(0, -bs.lightning_overcap),
            chaos_gap=max(0, 75 - bs.chaos_res),  # Chaos cap at 75
        )

        return gaps

    def calculate_upgrade(
        self,
        new_item_mods: List[str],
        current_item_mods: Optional[List[str]] = None,
    ) -> UpgradeImpact:
        """
        Calculate the upgrade impact of replacing an item.

        Args:
            new_item_mods: Mods on the potential new item
            current_item_mods: Mods on current equipped item (None = empty slot)

        Returns:
            UpgradeImpact with calculated deltas and summary
        """
        # Extract stats from both items
        new_stats = self.extractor.extract(new_item_mods)
        current_stats = self.extractor.extract(current_item_mods or [])

        # Calculate raw deltas
        impact = UpgradeImpact()
        impact.life_delta = new_stats.flat_life - current_stats.flat_life
        impact.es_delta = new_stats.flat_es - current_stats.flat_es
        impact.armour_delta = new_stats.flat_armour - current_stats.flat_armour
        impact.evasion_delta = new_stats.flat_evasion - current_stats.flat_evasion

        impact.fire_res_delta = new_stats.fire_res - current_stats.fire_res
        impact.cold_res_delta = new_stats.cold_res - current_stats.cold_res
        impact.lightning_res_delta = new_stats.lightning_res - current_stats.lightning_res
        impact.chaos_res_delta = new_stats.chaos_res - current_stats.chaos_res

        impact.strength_delta = new_stats.strength - current_stats.strength
        impact.dexterity_delta = new_stats.dexterity - current_stats.dexterity
        impact.intelligence_delta = new_stats.intelligence - current_stats.intelligence

        # Apply scaling for effective values
        bs = self.build_stats
        life_mult = 1 + (bs.life_inc / 100)
        es_mult = 1 + (bs.es_inc / 100)
        armour_mult = 1 + (bs.armour_inc / 100)

        impact.effective_life_delta = impact.life_delta * life_mult
        # Add life from strength (0.5 life per str, scaled)
        impact.effective_life_delta += (impact.strength_delta / 2) * life_mult

        impact.effective_es_delta = impact.es_delta * es_mult
        impact.effective_armour_delta = impact.armour_delta * armour_mult

        # Calculate gap coverage
        gaps = self.calculate_resistance_gaps()
        if gaps.fire_gap > 0 and impact.fire_res_delta > 0:
            impact.fire_res_gap_covered = min(100, (impact.fire_res_delta / gaps.fire_gap) * 100)
        if gaps.cold_gap > 0 and impact.cold_res_delta > 0:
            impact.cold_res_gap_covered = min(100, (impact.cold_res_delta / gaps.cold_gap) * 100)
        if gaps.lightning_gap > 0 and impact.lightning_res_delta > 0:
            impact.lightning_res_gap_covered = min(100, (impact.lightning_res_delta / gaps.lightning_gap) * 100)
        if gaps.chaos_gap > 0 and impact.chaos_res_delta > 0:
            impact.chaos_res_gap_covered = min(100, (impact.chaos_res_delta / gaps.chaos_gap) * 100)

        # Build improvements and losses lists
        self._categorize_changes(impact, new_stats, current_stats, gaps)

        # Calculate overall upgrade score
        impact.upgrade_score = self._calculate_upgrade_score(impact, gaps)

        # Determine upgrade/sidegrade/downgrade
        if impact.upgrade_score > 10:
            impact.is_upgrade = True
        elif impact.upgrade_score < -10:
            impact.is_downgrade = True
        else:
            impact.is_sidegrade = True

        return impact

    def _categorize_changes(
        self,
        impact: UpgradeImpact,
        new_stats: ItemStats,
        current_stats: ItemStats,
        gaps: ResistanceGaps
    ) -> None:
        """Categorize changes into improvements and losses."""
        improvements = []
        losses = []

        # Life
        if impact.effective_life_delta > 5:
            improvements.append(f"+{int(impact.effective_life_delta)} effective life")
        elif impact.effective_life_delta < -5:
            losses.append(f"{int(impact.effective_life_delta)} effective life")

        # ES
        if impact.effective_es_delta > 5:
            improvements.append(f"+{int(impact.effective_es_delta)} effective ES")
        elif impact.effective_es_delta < -5:
            losses.append(f"{int(impact.effective_es_delta)} effective ES")

        # Resistances with gap context
        for res_name, delta, gap, gap_covered in [
            ("fire", impact.fire_res_delta, gaps.fire_gap, impact.fire_res_gap_covered),
            ("cold", impact.cold_res_delta, gaps.cold_gap, impact.cold_res_gap_covered),
            ("lightning", impact.lightning_res_delta, gaps.lightning_gap, impact.lightning_res_gap_covered),
            ("chaos", impact.chaos_res_delta, gaps.chaos_gap, impact.chaos_res_gap_covered),
        ]:
            if delta > 0:
                msg = f"+{int(delta)}% {res_name} res"
                if gap_covered > 0:
                    msg += f" (covers {int(gap_covered)}% of gap)"
                improvements.append(msg)
            elif delta < 0:
                losses.append(f"{int(delta)}% {res_name} res")

        # Attributes
        if impact.strength_delta > 5:
            improvements.append(f"+{int(impact.strength_delta)} strength")
        elif impact.strength_delta < -5:
            losses.append(f"{int(impact.strength_delta)} strength")

        if impact.dexterity_delta > 5:
            improvements.append(f"+{int(impact.dexterity_delta)} dexterity")
        elif impact.dexterity_delta < -5:
            losses.append(f"{int(impact.dexterity_delta)} dexterity")

        if impact.intelligence_delta > 5:
            improvements.append(f"+{int(impact.intelligence_delta)} intelligence")
        elif impact.intelligence_delta < -5:
            losses.append(f"{int(impact.intelligence_delta)} intelligence")

        impact.improvements = improvements
        impact.losses = losses

    def _calculate_upgrade_score(
        self,
        impact: UpgradeImpact,
        gaps: ResistanceGaps
    ) -> float:
        """
        Calculate an overall upgrade score.

        Positive = upgrade, negative = downgrade.
        """
        score = 0.0

        # Life is always valuable
        score += impact.effective_life_delta * 0.5

        # ES valuable for ES builds
        if self.build_stats.total_es > 500:
            score += impact.effective_es_delta * 0.5

        # Resistances - more valuable when there are gaps
        res_weight = 2.0 if gaps.has_gaps() else 0.5

        # Weight uncapped res higher
        if gaps.fire_gap > 0:
            score += impact.fire_res_delta * 3.0  # Very valuable if uncapped
        else:
            score += impact.fire_res_delta * res_weight

        if gaps.cold_gap > 0:
            score += impact.cold_res_delta * 3.0
        else:
            score += impact.cold_res_delta * res_weight

        if gaps.lightning_gap > 0:
            score += impact.lightning_res_delta * 3.0
        else:
            score += impact.lightning_res_delta * res_weight

        # Chaos res always has some value
        score += impact.chaos_res_delta * 1.5

        # Attributes
        score += impact.strength_delta * 0.3
        score += impact.dexterity_delta * 0.2
        score += impact.intelligence_delta * 0.2

        return score

    def compare_items(
        self,
        new_item_mods: List[str],
        current_item_mods: List[str],
    ) -> Dict[str, Any]:
        """
        Compare two items and return detailed comparison.

        Args:
            new_item_mods: Mods on potential new item
            current_item_mods: Mods on current item

        Returns:
            Dict with comparison details suitable for UI display
        """
        impact = self.calculate_upgrade(new_item_mods, current_item_mods)
        gaps = self.calculate_resistance_gaps()

        return {
            "impact": impact,
            "gaps": gaps,
            "summary": impact.get_summary(),
            "is_upgrade": impact.is_upgrade,
            "is_sidegrade": impact.is_sidegrade,
            "is_downgrade": impact.is_downgrade,
            "upgrade_score": impact.upgrade_score,
            "improvements": impact.improvements,
            "losses": impact.losses,
            "effective_life_change": impact.effective_life_delta,
            "effective_es_change": impact.effective_es_delta,
            "total_res_change": (
                impact.fire_res_delta + impact.cold_res_delta +
                impact.lightning_res_delta + impact.chaos_res_delta
            ),
        }


# Testing
if __name__ == "__main__":
    # Test with sample build stats
    sample_stats = {
        "Spec:LifeInc": 158.0,
        "Life": 5637.0,
        "Spec:EnergyShieldInc": 22.0,
        "EnergyShield": 113.0,
        "FireResist": 75.0,
        "FireResistOverCap": 10.0,
        "ColdResist": 75.0,
        "ColdResistOverCap": -5.0,  # 5% under cap
        "LightningResist": 75.0,
        "LightningResistOverCap": 20.0,
        "ChaosResist": 30.0,
        "Str": 200.0,
        "Dex": 100.0,
        "Int": 100.0,
    }

    build_stats = BuildStats.from_pob_stats(sample_stats)
    calculator = UpgradeCalculator(build_stats)

    print("=== Resistance Gaps ===")
    gaps = calculator.calculate_resistance_gaps()
    print(f"Fire gap: {gaps.fire_gap}%")
    print(f"Cold gap: {gaps.cold_gap}%")
    print(f"Lightning gap: {gaps.lightning_gap}%")
    print(f"Chaos gap: {gaps.chaos_gap}%")
    print()

    # Test upgrade calculation
    current_mods = [
        "+65 to maximum Life",
        "+30% to Fire Resistance",
        "+25% to Cold Resistance",
    ]

    new_mods = [
        "+80 to maximum Life",
        "+40% to Fire Resistance",
        "+35% to Cold Resistance",
        "+20% to Chaos Resistance",
    ]

    print("=== Upgrade Comparison ===")
    print("Current item:", current_mods)
    print("New item:", new_mods)
    print()

    comparison = calculator.compare_items(new_mods, current_mods)
    print(f"Summary: {comparison['summary']}")
    print(f"Is upgrade: {comparison['is_upgrade']}")
    print(f"Score: {comparison['upgrade_score']:.1f}")
    print()
    print("Improvements:", comparison['improvements'])
    print("Losses:", comparison['losses'])
