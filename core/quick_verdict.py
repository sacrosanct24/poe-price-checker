"""
Quick Verdict System - Simple item valuation for casual players.

Provides a thumbs up/down/maybe verdict with plain-English explanations
for why an item is worth keeping or vendoring.

Usage:
    from core.quick_verdict import QuickVerdictCalculator, Verdict

    calculator = QuickVerdictCalculator()
    result = calculator.calculate(item, price_chaos=50.0)
    print(result.verdict)  # Verdict.KEEP
    print(result.explanation)  # "Good life roll and resists"

For league-specific thresholds:
    thresholds = VerdictThresholds.for_league_start()
    calculator = QuickVerdictCalculator(thresholds=thresholds)

Limitations:
    - Best for casual players; experts may want more detailed analysis
    - Cluster jewels, gems, and some niche items need manual checking
    - Always verify high-value items on the trade site
"""

# Disclaimer for UI display
QUICK_VERDICT_DISCLAIMER = (
    "Quick Verdict provides basic guidance for common items. "
    "For influenced, fractured, cluster jewels, or high-value uniques, "
    "verify on poe.ninja or the trade site. "
    "Thresholds can be adjusted for league timing (early/mid/late)."
)

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.result import Result, Ok, Err


class Verdict(Enum):
    """Simple verdict for item value."""
    KEEP = "keep"      # Worth more than keep_threshold
    VENDOR = "vendor"  # Worth less than vendor_threshold
    MAYBE = "maybe"    # In between - needs manual evaluation


@dataclass
class VerdictThresholds:
    """Configurable thresholds for verdict calculation."""
    vendor_threshold: float = 2.0    # Below this = vendor
    keep_threshold: float = 15.0     # Above this = definitely keep

    # Modifiers for special cases
    # Note: Most uniques are worthless (99%), only specific ones have value
    # Without price data, uniques should go to MAYBE for manual check
    unique_modifier: float = 0.0     # Neutral - requires price lookup
    six_link_bonus: float = 150.0    # 6-links are valuable (Divine Orb recipe)
    six_socket_bonus: float = 7.0    # 6-sockets have jeweller value

    # High-value mod bonuses
    gem_level_bonus: float = 50.0    # +1 to gem levels is build-defining
    influenced_bonus: float = 20.0   # Influenced items have crafting potential
    fractured_bonus: float = 30.0    # Fractured items are crafting bases

    # Meta weight bonuses (when meta data is available)
    meta_bonus_per_affix: float = 5.0    # Bonus per meta-popular affix
    meta_popularity_threshold: float = 30.0  # % popularity to count as "meta"

    @classmethod
    def for_league_start(cls) -> 'VerdictThresholds':
        """Thresholds for league start (days 1-7) - more lenient."""
        return cls(
            vendor_threshold=1.0,    # Keep more early
            keep_threshold=5.0,      # Lower bar for keeping
            six_link_bonus=200.0,    # 6-links very valuable early
            gem_level_bonus=30.0,    # Gem levels less important early
            influenced_bonus=10.0,   # Influenced less valuable early
            fractured_bonus=15.0,    # Fractured bases less developed
        )

    @classmethod
    def for_mid_league(cls) -> 'VerdictThresholds':
        """Thresholds for mid-league (days 8-30) - balanced."""
        return cls(
            vendor_threshold=2.0,
            keep_threshold=10.0,
            six_link_bonus=150.0,
            gem_level_bonus=50.0,
            influenced_bonus=20.0,
            fractured_bonus=30.0,
        )

    @classmethod
    def for_late_league(cls) -> 'VerdictThresholds':
        """Thresholds for late league (days 30+) - more strict."""
        return cls(
            vendor_threshold=5.0,     # Higher bar for keeping
            keep_threshold=20.0,      # Only keep high value
            six_link_bonus=100.0,     # 6-links more common
            gem_level_bonus=50.0,     # Still valuable
            influenced_bonus=30.0,    # Crafting bases more valuable
            fractured_bonus=40.0,     # Premium crafting bases
        )

    @classmethod
    def for_ssf(cls) -> 'VerdictThresholds':
        """Thresholds for SSF - keep more, can't trade."""
        return cls(
            vendor_threshold=0.5,     # Keep almost everything useful
            keep_threshold=3.0,       # Low bar for SSF
            six_link_bonus=500.0,     # 6-links are huge in SSF
            gem_level_bonus=100.0,    # Gem levels very impactful
            influenced_bonus=50.0,    # Can't buy influenced bases
            fractured_bonus=75.0,     # Can't buy crafting bases
        )


@dataclass
class VerdictResult:
    """Result of verdict calculation with explanation."""
    verdict: Verdict
    explanation: str
    detailed_reasons: List[str]
    estimated_value: Optional[float] = None
    confidence: str = "medium"  # low, medium, high
    meta_affixes_found: List[str] = None  # Meta-popular affixes on item
    meta_bonus_applied: float = 0.0  # Total meta bonus added

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.meta_affixes_found is None:
            self.meta_affixes_found = []

    @property
    def has_meta_bonus(self) -> bool:
        """Check if any meta bonus was applied."""
        return self.meta_bonus_applied > 0

    @property
    def emoji(self) -> str:
        """Get emoji for verdict."""
        return {
            Verdict.KEEP: "👍",
            Verdict.VENDOR: "👎",
            Verdict.MAYBE: "🤔",
        }[self.verdict]

    @property
    def color(self) -> str:
        """Get color for verdict display."""
        return {
            Verdict.KEEP: "#22bb22",    # Green
            Verdict.VENDOR: "#bb2222",  # Red
            Verdict.MAYBE: "#bbbb22",   # Yellow
        }[self.verdict]


class QuickVerdictCalculator:
    """
    Calculates simple keep/vendor/maybe verdicts for items.

    Designed for casual players who want quick decisions without
    deep market knowledge.

    Can optionally use meta weights from MetaAnalyzer to boost
    verdicts for items with currently-popular affixes.
    """

    # Mapping of mod text patterns to meta affix types
    MOD_TO_META_TYPE = {
        'maximum life': 'life',
        'regenerate': 'life',
        'fire resistance': 'resistances',
        'cold resistance': 'resistances',
        'lightning resistance': 'resistances',
        'chaos resistance': 'chaos_resistance',
        'movement speed': 'movement_speed',
        'attack speed': 'attack_speed',
        'cast speed': 'cast_speed',
        'suppress spell damage': 'spell_suppression',
        'energy shield': 'energy_shield',
        'critical strike multiplier': 'critical_strike_multiplier',
        'to strength': 'attributes',
        'to dexterity': 'attributes',
        'to intelligence': 'attributes',
        'maximum mana': 'mana',
    }

    def __init__(
        self,
        thresholds: Optional[VerdictThresholds] = None,
        meta_weights: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize with optional custom thresholds and meta weights.

        Args:
            thresholds: Custom verdict thresholds
            meta_weights: Meta weight data from RareItemEvaluator.meta_weights
                         Dict mapping affix_type -> {'popularity_percent': float, ...}
        """
        self.thresholds = thresholds or VerdictThresholds()
        self.meta_weights = meta_weights or {}

    def set_meta_weights(self, meta_weights: Dict[str, Any]) -> None:
        """
        Update meta weights dynamically.

        Args:
            meta_weights: New meta weight data from RareItemEvaluator.meta_weights
        """
        self.meta_weights = meta_weights or {}

    def set_thresholds(self, thresholds: VerdictThresholds) -> None:
        """
        Update verdict thresholds dynamically.

        Args:
            thresholds: New verdict thresholds to use
        """
        self.thresholds = thresholds or VerdictThresholds()

    def set_thresholds_from_values(
        self,
        vendor_threshold: float,
        keep_threshold: float,
    ) -> None:
        """
        Update verdict thresholds from individual values.

        Args:
            vendor_threshold: Threshold below which items are VENDOR
            keep_threshold: Threshold above which items are KEEP
        """
        self.thresholds = VerdictThresholds(
            vendor_threshold=vendor_threshold,
            keep_threshold=keep_threshold,
        )

    def calculate(
        self,
        item: Any,
        price_chaos: Optional[float] = None,
        build_context: Optional[str] = None,
    ) -> VerdictResult:
        """
        Calculate verdict for an item.

        Args:
            item: Parsed item object
            price_chaos: Estimated price in chaos (if known)
            build_context: Optional build info for relevance

        Returns:
            VerdictResult with verdict and explanation
        """
        reasons = []
        modifiers = 0.0

        # Extract item properties
        rarity = getattr(item, 'rarity', 'Normal')
        name = getattr(item, 'name', '') or getattr(item, 'base_type', 'Item')
        sockets = getattr(item, 'sockets', 0) or 0
        links = getattr(item, 'links', 0) or 0
        item_level = getattr(item, 'item_level', 0) or 0
        corrupted = getattr(item, 'corrupted', False)

        # Extract special item properties
        influences = getattr(item, 'influences', []) or []
        is_fractured = getattr(item, 'is_fractured', False)
        is_synthesised = getattr(item, 'is_synthesised', False)

        # Check for obvious keeps
        if links >= 6:
            modifiers += self.thresholds.six_link_bonus
            reasons.append("6-link is valuable (Divine Orb recipe)")
        elif sockets >= 6:
            modifiers += self.thresholds.six_socket_bonus
            reasons.append("6-socket can be sold for jewellers")

        # Influenced items have crafting potential
        if influences:
            influence_names = ', '.join(influences) if isinstance(influences, list) else str(influences)
            modifiers += self.thresholds.influenced_bonus
            reasons.append(f"Influenced item ({influence_names}) - crafting potential")

        # Fractured items are crafting bases
        if is_fractured:
            modifiers += self.thresholds.fractured_bonus
            reasons.append("Fractured item - locked mod for crafting")

        # Synthesised items can have valuable implicits
        if is_synthesised:
            modifiers += self.thresholds.fractured_bonus  # Similar value
            reasons.append("Synthesised item - check implicit value")

        # Unique items: most are worthless, need price lookup
        # Don't add bonus - push to MAYBE for manual check
        if rarity == 'Unique':
            modifiers += self.thresholds.unique_modifier  # 0 by default
            if not price_chaos:
                reasons.append("Unique - check price (most are cheap)")

        # Track meta bonuses
        meta_affixes_found = []
        meta_bonus = 0.0

        # Analyze rare item affixes
        if rarity == 'Rare':
            affix_reasons, meta_matches = self._analyze_rare_affixes_with_meta(item)
            reasons.extend(affix_reasons)
            if affix_reasons:
                modifiers += len(affix_reasons) * 3.0
                # Extra bonus for +gem level mods (build-defining)
                if any('+level to' in r.lower() for r in affix_reasons):
                    modifiers += self.thresholds.gem_level_bonus

            # Apply meta bonuses
            if meta_matches:
                meta_affixes_found = meta_matches
                meta_bonus = len(meta_matches) * self.thresholds.meta_bonus_per_affix
                modifiers += meta_bonus
                if len(meta_matches) >= 2:
                    reasons.append(f"Meta build synergy ({', '.join(meta_matches[:3])})")

        # Currency items
        if rarity == 'Currency':
            reasons.append("Currency is always useful")
            modifiers += 10.0

        # Divination cards
        if self._is_divination_card(item):
            reasons.append("Div cards stack - check full set value")
            modifiers += 5.0

        # Calculate effective value
        effective_value = (price_chaos or 0) + modifiers

        # Determine verdict
        if effective_value >= self.thresholds.keep_threshold:
            verdict = Verdict.KEEP
            if price_chaos and price_chaos >= self.thresholds.keep_threshold:
                explanation = f"Worth ~{int(price_chaos)}c - definitely keep"
            elif reasons:
                explanation = reasons[0]
            else:
                explanation = "Looks valuable - worth keeping"
            confidence = "high" if price_chaos else "medium"

        elif effective_value <= self.thresholds.vendor_threshold:
            verdict = Verdict.VENDOR
            explanation = self._get_vendor_reason(item, reasons)
            confidence = "high" if price_chaos and price_chaos < 1 else "medium"

        else:
            verdict = Verdict.MAYBE
            if price_chaos:
                explanation = f"Worth ~{int(price_chaos)}c - your call"
            else:
                explanation = "Could be worth something - check market"
            confidence = "low"

        return VerdictResult(
            verdict=verdict,
            explanation=explanation,
            detailed_reasons=reasons,
            estimated_value=price_chaos,
            confidence=confidence,
            meta_affixes_found=meta_affixes_found,
            meta_bonus_applied=meta_bonus,
        )

    def _analyze_rare_affixes_with_meta(self, item: Any) -> Tuple[List[str], List[str]]:
        """
        Analyze rare item affixes for value indicators with meta awareness.

        Returns:
            Tuple of (affix_reasons, meta_affix_types_found)
        """
        reasons = self._analyze_rare_affixes(item)
        meta_matches = []

        if not self.meta_weights:
            return reasons, meta_matches

        # Check item mods against meta weights
        explicits = getattr(item, 'explicits', []) or []
        implicits = getattr(item, 'implicits', []) or []
        all_mods = list(explicits) + list(implicits)

        for mod in all_mods:
            mod_lower = mod.lower()

            # Check against known meta patterns
            for pattern, meta_type in self.MOD_TO_META_TYPE.items():
                if pattern in mod_lower:
                    # Check if this affix type is meta-popular
                    if meta_type in self.meta_weights:
                        weight_data = self.meta_weights[meta_type]
                        if isinstance(weight_data, dict):
                            popularity = weight_data.get('popularity_percent', 0)
                        else:
                            popularity = float(weight_data) * 10  # Convert raw weight

                        if popularity >= self.thresholds.meta_popularity_threshold:
                            if meta_type not in meta_matches:
                                meta_matches.append(meta_type)
                    break  # Only match one pattern per mod

        return reasons, meta_matches

    def _analyze_rare_affixes(self, item: Any) -> List[str]:
        """Analyze rare item affixes for value indicators."""
        reasons = []

        explicits = getattr(item, 'explicits', []) or []
        implicits = getattr(item, 'implicits', []) or []
        all_mods = list(explicits) + list(implicits)

        # Check for valuable mod patterns
        has_life = False
        has_resists = False
        has_damage = False
        has_crit = False
        has_gem_level = False

        for mod in all_mods:
            mod_lower = mod.lower()

            # +Gem level mods - VERY valuable (build-defining)
            # Patterns: "+1 to Level of all X Gems", "+1 to Level of all Skill Gems"
            if 'to level of all' in mod_lower and 'gem' in mod_lower:
                has_gem_level = True
                # Extract the gem type for better description
                # Check specific types BEFORE generic "skill gems"
                if 'spell' in mod_lower:
                    reasons.append("+Level to Spell Gems (very valuable)")
                elif 'aura' in mod_lower:
                    reasons.append("+Level to Aura Gems (aurastacker value)")
                elif 'curse' in mod_lower:
                    reasons.append("+Level to Curse Gems (valuable)")
                elif any(x in mod_lower for x in ['fire', 'cold', 'lightning', 'chaos', 'physical']):
                    reasons.append("+Level to Elemental Gems (valuable)")
                elif any(x in mod_lower for x in ['strength', 'dexterity', 'intelligence']):
                    reasons.append("+Level to Attribute Gems (valuable)")
                elif 'skill gems' in mod_lower:
                    # Generic "all skill gems" - most valuable
                    reasons.append("+Level to Skill Gems (build-defining!)")
                else:
                    reasons.append("+Level to Gems (check specific type)")

            # Life roll
            if 'maximum life' in mod_lower:
                # Check for high roll (T1-T2)
                try:
                    value = self._extract_number(mod)
                    if value and value >= 80:
                        reasons.append(f"High life roll (+{value})")
                        has_life = True
                    elif value and value >= 60:
                        has_life = True
                except (ValueError, TypeError, AttributeError):
                    pass

            # Resistance
            if 'resistance' in mod_lower and '%' in mod:
                try:
                    value = self._extract_number(mod)
                    if value and value >= 35:
                        has_resists = True
                        reasons.append(f"Good resistance roll ({value}%)")
                except (ValueError, TypeError, AttributeError):
                    pass

            # Damage mods
            if any(x in mod_lower for x in ['increased damage', 'adds', 'to attacks']):
                has_damage = True

            # Crit
            if 'critical' in mod_lower:
                has_crit = True

            # Movement speed on boots
            if 'movement speed' in mod_lower:
                try:
                    value = self._extract_number(mod)
                    if value and value >= 25:
                        reasons.append(f"Good movement speed ({value}%)")
                except (ValueError, TypeError, AttributeError):
                    pass

        # Combo bonuses
        if has_life and has_resists:
            if "High life roll" not in str(reasons):
                reasons.append("Life + resists combo")

        if has_damage and has_crit:
            reasons.append("Offensive stat combo")

        return reasons

    def _extract_number(self, text: str) -> Optional[int]:
        """Extract first number from mod text."""
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        return None

    def _is_divination_card(self, item: Any) -> bool:
        """Check if item is a divination card."""
        item_class = getattr(item, 'item_class', '')
        base_type = getattr(item, 'base_type', '')
        return 'divination' in str(item_class).lower() or 'card' in str(base_type).lower()

    def _get_vendor_reason(self, item: Any, existing_reasons: List[str]) -> str:
        """Get explanation for vendor verdict."""
        rarity = getattr(item, 'rarity', 'Normal')

        if rarity == 'Normal':
            return "Normal items vendor for scraps"
        elif rarity == 'Magic':
            return "Magic items rarely worth selling"
        elif rarity == 'Rare':
            if not existing_reasons:
                return "No valuable mods detected"
            return "Mods not good enough for trade"
        else:
            return "Low value - vendor or leave"

    def calculate_from_prices(
        self,
        item: Any,
        prices: List[Tuple[str, float]],  # (source, price) pairs
    ) -> VerdictResult:
        """
        Calculate verdict using multiple price sources.

        Args:
            item: Parsed item
            prices: List of (source_name, price_in_chaos) tuples

        Returns:
            VerdictResult with aggregated verdict
        """
        if not prices:
            return self.calculate(item, price_chaos=None)

        # Use median price for stability
        sorted_prices = sorted(p[1] for p in prices)
        median_price = sorted_prices[len(sorted_prices) // 2]

        result = self.calculate(item, price_chaos=median_price)

        # Add source info to reasons
        sources = [f"{src}: {p:.1f}c" for src, p in prices]
        result.detailed_reasons.insert(0, f"Prices: {', '.join(sources)}")

        # Higher confidence with multiple sources
        if len(prices) >= 2:
            result.confidence = "high"

        return result


# Convenience function for quick checks
def quick_verdict(
    item: Any,
    price_chaos: Optional[float] = None,
) -> VerdictResult:
    """Quick verdict calculation with default settings."""
    calculator = QuickVerdictCalculator()
    return calculator.calculate(item, price_chaos)
