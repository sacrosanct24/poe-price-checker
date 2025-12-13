"""
Build Archetype Models

Dataclasses defining build archetypes and match results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class BuildCategory(Enum):
    """Categories of build archetypes."""
    ATTACK = "attack"
    SPELL = "spell"
    MINION = "minion"
    DOT = "dot"  # Damage over time
    TOTEM_TRAP_MINE = "totem_trap_mine"
    AURA_SUPPORT = "aura_support"


# Alias for backward compatibility
ArchetypeCategory = BuildCategory


class DamageType(Enum):
    """Primary damage types."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"
    ELEMENTAL = "elemental"  # Mixed elemental


class DefenseType(Enum):
    """Primary defense mechanisms."""
    LIFE = "life"
    ENERGY_SHIELD = "energy_shield"
    HYBRID = "hybrid"  # Life + ES
    EVASION = "evasion"
    ARMOUR = "armour"
    BLOCK = "block"
    DODGE = "dodge"
    MOM = "mind_over_matter"
    LOW_LIFE = "low_life"


@dataclass
class StatWeight:
    """A weighted stat for a build archetype."""
    stat_name: str
    weight: float = 1.0
    min_threshold: Optional[float] = None  # Minimum value to be useful
    ideal_value: Optional[float] = None  # Ideal value for max scoring


@dataclass
class StatRequirement:
    """A stat requirement for a build archetype."""
    stat_type: str  # e.g., "life", "fire_resistance", "spell_damage"
    weight: float = 1.0  # How important (0.5 = nice to have, 2.0 = critical)
    min_value: Optional[int] = None  # Minimum value to be useful
    ideal_value: Optional[int] = None  # Ideal value for scoring


@dataclass
class BuildArchetype:
    """
    Defines a build archetype for cross-build item matching.

    Archetypes represent common/meta builds and their stat priorities,
    allowing items to be scored against builds the user may not have.
    """
    # Identity
    id: str  # e.g., "rf_juggernaut"
    name: str  # e.g., "RF Juggernaut"
    description: str  # Brief description

    # Classification
    category: BuildCategory
    ascendancy: str  # e.g., "Juggernaut", "Necromancer"
    damage_types: List[DamageType] = field(default_factory=list)
    defense_types: List[DefenseType] = field(default_factory=list)

    # Stat priorities
    key_stats: List[StatWeight] = field(default_factory=list)  # Primary stats with weights
    stat_weights: Dict[str, float] = field(default_factory=dict)  # Additional stat weights
    required_stats: Set[str] = field(default_factory=set)  # Must-have stats

    # Metadata
    popularity: float = 0.05  # Fraction of players (0.05 = 5%)
    tags: List[str] = field(default_factory=list)  # ["tanky", "league_starter", "boss_killer"]
    league_starter: bool = False  # Good for league start
    ssf_viable: bool = False  # Viable in SSF
    budget_tier: int = 2  # 1=budget, 2=mid, 3=expensive
    poe_version: str = "poe1"  # "poe1" or "poe2"

    def get_stat_weight(self, stat: str) -> float:
        """Get the weight for a stat, defaulting to 0 if not relevant."""
        # First check key_stats
        for key_stat in self.key_stats:
            if key_stat.stat_name == stat:
                return key_stat.weight
        # Then check stat_weights dict
        return self.stat_weights.get(stat, 0.0)

    def is_key_stat(self, stat: str) -> bool:
        """Check if a stat is a key stat for this archetype."""
        return any(ks.stat_name == stat for ks in self.key_stats)


@dataclass
class ArchetypeMatch:
    """Result of matching an item against an archetype."""
    archetype: BuildArchetype
    score: float  # 0-100 match score
    matching_stats: List[str] = field(default_factory=list)  # Stats found on item
    missing_required: List[str] = field(default_factory=list)  # Required stats missing
    reasons: List[str] = field(default_factory=list)  # Why this is a good match

    @property
    def is_strong_match(self) -> bool:
        """Check if this is a strong match (>= 70%)."""
        return self.score >= 70

    @property
    def is_moderate_match(self) -> bool:
        """Check if this is a moderate match (50-69%)."""
        return 50 <= self.score < 70

    @property
    def match_summary(self) -> str:
        """Get a brief summary of the match."""
        if self.score >= 90:
            return "Excellent"
        elif self.score >= 70:
            return "Strong"
        elif self.score >= 50:
            return "Moderate"
        elif self.score >= 30:
            return "Weak"
        return "Poor"


@dataclass
class CrossBuildAnalysis:
    """Analysis of an item against all build archetypes."""
    item_name: str
    matches: List[ArchetypeMatch] = field(default_factory=list)

    @property
    def best_match(self) -> Optional[ArchetypeMatch]:
        """Get the best matching archetype."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.score)

    @property
    def strong_matches(self) -> List[ArchetypeMatch]:
        """Get all strong matches (>= 70% score)."""
        return [m for m in self.matches if m.score >= 70]

    @property
    def moderate_matches(self) -> List[ArchetypeMatch]:
        """Get all moderate matches (50-69% score)."""
        return [m for m in self.matches if 50 <= m.score < 70]

    def get_top_matches(self, n: int = 3) -> List[ArchetypeMatch]:
        """Get top N matches by score."""
        sorted_matches = sorted(self.matches, key=lambda m: m.score, reverse=True)
        return sorted_matches[:n]

    @property
    def summary(self) -> str:
        """Get a summary of the analysis."""
        strong = len(self.strong_matches)
        moderate = len(self.moderate_matches)
        if strong > 0:
            best = self.best_match
            return f"Strong fit for {strong} builds (best: {best.archetype.name} {best.score:.0f}%)"
        elif moderate > 0:
            return f"Moderate fit for {moderate} builds"
        return "No strong build matches"
