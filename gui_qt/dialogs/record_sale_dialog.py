"""
gui_qt.dialogs.record_sale_dialog

Dialog for recording item sales.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QPushButton,
    QWidget,
)

from gui_qt.styles import COLORS


class RecordSaleDialog(QDialog):
    """Dialog for recording an item sale."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        item_name: str = "",
        suggested_price: float = 0.0,
    ):
        super().__init__(parent)

        self.setWindowTitle("Record Sale")
        self.setMinimumWidth(350)
        self.setModal(True)

        self._item_name = item_name
        self._suggested_price = suggested_price

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Item name display
        name_label = QLabel(f"Item: {self._item_name}")
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)

        # Form
        form = QFormLayout()
        form.setSpacing(8)

        # Price input
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 999999)
        self.price_spin.setDecimals(1)
        self.price_spin.setSuffix(" c")
        self.price_spin.setValue(self._suggested_price)
        form.addRow("Sale Price:", self.price_spin)

        # Notes input
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes...")
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

    def get_values(self) -> Tuple[float, str]:
        """Get the entered values."""
        return (
            self.price_spin.value(),
            self.notes_input.text().strip(),
        )
