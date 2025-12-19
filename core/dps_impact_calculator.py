"""
DPS Impact Calculator.

Estimates the DPS impact of item mods based on PoB build stats and archetype.
Uses build-specific multipliers to show how much an item affects damage output.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DamageType(Enum):
    """Primary damage type for a build."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"
    ELEMENTAL = "elemental"  # Mixed elemental
    MINION = "minion"
    DOT = "dot"  # Damage over time
    UNKNOWN = "unknown"


@dataclass
class DPSStats:
    """Container for DPS-related build stats from PoB."""
    # Main DPS values
    combined_dps: float = 0.0
    total_dps: float = 0.0

    # DPS by damage type
    physical_dps: float = 0.0
    fire_dps: float = 0.0
    cold_dps: float = 0.0
    lightning_dps: float = 0.0
    chaos_dps: float = 0.0

    # Special DPS types
    minion_dps: float = 0.0
    totem_dps: float = 0.0
    trap_dps: float = 0.0
    mine_dps: float = 0.0

    # DoT DPS
    bleed_dps: float = 0.0
    ignite_dps: float = 0.0
    poison_dps: float = 0.0
    total_dot_dps: float = 0.0

    # Crit stats
    crit_chance: float = 0.0
    crit_multi: float = 0.0

    # Scaling stats (% increased from tree/gear)
    increased_damage: float = 0.0
    increased_physical: float = 0.0
    increased_elemental: float = 0.0
    increased_spell: float = 0.0
    increased_attack: float = 0.0

    # Speed
    attack_speed: float = 0.0
    cast_speed: float = 0.0

    # Derived
    primary_damage_type: DamageType = DamageType.UNKNOWN
    is_crit_build: bool = False
    is_dot_build: bool = False
    is_minion_build: bool = False
    is_spell_build: bool = False
    is_attack_build: bool = False

    @classmethod
    def from_pob_stats(cls, stats: Dict[str, float]) -> "DPSStats":
        """Create DPSStats from PoB PlayerStat dictionary."""
        # Extract DPS values
        phys_dps = stats.get("PhysicalDPS", stats.get("TotalPhysicalDPS", 0))
        fire_dps = stats.get("FireDPS", stats.get("TotalFireDPS", 0))
        cold_dps = stats.get("ColdDPS", stats.get("TotalColdDPS", 0))
        lightning_dps = stats.get("LightningDPS", stats.get("TotalLightningDPS", 0))
        chaos_dps = stats.get("ChaosDPS", stats.get("TotalChaosDPS", 0))
        minion_dps = stats.get("MinionDPS", stats.get("TotalMinionDPS", 0))

        total_dps = stats.get("TotalDPS", phys_dps + fire_dps + cold_dps + lightning_dps + chaos_dps)
        combined_dps = stats.get("CombinedDPS", total_dps)

        # DoT
        bleed_dps = stats.get("BleedDPS", 0)
        ignite_dps = stats.get("IgniteDPS", 0)
        poison_dps = stats.get("PoisonDPS", 0)
        total_dot_dps = stats.get("TotalDotDPS", bleed_dps + ignite_dps + poison_dps)

        # Crit
        crit_chance = stats.get("CritChance", stats.get("MeleeCritChance", stats.get("SpellCritChance", 0)))
        crit_multi = stats.get("CritMultiplier", stats.get("CritDamage", 150))

        # Speed (for future per-hit damage calculations)
        attack_speed = stats.get("Speed", stats.get("AttackRate", 1.0))
        cast_speed = stats.get("CastSpeed", stats.get("CastRate", 1.0))

        # Determine primary damage type
        total_ele = fire_dps + cold_dps + lightning_dps
        primary_type = DamageType.UNKNOWN

        if minion_dps > total_dps * 0.5:
            primary_type = DamageType.MINION
        elif total_dot_dps > total_dps * 0.5 or (total_dps == 0 and total_dot_dps > 0):
            primary_type = DamageType.DOT
        elif total_dps > 0:
            if total_ele > total_dps * 0.6:
                # Find dominant element
                max_ele = max(fire_dps, cold_dps, lightning_dps)
                if max_ele == fire_dps:
                    primary_type = DamageType.FIRE
                elif max_ele == cold_dps:
                    primary_type = DamageType.COLD
                elif max_ele == lightning_dps:
                    primary_type = DamageType.LIGHTNING
                else:
                    primary_type = DamageType.ELEMENTAL
            elif phys_dps > total_dps * 0.5:
                primary_type = DamageType.PHYSICAL
            elif chaos_dps > total_dps * 0.5:
                primary_type = DamageType.CHAOS

        # Build flags
        is_crit = crit_chance > 40 or (crit_chance > 25 and crit_multi > 300)
        is_dot = total_dot_dps > 0 and (total_dps == 0 or total_dot_dps > total_dps * 0.3)
        is_minion = minion_dps > total_dps * 0.5

        # Attack vs spell - infer from skill type naming in stats
        is_spell = stats.get("SpellDPS", 0) > 0 or "Spell" in str(stats.get("MainSkill", ""))
        is_attack = stats.get("AttackDPS", 0) > 0 or not is_spell

        return cls(
            combined_dps=combined_dps,
            total_dps=total_dps,
            physical_dps=phys_dps,
            fire_dps=fire_dps,
            cold_dps=cold_dps,
            lightning_dps=lightning_dps,
            chaos_dps=chaos_dps,
            minion_dps=minion_dps,
            totem_dps=stats.get("TotemDPS", 0),
            trap_dps=stats.get("TrapDPS", 0),
            mine_dps=stats.get("MineDPS", 0),
            bleed_dps=bleed_dps,
            ignite_dps=ignite_dps,
            poison_dps=poison_dps,
            total_dot_dps=total_dot_dps,
            crit_chance=crit_chance,
            crit_multi=crit_multi,
            attack_speed=attack_speed,
            cast_speed=cast_speed,
            primary_damage_type=primary_type,
            is_crit_build=is_crit,
            is_dot_build=is_dot,
            is_minion_build=is_minion,
            is_spell_build=is_spell,
            is_attack_build=is_attack,
        )


@dataclass
class DPSModImpact:
    """Represents the DPS impact of an item mod."""
    mod_text: str
    mod_category: str  # "damage", "crit", "speed", "multiplier"
    raw_value: float
    estimated_dps_change: float  # Estimated DPS change (absolute)
    estimated_dps_percent: float  # Estimated % DPS change
    relevance: str  # "high", "medium", "low", "none"
    explanation: str


@dataclass
class DPSImpactResult:
    """Complete DPS impact analysis for an item."""
    total_dps_change: float = 0.0
    total_dps_percent: float = 0.0
    mod_impacts: List[DPSModImpact] = field(default_factory=list)
    summary: str = ""
    build_info: str = ""


class DPSImpactCalculator:
    """
    Calculates estimated DPS impact of items based on build stats.

    This provides rough estimates based on common damage scaling patterns.
    For precise DPS calculations, use Path of Building.
    """

    # Damage mod patterns with their categories
    DAMAGE_PATTERNS = {
        # % Increased Damage
        "phys_dmg_pct": (r"(\d+)%? increased Physical Damage", "physical_damage"),
        "ele_dmg_pct": (r"(\d+)%? increased Elemental Damage", "elemental_damage"),
        "fire_dmg_pct": (r"(\d+)%? increased Fire Damage", "fire_damage"),
        "cold_dmg_pct": (r"(\d+)%? increased Cold Damage", "cold_damage"),
        "lightning_dmg_pct": (r"(\d+)%? increased Lightning Damage", "lightning_damage"),
        "chaos_dmg_pct": (r"(\d+)%? increased Chaos Damage", "chaos_damage"),
        "spell_dmg_pct": (r"(\d+)%? increased Spell Damage", "spell_damage"),
        "minion_dmg_pct": (r"(\d+)%? increased Minion Damage", "minion_damage"),
        "dot_pct": (r"(\d+)%? increased Damage over Time", "dot_damage"),

        # Flat Added Damage (attacks)
        "added_phys": (r"Adds (\d+) to \d+ Physical Damage", "added_physical"),
        "added_fire": (r"Adds (\d+) to \d+ Fire Damage", "added_fire"),
        "added_cold": (r"Adds (\d+) to \d+ Cold Damage", "added_cold"),
        "added_lightning": (r"Adds (\d+) to \d+ Lightning Damage", "added_lightning"),
        "added_chaos": (r"Adds (\d+) to \d+ Chaos Damage", "added_chaos"),

        # Critical Strike
        "crit_chance": (r"(\d+)%? increased (?:Global )?Critical Strike Chance", "crit_chance"),
        "crit_multi": (r"\+(\d+)%? to (?:Global )?Critical Strike Multiplier", "crit_multi"),
        "crit_chance_spell": (r"(\d+)%? increased Critical Strike Chance for Spells", "crit_chance_spell"),

        # Attack/Cast Speed
        "attack_speed": (r"(\d+)%? increased Attack Speed", "attack_speed"),
        "cast_speed": (r"(\d+)%? increased Cast Speed", "cast_speed"),

        # Global damage multipliers
        "dmg_with_hits": (r"(\d+)%? increased Damage with Hits", "damage_hits"),
        "more_dmg": (r"(\d+)%? more Damage", "more_damage"),

        # Weapon-specific
        "weapon_ele": (r"(\d+)%? increased Elemental Damage with Attack Skills", "weapon_elemental"),
        "melee_dmg": (r"(\d+)%? increased Melee Damage", "melee_damage"),
        "projectile_dmg": (r"(\d+)%? increased Projectile Damage", "projectile_damage"),
    }

    def __init__(self, dps_stats: Optional[DPSStats] = None):
        """
        Initialize calculator with DPS stats.

        Args:
            dps_stats: DPSStats object with build DPS information
        """
        self.dps_stats = dps_stats or DPSStats()

    def set_stats(self, dps_stats: DPSStats) -> None:
        """Update the DPS stats."""
        self.dps_stats = dps_stats

    def calculate_impact(self, mods: List[str]) -> DPSImpactResult:
        """
        Calculate DPS impact for a list of item mods.

        Args:
            mods: List of item mod strings

        Returns:
            DPSImpactResult with breakdown and totals
        """
        result = DPSImpactResult()
        result.build_info = self._get_build_info()

        if self.dps_stats.combined_dps <= 0:
            result.summary = "No DPS data available from build"
            return result

        total_percent_change = 0.0

        for mod in mods:
            impact = self._calculate_mod_impact(mod)
            if impact:
                result.mod_impacts.append(impact)
                total_percent_change += impact.estimated_dps_percent

        # Calculate total DPS change
        result.total_dps_percent = total_percent_change
        result.total_dps_change = self.dps_stats.combined_dps * (total_percent_change / 100)
        result.summary = self._generate_summary(result)

        return result

    def _calculate_mod_impact(self, mod: str) -> Optional[DPSModImpact]:
        """Calculate DPS impact for a single mod."""
        for pattern_name, (pattern, category) in self.DAMAGE_PATTERNS.items():
            match = re.search(pattern, mod, re.IGNORECASE)
            if match:
                raw_value = float(match.group(1))
                dps_percent, relevance, explanation = self._estimate_dps_percent(
                    category, raw_value
                )

                dps_change = self.dps_stats.combined_dps * (dps_percent / 100)

                return DPSModImpact(
                    mod_text=mod,
                    mod_category=category,
                    raw_value=raw_value,
                    estimated_dps_change=dps_change,
                    estimated_dps_percent=dps_percent,
                    relevance=relevance,
                    explanation=explanation,
                )

        return None

    def _estimate_dps_percent(
        self,
        category: str,
        raw_value: float
    ) -> Tuple[float, str, str]:
        """
        Estimate DPS percentage change from a mod.

        Returns: (percent_change, relevance, explanation)
        """
        stats = self.dps_stats
        base_dps = stats.combined_dps

        # Base assumption: builds typically have 300-500% increased damage already
        # So each additional 1% increased damage is roughly 0.2-0.3% more DPS
        # This is a simplification - actual impact varies greatly by build

        # Default diminishing factor for % increased damage
        assumed_inc_damage = 400  # Assume ~400% increased damage baseline
        inc_multiplier = 100 / (100 + assumed_inc_damage)  # ~0.2

        # Category-specific calculations
        if category == "physical_damage":
            if stats.primary_damage_type == DamageType.PHYSICAL:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% phys dmg = ~{percent:.1f}% DPS (phys build)"
            else:
                phys_ratio = stats.physical_dps / base_dps if base_dps > 0 else 0
                percent = raw_value * inc_multiplier * phys_ratio
                relevance = "medium" if phys_ratio > 0.2 else "low"
                return percent, relevance, f"+{raw_value}% phys dmg ({phys_ratio*100:.0f}% phys) = ~{percent:.1f}% DPS"

        elif category == "fire_damage":
            if stats.primary_damage_type == DamageType.FIRE:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% fire dmg = ~{percent:.1f}% DPS (fire build)"
            fire_ratio = stats.fire_dps / base_dps if base_dps > 0 else 0
            percent = raw_value * inc_multiplier * fire_ratio
            relevance = "medium" if fire_ratio > 0.2 else "low"
            return percent, relevance, f"+{raw_value}% fire dmg ({fire_ratio*100:.0f}% fire) = ~{percent:.1f}% DPS"

        elif category == "cold_damage":
            if stats.primary_damage_type == DamageType.COLD:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% cold dmg = ~{percent:.1f}% DPS (cold build)"
            cold_ratio = stats.cold_dps / base_dps if base_dps > 0 else 0
            percent = raw_value * inc_multiplier * cold_ratio
            relevance = "medium" if cold_ratio > 0.2 else "low"
            return percent, relevance, f"+{raw_value}% cold dmg ({cold_ratio*100:.0f}% cold) = ~{percent:.1f}% DPS"

        elif category == "lightning_damage":
            if stats.primary_damage_type == DamageType.LIGHTNING:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% light dmg = ~{percent:.1f}% DPS (lightning build)"
            light_ratio = stats.lightning_dps / base_dps if base_dps > 0 else 0
            percent = raw_value * inc_multiplier * light_ratio
            relevance = "medium" if light_ratio > 0.2 else "low"
            return percent, relevance, f"+{raw_value}% light dmg ({light_ratio*100:.0f}% lightning) = ~{percent:.1f}% DPS"

        elif category == "chaos_damage":
            if stats.primary_damage_type == DamageType.CHAOS:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% chaos dmg = ~{percent:.1f}% DPS (chaos build)"
            chaos_ratio = stats.chaos_dps / base_dps if base_dps > 0 else 0
            percent = raw_value * inc_multiplier * chaos_ratio
            relevance = "medium" if chaos_ratio > 0.2 else "low"
            return percent, relevance, f"+{raw_value}% chaos dmg ({chaos_ratio*100:.0f}% chaos) = ~{percent:.1f}% DPS"

        elif category == "elemental_damage":
            ele_ratio = (stats.fire_dps + stats.cold_dps + stats.lightning_dps) / base_dps if base_dps > 0 else 0
            percent = raw_value * inc_multiplier * ele_ratio
            relevance = "high" if ele_ratio > 0.6 else ("medium" if ele_ratio > 0.2 else "low")
            return percent, relevance, f"+{raw_value}% ele dmg ({ele_ratio*100:.0f}% ele) = ~{percent:.1f}% DPS"

        elif category == "spell_damage":
            if stats.is_spell_build:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% spell dmg = ~{percent:.1f}% DPS (spell build)"
            return 0, "none", f"+{raw_value}% spell dmg (not spell build)"

        elif category == "minion_damage":
            if stats.is_minion_build:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% minion dmg = ~{percent:.1f}% DPS (minion build)"
            return 0, "none", f"+{raw_value}% minion dmg (not minion build)"

        elif category == "dot_damage":
            if stats.is_dot_build:
                percent = raw_value * inc_multiplier
                return percent, "high", f"+{raw_value}% DoT = ~{percent:.1f}% DPS (DoT build)"
            dot_ratio = stats.total_dot_dps / base_dps if base_dps > 0 else 0
            percent = raw_value * inc_multiplier * dot_ratio
            relevance = "medium" if dot_ratio > 0.2 else "low"
            return percent, relevance, f"+{raw_value}% DoT ({dot_ratio*100:.0f}% DoT) = ~{percent:.1f}% DPS"

        elif category == "crit_chance":
            if stats.is_crit_build:
                # Crit builds: each 1% crit chance is roughly 0.5-1% more DPS
                crit_effectiveness = min(1.0, (100 - stats.crit_chance) / 100)
                percent = raw_value * 0.5 * crit_effectiveness
                return percent, "high", f"+{raw_value}% crit chance = ~{percent:.1f}% DPS (crit build)"
            return raw_value * 0.1, "low", f"+{raw_value}% crit chance = ~{raw_value*0.1:.1f}% DPS (non-crit)"

        elif category == "crit_multi":
            if stats.is_crit_build:
                # Assume 50% effective crit rate for crit builds
                eff_crit = stats.crit_chance / 100
                # Each 1% crit multi with 50% crit = 0.5% more DPS
                percent = raw_value * eff_crit * 0.5
                return percent, "high", f"+{raw_value}% crit multi = ~{percent:.1f}% DPS ({stats.crit_chance:.0f}% crit)"
            return raw_value * 0.05, "low", f"+{raw_value}% crit multi = ~{raw_value*0.05:.1f}% DPS (non-crit)"

        elif category == "attack_speed":
            if stats.is_attack_build:
                # Attack speed is roughly linear for attack builds
                percent = raw_value * 0.7  # Diminished by existing speed
                return percent, "high", f"+{raw_value}% attack speed = ~{percent:.1f}% DPS (attack build)"
            return 0, "none", f"+{raw_value}% attack speed (not attack build)"

        elif category == "cast_speed":
            if stats.is_spell_build and not stats.is_dot_build:
                percent = raw_value * 0.7
                return percent, "high", f"+{raw_value}% cast speed = ~{percent:.1f}% DPS (spell build)"
            return 0, "low", f"+{raw_value}% cast speed (not relevant)"

        elif category == "more_damage":
            # "More" damage is multiplicative, very powerful
            percent = raw_value
            return percent, "high", f"+{raw_value}% MORE damage = ~{percent:.1f}% DPS"

        elif category in ("added_physical", "added_fire", "added_cold", "added_lightning", "added_chaos"):
            if stats.is_attack_build:
                # Flat damage depends on attack speed and conversion
                # Rough estimate: 10 flat damage = ~1% DPS for most builds
                percent = raw_value / 10
                return percent, "medium", f"+{raw_value} flat dmg = ~{percent:.1f}% DPS"
            return raw_value / 20, "low", f"+{raw_value} flat dmg = ~{raw_value/20:.1f}% DPS (not attack)"

        # Default for unhandled categories
        percent = raw_value * inc_multiplier * 0.5
        return percent, "medium", f"+{raw_value}% {category} = ~{percent:.1f}% DPS (estimated)"

    def _get_build_info(self) -> str:
        """Get build info string."""
        stats = self.dps_stats
        parts = []

        if stats.combined_dps > 0:
            if stats.combined_dps >= 1_000_000:
                parts.append(f"DPS: {stats.combined_dps/1_000_000:.2f}M")
            elif stats.combined_dps >= 1_000:
                parts.append(f"DPS: {stats.combined_dps/1_000:.1f}K")
            else:
                parts.append(f"DPS: {int(stats.combined_dps)}")

        if stats.primary_damage_type != DamageType.UNKNOWN:
            parts.append(f"Type: {stats.primary_damage_type.value.title()}")

        flags = []
        if stats.is_crit_build:
            flags.append("Crit")
        if stats.is_dot_build:
            flags.append("DoT")
        if stats.is_minion_build:
            flags.append("Minion")
        if stats.is_spell_build:
            flags.append("Spell")
        elif stats.is_attack_build:
            flags.append("Attack")

        if flags:
            parts.append(" | ".join(flags))

        return " | ".join(parts) if parts else "No build data"

    def _generate_summary(self, result: DPSImpactResult) -> str:
        """Generate summary text for the DPS impact."""
        if not result.mod_impacts:
            return "No offensive mods detected"

        _high_impacts = [m for m in result.mod_impacts if m.relevance == "high"]  # Reserved for future summary
        total_percent = result.total_dps_percent

        if total_percent >= 5:
            verdict = "Significant DPS upgrade"
        elif total_percent >= 2:
            verdict = "Moderate DPS increase"
        elif total_percent >= 0.5:
            verdict = "Minor DPS increase"
        elif total_percent > 0:
            verdict = "Negligible DPS impact"
        else:
            verdict = "No DPS impact"

        dps_change = result.total_dps_change
        if abs(dps_change) >= 1_000_000:
            dps_str = f"{dps_change/1_000_000:+.2f}M"
        elif abs(dps_change) >= 1_000:
            dps_str = f"{dps_change/1_000:+.1f}K"
        else:
            dps_str = f"{dps_change:+.0f}"

        return f"{verdict}: {dps_str} DPS ({total_percent:+.1f}%)"


def get_dps_calculator() -> DPSImpactCalculator:
    """Get a default DPS impact calculator instance."""
    return DPSImpactCalculator()


# Testing
if __name__ == "__main__":
    # Test with sample PoB stats (fire spell build)
    sample_stats = {
        "CombinedDPS": 2_500_000,
        "TotalDPS": 2_500_000,
        "FireDPS": 2_200_000,
        "ColdDPS": 100_000,
        "LightningDPS": 100_000,
        "PhysicalDPS": 100_000,
        "CritChance": 65.0,
        "CritMultiplier": 450.0,
        "SpellDPS": 2_500_000,
    }

    dps_stats = DPSStats.from_pob_stats(sample_stats)
    calculator = DPSImpactCalculator(dps_stats)

    print("=== Build Info ===")
    print(f"Primary: {dps_stats.primary_damage_type.value}")
    print(f"Crit: {dps_stats.is_crit_build}, Spell: {dps_stats.is_spell_build}")
    print()

    test_mods = [
        "+35% increased Fire Damage",
        "+25% increased Spell Damage",
        "+40% to Global Critical Strike Multiplier",
        "+15% increased Cast Speed",
        "+20% increased Elemental Damage",
        "Adds 15 to 30 Fire Damage",
    ]

    print("=== DPS Impact ===")
    result = calculator.calculate_impact(test_mods)
    print(f"Build: {result.build_info}")
    print(f"Summary: {result.summary}")
    print()

    for impact in result.mod_impacts:
        print(f"{impact.mod_text}")
        print(f"  [{impact.relevance.upper()}] {impact.explanation}")
        print()
