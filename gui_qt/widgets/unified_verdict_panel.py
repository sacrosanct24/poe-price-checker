"""
Unified Verdict Panel Widget.

Consolidated panel that merges:
- QuickVerdictPanel (emoji + Keep/Vendor/Maybe)
- RareEvaluationPanelWidget (tier + scores + affixes + builds + crafting)
- UnifiedVerdictPanel (FOR YOU + TO SELL + TO STASH + WHY)

Shows a complete evaluation with quick verdict header and detailed sections.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGroupBox,
    QScrollArea,
    QPushButton,
)

from gui_qt.styles import COLORS
from gui_qt.accessibility import set_accessible_name, set_accessible_description

if TYPE_CHECKING:
    from core.unified_verdict import UnifiedVerdict, PrimaryAction
    from core.rare_evaluation.models import RareItemEvaluation

logger = logging.getLogger(__name__)


class VerdictSectionWidget(QFrame):
    """A section showing one aspect of the verdict (FOR YOU, TO SELL, etc.)."""

    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header row with title and status
        header_layout = QHBoxLayout()

        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: {COLORS['text_secondary']};
                font-size: 10px;
            }}
        """)
        header_layout.addWidget(self.title_label)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Content
        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(self.content_label)

    def set_status(self, is_positive: bool, is_neutral: bool = False) -> None:
        """Set the status indicator."""
        if is_positive:
            self.status_label.setText("[OK]")
            self.status_label.setStyleSheet(f"font-weight: bold; color: {COLORS['high_value']};")
        elif is_neutral:
            self.status_label.setText("[!]")
            self.status_label.setStyleSheet(f"font-weight: bold; color: #FFA726;")
        else:
            self.status_label.setText("[X]")
            self.status_label.setStyleSheet(f"font-weight: bold; color: {COLORS['low_value']};")

    def set_content(self, text: str) -> None:
        """Set the content text."""
        self.content_label.setText(text)


class CollapsibleSection(QFrame):
    """A collapsible section for detailed information."""

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._is_expanded = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header (clickable)
        self.header_btn = QPushButton(f"▶ {self._title}")
        self.header_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: none;
                border-radius: 4px 4px 0 0;
                padding: 6px 10px;
                text-align: left;
                font-weight: bold;
                font-size: 10px;
                color: {COLORS['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        self.header_btn.clicked.connect(self._toggle)
        layout.addWidget(self.header_btn)

        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 6, 10, 10)
        self.content_layout.setSpacing(4)
        self.content_widget.setVisible(False)
        layout.addWidget(self.content_widget)

    def _toggle(self) -> None:
        self._is_expanded = not self._is_expanded
        self.content_widget.setVisible(self._is_expanded)
        arrow = "▼" if self._is_expanded else "▶"
        self.header_btn.setText(f"{arrow} {self._title}")

    def expand(self) -> None:
        """Expand the section."""
        if not self._is_expanded:
            self._toggle()

    def collapse(self) -> None:
        """Collapse the section."""
        if self._is_expanded:
            self._toggle()


class UnifiedVerdictPanel(QGroupBox):
    """
    Consolidated verdict panel with all evaluation signals.

    Merged from QuickVerdictPanel, RareEvaluationPanel, and original UnifiedVerdictPanel.

    Shows:
    - Quick verdict header (emoji + KEEP/VENDOR/MAYBE + confidence)
    - Primary action badge
    - FOR YOU / TO SELL / TO STASH sections
    - WHY VALUABLE: Key factors
    - BUILDS THAT WANT THIS: Cross-build matches
    - DETAILED ANALYSIS: Scores, tier, matched affixes (collapsible)
    - CLUSTER JEWEL INFO: If cluster jewel (collapsible)
    - UNIQUE ITEM INFO: If unique item (collapsible)
    """

    # Signals
    refresh_requested = pyqtSignal()
    details_requested = pyqtSignal()

    ACTION_COLORS = {
        "KEEP": "#4CAF50",    # Green
        "SELL": "#2196F3",    # Blue
        "STASH": "#FFA726",   # Orange
        "VENDOR": "#F44336",  # Red
        "EVALUATE": "#9E9E9E",  # Grey
    }

    # Tier colors for rare evaluation
    TIER_COLORS = {
        "EXCELLENT": "#22dd22",   # Green
        "GOOD": "#4488ff",        # Blue
        "AVERAGE": "#ff8800",     # Orange
        "VENDOR": "#dd2222",      # Red
        "NOT_RARE": "#888888",    # Gray
    }

    # Unique item tier colors
    UNIQUE_TIER_COLORS = {
        "chase": "#ff00ff",     # Magenta
        "excellent": "#22dd22", # Green
        "good": "#4488ff",      # Blue
        "average": "#ff8800",   # Orange
        "vendor": "#dd2222",    # Red
    }

    # Cluster jewel notable tier colors
    NOTABLE_TIER_COLORS = {
        "meta": "#22dd22",     # Green
        "high": "#4488ff",     # Blue
        "medium": "#ff8800",   # Orange
        "low": "#888888",      # Gray
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Unified Verdict", parent)
        self._current_verdict: Optional["UnifiedVerdict"] = None
        self._current_rare_eval: Optional["RareItemEvaluation"] = None
        self._setup_ui()
        self.clear()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ========== QUICK VERDICT HEADER ==========
        # Large emoji + verdict word + confidence + explanation
        self.quick_verdict_frame = QFrame()
        self.quick_verdict_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)

        quick_layout = QVBoxLayout(self.quick_verdict_frame)
        quick_layout.setSpacing(4)

        # Top row: emoji + verdict word + confidence
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self.emoji_label = QLabel("❓")
        self.emoji_label.setStyleSheet("font-size: 48px; padding: 0; margin: 0;")
        self.emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_accessible_name(self.emoji_label, "Verdict indicator")
        top_row.addWidget(self.emoji_label)

        # Verdict text column
        verdict_text_layout = QVBoxLayout()
        verdict_text_layout.setSpacing(2)

        self.verdict_word_label = QLabel("Waiting...")
        self.verdict_word_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['text']};
        """)
        set_accessible_name(self.verdict_word_label, "Verdict")
        set_accessible_description(
            self.verdict_word_label,
            "Primary verdict for the evaluated item: Keep, Sell, Vendor, or Maybe"
        )
        verdict_text_layout.addWidget(self.verdict_word_label)

        self.confidence_dots_label = QLabel("")
        self.confidence_dots_label.setStyleSheet(f"""
            font-size: 11px;
            color: {COLORS['text_secondary']};
        """)
        set_accessible_name(self.confidence_dots_label, "Confidence level")
        verdict_text_layout.addWidget(self.confidence_dots_label)

        top_row.addLayout(verdict_text_layout)
        top_row.addStretch()

        quick_layout.addLayout(top_row)

        # Explanation
        self.explanation_label = QLabel("Paste an item to get a verdict")
        self.explanation_label.setWordWrap(True)
        self.explanation_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text']};
            padding: 8px 0;
        """)
        set_accessible_name(self.explanation_label, "Verdict explanation")
        set_accessible_description(
            self.explanation_label,
            "Detailed explanation of why this verdict was given"
        )
        quick_layout.addWidget(self.explanation_label)

        layout.addWidget(self.quick_verdict_frame)

        # ========== PRIMARY ACTION BADGE ==========
        self.action_frame = QFrame()
        self.action_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        action_layout = QHBoxLayout(self.action_frame)
        action_layout.setContentsMargins(12, 8, 12, 8)

        self.action_label = QLabel("VERDICT: ---")
        action_font = QFont()
        action_font.setPointSize(16)
        action_font.setBold(True)
        self.action_label.setFont(action_font)
        action_layout.addWidget(self.action_label)

        action_layout.addStretch()

        self.confidence_label = QLabel()
        self.confidence_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        action_layout.addWidget(self.confidence_label)

        layout.addWidget(self.action_frame)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # FOR YOU section
        self.for_you_section = VerdictSectionWidget("FOR YOU:")
        set_accessible_name(self.for_you_section, "For You assessment")
        set_accessible_description(
            self.for_you_section,
            "Shows if this item is an upgrade for your character"
        )
        content_layout.addWidget(self.for_you_section)

        # TO SELL section
        self.to_sell_section = VerdictSectionWidget("TO SELL:")
        set_accessible_name(self.to_sell_section, "To Sell assessment")
        set_accessible_description(
            self.to_sell_section,
            "Shows the market value and selling potential of this item"
        )
        content_layout.addWidget(self.to_sell_section)

        # TO STASH section
        self.to_stash_section = VerdictSectionWidget("TO STASH:")
        set_accessible_name(self.to_stash_section, "To Stash assessment")
        set_accessible_description(
            self.to_stash_section,
            "Shows if this item should be saved for other builds"
        )
        content_layout.addWidget(self.to_stash_section)

        # WHY VALUABLE section
        self.why_section = QFrame()
        self.why_section.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        why_layout = QVBoxLayout(self.why_section)
        why_layout.setContentsMargins(8, 6, 8, 6)

        why_header = QLabel("WHY VALUABLE:")
        why_header.setStyleSheet(f"""
            font-weight: bold;
            color: {COLORS['text_secondary']};
            font-size: 10px;
        """)
        why_layout.addWidget(why_header)

        self.why_content = QLabel()
        self.why_content.setWordWrap(True)
        self.why_content.setStyleSheet(f"color: {COLORS['text']};")
        why_layout.addWidget(self.why_content)

        # Tier summary (visible without expanding)
        self.tier_summary_label = QLabel()
        self.tier_summary_label.setWordWrap(True)
        self.tier_summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.tier_summary_label.setStyleSheet(f"""
            font-size: 11px;
            padding-top: 4px;
            border-top: 1px solid {COLORS['border']};
            margin-top: 4px;
        """)
        self.tier_summary_label.setVisible(False)
        why_layout.addWidget(self.tier_summary_label)

        content_layout.addWidget(self.why_section)

        # BUILDS section
        self.builds_section = QFrame()
        self.builds_section.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['accent_blue']};
                border-radius: 4px;
            }}
        """)
        builds_layout = QVBoxLayout(self.builds_section)
        builds_layout.setContentsMargins(8, 6, 8, 6)

        builds_header = QLabel("BUILDS THAT WANT THIS:")
        builds_header.setStyleSheet(f"""
            font-weight: bold;
            color: {COLORS['accent_blue']};
            font-size: 10px;
        """)
        builds_layout.addWidget(builds_header)

        self.builds_content = QLabel()
        self.builds_content.setWordWrap(True)
        self.builds_content.setStyleSheet(f"color: {COLORS['text']};")
        builds_layout.addWidget(self.builds_content)

        content_layout.addWidget(self.builds_section)

        # MARKET CONTEXT section
        self.market_section = QFrame()
        self.market_section.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        market_layout = QVBoxLayout(self.market_section)
        market_layout.setContentsMargins(8, 6, 8, 6)

        market_header = QLabel("MARKET CONTEXT:")
        market_header.setStyleSheet(f"""
            font-weight: bold;
            color: {COLORS['text_secondary']};
            font-size: 10px;
        """)
        market_layout.addWidget(market_header)

        self.market_content = QLabel()
        self.market_content.setWordWrap(True)
        self.market_content.setStyleSheet(f"color: {COLORS['text']};")
        market_layout.addWidget(self.market_content)

        content_layout.addWidget(self.market_section)

        # ========== DETAILED ANALYSIS (Collapsible) ==========
        self.detailed_section = CollapsibleSection("DETAILED ANALYSIS")
        self.detailed_section.setVisible(False)

        # Tier and scores
        self.detail_tier_label = QLabel()
        self.detail_tier_label.setStyleSheet("font-weight: bold;")
        self.detailed_section.content_layout.addWidget(self.detail_tier_label)

        self.detail_scores_label = QLabel()
        self.detail_scores_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.detailed_section.content_layout.addWidget(self.detail_scores_label)

        # Matched affixes
        self.detail_affixes_label = QLabel()
        self.detail_affixes_label.setWordWrap(True)
        self.detail_affixes_label.setStyleSheet(f"color: {COLORS['text']};")
        self.detailed_section.content_layout.addWidget(self.detail_affixes_label)

        # Crafting potential
        self.detail_crafting_label = QLabel()
        self.detail_crafting_label.setWordWrap(True)
        self.detail_crafting_label.setStyleSheet(f"color: {COLORS['text']};")
        self.detailed_section.content_layout.addWidget(self.detail_crafting_label)

        content_layout.addWidget(self.detailed_section)

        # ========== CLUSTER JEWEL INFO (Collapsible) ==========
        self.cluster_section = CollapsibleSection("CLUSTER JEWEL INFO")
        self.cluster_section.setVisible(False)

        self.cluster_info_label = QLabel()
        self.cluster_info_label.setWordWrap(True)
        self.cluster_info_label.setStyleSheet(f"color: {COLORS['text']};")
        self.cluster_section.content_layout.addWidget(self.cluster_info_label)

        self.cluster_notables_label = QLabel()
        self.cluster_notables_label.setWordWrap(True)
        self.cluster_section.content_layout.addWidget(self.cluster_notables_label)

        content_layout.addWidget(self.cluster_section)

        # ========== UNIQUE ITEM INFO (Collapsible) ==========
        self.unique_section = CollapsibleSection("UNIQUE ITEM INFO")
        self.unique_section.setVisible(False)
        self.unique_section.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid #af6025;
                border-radius: 4px;
            }}
        """)

        self.unique_name_label = QLabel()
        self.unique_name_label.setStyleSheet("font-weight: bold;")
        self.unique_section.content_layout.addWidget(self.unique_name_label)

        self.unique_price_label = QLabel()
        self.unique_price_label.setStyleSheet(f"color: {COLORS['text']};")
        self.unique_section.content_layout.addWidget(self.unique_price_label)

        self.unique_details_label = QLabel()
        self.unique_details_label.setWordWrap(True)
        self.unique_details_label.setStyleSheet(f"color: {COLORS['text']};")
        self.unique_section.content_layout.addWidget(self.unique_details_label)

        content_layout.addWidget(self.unique_section)

        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)

        # Action buttons
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        set_accessible_name(self.refresh_btn, "Refresh verdict")
        set_accessible_description(self.refresh_btn, "Re-evaluate the current item")
        button_layout.addWidget(self.refresh_btn)

        self.details_btn = QPushButton("Full Details")
        self.details_btn.clicked.connect(self.details_requested.emit)
        self.details_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_blue']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
        """)
        set_accessible_name(self.details_btn, "Full Details")
        set_accessible_description(
            self.details_btn,
            "Show detailed analysis and evaluation breakdown"
        )
        button_layout.addWidget(self.details_btn)

        layout.addLayout(button_layout)

    def set_verdict(
        self,
        verdict: "UnifiedVerdict",
        rare_evaluation: Optional["RareItemEvaluation"] = None,
    ) -> None:
        """Display a unified verdict with optional rare evaluation details."""
        self._current_verdict = verdict
        self._current_rare_eval = rare_evaluation

        # ========== QUICK VERDICT HEADER ==========
        self._update_quick_verdict_section(verdict)

        # ========== PRIMARY ACTION BADGE ==========
        action_name = verdict.primary_action.name
        color = self.ACTION_COLORS.get(action_name, COLORS['text'])

        self.action_label.setText(f"VERDICT: {action_name}")
        self.action_label.setStyleSheet(f"color: {color};")
        self.action_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {color};
                border-radius: 8px;
                padding: 8px;
            }}
        """)

        # Confidence
        conf = verdict.confidence.upper()
        self.confidence_label.setText(f"Confidence: {conf}")

        # FOR YOU section
        if verdict.for_you.is_upgrade:
            self.for_you_section.set_status(True)
            slot = verdict.for_you.upgrade_slot or "equipment"
            content = f"Upgrade for {slot}"
            if verdict.for_you.improvement_percent > 0:
                content += f" (+{verdict.for_you.improvement_percent:.0f}%)"
        else:
            self.for_you_section.set_status(False)
            content = verdict.for_you.reason or "Not an upgrade"
        self.for_you_section.set_content(content)

        # TO SELL section
        if verdict.to_sell.is_valuable:
            self.to_sell_section.set_status(True)
            content = f"Worth {verdict.to_sell.price_range}"
            # Add price context badge if available
            if verdict.to_sell.price_context:
                ctx_color = verdict.to_sell.price_context_color or "#2196F3"
                content += f"  [{verdict.to_sell.price_context}]"
            if verdict.to_sell.demand_level != "unknown":
                content += f"\nDemand: {verdict.to_sell.demand_level}"
            # Add price context explanation as tooltip hint
            if verdict.to_sell.price_context_explanation:
                content += f"\n{verdict.to_sell.price_context_explanation}"
        else:
            self.to_sell_section.set_status(False)
            content = "Low market value"
            # Still show price context for low-value items
            if verdict.to_sell.price_context:
                content += f"  [{verdict.to_sell.price_context}]"
        self.to_sell_section.set_content(content)

        # TO STASH section
        if verdict.to_stash.should_stash:
            self.to_stash_section.set_status(True, is_neutral=True)
            builds = verdict.to_stash.good_for_builds[:3]
            content = f"Good for: {', '.join(builds)}"
            if verdict.to_stash.stash_reason:
                content += f"\n{verdict.to_stash.stash_reason}"
        else:
            self.to_stash_section.set_status(False)
            content = "No specific build fit"
        self.to_stash_section.set_content(content)

        # WHY VALUABLE section
        factors = verdict.why_valuable.factors[:5]
        if factors:
            self.why_content.setText("\n".join(f"* {f}" for f in factors))
            self.why_section.setVisible(True)
        else:
            self.why_section.setVisible(False)

        # BUILDS section
        if verdict.top_build_matches:
            self.builds_content.setText("\n".join(verdict.top_build_matches[:4]))
            self.builds_section.setVisible(True)
        else:
            self.builds_section.setVisible(False)

        # MARKET CONTEXT section
        market_lines = []
        mc = verdict.market_context
        if mc.price_trend and mc.price_trend != "UNKNOWN":
            trend_symbol = {"UP": "+", "DOWN": "-", "STABLE": "~"}.get(mc.price_trend, "?")
            market_lines.append(
                f"Trending {mc.price_trend} ({trend_symbol}{abs(mc.trend_percent):.0f}%)"
            )
        if mc.similar_listings:
            market_lines.append(f"Similar: {', '.join(mc.similar_listings[:3])}")
        if mc.last_sale:
            market_lines.append(f"Last sale: {mc.last_sale}")

        if market_lines:
            self.market_content.setText("\n".join(market_lines))
            self.market_section.setVisible(True)
        else:
            self.market_section.setVisible(False)

        # ========== DETAILED SECTIONS (from rare evaluation) ==========
        if rare_evaluation:
            self._update_detailed_analysis(rare_evaluation)
            self._update_cluster_section(rare_evaluation)
            self._update_unique_section(rare_evaluation)
        else:
            self.detailed_section.setVisible(False)
            self.cluster_section.setVisible(False)
            self.unique_section.setVisible(False)

    def _update_quick_verdict_section(self, verdict: "UnifiedVerdict") -> None:
        """Update the quick verdict header from verdict data."""
        # Get quick verdict result if available
        quick_result = getattr(verdict, 'quick_verdict_result', None)

        if quick_result:
            # Use the emoji and verdict from quick_verdict_result
            self.emoji_label.setText(quick_result.emoji)
            verdict_text = quick_result.verdict.value.upper()
            self.verdict_word_label.setText(verdict_text)
            self.verdict_word_label.setStyleSheet(f"""
                font-size: 24px;
                font-weight: bold;
                color: {quick_result.color};
            """)

            # Confidence dots
            confidence_icons = {"low": "○○○", "medium": "●○○", "high": "●●●"}
            self.confidence_dots_label.setText(
                f"Confidence: {confidence_icons.get(quick_result.confidence, '○○○')}"
            )

            # Explanation
            self.explanation_label.setText(quick_result.explanation or "")

            # Update frame border color
            self.quick_verdict_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['surface']};
                    border: 2px solid {quick_result.color};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
        else:
            # Map primary action to emoji/verdict
            action_to_emoji = {
                "KEEP": "👍",
                "SELL": "💰",
                "STASH": "📦",
                "VENDOR": "👎",
                "EVALUATE": "🤔",
            }
            action_to_verdict = {
                "KEEP": "KEEP",
                "SELL": "SELL",
                "STASH": "MAYBE",
                "VENDOR": "VENDOR",
                "EVALUATE": "MAYBE",
            }

            action_name = verdict.primary_action.name
            emoji = action_to_emoji.get(action_name, "❓")
            word = action_to_verdict.get(action_name, "UNKNOWN")
            color = self.ACTION_COLORS.get(action_name, COLORS['text'])

            self.emoji_label.setText(emoji)
            self.verdict_word_label.setText(word)
            self.verdict_word_label.setStyleSheet(f"""
                font-size: 24px;
                font-weight: bold;
                color: {color};
            """)

            # Confidence from verdict
            confidence_icons = {"low": "○○○", "medium": "●○○", "high": "●●●"}
            self.confidence_dots_label.setText(
                f"Confidence: {confidence_icons.get(verdict.confidence, '○○○')}"
            )

            # Generate explanation from verdict
            explanation = verdict.for_you.reason or verdict.to_sell.price_range or ""
            self.explanation_label.setText(explanation)

            self.quick_verdict_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['surface']};
                    border: 2px solid {color};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)

    def _update_detailed_analysis(self, evaluation: Any) -> None:
        """Update the detailed analysis section from rare evaluation."""
        # Get tier and scores
        tier = getattr(evaluation, 'tier', 'UNKNOWN').upper()
        tier_color = self.TIER_COLORS.get(tier, COLORS['text'])
        self.detail_tier_label.setText(f"Tier: {tier}")
        self.detail_tier_label.setStyleSheet(f"font-weight: bold; color: {tier_color};")

        total = getattr(evaluation, 'total_score', 0)
        base = getattr(evaluation, 'base_score', 0)
        affix = getattr(evaluation, 'affix_score', 0)
        self.detail_scores_label.setText(f"Score: {total}/100 (Base: {base}, Affix: {affix})")

        # Matched affixes
        matched = getattr(evaluation, 'matched_affixes', [])
        tier_summary_parts = []  # For visible tier summary

        if matched:
            affix_lines = []
            for affix_match in matched[:5]:
                text = getattr(affix_match, 'mod_text', str(affix_match))[:50]
                tier_str = getattr(affix_match, 'tier', '')
                has_meta = getattr(affix_match, 'has_meta_bonus', False)
                line = f"• {text}"
                if tier_str:
                    line += f" [{tier_str}]"
                    # Add to tier summary for high-value tiers
                    if tier_str in ('T1', 'T2') or has_meta:
                        short_text = text[:25] + "..." if len(text) > 25 else text
                        color = "#22dd22" if tier_str == 'T1' else "#4488ff"
                        meta_tag = " <b style='color:#22dd22;'>META</b>" if has_meta else ""
                        tier_summary_parts.append(
                            f"<span style='color:{color};'>[{tier_str}]</span> {short_text}{meta_tag}"
                        )
                if has_meta:
                    line += " <span style='color: #22dd22;'>[META]</span>"
                affix_lines.append(line)
            self.detail_affixes_label.setText("<br>".join(affix_lines))
            self.detail_affixes_label.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.detail_affixes_label.setText("No valuable affixes detected")

        # Update visible tier summary in WHY VALUABLE section
        if tier_summary_parts:
            summary_text = "📊 <b>Key Affixes:</b> " + " • ".join(tier_summary_parts[:3])
            if len(tier_summary_parts) > 3:
                summary_text += f" <i>(+{len(tier_summary_parts) - 3} more)</i>"
            self.tier_summary_label.setText(summary_text)
            self.tier_summary_label.setVisible(True)
            self.why_section.setVisible(True)  # Ensure WHY section is visible
        else:
            self.tier_summary_label.setVisible(False)

        # Crafting potential
        open_pre = getattr(evaluation, 'open_prefixes', 0)
        open_suf = getattr(evaluation, 'open_suffixes', 0)
        if open_pre > 0 or open_suf > 0:
            self.detail_crafting_label.setText(
                f"Crafting: {open_pre} open prefix(es), {open_suf} open suffix(es)"
            )
            self.detail_crafting_label.setVisible(True)
        else:
            self.detail_crafting_label.setVisible(False)

        self.detailed_section.setVisible(True)

    def _update_cluster_section(self, evaluation: Any) -> None:
        """Update the cluster jewel section if applicable."""
        cluster_eval = getattr(evaluation, '_cluster_evaluation', None)
        if not cluster_eval:
            self.cluster_section.setVisible(False)
            return

        # Size and passives
        size = getattr(cluster_eval, 'size', 'Unknown')
        passives = getattr(cluster_eval, 'passive_count', 0)
        enchant = getattr(cluster_eval, 'enchantment', '')
        self.cluster_info_label.setText(f"{size} ({passives} passives) - {enchant}")

        # Notables
        notables = getattr(cluster_eval, 'matched_notables', [])
        if notables:
            notable_lines = []
            for notable in notables[:4]:
                name = getattr(notable, 'name', str(notable))
                tier = getattr(notable, 'tier', 'low')
                tier_color = self.NOTABLE_TIER_COLORS.get(tier, "#888888")
                tier_symbol = {"meta": "★", "high": "●", "medium": "◐", "low": "○"}.get(tier, "○")
                notable_lines.append(
                    f"<span style='color: {tier_color};'>{tier_symbol}</span> {name}"
                )
            self.cluster_notables_label.setText("<br>".join(notable_lines))
            self.cluster_notables_label.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.cluster_notables_label.setText("No matching notables")

        self.cluster_section.setVisible(True)

    def _update_unique_section(self, evaluation: Any) -> None:
        """Update the unique item section if applicable."""
        unique_eval = getattr(evaluation, '_unique_evaluation', None)
        if not unique_eval:
            self.unique_section.setVisible(False)
            return

        # Name and tier
        name = getattr(unique_eval, 'unique_name', 'Unknown')
        tier = getattr(unique_eval, 'tier', 'average')
        tier_color = self.UNIQUE_TIER_COLORS.get(tier, COLORS['text'])
        tier_symbols = {"chase": "★★★", "excellent": "★★", "good": "★", "average": "", "vendor": ""}
        symbol = tier_symbols.get(tier, "")
        self.unique_name_label.setText(f"{name} {symbol} ({tier.title()})")
        self.unique_name_label.setStyleSheet(f"font-weight: bold; color: {tier_color};")

        # Price
        has_price = getattr(unique_eval, 'has_poe_ninja_price', False)
        ninja_price = getattr(unique_eval, 'ninja_price_chaos', None)
        if has_price and ninja_price:
            self.unique_price_label.setText(f"poe.ninja: {ninja_price:.0f}c")
        else:
            estimated = getattr(unique_eval, 'estimated_value', 'Unknown')
            self.unique_price_label.setText(f"Estimated: {estimated}")

        # Details (corruption, links, factors)
        details = []
        corr_tier = getattr(unique_eval, 'corruption_tier', 'none')
        if corr_tier and corr_tier != 'none':
            details.append(f"Corruption: {corr_tier.title()}")

        link_eval = getattr(unique_eval, 'link_evaluation', None)
        if link_eval:
            links = getattr(link_eval, 'links', 0)
            if links >= 5:
                details.append(f"{links}-Link")

        factors = getattr(unique_eval, 'factors', [])
        for factor in factors[:2]:
            details.append(f"• {factor}")

        self.unique_details_label.setText("\n".join(details) if details else "")
        self.unique_section.setVisible(True)

    def clear(self) -> None:
        """Clear the verdict display."""
        self._current_verdict = None
        self._current_rare_eval = None

        # Quick verdict header
        self.emoji_label.setText("❓")
        self.verdict_word_label.setText("Waiting...")
        self.verdict_word_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['text']};
        """)
        self.confidence_dots_label.setText("")
        self.explanation_label.setText("Paste an item to get a verdict")
        self.quick_verdict_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)

        # Action badge
        self.action_label.setText("VERDICT: ---")
        self.action_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.action_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        self.confidence_label.setText("")

        # Standard sections
        self.for_you_section.set_status(False)
        self.for_you_section.set_content("Evaluate an item to see verdict")

        self.to_sell_section.set_status(False)
        self.to_sell_section.set_content("---")

        self.to_stash_section.set_status(False)
        self.to_stash_section.set_content("---")

        self.why_section.setVisible(False)
        self.tier_summary_label.setVisible(False)
        self.tier_summary_label.setText("")
        self.builds_section.setVisible(False)
        self.market_section.setVisible(False)

        # Detailed sections
        self.detailed_section.setVisible(False)
        self.detailed_section.collapse()
        self.cluster_section.setVisible(False)
        self.cluster_section.collapse()
        self.unique_section.setVisible(False)
        self.unique_section.collapse()

    def get_verdict(self) -> Optional["UnifiedVerdict"]:
        """Get the current verdict."""
        return self._current_verdict

    def get_rare_evaluation(self) -> Optional["RareItemEvaluation"]:
        """Get the current rare evaluation."""
        return self._current_rare_eval
