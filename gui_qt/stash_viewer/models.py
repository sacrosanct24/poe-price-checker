"""
Table models for stash viewer.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget

from gui_qt.styles import COLORS
from core.stash_valuator import PricedItem, PriceSource
from core.quick_verdict import QuickVerdictCalculator, Verdict, VerdictResult


class ItemTableModel(QAbstractTableModel):
    """Table model for priced items."""

    COLUMNS = [
        ("verdict", "📊", 45),  # Verdict emoji column
        ("display_name", "Item", 250),
        ("stack_size", "Qty", 50),
        ("unit_price", "Unit", 70),
        ("total_price", "Total", 80),
        ("rarity", "Rarity", 80),
        ("price_source", "Source", 80),
    ]

    # Verdict colors
    VERDICT_COLORS = {
        Verdict.KEEP: QColor("#22bb22"),    # Green
        Verdict.VENDOR: QColor("#bb2222"),  # Red
        Verdict.MAYBE: QColor("#bbbb22"),   # Yellow
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._items: List[PricedItem] = []
        self._min_value: float = 0.0
        self._search_text: str = ""
        self._verdict_calculator = QuickVerdictCalculator()
        self._verdict_cache: Dict[tuple, VerdictResult] = {}  # Cache verdicts by item id

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._filtered_items())

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def _filtered_items(self) -> List[PricedItem]:
        """Get items filtered by minimum value and search text."""
        items = [i for i in self._items if i.total_price >= self._min_value]
        if self._search_text:
            search_lower = self._search_text.lower()
            items = [i for i in items if search_lower in i.display_name.lower()]
        return items

    def _get_verdict(self, item: PricedItem) -> VerdictResult:
        """Get verdict for an item, using cache if available."""
        # Create a cache key from item identity
        cache_key = (item.name, item.type_line, item.tab_name, item.stack_size)
        if cache_key in self._verdict_cache:
            return self._verdict_cache[cache_key]

        # For items evaluated by RareItemEvaluator, use their eval_tier directly
        # This ensures consistency between the two evaluation systems
        if item.price_source == PriceSource.RARE_EVALUATED and item.eval_tier:
            tier = item.eval_tier.lower()
            if tier == "excellent":
                verdict = VerdictResult(
                    verdict=Verdict.KEEP,
                    explanation="Excellent rare - high-value affixes",
                    detailed_reasons=[item.eval_summary] if item.eval_summary else [],
                    estimated_value=item.total_price if item.total_price > 0 else None,
                    confidence="high",
                )
            elif tier == "good":
                verdict = VerdictResult(
                    verdict=Verdict.MAYBE,
                    explanation="Good rare - worth checking",
                    detailed_reasons=[item.eval_summary] if item.eval_summary else [],
                    estimated_value=item.total_price if item.total_price > 0 else None,
                    confidence="medium",
                )
            else:  # average, vendor, etc.
                verdict = VerdictResult(
                    verdict=Verdict.VENDOR,
                    explanation=f"Rare evaluated as {tier}",
                    detailed_reasons=[item.eval_summary] if item.eval_summary else [],
                    estimated_value=item.total_price if item.total_price > 0 else None,
                    confidence="medium",
                )
            self._verdict_cache[cache_key] = verdict
            return verdict

        # Create a simple object for the calculator
        class ItemAdapter:
            """Adapter to make PricedItem work with QuickVerdictCalculator."""
            def __init__(self, priced_item: PricedItem):
                self.rarity = priced_item.rarity
                self.name = priced_item.name
                self.base_type = priced_item.base_type
                self.item_class = priced_item.item_class
                self.sockets = len(priced_item.sockets.replace("-", "").replace(" ", ""))
                self.links = priced_item.links
                self.item_level = priced_item.ilvl
                self.corrupted = priced_item.corrupted

                # Extract from raw_item if available
                raw = priced_item.raw_item or {}
                self.explicits = raw.get("explicitMods", [])
                self.implicits = raw.get("implicitMods", [])
                self.influences = list(raw.get("influences", {}).keys()) if raw.get("influences") else []
                self.is_fractured = raw.get("fractured", False)
                self.is_synthesised = raw.get("synthesised", False)

        adapter = ItemAdapter(item)
        # Use total_price as chaos value if available
        price = item.total_price if item.total_price > 0 else None
        verdict = self._verdict_calculator.calculate(adapter, price_chaos=price)

        self._verdict_cache[cache_key] = verdict
        return verdict

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        items = self._filtered_items()
        if not index.isValid() or not (0 <= index.row() < len(items)):
            return None

        item = items[index.row()]
        col_key = self.COLUMNS[index.column()][0]

        if role == Qt.ItemDataRole.DisplayRole:
            if col_key == "verdict":
                verdict = self._get_verdict(item)
                return verdict.emoji
            elif col_key == "display_name":
                return item.display_name
            elif col_key == "stack_size":
                return str(item.stack_size) if item.stack_size > 1 else ""
            elif col_key == "unit_price":
                if item.unit_price >= 1:
                    return f"{item.unit_price:.1f}c"
                elif item.unit_price > 0:
                    return f"{item.unit_price:.2f}c"
                return ""
            elif col_key == "total_price":
                return item.display_price
            elif col_key == "rarity":
                return item.rarity
            elif col_key == "price_source":
                if item.price_source == PriceSource.POE_NINJA:
                    return "poe.ninja"
                elif item.price_source == PriceSource.POE_PRICES:
                    return "poeprices"
                elif item.price_source == PriceSource.RARE_EVALUATED:
                    return "eval"
                return ""
            return ""

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_key == "verdict":
                verdict = self._get_verdict(item)
                tooltip = f"{verdict.verdict.value.upper()}: {verdict.explanation}"
                if verdict.detailed_reasons:
                    tooltip += "\n\n" + "\n".join(f"• {r}" for r in verdict.detailed_reasons[:5])
                if verdict.has_meta_bonus:
                    tooltip += f"\n\n🔥 Meta bonus: +{verdict.meta_bonus_applied:.0f}"
                return tooltip
            return None

        elif role == Qt.ItemDataRole.ForegroundRole:
            # Color verdict column by verdict type
            if col_key == "verdict":
                verdict = self._get_verdict(item)
                return self.VERDICT_COLORS.get(verdict.verdict, QColor(COLORS["text"]))
            # Color by rarity
            rarity_colors = {
                "Unique": QColor(COLORS["unique"]),
                "Rare": QColor(COLORS["rare"]),
                "Magic": QColor(COLORS["magic"]),
                "Currency": QColor(COLORS["currency"]),
                "Gem": QColor(COLORS["gem"]),
                "Divination": QColor(COLORS["divination"]),
            }
            if col_key == "display_name":
                return rarity_colors.get(item.rarity, QColor(COLORS["text"]))
            # Color by value
            if col_key == "total_price":
                if item.total_price >= 100:
                    return QColor(COLORS["high_value"])
                elif item.total_price >= 10:
                    return QColor(COLORS["medium_value"])
            return None

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key == "verdict":
                return Qt.AlignmentFlag.AlignCenter
            if col_key in ("stack_size", "unit_price", "total_price"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.COLUMNS[section][1]
        return None

    def set_items(self, items: List[PricedItem]) -> None:
        """Set items to display."""
        self.beginResetModel()
        self._items = items
        self._verdict_cache.clear()  # Clear cache when items change
        self.endResetModel()

    def set_meta_weights(self, meta_weights: dict) -> None:
        """Set meta weights for verdict calculation."""
        self._verdict_calculator.set_meta_weights(meta_weights)
        self._verdict_cache.clear()  # Clear cache to recalculate with new weights
        # Refresh display
        self.beginResetModel()
        self.endResetModel()

    def set_verdict_thresholds(self, vendor: float, keep: float) -> None:
        """Set verdict thresholds for calculation."""
        self._verdict_calculator.set_thresholds_from_values(vendor, keep)
        self._verdict_cache.clear()  # Clear cache to recalculate with new thresholds
        # Refresh display
        self.beginResetModel()
        self.endResetModel()

    def set_min_value(self, min_value: float) -> None:
        """Set minimum value filter."""
        self.beginResetModel()
        self._min_value = min_value
        self.endResetModel()

    def set_search_text(self, text: str) -> None:
        """Set search text filter."""
        self.beginResetModel()
        self._search_text = text.strip()
        self.endResetModel()

    def get_item(self, row: int) -> Optional[PricedItem]:
        """Get item at row."""
        items = self._filtered_items()
        if 0 <= row < len(items):
            return items[row]
        return None
