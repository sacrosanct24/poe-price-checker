"""
Unified Item Verdict Engine.

Provides a comprehensive single-verdict answer combining all evaluation signals:
- FOR YOU: Is this an upgrade for your build?
- TO SELL: What's it worth and is there demand?
- TO STASH: Good for other builds/alts?

Part of Phase 4: Think Big features.

Usage:
    from core.unified_verdict import UnifiedVerdictEngine, get_unified_verdict

    engine = UnifiedVerdictEngine()
    verdict = engine.evaluate(item, price=50.0, user_build=my_build)
    print(verdict.primary_action)  # "SELL"
    print(verdict.get_summary())   # Full formatted summary
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.item_parser import ParsedItem
    from core.pob.models import CharacterProfile

logger = logging.getLogger(__name__)


class PrimaryAction(Enum):
    """Recommended primary action for the item."""
    KEEP = "keep"       # Use it - it's an upgrade
    SELL = "sell"       # List it for sale
    STASH = "stash"     # Save for alt/later
    VENDOR = "vendor"   # Vendor trash
    EVALUATE = "evaluate"  # Needs manual evaluation


@dataclass
class ForYouVerdict:
    """Is this item good for the user's current build?"""
    is_upgrade: bool = False
    upgrade_slot: Optional[str] = None
    improvement_percent: float = 0.0
    reason: str = ""
    current_item_value: float = 0.0
    comparison_notes: List[str] = field(default_factory=list)


@dataclass
class ToSellVerdict:
    """Is this item valuable on the market?"""
    is_valuable: bool = False
    estimated_price: float = 0.0
    price_range: str = ""  # e.g., "3-5 div"
    demand_level: str = "unknown"  # "high", "medium", "low", "unknown"
    price_confidence: str = "low"  # "high", "medium", "low"
    price_source: str = ""
    market_notes: List[str] = field(default_factory=list)
    # Price context (CHEAP/AVERAGE/EXPENSIVE)
    price_context: str = ""  # "CHEAP", "AVERAGE", "EXPENSIVE", or ""
    price_context_color: str = ""  # Hex color for display
    price_context_explanation: str = ""  # Human-readable explanation


@dataclass
class ToStashVerdict:
    """Should this item be saved for alts or later?"""
    should_stash: bool = False
    good_for_builds: List[str] = field(default_factory=list)
    build_match_scores: Dict[str, float] = field(default_factory=dict)
    stash_reason: str = ""


@dataclass
class WhyValuable:
    """Key factors that make this item valuable."""
    factors: List[str] = field(default_factory=list)
    tier1_mods: List[str] = field(default_factory=list)
    synergies: List[str] = field(default_factory=list)
    crafting_potential: str = ""


@dataclass
class MarketContext:
    """Market context and trends for the item."""
    price_trend: str = ""  # "UP", "DOWN", "STABLE", "UNKNOWN"
    trend_percent: float = 0.0
    similar_listings: List[str] = field(default_factory=list)
    last_sale: Optional[str] = None
    days_to_sell: Optional[int] = None


@dataclass
class UnifiedVerdict:
    """Complete unified verdict combining all evaluation signals."""
    # Primary recommendation
    primary_action: PrimaryAction
    confidence: str = "medium"  # "high", "medium", "low"

    # Component verdicts
    for_you: ForYouVerdict = field(default_factory=ForYouVerdict)
    to_sell: ToSellVerdict = field(default_factory=ToSellVerdict)
    to_stash: ToStashVerdict = field(default_factory=ToStashVerdict)
    why_valuable: WhyValuable = field(default_factory=WhyValuable)
    market_context: MarketContext = field(default_factory=MarketContext)

    # Build matches
    top_build_matches: List[str] = field(default_factory=list)

    # Quick verdict integration
    quick_verdict_result: Optional[Any] = None

    # Rare evaluation integration
    rare_evaluation_result: Optional[Any] = None

    def get_summary(self) -> str:
        """Get a formatted text summary of the verdict."""
        lines = []

        # Header
        action_emoji = {
            PrimaryAction.KEEP: "KEEP",
            PrimaryAction.SELL: "SELL",
            PrimaryAction.STASH: "STASH",
            PrimaryAction.VENDOR: "VENDOR",
            PrimaryAction.EVALUATE: "CHECK",
        }
        lines.append(f"VERDICT: {action_emoji.get(self.primary_action, '???')}")
        lines.append("=" * 30)

        # FOR YOU
        if self.for_you.is_upgrade:
            lines.append(f"FOR YOU:  [OK] Upgrade for {self.for_you.upgrade_slot}")
            if self.for_you.improvement_percent > 0:
                lines.append(f"          +{self.for_you.improvement_percent:.0f}% improvement")
        else:
            lines.append(f"FOR YOU:  [X] {self.for_you.reason or 'Not an upgrade'}")

        # TO SELL
        if self.to_sell.is_valuable:
            lines.append(f"TO SELL:  [OK] Worth {self.to_sell.price_range}")
            if self.to_sell.demand_level != "unknown":
                lines.append(f"          Demand: {self.to_sell.demand_level}")
        else:
            lines.append("TO SELL:  [X] Low market value")

        # TO STASH
        if self.to_stash.should_stash:
            builds = ", ".join(self.to_stash.good_for_builds[:2])
            lines.append(f"TO STASH: [!] Good for: {builds}")
        else:
            lines.append("TO STASH: [-] No specific build fit")

        # WHY VALUABLE
        if self.why_valuable.factors:
            lines.append("")
            lines.append("WHY VALUABLE:")
            for factor in self.why_valuable.factors[:4]:
                lines.append(f"  * {factor}")

        # TOP BUILDS
        if self.top_build_matches:
            lines.append("")
            lines.append("BUILDS THAT WANT THIS:")
            for build in self.top_build_matches[:3]:
                lines.append(f"  {build}")

        # MARKET CONTEXT
        if self.market_context.price_trend and self.market_context.price_trend != "UNKNOWN":
            lines.append("")
            lines.append("MARKET CONTEXT:")
            trend_symbol = {"UP": "+", "DOWN": "-", "STABLE": "~"}.get(
                self.market_context.price_trend, "?"
            )
            lines.append(
                f"  Trending {self.market_context.price_trend} "
                f"({trend_symbol}{abs(self.market_context.trend_percent):.0f}%)"
            )
            if self.market_context.similar_listings:
                lines.append(f"  Similar: {', '.join(self.market_context.similar_listings[:3])}")

        return "\n".join(lines)

    def get_action_text(self) -> str:
        """Get short action recommendation text."""
        if self.primary_action == PrimaryAction.KEEP:
            return "KEEP - Upgrade for your build"
        elif self.primary_action == PrimaryAction.SELL:
            return f"SELL - Worth {self.to_sell.price_range or 'checking'}"
        elif self.primary_action == PrimaryAction.STASH:
            builds = self.to_stash.good_for_builds[:2]
            return f"STASH - Good for {', '.join(builds) if builds else 'alts'}"
        elif self.primary_action == PrimaryAction.VENDOR:
            return "VENDOR - Low value"
        else:
            return "EVALUATE - Needs manual check"


class UnifiedVerdictEngine:
    """
    Engine that combines all evaluation signals into a unified verdict.

    Integrates:
    - QuickVerdictCalculator for basic verdict
    - RareItemEvaluator for rare item analysis
    - UpgradeFinder for build comparison
    - Build Archetypes for cross-build analysis
    - Market data for price context
    """

    def __init__(
        self,
        quick_verdict_calculator: Optional[Any] = None,
        rare_evaluator: Optional[Any] = None,
        upgrade_finder: Optional[Any] = None,
    ):
        """
        Initialize the unified verdict engine.

        Args:
            quick_verdict_calculator: QuickVerdictCalculator instance
            rare_evaluator: RareItemEvaluator instance
            upgrade_finder: UpgradeFinder instance
        """
        self._quick_verdict = quick_verdict_calculator
        self._rare_evaluator = rare_evaluator
        self._upgrade_finder = upgrade_finder

    def evaluate(
        self,
        item: "ParsedItem",
        price: Optional[float] = None,
        user_build: Optional["CharacterProfile"] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> UnifiedVerdict:
        """
        Perform unified evaluation of an item.

        Args:
            item: Parsed item to evaluate
            price: Known price in chaos (optional)
            user_build: User's current build profile (optional)
            market_data: Additional market data (optional)

        Returns:
            UnifiedVerdict with all evaluation signals
        """
        verdict = UnifiedVerdict(primary_action=PrimaryAction.EVALUATE)

        # 1. Quick verdict for basic evaluation
        self._evaluate_quick_verdict(verdict, item, price)

        # 2. Rare item evaluation for detailed analysis
        self._evaluate_rare_item(verdict, item)

        # 3. Check if upgrade for user's build
        self._evaluate_for_user(verdict, item, user_build)

        # 4. Cross-build analysis
        self._evaluate_cross_builds(verdict, item)

        # 5. Market context
        self._evaluate_market_context(verdict, item, price, market_data)

        # 6. Determine primary action
        self._determine_primary_action(verdict, price)

        return verdict

    def _evaluate_quick_verdict(
        self,
        verdict: UnifiedVerdict,
        item: "ParsedItem",
        price: Optional[float],
    ) -> None:
        """Evaluate using quick verdict calculator."""
        if not self._quick_verdict:
            try:
                from core.quick_verdict import QuickVerdictCalculator
                self._quick_verdict = QuickVerdictCalculator()
            except ImportError:
                return

        try:
            qv_result = self._quick_verdict.calculate(item, price_chaos=price)
            verdict.quick_verdict_result = qv_result

            # Extract to_sell info
            if qv_result.estimated_value:
                verdict.to_sell.estimated_price = qv_result.estimated_value
                verdict.to_sell.price_confidence = qv_result.confidence

            # Extract WHY factors from detailed reasons
            for reason in qv_result.detailed_reasons[:5]:
                if reason not in verdict.why_valuable.factors:
                    verdict.why_valuable.factors.append(reason)

        except Exception as e:
            logger.debug(f"Quick verdict evaluation failed: {e}")

    def _evaluate_rare_item(
        self,
        verdict: UnifiedVerdict,
        item: "ParsedItem",
    ) -> None:
        """Evaluate rare item for detailed analysis."""
        rarity = getattr(item, 'rarity', '')
        if rarity != 'Rare':
            return

        if not self._rare_evaluator:
            try:
                from core.rare_evaluation import RareItemEvaluator
                self._rare_evaluator = RareItemEvaluator()
            except ImportError:
                return

        try:
            evaluation = self._rare_evaluator.evaluate(item)
            verdict.rare_evaluation_result = evaluation

            # Extract T1 mods
            matched_affixes = getattr(evaluation, 'matched_affixes', []) or []
            for affix in matched_affixes:
                tier = getattr(affix, 'tier', '')
                if tier == 'tier1':
                    affix_type = getattr(affix, 'affix_type', '')
                    if affix_type:
                        verdict.why_valuable.tier1_mods.append(f"T1 {affix_type}")

            # Extract synergies
            synergies = getattr(evaluation, 'synergies_found', []) or []
            verdict.why_valuable.synergies.extend(synergies[:3])

            # Add synergies to factors
            for syn in synergies[:2]:
                factor = f"{syn} synergy"
                if factor not in verdict.why_valuable.factors:
                    verdict.why_valuable.factors.append(factor)

            # Extract crafting potential
            open_p = getattr(evaluation, 'open_prefixes', 0)
            open_s = getattr(evaluation, 'open_suffixes', 0)
            if open_p > 0 or open_s > 0:
                verdict.why_valuable.crafting_potential = f"{open_p}P/{open_s}S open"
                verdict.why_valuable.factors.append(
                    f"Crafting potential ({open_p}P/{open_s}S)"
                )

            # Cross-build matches from rare evaluation
            cross_matches = getattr(evaluation, 'cross_build_matches', []) or []
            for match in cross_matches[:5]:
                archetype = getattr(match, 'archetype', None)
                score = getattr(match, 'score', 0)
                if archetype:
                    name = getattr(archetype, 'name', 'Unknown')
                    verdict.top_build_matches.append(f"{name} ({score:.0f}%)")
                    verdict.to_stash.good_for_builds.append(name)
                    verdict.to_stash.build_match_scores[name] = score

        except Exception as e:
            logger.debug(f"Rare item evaluation failed: {e}")

    def _evaluate_for_user(
        self,
        verdict: UnifiedVerdict,
        item: "ParsedItem",
        user_build: Optional["CharacterProfile"],
    ) -> None:
        """Evaluate if item is an upgrade for user's build."""
        if not user_build:
            verdict.for_you.reason = "No build profile set"
            return

        # Get item slot
        slot = getattr(item, 'slot', None)
        if not slot:
            # Try to infer slot from base type
            base_type = getattr(item, 'base_type', '') or ''
            slot = self._infer_slot(base_type)

        if not slot:
            verdict.for_you.reason = "Unknown equipment slot"
            return

        # Try upgrade finder
        if self._upgrade_finder:
            try:
                # Check if item is better than current equipment
                is_upgrade = self._upgrade_finder.is_upgrade(
                    item, user_build, slot
                )
                if is_upgrade:
                    verdict.for_you.is_upgrade = True
                    verdict.for_you.upgrade_slot = slot
                    verdict.for_you.reason = f"Better than current {slot}"
                else:
                    verdict.for_you.reason = f"Current {slot} is better"
            except Exception as e:
                logger.debug(f"Upgrade check failed: {e}")
                verdict.for_you.reason = "Could not compare"
        else:
            verdict.for_you.reason = "Upgrade finder not available"

    def _evaluate_cross_builds(
        self,
        verdict: UnifiedVerdict,
        item: "ParsedItem",
    ) -> None:
        """Evaluate cross-build appeal using archetype matcher."""
        # If rare evaluation already provided matches, use those
        if verdict.top_build_matches:
            if len(verdict.to_stash.good_for_builds) >= 2:
                verdict.to_stash.should_stash = True
                verdict.to_stash.stash_reason = (
                    f"Good for {len(verdict.to_stash.good_for_builds)} builds"
                )
            return

        # For all items (including non-rares), use archetype matcher
        try:
            from core.build_archetypes import analyze_item_for_builds

            # Use lower threshold to capture weaker matches for informational purposes
            cross_analysis = analyze_item_for_builds(item, min_score=15.0)
            top_matches = cross_analysis.get_top_matches(5)

            for match in top_matches:
                archetype = match.archetype
                verdict.top_build_matches.append(
                    f"{archetype.name} ({match.score:.0f}%)"
                )
                if match.score >= 50:  # Moderate+ match
                    verdict.to_stash.good_for_builds.append(archetype.name)
                    verdict.to_stash.build_match_scores[archetype.name] = match.score

            # Set stash recommendation if good matches
            if len(verdict.to_stash.good_for_builds) >= 2:
                verdict.to_stash.should_stash = True
                verdict.to_stash.stash_reason = (
                    f"Good for {len(verdict.to_stash.good_for_builds)} builds"
                )
            elif cross_analysis.strong_matches:
                verdict.to_stash.should_stash = True
                best = cross_analysis.best_match
                verdict.to_stash.stash_reason = (
                    f"Strong match for {best.archetype.name}"
                )

        except Exception as e:
            logger.debug(f"Cross-build analysis failed: {e}")

    def _evaluate_market_context(
        self,
        verdict: UnifiedVerdict,
        item: "ParsedItem",
        price: Optional[float],
        market_data: Optional[Dict[str, Any]],
    ) -> None:
        """Evaluate market context for the item."""
        if not price:
            verdict.to_sell.is_valuable = False
            verdict.market_context.price_trend = "UNKNOWN"
            return

        # Set price info
        verdict.to_sell.estimated_price = price
        verdict.to_sell.is_valuable = price >= 10  # 10c threshold

        # Format price range
        if price >= 150:  # ~1 divine
            divines = price / 150
            if divines >= 1.5:
                verdict.to_sell.price_range = f"{divines:.1f} div"
            else:
                verdict.to_sell.price_range = "~1 div"
        else:
            verdict.to_sell.price_range = f"~{int(price)}c"

        # Calculate price context (CHEAP/AVERAGE/EXPENSIVE)
        self._evaluate_price_context(verdict, item, price)

        # Use market data if provided
        if market_data:
            trend = market_data.get('trend', 'UNKNOWN')
            verdict.market_context.price_trend = trend
            verdict.market_context.trend_percent = market_data.get('trend_percent', 0)

            similar = market_data.get('similar_listings', [])
            verdict.market_context.similar_listings = similar[:5]

            verdict.to_sell.demand_level = market_data.get('demand', 'unknown')

    def _evaluate_price_context(
        self,
        verdict: UnifiedVerdict,
        item: "ParsedItem",
        price: float,
    ) -> None:
        """Calculate price context (CHEAP/AVERAGE/EXPENSIVE) for the item."""
        try:
            from core.price_context import PriceContextCalculator

            # Get item class and rarity
            item_class = getattr(item, 'item_class', '') or ''
            rarity = getattr(item, 'rarity', 'Normal') or 'Normal'

            # Create calculator (uses config for thresholds if available)
            config = getattr(self, '_config', None)
            calculator = PriceContextCalculator(config)

            # Skip if disabled in config
            if not calculator.is_enabled():
                return

            # Get context
            context = calculator.get_context(price, item_class, rarity)

            # Set verdict fields
            verdict.to_sell.price_context = context.label
            verdict.to_sell.price_context_color = context.color
            verdict.to_sell.price_context_explanation = context.explanation

        except Exception as e:
            logger.debug(f"Price context calculation failed: {e}")

    def _determine_primary_action(
        self,
        verdict: UnifiedVerdict,
        price: Optional[float],
    ) -> None:
        """Determine the primary recommended action."""
        # Priority order:
        # 1. KEEP if it's an upgrade for user's build
        # 2. SELL if valuable on market
        # 3. STASH if good for other builds
        # 4. VENDOR if low value
        # 5. EVALUATE if unsure

        if verdict.for_you.is_upgrade:
            verdict.primary_action = PrimaryAction.KEEP
            verdict.confidence = "high"
            return

        if verdict.to_sell.is_valuable:
            verdict.primary_action = PrimaryAction.SELL
            verdict.confidence = verdict.to_sell.price_confidence
            return

        if verdict.to_stash.should_stash:
            verdict.primary_action = PrimaryAction.STASH
            verdict.confidence = "medium"
            return

        # Check quick verdict for vendor decision
        if verdict.quick_verdict_result:
            from core.quick_verdict import Verdict
            qv = verdict.quick_verdict_result.verdict
            if qv == Verdict.VENDOR:
                verdict.primary_action = PrimaryAction.VENDOR
                verdict.confidence = verdict.quick_verdict_result.confidence
                return
            elif qv == Verdict.MAYBE:
                verdict.primary_action = PrimaryAction.EVALUATE
                verdict.confidence = "low"
                return

        # Default based on price
        if price is not None:
            if price < 2:
                verdict.primary_action = PrimaryAction.VENDOR
                verdict.confidence = "medium"
            elif price < 10:
                verdict.primary_action = PrimaryAction.EVALUATE
                verdict.confidence = "low"
            else:
                verdict.primary_action = PrimaryAction.SELL
                verdict.confidence = "low"
        else:
            verdict.primary_action = PrimaryAction.EVALUATE
            verdict.confidence = "low"

    def _infer_slot(self, base_type: str) -> Optional[str]:
        """Infer equipment slot from base type."""
        base_lower = base_type.lower()

        # Helmets
        if any(x in base_lower for x in ['helmet', 'cap', 'circlet', 'crown', 'mask', 'hood', 'burgonet']):
            return "Helmet"

        # Body Armour
        if any(x in base_lower for x in ['vest', 'robe', 'plate', 'jacket', 'coat', 'garb', 'regalia', 'raiment']):
            return "Body Armour"

        # Gloves
        if any(x in base_lower for x in ['glove', 'gauntlet', 'mitt', 'wrap']):
            return "Gloves"

        # Boots
        if any(x in base_lower for x in ['boot', 'greave', 'shoe', 'slipper']):
            return "Boots"

        # Belt
        if any(x in base_lower for x in ['belt', 'sash', 'stygian']):
            return "Belt"

        # Ring
        if 'ring' in base_lower:
            return "Ring"

        # Amulet
        if any(x in base_lower for x in ['amulet', 'talisman']):
            return "Amulet"

        # Shield
        if any(x in base_lower for x in ['shield', 'buckler', 'tower']):
            return "Shield"

        return None


def get_unified_verdict(
    item: "ParsedItem",
    price: Optional[float] = None,
    user_build: Optional["CharacterProfile"] = None,
) -> UnifiedVerdict:
    """
    Convenience function to get unified verdict for an item.

    Args:
        item: Parsed item to evaluate
        price: Known price in chaos (optional)
        user_build: User's current build profile (optional)

    Returns:
        UnifiedVerdict with complete evaluation
    """
    engine = UnifiedVerdictEngine()
    return engine.evaluate(item, price=price, user_build=user_build)


# Testing
if __name__ == "__main__":
    from core.item_parser import ParsedItem

    # Create a test item
    test_item = ParsedItem(
        raw_text="Test Rare Ring",
        name="Apocalypse Turn",
        base_type="Two-Stone Ring",
        rarity="Rare",
        item_level=85,
        explicits=[
            "+92 to Maximum Life",
            "+45% to Fire Resistance",
            "+38% to Cold Resistance",
            "+12% to Chaos Resistance",
        ],
    )

    print("=== Unified Verdict Test ===\n")

    verdict = get_unified_verdict(test_item, price=75.0)
    print(verdict.get_summary())
    print()
    print(f"Action: {verdict.get_action_text()}")
