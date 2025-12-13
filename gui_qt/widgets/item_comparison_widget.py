"""
Item Comparison Widget.

Compares user's item against ideal (T1 max rolls) and market average.
Shows visual roll quality bars and improvement suggestions.

Part of Phase 3: Teaching & Learning features.
"""
from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QGridLayout,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtGui import QFont

from gui_qt.styles import COLORS

if TYPE_CHECKING:
    from core.item_parser import ParsedItem
    from core.crafting_potential import CraftingAnalysis, ModAnalysis

logger = logging.getLogger(__name__)


class ModComparisonRow(QWidget):
    """A row comparing a single mod across your item, ideal, and market."""

    def __init__(
        self,
        mod_analysis: "ModAnalysis",
        ideal_max: int,
        market_avg: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._mod = mod_analysis
        self._ideal_max = ideal_max
        self._market_avg = market_avg
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        # Tier badge
        tier_label = QLabel(self._mod.tier_label or "???")
        tier_label.setFixedWidth(30)
        tier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tier_color = self._get_tier_color(self._mod.tier)
        tier_label.setStyleSheet(f"""
            QLabel {{
                background-color: {tier_color};
                color: white;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
                padding: 2px;
            }}
        """)
        layout.addWidget(tier_label)

        # Stat name
        stat_name = self._mod.stat_type or "Unknown"
        stat_name = stat_name.replace("_", " ").title()
        name_label = QLabel(stat_name)
        name_label.setFixedWidth(120)
        name_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(name_label)

        # Your value with bar
        your_value = self._mod.current_value or 0
        your_widget = self._create_value_widget(
            your_value,
            self._ideal_max,
            COLORS["accent_blue"],
            "Your Item"
        )
        layout.addWidget(your_widget, stretch=1)

        # Ideal value with bar
        ideal_widget = self._create_value_widget(
            self._ideal_max,
            self._ideal_max,
            COLORS["high_value"],
            "Ideal"
        )
        layout.addWidget(ideal_widget, stretch=1)

        # Market average with bar
        market_widget = self._create_value_widget(
            self._market_avg,
            self._ideal_max,
            COLORS["text_secondary"],
            "Market"
        )
        layout.addWidget(market_widget, stretch=1)

    def _create_value_widget(
        self,
        value: int,
        max_value: int,
        color: str,
        label: str
    ) -> QWidget:
        """Create a value display with progress bar."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Value label
        value_label = QLabel(str(value))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        layout.addWidget(value_label)

        # Progress bar
        bar_frame = QFrame()
        bar_frame.setFixedHeight(8)
        bar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 4px;
            }}
        """)

        # Calculate fill percentage
        if max_value > 0:
            fill_pct = min(100, (value / max_value) * 100)
        else:
            fill_pct = 0

        # Inner fill bar
        bar_layout = QHBoxLayout(bar_frame)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        fill = QFrame()
        fill.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        fill.setFixedWidth(int(fill_pct * 0.8))  # Scale to widget width

        bar_layout.addWidget(fill)
        bar_layout.addStretch()

        layout.addWidget(bar_frame)

        return widget

    def _get_tier_color(self, tier: Optional[int]) -> str:
        """Get color based on tier."""
        if tier == 1:
            return str(COLORS["high_value"])
        elif tier == 2:
            return str(COLORS["accent_blue"])
        elif tier == 3:
            return str(COLORS["text_secondary"])
        elif tier is not None and tier >= 4:
            return str(COLORS["low_value"])
        return str(COLORS["border"])


class ItemComparisonWidget(QWidget):
    """
    Widget for comparing item against ideal and market average.

    Shows:
    - Side-by-side mod comparison
    - Roll quality visualization
    - Improvement suggestions
    - Overall quality score
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_item: Optional["ParsedItem"] = None
        self._current_analysis: Optional["CraftingAnalysis"] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QLabel("Item Comparison")
        header.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(header)

        # Summary section
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(12, 8, 12, 8)

        # Quality score
        self.quality_label = QLabel("Quality: --")
        self.quality_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        summary_layout.addWidget(self.quality_label)

        summary_layout.addStretch()

        # Comparison text
        self.comparison_label = QLabel("")
        self.comparison_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        summary_layout.addWidget(self.comparison_label)

        layout.addWidget(self.summary_frame)

        # Column headers
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(8)

        # Spacers to align with content
        header_layout.addSpacing(30)  # Tier badge
        header_layout.addSpacing(120)  # Stat name

        for label_text in ["Your Item", "Ideal (T1 Max)", "Market Avg"]:
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                font-size: 11px;
                font-weight: bold;
            """)
            header_layout.addWidget(label, stretch=1)

        layout.addWidget(header_frame)

        # Scrollable mod comparison area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
        """)

        self.comparison_container = QWidget()
        self.comparison_layout = QVBoxLayout(self.comparison_container)
        self.comparison_layout.setContentsMargins(4, 4, 4, 4)
        self.comparison_layout.setSpacing(4)

        scroll.setWidget(self.comparison_container)
        layout.addWidget(scroll, stretch=1)

        # Improvement suggestions
        self.improvement_group = QGroupBox("Improvement Suggestions")
        self.improvement_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text']};
                font-weight: bold;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        improvement_layout = QVBoxLayout(self.improvement_group)

        self.improvement_label = QLabel("No analysis available")
        self.improvement_label.setWordWrap(True)
        self.improvement_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        improvement_layout.addWidget(self.improvement_label)

        layout.addWidget(self.improvement_group)

        # Show empty state
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        """Show empty state when no item loaded."""
        # Clear comparison rows
        while self.comparison_layout.count():
            layout_item = self.comparison_layout.takeAt(0)
            if layout_item is not None:
                widget = layout_item.widget()
                if widget is not None:
                    widget.deleteLater()

        empty_label = QLabel("Evaluate a rare item to see comparison")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 20px;")
        self.comparison_layout.addWidget(empty_label)

        self.quality_label.setText("Quality: --")
        self.comparison_label.setText("")
        self.improvement_label.setText("No analysis available")

    def set_item(
        self,
        item: "ParsedItem",
        analysis: "CraftingAnalysis"
    ) -> None:
        """
        Set item to display comparison for.

        Args:
            item: The parsed item
            analysis: Crafting analysis results
        """
        self._current_item = item
        self._current_analysis = analysis
        self._update_display()

    def _update_display(self) -> None:
        """Update the display with current item analysis."""
        if not self._current_analysis:
            self._show_empty_state()
            return

        # Clear existing rows
        while self.comparison_layout.count():
            layout_item = self.comparison_layout.takeAt(0)
            if layout_item is not None:
                widget = layout_item.widget()
                if widget is not None:
                    widget.deleteLater()

        # Calculate overall quality
        total_quality: float = 0.0
        mod_count = 0

        # Add comparison rows for each mod
        for mod in self._current_analysis.mod_analyses:
            if mod.stat_type and mod.current_value is not None:
                # Get ideal (T1 max)
                ideal_max = mod.max_roll
                if mod.tier and mod.tier > 1:
                    # Need to look up T1 max
                    ideal_max = self._get_t1_max(mod.stat_type)

                # Estimate market average (roughly 70% of max)
                market_avg = int(ideal_max * 0.70)

                row = ModComparisonRow(
                    mod_analysis=mod,
                    ideal_max=ideal_max,
                    market_avg=market_avg,
                    parent=self.comparison_container,
                )
                self.comparison_layout.addWidget(row)

                # Track quality
                if ideal_max > 0:
                    total_quality += (mod.current_value / ideal_max) * 100
                    mod_count += 1

        self.comparison_layout.addStretch()

        # Update summary
        if mod_count > 0:
            avg_quality = total_quality / mod_count
            quality_text = f"Quality: {avg_quality:.0f}%"
            if avg_quality >= 90:
                quality_color = COLORS["high_value"]
                quality_text += " (Excellent)"
            elif avg_quality >= 75:
                quality_color = COLORS["accent_blue"]
                quality_text += " (Good)"
            elif avg_quality >= 60:
                quality_color = COLORS["text"]
                quality_text += " (Average)"
            else:
                quality_color = COLORS["low_value"]
                quality_text += " (Below Average)"

            self.quality_label.setText(quality_text)
            self.quality_label.setStyleSheet(f"""
                QLabel {{
                    color: {quality_color};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)

            # Comparison text
            market_comparison = avg_quality - 70  # Market avg is ~70%
            if market_comparison > 0:
                self.comparison_label.setText(
                    f"+{market_comparison:.0f}% above market average"
                )
            else:
                self.comparison_label.setText(
                    f"{market_comparison:.0f}% vs market average"
                )
        else:
            self.quality_label.setText("Quality: --")
            self.comparison_label.setText("")

        # Update improvement suggestions
        self._update_improvements()

    def _get_t1_max(self, stat_type: str) -> int:
        """Get T1 max value for a stat type."""
        from core.affix_tier_calculator import AFFIX_TIER_DATA

        tier_data = AFFIX_TIER_DATA.get(stat_type, [])
        if tier_data:
            # T1 is first entry, max is index 3
            return tier_data[0][3]
        return 100  # Default fallback

    def _update_improvements(self) -> None:
        """Update improvement suggestions."""
        if not self._current_analysis:
            self.improvement_label.setText("No analysis available")
            return

        suggestions = []

        # Divine recommendation
        if self._current_analysis.divine_recommended:
            divine_mods = [
                m for m in self._current_analysis.mod_analyses
                if m.divine_potential > 0 and m.tier and m.tier <= 2
            ]
            if divine_mods:
                best = max(divine_mods, key=lambda x: x.divine_potential)
                stat = best.stat_type or "mod"
                stat = stat.replace("_", " ").title()
                suggestions.append(
                    f"Divine for +{best.divine_potential} {stat} potential"
                )

        # Craft recommendations
        if self._current_analysis.open_prefixes > 0:
            suggestions.append(
                f"Craft prefix ({self._current_analysis.open_prefixes} open)"
            )
        if self._current_analysis.open_suffixes > 0:
            suggestions.append(
                f"Craft suffix ({self._current_analysis.open_suffixes} open)"
            )

        # Low roll warnings
        low_rolls = [
            m for m in self._current_analysis.mod_analyses
            if m.roll_quality < 50 and m.tier and m.tier <= 2
        ]
        if low_rolls:
            stat = low_rolls[0].stat_type or "mod"
            stat = stat.replace("_", " ").title()
            suggestions.append(f"Low roll on {stat} ({low_rolls[0].roll_quality:.0f}%)")

        if suggestions:
            self.improvement_label.setText("\n".join(f"- {s}" for s in suggestions))
        else:
            self.improvement_label.setText("Item is well-rolled - no major improvements")

    def clear(self) -> None:
        """Clear the widget."""
        self._current_item = None
        self._current_analysis = None
        self._show_empty_state()
