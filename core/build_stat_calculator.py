"""
Build Stat Calculator.

Calculates effective item mod values based on PoB build stats.
For example, +80 flat life with 158% increased life = 206 effective life.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EffectiveModValue:
    """Represents an item mod with its effective value based on build stats."""
    mod_text: str  # Original mod text
    mod_type: str  # Category: "life", "es", "armour", "resistance", "attribute", "damage", etc.
    raw_value: float  # Raw value from the mod
    effective_value: float  # Value after applying build multipliers
    multiplier: float  # The multiplier applied (1.0 = no change)
    explanation: str  # Human-readable explanation


@dataclass
class BuildStats:
    """Container for relevant build stats from PoB."""
    # Defensive scaling
    life_inc: float = 0.0  # Spec:LifeInc - % increased max life
    es_inc: float = 0.0  # Spec:EnergyShieldInc - % increased ES
    armour_inc: float = 0.0  # Spec:ArmourInc - % increased armour
    evasion_inc: float = 0.0  # Spec:EvasionInc - % increased evasion

    # Current totals
    total_life: float = 0.0
    total_es: float = 0.0
    total_armour: float = 0.0
    total_evasion: float = 0.0

    # Resistances (current values and overcap)
    fire_res: float = 0.0
    fire_overcap: float = 0.0
    cold_res: float = 0.0
    cold_overcap: float = 0.0
    lightning_res: float = 0.0
    lightning_overcap: float = 0.0
    chaos_res: float = 0.0
    chaos_overcap: float = 0.0

    # Attributes
    strength: float = 0.0
    dexterity: float = 0.0
    intelligence: float = 0.0

    # Other useful stats
    combined_dps: float = 0.0
    total_ehp: float = 0.0

    @classmethod
    def from_pob_stats(cls, stats: Dict[str, float]) -> "BuildStats":
        """Create BuildStats from PoB PlayerStat dictionary."""
        return cls(
            # Scaling percentages
            life_inc=stats.get("Spec:LifeInc", 0.0),
            es_inc=stats.get("Spec:EnergyShieldInc", 0.0),
            armour_inc=stats.get("Spec:ArmourInc", 0.0),
            evasion_inc=stats.get("Spec:EvasionInc", 0.0),

            # Totals
            total_life=stats.get("Life", 0.0),
            total_es=stats.get("EnergyShield", 0.0),
            total_armour=stats.get("Armour", 0.0),
            total_evasion=stats.get("Evasion", 0.0),

            # Resistances
            fire_res=stats.get("FireResist", 0.0),
            fire_overcap=stats.get("FireResistOverCap", 0.0),
            cold_res=stats.get("ColdResist", 0.0),
            cold_overcap=stats.get("ColdResistOverCap", 0.0),
            lightning_res=stats.get("LightningResist", 0.0),
            lightning_overcap=stats.get("LightningResistOverCap", 0.0),
            chaos_res=stats.get("ChaosResist", 0.0),
            chaos_overcap=stats.get("ChaosResistOverCap", 0.0),

            # Attributes
            strength=stats.get("Str", 0.0),
            dexterity=stats.get("Dex", 0.0),
            intelligence=stats.get("Int", 0.0),

            # Other
            combined_dps=stats.get("CombinedDPS", 0.0),
            total_ehp=stats.get("TotalEHP", 0.0),
        )

    def get_summary(self) -> Dict[str, str]:
        """Get a summary dict for display."""
        return {
            "Life": f"{int(self.total_life)} (+{int(self.life_inc)}%)",
            "ES": f"{int(self.total_es)} (+{int(self.es_inc)}%)" if self.total_es > 0 else None,
            "Armour": f"{int(self.total_armour)} (+{int(self.armour_inc)}%)" if self.total_armour > 0 else None,
            "Fire Res": f"{int(self.fire_res)}% (+{int(self.fire_overcap)}% overcap)",
            "Cold Res": f"{int(self.cold_res)}% (+{int(self.cold_overcap)}% overcap)",
            "Lightning Res": f"{int(self.lightning_res)}% (+{int(self.lightning_overcap)}% overcap)",
            "Chaos Res": f"{int(self.chaos_res)}%",
            "Str/Dex/Int": f"{int(self.strength)}/{int(self.dexterity)}/{int(self.intelligence)}",
        }


class BuildStatCalculator:
    """
    Calculates effective item mod values based on build stats.

    Takes item mod text and applies build multipliers to show
    the actual impact of mods on the character.
    """

    # Patterns for parsing item mods
    MOD_PATTERNS = {
        # Life mods
        "flat_life": (r"\+(\d+) to maximum Life", "life"),
        "percent_life": (r"(\d+)% increased maximum Life", "life_percent"),

        # Energy Shield mods
        "flat_es": (r"\+(\d+) to maximum Energy Shield", "es"),
        "percent_es": (r"(\d+)% increased maximum Energy Shield", "es_percent"),

        # Armour/Evasion
        "flat_armour": (r"\+(\d+) to Armour", "armour"),
        "percent_armour": (r"(\d+)% increased Armour", "armour_percent"),
        "flat_evasion": (r"\+(\d+) to Evasion Rating", "evasion"),
        "percent_evasion": (r"(\d+)% increased Evasion Rating", "evasion_percent"),

        # Resistances
        "fire_res": (r"\+(\d+)%? to Fire Resistance", "fire_res"),
        "cold_res": (r"\+(\d+)%? to Cold Resistance", "cold_res"),
        "lightning_res": (r"\+(\d+)%? to Lightning Resistance", "lightning_res"),
        "chaos_res": (r"\+(\d+)%? to Chaos Resistance", "chaos_res"),
        "all_res": (r"\+(\d+)%? to all Elemental Resistances", "all_ele_res"),

        # Attributes - compound patterns FIRST to match before single attributes
        "all_attributes": (r"\+(\d+) to all Attributes", "all_attributes"),
        "str_dex": (r"\+(\d+) to Strength and Dexterity", "str_dex"),
        "str_int": (r"\+(\d+) to Strength and Intelligence", "str_int"),
        "dex_int": (r"\+(\d+) to Dexterity and Intelligence", "dex_int"),
        # Single attributes - use $ anchor to avoid matching compound mods
        "strength": (r"\+(\d+) to Strength$", "strength"),
        "dexterity": (r"\+(\d+) to Dexterity$", "dexterity"),
        "intelligence": (r"\+(\d+) to Intelligence$", "intelligence"),
    }

    def __init__(self, build_stats: Optional[BuildStats] = None):
        """
        Initialize calculator with build stats.

        Args:
            build_stats: BuildStats object with PoB-calculated values
        """
        self.build_stats = build_stats or BuildStats()

    def calculate_effective_values(
        self,
        mods: List[str]
    ) -> List[EffectiveModValue]:
        """
        Calculate effective values for a list of item mods.

        Args:
            mods: List of item mod strings

        Returns:
            List of EffectiveModValue objects with calculated effective values
        """
        results = []

        for mod in mods:
            effective = self._calculate_mod_value(mod)
            if effective:
                results.append(effective)

        return results

    def _calculate_mod_value(self, mod: str) -> Optional[EffectiveModValue]:
        """Calculate effective value for a single mod."""

        for pattern_name, (pattern, mod_type) in self.MOD_PATTERNS.items():
            match = re.search(pattern, mod, re.IGNORECASE)
            if match:
                raw_value = float(match.group(1))
                effective_value, multiplier, explanation = self._apply_scaling(
                    mod_type, raw_value
                )

                return EffectiveModValue(
                    mod_text=mod,
                    mod_type=mod_type,
                    raw_value=raw_value,
                    effective_value=effective_value,
                    multiplier=multiplier,
                    explanation=explanation,
                )

        return None

    def _apply_scaling(
        self,
        mod_type: str,
        raw_value: float
    ) -> Tuple[float, float, str]:
        """
        Apply build scaling to a mod value.

        Returns: (effective_value, multiplier, explanation)
        """
        bs = self.build_stats

        if mod_type == "life":
            # Flat life scales with % increased life
            multiplier = 1 + (bs.life_inc / 100)
            effective = raw_value * multiplier
            explanation = f"+{int(raw_value)} life x {multiplier:.2f} ({int(bs.life_inc)}% inc) = {int(effective)} effective"
            return effective, multiplier, explanation

        elif mod_type == "life_percent":
            # % life adds to the pool, estimate based on current total
            # This is approximate - actual depends on base life
            base_life = bs.total_life / (1 + bs.life_inc / 100) if bs.life_inc else bs.total_life
            effective = base_life * (raw_value / 100)
            explanation = f"+{int(raw_value)}% life = ~{int(effective)} life (based on {int(base_life)} base)"
            return effective, 1.0, explanation

        elif mod_type == "es":
            # Flat ES scales with % increased ES
            multiplier = 1 + (bs.es_inc / 100)
            effective = raw_value * multiplier
            explanation = f"+{int(raw_value)} ES x {multiplier:.2f} ({int(bs.es_inc)}% inc) = {int(effective)} effective"
            return effective, multiplier, explanation

        elif mod_type == "armour":
            # Flat armour scales with % increased armour
            multiplier = 1 + (bs.armour_inc / 100)
            effective = raw_value * multiplier
            explanation = f"+{int(raw_value)} armour x {multiplier:.2f} ({int(bs.armour_inc)}% inc) = {int(effective)} effective"
            return effective, multiplier, explanation

        elif mod_type == "evasion":
            multiplier = 1 + (bs.evasion_inc / 100)
            effective = raw_value * multiplier
            explanation = f"+{int(raw_value)} evasion x {multiplier:.2f} ({int(bs.evasion_inc)}% inc) = {int(effective)} effective"
            return effective, multiplier, explanation

        elif mod_type == "fire_res":
            overcap = bs.fire_overcap + raw_value
            effective = raw_value
            explanation = f"+{int(raw_value)}% fire res (overcap: {int(bs.fire_overcap)}% -> {int(overcap)}%)"
            return effective, 1.0, explanation

        elif mod_type == "cold_res":
            overcap = bs.cold_overcap + raw_value
            effective = raw_value
            explanation = f"+{int(raw_value)}% cold res (overcap: {int(bs.cold_overcap)}% -> {int(overcap)}%)"
            return effective, 1.0, explanation

        elif mod_type == "lightning_res":
            overcap = bs.lightning_overcap + raw_value
            effective = raw_value
            explanation = f"+{int(raw_value)}% lightning res (overcap: {int(bs.lightning_overcap)}% -> {int(overcap)}%)"
            return effective, 1.0, explanation

        elif mod_type == "chaos_res":
            new_res = min(75, bs.chaos_res + raw_value)
            effective = raw_value
            explanation = f"+{int(raw_value)}% chaos res ({int(bs.chaos_res)}% -> {int(new_res)}%)"
            return effective, 1.0, explanation

        elif mod_type == "all_ele_res":
            explanation = f"+{int(raw_value)}% all ele res (adds to fire/cold/lightning overcaps)"
            return raw_value * 3, 3.0, explanation

        elif mod_type == "strength":
            # Strength gives 0.5 life per point, scaled by life%
            life_mult = 1 + (bs.life_inc / 100)
            life_from_str = (raw_value / 2) * life_mult
            explanation = f"+{int(raw_value)} str = +{int(life_from_str)} effective life ({int(raw_value/2)} base x {life_mult:.2f})"
            return raw_value, 1.0, explanation

        elif mod_type == "intelligence":
            # Intelligence gives 0.5 mana and 2% ES per 10 points
            es_bonus = (raw_value / 5)  # 2 ES per 10 int
            es_mult = 1 + (bs.es_inc / 100)
            effective_es = es_bonus * es_mult
            explanation = f"+{int(raw_value)} int = +{int(effective_es)} effective ES"
            return raw_value, 1.0, explanation

        elif mod_type == "dexterity":
            # Dexterity gives 2 accuracy and 0.2% evasion per point
            explanation = f"+{int(raw_value)} dex (evasion & accuracy)"
            return raw_value, 1.0, explanation

        elif mod_type == "all_attributes":
            # All attributes - combined effect
            life_mult = 1 + (bs.life_inc / 100)
            life_from_str = (raw_value / 2) * life_mult
            explanation = f"+{int(raw_value)} all attr = +{int(life_from_str)} effective life from str"
            return raw_value * 3, 3.0, explanation

        elif mod_type in ("str_dex", "str_int", "dex_int"):
            life_mult = 1 + (bs.life_inc / 100)
            life_from_str = (raw_value / 2) * life_mult if "str" in mod_type else 0
            explanation = f"+{int(raw_value)} to two attributes"
            if life_from_str:
                explanation += f" (+{int(life_from_str)} effective life from str)"
            return raw_value * 2, 2.0, explanation

        # Default: no scaling
        return raw_value, 1.0, f"{mod} (no scaling applied)"

    def get_build_summary(self) -> str:
        """Get a formatted summary of build stats."""
        bs = self.build_stats
        lines = [
            f"Life: {int(bs.total_life)} ({int(bs.life_inc)}% increased)",
        ]

        if bs.total_es > 50:
            lines.append(f"ES: {int(bs.total_es)} ({int(bs.es_inc)}% increased)")

        if bs.total_armour > 100:
            lines.append(f"Armour: {int(bs.total_armour)} ({int(bs.armour_inc)}% increased)")

        lines.append(
            f"Res: {int(bs.fire_res)}/{int(bs.cold_res)}/{int(bs.lightning_res)}/{int(bs.chaos_res)} "
            f"(+{int(bs.fire_overcap)}/+{int(bs.cold_overcap)}/+{int(bs.lightning_overcap)} overcap)"
        )

        lines.append(f"Attributes: {int(bs.strength)}/{int(bs.dexterity)}/{int(bs.intelligence)} (Str/Dex/Int)")

        if bs.combined_dps > 0:
            if bs.combined_dps >= 1_000_000:
                lines.append(f"DPS: {bs.combined_dps/1_000_000:.2f}M")
            elif bs.combined_dps >= 1_000:
                lines.append(f"DPS: {bs.combined_dps/1_000:.1f}K")
            else:
                lines.append(f"DPS: {int(bs.combined_dps)}")

        return "\n".join(lines)


# Testing
if __name__ == "__main__":
    # Test with sample build stats
    sample_stats = {
        "Spec:LifeInc": 158.0,
        "Life": 5637.0,
        "Spec:EnergyShieldInc": 22.0,
        "EnergyShield": 113.0,
        "Spec:ArmourInc": 92.0,
        "Armour": 13878.0,
        "FireResist": 90.0,
        "FireResistOverCap": 377.0,
        "ColdResist": 90.0,
        "ColdResistOverCap": 136.0,
        "LightningResist": 90.0,
        "LightningResistOverCap": 132.0,
        "ChaosResist": 75.0,
        "Str": 332.0,
        "Dex": 128.0,
        "Int": 144.0,
        "CombinedDPS": 294808.0,
    }

    build_stats = BuildStats.from_pob_stats(sample_stats)
    calculator = BuildStatCalculator(build_stats)

    print("=== Build Summary ===")
    print(calculator.get_build_summary())
    print()

    # Test with sample item mods
    test_mods = [
        "+80 to maximum Life",
        "+45% to Fire Resistance",
        "+30% to Cold Resistance",
        "+50 to Strength",
        "+40 to Intelligence",
        "+12% to all Elemental Resistances",
        "+500 to Armour",
        "+150 to maximum Energy Shield",
    ]

    print("=== Effective Mod Values ===")
    results = calculator.calculate_effective_values(test_mods)
    for result in results:
        print(f"\n{result.mod_text}")
        print(f"  -> {result.explanation}")
