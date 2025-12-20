"""
Stash Grid Dialog.

Full-window dialog for viewing stash tabs as a visual grid
with heatmap coloring based on item values.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QWidget,
    QGroupBox,
    QTextBrowser,
    QSplitter,
)

from gui_qt.styles import COLORS, apply_window_icon
from gui_qt.widgets.stash_grid_visualizer import StashGridVisualizerWidget

if TYPE_CHECKING:
    from core.stash_valuator import ValuationResult, PricedTab, PricedItem

logger = logging.getLogger(__name__)


class StashGridDialog(QDialog):
    """
    Dialog for viewing stash tabs as a visual grid.

    Features:
    - Tab selector to switch between stash tabs
    - Grid visualization with heatmap coloring
    - Item details panel showing selected item info
    - Value filtering and zoom controls
    """

    def __init__(
        self,
        valuation_result: "ValuationResult",
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize dialog.

        Args:
            valuation_result: Valuated stash data
            parent: Parent widget
        """
        super().__init__(parent)
        self._result = valuation_result
        self._current_tab: Optional["PricedTab"] = None

        self.setWindowTitle("Stash Grid View")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        self.resize(1100, 800)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_tabs()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # === Tab Selector ===
        selector_layout = QHBoxLayout()

        selector_layout.addWidget(QLabel("Stash Tab:"))
        self.tab_combo = QComboBox()
        self.tab_combo.setMinimumWidth(250)
        self.tab_combo.currentIndexChanged.connect(self._on_tab_changed)
        selector_layout.addWidget(self.tab_combo)

        selector_layout.addStretch()

        # Total value label
        self.total_value_label = QLabel()
        self.total_value_label.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: {COLORS["accent"]};
                padding: 4px 8px;
                background-color: {COLORS["surface"]};
                border-radius: 4px;
            }}
        """)
        selector_layout.addWidget(self.total_value_label)

        layout.addLayout(selector_layout)

        # === Main Content (Splitter) ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Grid Visualizer
        self.grid_widget = StashGridVisualizerWidget()
        self.grid_widget.itemSelected.connect(self._on_item_selected)
        splitter.addWidget(self.grid_widget)

        # Right: Item Details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)

        details_group = QGroupBox("Selected Item")
        details_inner = QVBoxLayout(details_group)

        self.details_browser = QTextBrowser()
        self.details_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        details_inner.addWidget(self.details_browser)

        details_layout.addWidget(details_group)

        # Quick stats for selected tab
        stats_group = QGroupBox("Tab Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_browser = QTextBrowser()
        self.stats_browser.setMaximumHeight(200)
        self.stats_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        stats_layout.addWidget(self.stats_browser)

        details_layout.addWidget(stats_group)

        splitter.addWidget(details_widget)

        # Set splitter proportions (70% grid, 30% details)
        splitter.setSizes([700, 300])

        layout.addWidget(splitter, stretch=1)

        # === Bottom Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Initial state
        self._show_no_selection()

    def _load_tabs(self) -> None:
        """Load tabs into combo box."""
        self.tab_combo.blockSignals(True)
        self.tab_combo.clear()

        total_value: float = 0
        for tab in self._result.tabs:
            item_count = len(tab.items)
            tab_value = sum(item.total_price for item in tab.items)
            total_value += tab_value

            if tab_value >= 1000:
                value_str = f"{tab_value/1000:.1f}k"
            else:
                value_str = f"{tab_value:.0f}"

            self.tab_combo.addItem(
                f"{tab.name} ({item_count} items, {value_str}c)",
                tab
            )

        # Update total value label
        if total_value >= 1000:
            total_str = f"{total_value/1000:.1f}k"
        else:
            total_str = f"{total_value:.0f}"
        self.total_value_label.setText(f"Total Stash Value: {total_str}c")

        self.tab_combo.blockSignals(False)

        # Select first tab
        if self.tab_combo.count() > 0:
            self._on_tab_changed(0)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab selection change."""
        if index < 0:
            return

        tab = self.tab_combo.currentData()
        if not tab:
            return

        self._current_tab = tab
        self.grid_widget.load_tab(tab)
        self._update_tab_stats()
        self._show_no_selection()

    def _on_item_selected(self, item: "PricedItem") -> None:
        """Handle item selection from grid."""
        self._show_item_details(item)

    def _show_item_details(self, item: "PricedItem") -> None:
        """Display item details."""
        # Get rarity color
        rarity = getattr(item, "rarity", "Normal").lower()
        rarity_colors = {
            "unique": COLORS.get("unique", "#af6025"),
            "rare": COLORS.get("rare", "#ffff77"),
            "magic": COLORS.get("magic", "#8888ff"),
            "normal": COLORS.get("text", "#ffffff"),
            "gem": COLORS.get("gem", "#1ba29b"),
            "currency": COLORS.get("currency", "#aa9e82"),
        }
        name_color = rarity_colors.get(rarity, COLORS["text"])

        # Build HTML
        html = f"""
        <h3 style="color: {name_color}; margin: 0 0 8px 0;">
            {item.name or item.type_line}
        </h3>
        """

        if item.name and item.name != item.type_line:
            html += f"""
            <p style="color: {COLORS['text_secondary']}; margin: 0 0 8px 0;">
                {item.type_line}
            </p>
            """

        # Price info
        html += f"""
        <div style="margin: 12px 0; padding: 8px; background-color: {COLORS['background']}; border-radius: 4px;">
            <p style="margin: 0;"><b>Unit Price:</b> {item.unit_price:.1f}c</p>
        """

        if item.stack_size > 1:
            html += f"""
            <p style="margin: 4px 0 0 0;"><b>Stack Size:</b> {item.stack_size}</p>
            <p style="margin: 4px 0 0 0;"><b>Total Value:</b>
                <span style="color: {COLORS['accent']};">{item.total_price:.1f}c</span>
            </p>
            """
        else:
            html += f"""
            <p style="margin: 4px 0 0 0;"><b>Value:</b>
                <span style="color: {COLORS['accent']};">{item.total_price:.1f}c</span>
            </p>
            """

        html += "</div>"

        # Item properties
        html += "<h4 style='margin: 12px 0 4px 0;'>Properties</h4>"
        html += f"<p><b>Rarity:</b> {item.rarity}</p>"
        html += f"<p><b>Item Class:</b> {item.item_class}</p>"

        if item.ilvl > 0:
            html += f"<p><b>Item Level:</b> {item.ilvl}</p>"

        # Position
        x = getattr(item, "x", 0)
        y = getattr(item, "y", 0)
        html += f"<p><b>Position:</b> ({x}, {y})</p>"

        # Price source
        source = getattr(item, "price_source", None)
        if source:
            html += f"<p><b>Price Source:</b> {source.value if hasattr(source, 'value') else source}</p>"

        self.details_browser.setHtml(html)

    def _show_no_selection(self) -> None:
        """Show placeholder when no item selected."""
        self.details_browser.setHtml(f"""
            <p style="color: {COLORS['text_secondary']}; text-align: center; margin-top: 40px;">
                Click an item in the grid to view details
            </p>
        """)

    def _update_tab_stats(self) -> None:
        """Update tab statistics display."""
        if not self._current_tab:
            self.stats_browser.clear()
            return

        tab = self._current_tab

        # Calculate statistics
        items = tab.items

        # Value tier counts
        tier_counts = {
            "exceptional": 0,
            "very_high": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "vendor": 0,
        }

        for item in items:
            value = item.total_price
            if value >= 1000:
                tier_counts["exceptional"] += 1
            elif value >= 200:
                tier_counts["very_high"] += 1
            elif value >= 50:
                tier_counts["high"] += 1
            elif value >= 5:
                tier_counts["medium"] += 1
            elif value >= 1:
                tier_counts["low"] += 1
            else:
                tier_counts["vendor"] += 1

        # Rarity counts
        rarity_counts: Dict[str, int] = {}
        for item in items:
            rarity = getattr(item, "rarity", "Normal")
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

        # Build HTML
        html = """
        <h4 style="margin: 0 0 8px 0;">Value Distribution</h4>
        <table style="width: 100%;">
        """

        tier_labels = {
            "exceptional": (">1000c", "#cc2222"),
            "very_high": ("200-1000c", "#aa5500"),
            "high": ("50-200c", "#227722"),
            "medium": ("5-50c", "#7a7a22"),
            "low": ("1-5c", "#444444"),
            "vendor": ("<1c", "#2a2a2a"),
        }

        for tier, (label, color) in tier_labels.items():
            count = tier_counts[tier]
            if count > 0:
                html += f"""
                <tr>
                    <td style="width: 20px; background-color: {color};">&nbsp;</td>
                    <td style="padding-left: 8px;">{label}</td>
                    <td style="text-align: right;">{count}</td>
                </tr>
                """

        html += "</table>"

        # Rarity breakdown
        html += "<h4 style='margin: 12px 0 8px 0;'>Rarity Breakdown</h4>"
        for rarity, count in sorted(rarity_counts.items(), key=lambda x: -x[1]):
            html += f"<p style='margin: 2px 0;'>{rarity}: {count}</p>"

        self.stats_browser.setHtml(html)
