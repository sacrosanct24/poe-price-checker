"""
gui_qt.dialogs.item_comparison_dialog

Side-by-side item comparison dialog for PoE Price Checker.
Allows users to compare two items and see stat differences.
"""

from __future__ import annotations

import html
import logging
from typing import Any, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTextBrowser,
    QGroupBox,
    QWidget,
)

from gui_qt.styles import COLORS, apply_window_icon
from gui_qt.widgets.item_inspector import ItemInspectorWidget
from core.item_parser import ItemParser
from core.build_stat_calculator import BuildStatCalculator, BuildStats
from core.upgrade_calculator import UpgradeCalculator

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class ItemComparisonDialog(QDialog):
    """
    Dialog for comparing two items side-by-side.

    Shows both items with their stats and a summary of differences.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        app_context: Optional["AppContext"] = None,
    ):
        super().__init__(parent)
        self._app_context = app_context
        self._parser = ItemParser()

        # Store parsed items
        self._item1: Optional[Any] = None
        self._item2: Optional[Any] = None

        # Build stats for calculations (from PoB if available)
        self._build_stats: Optional[BuildStats] = None
        self._calculator: Optional[BuildStatCalculator] = None
        self._upgrade_calculator: Optional[UpgradeCalculator] = None

        self._setup_ui()
        self._load_build_stats()

        apply_window_icon(self)
        self.setWindowTitle("Item Comparison")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Main splitter for side-by-side view
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left item panel
        left_panel = self._create_item_panel("Item 1", is_left=True)
        main_splitter.addWidget(left_panel)

        # Right item panel
        right_panel = self._create_item_panel("Item 2", is_left=False)
        main_splitter.addWidget(right_panel)

        # Set equal sizes
        main_splitter.setSizes([500, 500])

        layout.addWidget(main_splitter, stretch=3)

        # Comparison summary section
        summary_group = QGroupBox("Comparison Summary")
        summary_layout = QVBoxLayout(summary_group)

        self._summary_browser = QTextBrowser()
        self._summary_browser.setMaximumHeight(180)
        self._summary_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        self._summary_browser.setHtml(
            f'<p style="color: {COLORS["text_secondary"]};">Paste or load items to compare</p>'
        )
        summary_layout.addWidget(self._summary_browser)

        layout.addWidget(summary_group, stretch=1)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        button_layout.addWidget(clear_btn)

        swap_btn = QPushButton("Swap Items")
        swap_btn.clicked.connect(self._swap_items)
        button_layout.addWidget(swap_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_item_panel(self, title: str, is_left: bool) -> QWidget:
        """Create an item panel with input and inspector."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)

        # Title
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(title_label)

        # Paste area
        paste_group = QGroupBox("Paste Item (Ctrl+C from game)")
        paste_layout = QVBoxLayout(paste_group)

        text_edit = QTextEdit()
        text_edit.setMaximumHeight(100)
        text_edit.setPlaceholderText("Paste item text here...")
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-family: monospace;
                font-size: 10px;
            }}
        """)
        paste_layout.addWidget(text_edit)

        # Parse button
        parse_btn = QPushButton("Parse Item")
        paste_layout.addWidget(parse_btn)

        layout.addWidget(paste_group)

        # Item inspector
        inspector = ItemInspectorWidget()
        inspector.setMinimumHeight(300)
        layout.addWidget(inspector, stretch=1)

        # Store references
        if is_left:
            self._text_edit1 = text_edit
            self._inspector1 = inspector
            parse_btn.clicked.connect(self._parse_item1)
            text_edit.textChanged.connect(self._on_text1_changed)
        else:
            self._text_edit2 = text_edit
            self._inspector2 = inspector
            parse_btn.clicked.connect(self._parse_item2)
            text_edit.textChanged.connect(self._on_text2_changed)

        return panel

    def _load_build_stats(self) -> None:
        """Load build stats from app context if available."""
        if self._app_context:
            build = getattr(self._app_context, 'pob_build', None)
            if build:
                self._build_stats = getattr(build, 'stats', None)
                if self._build_stats:
                    self._calculator = BuildStatCalculator(self._build_stats)
                    self._upgrade_calculator = UpgradeCalculator(self._build_stats)
                    self._inspector1.set_build_stats(self._build_stats)
                    self._inspector2.set_build_stats(self._build_stats)

    def _on_text1_changed(self) -> None:
        """Auto-parse when text changes significantly."""
        pass  # Could auto-parse on paste detection

    def _on_text2_changed(self) -> None:
        """Auto-parse when text changes significantly."""

    def _parse_item1(self) -> None:
        """Parse item 1 from text input."""
        text = self._text_edit1.toPlainText().strip()
        if not text:
            self._item1 = None
            self._inspector1.clear()
            self._update_comparison()
            return

        try:
            self._item1 = self._parser.parse(text)
            if self._item1:
                self._inspector1.set_item(self._item1)
            else:
                self._inspector1.clear()
        except Exception as e:
            logger.warning(f"Failed to parse item 1: {e}")
            self._item1 = None
            self._inspector1.clear()

        self._update_comparison()

    def _parse_item2(self) -> None:
        """Parse item 2 from text input."""
        text = self._text_edit2.toPlainText().strip()
        if not text:
            self._item2 = None
            self._inspector2.clear()
            self._update_comparison()
            return

        try:
            self._item2 = self._parser.parse(text)
            if self._item2:
                self._inspector2.set_item(self._item2)
            else:
                self._inspector2.clear()
        except Exception as e:
            logger.warning(f"Failed to parse item 2: {e}")
            self._item2 = None
            self._inspector2.clear()

        self._update_comparison()

    def _update_comparison(self) -> None:
        """Update the comparison summary."""
        if not self._item1 and not self._item2:
            self._summary_browser.setHtml(
                f'<p style="color: {COLORS["text_secondary"]};">Paste or load items to compare</p>'
            )
            return

        if not self._item1 or not self._item2:
            which = "Item 1" if not self._item1 else "Item 2"
            self._summary_browser.setHtml(
                f'<p style="color: {COLORS["text_secondary"]};">Waiting for {which}...</p>'
            )
            return

        # Generate comparison HTML
        html_content = self._generate_comparison_html()
        self._summary_browser.setHtml(html_content)

    def _generate_comparison_html(self) -> str:
        """Generate HTML comparison summary."""
        if not self._item1 or not self._item2:
            return ""

        html_parts = []

        # Header
        name1 = html.escape(str(getattr(self._item1, 'name', '') or getattr(self._item1, 'base_type', 'Item 1')))
        name2 = html.escape(str(getattr(self._item2, 'name', '') or getattr(self._item2, 'base_type', 'Item 2')))

        html_parts.append(
            f'<p style="font-weight: bold; color: {COLORS["accent"]};">'
            f'Comparing: <span style="color: {COLORS["rare"]};">{name1}</span> vs '
            f'<span style="color: {COLORS["rare"]};">{name2}</span>'
            f'</p>'
        )

        # Get mods for both items
        mods1 = self._get_all_mods(self._item1)
        mods2 = self._get_all_mods(self._item2)

        # Calculate stat differences if we have a calculator
        if self._upgrade_calculator:
            comparison = self._upgrade_calculator.compare_items(mods2, mods1)

            # Overall verdict
            if comparison["is_upgrade"]:
                verdict = f'<span style="color: {COLORS.get("currency", "#ffcc00")}; font-weight: bold;">Item 2 is an UPGRADE</span>'
            elif comparison["is_downgrade"]:
                verdict = f'<span style="color: {COLORS.get("corrupted", "#ff4444")}; font-weight: bold;">Item 2 is a DOWNGRADE</span>'
            else:
                verdict = f'<span style="color: {COLORS["text_secondary"]}; font-weight: bold;">Items are similar (SIDEGRADE)</span>'

            html_parts.append(f'<p style="margin: 8px 0;">{verdict}</p>')

            # Summary
            if comparison["summary"] and comparison["summary"] != "No significant change":
                html_parts.append(
                    f'<p style="color: {COLORS["text"]}; margin: 4px 0;">{html.escape(comparison["summary"])}</p>'
                )

            # Improvements (Item 2 gains over Item 1)
            improvements = comparison.get("improvements", [])
            if improvements:
                html_parts.append(
                    f'<p style="color: {COLORS.get("currency", "#ffcc00")}; font-weight: bold; margin: 8px 0 4px 0;">'
                    f'Item 2 Gains:</p>'
                )
                for imp in improvements[:8]:
                    html_parts.append(
                        f'<p style="color: {COLORS.get("currency", "#ffcc00")}; margin: 2px 0 2px 12px;">+ {html.escape(imp)}</p>'
                    )

            # Losses (Item 2 loses vs Item 1)
            losses = comparison.get("losses", [])
            if losses:
                html_parts.append(
                    f'<p style="color: {COLORS.get("corrupted", "#ff4444")}; font-weight: bold; margin: 8px 0 4px 0;">'
                    f'Item 2 Loses:</p>'
                )
                for loss in losses[:8]:
                    html_parts.append(
                        f'<p style="color: {COLORS.get("corrupted", "#ff4444")}; margin: 2px 0 2px 12px;">- {html.escape(loss)}</p>'
                    )
        else:
            # Basic mod comparison without build stats
            html_parts.append(self._basic_mod_comparison(mods1, mods2))

        return "\n".join(html_parts)

    def _get_all_mods(self, item: Any) -> List[str]:
        """Extract all mods from an item."""
        if not item:
            return []

        implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", []) or []
        explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", []) or []
        enchants = getattr(item, "enchants", []) or []

        return list(implicits) + list(explicits) + list(enchants)

    def _basic_mod_comparison(self, mods1: List[str], mods2: List[str]) -> str:
        """Generate basic mod comparison without build stats."""
        html_parts = []

        # Find unique mods
        set1 = set(mods1)
        set2 = set(mods2)

        only_in_1 = set1 - set2
        only_in_2 = set2 - set1
        common = set1 & set2

        html_parts.append(
            f'<p style="color: {COLORS["text_secondary"]}; margin: 8px 0;">'
            f'Common mods: {len(common)} | Unique to Item 1: {len(only_in_1)} | Unique to Item 2: {len(only_in_2)}'
            f'</p>'
        )

        if only_in_1:
            html_parts.append(
                f'<p style="color: {COLORS.get("corrupted", "#ff4444")}; font-weight: bold; margin: 8px 0 4px 0;">'
                f'Only in Item 1:</p>'
            )
            for mod in list(only_in_1)[:5]:
                html_parts.append(
                    f'<p style="color: {COLORS.get("corrupted", "#ff4444")}; margin: 2px 0 2px 12px;">- {html.escape(mod)}</p>'
                )

        if only_in_2:
            html_parts.append(
                f'<p style="color: {COLORS.get("currency", "#ffcc00")}; font-weight: bold; margin: 8px 0 4px 0;">'
                f'Only in Item 2:</p>'
            )
            for mod in list(only_in_2)[:5]:
                html_parts.append(
                    f'<p style="color: {COLORS.get("currency", "#ffcc00")}; margin: 2px 0 2px 12px;">+ {html.escape(mod)}</p>'
                )

        return "\n".join(html_parts)

    def _swap_items(self) -> None:
        """Swap item 1 and item 2."""
        # Swap text
        text1 = self._text_edit1.toPlainText()
        text2 = self._text_edit2.toPlainText()
        self._text_edit1.setPlainText(text2)
        self._text_edit2.setPlainText(text1)

        # Swap parsed items
        self._item1, self._item2 = self._item2, self._item1

        # Update inspectors
        if self._item1:
            self._inspector1.set_item(self._item1)
        else:
            self._inspector1.clear()

        if self._item2:
            self._inspector2.set_item(self._item2)
        else:
            self._inspector2.clear()

        self._update_comparison()

    def _clear_all(self) -> None:
        """Clear all items."""
        self._text_edit1.clear()
        self._text_edit2.clear()
        self._item1 = None
        self._item2 = None
        self._inspector1.clear()
        self._inspector2.clear()
        self._update_comparison()

    def set_item1(self, item: Any) -> None:
        """Set item 1 programmatically."""
        self._item1 = item
        if item:
            self._inspector1.set_item(item)
            # Try to set the raw text if available
            raw_text = getattr(item, 'raw_text', None)
            if raw_text:
                self._text_edit1.setPlainText(raw_text)
        self._update_comparison()

    def set_item2(self, item: Any) -> None:
        """Set item 2 programmatically."""
        self._item2 = item
        if item:
            self._inspector2.set_item(item)
            raw_text = getattr(item, 'raw_text', None)
            if raw_text:
                self._text_edit2.setPlainText(raw_text)
        self._update_comparison()
