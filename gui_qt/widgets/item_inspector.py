"""
gui_qt.widgets.item_inspector

PyQt6 widget for displaying parsed item details.
Optionally shows effective values based on PoB build stats.
Uses QTextBrowser for native scrolling and copy/paste support.
"""

from __future__ import annotations

import html
from typing import Any, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextBrowser,
)

from gui_qt.styles import COLORS, get_rarity_color
from core.build_stat_calculator import BuildStatCalculator, BuildStats
from core.build_archetype import BuildArchetype
from core.upgrade_calculator import UpgradeCalculator, UpgradeImpact


class ItemInspectorWidget(QWidget):
    """Widget for displaying parsed item information using HTML."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Build stats for calculating effective values
        self._build_stats: Optional[BuildStats] = None
        self._calculator: Optional[BuildStatCalculator] = None

        # Build archetype for weighted scoring
        self._archetype: Optional[BuildArchetype] = None

        # Evaluation results from rare item evaluator
        self._evaluation: Optional[Any] = None

        # Upgrade calculator and comparison
        self._upgrade_calculator: Optional[UpgradeCalculator] = None
        self._current_equipped_mods: Optional[List[str]] = None

        # Set minimum size
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Use QTextBrowser for native scrolling and copy/paste
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setReadOnly(True)
        self._browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: none;
                padding: 8px;
                font-size: 11px;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['surface']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                min-height: 30px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['text_secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        layout.addWidget(self._browser)

        # Show placeholder
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        """Show placeholder text."""
        self._browser.setHtml(
            f'<p style="color: {COLORS["text_secondary"]};">No item selected</p>'
        )

    def set_build_stats(self, stats: Optional[BuildStats]) -> None:
        """Set build stats for calculating effective values."""
        self._build_stats = stats
        if stats:
            self._calculator = BuildStatCalculator(stats)
            self._upgrade_calculator = UpgradeCalculator(stats)
        else:
            self._calculator = None
            self._upgrade_calculator = None

    def set_archetype(self, archetype: Optional[BuildArchetype]) -> None:
        """Set build archetype for weighted scoring."""
        self._archetype = archetype

    def set_evaluation(self, evaluation: Optional[Any]) -> None:
        """Set evaluation results from rare item evaluator."""
        self._evaluation = evaluation

    def set_current_equipped(self, item: Optional[Any]) -> None:
        """
        Set the current equipped item for upgrade comparison.

        Args:
            item: The currently equipped item (with mods) or None to clear
        """
        if item is None:
            self._current_equipped_mods = None
            return

        # Extract mods from item
        implicit_mods = getattr(item, "implicits", []) or getattr(item, "implicit_mods", [])
        explicit_mods = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", [])
        self._current_equipped_mods = list(implicit_mods) + list(explicit_mods)

    def clear_current_equipped(self) -> None:
        """Clear the current equipped item comparison."""
        self._current_equipped_mods = None

    def set_item(self, item: Any) -> None:
        """Display parsed item information as HTML."""
        if item is None:
            self._show_placeholder()
            return

        html_parts = []

        # Item name with rarity color (escape for XSS protection)
        name = getattr(item, "name", "") or getattr(item, "base_type", "Unknown Item")
        safe_name = html.escape(str(name))
        rarity = getattr(item, "rarity", "Normal")
        rarity_color = get_rarity_color(rarity)

        html_parts.append(
            f'<p style="color: {rarity_color}; font-size: 14px; font-weight: bold; margin: 0 0 4px 0;">{safe_name}</p>'
        )

        # Base type (if different from name)
        base_type = getattr(item, "base_type", "")
        if base_type and base_type != name:
            safe_base_type = html.escape(str(base_type))
            html_parts.append(
                f'<p style="color: {COLORS["text_secondary"]}; margin: 0 0 4px 0;">{safe_base_type}</p>'
            )

        # Rarity
        html_parts.append(
            f'<p style="color: {rarity_color}; margin: 0 0 8px 0;">Rarity: {rarity}</p>'
        )

        # Build-effective values section - SHOW PROMINENTLY AT TOP
        # Note: ParsedItem uses 'implicits' and 'explicits' not 'implicit_mods'/'explicit_mods'
        implicit_mods = getattr(item, "implicits", []) or getattr(item, "implicit_mods", [])
        explicit_mods = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", [])
        all_mods = list(implicit_mods) + list(explicit_mods)
        if all_mods and self._calculator:
            effective_html = self._build_effective_values_html(all_mods)
            if effective_html:
                html_parts.append(effective_html)

        # Archetype-weighted scores section
        if self._evaluation and hasattr(self._evaluation, 'archetype_affix_details'):
            archetype_html = self._build_archetype_scores_html()
            if archetype_html:
                html_parts.append(archetype_html)

        # Upgrade comparison section
        if self._upgrade_calculator and all_mods:
            upgrade_html = self._build_upgrade_comparison_html(all_mods)
            if upgrade_html:
                html_parts.append(upgrade_html)

        # Separator
        html_parts.append(f'<hr style="border: 1px solid {COLORS["border"]}; margin: 8px 0;">')

        # Item properties
        props = []

        ilvl = getattr(item, "item_level", None) or getattr(item, "ilvl", None)
        if ilvl:
            props.append(("Item Level", str(ilvl)))

        req_level = getattr(item, "required_level", None)
        if req_level:
            props.append(("Required Level", str(req_level)))

        sockets = getattr(item, "sockets", None)
        if sockets:
            props.append(("Sockets", sockets))

        links = getattr(item, "links", None) or getattr(item, "max_links", None)
        if links:
            props.append(("Links", str(links)))

        quality = getattr(item, "quality", None)
        if quality:
            props.append(("Quality", f"+{quality}%"))

        stack = getattr(item, "stack_size", None)
        if stack:
            props.append(("Stack Size", str(stack)))

        map_tier = getattr(item, "map_tier", None)
        if map_tier:
            props.append(("Map Tier", str(map_tier)))

        gem_level = getattr(item, "gem_level", None)
        if gem_level:
            props.append(("Gem Level", str(gem_level)))

        for label, value in props:
            html_parts.append(
                f'<p style="margin: 2px 0;">'
                f'<span style="color: {COLORS["text_secondary"]};">{label}:</span> '
                f'<span style="color: {COLORS["text"]};">{value}</span>'
                f'</p>'
            )

        # Corrupted status
        corrupted = getattr(item, "corrupted", False)
        if corrupted:
            html_parts.append(
                f'<p style="color: {COLORS["corrupted"]}; font-weight: bold; margin: 4px 0;">Corrupted</p>'
            )

        # Implicit mods
        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", [])
        if implicits:
            html_parts.append(f'<hr style="border: 1px solid {COLORS["border"]}; margin: 8px 0;">')
            for mod in implicits:
                html_parts.append(
                    f'<p style="color: {COLORS["magic"]}; margin: 2px 0;">{mod}</p>'
                )

        # Explicit mods
        explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", [])
        if explicits:
            html_parts.append(f'<hr style="border: 1px solid {COLORS["border"]}; margin: 8px 0;">')
            for mod in explicits:
                if "(crafted)" in mod.lower():
                    color = "#b4b4ff"
                else:
                    color = COLORS["text"]
                html_parts.append(
                    f'<p style="color: {color}; margin: 2px 0;">{mod}</p>'
                )

        # Flavor text
        flavor = getattr(item, "flavor_text", None)
        if flavor:
            html_parts.append(f'<hr style="border: 1px solid {COLORS["border"]}; margin: 8px 0;">')
            html_parts.append(
                f'<p style="color: {COLORS["unique"]}; font-style: italic; margin: 2px 0;">{flavor}</p>'
            )

        # Set the HTML content
        full_html = "\n".join(html_parts)
        self._browser.setHtml(full_html)

    def clear(self) -> None:
        """Clear the inspector."""
        self._show_placeholder()

    def _build_effective_values_html(self, mods: List[str]) -> str:
        """Build HTML for effective values section."""
        if not self._calculator:
            return ""

        # Calculate effective values
        results = self._calculator.calculate_effective_values(mods)
        if not results:
            return ""

        html_parts = []

        # Separator and header
        html_parts.append(f'<hr style="border: 1px solid {COLORS["border"]}; margin: 8px 0;">')
        html_parts.append(
            f'<p style="color: {COLORS["currency"]}; font-weight: bold; margin: 0 0 4px 0;">Build-Effective Values</p>'
        )

        # Show build summary
        if self._build_stats:
            summary = (
                f"Life: {int(self._build_stats.total_life)} "
                f"(+{int(self._build_stats.life_inc)}% inc)"
            )
            html_parts.append(
                f'<p style="color: {COLORS["text_secondary"]}; font-size: 10px; margin: 0 0 4px 0;">{summary}</p>'
            )

        # Show effective values for each scalable mod
        for result in results:
            # Only show mods that have meaningful scaling
            if result.multiplier > 1.0 or result.mod_type in (
                "fire_res", "cold_res", "lightning_res", "chaos_res",
                "strength", "intelligence", "all_ele_res"
            ):
                if result.mod_type == "life" and result.multiplier > 1:
                    text = f"+{int(result.raw_value)} life → {int(result.effective_value)} effective"
                    color = COLORS.get('life', "#ff6666")
                elif result.mod_type == "es" and result.multiplier > 1:
                    text = f"+{int(result.raw_value)} ES → {int(result.effective_value)} effective"
                    color = COLORS.get('es', "#8888ff")
                elif result.mod_type == "armour" and result.multiplier > 1:
                    text = f"+{int(result.raw_value)} armour → {int(result.effective_value)} effective"
                    color = COLORS.get('armour', "#ccaa66")
                elif result.mod_type == "strength":
                    life_from_str = (result.raw_value / 2) * (1 + self._build_stats.life_inc / 100)
                    text = f"+{int(result.raw_value)} str = +{int(life_from_str)} effective life"
                    color = COLORS.get('strength', "#ff8866")
                elif result.mod_type == "intelligence":
                    text = result.explanation
                    color = COLORS.get('intelligence', "#6688ff")
                elif result.mod_type in ("fire_res", "cold_res", "lightning_res", "chaos_res"):
                    text = result.explanation
                    color = COLORS.get('text', "#ffffff")
                else:
                    text = result.explanation
                    color = COLORS.get('text', "#ffffff")

                html_parts.append(
                    f'<p style="color: {color}; margin: 2px 0 2px 8px; font-size: 11px;">• {text}</p>'
                )

        return "\n".join(html_parts)

    def _build_archetype_scores_html(self) -> str:
        """Build HTML for archetype-weighted scores section."""
        if not self._evaluation:
            return ""

        affix_details = getattr(self._evaluation, 'archetype_affix_details', None)
        if not affix_details:
            return ""

        html_parts = []

        # Separator and header
        html_parts.append(f'<hr style="border: 1px solid {COLORS["border"]}; margin: 8px 0;">')
        html_parts.append(
            f'<p style="color: {COLORS["accent"]}; font-weight: bold; margin: 0 0 4px 0;">Archetype-Weighted Scores</p>'
        )

        # Show archetype summary if available
        archetype = getattr(self._evaluation, 'build_archetype', None)
        if archetype and hasattr(archetype, 'get_summary'):
            summary = archetype.get_summary()
            html_parts.append(
                f'<p style="color: {COLORS["text_secondary"]}; font-size: 10px; margin: 0 0 4px 0;">{summary}</p>'
            )

        # Show total scores
        base_score = getattr(self._evaluation, 'total_score', 0)
        weighted_score = getattr(self._evaluation, 'archetype_weighted_score', 0)
        if weighted_score and weighted_score != base_score:
            delta = weighted_score - base_score
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            delta_color = COLORS.get('currency', '#ffcc00') if delta > 0 else COLORS.get('corrupted', '#ff4444')
            html_parts.append(
                f'<p style="margin: 2px 0; font-size: 11px;">'
                f'<span style="color: {COLORS["text_secondary"]};">Score:</span> '
                f'<span style="color: {COLORS["text"]};">{base_score}</span> → '
                f'<span style="color: {delta_color}; font-weight: bold;">{weighted_score}</span> '
                f'<span style="color: {delta_color};">({delta_str})</span>'
                f'</p>'
            )

        # Show individual affix weights
        for detail in affix_details:
            affix_type = detail.get('affix_type', '')
            multiplier = detail.get('multiplier', 1.0)
            base_weight = detail.get('base_weight', 0)
            weighted_weight = detail.get('weighted_weight', 0)
            tier = detail.get('tier', '')

            # Skip if no meaningful change
            if abs(multiplier - 1.0) < 0.01:
                continue

            # Color based on multiplier
            if multiplier > 1.0:
                mult_color = COLORS.get('currency', '#ffcc00')
                arrow = "↑"
            else:
                mult_color = COLORS.get('corrupted', '#ff4444')
                arrow = "↓"

            # Format affix type for display
            display_type = affix_type.replace('_', ' ').title()

            html_parts.append(
                f'<p style="margin: 2px 0 2px 8px; font-size: 10px;">'
                f'<span style="color: {COLORS["text_secondary"]};">•</span> '
                f'<span style="color: {COLORS["text"]};">{display_type}</span> '
                f'<span style="color: {mult_color};">{arrow} {multiplier:.1f}x</span> '
                f'<span style="color: {COLORS["text_secondary"]};">({tier})</span>'
                f'</p>'
            )

        return "\n".join(html_parts)

    def _build_upgrade_comparison_html(self, new_mods: List[str]) -> str:
        """Build HTML for upgrade comparison section."""
        if not self._upgrade_calculator:
            return ""

        # Calculate upgrade impact
        comparison = self._upgrade_calculator.compare_items(
            new_mods,
            self._current_equipped_mods
        )
        impact = comparison["impact"]

        html_parts = []

        # Separator and header
        html_parts.append(f'<hr style="border: 1px solid {COLORS["border"]}; margin: 8px 0;">')

        # Header with status indicator
        if comparison["is_upgrade"]:
            status_color = COLORS.get('currency', '#ffcc00')
            status_icon = "▲"
            status_text = "UPGRADE"
        elif comparison["is_downgrade"]:
            status_color = COLORS.get('corrupted', '#ff4444')
            status_icon = "▼"
            status_text = "DOWNGRADE"
        else:
            status_color = COLORS.get('text_secondary', '#888888')
            status_icon = "◆"
            status_text = "SIDEGRADE"

        header_text = "vs Current Equipped" if self._current_equipped_mods else "vs Empty Slot"
        html_parts.append(
            f'<p style="color: {status_color}; font-weight: bold; margin: 0 0 4px 0;">'
            f'{status_icon} {status_text} {header_text}'
            f'</p>'
        )

        # Summary line
        summary = comparison["summary"]
        if summary and summary != "No significant change":
            html_parts.append(
                f'<p style="color: {COLORS["text"]}; margin: 0 0 4px 0; font-size: 11px;">{summary}</p>'
            )

        # Improvements
        improvements = comparison.get("improvements", [])
        if improvements:
            for imp in improvements[:5]:  # Limit to 5
                html_parts.append(
                    f'<p style="color: {COLORS.get("currency", "#ffcc00")}; margin: 2px 0 2px 8px; font-size: 10px;">+ {imp}</p>'
                )

        # Losses
        losses = comparison.get("losses", [])
        if losses:
            for loss in losses[:5]:  # Limit to 5
                html_parts.append(
                    f'<p style="color: {COLORS.get("corrupted", "#ff4444")}; margin: 2px 0 2px 8px; font-size: 10px;">- {loss}</p>'
                )

        # Resistance gap info if relevant
        gaps = comparison.get("gaps")
        if gaps and gaps.has_gaps():
            gap_parts = []
            if gaps.fire_gap > 0:
                gap_parts.append(f"Fire: {int(gaps.fire_gap)}%")
            if gaps.cold_gap > 0:
                gap_parts.append(f"Cold: {int(gaps.cold_gap)}%")
            if gaps.lightning_gap > 0:
                gap_parts.append(f"Light: {int(gaps.lightning_gap)}%")
            if gaps.chaos_gap > 0:
                gap_parts.append(f"Chaos: {int(gaps.chaos_gap)}%")

            if gap_parts:
                html_parts.append(
                    f'<p style="color: {COLORS["text_secondary"]}; margin: 4px 0 2px 0; font-size: 10px;">'
                    f'Res gaps remaining: {", ".join(gap_parts)}'
                    f'</p>'
                )

        return "\n".join(html_parts)
