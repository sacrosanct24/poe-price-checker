"""
Data models for price rankings.

Contains dataclasses for ranked items and category rankings.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class RankedItem:
    """A single ranked item with price information."""
    rank: int
    name: str
    chaos_value: float
    divine_value: Optional[float] = None
    base_type: Optional[str] = None
    icon: Optional[str] = None

    # For uniques, track the item type
    item_class: Optional[str] = None

    # Item rarity for display coloring (unique, rare, magic, normal, currency, divination)
    rarity: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RankedItem":
        """Create from dictionary."""
        return cls(
            rank=data.get("rank", 0),
            name=data.get("name", ""),
            chaos_value=data.get("chaos_value", 0.0),
            divine_value=data.get("divine_value"),
            base_type=data.get("base_type"),
            icon=data.get("icon"),
            item_class=data.get("item_class"),
            rarity=data.get("rarity"),
        )


@dataclass
class CategoryRanking:
    """Rankings for a single category."""
    category: str
    display_name: str
    items: List[RankedItem] = field(default_factory=list)
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "display_name": self.display_name,
            "items": [item.to_dict() for item in self.items],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CategoryRanking":
        """Create from dictionary."""
        return cls(
            category=data.get("category", ""),
            display_name=data.get("display_name", ""),
            items=[RankedItem.from_dict(item) for item in data.get("items", [])],
            updated_at=data.get("updated_at"),
        )
