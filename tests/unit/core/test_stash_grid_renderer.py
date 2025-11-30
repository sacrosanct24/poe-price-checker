"""
Tests for Stash Grid Renderer.
"""
import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass, field
from typing import List

from core.stash_grid_renderer import (
    StashGridRenderer,
    StashGridCell,
    StashGridLayout,
    StashGridFilter,
    VALUE_THRESHOLDS,
    STANDARD_STASH_WIDTH,
    STANDARD_STASH_HEIGHT,
)


@dataclass
class MockPricedItem:
    """Mock PricedItem for testing."""
    name: str = "Test Item"
    type_line: str = "Test Base"
    base_type: str = "Test Base"
    item_class: str = "Currency"
    stack_size: int = 1
    ilvl: int = 0
    rarity: str = "Normal"
    x: int = 0
    y: int = 0
    width: int = 1
    height: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    price_source: str = "poe_ninja"
    tab_name: str = "Test Tab"
    tab_index: int = 0


@dataclass
class MockPricedTab:
    """Mock PricedTab for testing."""
    id: str = "test-tab-1"
    name: str = "Test Tab"
    index: int = 0
    type: str = "NormalStash"
    items: List[MockPricedItem] = field(default_factory=list)


class TestStashGridCell:
    """Tests for StashGridCell dataclass."""

    def test_is_empty_true(self):
        """Test is_empty returns True when no item."""
        cell = StashGridCell(x=0, y=0)
        assert cell.is_empty is True

    def test_is_empty_false(self):
        """Test is_empty returns False when item present."""
        cell = StashGridCell(x=0, y=0, item=MockPricedItem())
        assert cell.is_empty is False

    def test_bounds(self):
        """Test bounds property."""
        cell = StashGridCell(x=2, y=3, width=2, height=2)
        assert cell.bounds == (2, 3, 2, 2)


class TestStashGridLayout:
    """Tests for StashGridLayout dataclass."""

    def test_add_cell(self):
        """Test adding cells to layout."""
        layout = StashGridLayout(tab_name="Test", tab_type="NormalStash")
        cell = StashGridCell(x=0, y=0)
        layout.add_cell(cell)

        assert len(layout.cells) == 1
        assert layout.get_cell_at(0, 0) == cell

    def test_add_multi_cell_item(self):
        """Test adding multi-cell item marks all positions."""
        layout = StashGridLayout(tab_name="Test", tab_type="NormalStash")
        cell = StashGridCell(x=0, y=0, width=2, height=2)
        layout.add_cell(cell)

        # All 4 positions should return the same cell
        assert layout.get_cell_at(0, 0) == cell
        assert layout.get_cell_at(1, 0) == cell
        assert layout.get_cell_at(0, 1) == cell
        assert layout.get_cell_at(1, 1) == cell

    def test_is_occupied(self):
        """Test is_occupied method."""
        layout = StashGridLayout(tab_name="Test", tab_type="NormalStash")
        cell = StashGridCell(x=5, y=5)
        layout.add_cell(cell)

        assert layout.is_occupied(5, 5) is True
        assert layout.is_occupied(0, 0) is False

    def test_get_cell_at_returns_none(self):
        """Test get_cell_at returns None for empty position."""
        layout = StashGridLayout(tab_name="Test", tab_type="NormalStash")
        assert layout.get_cell_at(0, 0) is None


class TestStashGridRenderer:
    """Tests for StashGridRenderer."""

    @pytest.fixture
    def renderer(self):
        """Create renderer instance."""
        return StashGridRenderer()

    @pytest.fixture
    def sample_tab(self):
        """Create sample tab with items."""
        items = [
            MockPricedItem(name="Chaos Orb", x=0, y=0, total_price=1.0, rarity="Currency"),
            MockPricedItem(name="Divine Orb", x=1, y=0, total_price=180.0, rarity="Currency"),
            MockPricedItem(name="Exalted Orb", x=2, y=0, total_price=15.0, rarity="Currency"),
            MockPricedItem(name="Mirror", x=3, y=0, total_price=50000.0, rarity="Currency"),
        ]
        return MockPricedTab(name="Currency", items=items)

    def test_init_default(self):
        """Test default initialization."""
        renderer = StashGridRenderer()
        assert renderer.colorblind_mode is False

    def test_init_colorblind(self):
        """Test colorblind mode initialization."""
        renderer = StashGridRenderer(colorblind_mode=True)
        assert renderer.colorblind_mode is True

    def test_render_tab_creates_layout(self, renderer, sample_tab):
        """Test render_tab creates a layout."""
        layout = renderer.render_tab(sample_tab)

        assert layout.tab_name == "Currency"
        assert layout.item_count == 4
        assert len(layout.cells) == 4

    def test_render_tab_calculates_total(self, renderer, sample_tab):
        """Test render_tab calculates total value."""
        layout = renderer.render_tab(sample_tab)
        expected_total = 1.0 + 180.0 + 15.0 + 50000.0
        assert layout.total_value == expected_total

    def test_render_tab_positions_cells(self, renderer, sample_tab):
        """Test render_tab positions cells correctly."""
        layout = renderer.render_tab(sample_tab)

        for i, cell in enumerate(layout.cells):
            assert cell.x == i
            assert cell.y == 0

    def test_get_value_tier_vendor(self, renderer):
        """Test value tier for vendor trash."""
        assert renderer._get_value_tier(0.5) == "vendor"

    def test_get_value_tier_low(self, renderer):
        """Test value tier for low value items."""
        assert renderer._get_value_tier(3.0) == "low"

    def test_get_value_tier_medium(self, renderer):
        """Test value tier for medium value items."""
        assert renderer._get_value_tier(25.0) == "medium"

    def test_get_value_tier_high(self, renderer):
        """Test value tier for high value items."""
        assert renderer._get_value_tier(100.0) == "high"

    def test_get_value_tier_very_high(self, renderer):
        """Test value tier for very high value items."""
        assert renderer._get_value_tier(500.0) == "very_high"

    def test_get_value_tier_exceptional(self, renderer):
        """Test value tier for exceptional value items."""
        assert renderer._get_value_tier(5000.0) == "exceptional"

    def test_generate_tooltip(self, renderer):
        """Test tooltip generation."""
        item = MockPricedItem(
            name="Chaos Orb",
            type_line="Chaos Orb",
            stack_size=10,
            unit_price=1.0,
            total_price=10.0,
            rarity="Currency",
        )
        tooltip = renderer._generate_tooltip(item)

        assert "Chaos Orb" in tooltip
        assert "Stack: 10" in tooltip
        assert "Unit: 1.0c" in tooltip
        assert "Total: 10.0c" in tooltip

    def test_get_value_statistics(self, renderer, sample_tab):
        """Test value statistics calculation."""
        layout = renderer.render_tab(sample_tab)
        stats = renderer.get_value_statistics(layout)

        assert stats["low"] == 1  # Chaos Orb (1c)
        assert stats["medium"] == 1  # Exalted (15c)
        assert stats["high"] == 1  # Divine (180c)
        assert stats["exceptional"] == 1  # Mirror (50000c)

    def test_colorblind_colors_different(self):
        """Test colorblind mode uses different colors."""
        normal = StashGridRenderer(colorblind_mode=False)
        colorblind = StashGridRenderer(colorblind_mode=True)

        # High value colors should be different
        assert normal.HEATMAP_COLORS["high"] != colorblind.HEATMAP_COLORS_COLORBLIND["high"]

    def test_rarity_colors(self, renderer):
        """Test rarity colors are defined."""
        assert "unique" in renderer.RARITY_COLORS
        assert "rare" in renderer.RARITY_COLORS
        assert "magic" in renderer.RARITY_COLORS
        assert "currency" in renderer.RARITY_COLORS


class TestStashGridFilter:
    """Tests for StashGridFilter."""

    @pytest.fixture
    def sample_cells(self):
        """Create sample cells for filtering."""
        return [
            StashGridCell(
                x=0, y=0,
                item=MockPricedItem(name="Low", total_price=2.0, rarity="Normal")
            ),
            StashGridCell(
                x=1, y=0,
                item=MockPricedItem(name="Medium", total_price=30.0, rarity="Rare")
            ),
            StashGridCell(
                x=2, y=0,
                item=MockPricedItem(name="High", total_price=200.0, rarity="Unique")
            ),
            StashGridCell(x=3, y=0),  # Empty cell
        ]

    def test_filter_by_min_value(self, sample_cells):
        """Test filtering by minimum value."""
        filter_ = StashGridFilter(min_value=10)

        matching = [c for c in sample_cells if filter_.matches(c)]
        assert len(matching) == 2
        assert all(c.item.total_price >= 10 for c in matching)

    def test_filter_by_max_value(self, sample_cells):
        """Test filtering by maximum value."""
        filter_ = StashGridFilter(max_value=100)

        matching = [c for c in sample_cells if filter_.matches(c)]
        assert len(matching) == 2
        assert all(c.item.total_price <= 100 for c in matching)

    def test_filter_by_rarity(self, sample_cells):
        """Test filtering by rarity."""
        filter_ = StashGridFilter(rarities=["Unique"])

        matching = [c for c in sample_cells if filter_.matches(c)]
        assert len(matching) == 1
        assert matching[0].item.name == "High"

    def test_filter_empty_cells(self, sample_cells):
        """Test that empty cells are filtered out."""
        filter_ = StashGridFilter()

        matching = [c for c in sample_cells if filter_.matches(c)]
        assert len(matching) == 3  # All non-empty cells

    def test_apply_returns_matching(self, sample_cells):
        """Test apply method returns matching cells."""
        layout = StashGridLayout(tab_name="Test", tab_type="NormalStash")
        for cell in sample_cells:
            layout.add_cell(cell)

        filter_ = StashGridFilter(min_value=10)
        result = filter_.apply(layout)

        assert len(result) == 2

    def test_combined_filters(self, sample_cells):
        """Test combining multiple filters."""
        filter_ = StashGridFilter(min_value=10, rarities=["Rare", "Unique"])

        matching = [c for c in sample_cells if filter_.matches(c)]
        assert len(matching) == 2


class TestValueThresholds:
    """Tests for value threshold constants."""

    def test_thresholds_ascending(self):
        """Test that thresholds are in ascending order."""
        values = list(VALUE_THRESHOLDS.values())
        assert values == sorted(values)

    def test_standard_dimensions(self):
        """Test standard stash dimensions."""
        assert STANDARD_STASH_WIDTH == 12
        assert STANDARD_STASH_HEIGHT == 12
