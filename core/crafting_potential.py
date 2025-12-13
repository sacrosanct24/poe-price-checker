"""
Crafting Potential Analyzer.

Analyzes items to determine:
- Divine orb improvement potential (roll ranges)
- Open affix slots for crafting
- Suggested crafting options
- Overall crafting value estimate

Part of Phase 3: Teaching & Learning features.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from core.affix_tier_calculator import AFFIX_TIER_DATA, AffixTierCalculator
from core.mod_tier_detector import detect_mod_tier, ModTierResult

if TYPE_CHECKING:
    from core.item_parser import ParsedItem

logger = logging.getLogger(__name__)


@dataclass
class ModAnalysis:
    """Analysis of a single mod on an item."""
    mod_text: str
    stat_type: Optional[str]
    current_value: Optional[int]
    tier: Optional[int]
    min_roll: int = 0
    max_roll: int = 0
    is_crafted: bool = False
    is_fractured: bool = False

    @property
    def divine_potential(self) -> int:
        """How much value could be gained by divine orb (max - current)."""
        if self.current_value is None or self.max_roll == 0:
            return 0
        return max(0, self.max_roll - self.current_value)

    @property
    def roll_quality(self) -> float:
        """Percentage of max roll achieved (0-100)."""
        if self.max_roll == 0 or self.min_roll == self.max_roll:
            return 100.0
        if self.current_value is None:
            return 0.0
        range_size = self.max_roll - self.min_roll
        if range_size == 0:
            return 100.0
        position = self.current_value - self.min_roll
        return min(100.0, max(0.0, (position / range_size) * 100))

    @property
    def tier_label(self) -> str:
        """Get tier label like 'T1', 'T2', etc."""
        if self.tier is None:
            return ""
        return f"T{self.tier}"


@dataclass
class CraftOption:
    """A potential crafting option."""
    name: str
    cost_estimate: str  # e.g., "2c", "1 divine", "~50c"
    expected_value_add: int  # Estimated value added in chaos
    description: str
    risk_level: str = "low"  # "low", "medium", "high"
    slot_type: str = ""  # "prefix", "suffix", or ""


@dataclass
class CraftingAnalysis:
    """Complete crafting potential analysis for an item."""
    # Slot counts
    open_prefixes: int = 0
    open_suffixes: int = 0
    total_mods: int = 0

    # Mod analysis
    mod_analyses: List[ModAnalysis] = field(default_factory=list)

    # Divine potential
    total_divine_potential: int = 0  # Sum of all divine improvements
    best_divine_target: Optional[str] = None  # Which mod benefits most
    divine_recommended: bool = False

    # Crafting options
    craft_options: List[CraftOption] = field(default_factory=list)

    # Overall assessment
    crafting_value: str = "low"  # "low", "medium", "high", "very high"
    summary: str = ""

    def get_divine_summary(self) -> str:
        """Get a summary of divine orb potential."""
        if not self.divine_recommended:
            return "Divine not recommended (rolls near max or low tier)"

        upgradeable = [m for m in self.mod_analyses
                       if m.divine_potential > 0 and m.tier and m.tier <= 2]
        if not upgradeable:
            return "No significant divine potential"

        parts = []
        for mod in sorted(upgradeable, key=lambda x: -x.divine_potential)[:3]:
            stat = mod.stat_type or "mod"
            parts.append(f"{stat}: +{mod.divine_potential} potential")

        return "; ".join(parts)

    def get_craft_summary(self) -> str:
        """Get a summary of crafting options."""
        if not self.craft_options:
            return "No crafting recommended"

        best = self.craft_options[0]
        return f"Best option: {best.name} ({best.cost_estimate})"


# Common bench crafts organized by slot type
BENCH_CRAFTS: Dict[str, List[CraftOption]] = {
    "prefix": [
        CraftOption(
            name="Craft Life",
            cost_estimate="2c",
            expected_value_add=15,
            description="+55-64 to Maximum Life",
            slot_type="prefix",
        ),
        CraftOption(
            name="Craft ES%",
            cost_estimate="2c",
            expected_value_add=10,
            description="+80-104% Energy Shield",
            slot_type="prefix",
        ),
        CraftOption(
            name="Craft Flat ES",
            cost_estimate="1c",
            expected_value_add=8,
            description="+30-37 to Maximum Energy Shield",
            slot_type="prefix",
        ),
    ],
    "suffix": [
        CraftOption(
            name="Craft Resistance",
            cost_estimate="1c",
            expected_value_add=10,
            description="+29-35% to Resistance",
            slot_type="suffix",
        ),
        CraftOption(
            name="Craft Attack Speed",
            cost_estimate="2c",
            expected_value_add=12,
            description="+7-8% Attack Speed (gloves)",
            slot_type="suffix",
        ),
        CraftOption(
            name="Craft Movement Speed",
            cost_estimate="2c",
            expected_value_add=20,
            description="+20-25% Movement Speed (boots)",
            slot_type="suffix",
        ),
        CraftOption(
            name="Craft Crit Multi",
            cost_estimate="3c",
            expected_value_add=15,
            description="+16-20% Critical Strike Multiplier",
            slot_type="suffix",
        ),
    ],
}

# Advanced crafting options
ADVANCED_CRAFTS: List[CraftOption] = [
    CraftOption(
        name="Exalt Slam",
        cost_estimate="1 divine",
        expected_value_add=40,
        description="Random mod - high variance",
        risk_level="high",
    ),
    CraftOption(
        name="Aisling Slam (T4)",
        cost_estimate="~50c",
        expected_value_add=60,
        description="Veiled mod with choice",
        risk_level="medium",
    ),
    CraftOption(
        name="Harvest Reforge",
        cost_estimate="~30c",
        expected_value_add=30,
        description="Reroll keeping prefixes/suffixes",
        risk_level="medium",
    ),
]


class CraftingPotentialAnalyzer:
    """
    Analyzes items for crafting potential and improvement opportunities.
    """

    def __init__(self):
        self._tier_calc = AffixTierCalculator(use_repoe=True)

    def analyze(self, item: "ParsedItem") -> CraftingAnalysis:
        """
        Perform complete crafting potential analysis on an item.

        Args:
            item: Parsed item to analyze

        Returns:
            CraftingAnalysis with all findings
        """
        analysis = CraftingAnalysis()

        # Get explicit mods (field is 'explicits' in ParsedItem)
        explicit_mods = getattr(item, 'explicits', []) or []
        if not explicit_mods:
            # Fallback for alternate attribute name
            explicit_mods = getattr(item, 'explicit_mods', []) or []

        # Analyze each mod
        for mod_text in explicit_mods:
            mod_analysis = self._analyze_mod(mod_text, item)
            analysis.mod_analyses.append(mod_analysis)

        # Estimate open slots
        analysis.total_mods = len(explicit_mods)
        self._estimate_open_slots(analysis, item)

        # Calculate divine potential
        self._calculate_divine_potential(analysis)

        # Determine crafting options
        self._determine_craft_options(analysis, item)

        # Generate summary
        self._generate_summary(analysis, item)

        return analysis

    def _analyze_mod(
        self,
        mod_text: str,
        item: "ParsedItem"
    ) -> ModAnalysis:
        """Analyze a single mod."""
        # Use existing tier detector
        tier_result = detect_mod_tier(mod_text)

        # Check if fractured
        is_fractured = "(fractured)" in mod_text.lower()
        if not is_fractured:
            # Check item's fractured mods if available
            fractured_mods = getattr(item, 'fractured_mods', []) or []
            is_fractured = mod_text in fractured_mods

        mod_analysis = ModAnalysis(
            mod_text=mod_text,
            stat_type=tier_result.stat_type,
            current_value=tier_result.value,
            tier=tier_result.tier,
            is_crafted=tier_result.is_crafted,
            is_fractured=is_fractured,
        )

        # Get roll range for the tier
        if tier_result.stat_type and tier_result.tier:
            tier_data = AFFIX_TIER_DATA.get(tier_result.stat_type, [])
            for tier, ilvl_req, min_val, max_val in tier_data:
                if tier == tier_result.tier:
                    mod_analysis.min_roll = min_val
                    mod_analysis.max_roll = max_val
                    break

        return mod_analysis

    def _estimate_open_slots(
        self,
        analysis: CraftingAnalysis,
        item: "ParsedItem"
    ) -> None:
        """Estimate open prefix/suffix slots."""
        # Categorize mods by prefix/suffix
        prefix_count: float = 0
        suffix_count: float = 0

        # Known prefix stats
        prefix_stats = {
            "life", "energy_shield", "mana", "armour", "evasion",
            "physical_damage", "elemental_damage", "spell_damage",
        }
        # Known suffix stats
        suffix_stats = {
            "fire_resistance", "cold_resistance", "lightning_resistance",
            "chaos_resistance", "strength", "dexterity", "intelligence",
            "all_attributes", "attack_speed", "cast_speed", "movement_speed",
            "critical_strike_chance", "critical_strike_multiplier",
            "mana_regeneration", "life_regeneration", "spell_suppression",
        }

        for mod in analysis.mod_analyses:
            if mod.stat_type:
                if mod.stat_type in prefix_stats:
                    prefix_count += 1
                elif mod.stat_type in suffix_stats:
                    suffix_count += 1
                else:
                    # Unknown - assume even split
                    prefix_count += 0.5
                    suffix_count += 0.5
            else:
                # Can't determine - assume even split
                prefix_count += 0.5
                suffix_count += 0.5

        # Convert to integers and calculate open slots
        prefix_count = int(prefix_count + 0.5)  # Round
        suffix_count = int(suffix_count + 0.5)

        # Max 3 prefixes, 3 suffixes for rare items
        analysis.open_prefixes = max(0, 3 - prefix_count)
        analysis.open_suffixes = max(0, 3 - suffix_count)

    def _calculate_divine_potential(self, analysis: CraftingAnalysis) -> None:
        """Calculate divine orb improvement potential."""
        total_potential = 0
        best_target = None
        best_potential = 0

        for mod in analysis.mod_analyses:
            # Only consider T1-T2 mods for divine (T3+ not worth divining)
            if mod.tier and mod.tier <= 2 and not mod.is_crafted:
                potential = mod.divine_potential
                total_potential += potential

                if potential > best_potential:
                    best_potential = potential
                    best_target = mod.stat_type

        analysis.total_divine_potential = total_potential
        analysis.best_divine_target = best_target

        # Recommend divine if significant potential exists
        # Generally worth if potential > 10% of average mod value
        analysis.divine_recommended = best_potential >= 5 and total_potential >= 10

    def _determine_craft_options(
        self,
        analysis: CraftingAnalysis,
        item: "ParsedItem"
    ) -> None:
        """Determine available crafting options."""
        options = []

        # Get item slot for slot-specific crafts
        slot = getattr(item, 'slot', '') or ''
        slot_lower = slot.lower()

        # Add bench crafts based on open slots
        if analysis.open_prefixes > 0:
            for craft in BENCH_CRAFTS["prefix"]:
                options.append(craft)

        if analysis.open_suffixes > 0:
            for craft in BENCH_CRAFTS["suffix"]:
                # Filter by slot appropriateness
                if "movement speed" in craft.name.lower() and "boot" not in slot_lower:
                    continue
                if "attack speed" in craft.name.lower() and "glove" not in slot_lower:
                    continue
                options.append(craft)

        # Add advanced options if item has good base
        has_good_mods = sum(1 for m in analysis.mod_analyses
                           if m.tier and m.tier <= 2) >= 2

        if has_good_mods and (analysis.open_prefixes > 0 or analysis.open_suffixes > 0):
            for craft in ADVANCED_CRAFTS:
                options.append(craft)

        # Sort by expected value
        options.sort(key=lambda x: -x.expected_value_add)
        analysis.craft_options = options[:5]  # Top 5

    def _generate_summary(
        self,
        analysis: CraftingAnalysis,
        item: "ParsedItem"
    ) -> None:
        """Generate overall crafting assessment."""
        # Count good mods
        good_mod_count = sum(1 for m in analysis.mod_analyses
                            if m.tier and m.tier <= 2)
        great_mod_count = sum(1 for m in analysis.mod_analyses
                             if m.tier and m.tier == 1)

        # Calculate crafting value
        score = 0

        # Open slots are valuable
        score += analysis.open_prefixes * 10
        score += analysis.open_suffixes * 10

        # Good mods to preserve
        score += good_mod_count * 5
        score += great_mod_count * 10

        # Divine potential
        if analysis.divine_recommended:
            score += 10

        # Categorize
        if score >= 50:
            analysis.crafting_value = "very high"
        elif score >= 30:
            analysis.crafting_value = "high"
        elif score >= 15:
            analysis.crafting_value = "medium"
        else:
            analysis.crafting_value = "low"

        # Build summary
        parts = []

        if analysis.open_prefixes > 0 or analysis.open_suffixes > 0:
            parts.append(
                f"{analysis.open_prefixes}P/{analysis.open_suffixes}S open"
            )

        if great_mod_count > 0:
            parts.append(f"{great_mod_count} T1 mods")
        elif good_mod_count > 0:
            parts.append(f"{good_mod_count} good mods")

        if analysis.divine_recommended:
            parts.append("divine potential")

        if parts:
            analysis.summary = "; ".join(parts)
        else:
            analysis.summary = "Limited crafting potential"


def analyze_crafting_potential(item: "ParsedItem") -> CraftingAnalysis:
    """
    Convenience function to analyze an item's crafting potential.

    Args:
        item: ParsedItem to analyze

    Returns:
        CraftingAnalysis with full results
    """
    analyzer = CraftingPotentialAnalyzer()
    return analyzer.analyze(item)


def get_divine_recommendation(item: "ParsedItem") -> str:
    """
    Get a quick divine orb recommendation.

    Args:
        item: ParsedItem to analyze

    Returns:
        Human-readable recommendation
    """
    analysis = analyze_crafting_potential(item)
    return analysis.get_divine_summary()


# Testing
if __name__ == "__main__":
    from core.item_parser import ParsedItem

    # Create a test item
    test_item = ParsedItem(
        raw_text="Test Rare Helmet",
        name="Test Rare Helmet",
        base_type="Hubris Circlet",
        rarity="Rare",
        item_level=86,
        explicits=[
            "+92 to Maximum Life",      # T2 life (90-99)
            "+45% to Fire Resistance",  # T2 fire res (43-45)
            "+30% to Cold Resistance",  # T4 cold res (30-35)
            "+55 to Intelligence",      # T1 int (51-55)
        ],
    )

    print("=== Crafting Potential Analysis ===\n")
    analysis = analyze_crafting_potential(test_item)

    print(f"Open Slots: {analysis.open_prefixes}P / {analysis.open_suffixes}S")
    print(f"Crafting Value: {analysis.crafting_value}")
    print(f"Summary: {analysis.summary}")
    print()

    print("=== Mod Analysis ===")
    for mod in analysis.mod_analyses:
        quality_bar = "=" * int(mod.roll_quality / 10)
        print(f"  {mod.tier_label:3} | {mod.mod_text}")
        if mod.stat_type:
            print(f"       Roll: {mod.current_value} ({mod.min_roll}-{mod.max_roll})")
            print(f"       Quality: [{quality_bar:<10}] {mod.roll_quality:.0f}%")
            if mod.divine_potential > 0:
                print(f"       Divine: +{mod.divine_potential} potential")
        print()

    print("=== Divine Potential ===")
    print(f"  {analysis.get_divine_summary()}")
    print()

    print("=== Crafting Options ===")
    for opt in analysis.craft_options[:3]:
        print(f"  {opt.name} ({opt.cost_estimate})")
        print(f"    {opt.description}")
        print(f"    Expected value: +{opt.expected_value_add}c")
        print()
