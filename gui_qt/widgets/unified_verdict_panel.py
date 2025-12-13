"""
Unified Verdict Panel Widget.

Displays the comprehensive unified verdict combining all evaluation signals.
Shows FOR YOU, TO SELL, TO STASH, WHY VALUABLE, and MARKET CONTEXT.

Part of Phase 4: Think Big features.
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

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

if TYPE_CHECKING:
    from core.unified_verdict import UnifiedVerdict, PrimaryAction

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


class UnifiedVerdictPanel(QGroupBox):
    """
    Panel displaying the unified verdict with all evaluation signals.

    Shows:
    - Primary action badge (KEEP/SELL/STASH/VENDOR)
    - FOR YOU: Upgrade status
    - TO SELL: Market value
    - TO STASH: Alt/build fit
    - WHY VALUABLE: Key factors
    - BUILDS THAT WANT THIS: Cross-build matches
    - MARKET CONTEXT: Trends and comparables
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

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Unified Verdict", parent)
        self._current_verdict: Optional["UnifiedVerdict"] = None
        self._setup_ui()
        self.clear()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Primary action badge
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
        content_layout.addWidget(self.for_you_section)

        # TO SELL section
        self.to_sell_section = VerdictSectionWidget("TO SELL:")
        content_layout.addWidget(self.to_sell_section)

        # TO STASH section
        self.to_stash_section = VerdictSectionWidget("TO STASH:")
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
        button_layout.addWidget(self.details_btn)

        layout.addLayout(button_layout)

    def set_verdict(self, verdict: "UnifiedVerdict") -> None:
        """Display a unified verdict."""
        self._current_verdict = verdict

        # Update primary action
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
            if verdict.to_sell.demand_level != "unknown":
                content += f"\nDemand: {verdict.to_sell.demand_level}"
        else:
            self.to_sell_section.set_status(False)
            content = "Low market value"
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

    def clear(self) -> None:
        """Clear the verdict display."""
        self._current_verdict = None

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

        self.for_you_section.set_status(False)
        self.for_you_section.set_content("Evaluate an item to see verdict")

        self.to_sell_section.set_status(False)
        self.to_sell_section.set_content("---")

        self.to_stash_section.set_status(False)
        self.to_stash_section.set_content("---")

        self.why_section.setVisible(False)
        self.builds_section.setVisible(False)
        self.market_section.setVisible(False)

    def get_verdict(self) -> Optional["UnifiedVerdict"]:
        """Get the current verdict."""
        return self._current_verdict
