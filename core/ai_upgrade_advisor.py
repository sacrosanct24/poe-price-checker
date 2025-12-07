"""
AI Upgrade Advisor Service.

Provides intelligent gear upgrade recommendations by:
1. Analyzing current equipped gear from PoB
2. Scanning stash cache for potential upgrades
3. Generating Good/Better/Best recommendations via AI
4. Creating trade search suggestions for external upgrades
5. Researching build guides via web search

Usage:
    advisor = AIUpgradeAdvisorService(db, config)

    # Get upgrade recommendations for a slot
    result = advisor.get_upgrade_recommendations(
        profile=character_profile,
        slot="Helmet",
        stash_account="MyAccount",
    )

    # Research build online
    research = advisor.research_build(
        build_name="Lightning Arrow Deadeye",
        guide_url="https://maxroll.gg/poe/build-guides/..."
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.database import Database
    from core.config import Config
    from core.pob_integration import CharacterProfile, PoBItem
    from core.build_summarizer import BuildSummary
    from core.stash_storage import StashStorageService
    from core.stash_valuator import PricedItem

logger = logging.getLogger(__name__)


class UpgradeTier(str, Enum):
    """Tier classification for upgrade recommendations."""
    BEST = "best"  # Significant upgrade, worth prioritizing
    BETTER = "better"  # Notable improvement
    GOOD = "good"  # Minor but positive upgrade
    SIDEGRADE = "sidegrade"  # Different, not necessarily better
    SKIP = "skip"  # Not recommended


@dataclass
class StashUpgradeCandidate:
    """A potential upgrade found in the player's stash."""

    # Item identification
    name: str
    base_type: str
    item_class: str
    tab_name: str
    tab_index: int
    position: tuple[int, int]  # (x, y) in stash grid

    # Item properties
    rarity: str
    item_level: int
    links: int
    sockets: str
    corrupted: bool

    # Mods
    implicit_mods: List[str] = field(default_factory=list)
    explicit_mods: List[str] = field(default_factory=list)

    # Value
    chaos_value: float = 0.0

    # Raw data for AI context
    raw_item: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_mods(self) -> List[str]:
        """Get all mods combined."""
        return self.implicit_mods + self.explicit_mods

    def to_item_text(self) -> str:
        """Convert to PoE item text format for AI analysis."""
        lines = []
        lines.append(f"Rarity: {self.rarity}")
        if self.name and self.name != self.base_type:
            lines.append(self.name)
        lines.append(self.base_type)
        lines.append("--------")
        if self.item_level:
            lines.append(f"Item Level: {self.item_level}")
        if self.sockets:
            lines.append(f"Sockets: {self.sockets}")
        if self.implicit_mods:
            lines.append("--------")
            for mod in self.implicit_mods:
                lines.append(mod)
        if self.explicit_mods:
            lines.append("--------")
            for mod in self.explicit_mods:
                lines.append(mod)
        if self.corrupted:
            lines.append("--------")
            lines.append("Corrupted")
        return "\n".join(lines)


@dataclass
class TradeSearchSuggestion:
    """Suggested trade search parameters for finding upgrades."""

    slot: str
    description: str  # Human-readable description
    required_stats: List[Dict[str, Any]] = field(default_factory=list)
    min_values: Dict[str, float] = field(default_factory=dict)
    max_price_chaos: float = 0.0
    trade_url: str = ""  # Pre-built trade URL if possible
    priority: int = 1  # 1 = highest priority

    def to_search_description(self) -> str:
        """Generate human-readable search description."""
        parts = [f"Search for {self.slot}:"]
        for stat in self.required_stats:
            stat_name = stat.get("name", "Unknown")
            min_val = stat.get("min", 0)
            parts.append(f"  - {stat_name} >= {min_val}")
        if self.max_price_chaos:
            parts.append(f"  - Max price: {self.max_price_chaos:.0f}c")
        return "\n".join(parts)


@dataclass
class UpgradeRecommendation:
    """A single upgrade recommendation with tier classification."""

    tier: UpgradeTier
    item: Optional[StashUpgradeCandidate]  # None for trade suggestions
    trade_suggestion: Optional[TradeSearchSuggestion]

    # AI analysis
    reason: str  # Why this is recommended
    stat_changes: Dict[str, float] = field(default_factory=dict)  # e.g., {"life": +50, "fire_res": +20}
    dps_change_percent: float = 0.0

    # Comparison to current
    improvements: List[str] = field(default_factory=list)
    downgrades: List[str] = field(default_factory=list)

    @property
    def source(self) -> str:
        """Where this upgrade comes from."""
        if self.item:
            return f"Stash: {self.item.tab_name}"
        elif self.trade_suggestion:
            return "Trade Search"
        return "Unknown"


@dataclass
class SlotUpgradeAnalysis:
    """Complete upgrade analysis for a single equipment slot."""

    slot: str
    current_item: Optional["PoBItem"]
    current_item_text: str = ""

    # Categorized recommendations
    best: Optional[UpgradeRecommendation] = None
    better: List[UpgradeRecommendation] = field(default_factory=list)
    good: List[UpgradeRecommendation] = field(default_factory=list)

    # Trade suggestions for external upgrades
    trade_suggestions: List[TradeSearchSuggestion] = field(default_factory=list)

    # Stash candidates that were analyzed
    stash_candidates_found: int = 0

    # AI reasoning
    ai_summary: str = ""

    @property
    def has_stash_upgrades(self) -> bool:
        """Check if any upgrades were found in stash."""
        return (
            (self.best is not None and self.best.item is not None) or
            any(r.item is not None for r in self.better) or
            any(r.item is not None for r in self.good)
        )


@dataclass
class BuildResearch:
    """Results of researching a build online."""

    build_name: str
    researched_at: datetime = field(default_factory=datetime.now)

    # Sources found
    guide_urls: List[str] = field(default_factory=list)
    video_urls: List[str] = field(default_factory=list)
    pob_codes: List[str] = field(default_factory=list)

    # Extracted information
    key_uniques: List[str] = field(default_factory=list)  # Required unique items
    budget_tiers: Dict[str, str] = field(default_factory=dict)  # e.g., {"starter": "10div", "endgame": "100div"}
    playstyle_notes: str = ""

    # Stat priorities discovered
    stat_priorities: List[str] = field(default_factory=list)

    # AI summary of the build
    ai_summary: str = ""

    def to_context_string(self) -> str:
        """Convert to context string for AI prompts."""
        lines = [f"Build Research: {self.build_name}"]

        if self.key_uniques:
            lines.append(f"Key Uniques: {', '.join(self.key_uniques)}")

        if self.stat_priorities:
            lines.append(f"Stat Priorities: {', '.join(self.stat_priorities)}")

        if self.playstyle_notes:
            lines.append(f"Playstyle: {self.playstyle_notes}")

        if self.budget_tiers:
            budget_str = ", ".join(f"{k}: {v}" for k, v in self.budget_tiers.items())
            lines.append(f"Budget Tiers: {budget_str}")

        return "\n".join(lines)


@dataclass
class UpgradeAdvisorResult:
    """Complete result from the upgrade advisor."""

    profile_name: str
    build_summary: Optional["BuildSummary"]
    build_research: Optional[BuildResearch]

    # Per-slot analysis
    slot_analyses: Dict[str, SlotUpgradeAnalysis] = field(default_factory=dict)

    # Overall recommendations
    top_priorities: List[str] = field(default_factory=list)  # Slots to upgrade first

    # Budget context
    available_budget_chaos: float = 0.0

    # AI overall summary
    ai_overall_summary: str = ""

    def get_best_upgrades(self) -> List[tuple[str, UpgradeRecommendation]]:
        """Get all BEST tier recommendations across slots."""
        results = []
        for slot, analysis in self.slot_analyses.items():
            if analysis.best:
                results.append((slot, analysis.best))
        return results


class AIUpgradeAdvisorService:
    """
    Service for AI-powered gear upgrade recommendations.

    Combines:
    - PoB build data (current gear, stats, priorities)
    - Stash cache (potential upgrades already owned)
    - AI analysis (Good/Better/Best classification)
    - Trade suggestions (external upgrade paths)
    - Web research (build guide knowledge)
    """

    # Equipment slots to analyze
    EQUIPMENT_SLOTS = [
        "Helmet", "Body Armour", "Gloves", "Boots",
        "Belt", "Ring 1", "Ring 2", "Amulet",
        "Weapon 1", "Weapon 2"
    ]

    # Item classes that match equipment slots
    SLOT_TO_ITEM_CLASS = {
        "Helmet": ["Helmet", "Helmets"],
        "Body Armour": ["Body Armour", "Body Armours", "Chest"],
        "Gloves": ["Gloves"],
        "Boots": ["Boots"],
        "Belt": ["Belt", "Belts"],
        "Ring 1": ["Ring", "Rings"],
        "Ring 2": ["Ring", "Rings"],
        "Amulet": ["Amulet", "Amulets"],
        "Weapon 1": ["Weapon", "Bow", "Wand", "Sceptre", "Staff", "Dagger", "Claw", "Sword", "Axe", "Mace"],
        "Weapon 2": ["Shield", "Quiver", "Weapon"],
    }

    def __init__(
        self,
        db: "Database",
        config: "Config",
    ):
        """
        Initialize the upgrade advisor.

        Args:
            db: Database for stash storage access.
            config: Application configuration.
        """
        self._db = db
        self._config = config
        self._build_research_cache: Dict[str, BuildResearch] = {}

    def get_stash_storage(self) -> "StashStorageService":
        """Get the stash storage service."""
        from core.stash_storage import get_stash_storage
        return get_stash_storage(self._db)

    def get_stash_candidates_for_slot(
        self,
        slot: str,
        account_name: str,
        league: str,
    ) -> List[StashUpgradeCandidate]:
        """
        Find items in stash cache that could fit a slot.

        Args:
            slot: Equipment slot to find items for.
            account_name: PoE account name.
            league: League name.

        Returns:
            List of potential upgrade candidates from stash.
        """
        candidates = []

        storage = self.get_stash_storage()
        stored = storage.load_latest_snapshot(account_name, league)

        if not stored:
            logger.info(f"No cached stash found for {account_name}/{league}")
            return candidates

        valuation = storage.reconstruct_valuation(stored)
        if not valuation:
            logger.warning("Could not reconstruct valuation from stored snapshot")
            return candidates

        # Get valid item classes for this slot
        valid_classes = self.SLOT_TO_ITEM_CLASS.get(slot, [])

        # Scan all tabs for matching items
        for tab in valuation.tabs:
            for item in tab.items:
                if self._item_matches_slot(item, slot, valid_classes):
                    candidate = self._priced_item_to_candidate(item, tab.name, tab.index)
                    candidates.append(candidate)

        logger.info(f"Found {len(candidates)} stash candidates for {slot}")
        return candidates

    def _item_matches_slot(
        self,
        item: "PricedItem",
        slot: str,
        valid_classes: List[str],
    ) -> bool:
        """Check if a stash item could fit the given slot."""
        item_class = item.item_class or ""

        # Direct class match
        for valid_class in valid_classes:
            if valid_class.lower() in item_class.lower():
                return True

        # Check base type as fallback
        base_type = item.base_type or ""
        for valid_class in valid_classes:
            if valid_class.lower() in base_type.lower():
                return True

        return False

    def _priced_item_to_candidate(
        self,
        item: "PricedItem",
        tab_name: str,
        tab_index: int,
    ) -> StashUpgradeCandidate:
        """Convert a PricedItem to a StashUpgradeCandidate."""
        # Extract mods from raw item data
        raw = item.raw_item or {}
        implicit_mods = raw.get("implicitMods", [])
        explicit_mods = raw.get("explicitMods", [])

        return StashUpgradeCandidate(
            name=item.name,
            base_type=item.base_type or item.type_line,
            item_class=item.item_class,
            tab_name=tab_name,
            tab_index=tab_index,
            position=(item.x, item.y),
            rarity=item.rarity,
            item_level=item.ilvl,
            links=item.links,
            sockets=item.sockets,
            corrupted=item.corrupted,
            implicit_mods=implicit_mods,
            explicit_mods=explicit_mods,
            chaos_value=item.total_price,
            raw_item=raw,
        )

    def build_upgrade_context(
        self,
        profile: "CharacterProfile",
        slot: str,
        stash_candidates: List[StashUpgradeCandidate],
        build_research: Optional[BuildResearch] = None,
    ) -> str:
        """
        Build comprehensive context string for AI upgrade analysis.

        Args:
            profile: Character profile with build data.
            slot: Equipment slot being analyzed.
            stash_candidates: Potential upgrades from stash.
            build_research: Optional research about the build.

        Returns:
            Formatted context string for AI prompt.
        """
        from core.build_summarizer import BuildSummarizer

        lines = []

        # Build summary
        summarizer = BuildSummarizer()
        summary = summarizer.summarize_profile(profile)
        lines.append("=== BUILD CONTEXT ===")
        lines.append(summary.to_compact_context())
        lines.append("")

        # Current equipped item
        current_item = profile.build.items.get(slot)
        lines.append(f"=== CURRENT {slot.upper()} ===")
        if current_item:
            lines.append(f"Name: {current_item.display_name}")
            lines.append(f"Rarity: {current_item.rarity}")
            if current_item.implicit_mods:
                lines.append("Implicits:")
                for mod in current_item.implicit_mods:
                    lines.append(f"  - {mod}")
            if current_item.explicit_mods:
                lines.append("Explicits:")
                for mod in current_item.explicit_mods:
                    lines.append(f"  - {mod}")
        else:
            lines.append("(Empty slot)")
        lines.append("")

        # Stash candidates
        lines.append(f"=== STASH OPTIONS ({len(stash_candidates)} found) ===")
        for i, candidate in enumerate(stash_candidates[:10], 1):  # Limit to top 10
            lines.append(f"\n--- Option {i}: {candidate.name} ---")
            lines.append(f"Tab: {candidate.tab_name}")
            lines.append(f"Rarity: {candidate.rarity}, iLvl: {candidate.item_level}")
            if candidate.chaos_value > 0:
                lines.append(f"Estimated value: {candidate.chaos_value:.0f}c")
            if candidate.all_mods:
                lines.append("Mods:")
                for mod in candidate.all_mods[:8]:  # Limit mods shown
                    lines.append(f"  - {mod}")

        if not stash_candidates:
            lines.append("(No matching items found in stash)")
        lines.append("")

        # Build research context
        if build_research:
            lines.append("=== BUILD RESEARCH ===")
            lines.append(build_research.to_context_string())
            lines.append("")

        # Stat priorities from build
        if summary.upgrade_priorities:
            lines.append("=== UPGRADE PRIORITIES ===")
            for priority in summary.upgrade_priorities:
                lines.append(f"- {priority}")
            lines.append("")

        return "\n".join(lines)

    def generate_trade_suggestions(
        self,
        profile: "CharacterProfile",
        slot: str,
        budget_chaos: float,
    ) -> List[TradeSearchSuggestion]:
        """
        Generate trade search suggestions based on build needs.

        Args:
            profile: Character profile with build data.
            slot: Equipment slot to suggest trades for.
            budget_chaos: Maximum budget in chaos.

        Returns:
            List of trade search suggestions.
        """
        from core.build_summarizer import BuildSummarizer

        suggestions = []

        # Get build summary for stat priorities
        summarizer = BuildSummarizer()
        summary = summarizer.summarize_profile(profile)

        # Determine what stats to search for based on build and slot
        required_stats = []

        # Life/ES based on defense focus
        if summary.defense_focus in ("Life", "Hybrid", "Armour", "Evasion"):
            required_stats.append({
                "name": "Maximum Life",
                "id": "pseudo.pseudo_total_life",
                "min": 60,
            })

        if summary.defense_focus in ("ES", "Hybrid"):
            required_stats.append({
                "name": "Maximum Energy Shield",
                "id": "pseudo.pseudo_total_energy_shield",
                "min": 40,
            })

        # Resistances if not capped
        if summary.fire_res < 75:
            required_stats.append({
                "name": "Fire Resistance",
                "id": "pseudo.pseudo_total_fire_resistance",
                "min": 30,
            })

        if summary.cold_res < 75:
            required_stats.append({
                "name": "Cold Resistance",
                "id": "pseudo.pseudo_total_cold_resistance",
                "min": 30,
            })

        if summary.lightning_res < 75:
            required_stats.append({
                "name": "Lightning Resistance",
                "id": "pseudo.pseudo_total_lightning_resistance",
                "min": 30,
            })

        # Create primary suggestion
        if required_stats:
            suggestions.append(TradeSearchSuggestion(
                slot=slot,
                description=f"Defensive upgrade for {slot}",
                required_stats=required_stats[:3],  # Top 3 stats
                max_price_chaos=budget_chaos,
                priority=1,
            ))

        # Add DPS-focused suggestion for certain slots
        if slot in ("Weapon 1", "Amulet", "Ring 1", "Ring 2"):
            dps_stats = []
            if summary.playstyle == "Attack":
                dps_stats.append({
                    "name": "Increased Physical Damage",
                    "id": "explicit.stat_physical_damage",
                    "min": 50,
                })
            elif summary.playstyle == "Spell":
                dps_stats.append({
                    "name": "Spell Damage",
                    "id": "pseudo.pseudo_increased_spell_damage",
                    "min": 30,
                })

            if dps_stats:
                suggestions.append(TradeSearchSuggestion(
                    slot=slot,
                    description=f"DPS upgrade for {slot}",
                    required_stats=dps_stats,
                    max_price_chaos=budget_chaos,
                    priority=2,
                ))

        return suggestions

    async def research_build_async(
        self,
        build_name: str,
        guide_url: Optional[str] = None,
        ascendancy: Optional[str] = None,
        main_skill: Optional[str] = None,
    ) -> BuildResearch:
        """
        Research a build online to gather context.

        This performs web searches to find:
        - Build guides
        - Key unique items
        - Stat priorities
        - Budget recommendations

        Args:
            build_name: Name of the build to research.
            guide_url: Optional specific guide URL to fetch.
            ascendancy: Optional ascendancy class.
            main_skill: Optional main skill name.

        Returns:
            BuildResearch with gathered information.
        """
        # Check cache first
        cache_key = f"{build_name}:{ascendancy}:{main_skill}"
        if cache_key in self._build_research_cache:
            cached = self._build_research_cache[cache_key]
            # Check if cache is still fresh (24 hours)
            age = datetime.now() - cached.researched_at
            if age.total_seconds() < 86400:
                logger.info(f"Using cached build research for {build_name}")
                return cached

        research = BuildResearch(build_name=build_name)

        # Build search query
        search_terms = [build_name]
        if ascendancy:
            search_terms.append(ascendancy)
        if main_skill:
            search_terms.append(main_skill)
        search_terms.append("poe build guide")

        search_query = " ".join(search_terms)

        # Note: Actual web search implementation would go here
        # For now, we'll set up the structure for the AI to use
        logger.info(f"Would search for: {search_query}")

        # If a guide URL was provided, we could fetch and parse it
        if guide_url:
            research.guide_urls.append(guide_url)

        # Cache the result
        self._build_research_cache[cache_key] = research

        return research

    def get_upgrade_prompt(
        self,
        profile: "CharacterProfile",
        slot: str,
        stash_candidates: List[StashUpgradeCandidate],
        trade_suggestions: List[TradeSearchSuggestion],
        build_research: Optional[BuildResearch] = None,
    ) -> str:
        """
        Build the complete AI prompt for upgrade analysis.

        Returns a prompt that asks the AI to:
        1. Evaluate stash items as Good/Better/Best
        2. Recommend trade searches
        3. Provide reasoning for recommendations
        """
        context = self.build_upgrade_context(
            profile, slot, stash_candidates, build_research
        )

        # Determine game version from config
        game_version = self._config.current_game
        game_name = game_version.display_name()
        league = self._config.league or "unknown league"

        # Set currency context based on game version
        if game_version.value == "poe2":
            currency_context = """
IMPORTANT - PATH OF EXILE 2 ECONOMY:
- Primary currency: Divine Orbs and Exalted Orbs (both valuable)
- Divine Orbs are the main high-value currency
- Chaos Orbs are common currency for smaller trades
- Do NOT reference Mirror of Kalandra (not in PoE2)
- Crafting uses different methods than PoE1"""
        else:
            currency_context = """
IMPORTANT - PATH OF EXILE 1 ECONOMY:
- Primary currency: Divine Orbs (most valuable trade currency)
- Chaos Orbs are the standard trade currency
- Exalted Orbs are used for crafting, less valuable than Divines
- Mirror of Kalandra exists but extremely rare"""

        prompt = f"""You are analyzing gear upgrades for a {game_name} character.

GAME: {game_name}
LEAGUE: {league}
{currency_context}

{context}

=== TASK ===
Analyze the current {slot} and the stash options. Provide recommendations in this format:

1. **BEST** (if any): The single best upgrade from stash that significantly improves the build.
   - Item name and tab location
   - Key improvements (life, resistances, DPS, etc.)
   - What you'd be giving up vs current gear

2. **BETTER** (0-3): Notable upgrades that are solid improvements.
   - Same format as above

3. **GOOD** (0-3): Minor but positive upgrades worth considering.
   - Same format as above

4. **TRADE RECOMMENDATIONS**: What to search for on trade if stash options are insufficient.
   - Specific stat requirements (e.g., "+70 life, +30% fire res")
   - Budget range in chaos orbs (use {game_name} economy context)
   - Priority order

5. **SUMMARY**: 2-3 sentences on the upgrade path for this slot.

Be practical and specific. Focus on stats that matter for this build type ({profile.build.ascendancy or profile.build.class_name} using {profile.build.main_skill}).
Use appropriate currency references for {game_name}.
"""

        return prompt


# Singleton instance
_advisor_instance: Optional[AIUpgradeAdvisorService] = None


def get_ai_upgrade_advisor(db: "Database", config: "Config") -> AIUpgradeAdvisorService:
    """Get or create the AI upgrade advisor singleton."""
    global _advisor_instance
    if _advisor_instance is None:
        _advisor_instance = AIUpgradeAdvisorService(db, config)
    return _advisor_instance


def reset_ai_upgrade_advisor() -> None:
    """Reset the singleton (for testing)."""
    global _advisor_instance
    _advisor_instance = None
