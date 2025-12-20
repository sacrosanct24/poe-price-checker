"""
Cluster jewel evaluation data models.

Contains dataclasses for representing cluster jewel evaluation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from core.item_parser import ParsedItem


@dataclass
class NotableMatch:
    """Represents a matched notable on a cluster jewel."""

    name: str
    weight: int
    tier: str  # "meta", "high", "medium", "low"
    description: str = ""
    skill_type: str = ""
    has_synergy: bool = False
    synergy_bonus: int = 0


@dataclass
class ClusterJewelEvaluation:
    """Results of cluster jewel evaluation."""

    item: "ParsedItem"

    # Size and structure
    size: str  # "Small", "Medium", "Large"
    passive_count: int
    jewel_sockets: int

    # Enchantment
    enchantment_type: str
    enchantment_display: str = ""
    enchantment_score: int = 0  # 0-100

    # Notables
    matched_notables: List[NotableMatch] = field(default_factory=list)
    notable_score: int = 0  # 0-100

    # Synergies
    synergies_found: List[str] = field(default_factory=list)
    synergy_bonus: int = 0

    # ilvl scoring
    ilvl_score: int = 0

    # Open affix potential
    has_open_suffix: bool = False
    crafting_potential: int = 0

    # Final scores
    total_score: int = 0
    tier: str = "vendor"  # "excellent", "good", "average", "vendor"
    estimated_value: str = "<10c"

    # Explanation factors (for UI "WHY" section)
    factors: List[str] = field(default_factory=list)
