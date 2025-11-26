"""
gui_qt.widgets.rare_evaluation_panel

PyQt6 widget for displaying rare item evaluation results.
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QTextEdit,
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
    - Matched affixes
    """

    TIER_COLORS = {
        "EXCELLENT": "#22dd22",   # Green
        "GOOD": "#4488ff",        # Blue
        "AVERAGE": "#ff8800",     # Orange
        "VENDOR": "#dd2222",      # Red
        "NOT_RARE": "#888888",    # Gray
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Rare Item Evaluation", parent)

        self._evaluation = None
        self._create_widgets()
        self.clear()

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

        # Update scores
        self.total_score_label.setText(f"{evaluation.total_score}/100")
        self.base_score_label.setText(f"{evaluation.base_score}/50")
        self.affix_score_label.setText(f"{evaluation.affix_score}/100")

        # Update affixes list
        if evaluation.matched_affixes:
            lines = []
            for match in evaluation.matched_affixes:
                value_str = f" [{int(match.value)}]" if match.value else ""
                weight_str = f" (weight: {match.weight})"
                line = f"[OK] {match.affix_type}: {match.mod_text}{value_str}{weight_str}"
                lines.append(line)
            self.affixes_text.setPlainText("\n".join(lines))
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

    def clear(self) -> None:
        """Clear the evaluation display."""
        self._evaluation = None

        self.tier_label.setText("")
        self.value_label.setText("")
        self.total_score_label.setText("")
        self.base_score_label.setText("")
        self.affix_score_label.setText("")
        self.affixes_text.setPlainText("Paste a rare item to see evaluation...")
