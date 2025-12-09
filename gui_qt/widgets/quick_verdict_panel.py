"""
Quick Verdict Panel - Simple keep/vendor/maybe display for casual players.

Shows a large emoji verdict with plain-English explanation.
Designed to be visible at a glance without requiring market knowledge.

Usage:
    panel = QuickVerdictPanel()
    panel.update_verdict(item, price_chaos=50.0)
"""

from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)

from gui_qt.styles import COLORS
from core.quick_verdict import (
    QuickVerdictCalculator,
    VerdictResult,
    VerdictStatistics,
    Verdict,
    VerdictThresholds,
)


class QuickVerdictPanel(QWidget):
    """
    Panel displaying simple keep/vendor/maybe verdict.

    Shows:
    - Large emoji (👍/👎/🤔)
    - One-word verdict (Keep/Vendor/Maybe)
    - Single-sentence explanation
    - Optional "Why?" expandable details

    Signals:
        details_requested: Emitted when user wants more details
        threshold_changed: Emitted when user adjusts thresholds
    """

    details_requested = pyqtSignal()
    threshold_changed = pyqtSignal(float, float)  # vendor, keep thresholds

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._calculator = QuickVerdictCalculator()
        self._current_result: Optional[VerdictResult] = None
        self._details_visible = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Main verdict container
        self._verdict_frame = QFrame()
        self._verdict_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self._verdict_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)

        verdict_layout = QVBoxLayout(self._verdict_frame)
        verdict_layout.setSpacing(4)

        # Emoji + verdict word row
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self._emoji_label = QLabel("❓")
        self._emoji_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                padding: 0;
                margin: 0;
            }
        """)
        self._emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self._emoji_label)

        # Verdict text
        verdict_text_layout = QVBoxLayout()
        verdict_text_layout.setSpacing(2)

        self._verdict_label = QLabel("Waiting...")
        self._verdict_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {COLORS['text']};
            }}
        """)
        verdict_text_layout.addWidget(self._verdict_label)

        self._confidence_label = QLabel("")
        self._confidence_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {COLORS['text_secondary']};
            }}
        """)
        verdict_text_layout.addWidget(self._confidence_label)

        top_row.addLayout(verdict_text_layout)
        top_row.addStretch()

        verdict_layout.addLayout(top_row)

        # Explanation
        self._explanation_label = QLabel("Paste an item to get a verdict")
        self._explanation_label.setWordWrap(True)
        self._explanation_label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                color: {COLORS['text']};
                padding: 8px 0;
            }}
        """)
        verdict_layout.addWidget(self._explanation_label)

        # Details section (initially hidden)
        self._details_frame = QFrame()
        self._details_frame.setVisible(False)
        self._details_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

        details_layout = QVBoxLayout(self._details_frame)
        details_layout.setContentsMargins(8, 8, 8, 8)

        self._details_title = QLabel("Why this verdict?")
        self._details_title.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: {COLORS['accent']};
                font-size: 12px;
            }}
        """)
        details_layout.addWidget(self._details_title)

        self._details_list = QLabel("")
        self._details_list.setWordWrap(True)
        self._details_list.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 11px;
            }}
        """)
        details_layout.addWidget(self._details_list)

        verdict_layout.addWidget(self._details_frame)

        # Toggle details button
        self._toggle_btn = QPushButton("Show details")
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['accent_blue']};
                border: none;
                font-size: 11px;
                text-decoration: underline;
                padding: 4px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
            }}
        """)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_details)
        verdict_layout.addWidget(self._toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self._verdict_frame)

        # Value estimate (if available)
        self._value_label = QLabel("")
        self._value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {COLORS['text_muted']};
                padding: 4px 0;
            }}
        """)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        layout.addStretch()

        # Set fixed width for sidebar
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)

    def update_verdict(
        self,
        item: Any,
        price_chaos: Optional[float] = None,
        prices: Optional[List[Tuple[str, float]]] = None,
    ) -> VerdictResult:
        """
        Update the verdict display for an item.

        Args:
            item: Parsed item object
            price_chaos: Single price estimate (optional)
            prices: Multiple (source, price) pairs (optional)

        Returns:
            The calculated VerdictResult
        """
        if prices:
            result = self._calculator.calculate_from_prices(item, prices)
        else:
            result = self._calculator.calculate(item, price_chaos)

        self._current_result = result
        self._update_display(result)
        return result

    def _update_display(self, result: VerdictResult) -> None:
        """Update UI elements with verdict result."""
        # Emoji
        self._emoji_label.setText(result.emoji)

        # Verdict word
        verdict_text = result.verdict.value.upper()
        self._verdict_label.setText(verdict_text)
        self._verdict_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {result.color};
            }}
        """)

        # Confidence
        confidence_icons = {
            "low": "○○○",
            "medium": "●○○",
            "high": "●●●",
        }
        self._confidence_label.setText(f"Confidence: {confidence_icons.get(result.confidence, '○○○')}")

        # Explanation
        self._explanation_label.setText(result.explanation)

        # Details
        if result.detailed_reasons:
            details_text = "\n".join(f"• {r}" for r in result.detailed_reasons)

            # Add meta bonus info if present
            if result.has_meta_bonus:
                meta_info = f"\n\n🔥 Meta bonus: +{result.meta_bonus_applied:.0f}"
                if result.meta_affixes_found:
                    meta_info += f" ({', '.join(result.meta_affixes_found)})"
                details_text += meta_info

            self._details_list.setText(details_text)
            self._toggle_btn.setVisible(True)
        else:
            self._toggle_btn.setVisible(False)
            self._details_frame.setVisible(False)

        # Value estimate
        if result.estimated_value is not None:
            self._value_label.setText(f"Est. value: ~{result.estimated_value:.1f}c")
            self._value_label.setVisible(True)
        else:
            self._value_label.setVisible(False)

        # Update frame border color
        self._verdict_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {result.color};
                border-radius: 8px;
                padding: 8px;
            }}
        """)

    def _toggle_details(self) -> None:
        """Toggle details visibility."""
        self._details_visible = not self._details_visible
        self._details_frame.setVisible(self._details_visible)
        self._toggle_btn.setText(
            "Hide details" if self._details_visible else "Show details"
        )

    def clear(self) -> None:
        """Clear the verdict display."""
        self._current_result = None
        self._emoji_label.setText("❓")
        self._verdict_label.setText("Waiting...")
        self._verdict_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {COLORS['text']};
            }}
        """)
        self._confidence_label.setText("")
        self._explanation_label.setText("Paste an item to get a verdict")
        self._details_frame.setVisible(False)
        self._details_visible = False
        self._toggle_btn.setText("Show details")
        self._value_label.setVisible(False)

        self._verdict_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)

    def set_thresholds(self, vendor: float, keep: float) -> None:
        """Update verdict thresholds."""
        self._calculator.thresholds.vendor_threshold = vendor
        self._calculator.thresholds.keep_threshold = keep
        self.threshold_changed.emit(vendor, keep)

    def set_meta_weights(self, meta_weights: Dict[str, Any]) -> None:
        """
        Update meta weights for smarter verdicts.

        Args:
            meta_weights: Meta weight data from RareItemEvaluator.meta_weights
        """
        self._calculator.set_meta_weights(meta_weights)

    def get_current_result(self) -> Optional[VerdictResult]:
        """Get the current verdict result."""
        return self._current_result


class CompactVerdictWidget(QWidget):
    """
    Compact single-line verdict display for table rows or tight spaces.

    Shows: [emoji] VERDICT - explanation
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._calculator = QuickVerdictCalculator()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up compact UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self._emoji_label = QLabel("❓")
        self._emoji_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self._emoji_label)

        self._text_label = QLabel("Waiting...")
        self._text_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(self._text_label)

        layout.addStretch()

    def update_verdict(self, item: Any, price_chaos: Optional[float] = None) -> None:
        """Update compact verdict display."""
        result = self._calculator.calculate(item, price_chaos)

        self._emoji_label.setText(result.emoji)
        self._text_label.setText(f"{result.verdict.value.upper()} - {result.explanation}")
        self._text_label.setStyleSheet(f"color: {result.color};")

    def set_meta_weights(self, meta_weights: Dict[str, Any]) -> None:
        """Update meta weights for smarter verdicts."""
        self._calculator.set_meta_weights(meta_weights)

    def set_thresholds(self, vendor: float, keep: float) -> None:
        """Update verdict thresholds."""
        self._calculator.set_thresholds_from_values(vendor, keep)

    def clear(self) -> None:
        """Clear the display."""
        self._emoji_label.setText("❓")
        self._text_label.setText("Waiting...")
        self._text_label.setStyleSheet(f"color: {COLORS['text']};")


class VerdictStatisticsWidget(QWidget):
    """
    Compact widget displaying verdict statistics for a session.

    Shows verdict distribution (keep/vendor/maybe counts) and
    estimated value of keep items.

    Usage:
        stats_widget = VerdictStatisticsWidget()
        stats_widget.update_stats(verdict_statistics)
    """

    stats_reset = pyqtSignal()  # Emitted when user clicks reset
    stats_changed = pyqtSignal(VerdictStatistics)  # Emitted when stats change

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._stats = VerdictStatistics()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Stats frame
        self._stats_frame = QFrame()
        self._stats_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self._stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px;
            }}
        """)

        stats_layout = QHBoxLayout(self._stats_frame)
        stats_layout.setContentsMargins(8, 4, 8, 4)
        stats_layout.setSpacing(16)

        # Session label
        session_label = QLabel("Session:")
        session_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        stats_layout.addWidget(session_label)

        # Keep count
        self._keep_label = QLabel("👍 0")
        self._keep_label.setStyleSheet(f"color: #22bb22; font-weight: bold;")
        self._keep_label.setToolTip("Items marked as KEEP")
        stats_layout.addWidget(self._keep_label)

        # Vendor count
        self._vendor_label = QLabel("👎 0")
        self._vendor_label.setStyleSheet(f"color: #bb2222; font-weight: bold;")
        self._vendor_label.setToolTip("Items marked as VENDOR")
        stats_layout.addWidget(self._vendor_label)

        # Maybe count
        self._maybe_label = QLabel("🤔 0")
        self._maybe_label.setStyleSheet(f"color: #bbbb22; font-weight: bold;")
        self._maybe_label.setToolTip("Items marked as MAYBE")
        stats_layout.addWidget(self._maybe_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(f"color: {COLORS['border']};")
        stats_layout.addWidget(separator)

        # Estimated value
        self._value_label = QLabel("Est: ~0c")
        self._value_label.setStyleSheet(f"color: {COLORS['high_value']}; font-weight: bold;")
        self._value_label.setToolTip("Estimated total value of KEEP items")
        stats_layout.addWidget(self._value_label)

        layout.addWidget(self._stats_frame)

        # Reset button
        reset_btn = QPushButton("↻")
        reset_btn.setFixedSize(24, 24)
        reset_btn.setToolTip("Reset session statistics")
        reset_btn.clicked.connect(self._on_reset_clicked)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        layout.addWidget(reset_btn)

        layout.addStretch()

    def record_verdict(self, result: VerdictResult) -> None:
        """
        Record a new verdict result and update display.

        Args:
            result: The VerdictResult to record
        """
        self._stats.record(result)
        self._update_display()
        self.stats_changed.emit(self._stats)

    def update_stats(self, stats: VerdictStatistics) -> None:
        """
        Update display with external statistics.

        Args:
            stats: Statistics to display
        """
        self._stats = stats
        self._update_display()

    def get_stats(self) -> VerdictStatistics:
        """Get current statistics."""
        return self._stats

    def _update_display(self) -> None:
        """Update the display with current statistics."""
        self._keep_label.setText(f"👍 {self._stats.keep_count}")
        self._vendor_label.setText(f"👎 {self._stats.vendor_count}")
        self._maybe_label.setText(f"🤔 {self._stats.maybe_count}")

        if self._stats.keep_value > 0:
            self._value_label.setText(f"Est: ~{self._stats.keep_value:.0f}c")
        else:
            self._value_label.setText("Est: ~0c")

        # Update tooltips with detailed info
        self._keep_label.setToolTip(
            f"Items marked as KEEP: {self._stats.keep_count}\n"
            f"Total estimated value: {self._stats.keep_value:.1f}c\n"
            f"Percentage: {self._stats.keep_percentage:.1f}%"
        )
        self._vendor_label.setToolTip(
            f"Items marked as VENDOR: {self._stats.vendor_count}\n"
            f"Percentage: {self._stats.vendor_percentage:.1f}%"
        )
        self._maybe_label.setToolTip(
            f"Items marked as MAYBE: {self._stats.maybe_count}\n"
            f"Percentage: {self._stats.maybe_percentage:.1f}%"
        )

        # Show meta bonus info if applicable
        if self._stats.items_with_meta_bonus > 0:
            meta_info = (
                f"Items with meta bonus: {self._stats.items_with_meta_bonus}\n"
                f"Average meta bonus: {self._stats.average_meta_bonus:.1f}"
            )
            self._value_label.setToolTip(
                f"Estimated total value of KEEP items: {self._stats.keep_value:.1f}c\n\n"
                f"{meta_info}"
            )

    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        self._stats.reset()
        self._update_display()
        self.stats_reset.emit()

    def reset(self) -> None:
        """Reset statistics and display."""
        self._stats.reset()
        self._update_display()
