"""
Rare Item Evaluation Models.

Data structures for rare item evaluation results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.item_parser import ParsedItem
    from core.build_archetype import BuildArchetype
    from core.build_archetypes.archetype_models import ArchetypeMatch


@dataclass
class AffixMatch:
    """Represents a matched valuable affix on an item."""
    affix_type: str  # e.g., "life", "resistances"
    pattern: str     # Pattern that matched
    mod_text: str    # Actual mod text from item
    value: Optional[float]  # Extracted numeric value
    weight: int      # Importance weight (1-10)
    tier: str        # "tier1", "tier2", "tier3"
    is_influence_mod: bool = False  # True if from influence
    has_meta_bonus: bool = False  # True if weight includes meta bonus


@dataclass
class RareItemEvaluation:
    """Results of rare item evaluation."""
    item: "ParsedItem"
    base_score: int  # 0-100 based on base type and ilvl
    affix_score: int  # 0-100 based on valuable affixes
    synergy_bonus: int  # Bonus from mod combinations
    red_flag_penalty: int  # Penalty from anti-synergies
    total_score: int  # Combined score

    is_valuable_base: bool
    has_high_ilvl: bool
    matched_affixes: List[AffixMatch]

    # Categorization
    tier: str  # "excellent", "good", "average", "vendor"
    estimated_value: str  # "10c+", "50c+", "1div+", etc.

    # Fields with defaults must come last
    synergies_found: List[str] = field(default_factory=list)
    red_flags_found: List[str] = field(default_factory=list)

    # Slot-specific bonuses (Phase 1.3)
    slot_bonus: int = 0  # Bonus from slot-specific rules
    slot_bonus_reasons: List[str] = field(default_factory=list)

    # Crafting potential (Phase 1.3)
    open_prefixes: int = 0  # Estimated open prefix slots
    open_suffixes: int = 0  # Estimated open suffix slots
    crafting_bonus: int = 0  # Bonus for crafting potential

    # Fractured items (Phase 1.3)
    is_fractured: bool = False
    fractured_bonus: int = 0  # Bonus for fractured T1 mods
    fractured_mod: Optional[str] = None  # The fractured mod if detected

    # Build archetype matching (Phase 2)
    matched_archetypes: List[str] = field(default_factory=list)
    archetype_bonus: int = 0  # Bonus for fitting meta archetypes
    meta_bonus: int = 0  # Bonus from current meta popularity

    # Build matching (if provided)
    matches_build: bool = False
    build_name: Optional[str] = None
    matching_requirements: List[str] = field(default_factory=list)

    # Build archetype context (Phase 2 - PoB integration)
    build_archetype: Optional["BuildArchetype"] = None
    archetype_weighted_score: int = 0  # Score adjusted by archetype weights
    archetype_affix_details: List[Dict[str, Any]] = field(default_factory=list)

    # Cross-build analysis (Phase 2 - What builds want this?)
    cross_build_matches: List["ArchetypeMatch"] = field(default_factory=list)
    cross_build_appeal: int = 0  # Number of builds this is good for
    cross_build_summary: str = ""  # Human-readable summary

    # Cluster jewel evaluation (stored for UI access)
    _cluster_evaluation: Optional[Any] = None  # ClusterJewelEvaluation if cluster jewel

    # Unique item evaluation (stored for UI access)
    _unique_evaluation: Optional[Any] = None  # UniqueItemEvaluation if unique item
