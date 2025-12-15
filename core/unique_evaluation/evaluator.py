"""
Unique Item Evaluator.

Evaluates unique items based on meta relevance, corruption value,
link/socket configuration, and poe.ninja pricing.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.item_parser import ParsedItem
from core.unique_evaluation.models import (
    CorruptionMatch,
    LinkEvaluation,
    MetaRelevance,
    UniqueItemEvaluation,
)

logger = logging.getLogger(__name__)


class UniqueItemEvaluator:
    """
    Evaluates unique items for comprehensive value assessment.

    Scoring components:
    1. Base value from poe.ninja (or fallback estimation)
    2. Corruption value analysis (+gems = premium, bricks = penalty)
    3. Link/socket evaluation (6L premium, white sockets)
    4. Meta relevance (which builds want this?)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        game_version: str = "poe1",
    ):
        """
        Initialize the unique item evaluator.

        Args:
            data_dir: Path to data directory
            game_version: "poe1" or "poe2" for meta data selection
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = data_dir
        self.game_version = game_version
        self._unique_data: Dict[str, Any] = {}
        self._meta_builds: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load unique item data and meta builds from JSON files."""
        # Load unique item data
        unique_file = self.data_dir / "unique_item_data.json"
        if unique_file.exists():
            try:
                with open(unique_file, encoding='utf-8') as f:
                    self._unique_data = json.load(f)
                logger.debug("Loaded unique item data")
            except Exception as e:
                logger.warning(f"Failed to load unique item data: {e}")
                self._unique_data = {}
        else:
            logger.warning(f"Unique item data file not found: {unique_file}")
            self._unique_data = {}

        # Load meta builds data
        meta_file = self.data_dir / "meta_builds" / self.game_version / "current_league.json"
        if meta_file.exists():
            try:
                with open(meta_file, encoding='utf-8') as f:
                    self._meta_builds = json.load(f)
                logger.debug(f"Loaded meta builds for {self.game_version}")
            except Exception as e:
                logger.warning(f"Failed to load meta builds: {e}")
                self._meta_builds = {}
        else:
            logger.debug(f"Meta builds file not found: {meta_file}")
            self._meta_builds = {}

    @property
    def chase_uniques(self) -> Dict[str, Any]:
        """Get chase uniques data."""
        return self._unique_data.get("chase_uniques", {})

    @property
    def valuable_corruptions(self) -> Dict[str, Any]:
        """Get valuable corruptions data."""
        return self._unique_data.get("valuable_corruptions", {})

    @property
    def link_values(self) -> Dict[str, Any]:
        """Get link value multipliers."""
        return self._unique_data.get("link_values", {})

    @property
    def slot_categories(self) -> Dict[str, Any]:
        """Get slot category data."""
        return self._unique_data.get("slot_categories", {})

    def is_unique_item(self, item: ParsedItem) -> bool:
        """Check if item is a unique."""
        return bool(item.rarity and item.rarity.upper() == "UNIQUE")

    def evaluate(
        self,
        item: ParsedItem,
        ninja_price: Optional[float] = None,
    ) -> Optional[UniqueItemEvaluation]:
        """
        Evaluate a unique item.

        Args:
            item: ParsedItem with rarity=UNIQUE
            ninja_price: Optional pre-fetched poe.ninja price in chaos

        Returns:
            UniqueItemEvaluation or None if not unique
        """
        if not self.is_unique_item(item):
            return None

        factors: List[str] = []
        warnings: List[str] = []

        # Basic info
        unique_name = item.name or ""
        base_type = item.base_type or ""
        slot_category = self._determine_slot_category(item)

        # Check if chase unique
        is_chase = unique_name in self.chase_uniques
        chase_data = self.chase_uniques.get(unique_name, {})
        if is_chase:
            factors.append(f"Chase unique: {unique_name}")

        # Pricing
        has_ninja_price = ninja_price is not None and ninja_price > 0
        ninja_divine = None
        if ninja_price and ninja_price >= 150:  # Rough divine conversion
            ninja_divine = ninja_price / 150

        # Calculate base score from price
        base_score = self._calculate_base_score(ninja_price, is_chase, chase_data)
        if has_ninja_price:
            if ninja_price >= 500:
                factors.append(f"High poe.ninja price: {ninja_price:.0f}c")
            elif ninja_price >= 50:
                factors.append(f"Good poe.ninja price: {ninja_price:.0f}c")

        # Corruption analysis
        corruption_matches, corruption_tier, corruption_modifier = self._evaluate_corruption(
            item, slot_category
        )
        corruption_score = self._calculate_corruption_score(
            corruption_matches, corruption_tier
        )
        if corruption_tier == "excellent":
            factors.append(f"Excellent corruption: {corruption_matches[0].mod_text}")
        elif corruption_tier == "high":
            factors.append(f"Good corruption: {corruption_matches[0].mod_text}")
        elif corruption_tier == "bricked":
            warnings.append("Bricked corruption reduces value")
            factors.append("Bricked corruption (-15)")

        # Link evaluation
        link_eval = self._evaluate_links(item, slot_category)
        link_score = self._calculate_link_score(link_eval, slot_category)
        if link_eval and link_eval.links >= 6:
            factors.append(f"6-Link ({link_eval.link_multiplier:.1f}x multiplier)")
        elif link_eval and link_eval.links >= 5:
            factors.append(f"5-Link (+{link_score} score)")
        if link_eval and link_eval.white_sockets > 0:
            factors.append(f"{link_eval.white_sockets} white socket(s)")

        # Meta relevance
        meta_relevance = self._calculate_meta_relevance(unique_name)
        meta_score = meta_relevance.meta_score if meta_relevance else 0
        if meta_relevance and meta_relevance.builds_using:
            build_list = ", ".join(meta_relevance.builds_using[:2])
            factors.append(f"Meta builds: {build_list}")
            if meta_relevance.is_trending:
                factors.append(f"Trending: {meta_relevance.trend_direction}")

        # Calculate total score
        # Weights: base 40%, corruption 20%, links 20%, meta 20%
        total_score = int(
            base_score * 0.40 +
            corruption_score * 0.20 +
            link_score * 0.20 +
            meta_score * 0.20
        )

        # Apply corruption modifier to final score
        if corruption_modifier != 1.0:
            total_score = int(total_score * corruption_modifier)
            total_score = max(0, min(100, total_score))

        # Determine tier and estimated value
        tier, estimated_value, confidence = self._determine_tier(
            total_score=total_score,
            ninja_price=ninja_price,
            is_chase=is_chase,
            link_eval=link_eval,
            corruption_modifier=corruption_modifier,
        )

        return UniqueItemEvaluation(
            item=item,
            unique_name=unique_name,
            base_type=base_type,
            slot_category=slot_category,
            ninja_price_chaos=ninja_price,
            ninja_price_divine=ninja_divine,
            has_poe_ninja_price=has_ninja_price,
            is_corrupted=item.is_corrupted,
            corruption_matches=corruption_matches,
            corruption_tier=corruption_tier,
            corruption_value_modifier=corruption_modifier,
            link_evaluation=link_eval,
            meta_relevance=meta_relevance,
            base_score=base_score,
            corruption_score=corruption_score,
            link_score=link_score,
            meta_score=meta_score,
            total_score=total_score,
            tier=tier,
            estimated_value=estimated_value,
            confidence=confidence,
            factors=factors,
            warnings=warnings,
            is_chase_unique=is_chase,
        )

    def _determine_slot_category(self, item: ParsedItem) -> str:
        """Determine the slot category from item base type."""
        base_type = (item.base_type or "").lower()

        patterns = self._unique_data.get("slot_detection_patterns", {})
        for slot, keywords in patterns.items():
            for keyword in keywords:
                if keyword.lower() in base_type:
                    return slot

        # Fallback detection
        if "jewel" in base_type:
            return "jewel"
        if any(w in base_type for w in ["ring"]):
            return "ring"
        if any(w in base_type for w in ["amulet", "talisman"]):
            return "amulet"

        return "unknown"

    def _evaluate_corruption(
        self,
        item: ParsedItem,
        slot_category: str,
    ) -> Tuple[List[CorruptionMatch], str, float]:
        """
        Evaluate corruption on an item.

        Returns:
            Tuple of (matches, tier, value_modifier)
        """
        if not item.is_corrupted:
            return [], "none", 1.0

        matches: List[CorruptionMatch] = []
        best_tier = "neutral"
        modifier = 1.0

        # Check implicits for valuable corruptions
        implicit_overrides = self.valuable_corruptions.get("implicit_overrides", {})
        for implicit in item.implicits:
            for pattern, data in implicit_overrides.items():
                # Create regex pattern from the corruption pattern
                # Escape special regex characters first, then replace # with \d+
                escaped_pattern = re.escape(pattern)
                regex_pattern = escaped_pattern.replace(r"\#", r"\d+")
                if re.search(regex_pattern, implicit, re.IGNORECASE):
                    # Check if applies to this slot
                    applies_to = data.get("applies_to", ["all"])
                    applies = "all" in applies_to or slot_category in applies_to

                    match = CorruptionMatch(
                        corruption_type="implicit_override",
                        mod_text=implicit,
                        tier=data.get("tier", "good"),
                        weight=data.get("weight", 5),
                        applies_to_slot=applies,
                    )
                    matches.append(match)

                    # Update best tier
                    if applies:
                        tier_priority = {"excellent": 4, "high": 3, "good": 2, "niche": 1}
                        current_priority = tier_priority.get(best_tier, 0)
                        new_priority = tier_priority.get(match.tier, 0)
                        if new_priority > current_priority:
                            best_tier = match.tier

        # Check for keystone grants
        keystone_grants = self.valuable_corruptions.get("keystone_grants", {})
        for implicit in item.implicits:
            for keystone, data in keystone_grants.items():
                if keystone.lower() in implicit.lower():
                    match = CorruptionMatch(
                        corruption_type="keystone",
                        mod_text=implicit,
                        tier=data.get("tier", "niche"),
                        weight=data.get("weight", 5),
                        applies_to_slot=True,
                    )
                    matches.append(match)

        # Check for white sockets
        if item.sockets:
            white_count = item.sockets.count("W")
            if white_count > 0:
                socket_data = self.valuable_corruptions.get("socket_corruptions", {}).get(
                    "white_sockets", {}
                )
                weight = min(
                    white_count * socket_data.get("weight_per_socket", 5),
                    socket_data.get("max_weight", 30)
                )
                match = CorruptionMatch(
                    corruption_type="socket",
                    mod_text=f"{white_count} white socket(s)",
                    tier="good",
                    weight=weight,
                    applies_to_slot=True,
                )
                matches.append(match)

        # Check for brick corruptions
        brick_data = self.valuable_corruptions.get("brick_corruptions", {})
        brick_patterns = (
            brick_data.get("reduced_resistance_patterns", []) +
            brick_data.get("reduced_attribute_patterns", [])
        )
        for implicit in item.implicits:
            for pattern in brick_patterns:
                regex_pattern = pattern.replace("#", r"\d+")
                if re.search(regex_pattern, implicit, re.IGNORECASE):
                    match = CorruptionMatch(
                        corruption_type="brick",
                        mod_text=implicit,
                        tier="brick",
                        weight=brick_data.get("brick_penalty", -15),
                        applies_to_slot=True,
                    )
                    matches.append(match)
                    best_tier = "bricked"
                    modifier = 0.5  # Bricked items worth less

        # Calculate modifier based on best tier
        if best_tier == "excellent":
            modifier = 3.0
        elif best_tier == "high":
            modifier = 1.8
        elif best_tier == "good":
            modifier = 1.3
        elif best_tier == "niche":
            modifier = 1.1
        elif best_tier == "bricked":
            modifier = 0.5

        return matches, best_tier, modifier

    def _calculate_corruption_score(
        self,
        matches: List[CorruptionMatch],
        tier: str,
    ) -> int:
        """Calculate corruption score from matches."""
        if not matches or tier == "none":
            return 50  # Neutral - not corrupted

        if tier == "bricked":
            return 10

        # Sum weights from applicable matches
        total_weight = sum(m.weight for m in matches if m.applies_to_slot and m.weight > 0)

        # Convert to 0-100 scale
        if tier == "excellent":
            return min(100, 80 + total_weight)
        elif tier == "high":
            return min(100, 60 + total_weight)
        elif tier == "good":
            return min(100, 50 + total_weight)
        elif tier == "niche":
            return min(100, 40 + total_weight)

        return 50  # Neutral corruption

    def _evaluate_links(
        self,
        item: ParsedItem,
        slot_category: str,
    ) -> Optional[LinkEvaluation]:
        """Evaluate socket and link configuration."""
        if not item.sockets:
            return None

        # Count sockets and white sockets
        socket_str = item.sockets
        total_sockets = len(socket_str.replace("-", "").replace(" ", ""))
        white_sockets = socket_str.count("W")
        links = item.links or 1

        # Calculate link multiplier
        link_data = self.link_values
        if links >= 6:
            multiplier = link_data.get("6_link", {}).get("multiplier", 2.5)
        elif links >= 5:
            multiplier = link_data.get("5_link", {}).get("multiplier", 1.3)
        else:
            multiplier = 1.0

        # Socket bonus (mainly for white sockets)
        socket_bonus = white_sockets * 5

        return LinkEvaluation(
            total_sockets=total_sockets,
            links=links,
            white_sockets=white_sockets,
            link_multiplier=multiplier,
            socket_bonus=socket_bonus,
        )

    def _calculate_link_score(
        self,
        link_eval: Optional[LinkEvaluation],
        slot_category: str,
    ) -> int:
        """Calculate link score from evaluation."""
        if not link_eval:
            return 50  # No sockets to evaluate

        slot_data = self.slot_categories.get(slot_category, {})
        has_6L_premium = slot_data.get("6L_premium", False)

        score = 50  # Baseline

        # Link bonuses
        if link_eval.links >= 6 and has_6L_premium:
            score = 100  # Max for 6L on body/2h weapon
        elif link_eval.links >= 6:
            score = 80
        elif link_eval.links >= 5:
            score = 70
        elif link_eval.links >= 4:
            score = 55

        # White socket bonus
        score += link_eval.socket_bonus

        return min(100, score)

    def _calculate_meta_relevance(self, unique_name: str) -> MetaRelevance:
        """Calculate meta relevance from build data."""
        relevance = MetaRelevance()

        if not self._meta_builds:
            return relevance

        builds = self._meta_builds.get("builds", [])
        trending = self._meta_builds.get("trending_uniques", [])

        # Find builds using this unique
        for build in builds:
            key_uniques = build.get("key_uniques", [])
            for unique in key_uniques:
                if unique.get("name", "").lower() == unique_name.lower():
                    build_name = build.get("name", "Unknown")
                    relevance.builds_using.append(build_name)
                    relevance.total_usage_percent += unique.get("usage_percent", 0) * (
                        build.get("popularity_percent", 0) / 100
                    )

                    # Track highest tier
                    tier = build.get("tier", "D")
                    tier_priority = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
                    if tier_priority.get(tier, 0) > tier_priority.get(
                        relevance.highest_tier_build, 0
                    ):
                        relevance.highest_tier_build = tier

        # Check trending
        for trend_item in trending:
            if trend_item.get("name", "").lower() == unique_name.lower():
                relevance.is_trending = True
                relevance.trend_direction = trend_item.get("price_trend", "stable")

        # Calculate meta score
        if relevance.builds_using:
            # More builds using = higher score
            build_count_score = min(30, len(relevance.builds_using) * 10)

            # Higher tier builds = higher score
            tier_scores = {"S": 40, "A": 30, "B": 20, "C": 10, "D": 5}
            tier_score = tier_scores.get(relevance.highest_tier_build, 5)

            # Usage percentage contribution
            usage_score = min(20, relevance.total_usage_percent * 2)

            # Trending bonus
            trend_bonus = 10 if relevance.is_trending else 0

            relevance.meta_score = min(100, build_count_score + tier_score + usage_score + trend_bonus)
        else:
            relevance.meta_score = 20  # Baseline for unlisted uniques

        return relevance

    def _calculate_base_score(
        self,
        ninja_price: Optional[float],
        is_chase: bool,
        chase_data: Dict[str, Any],
    ) -> int:
        """Calculate base score from poe.ninja price."""
        if is_chase:
            return 95  # Chase uniques get near-max base score

        if not ninja_price:
            return 30  # Unknown price = low base score

        # Price tier thresholds
        thresholds = self._unique_data.get("base_value_tiers", {}).get(
            "chaos_thresholds", {}
        )

        if ninja_price >= thresholds.get("excellent", 500):
            return 90
        elif ninja_price >= thresholds.get("good", 100):
            return 70
        elif ninja_price >= thresholds.get("average", 20):
            return 50
        elif ninja_price >= thresholds.get("vendor", 5):
            return 30
        else:
            return 15  # Vendor trash

    def _determine_tier(
        self,
        total_score: int,
        ninja_price: Optional[float],
        is_chase: bool,
        link_eval: Optional[LinkEvaluation],
        corruption_modifier: float,
    ) -> Tuple[str, str, str]:
        """
        Determine final tier and estimated value.

        Returns:
            Tuple of (tier, estimated_value, confidence)
        """
        # Chase uniques always high tier
        if is_chase:
            if ninja_price:
                return "chase", f"{ninja_price:.0f}c+", "exact"
            return "chase", "10div+", "estimated"

        # Determine tier from score
        if total_score >= 90:
            tier = "chase"
        elif total_score >= 75:
            tier = "excellent"
        elif total_score >= 50:
            tier = "good"
        elif total_score >= 25:
            tier = "average"
        else:
            tier = "vendor"

        # Estimate value
        confidence = "exact" if ninja_price else "estimated"

        if ninja_price:
            # Apply modifiers to ninja price
            adjusted_price = ninja_price * corruption_modifier
            if link_eval and link_eval.links >= 6:
                adjusted_price *= link_eval.link_multiplier

            if adjusted_price >= 500:
                value = f"{adjusted_price:.0f}c ({adjusted_price/150:.1f}div)"
            else:
                value = f"{adjusted_price:.0f}c"
        else:
            # Estimate based on tier
            tier_values = {
                "chase": "5div+",
                "excellent": "50c-2div",
                "good": "10-50c",
                "average": "1-10c",
                "vendor": "<1c",
            }
            value = tier_values.get(tier, "Unknown")
            confidence = "fallback"

        return tier, value, confidence
