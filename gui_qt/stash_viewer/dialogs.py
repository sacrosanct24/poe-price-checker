"""
Dialogs for stash viewer.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QTextBrowser,
    QApplication,
)

from gui_qt.styles import COLORS, apply_window_icon, get_rarity_color
from core.stash_valuator import PricedItem, PriceSource


class StashItemDetailsDialog(QDialog):
    """Dialog showing stash item details with copy functionality."""

    def __init__(self, item: PricedItem, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.item = item

        self.setWindowTitle("Item Details")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.resize(450, 400)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Item header
        name_color = get_rarity_color(self.item.rarity.lower())
        header_html = f'''
        <div style="text-align: center;">
            <p style="font-size: 16px; font-weight: bold; color: {name_color}; margin: 4px;">
                {self.item.display_name}
            </p>
            <p style="color: {COLORS["text_secondary"]}; margin: 2px;">
                {self.item.rarity} • {self.item.item_class}
            </p>
        </div>
        '''

        header_browser = QTextBrowser()
        header_browser.setMaximumHeight(80)
        header_browser.setHtml(header_html)
        header_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(header_browser)

        # Price info
        price_html = f'''
        <table style="width: 100%;">
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Stack Size:</td>
                <td style="text-align: right;">{self.item.stack_size}</td>
            </tr>
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Unit Price:</td>
                <td style="text-align: right; color: {COLORS["currency"]};">
                    {self.item.unit_price:.2f}c
                </td>
            </tr>
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Total Value:</td>
                <td style="text-align: right; font-weight: bold; color: {COLORS["high_value"]};">
                    {self.item.display_price}
                </td>
            </tr>
            <tr>
                <td style="color: {COLORS["text_secondary"]};">Price Source:</td>
                <td style="text-align: right;">
                    {"poe.ninja" if self.item.price_source == PriceSource.POE_NINJA else "poeprices" if self.item.price_source == PriceSource.POE_PRICES else "unknown"}
                </td>
            </tr>
        </table>
        '''

        price_browser = QTextBrowser()
        price_browser.setMaximumHeight(120)
        price_browser.setHtml(price_html)
        price_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        layout.addWidget(price_browser)

        # Tab info
        if self.item.tab_name:
            tab_label = QLabel(f"Found in: {self.item.tab_name}")
            tab_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(tab_label)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()

        copy_name_btn = QPushButton("Copy Name")
        copy_name_btn.clicked.connect(self._copy_name)
        btn_row.addWidget(copy_name_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _copy_name(self) -> None:
        """Copy item name to clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.item.display_name)
        QMessageBox.information(self, "Copied", "Item name copied to clipboard.")
