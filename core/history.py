"""
History management for price-checked items.

Provides type-safe HistoryEntry dataclass for tracking checked items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.item_parser import ParsedItem


@dataclass
class HistoryEntry:
    """A single price check history entry.

    Attributes:
        timestamp: When the item was checked (ISO format string).
        item_name: Display name for the item (truncated if needed).
        item_text: Full item text for re-checking.
        results_count: Number of price results found.
        best_price: Highest chaos value found.
        parsed_item: Reference to the ParsedItem (optional).
    """

    timestamp: str
    item_name: str
    item_text: str
    results_count: int = 0
    best_price: float = 0.0
    parsed_item: Optional[Any] = field(default=None, repr=False)

    @classmethod
    def from_price_check(
        cls,
        item_text: str,
        parsed: "ParsedItem",
        results: List[Dict[str, Any]],
    ) -> "HistoryEntry":
        """Create a history entry from a price check result.

        Args:
            item_text: Raw item text that was checked.
            parsed: The parsed item object.
            results: List of price results from the check.

        Returns:
            A new HistoryEntry instance.
        """
        best_price = 0.0
        if results:
            def safe_float(val) -> float:
                """Convert value to float safely."""
                if val is None:
                    return 0.0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0

            best_price = max(
                safe_float(r.get("chaos_value", 0)) for r in results
            )

        return cls(
            timestamp=datetime.now().isoformat(),
            item_name=parsed.name or item_text[:50],
            item_text=item_text,
            results_count=len(results),
            best_price=best_price,
            parsed_item=parsed,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for backward compatibility.

        Returns:
            Dictionary with keys matching the legacy format.
        """
        return {
            "timestamp": self.timestamp,
            "item_name": self.item_name,
            "item_text": self.item_text,
            "results_count": self.results_count,
            "best_price": self.best_price,
            "_parsed": self.parsed_item,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like access for backward compatibility.

        Args:
            key: The attribute name to access.
            default: Default value if key not found.

        Returns:
            The attribute value or default.
        """
        # Map dict keys to dataclass attributes
        key_map = {
            "_parsed": "parsed_item",
        }
        attr_name = key_map.get(key, key)

        if hasattr(self, attr_name):
            return getattr(self, attr_name)
        return default
