"""
Unique item evaluation data models.

Contains dataclasses for representing unique item evaluation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from core.item_parser import ParsedItem


@dataclass
class CorruptionMatch:
    """Represents a matched corruption implicit on a unique item."""

    corruption_type: str  # "implicit_override", "keystone", "socket", "brick"
    mod_text: str  # The actual mod text
    tier: str  # "excellent", "high", "good", "niche", "brick"
    weight: int  # Scoring weight
    applies_to_slot: bool = True  # Whether this corruption is relevant for the slot


@dataclass
class LinkEvaluation:
    """Socket and link evaluation results."""

    total_sockets: int
    links: int  # Largest linked group
    white_sockets: int
    link_multiplier: float  # Price multiplier (e.g., 2.5 for 6L)
    socket_bonus: int  # Bonus score from sockets


@dataclass
class MetaRelevance:
    """Build meta relevance scoring."""

    builds_using: List[str] = field(default_factory=list)  # Build names using this unique
    total_usage_percent: float = 0.0  # Sum of usage across all builds
    highest_tier_build: str = "D"  # Highest tier build using this (S, A, B, C, D)
    is_trending: bool = False  # Whether the item is trending up
    trend_direction: str = "stable"  # "rising", "stable", "falling"
    meta_score: int = 0  # 0-100 meta relevance score


@dataclass
class UniqueItemEvaluation:
    """Complete evaluation result for a unique item."""

    item: "ParsedItem"

    # Basic info
    unique_name: str
    base_type: str
    slot_category: str

    # Pricing from poe.ninja
    ninja_price_chaos: Optional[float] = None
    ninja_price_divine: Optional[float] = None
    has_poe_ninja_price: bool = False

    # Corruption analysis
    is_corrupted: bool = False
    corruption_matches: List[CorruptionMatch] = field(default_factory=list)
    corruption_tier: str = "none"  # "excellent", "high", "good", "neutral", "bricked"
    corruption_value_modifier: float = 1.0  # Multiplier (0.3 for bricked, up to 5x for +gems)

    # Link/socket evaluation
    link_evaluation: Optional[LinkEvaluation] = None

    # Meta relevance
    meta_relevance: Optional[MetaRelevance] = None

    # Component scores (0-100 each)
    base_score: int = 0  # From poe.ninja price or fallback
    corruption_score: int = 0  # From corruption analysis
    link_score: int = 0  # From socket/link evaluation
    meta_score: int = 0  # From build relevance

    # Final combined score
    total_score: int = 0

    # Tier and value determination
    tier: str = "unknown"  # "chase", "excellent", "good", "average", "vendor"
    estimated_value: str = "Unknown"
    confidence: str = "unknown"  # "exact", "estimated", "fallback"

    # WHY factors - human readable explanations
    factors: List[str] = field(default_factory=list)

    # Warnings for user
    warnings: List[str] = field(default_factory=list)

    # Is this a chase unique?
    is_chase_unique: bool = False
