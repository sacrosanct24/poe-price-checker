"""
Build Archetype Models.

Defines data structures for representing build archetypes used
in cross-build item analysis. Each archetype represents a popular
build type with its stat priorities and requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class BuildCategory(Enum):
    """Categories for organizing build archetypes."""
    ATTACK = "Attack"
    SPELL = "Spell"
    MINION = "Minion"
    DOT = "Damage Over Time"
    TOTEM_TRAP_MINE = "Totem/Trap/Mine"
    AURA_SUPPORT = "Aura/Support"


class DefenseType(Enum):
    """Primary defense mechanisms."""
    LIFE = "Life"
    ENERGY_SHIELD = "Energy Shield"
    HYBRID = "Hybrid"
    LOW_LIFE = "Low Life"
    WARD = "Ward"
    EVASION = "Evasion"
    ARMOUR = "Armour"
    BLOCK = "Block"
    DODGE = "Dodge"


class DamageType(Enum):
    """Primary damage types."""
    PHYSICAL = "Physical"
    FIRE = "Fire"
    COLD = "Cold"
    LIGHTNING = "Lightning"
    CHAOS = "Chaos"
    ELEMENTAL = "Elemental"  # Multi-element


@dataclass
class StatWeight:
    """
    Weight for a specific stat in build evaluation.

    Attributes:
        stat_name: Normalized stat identifier (e.g., "maximum_life", "fire_resistance")
        weight: Importance multiplier (1.0 = normal, 2.0 = very important)
        min_threshold: Minimum value to be considered useful (optional)
        ideal_value: Target value for "perfect" item (optional)
    """
    stat_name: str
    weight: float = 1.0
    min_threshold: Optional[float] = None
    ideal_value: Optional[float] = None


@dataclass
class BuildArchetype:
    """
    Represents a popular build archetype for cross-build analysis.

    Used to determine if an item is valuable for builds the user
    doesn't currently have loaded.

    Attributes:
        id: Unique identifier (e.g., "rf_juggernaut")
        name: Display name (e.g., "RF Juggernaut")
        description: Brief description of the build
        category: Build category (attack, spell, etc.)
        ascendancy: Primary ascendancy class
        damage_types: Primary damage types used
        defense_types: Primary defense mechanisms
        key_stats: List of essential stats with weights
        required_stats: Stats that MUST be present for the item to be useful
        stat_weights: Full dictionary of stat -> weight mappings
        popularity: Estimated percentage of players (0.0-1.0)
        tags: Search/filter tags
        league_starter: Whether this is a good league starter
        ssf_viable: Whether this build works in SSF
        budget_tier: Estimated budget tier (1=budget, 2=mid, 3=high)
        guide_url: Optional link to a build guide
        poe_ninja_id: Optional poe.ninja build identifier
    """
    id: str
    name: str
    description: str = ""
    category: BuildCategory = BuildCategory.ATTACK
    ascendancy: str = ""
    damage_types: List[DamageType] = field(default_factory=list)
    defense_types: List[DefenseType] = field(default_factory=list)
    key_stats: List[StatWeight] = field(default_factory=list)
    required_stats: Set[str] = field(default_factory=set)
    stat_weights: Dict[str, float] = field(default_factory=dict)
    popularity: float = 0.0
    tags: List[str] = field(default_factory=list)
    league_starter: bool = False
    ssf_viable: bool = False
    budget_tier: int = 2
    guide_url: str = ""
    poe_ninja_id: str = ""

    def get_stat_weight(self, stat_name: str) -> float:
        """Get the weight for a specific stat, defaulting to 0 if not relevant."""
        # Check key_stats first
        for key_stat in self.key_stats:
            if key_stat.stat_name == stat_name:
                return key_stat.weight

        # Fall back to stat_weights dict
        return self.stat_weights.get(stat_name, 0.0)

    def is_stat_required(self, stat_name: str) -> bool:
        """Check if a stat is required for this build."""
        return stat_name in self.required_stats

    def matches_tags(self, tags: List[str]) -> bool:
        """Check if this archetype matches any of the given tags."""
        return bool(set(self.tags) & set(tags))


@dataclass
class ArchetypeMatch:
    """
    Result of matching an item against a build archetype.

    Attributes:
        archetype: The matched build archetype
        score: Match score (0-100)
        matching_stats: Stats that contributed positively
        missing_required: Required stats that are missing
        reasons: Human-readable reasons for the match
    """
    archetype: BuildArchetype
    score: float
    matching_stats: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    @property
    def is_good_match(self) -> bool:
        """Check if this is a good match (score >= 60)."""
        return self.score >= 60.0 and not self.missing_required

    @property
    def is_excellent_match(self) -> bool:
        """Check if this is an excellent match (score >= 80)."""
        return self.score >= 80.0 and not self.missing_required


@dataclass
class CrossBuildAnalysis:
    """
    Complete analysis of an item across all build archetypes.

    Attributes:
        item_name: Name of the analyzed item
        matches: List of archetype matches, sorted by score
        best_match: The highest-scoring match
        good_for_builds: Number of builds this item is good for
        universal_appeal: Whether this item is good for many builds
    """
    item_name: str
    matches: List[ArchetypeMatch] = field(default_factory=list)

    @property
    def best_match(self) -> Optional[ArchetypeMatch]:
        """Get the best matching archetype."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.score)

    @property
    def good_matches(self) -> List[ArchetypeMatch]:
        """Get all good matches (score >= 60)."""
        return [m for m in self.matches if m.is_good_match]

    @property
    def excellent_matches(self) -> List[ArchetypeMatch]:
        """Get all excellent matches (score >= 80)."""
        return [m for m in self.matches if m.is_excellent_match]

    @property
    def good_for_builds(self) -> int:
        """Count of builds this item is good for."""
        return len(self.good_matches)

    @property
    def universal_appeal(self) -> bool:
        """Check if item is good for 5+ different builds."""
        return self.good_for_builds >= 5

    def get_top_matches(self, limit: int = 3) -> List[ArchetypeMatch]:
        """Get the top N matches by score."""
        sorted_matches = sorted(self.matches, key=lambda m: m.score, reverse=True)
        return sorted_matches[:limit]

    def get_summary(self) -> str:
        """Generate a human-readable summary."""
        if not self.matches:
            return "No build matches found"

        best = self.best_match
        if best is None:
            return "No build matches found"

        if best.score < 40:
            return "Niche item - limited build appeal"

        good_count = self.good_for_builds
        if good_count == 0:
            return f"Best match: {best.archetype.name} ({best.score:.0f}%)"

        if self.universal_appeal:
            return f"Universal item - good for {good_count}+ builds"

        top_names = [m.archetype.name for m in self.get_top_matches(3)]
        return f"Good for: {', '.join(top_names)}"
