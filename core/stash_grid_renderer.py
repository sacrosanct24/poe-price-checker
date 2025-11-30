"""
Stash Grid Renderer.

Converts stash tab data into a grid layout for visualization.
Handles item positioning, multi-cell items, and heatmap color mapping.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.stash_valuator import PricedItem, PricedTab

logger = logging.getLogger(__name__)


# Standard stash dimensions
STANDARD_STASH_WIDTH = 12
STANDARD_STASH_HEIGHT = 12

# Tab type dimensions
TAB_DIMENSIONS = {
    "NormalStash": (12, 12),
    "PremiumStash": (12, 12),
    "QuadStash": (24, 24),
    "CurrencyStash": (12, 12),  # Actually specialized layout
    "MapStash": (12, 12),  # Actually specialized layout
    "FragmentStash": (12, 12),
    "DivinationCardStash": (12, 12),
    "EssenceStash": (12, 12),
    "UniqueStash": (12, 12),
    "DelveStash": (12, 12),
    "BlightStash": (12, 12),
    "MetamorphStash": (12, 12),
    "DeliriumStash": (12, 12),
    "GemStash": (12, 12),
    "FlaskStash": (12, 12),
}

# Value thresholds for heatmap (in chaos)
VALUE_THRESHOLDS = {
    "vendor": 1,       # < 1c
    "low": 5,          # 1-5c
    "medium": 50,      # 5-50c
    "high": 200,       # 50-200c
    "very_high": 1000, # 200-1000c
    # > 1000c = exceptional
}


@dataclass
class StashGridCell:
    """Represents a single cell in the stash grid."""
    x: int
    y: int
    width: int = 1
    height: int = 1
    item: Optional["PricedItem"] = None
    color: str = "#333333"
    border_color: str = "#555555"
    value_tier: str = "empty"
    tooltip: str = ""

    @property
    def is_empty(self) -> bool:
        """Check if cell is empty."""
        return self.item is None

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get cell bounds as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)


@dataclass
class StashGridLayout:
    """Complete grid layout for a stash tab."""
    tab_name: str
    tab_type: str
    width: int = STANDARD_STASH_WIDTH
    height: int = STANDARD_STASH_HEIGHT
    cells: List[StashGridCell] = field(default_factory=list)
    total_value: float = 0.0
    item_count: int = 0

    # Occupancy grid for collision detection
    _occupancy: Dict[Tuple[int, int], StashGridCell] = field(
        default_factory=dict, repr=False
    )

    def add_cell(self, cell: StashGridCell) -> None:
        """Add a cell to the grid."""
        self.cells.append(cell)
        # Mark all occupied positions
        for dx in range(cell.width):
            for dy in range(cell.height):
                self._occupancy[(cell.x + dx, cell.y + dy)] = cell

    def get_cell_at(self, x: int, y: int) -> Optional[StashGridCell]:
        """Get the cell at a specific position."""
        return self._occupancy.get((x, y))

    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a position is occupied."""
        return (x, y) in self._occupancy


class StashGridRenderer:
    """
    Renders stash tab data into a grid layout.

    Converts PricedTab items into StashGridCells with appropriate
    colors based on value heatmap.
    """

    # Heatmap colors (dark theme)
    HEATMAP_COLORS = {
        "empty": "#1a1a1a",
        "vendor": "#2a2a2a",
        "low": "#444444",
        "medium": "#7a7a22",
        "high": "#227722",
        "very_high": "#aa5500",
        "exceptional": "#cc2222",
    }

    # Heatmap colors (colorblind-safe)
    HEATMAP_COLORS_COLORBLIND = {
        "empty": "#1a1a1a",
        "vendor": "#3a3a3a",
        "low": "#666666",
        "medium": "#e69f00",
        "high": "#0072b2",
        "very_high": "#d55e00",
        "exceptional": "#cc79a7",
    }

    # Rarity border colors
    RARITY_COLORS = {
        "unique": "#af6025",
        "rare": "#ffff77",
        "magic": "#8888ff",
        "normal": "#c8c8c8",
        "gem": "#1ba29b",
        "currency": "#aa9e82",
        "divination card": "#0ebaff",
    }

    def __init__(self, colorblind_mode: bool = False):
        """
        Initialize renderer.

        Args:
            colorblind_mode: Use colorblind-safe colors
        """
        self.colorblind_mode = colorblind_mode
        self._colors = (
            self.HEATMAP_COLORS_COLORBLIND if colorblind_mode
            else self.HEATMAP_COLORS
        )

    def render_tab(self, priced_tab: "PricedTab") -> StashGridLayout:
        """
        Convert a priced tab into a grid layout.

        Args:
            priced_tab: Tab with priced items

        Returns:
            StashGridLayout with positioned cells
        """
        # Determine grid dimensions
        tab_type = getattr(priced_tab, "type", "NormalStash")
        width, height = TAB_DIMENSIONS.get(tab_type, (12, 12))

        layout = StashGridLayout(
            tab_name=priced_tab.name,
            tab_type=tab_type,
            width=width,
            height=height,
        )

        total_value = 0.0
        item_count = 0

        for item in priced_tab.items:
            cell = self._create_cell(item)
            layout.add_cell(cell)
            total_value += item.total_price
            item_count += 1

        layout.total_value = total_value
        layout.item_count = item_count

        logger.debug(
            f"Rendered tab '{priced_tab.name}': {item_count} items, "
            f"{total_value:.0f}c total value"
        )

        return layout

    def _create_cell(self, item: "PricedItem") -> StashGridCell:
        """Create a grid cell from a priced item."""
        # Get position (default to 0,0 if not available)
        x = getattr(item, "x", 0)
        y = getattr(item, "y", 0)

        # Get item dimensions (default to 1x1)
        width = getattr(item, "width", 1) or 1
        height = getattr(item, "height", 1) or 1

        # Calculate value tier and color
        value_tier = self._get_value_tier(item.total_price)
        color = self._colors[value_tier]

        # Get border color from rarity
        rarity = getattr(item, "rarity", "normal").lower()
        border_color = self.RARITY_COLORS.get(rarity, "#555555")

        # Generate tooltip
        tooltip = self._generate_tooltip(item)

        return StashGridCell(
            x=x,
            y=y,
            width=width,
            height=height,
            item=item,
            color=color,
            border_color=border_color,
            value_tier=value_tier,
            tooltip=tooltip,
        )

    def _get_value_tier(self, value: float) -> str:
        """Determine value tier from chaos value."""
        if value < VALUE_THRESHOLDS["vendor"]:
            return "vendor"
        elif value < VALUE_THRESHOLDS["low"]:
            return "low"
        elif value < VALUE_THRESHOLDS["medium"]:
            return "medium"
        elif value < VALUE_THRESHOLDS["high"]:
            return "high"
        elif value < VALUE_THRESHOLDS["very_high"]:
            return "very_high"
        else:
            return "exceptional"

    def _generate_tooltip(self, item: "PricedItem") -> str:
        """Generate tooltip text for an item."""
        lines = []

        # Item name
        name = getattr(item, "name", "") or ""
        type_line = getattr(item, "type_line", "") or ""
        if name and name != type_line:
            lines.append(f"{name}")
            lines.append(f"{type_line}")
        else:
            lines.append(type_line or name or "Unknown")

        # Price
        unit_price = getattr(item, "unit_price", 0)
        total_price = getattr(item, "total_price", 0)
        stack_size = getattr(item, "stack_size", 1)

        if stack_size > 1:
            lines.append(f"Stack: {stack_size}")
            lines.append(f"Unit: {unit_price:.1f}c")
            lines.append(f"Total: {total_price:.1f}c")
        else:
            lines.append(f"Value: {total_price:.1f}c")

        # Rarity
        rarity = getattr(item, "rarity", "")
        if rarity:
            lines.append(f"Rarity: {rarity}")

        return "\n".join(lines)

    def get_value_statistics(
        self,
        layout: StashGridLayout
    ) -> Dict[str, int]:
        """
        Get count of items by value tier.

        Args:
            layout: Grid layout to analyze

        Returns:
            Dict mapping tier name to item count
        """
        stats = {tier: 0 for tier in self._colors.keys()}
        for cell in layout.cells:
            if not cell.is_empty:
                stats[cell.value_tier] += 1
        return stats


class StashGridFilter:
    """Filter for stash grid display."""

    def __init__(
        self,
        min_value: float = 0,
        max_value: Optional[float] = None,
        rarities: Optional[List[str]] = None,
        item_classes: Optional[List[str]] = None,
    ):
        """
        Initialize filter.

        Args:
            min_value: Minimum item value to show
            max_value: Maximum item value to show (None = no max)
            rarities: List of rarities to show (None = all)
            item_classes: List of item classes to show (None = all)
        """
        self.min_value = min_value
        self.max_value = max_value
        self.rarities = rarities
        self.item_classes = item_classes

    def matches(self, cell: StashGridCell) -> bool:
        """Check if a cell matches the filter."""
        if cell.is_empty:
            return False

        item = cell.item

        # Value filter
        value = getattr(item, "total_price", 0)
        if value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False

        # Rarity filter
        if self.rarities:
            rarity = getattr(item, "rarity", "").lower()
            if rarity not in [r.lower() for r in self.rarities]:
                return False

        # Item class filter
        if self.item_classes:
            item_class = getattr(item, "item_class", "")
            if item_class not in self.item_classes:
                return False

        return True

    def apply(self, layout: StashGridLayout) -> List[StashGridCell]:
        """
        Apply filter to layout and return matching cells.

        Args:
            layout: Grid layout to filter

        Returns:
            List of cells matching the filter
        """
        return [cell for cell in layout.cells if self.matches(cell)]
