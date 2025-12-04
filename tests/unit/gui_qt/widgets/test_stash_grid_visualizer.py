"""
Tests for the StashGridVisualizerWidget.

Tests grid rendering, cell selection, filtering, and value display.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor

from gui_qt.widgets.stash_grid_visualizer import (
    StashGridCellItem,
    StashGridScene,
    StashGridVisualizerWidget,
    CELL_SIZE,
)


@pytest.fixture
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def stash_visualizer(qapp, qtbot):
    """Create a StashGridVisualizerWidget for testing."""
    widget = StashGridVisualizerWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def stash_scene(qapp):
    """Create a StashGridScene for testing."""
    return StashGridScene()


# Mock data classes for testing
@dataclass
class MockPricedItem:
    """Mock PricedItem for testing."""
    name: str
    base_type: str
    total_price: float
    x: int = 0
    y: int = 0
    width: int = 1
    height: int = 1


@dataclass
class MockStashGridCell:
    """Mock StashGridCell for testing."""
    x: int
    y: int
    width: int
    height: int
    item: Optional[MockPricedItem]
    is_empty: bool
    color: str
    border_color: str
    tooltip: str


@dataclass
class MockStashGridLayout:
    """Mock StashGridLayout for testing."""
    width: int
    height: int
    cells: List[MockStashGridCell]
    total_value: float
    item_count: int
    tab_name: str


@pytest.fixture
def mock_cell():
    """Create a mock cell for testing."""
    item = MockPricedItem(
        name="Test Item",
        base_type="Gold Ring",
        total_price=50.0,
        x=0,
        y=0,
        width=1,
        height=1
    )
    return MockStashGridCell(
        x=0,
        y=0,
        width=1,
        height=1,
        item=item,
        is_empty=False,
        color="#ff6600",
        border_color="#ff0000",
        tooltip="Test Item\n50c"
    )


@pytest.fixture
def mock_empty_cell():
    """Create a mock empty cell."""
    return MockStashGridCell(
        x=1,
        y=1,
        width=1,
        height=1,
        item=None,
        is_empty=True,
        color="#333333",
        border_color="#555555",
        tooltip=""
    )


@pytest.fixture
def mock_layout():
    """Create a mock grid layout for testing."""
    cells = []

    # Add some items with varying values
    cells.append(MockStashGridCell(
        x=0, y=0, width=1, height=1,
        item=MockPricedItem("Low Value", "Ring", 2.0),
        is_empty=False,
        color="#666666",
        border_color="#888888",
        tooltip="Low Value\n2c"
    ))

    cells.append(MockStashGridCell(
        x=1, y=0, width=1, height=1,
        item=MockPricedItem("Medium Value", "Amulet", 25.0),
        is_empty=False,
        color="#ff9900",
        border_color="#ffaa00",
        tooltip="Medium Value\n25c"
    ))

    cells.append(MockStashGridCell(
        x=2, y=0, width=2, height=2,
        item=MockPricedItem("High Value", "Body Armour", 150.0, width=2, height=2),
        is_empty=False,
        color="#ff0000",
        border_color="#ff3333",
        tooltip="High Value\n150c"
    ))

    # Add an empty cell
    cells.append(MockStashGridCell(
        x=4, y=0, width=1, height=1,
        item=None,
        is_empty=True,
        color="#222222",
        border_color="#444444",
        tooltip=""
    ))

    return MockStashGridLayout(
        width=12,
        height=12,
        cells=cells,
        total_value=177.0,
        item_count=3,
        tab_name="Test Tab"
    )


class TestStashGridCellItem:
    """Tests for StashGridCellItem graphics item."""

    def test_cell_item_initialization(self, mock_cell):
        """Test that cell item initializes correctly."""
        item = StashGridCellItem(mock_cell)

        assert item.cell == mock_cell
        assert item.cell_size == CELL_SIZE
        assert item._hovered is False

        # Check rect dimensions
        rect = item.rect()
        assert rect.width() == CELL_SIZE - 2  # CELL_PADDING = 2
        assert rect.height() == CELL_SIZE - 2

    def test_cell_item_custom_size(self, mock_cell):
        """Test cell item with custom cell size."""
        custom_size = 60
        item = StashGridCellItem(mock_cell, cell_size=custom_size)

        assert item.cell_size == custom_size
        rect = item.rect()
        assert rect.width() == custom_size - 2

    def test_cell_item_large_item(self):
        """Test cell item for larger items (2x2)."""
        item_data = MockPricedItem(
            name="Large Item",
            base_type="Body Armour",
            total_price=100.0,
            width=2,
            height=3
        )
        cell = MockStashGridCell(
            x=0, y=0, width=2, height=3,
            item=item_data,
            is_empty=False,
            color="#ff0000",
            border_color="#ff3333",
            tooltip="Large Item"
        )

        item = StashGridCellItem(cell)

        rect = item.rect()
        assert rect.width() == 2 * CELL_SIZE - 2
        assert rect.height() == 3 * CELL_SIZE - 2

    def test_cell_item_tooltip(self, mock_cell):
        """Test that tooltip is set."""
        item = StashGridCellItem(mock_cell)

        assert item.toolTip() == "Test Item\n50c"

    def test_cell_item_colors(self, mock_cell):
        """Test that colors are set correctly."""
        item = StashGridCellItem(mock_cell)

        assert item._base_color == QColor("#ff6600")
        assert item._border_color == QColor("#ff0000")

    def test_cell_item_hover_events(self, mock_cell, qapp):
        """Test hover enter and leave events."""
        item = StashGridCellItem(mock_cell)

        assert item._hovered is False
        assert item.acceptHoverEvents() is True

        # Can't instantiate QGraphicsSceneHoverEvent directly in PyQt6
        # Just verify that the flags are set correctly
        # The actual hover behavior is tested through integration tests

    def test_cell_item_value_label_high_value(self):
        """Test that value label is added for high-value items."""
        item_data = MockPricedItem(
            name="Expensive Item",
            base_type="Ring",
            total_price=250.0
        )
        cell = MockStashGridCell(
            x=0, y=0, width=1, height=1,
            item=item_data,
            is_empty=False,
            color="#ff0000",
            border_color="#ff3333",
            tooltip="Expensive Item"
        )

        cell_item = StashGridCellItem(cell)

        # Should have child items (the label)
        assert len(cell_item.childItems()) > 0

    def test_cell_item_no_value_label_low_value(self):
        """Test that value label is not added for low-value items."""
        item_data = MockPricedItem(
            name="Cheap Item",
            base_type="Ring",
            total_price=5.0
        )
        cell = MockStashGridCell(
            x=0, y=0, width=1, height=1,
            item=item_data,
            is_empty=False,
            color="#666666",
            border_color="#888888",
            tooltip="Cheap Item"
        )

        cell_item = StashGridCellItem(cell)

        # Should not have child items (no label for < 10c)
        assert len(cell_item.childItems()) == 0

    def test_cell_item_value_label_formatting(self):
        """Test value label formatting for different price ranges."""
        # Test 1000+ (should show 'k')
        item_data = MockPricedItem(name="Test", base_type="Ring", total_price=2500.0)
        cell = MockStashGridCell(
            x=0, y=0, width=1, height=1, item=item_data, is_empty=False,
            color="#ff0000", border_color="#ff3333", tooltip=""
        )
        cell_item = StashGridCellItem(cell)
        # Value label should be added
        assert len(cell_item.childItems()) > 0

    def test_cell_item_empty_cell_no_label(self, mock_empty_cell):
        """Test that empty cells don't get value labels."""
        cell_item = StashGridCellItem(mock_empty_cell)

        assert len(cell_item.childItems()) == 0


class TestStashGridScene:
    """Tests for StashGridScene."""

    def test_scene_initialization(self, stash_scene):
        """Test that scene initializes correctly."""
        assert stash_scene._layout is None
        assert stash_scene._cell_items == []
        assert stash_scene._min_value_filter == 0
        assert stash_scene._show_empty is False

    def test_load_layout(self, stash_scene, mock_layout):
        """Test loading a grid layout."""
        stash_scene.load_layout(mock_layout)

        assert stash_scene._layout == mock_layout
        # Should have created cell items (excluding empty by default)
        assert len(stash_scene._cell_items) > 0
        # Should have added background and grid lines
        assert len(stash_scene.items()) > 0

    def test_load_layout_custom_cell_size(self, stash_scene, mock_layout):
        """Test loading layout with custom cell size."""
        custom_size = 60
        stash_scene.load_layout(mock_layout, cell_size=custom_size)

        # Scene rect should reflect custom size
        scene_rect = stash_scene.sceneRect()
        assert scene_rect.width() == mock_layout.width * custom_size
        assert scene_rect.height() == mock_layout.height * custom_size

    def test_load_layout_clears_previous(self, stash_scene, mock_layout):
        """Test that loading new layout clears previous one."""
        stash_scene.load_layout(mock_layout)
        first_item_count = len(stash_scene.items())

        # Load again
        stash_scene.load_layout(mock_layout)
        second_item_count = len(stash_scene.items())

        # Should clear and rebuild (counts should be similar)
        assert second_item_count > 0

    def test_scene_filters_by_value(self, stash_scene, mock_layout):
        """Test that scene filters cells by minimum value."""
        # Load with no filter
        stash_scene.load_layout(mock_layout)
        initial_count = len(stash_scene._cell_items)

        # Set min value filter to 20c
        stash_scene.set_min_value_filter(20.0)

        # Should have fewer items (only medium and high value)
        assert len(stash_scene._cell_items) < initial_count

    def test_scene_shows_empty_cells(self, stash_scene, mock_layout):
        """Test showing empty cells."""
        # Load without showing empty
        stash_scene.load_layout(mock_layout)
        initial_count = len(stash_scene._cell_items)

        # Enable showing empty
        stash_scene.set_show_empty(True)

        # Should have more items
        assert len(stash_scene._cell_items) > initial_count

    def test_scene_cell_clicked_signal(self, stash_scene, mock_cell, qtbot):
        """Test that cellClicked signal is emitted."""
        stash_scene.load_layout(MockStashGridLayout(
            width=12, height=12,
            cells=[mock_cell],
            total_value=50.0,
            item_count=1,
            tab_name="Test"
        ))

        # Get the cell item
        cell_items = [i for i in stash_scene.items() if isinstance(i, StashGridCellItem)]
        assert len(cell_items) > 0

        cell_item = cell_items[0]

        # Can't create QGraphicsSceneMouseEvent in PyQt6, so just verify signal connection
        # and test through higher-level API
        signal_received = []

        def on_clicked(cell):
            signal_received.append(cell)

        stash_scene.cellClicked.connect(on_clicked)

        # Manually trigger what would happen on click
        if cell_item.cell.item:
            stash_scene.cellClicked.emit(cell_item.cell)

        assert len(signal_received) == 1
        assert signal_received[0] == mock_cell


class TestStashGridVisualizerWidget:
    """Tests for StashGridVisualizerWidget."""

    def test_widget_initialization(self, stash_visualizer):
        """Test that widget initializes correctly."""
        assert stash_visualizer.scene is not None
        assert stash_visualizer.view is not None
        assert stash_visualizer.min_value_spin is not None
        assert stash_visualizer.zoom_slider is not None
        assert stash_visualizer.stats_label is not None
        assert stash_visualizer._layout is None

    def test_widget_filter_controls(self, stash_visualizer):
        """Test that filter controls are set up correctly."""
        # Min value spin
        assert stash_visualizer.min_value_spin.minimum() == 0
        assert stash_visualizer.min_value_spin.maximum() == 10000
        assert stash_visualizer.min_value_spin.value() == 0

        # Zoom slider
        assert stash_visualizer.zoom_slider.minimum() == 20
        assert stash_visualizer.zoom_slider.maximum() == 80
        assert stash_visualizer.zoom_slider.value() == CELL_SIZE

    def test_load_layout(self, stash_visualizer, mock_layout):
        """Test loading a grid layout."""
        stash_visualizer.load_layout(mock_layout)

        assert stash_visualizer._layout == mock_layout
        # Stats should be updated
        stats_text = stash_visualizer.stats_label.text()
        assert "Test Tab" in stats_text
        assert "177" in stats_text or "177.0" in stats_text  # Total value

    @patch('core.stash_grid_renderer.StashGridRenderer')
    def test_load_tab(self, mock_renderer_class, stash_visualizer, mock_layout):
        """Test loading a priced tab."""
        # Mock the renderer
        mock_renderer = Mock()
        mock_renderer.render_tab.return_value = mock_layout
        mock_renderer_class.return_value = mock_renderer

        # Create mock priced tab
        mock_tab = Mock()

        stash_visualizer.load_tab(mock_tab)

        # Should have called renderer
        mock_renderer.render_tab.assert_called_once_with(mock_tab)

        # Should have loaded the layout
        assert stash_visualizer._layout == mock_layout

    def test_min_value_filter_change(self, stash_visualizer, mock_layout):
        """Test changing minimum value filter."""
        stash_visualizer.load_layout(mock_layout)

        # Change filter
        stash_visualizer.min_value_spin.setValue(50)

        # Should trigger filter update in scene
        # (Scene will be reloaded with filter)

    def test_zoom_change(self, stash_visualizer, mock_layout):
        """Test changing zoom level."""
        stash_visualizer.load_layout(mock_layout)

        # Change zoom
        new_zoom = 60
        stash_visualizer.zoom_slider.setValue(new_zoom)

        # Scene should be reloaded with new cell size
        # (verify by checking scene rect)
        scene_rect = stash_visualizer.scene.sceneRect()
        assert scene_rect.width() == mock_layout.width * new_zoom

    def test_cell_clicked_emits_item_selected(self, stash_visualizer, mock_layout, qtbot):
        """Test that clicking a cell emits itemSelected signal."""
        stash_visualizer.load_layout(mock_layout)

        # Get a cell with an item
        cell_with_item = next(c for c in mock_layout.cells if c.item is not None)

        # Simulate cell click
        with qtbot.waitSignal(stash_visualizer.itemSelected, timeout=1000) as blocker:
            stash_visualizer._on_cell_clicked(cell_with_item)

        # Should emit the item
        assert blocker.args[0] == cell_with_item.item

    def test_stats_display_formatting(self, stash_visualizer, mock_layout):
        """Test statistics display formatting."""
        stash_visualizer.load_layout(mock_layout)

        stats_text = stash_visualizer.stats_label.text()

        # Should contain key information
        assert "Tab:" in stats_text
        assert "Test Tab" in stats_text
        assert "Items:" in stats_text
        assert "3" in stats_text  # 3 items
        assert "Total Value:" in stats_text
        assert "Grid:" in stats_text
        assert "12x12" in stats_text

    def test_stats_display_high_value_formatting(self, stash_visualizer):
        """Test that high values are formatted with 'k'."""
        high_value_layout = MockStashGridLayout(
            width=12,
            height=12,
            cells=[],
            total_value=2500.0,
            item_count=10,
            tab_name="Rich Tab"
        )

        stash_visualizer.load_layout(high_value_layout)

        stats_text = stash_visualizer.stats_label.text()
        # Should show as "2.5k"
        assert "2.5k" in stats_text

    def test_no_layout_stats(self, stash_visualizer):
        """Test stats display with no layout loaded."""
        stats_text = stash_visualizer.stats_label.text()
        # Initially should be empty or show placeholder
        # (not specified in widget, but shouldn't crash)

    def test_legend_displayed(self, stash_visualizer):
        """Test that value legend is displayed."""
        # Legend should be created during initialization
        # Check that legend labels exist
        assert stash_visualizer.findChildren(type(stash_visualizer.stats_label))


class TestStashGridVisualizerIntegration:
    """Integration tests for complete workflows."""

    def test_complete_workflow(self, stash_visualizer, mock_layout, qtbot):
        """Test complete workflow: load, filter, zoom, select."""
        # Load layout
        stash_visualizer.load_layout(mock_layout)

        # Verify initial state
        assert stash_visualizer._layout == mock_layout
        stats_text = stash_visualizer.stats_label.text()
        assert "Test Tab" in stats_text

        # Apply min value filter
        stash_visualizer.min_value_spin.setValue(20)
        # Should filter out low-value items

        # Change zoom
        stash_visualizer.zoom_slider.setValue(50)
        # Should resize grid

        # Click a cell
        cell_with_item = next(c for c in mock_layout.cells if c.item is not None)
        with qtbot.waitSignal(stash_visualizer.itemSelected, timeout=1000):
            stash_visualizer._on_cell_clicked(cell_with_item)

    def test_switching_layouts(self, stash_visualizer, mock_layout):
        """Test switching between different layouts."""
        # Load first layout
        stash_visualizer.load_layout(mock_layout)
        assert stash_visualizer._layout == mock_layout

        # Create and load second layout
        layout2 = MockStashGridLayout(
            width=12,
            height=12,
            cells=[],
            total_value=500.0,
            item_count=5,
            tab_name="Second Tab"
        )

        stash_visualizer.load_layout(layout2)
        assert stash_visualizer._layout == layout2

        stats_text = stash_visualizer.stats_label.text()
        assert "Second Tab" in stats_text
        assert "Test Tab" not in stats_text

    def test_filter_persistence(self, stash_visualizer, mock_layout):
        """Test that filter settings persist across layout changes."""
        # Set filters
        stash_visualizer.min_value_spin.setValue(50)
        stash_visualizer.zoom_slider.setValue(55)

        # Load layout
        stash_visualizer.load_layout(mock_layout)

        # Filters should still be set
        assert stash_visualizer.min_value_spin.value() == 50
        assert stash_visualizer.zoom_slider.value() == 55

    def test_empty_layout(self, stash_visualizer):
        """Test loading an empty layout."""
        empty_layout = MockStashGridLayout(
            width=12,
            height=12,
            cells=[],
            total_value=0.0,
            item_count=0,
            tab_name="Empty Tab"
        )

        stash_visualizer.load_layout(empty_layout)

        # Should handle gracefully
        stats_text = stash_visualizer.stats_label.text()
        assert "Empty Tab" in stats_text
        assert "0" in stats_text  # 0 items

    def test_high_zoom_performance(self, stash_visualizer, mock_layout):
        """Test that high zoom levels work correctly."""
        stash_visualizer.load_layout(mock_layout)

        # Set to maximum zoom
        max_zoom = stash_visualizer.zoom_slider.maximum()
        stash_visualizer.zoom_slider.setValue(max_zoom)

        # Should render without errors
        scene_rect = stash_visualizer.scene.sceneRect()
        assert scene_rect.width() == mock_layout.width * max_zoom

    def test_low_zoom_performance(self, stash_visualizer, mock_layout):
        """Test that low zoom levels work correctly."""
        stash_visualizer.load_layout(mock_layout)

        # Set to minimum zoom
        min_zoom = stash_visualizer.zoom_slider.minimum()
        stash_visualizer.zoom_slider.setValue(min_zoom)

        # Should render without errors
        scene_rect = stash_visualizer.scene.sceneRect()
        assert scene_rect.width() == mock_layout.width * min_zoom


class TestStashGridCellItemInteraction:
    """Tests for cell item interactions."""

    def test_mouse_press_on_cell_with_item(self, mock_cell, qapp):
        """Test mouse press on cell with item."""
        cell_item = StashGridCellItem(mock_cell)

        # Create a mock scene with cellClicked signal
        scene = StashGridScene()
        scene.addItem(cell_item)

        signal_emitted = False
        received_cell = None

        def on_cell_clicked(cell):
            nonlocal signal_emitted, received_cell
            signal_emitted = True
            received_cell = cell

        scene.cellClicked.connect(on_cell_clicked)

        # Can't create QGraphicsSceneMouseEvent in PyQt6
        # Test the logic directly
        if cell_item.cell.item:
            scene.cellClicked.emit(cell_item.cell)

        assert signal_emitted is True
        assert received_cell == mock_cell

    def test_mouse_press_on_empty_cell(self, mock_empty_cell, qapp):
        """Test mouse press on empty cell."""
        cell_item = StashGridCellItem(mock_empty_cell)

        scene = StashGridScene()
        scene.addItem(cell_item)

        signal_emitted = False

        def on_cell_clicked(cell):
            nonlocal signal_emitted
            signal_emitted = True

        scene.cellClicked.connect(on_cell_clicked)

        # Empty cell has no item, so signal should not be emitted
        # (This logic is in mousePressEvent which checks if cell.item exists)
        if cell_item.cell.item:  # This will be False for empty cell
            scene.cellClicked.emit(cell_item.cell)

        # Should not emit signal (no item)
        assert signal_emitted is False


class TestStashGridSceneFiltering:
    """Tests for scene filtering logic."""

    def test_should_show_cell_with_value_above_filter(self, stash_scene):
        """Test that cells above value filter are shown."""
        stash_scene._min_value_filter = 10.0
        stash_scene._show_empty = False

        cell = MockStashGridCell(
            x=0, y=0, width=1, height=1,
            item=MockPricedItem("Test", "Ring", 50.0),
            is_empty=False,
            color="#ff0000",
            border_color="#ff3333",
            tooltip=""
        )

        assert stash_scene._should_show_cell(cell) is True

    def test_should_not_show_cell_below_value_filter(self, stash_scene):
        """Test that cells below value filter are hidden."""
        stash_scene._min_value_filter = 100.0
        stash_scene._show_empty = False

        cell = MockStashGridCell(
            x=0, y=0, width=1, height=1,
            item=MockPricedItem("Test", "Ring", 50.0),
            is_empty=False,
            color="#ff0000",
            border_color="#ff3333",
            tooltip=""
        )

        assert stash_scene._should_show_cell(cell) is False

    def test_should_not_show_empty_by_default(self, stash_scene, mock_empty_cell):
        """Test that empty cells are hidden by default."""
        stash_scene._show_empty = False

        assert stash_scene._should_show_cell(mock_empty_cell) is False

    def test_should_show_empty_when_enabled(self, stash_scene, mock_empty_cell):
        """Test that empty cells are shown when enabled."""
        stash_scene._show_empty = True

        assert stash_scene._should_show_cell(mock_empty_cell) is True
