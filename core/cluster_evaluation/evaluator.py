"""
Cluster Jewel Evaluator.

Evaluates cluster jewels based on notables, enchantments, and synergies
to determine their tier and estimated value.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.item_parser import ParsedItem
from core.cluster_evaluation.models import ClusterJewelEvaluation, NotableMatch

logger = logging.getLogger(__name__)


class ClusterJewelEvaluator:
    """
    Evaluates cluster jewels for potential value.

    Scoring is based on:
    - Notable quality and tier (meta, high, medium, low)
    - Synergistic notable combinations
    - Enchantment type popularity
    - Item level for crafting potential
    - Jewel socket count (for large clusters)
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the cluster jewel evaluator.

        Args:
            data_dir: Path to data directory containing cluster_jewel_notables.json
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = data_dir
        self._notables_data: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load cluster jewel notables data from JSON file."""
        notable_file = self.data_dir / "cluster_jewel_notables.json"
        if notable_file.exists():
            try:
                with open(notable_file, encoding='utf-8') as f:
                    self._notables_data = json.load(f)
                logger.debug(
                    f"Loaded cluster jewel data: "
                    f"{len(self._notables_data.get('notables', {}))} notables"
                )
            except Exception as e:
                logger.warning(f"Failed to load cluster jewel data: {e}")
                self._notables_data = {}
        else:
            logger.warning(f"Cluster jewel data file not found: {notable_file}")
            self._notables_data = {}

    @property
    def notables(self) -> Dict[str, Any]:
        """Get notables database."""
        return self._notables_data.get("notables", {})

    @property
    def enchantment_values(self) -> Dict[str, Any]:
        """Get enchantment values."""
        return self._notables_data.get("enchantment_values", {})

    @property
    def synergy_combos(self) -> Dict[str, Any]:
        """Get synergy combinations."""
        return self._notables_data.get("synergy_combos", {})

    @property
    def size_values(self) -> Dict[str, Any]:
        """Get size values."""
        return self._notables_data.get("size_values", {})

    def is_cluster_jewel(self, item: ParsedItem) -> bool:
        """Check if item is a cluster jewel."""
        if not item.base_type:
            return False
        return "Cluster Jewel" in item.base_type

    def evaluate(self, item: ParsedItem) -> Optional[ClusterJewelEvaluation]:
        """
        Evaluate a cluster jewel for value.

        Args:
            item: Parsed item to evaluate

        Returns:
            ClusterJewelEvaluation if item is a cluster jewel, None otherwise
        """
        if not self.is_cluster_jewel(item):
            return None

        # Get basic info
        size = item.cluster_jewel_size or self._detect_size(item)
        passive_count = item.cluster_jewel_passives or 0
        jewel_sockets = item.cluster_jewel_sockets
        enchantment_type = item.cluster_jewel_enchantment or "unknown"

        factors: List[str] = []

        # Evaluate enchantment
        enchantment_score, enchant_display = self._evaluate_enchantment(
            enchantment_type, size
        )
        if enchantment_score >= 70:
            factors.append(f"Popular enchantment: {enchant_display}")

        # Match notables
        matched_notables = self._match_notables(item.cluster_jewel_notables)
        notable_score = self._calculate_notable_score(matched_notables)

        # Count high-value notables
        meta_count = sum(1 for n in matched_notables if n.tier == "meta")
        high_count = sum(1 for n in matched_notables if n.tier in ["meta", "high"])
        if meta_count > 0:
            factors.append(f"{meta_count} meta-tier notable(s)")
        elif high_count > 0:
            factors.append(f"{high_count} high-tier notable(s)")

        # Check synergies
        synergies_found, synergy_bonus = self._check_synergies(matched_notables)
        if synergies_found:
            factors.append(f"Synergy: {', '.join(synergies_found)} (+{synergy_bonus})")

        # Mark notables with synergy
        notable_names_in_synergies = set()
        for combo_data in self.synergy_combos.values():
            notable_names_in_synergies.update(combo_data.get("required_notables", []))
        for notable in matched_notables:
            if notable.name in notable_names_in_synergies and synergies_found:
                notable.has_synergy = True

        # ilvl scoring
        ilvl_score = self._calculate_ilvl_score(item.item_level, size)
        if ilvl_score >= 10:
            factors.append(f"High ilvl ({item.item_level}+) for crafting")

        # Open suffix detection
        has_open_suffix, crafting_potential = self._check_crafting_potential(
            item, matched_notables, size
        )
        if has_open_suffix:
            factors.append("Open suffix for crafting")

        # Jewel socket bonus
        if jewel_sockets > 0:
            factors.append(f"{jewel_sockets} jewel socket(s)")

        # Calculate total score
        total_score = self._calculate_total_score(
            enchantment_score=enchantment_score,
            notable_score=notable_score,
            synergy_bonus=synergy_bonus,
            ilvl_score=ilvl_score,
            crafting_potential=crafting_potential,
            size=size,
            jewel_sockets=jewel_sockets,
        )

        # Determine tier and value
        tier, estimated_value = self._determine_tier(
            total_score=total_score,
            notables=matched_notables,
            synergies=synergies_found,
            size=size,
            jewel_sockets=jewel_sockets,
        )

        return ClusterJewelEvaluation(
            item=item,
            size=size,
            passive_count=passive_count,
            jewel_sockets=jewel_sockets,
            enchantment_type=enchantment_type,
            enchantment_display=enchant_display,
            enchantment_score=enchantment_score,
            matched_notables=matched_notables,
            notable_score=notable_score,
            synergies_found=synergies_found,
            synergy_bonus=synergy_bonus,
            ilvl_score=ilvl_score,
            has_open_suffix=has_open_suffix,
            crafting_potential=crafting_potential,
            total_score=total_score,
            tier=tier,
            estimated_value=estimated_value,
            factors=factors,
        )

    def _detect_size(self, item: ParsedItem) -> str:
        """Detect cluster size from base type."""
        base = item.base_type or ""
        if "Large" in base:
            return "Large"
        elif "Medium" in base:
            return "Medium"
        return "Small"

    def _evaluate_enchantment(
        self, enchant_type: str, size: str
    ) -> Tuple[int, str]:
        """
        Score the enchantment type.

        Returns:
            Tuple of (score 0-100, display name)
        """
        enchant_data = self.enchantment_values.get(enchant_type, {})
        base_weight = enchant_data.get("base_weight", 5)
        meta_mult = enchant_data.get("meta_multiplier", 1.0)
        display_name = enchant_data.get("display_name", enchant_type.replace("_", " ").title())

        # Base score from 0-100
        raw_score = base_weight * 10 * meta_mult

        # Adjust by size (larger = more valuable enchant matters more)
        size_mult = {"Small": 0.8, "Medium": 1.0, "Large": 1.2}.get(size, 1.0)

        return min(100, int(raw_score * size_mult)), display_name

    def _match_notables(self, notable_names: List[str]) -> List[NotableMatch]:
        """Match notable names against database."""
        matches = []

        for name in notable_names:
            notable_data = self.notables.get(name, {})
            if notable_data:
                matches.append(NotableMatch(
                    name=name,
                    weight=notable_data.get("weight", 5),
                    tier=notable_data.get("tier", "low"),
                    description=notable_data.get("description", ""),
                    skill_type=notable_data.get("skill_type", ""),
                ))
            else:
                # Unknown notable - give base score
                matches.append(NotableMatch(
                    name=name,
                    weight=5,
                    tier="medium",
                    description="Notable not in database",
                ))

        return matches

    def _calculate_notable_score(self, notables: List[NotableMatch]) -> int:
        """Calculate score from notables (0-100)."""
        if not notables:
            return 0

        total_weight = sum(n.weight for n in notables)
        meta_count = sum(1 for n in notables if n.tier == "meta")
        high_count = sum(1 for n in notables if n.tier == "high")

        # Base score from weight
        if len(notables) >= 3 and total_weight >= 25:
            base = 70 + min(30, total_weight - 25)
        elif len(notables) >= 2 and total_weight >= 15:
            base = 50 + min(30, (total_weight - 15) * 2)
        elif len(notables) >= 1:
            base = 20 + min(40, total_weight * 3)
        else:
            base = 0

        # Bonus for meta/high tier
        tier_bonus = meta_count * 10 + high_count * 5

        return min(100, base + tier_bonus)

    def _check_synergies(
        self, notables: List[NotableMatch]
    ) -> Tuple[List[str], int]:
        """Check for synergistic notable combinations."""
        found = []
        bonus = 0
        notable_names = {n.name for n in notables}

        for combo_name, combo_data in self.synergy_combos.items():
            required = set(combo_data.get("required_notables", []))
            if required.issubset(notable_names):
                # Clean up combo name for display
                display_name = combo_name.replace("_", " ").title()
                found.append(display_name)
                bonus += combo_data.get("bonus", 10)

        return found, bonus

    def _calculate_ilvl_score(self, ilvl: Optional[int], size: str) -> int:
        """Score item level for crafting potential."""
        if not ilvl:
            return 0

        # Higher ilvl = better notable possibilities
        # Large clusters benefit more from high ilvl
        size_mult = {"Small": 0.5, "Medium": 0.8, "Large": 1.0}.get(size, 0.8)

        if ilvl >= 84:
            return int(15 * size_mult)
        elif ilvl >= 75:
            return int(10 * size_mult)
        elif ilvl >= 68:
            return int(5 * size_mult)
        return 0

    def _check_crafting_potential(
        self,
        item: ParsedItem,
        notables: List[NotableMatch],
        size: str,
    ) -> Tuple[bool, int]:
        """
        Detect if cluster has open suffix for crafting.

        Returns:
            Tuple of (has_open_suffix, crafting_potential_score)
        """
        max_notables = self.size_values.get(size, {}).get("max_notables", 2)
        current_notables = len(notables)

        has_open = current_notables < max_notables
        potential = 5 if has_open else 0

        # Bonus if high ilvl + open suffix
        if has_open and item.item_level and item.item_level >= 75:
            potential += 5

        return has_open, potential

    def _calculate_total_score(
        self,
        enchantment_score: int,
        notable_score: int,
        synergy_bonus: int,
        ilvl_score: int,
        crafting_potential: int,
        size: str,
        jewel_sockets: int,
    ) -> int:
        """Calculate weighted total score."""
        # Weights: notables 50%, enchantment 25%, bonuses 25%
        base_score = (
            notable_score * 0.50 +
            enchantment_score * 0.25 +
            synergy_bonus +
            ilvl_score +
            crafting_potential
        )

        # Jewel socket bonus for large clusters
        socket_bonus = jewel_sockets * 10

        # Size multiplier
        size_mult = self.size_values.get(size, {}).get("base_value", 1.0)

        return min(100, int((base_score + socket_bonus) * size_mult))

    def _determine_tier(
        self,
        total_score: int,
        notables: List[NotableMatch],
        synergies: List[str],
        size: str,
        jewel_sockets: int,
    ) -> Tuple[str, str]:
        """
        Determine tier and estimated value.

        Returns:
            Tuple of (tier, estimated_value)
        """
        meta_notable_count = sum(1 for n in notables if n.tier == "meta")
        high_notable_count = sum(1 for n in notables if n.tier in ["meta", "high"])

        # Excellent: meta notables + synergy OR multiple high-tier notables
        if total_score >= 80:
            if meta_notable_count >= 1 or (high_notable_count >= 2 and synergies):
                if size == "Large" and jewel_sockets >= 2:
                    return "excellent", "5-20div"
                elif size == "Large":
                    return "excellent", "2-10div"
                return "excellent", "1-5div"

        # Good: high-tier notables or good synergy
        if total_score >= 60:
            if high_notable_count >= 1:
                if size == "Large":
                    return "good", "50c-2div"
                return "good", "30c-1div"

        # Average: decent notables or enchantment
        if total_score >= 40:
            return "average", "10-50c"

        # Vendor
        return "vendor", "<10c"
