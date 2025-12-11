"""
Upgrade Finder Service.

Finds the best gear upgrades for a build within a budget constraint.
Analyzes each equipment slot, queries the trade API, and ranks results
by upgrade impact (defensive stats, DPS, gap coverage).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from core.pob import CharacterProfile, PoBItem
from core.build_stat_calculator import BuildStats
from core.bis_calculator import BiSCalculator, BiSRequirements, EQUIPMENT_SLOTS
from core.upgrade_calculator import UpgradeCalculator, UpgradeImpact, ItemStatExtractor
from core.dps_impact_calculator import DPSStats, DPSImpactCalculator, DPSImpactResult

logger = logging.getLogger(__name__)


class UpgradeSlot(str, Enum):
    """Equipment slots that can be upgraded."""
    HELMET = "Helmet"
    BODY_ARMOUR = "Body Armour"
    GLOVES = "Gloves"
    BOOTS = "Boots"
    BELT = "Belt"
    RING_1 = "Ring 1"
    RING_2 = "Ring 2"
    AMULET = "Amulet"
    WEAPON = "Weapon 1"
    OFFHAND = "Weapon 2"
    # Note: We use Ring 1/Ring 2 from PoB slot names


# Map BiS slot names to PoB slot names
BIS_TO_POB_SLOT = {
    "Helmet": "Helmet",
    "Body Armour": "Body Armour",
    "Gloves": "Gloves",
    "Boots": "Boots",
    "Belt": "Belt",
    "Ring": "Ring 1",  # Default to Ring 1 for BiS
    "Amulet": "Amulet",
    "Shield": "Weapon 2",  # Offhand
}


@dataclass
class UpgradeCandidate:
    """A potential upgrade item found from trade search."""
    # Item info
    name: str
    base_type: str
    item_level: int
    explicit_mods: List[str] = field(default_factory=list)
    implicit_mods: List[str] = field(default_factory=list)

    # Price
    price_chaos: float = 0.0
    price_display: str = ""
    listing_id: str = ""

    # Upgrade analysis
    upgrade_impact: Optional[UpgradeImpact] = None
    dps_impact: Optional[DPSImpactResult] = None

    # Scores
    upgrade_score: float = 0.0
    dps_change: float = 0.0
    dps_percent_change: float = 0.0

    # Combined score for ranking
    total_score: float = 0.0

    @property
    def all_mods(self) -> List[str]:
        """Get all mods (implicit + explicit)."""
        return self.implicit_mods + self.explicit_mods

    def get_summary(self) -> str:
        """Get a brief summary of the upgrade."""
        parts = []
        if self.upgrade_impact:
            if self.upgrade_impact.effective_life_delta > 0:
                parts.append(f"+{int(self.upgrade_impact.effective_life_delta)} life")
            total_res = (
                self.upgrade_impact.fire_res_delta +
                self.upgrade_impact.cold_res_delta +
                self.upgrade_impact.lightning_res_delta +
                self.upgrade_impact.chaos_res_delta
            )
            if total_res > 0:
                parts.append(f"+{int(total_res)}% res")
        if self.dps_percent_change > 0.5:
            parts.append(f"+{self.dps_percent_change:.1f}% DPS")
        return ", ".join(parts) if parts else "Minor improvement"


@dataclass
class SlotUpgradeResult:
    """Upgrade search results for a single equipment slot."""
    slot: str
    current_item: Optional[PoBItem]
    current_item_mods: List[str] = field(default_factory=list)
    candidates: List[UpgradeCandidate] = field(default_factory=list)
    requirements: Optional[BiSRequirements] = None
    error: Optional[str] = None

    @property
    def has_upgrades(self) -> bool:
        """Check if any upgrade candidates were found."""
        return len(self.candidates) > 0

    @property
    def best_upgrade(self) -> Optional[UpgradeCandidate]:
        """Get the best upgrade candidate."""
        if not self.candidates:
            return None
        return self.candidates[0]


@dataclass
class UpgradeFinderResult:
    """Complete upgrade finder results across all slots."""
    profile_name: str
    budget_chaos: float
    slot_results: Dict[str, SlotUpgradeResult] = field(default_factory=dict)
    total_candidates: int = 0
    search_time_seconds: float = 0.0

    def get_best_upgrades(self, limit: int = 10) -> List[tuple[str, UpgradeCandidate]]:
        """
        Get the best upgrades across all slots, sorted by score.

        Returns:
            List of (slot_name, candidate) tuples
        """
        all_upgrades: List[tuple[str, UpgradeCandidate]] = []
        for slot, result in self.slot_results.items():
            for candidate in result.candidates:
                all_upgrades.append((slot, candidate))

        # Sort by total score descending
        all_upgrades.sort(key=lambda x: x[1].total_score, reverse=True)
        return all_upgrades[:limit]

    def get_slot_summary(self) -> Dict[str, str]:
        """Get a summary of best upgrade for each slot."""
        summary = {}
        for slot, result in self.slot_results.items():
            if result.error:
                summary[slot] = f"Error: {result.error}"
            elif result.best_upgrade:
                best = result.best_upgrade
                summary[slot] = f"{best.name} ({best.price_display}) - {best.get_summary()}"
            else:
                summary[slot] = "No upgrades found"
        return summary


class UpgradeFinderService:
    """
    Service for finding gear upgrades within a budget.

    Usage:
        service = UpgradeFinderService(character_manager)
        result = service.find_upgrades("MyCharacter", budget_chaos=500)
        for slot, candidate in result.get_best_upgrades():
            print(f"{slot}: {candidate.name} - {candidate.price_display}")
    """

    # Default equipment slots to search
    DEFAULT_SLOTS = [
        "Helmet", "Body Armour", "Gloves", "Boots",
        "Belt", "Ring", "Amulet"
    ]

    def __init__(
        self,
        character_manager: Any,
        league: str = "Standard",
    ):
        """
        Initialize the upgrade finder.

        Args:
            character_manager: CharacterManager for loading profiles
            league: League to search in
        """
        self.character_manager = character_manager
        self.league = league
        self._stat_extractor = ItemStatExtractor()

    def find_upgrades(
        self,
        profile_name: str,
        budget_chaos: float,
        slots: Optional[List[str]] = None,
        max_results_per_slot: int = 10,
    ) -> UpgradeFinderResult:
        """
        Find upgrade items for a character within budget.

        Args:
            profile_name: Name of the character profile to upgrade
            budget_chaos: Maximum price in chaos orbs
            slots: Specific slots to search (None = all default slots)
            max_results_per_slot: Maximum candidates per slot

        Returns:
            UpgradeFinderResult with candidates for each slot
        """
        import time
        start_time = time.time()

        result = UpgradeFinderResult(
            profile_name=profile_name,
            budget_chaos=budget_chaos,
        )

        # Load profile
        profile = self.character_manager.get_profile(profile_name)
        if not profile:
            logger.error(f"Profile not found: {profile_name}")
            return result

        if not profile.build or not profile.build.stats:
            logger.error(f"Profile has no build stats: {profile_name}")
            return result

        # Initialize calculators
        build_stats = BuildStats.from_pob_stats(profile.build.stats)
        bis_calculator = BiSCalculator(build_stats)
        upgrade_calculator = UpgradeCalculator(build_stats)

        # Initialize DPS calculator if we have DPS stats
        dps_calculator = None
        try:
            dps_stats = DPSStats.from_pob_stats(profile.build.stats)
            if dps_stats.combined_dps > 0:
                dps_calculator = DPSImpactCalculator(dps_stats)
        except Exception as e:
            logger.debug(f"Could not initialize DPS calculator: {e}")

        # Determine which slots to search
        search_slots = slots or self.DEFAULT_SLOTS

        for slot in search_slots:
            slot_result = self._search_slot(
                profile=profile,
                slot=slot,
                budget_chaos=budget_chaos,
                bis_calculator=bis_calculator,
                upgrade_calculator=upgrade_calculator,
                dps_calculator=dps_calculator,
                max_results=max_results_per_slot,
            )
            result.slot_results[slot] = slot_result
            result.total_candidates += len(slot_result.candidates)

        result.search_time_seconds = time.time() - start_time
        logger.info(
            f"Upgrade finder completed: {result.total_candidates} candidates "
            f"across {len(result.slot_results)} slots in {result.search_time_seconds:.1f}s"
        )

        return result

    def _search_slot(
        self,
        profile: CharacterProfile,
        slot: str,
        budget_chaos: float,
        bis_calculator: BiSCalculator,
        upgrade_calculator: UpgradeCalculator,
        dps_calculator: Optional[DPSImpactCalculator],
        max_results: int,
    ) -> SlotUpgradeResult:
        """Search for upgrades in a single equipment slot."""
        # Map BiS slot to PoB slot
        pob_slot = BIS_TO_POB_SLOT.get(slot, slot)

        # Get current equipped item
        current_item = profile.build.items.get(pob_slot)
        current_mods = []
        if current_item:
            current_mods = current_item.implicit_mods + current_item.explicit_mods

        result = SlotUpgradeResult(
            slot=slot,
            current_item=current_item,
            current_item_mods=current_mods,
        )

        try:
            # Get BiS requirements for this slot
            if slot not in EQUIPMENT_SLOTS:
                # Handle Ring specifically
                if slot == "Ring":
                    requirements = bis_calculator.calculate_requirements(
                        "Ring", custom_priorities=profile.priorities
                    )
                else:
                    logger.warning(f"Unknown slot for BiS calculation: {slot}")
                    result.error = f"Unknown slot: {slot}"
                    return result
            else:
                requirements = bis_calculator.calculate_requirements(
                    slot, custom_priorities=profile.priorities
                )

            result.requirements = requirements

            # Build trade query with price constraint
            query = self._build_upgrade_query(requirements, budget_chaos)

            # Search trade API
            candidates = self._execute_trade_search(query, max_results)

            # Score each candidate
            for candidate in candidates:
                self._score_candidate(
                    candidate=candidate,
                    current_mods=current_mods,
                    upgrade_calculator=upgrade_calculator,
                    dps_calculator=dps_calculator,
                )

            # Sort by total score
            candidates.sort(key=lambda c: c.total_score, reverse=True)
            result.candidates = candidates[:max_results]

        except Exception as e:
            logger.exception(f"Error searching slot {slot}")
            result.error = str(e)

        return result

    def _build_upgrade_query(
        self,
        requirements: BiSRequirements,
        budget_chaos: float,
    ) -> Dict[str, Any]:
        """Build a trade API query from BiS requirements with price filter."""

        query: Dict[str, Any] = {
            "query": {
                "status": {"option": "online"},
                "stats": [{"type": "and", "filters": []}],
                "filters": {
                    "trade_filters": {
                        "filters": {
                            "price": {
                                "max": int(budget_chaos),
                                "option": "chaos"
                            }
                        }
                    }
                }
            },
            "sort": {"price": "asc"},
        }

        # Add stat filters from required stats (first 2)
        stat_filters = []
        for stat in requirements.required_stats[:2]:
            stat_filters.append({
                "id": stat.stat_id,
                "value": {"min": stat.min_value},
            })

        # Add stat filters from desired stats (up to 2 more)
        remaining_slots = 4 - len(stat_filters)
        for stat in requirements.desired_stats[:remaining_slots]:
            stat_filters.append({
                "id": stat.stat_id,
                "value": {"min": stat.min_value},
            })

        query["query"]["stats"][0]["filters"] = stat_filters

        return query

    def _execute_trade_search(
        self,
        query: Dict[str, Any],
        max_results: int,
    ) -> List[UpgradeCandidate]:
        """Execute trade API search and return candidates."""
        candidates: List[UpgradeCandidate] = []

        try:
            from data_sources.pricing.trade_api import TradeApiSource

            source = TradeApiSource(league=self.league)
            search_id, result_ids = source._search(query, max_results=max_results)

            if not result_ids or not search_id:
                return candidates

            listings = source._fetch_listings(search_id, result_ids[:max_results])

            for listing in listings:
                candidate = self._parse_listing(listing)
                if candidate:
                    candidates.append(candidate)

        except Exception as e:
            logger.exception(f"Trade search failed: {e}")

        return candidates

    def _parse_listing(self, listing: Dict[str, Any]) -> Optional[UpgradeCandidate]:
        """Parse a trade API listing into an UpgradeCandidate."""
        try:
            item_data = listing.get("item", {})
            listing_data = listing.get("listing", {})
            price_data = listing_data.get("price", {})

            item_name = item_data.get("name", "") or ""
            type_line = item_data.get("typeLine", "") or ""
            full_name = f"{item_name} {type_line}".strip() if item_name else type_line

            amount = price_data.get("amount", 0)
            currency = price_data.get("currency", "chaos")

            # Convert to chaos (approximate)
            chaos_value = amount
            if currency == "divine":
                chaos_value = amount * 180  # Approximate divine value
            elif currency == "exalted":
                chaos_value = amount * 15  # Approximate exalt value

            return UpgradeCandidate(
                name=full_name,
                base_type=type_line,
                item_level=item_data.get("ilvl", 0),
                explicit_mods=item_data.get("explicitMods", []),
                implicit_mods=item_data.get("implicitMods", []),
                price_chaos=chaos_value,
                price_display=f"{amount} {currency}",
                listing_id=listing.get("id", ""),
            )

        except Exception as e:
            logger.debug(f"Failed to parse listing: {e}")
            return None

    def _score_candidate(
        self,
        candidate: UpgradeCandidate,
        current_mods: List[str],
        upgrade_calculator: UpgradeCalculator,
        dps_calculator: Optional[DPSImpactCalculator],
    ) -> None:
        """Calculate scores for an upgrade candidate."""
        # Calculate defensive upgrade impact
        try:
            impact = upgrade_calculator.calculate_upgrade(
                new_item_mods=candidate.all_mods,
                current_item_mods=current_mods,
            )
            candidate.upgrade_impact = impact
            candidate.upgrade_score = impact.upgrade_score
        except Exception as e:
            logger.debug(f"Failed to calculate upgrade impact: {e}")
            candidate.upgrade_score = 0

        # Calculate DPS impact
        if dps_calculator:
            try:
                dps_impact = dps_calculator.calculate_impact(candidate.all_mods)
                candidate.dps_impact = dps_impact
                candidate.dps_change = dps_impact.total_dps_change
                candidate.dps_percent_change = dps_impact.total_dps_percent
            except Exception as e:
                logger.debug(f"Failed to calculate DPS impact: {e}")

        # Calculate total score (weighted combination)
        # Defensive score is already weighted in upgrade_calculator
        # Add DPS contribution (scaled to be comparable)
        dps_contribution = candidate.dps_percent_change * 10  # Scale % to points

        # Price efficiency bonus (cheaper = better for same stats)
        price_penalty: float = 0.0
        if candidate.price_chaos > 0:
            # Small penalty for expensive items
            price_penalty = candidate.price_chaos / 100

        candidate.total_score = (
            candidate.upgrade_score +
            dps_contribution -
            price_penalty
        )


def get_upgrade_finder(character_manager: Any, league: str = "Standard") -> UpgradeFinderService:
    """Factory function to create an UpgradeFinderService."""
    return UpgradeFinderService(character_manager, league)
