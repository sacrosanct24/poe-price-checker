"""
Price Integrator - Connects multiple pricing sources to item evaluation.

This module provides:
1. Unique item pricing from poe.ninja
2. ML-based rare item pricing from poeprices.info
3. Evaluation-based rare item scoring
4. Meta-weighted affix adjustments based on high-value item analysis
5. Base type value analysis
6. Currency conversion utilities
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.item_parser import ParsedItem
from core.rare_item_evaluator import RareItemEvaluation, RareItemEvaluator

logger = logging.getLogger(__name__)


@dataclass
class PriceResult:
    """Result of price lookup or estimation."""
    chaos_value: float
    divine_value: float
    confidence: str  # "exact", "estimated", "ml_predicted", "unknown"
    source: str  # "poe.ninja", "poeprices", "evaluation", "meta_analysis"
    notes: List[str] = field(default_factory=list)
    ml_confidence_score: Optional[float] = None  # 0-100 from poeprices.info
    price_range: Optional[Tuple[float, float]] = None  # (min, max) for ML predictions

    @property
    def display_price(self) -> str:
        """Get formatted price string."""
        if self.divine_value >= 1:
            return f"{self.divine_value:.1f} divine"
        elif self.chaos_value >= 1:
            return f"{self.chaos_value:.0f}c"
        else:
            return "<1c"

    @property
    def display_range(self) -> Optional[str]:
        """Get formatted price range string (if available)."""
        if self.price_range:
            min_val, max_val = self.price_range
            if max_val >= self._divine_threshold:
                return f"{min_val / self._divine_threshold:.1f}-{max_val / self._divine_threshold:.1f} divine"
            return f"{min_val:.0f}-{max_val:.0f}c"
        return None

    _divine_threshold: float = 180.0  # Default, updated by integrator


class PriceIntegrator:
    """
    Integrates multiple pricing sources for comprehensive item valuation.

    Uses:
    - poe.ninja for unique items and currency
    - poeprices.info for ML-based rare item pricing
    - RareItemEvaluator for rare item scoring
    - Meta analysis for market-aware adjustments
    """

    def __init__(
        self,
        league: str = "Standard",
        evaluator: Optional[RareItemEvaluator] = None,
        use_poeprices: bool = True,
    ):
        """
        Initialize the price integrator.

        Args:
            league: League for pricing data
            evaluator: RareItemEvaluator instance (creates new if None)
            use_poeprices: Enable poeprices.info ML pricing (default: True)
        """
        self.league = league
        self.evaluator = evaluator or RareItemEvaluator()
        self.use_poeprices = use_poeprices

        # Lazy-load API clients
        self._ninja_client = None
        self._poeprices_client = None
        self._divine_value: float = 180.0  # Default fallback

        # Cache for unique prices
        self._unique_prices: Dict[str, float] = {}
        self._prices_loaded = False

    @property
    def ninja_client(self):
        """Lazy-load poe.ninja client."""
        if self._ninja_client is None:
            try:
                from data_sources.pricing.poe_ninja import PoeNinjaAPI
                self._ninja_client = PoeNinjaAPI(league=self.league)
                self._divine_value = self._ninja_client.ensure_divine_rate()
                if self._divine_value <= 0:
                    self._divine_value = 180.0  # Fallback
                logger.info(f"Loaded PoeNinjaAPI, divine = {self._divine_value:.0f}c")
            except Exception as e:
                logger.warning(f"Failed to load PoeNinjaAPI: {e}")
                self._ninja_client = DummyPriceClient()
        return self._ninja_client

    @property
    def poeprices_client(self):
        """Lazy-load poeprices.info client."""
        if self._poeprices_client is None and self.use_poeprices:
            try:
                from data_sources.pricing.poeprices import PoePricesAPI
                self._poeprices_client = PoePricesAPI(league=self.league)
                logger.info(f"Loaded PoePricesAPI for league: {self.league}")
            except Exception as e:
                logger.warning(f"Failed to load PoePricesAPI: {e}")
                self._poeprices_client = None
        return self._poeprices_client

    def _ensure_prices_loaded(self) -> None:
        """Load unique item prices from poe.ninja."""
        if self._prices_loaded:
            return

        try:
            # Use load_all_prices from existing PoeNinjaAPI
            all_prices = self.ninja_client.load_all_prices()

            # Extract unique items
            for key, item in all_prices.get('uniques', {}).items():
                chaos = item.get('chaosValue', 0)
                if chaos > 0:
                    self._unique_prices[key] = chaos

            logger.info(f"Loaded {len(self._unique_prices)} unique item prices")
            self._prices_loaded = True
        except Exception as e:
            logger.warning(f"Failed to load unique prices: {e}")

    def get_unique_price(self, item: ParsedItem) -> Optional[PriceResult]:
        """
        Get price for a unique item.

        Args:
            item: ParsedItem with rarity=UNIQUE

        Returns:
            PriceResult if found, None otherwise
        """
        if not item.rarity or item.rarity.upper() != "UNIQUE":
            return None

        self._ensure_prices_loaded()

        name = item.name or ""
        name_lower = name.lower()

        # Try exact match first
        if name_lower in self._unique_prices:
            chaos = self._unique_prices[name_lower]
            return PriceResult(
                chaos_value=chaos,
                divine_value=chaos / self._divine_value,
                confidence="exact",
                source="poe.ninja",
                notes=[f"Direct price from poe.ninja: {chaos:.0f}c"]
            )

        # Try with links for weapons/armour
        if item.links and item.links >= 5:
            link_key = f"{name_lower}|{item.links}l"
            # Try various link formats
            for key in [link_key, f"{name_lower}|{item.links}-link"]:
                if key in self._unique_prices:
                    chaos = self._unique_prices[key]
                    return PriceResult(
                        chaos_value=chaos,
                        divine_value=chaos / self._divine_value,
                        confidence="exact",
                        source="poe.ninja",
                        notes=[f"{item.links}L variant: {chaos:.0f}c"]
                    )

        # Try direct API lookup using find_item_price
        try:
            ninja_item = self.ninja_client.find_item_price(
                item_name=name,
                base_type=item.base_type,
                rarity="UNIQUE"
            )
            if ninja_item:
                chaos = ninja_item.get('chaosValue', 0)
                return PriceResult(
                    chaos_value=chaos,
                    divine_value=chaos / self._divine_value,
                    confidence="exact",
                    source="poe.ninja",
                    notes=[f"API lookup: {chaos:.0f}c"]
                )
        except Exception:
            pass

        return None

    def get_rare_price(
        self,
        item: ParsedItem,
        item_text: Optional[str] = None,
    ) -> PriceResult:
        """
        Estimate price for a rare item using ML prediction and/or evaluation.

        Args:
            item: ParsedItem with rarity=RARE
            item_text: Raw item text for poeprices.info (optional)

        Returns:
            PriceResult with estimated value
        """
        # Try ML prediction first if enabled and item text provided
        if self.use_poeprices and item_text and self.poeprices_client:
            ml_result = self._get_ml_price(item_text)
            if ml_result and ml_result.chaos_value > 0:
                # Supplement with evaluation data
                evaluation = self.evaluator.evaluate(item)
                ml_result.notes.append(f"Evaluation tier: {evaluation.tier}")
                return ml_result

        # Fallback to evaluation-based pricing
        evaluation = self.evaluator.evaluate(item)

        # Map evaluation tier to chaos range
        chaos_estimate, notes = self._evaluation_to_chaos(evaluation)

        return PriceResult(
            chaos_value=chaos_estimate,
            divine_value=chaos_estimate / self._divine_value,
            confidence="estimated",
            source="evaluation",
            notes=notes
        )

    def _get_ml_price(self, item_text: str) -> Optional[PriceResult]:
        """
        Get ML-based price prediction from poeprices.info.

        Args:
            item_text: Raw item text (from Ctrl+C)

        Returns:
            PriceResult if successful, None otherwise
        """
        if not self.poeprices_client:
            return None

        try:
            prediction = self.poeprices_client.predict_price(item_text)

            if not prediction.is_valid:
                logger.warning(f"poeprices.info prediction failed: {prediction.error_msg}")
                return None

            # Convert to chaos if in divine
            if prediction.currency == "divine":
                chaos_min = prediction.min_price * self._divine_value
                chaos_max = prediction.max_price * self._divine_value
                chaos_avg = prediction.average_price * self._divine_value
            else:
                chaos_min = prediction.min_price
                chaos_max = prediction.max_price
                chaos_avg = prediction.average_price

            # Build notes from mod contributions
            notes = [f"ML prediction: {prediction.price_range_str}"]
            notes.append(f"Confidence: {prediction.confidence_score:.0f}%")

            top_mods = self.poeprices_client.get_top_contributing_mods(prediction, 3)
            if top_mods:
                notes.append("Top value mods:")
                for mod, contrib in top_mods:
                    notes.append(f"  {mod}: {'+' if contrib > 0 else ''}{contrib:.2f}")

            result = PriceResult(
                chaos_value=chaos_avg,
                divine_value=chaos_avg / self._divine_value,
                confidence="ml_predicted",
                source="poeprices",
                notes=notes,
                ml_confidence_score=prediction.confidence_score,
                price_range=(chaos_min, chaos_max),
            )
            result._divine_threshold = self._divine_value

            return result

        except Exception as e:
            logger.warning(f"ML price prediction failed: {e}")
            return None

    def _evaluation_to_chaos(
        self, evaluation: RareItemEvaluation
    ) -> Tuple[float, List[str]]:
        """
        Convert evaluation result to chaos estimate.

        Returns:
            (chaos_value, notes)
        """
        notes = []
        base_chaos = 0.0

        # Map tier to base value
        tier_values = {
            "excellent": 150.0,
            "good": 40.0,
            "average": 15.0,
            "vendor": 1.0,
        }

        base_chaos = tier_values.get(evaluation.tier, 5.0)
        notes.append(f"Base tier ({evaluation.tier}): {base_chaos:.0f}c")

        # Adjust based on score within tier
        if evaluation.tier == "excellent":
            if evaluation.total_score >= 90:
                base_chaos *= 3.0
                notes.append("Elite score (90+): 3x multiplier")
            elif evaluation.total_score >= 80:
                base_chaos *= 2.0
                notes.append("High score (80+): 2x multiplier")
        elif evaluation.tier == "good":
            if evaluation.total_score >= 70:
                base_chaos *= 1.5
                notes.append("Strong score (70+): 1.5x multiplier")

        # Synergy bonus
        if evaluation.synergies_found:
            synergy_mult = 1.0 + (len(evaluation.synergies_found) * 0.25)
            base_chaos *= synergy_mult
            notes.append(f"Synergies ({len(evaluation.synergies_found)}): {synergy_mult:.2f}x")

        # Fractured bonus
        if evaluation.is_fractured and evaluation.fractured_bonus >= 25:
            base_chaos *= 1.5
            notes.append("Fractured T1: 1.5x multiplier")

        # Archetype fit bonus
        if evaluation.matched_archetypes:
            archetype_mult = 1.0 + (len(evaluation.matched_archetypes) * 0.1)
            base_chaos *= archetype_mult
            notes.append(f"Meta archetypes: {archetype_mult:.2f}x")

        # Influence mod bonus
        influence_mods = [m for m in evaluation.matched_affixes if m.is_influence_mod]
        if influence_mods:
            base_chaos *= 1.3
            notes.append("Influence mods: 1.3x multiplier")

        return base_chaos, notes

    def price_item(
        self,
        item: ParsedItem,
        item_text: Optional[str] = None,
    ) -> PriceResult:
        """
        Get price for any item type.

        Args:
            item: ParsedItem to price
            item_text: Raw item text for ML pricing (optional, for rares)

        Returns:
            PriceResult with value
        """
        if not item.rarity:
            return PriceResult(
                chaos_value=0,
                divine_value=0,
                confidence="unknown",
                source="none",
                notes=["Unknown item rarity"]
            )

        rarity = item.rarity.upper()

        # Unique items - use poe.ninja
        if rarity == "UNIQUE":
            result = self.get_unique_price(item)
            if result:
                return result
            # Fallback for unpriced uniques
            return PriceResult(
                chaos_value=1,
                divine_value=0,
                confidence="unknown",
                source="fallback",
                notes=["Unique not found in poe.ninja"]
            )

        # Rare items - use ML prediction + evaluator
        if rarity == "RARE":
            return self.get_rare_price(item, item_text=item_text)

        # Magic/Normal items - generally worthless except special cases
        return PriceResult(
            chaos_value=0,
            divine_value=0,
            confidence="exact",
            source="static",
            notes=["Non-rare/unique items are typically vendor trash"]
        )

    def get_high_value_uniques(
        self,
        min_chaos: float = 50,
    ) -> List[dict]:
        """
        Get list of high-value unique items from loaded prices.

        Args:
            min_chaos: Minimum value threshold

        Returns:
            List of dicts with name and chaos_value
        """
        self._ensure_prices_loaded()

        high_value = []
        for name, chaos in self._unique_prices.items():
            if chaos >= min_chaos:
                high_value.append({
                    "name": name,
                    "chaos_value": chaos,
                    "divine_value": chaos / self._divine_value,
                })

        # Sort by value descending
        high_value.sort(key=lambda x: x['chaos_value'], reverse=True)
        return high_value

    def get_divine_value(self) -> float:
        """Get current Divine Orb value in chaos."""
        return self._divine_value

    def get_price_summary(
        self,
        item: ParsedItem,
        item_text: Optional[str] = None,
    ) -> str:
        """
        Get a formatted price summary for display.

        Args:
            item: Item to price
            item_text: Raw item text for ML pricing (optional)

        Returns:
            Multi-line formatted string
        """
        result = self.price_item(item, item_text=item_text)

        lines = []
        lines.append("=== Price Estimate ===")
        lines.append(f"Item: {item.get_display_name()}")
        lines.append(f"Rarity: {item.rarity}")
        lines.append("")
        lines.append(f"Price: {result.display_price}")

        # Show range if available (from ML prediction)
        if result.price_range:
            range_str = result.display_range
            if range_str:
                lines.append(f"Range: {range_str}")

        lines.append(f"Chaos: {result.chaos_value:.0f}c")
        lines.append(f"Divine: {result.divine_value:.2f}")
        lines.append("")
        lines.append(f"Confidence: {result.confidence}")
        lines.append(f"Source: {result.source}")

        # Show ML confidence score if available
        if result.ml_confidence_score is not None:
            lines.append(f"ML Confidence: {result.ml_confidence_score:.0f}%")

        if result.notes:
            lines.append("")
            lines.append("Details:")
            for note in result.notes:
                lines.append(f"  - {note}")

        return "\n".join(lines)


class DummyPriceClient:
    """Fallback when poe.ninja is unavailable."""

    def get_price(self, name: str):
        return None

    def fetch_all_uniques(self):
        return []

    def get_meta_uniques(self, **kwargs):
        return []

    def get_high_value_items(self, **kwargs):
        return []

    def get_divine_value(self):
        return 180.0


# Singleton instance
_integrator: Optional[PriceIntegrator] = None


def get_price_integrator(league: str = "Standard") -> PriceIntegrator:
    """Get or create price integrator singleton."""
    global _integrator
    if _integrator is None or _integrator.league != league:
        _integrator = PriceIntegrator(league=league)
    return _integrator


if __name__ == "__main__":
    # Test the integrator
    logging.basicConfig(level=logging.INFO)

    from core.item_parser import ItemParser

    parser = ItemParser()
    integrator = PriceIntegrator(league="Standard", use_poeprices=True)

    print("=" * 80)
    print("PRICE INTEGRATOR TEST")
    print("=" * 80)

    # Test unique item
    unique_text = """Rarity: UNIQUE
Headhunter
Leather Belt
--------
Item Level: 44
--------
+40 to maximum Life
--------
+55 to Strength
+70 to maximum Life
11% increased Damage with Hits against Rare monsters
When you Kill a Rare monster, you gain its Modifiers for 60 seconds
"""

    print("\n1. Testing Unique Item Pricing:")
    item = parser.parse(unique_text)
    if item:
        print(integrator.get_price_summary(item))

    # Test rare item with ML pricing
    rare_text = """Item Class: Body Armours
Rarity: Rare
Dread Shell
Vaal Regalia
--------
Quality: +20% (augmented)
Energy Shield: 437 (augmented)
--------
Requirements:
Level: 68
Int: 194
--------
Sockets: B-B-B-B-B-B
--------
Item Level: 86
--------
+87 to maximum Energy Shield
+78 to maximum Life
+42% to Fire Resistance
+38% to Cold Resistance
+35% to Lightning Resistance
14% increased Stun and Block Recovery"""

    print("\n2. Testing Rare Item with ML Pricing (poeprices.info):")
    item = parser.parse(rare_text)
    if item:
        # Pass raw item text for ML pricing
        print(integrator.get_price_summary(item, item_text=rare_text))

    # Test rare item without ML (evaluation only)
    print("\n3. Testing Rare Item Evaluation Only (no item text):")
    if item:
        # Create integrator without poeprices
        eval_only = PriceIntegrator(league="Standard", use_poeprices=False)
        print(eval_only.get_price_summary(item))

    # Test high-value uniques
    print("\n4. Top 10 High-Value Uniques:")
    high_value = integrator.get_high_value_uniques(min_chaos=100)
    for i, item_data in enumerate(high_value[:10], 1):
        print(f"  {i}. {item_data['name']}: {item_data['chaos_value']:.0f}c")

    print("\n" + "=" * 80)
