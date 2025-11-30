"""
Stash Grid Visualizer Widget.

Provides a visual grid representation of stash tab contents
with heatmap coloring based on item values.
"""
from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QFont,
)
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QGroupBox,
)

from gui_qt.styles import COLORS

if TYPE_CHECKING:
    from core.stash_grid_renderer import StashGridCell, StashGridLayout
    from core.stash_valuator import PricedTab

logger = logging.getLogger(__name__)

# Grid rendering constants
CELL_SIZE = 40  # Pixels per cell
CELL_PADDING = 2
BORDER_WIDTH = 2


class StashGridCellItem(QGraphicsRectItem):
    """
    Graphics item representing a single stash grid cell.

    Displays the item with heatmap coloring and handles hover/click events.
    """

    def __init__(
        self,
        cell: "StashGridCell",
        cell_size: int = CELL_SIZE,
        parent: Optional[QGraphicsItem] = None,
    ):
        """
        Initialize cell item.

        Args:
            cell: StashGridCell data
            cell_size: Size of one grid cell in pixels
            parent: Parent graphics item
        """
        super().__init__(parent)
        self.cell = cell
        self.cell_size = cell_size
        self._hovered = False

        # Calculate dimensions
        width = cell.width * cell_size - CELL_PADDING
        height = cell.height * cell_size - CELL_PADDING

        self.setRect(0, 0, width, height)

        # Set colors
        self._base_color = QColor(cell.color)
        self._hover_color = self._base_color.lighter(130)
        self._border_color = QColor(cell.border_color)

        self.setBrush(QBrush(self._base_color))
        self.setPen(QPen(self._border_color, BORDER_WIDTH))

        # Enable hover events
        self.setAcceptHoverEvents(True)

        # Set tooltip
        if cell.tooltip:
            self.setToolTip(cell.tooltip)

        # Add value label for high-value items
        if cell.item and cell.item.total_price >= 10:
            self._add_value_label()

    def _add_value_label(self) -> None:
        """Add a value label to the cell."""
        value = self.cell.item.total_price

        # Format value
        if value >= 1000:
            text = f"{value/1000:.1f}k"
        elif value >= 100:
            text = f"{int(value)}"
        else:
            text = f"{value:.0f}"

        label = QGraphicsSimpleTextItem(text, self)
        label.setBrush(QBrush(QColor("#ffffff")))

        # Center the label
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        label.setFont(font)

        bounds = label.boundingRect()
        rect = self.rect()
        label.setPos(
            (rect.width() - bounds.width()) / 2,
            (rect.height() - bounds.height()) / 2
        )

    def hoverEnterEvent(self, event) -> None:
        """Handle mouse enter."""
        self._hovered = True
        self.setBrush(QBrush(self._hover_color))
        self.setPen(QPen(self._border_color.lighter(150), BORDER_WIDTH + 1))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        """Handle mouse leave."""
        self._hovered = False
        self.setBrush(QBrush(self._base_color))
        self.setPen(QPen(self._border_color, BORDER_WIDTH))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Handle mouse click."""
        if self.cell.item:
            # Emit signal through scene
            scene = self.scene()
            if hasattr(scene, "cellClicked"):
                scene.cellClicked.emit(self.cell)
        super().mousePressEvent(event)


class StashGridScene(QGraphicsScene):
    """
    Graphics scene for stash grid visualization.

    Manages the grid cells and emits signals for user interactions.
    """

    cellClicked = pyqtSignal(object)  # StashGridCell
    cellHovered = pyqtSignal(object)  # StashGridCell or None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout: Optional["StashGridLayout"] = None
        self._cell_items: List[StashGridCellItem] = []
        self._min_value_filter: float = 0
        self._show_empty: bool = False

    def load_layout(
        self,
        layout: "StashGridLayout",
        cell_size: int = CELL_SIZE,
    ) -> None:
        """
        Load a stash grid layout.

        Args:
            layout: StashGridLayout to display
            cell_size: Size of each cell in pixels
        """
        self.clear()
        self._cell_items.clear()
        self._layout = layout

        # Draw grid background
        grid_width = layout.width * cell_size
        grid_height = layout.height * cell_size

        bg_rect = self.addRect(
            0, 0, grid_width, grid_height,
            QPen(QColor(COLORS["border"])),
            QBrush(QColor(COLORS["background"]))
        )
        bg_rect.setZValue(-1)

        # Draw grid lines
        pen = QPen(QColor(COLORS["border"]), 1)
        for x in range(layout.width + 1):
            self.addLine(x * cell_size, 0, x * cell_size, grid_height, pen)
        for y in range(layout.height + 1):
            self.addLine(0, y * cell_size, grid_width, y * cell_size, pen)

        # Add cell items
        for cell in layout.cells:
            if self._should_show_cell(cell):
                item = StashGridCellItem(cell, cell_size)
                item.setPos(
                    cell.x * cell_size + CELL_PADDING / 2,
                    cell.y * cell_size + CELL_PADDING / 2
                )
                self.addItem(item)
                self._cell_items.append(item)

        # Set scene rect
        self.setSceneRect(0, 0, grid_width, grid_height)

        logger.debug(
            f"Loaded grid: {layout.width}x{layout.height}, "
            f"{len(self._cell_items)} visible items"
        )

    def _should_show_cell(self, cell: "StashGridCell") -> bool:
        """Check if a cell should be displayed."""
        if cell.is_empty:
            return self._show_empty

        if cell.item.total_price < self._min_value_filter:
            return False

        return True

    def set_min_value_filter(self, min_value: float) -> None:
        """Set minimum value filter and refresh."""
        self._min_value_filter = min_value
        if self._layout:
            self.load_layout(self._layout)

    def set_show_empty(self, show: bool) -> None:
        """Set whether to show empty cells."""
        self._show_empty = show
        if self._layout:
            self.load_layout(self._layout)


class StashGridVisualizerWidget(QWidget):
    """
    Widget for visualizing stash tab contents as a grid.

    Features:
    - Visual grid with heatmap coloring by value
    - Filtering by minimum value
    - Item tooltips and click selection
    - Legend showing value tiers
    """

    itemSelected = pyqtSignal(object)  # PricedItem

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout: Optional["StashGridLayout"] = None

        self._create_widgets()
        self._connect_signals()

    def _create_widgets(self) -> None:
        """Create widget UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # === Filter Bar ===
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)

        # Min value filter
        filter_layout.addWidget(QLabel("Min Value:"))
        self.min_value_spin = QSpinBox()
        self.min_value_spin.setRange(0, 10000)
        self.min_value_spin.setValue(0)
        self.min_value_spin.setSuffix(" c")
        self.min_value_spin.setSingleStep(5)
        filter_layout.addWidget(self.min_value_spin)

        filter_layout.addSpacing(20)

        # Zoom slider
        filter_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(20, 80)
        self.zoom_slider.setValue(CELL_SIZE)
        self.zoom_slider.setMaximumWidth(150)
        filter_layout.addWidget(self.zoom_slider)

        filter_layout.addStretch()

        layout.addWidget(filter_group)

        # === Graphics View ===
        self.scene = StashGridScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {COLORS["background"]};
                border: 1px solid {COLORS["border"]};
            }}
        """)
        layout.addWidget(self.view, stretch=1)

        # === Legend ===
        legend_group = QGroupBox("Value Legend")
        legend_layout = QHBoxLayout(legend_group)

        from core.stash_grid_renderer import StashGridRenderer
        renderer = StashGridRenderer()

        legend_items = [
            ("vendor", "<1c"),
            ("low", "1-5c"),
            ("medium", "5-50c"),
            ("high", "50-200c"),
            ("very_high", "200-1000c"),
            ("exceptional", ">1000c"),
        ]

        for tier, label_text in legend_items:
            color = renderer.HEATMAP_COLORS[tier]
            legend_item = QWidget()
            item_layout = QHBoxLayout(legend_item)
            item_layout.setContentsMargins(4, 2, 4, 2)

            color_box = QLabel()
            color_box.setFixedSize(16, 16)
            color_box.setStyleSheet(
                f"background-color: {color}; border: 1px solid #555;"
            )
            item_layout.addWidget(color_box)

            text_label = QLabel(label_text)
            text_label.setStyleSheet(f"color: {COLORS['text']};")
            item_layout.addWidget(text_label)

            legend_layout.addWidget(legend_item)

        legend_layout.addStretch()
        layout.addWidget(legend_group)

        # === Stats Bar ===
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 6px;
            }}
        """)
        layout.addWidget(self.stats_label)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.min_value_spin.valueChanged.connect(self._on_min_value_changed)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self.scene.cellClicked.connect(self._on_cell_clicked)

    def load_tab(self, priced_tab: "PricedTab") -> None:
        """
        Load and display a priced stash tab.

        Args:
            priced_tab: Tab with priced items to display
        """
        from core.stash_grid_renderer import StashGridRenderer

        renderer = StashGridRenderer()
        self._layout = renderer.render_tab(priced_tab)

        cell_size = self.zoom_slider.value()
        self.scene.load_layout(self._layout, cell_size)

        self._update_stats()

    def load_layout(self, layout: "StashGridLayout") -> None:
        """
        Load a pre-rendered grid layout.

        Args:
            layout: StashGridLayout to display
        """
        self._layout = layout
        cell_size = self.zoom_slider.value()
        self.scene.load_layout(layout, cell_size)
        self._update_stats()

    def _on_min_value_changed(self, value: int) -> None:
        """Handle min value filter change."""
        self.scene.set_min_value_filter(value)

    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom level change."""
        if self._layout:
            self.scene.load_layout(self._layout, value)

    def _on_cell_clicked(self, cell: "StashGridCell") -> None:
        """Handle cell click."""
        if cell.item:
            self.itemSelected.emit(cell.item)

    def _update_stats(self) -> None:
        """Update statistics display."""
        if not self._layout:
            self.stats_label.setText("No tab loaded")
            return

        total_value = self._layout.total_value
        if total_value >= 1000:
            value_str = f"{total_value/1000:.1f}k"
        else:
            value_str = f"{total_value:.0f}"

        self.stats_label.setText(
            f"Tab: {self._layout.tab_name} | "
            f"Items: {self._layout.item_count} | "
            f"Total Value: {value_str}c | "
            f"Grid: {self._layout.width}x{self._layout.height}"
        )
