"""
gui_qt.widgets.rare_evaluation_panel

PyQt6 widget for displaying rare item evaluation results.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QTextEdit,
    QPushButton,
    QFrame,
)

from gui_qt.styles import COLORS


class RareEvaluationPanelWidget(QGroupBox):
    """
    Panel that displays rare item evaluation results.

    Shows:
    - Tier badge (Excellent/Good/Average/Vendor)
    - Estimated value
    - Score breakdown
    - Matched affixes with [META +2] tags
    - Meta analysis info (league, top affixes)
    """

    # Signal emitted when user clicks update meta weights button
    update_meta_requested = pyqtSignal()

    TIER_COLORS = {
        "EXCELLENT": "#22dd22",   # Green
        "GOOD": "#4488ff",        # Blue
        "AVERAGE": "#ff8800",     # Orange
        "VENDOR": "#dd2222",      # Red
        "NOT_RARE": "#888888",    # Gray
    }

    # Color for meta bonus tag
    META_BONUS_COLOR = "#00cc88"  # Teal/green

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Rare Item Evaluation", parent)

        self._evaluation = None
        self._evaluator = None  # Reference to evaluator for meta info
        self._create_widgets()
        self.clear()

    def set_evaluator(self, evaluator: Any) -> None:
        """Set reference to the rare item evaluator for meta info access."""
        self._evaluator = evaluator

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Row 1: Tier badge and value
        tier_row = QHBoxLayout()

        self.tier_label = QLabel()
        tier_font = QFont()
        tier_font.setPointSize(14)
        tier_font.setBold(True)
        self.tier_label.setFont(tier_font)
        tier_row.addWidget(self.tier_label)

        self.value_label = QLabel()
        self.value_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        tier_row.addWidget(self.value_label)

        tier_row.addStretch()
        layout.addLayout(tier_row)

        # Row 1.5: WHY section - shows contributing factors
        self.why_frame = QFrame()
        self.why_frame.setVisible(False)  # Hidden until evaluation
        self.why_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px;
                margin: 4px 0;
            }}
        """)

        why_layout = QVBoxLayout(self.why_frame)
        why_layout.setContentsMargins(8, 6, 8, 6)
        why_layout.setSpacing(2)

        why_header = QLabel("WHY THIS TIER:")
        why_header.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: {COLORS['text_secondary']};
                font-size: 10px;
                letter-spacing: 1px;
            }}
        """)
        why_layout.addWidget(why_header)

        self.why_content_label = QLabel("")
        self.why_content_label.setWordWrap(True)
        self.why_content_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 11px;
            }}
        """)
        why_layout.addWidget(self.why_content_label)

        layout.addWidget(self.why_frame)

        # Row 2: Scores
        score_row = QHBoxLayout()
        score_row.setSpacing(16)

        # Total score
        total_layout = QHBoxLayout()
        total_layout.setSpacing(4)
        total_layout.addWidget(QLabel("Total Score:"))
        self.total_score_label = QLabel()
        self.total_score_label.setStyleSheet("font-weight: bold;")
        total_layout.addWidget(self.total_score_label)
        score_row.addLayout(total_layout)

        # Base score
        base_layout = QHBoxLayout()
        base_layout.setSpacing(4)
        base_layout.addWidget(QLabel("Base:"))
        self.base_score_label = QLabel()
        base_layout.addWidget(self.base_score_label)
        score_row.addLayout(base_layout)

        # Affix score
        affix_layout = QHBoxLayout()
        affix_layout.setSpacing(4)
        affix_layout.addWidget(QLabel("Affixes:"))
        self.affix_score_label = QLabel()
        affix_layout.addWidget(self.affix_score_label)
        score_row.addLayout(affix_layout)

        score_row.addStretch()
        layout.addLayout(score_row)

        # Row 3: Affixes label
        layout.addWidget(QLabel("Valuable Affixes:"))

        # Row 4: Affixes text area
        self.affixes_text = QTextEdit()
        self.affixes_text.setReadOnly(True)
        self.affixes_text.setMaximumHeight(120)
        self.affixes_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                font-family: monospace;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.affixes_text)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(separator)

        # Row 5: Meta info section
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        self.meta_label = QLabel()
        self.meta_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.meta_label.setWordWrap(True)
        meta_row.addWidget(self.meta_label, stretch=1)

        # Update meta weights button
        self.update_meta_btn = QPushButton("↻ Update")
        self.update_meta_btn.setToolTip("Update meta weights from current league builds")
        self.update_meta_btn.setMaximumWidth(80)
        self.update_meta_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        self.update_meta_btn.clicked.connect(self._on_update_meta_clicked)
        meta_row.addWidget(self.update_meta_btn)

        layout.addLayout(meta_row)

        # Row 6: Builds That Want This section
        self.builds_frame = QFrame()
        self.builds_frame.setVisible(False)  # Hidden until evaluation
        self.builds_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['accent_blue']};
                border-radius: 4px;
                padding: 4px;
                margin: 4px 0;
            }}
        """)

        builds_layout = QVBoxLayout(self.builds_frame)
        builds_layout.setContentsMargins(8, 6, 8, 6)
        builds_layout.setSpacing(4)

        builds_header = QLabel("BUILDS THAT WANT THIS:")
        builds_header.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: {COLORS['accent_blue']};
                font-size: 10px;
                letter-spacing: 1px;
            }}
        """)
        builds_layout.addWidget(builds_header)

        self.builds_content_label = QLabel("")
        self.builds_content_label.setWordWrap(True)
        self.builds_content_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 11px;
            }}
        """)
        builds_layout.addWidget(self.builds_content_label)

        layout.addWidget(self.builds_frame)

        # Row 7: Crafting Potential section
        self.crafting_frame = QFrame()
        self.crafting_frame.setVisible(False)  # Hidden until evaluation
        self.crafting_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px;
                margin: 4px 0;
            }}
        """)

        crafting_layout = QVBoxLayout(self.crafting_frame)
        crafting_layout.setContentsMargins(8, 6, 8, 6)
        crafting_layout.setSpacing(4)

        crafting_header = QLabel("CRAFTING POTENTIAL:")
        crafting_header.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: #FFA726;
                font-size: 10px;
                letter-spacing: 1px;
            }}
        """)
        crafting_layout.addWidget(crafting_header)

        self.crafting_content_label = QLabel("")
        self.crafting_content_label.setWordWrap(True)
        self.crafting_content_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 11px;
            }}
        """)
        crafting_layout.addWidget(self.crafting_content_label)

        layout.addWidget(self.crafting_frame)

    def _on_update_meta_clicked(self) -> None:
        """Handle update meta weights button click."""
        self.update_meta_requested.emit()

    def _build_why_explanation(self, evaluation: Any) -> str:
        """
        Build a human-readable WHY explanation from evaluation factors.

        Shows the top contributing factors that led to the tier.
        """
        factors = []

        # Helper to safely get numeric values
        def safe_int(val: Any, default: int = 0) -> int:
            try:
                return int(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        # Synergies (e.g., "Life + resist combo")
        synergies = getattr(evaluation, 'synergies_found', []) or []
        synergy_bonus = safe_int(getattr(evaluation, 'synergy_bonus', 0))
        if synergies and synergy_bonus > 0:
            for syn in synergies[:2]:  # Max 2 synergies
                factors.append(f"+ {syn} (+{synergy_bonus // len(synergies)} synergy)")

        # Slot-specific bonuses (e.g., "Premium base: Stygian Vise")
        slot_reasons = getattr(evaluation, 'slot_bonus_reasons', []) or []
        slot_bonus = safe_int(getattr(evaluation, 'slot_bonus', 0))
        if slot_reasons and slot_bonus > 0:
            for reason in slot_reasons[:1]:  # Just top one
                factors.append(f"+ {reason} (+{slot_bonus})")

        # Matched archetypes / meta fit
        archetypes = getattr(evaluation, 'matched_archetypes', []) or []
        arch_bonus = safe_int(getattr(evaluation, 'archetype_bonus', 0))
        meta_bonus = safe_int(getattr(evaluation, 'meta_bonus', 0))
        if archetypes and arch_bonus > 0:
            archs = ", ".join(archetypes[:2])
            factors.append(f"+ Meta fit: {archs} (+{arch_bonus})")
        elif meta_bonus > 0:
            factors.append(f"+ Meta popularity bonus (+{meta_bonus})")

        # Crafting potential
        crafting_bonus = safe_int(getattr(evaluation, 'crafting_bonus', 0))
        if crafting_bonus > 0:
            open_slots = []
            open_prefixes = safe_int(getattr(evaluation, 'open_prefixes', 0))
            open_suffixes = safe_int(getattr(evaluation, 'open_suffixes', 0))
            if open_prefixes > 0:
                open_slots.append(f"{open_prefixes}P")
            if open_suffixes > 0:
                open_slots.append(f"{open_suffixes}S")
            slot_str = "/".join(open_slots) if open_slots else "open"
            factors.append(f"+ Crafting potential ({slot_str}) (+{crafting_bonus})")

        # Fractured bonus
        fractured_bonus = safe_int(getattr(evaluation, 'fractured_bonus', 0))
        if fractured_bonus > 0:
            mod = getattr(evaluation, 'fractured_mod', None) or "mod"
            factors.append(f"+ Fractured {str(mod)[:20]}... (+{fractured_bonus})")

        # High tier affixes (count T1s)
        matched_affixes = getattr(evaluation, 'matched_affixes', []) or []
        try:
            t1_count = sum(1 for m in matched_affixes if getattr(m, 'tier', '') == "tier1")
            if t1_count >= 2:
                factors.append(f"+ {t1_count}x T1 affixes (high value)")
            elif t1_count == 1:
                t1_affix = next((m for m in matched_affixes if getattr(m, 'tier', '') == "tier1"), None)
                if t1_affix:
                    factors.append(f"+ T1 {getattr(t1_affix, 'affix_type', 'affix')}")
        except (TypeError, AttributeError):
            pass  # Skip if matched_affixes is not iterable

        # Red flags (penalties)
        red_flags = getattr(evaluation, 'red_flags_found', []) or []
        red_penalty = safe_int(getattr(evaluation, 'red_flag_penalty', 0))
        if red_flags and red_penalty > 0:
            for flag in red_flags[:1]:
                factors.append(f"- {flag} (-{red_penalty})")

        # Base type quality
        is_valuable = getattr(evaluation, 'is_valuable_base', False)
        if is_valuable:
            factors.append("+ High-tier base type")
        else:
            factors.append("- Not a premium base")

        # If no factors found, provide basic info
        if len(factors) <= 1:  # Only base type info
            total_score = safe_int(getattr(evaluation, 'total_score', 0))
            if total_score >= 70:
                factors.insert(0, "+ High affix quality")
            elif total_score >= 50:
                factors.insert(0, "+ Decent affix rolls")
            else:
                factors.insert(0, "- No standout mods")

        # Limit to top 4 factors
        return "\n".join(factors[:4])

    def set_evaluation(self, evaluation: Any) -> None:
        """Display evaluation results."""
        self._evaluation = evaluation

        # Update tier badge
        tier = evaluation.tier.upper()
        color = self.TIER_COLORS.get(tier, COLORS["text"])
        self.tier_label.setText(tier)
        self.tier_label.setStyleSheet(f"color: {color};")

        # Update value
        self.value_label.setText(f"Est. Value: {evaluation.estimated_value}")

        # Update WHY section
        why_text = self._build_why_explanation(evaluation)
        self.why_content_label.setText(why_text)
        self.why_frame.setVisible(True)

        # Update scores
        self.total_score_label.setText(f"{evaluation.total_score}/100")
        self.base_score_label.setText(f"{evaluation.base_score}/50")
        self.affix_score_label.setText(f"{evaluation.affix_score}/100")

        # Update affixes list with meta bonus highlighting
        if evaluation.matched_affixes:
            # Use HTML for color-coded meta tags
            html_lines = []
            for match in evaluation.matched_affixes:
                value_str = f" [{int(match.value)}]" if match.value else ""
                weight_str = f" (weight: {match.weight})"

                # Add colored META +2 tag if applicable
                meta_str = ""
                if getattr(match, 'has_meta_bonus', False):
                    meta_str = f' <span style="color: {self.META_BONUS_COLOR}; font-weight: bold;">[META +2]</span>'

                line = f'[OK] {match.affix_type}: {match.mod_text}{value_str}{weight_str}{meta_str}'
                html_lines.append(line)

            # Set as HTML to render the colored meta tags
            self.affixes_text.setHtml(
                f'<pre style="font-family: monospace; font-size: 12px; margin: 0;">'
                + "<br>".join(html_lines)
                + "</pre>"
            )
        else:
            text = "No valuable affixes found.\n\nThis item has:"

            reasons = []
            if not evaluation.is_valuable_base:
                reasons.append("- Not a high-tier base type")
            if not evaluation.has_high_ilvl:
                reasons.append("- Item level too low (need 84+)")
            if not evaluation.matched_affixes:
                reasons.append("- No high-tier affixes above minimum thresholds")

            if reasons:
                text += "\n\n" + "\n".join(reasons)

            self.affixes_text.setPlainText(text)

        # Update meta info section
        self._update_meta_info()

        # Update builds that want this section
        self._update_builds_section(evaluation)

        # Update crafting potential section
        self._update_crafting_section(evaluation)

    def _update_meta_info(self) -> None:
        """Update the meta info section based on evaluator state."""
        if self._evaluator is None:
            self.meta_label.setText("Meta: N/A (no evaluator)")
            return

        # Get meta info from evaluator
        meta_info = getattr(self._evaluator, '_meta_cache_info', None)

        if not meta_info:
            self.meta_label.setText("Meta: Static weights (no meta data loaded)")
            return

        league = meta_info.get('league', 'Unknown')
        builds = meta_info.get('builds_analyzed', 0)
        source = meta_info.get('source', 'unknown')

        # Get top meta affixes
        meta_weights = getattr(self._evaluator, 'meta_weights', {})
        top_affixes = []
        if meta_weights:
            sorted_affixes = []
            for affix_type, data in meta_weights.items():
                if isinstance(data, dict):
                    pop = data.get('popularity_percent', 0)
                else:
                    pop = float(data) * 10
                sorted_affixes.append((affix_type, pop))

            sorted_affixes.sort(key=lambda x: x[1], reverse=True)
            top_affixes = sorted_affixes[:3]

        # Format display
        top_str = ""
        if top_affixes:
            top_str = " | Top: " + ", ".join(
                f"{a[0]}" for a in top_affixes
            )

        self.meta_label.setText(f"Meta: {league} ({builds} builds){top_str}")

    def _update_builds_section(self, evaluation: Any) -> None:
        """Update the builds that want this section."""
        # Safely get attributes with defensive checks
        cross_build_matches = getattr(evaluation, 'cross_build_matches', None)
        cross_build_summary = getattr(evaluation, 'cross_build_summary', None)
        cross_build_appeal = getattr(evaluation, 'cross_build_appeal', None)

        # Convert to safe types
        if not isinstance(cross_build_matches, list):
            cross_build_matches = []
        if not isinstance(cross_build_summary, str):
            cross_build_summary = ''
        try:
            cross_build_appeal = int(cross_build_appeal) if cross_build_appeal is not None else 0
        except (TypeError, ValueError):
            cross_build_appeal = 0

        if not cross_build_matches:
            self.builds_frame.setVisible(False)
            return

        # Build the display text
        lines = []

        # Show summary if available
        if cross_build_summary and cross_build_summary != "No build matches found":
            lines.append(cross_build_summary)
            lines.append("")

        # Show top matches with scores
        try:
            for match in cross_build_matches[:3]:  # Top 3
                archetype = getattr(match, 'archetype', None)
                score = getattr(match, 'score', 0)
                # Safe numeric conversion
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = 0.0
                if archetype:
                    name = getattr(archetype, 'name', 'Unknown')
                    if not isinstance(name, str):
                        name = 'Unknown'
                    # Use symbols to indicate match quality
                    if score >= 80:
                        symbol = "★"  # Excellent
                    elif score >= 60:
                        symbol = "●"  # Good
                    else:
                        symbol = "○"  # Moderate
                    lines.append(f"{symbol} {name} ({score:.0f}% match)")
        except (TypeError, AttributeError):
            pass  # Skip if iteration fails

        # Show appeal count if significant
        if cross_build_appeal >= 3:
            lines.append("")
            lines.append(f"→ Good for {cross_build_appeal}+ builds")

        if lines:
            self.builds_content_label.setText("\n".join(lines))
            self.builds_frame.setVisible(True)
        else:
            self.builds_frame.setVisible(False)

    def _update_crafting_section(self, evaluation: Any) -> None:
        """Update the crafting potential section."""
        # Get the item from evaluation
        item = getattr(evaluation, 'item', None)
        if not item:
            self.crafting_frame.setVisible(False)
            return

        try:
            from core.crafting_potential import analyze_crafting_potential

            analysis = analyze_crafting_potential(item)

            lines = []

            # Open slots info
            if analysis.open_prefixes > 0 or analysis.open_suffixes > 0:
                lines.append(
                    f"Open Slots: {analysis.open_prefixes}P / {analysis.open_suffixes}S"
                )

            # Divine potential
            if analysis.divine_recommended:
                lines.append("")
                lines.append("Divine Potential:")
                for mod in analysis.mod_analyses:
                    if mod.divine_potential > 0 and mod.tier and mod.tier <= 2:
                        stat = (mod.stat_type or "mod").replace("_", " ").title()
                        quality = mod.roll_quality
                        bar = "=" * int(quality / 10)
                        lines.append(
                            f"  {mod.tier_label} {stat}: {mod.current_value} "
                            f"[{bar:<10}] {quality:.0f}%"
                        )
                        lines.append(
                            f"     Roll range: {mod.min_roll}-{mod.max_roll} "
                            f"(+{mod.divine_potential} potential)"
                        )

            # Best craft option
            if analysis.craft_options:
                lines.append("")
                best = analysis.craft_options[0]
                lines.append(f"Suggested: {best.name} ({best.cost_estimate})")

            # Overall assessment
            if analysis.crafting_value in ("high", "very high"):
                lines.append("")
                lines.append(f"Crafting Value: {analysis.crafting_value.upper()}")

            if lines:
                self.crafting_content_label.setText("\n".join(lines))
                self.crafting_frame.setVisible(True)
            else:
                self.crafting_frame.setVisible(False)

        except Exception as e:
            # Don't show crafting section if analysis fails
            self.crafting_frame.setVisible(False)

    def clear(self) -> None:
        """Clear the evaluation display."""
        self._evaluation = None

        self.tier_label.setText("")
        self.value_label.setText("")
        self.why_content_label.setText("")
        self.why_frame.setVisible(False)
        self.total_score_label.setText("")
        self.base_score_label.setText("")
        self.affix_score_label.setText("")
        self.affixes_text.setPlainText("Paste a rare item to see evaluation...")
        self.meta_label.setText("Meta: Waiting...")
        self.builds_content_label.setText("")
        self.builds_frame.setVisible(False)
        self.crafting_content_label.setText("")
        self.crafting_frame.setVisible(False)
