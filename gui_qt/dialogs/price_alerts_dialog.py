"""
Price Alerts Dialog - Manage price alerts for item monitoring.

Provides a UI for:
- Viewing existing price alerts
- Creating new alerts with above/below thresholds
- Editing and deleting alerts
- Pre-filling from price check context
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QGroupBox,
    QSplitter,
    QAbstractItemView,
    QMessageBox,
)

from gui_qt.dialogs.base_dialog import BaseDialog
from gui_qt.design_system import Spacing

if TYPE_CHECKING:
    from gui_qt.services.price_alert_service import PriceAlertService

logger = logging.getLogger(__name__)


class PriceAlertsDialog(BaseDialog):
    """
    Dialog for managing price alerts.

    Features:
    - Table view of all alerts with status
    - Add/Edit/Delete alert forms
    - Pre-fill support from price check context menu
    """

    # Emitted when alerts change (for parent refresh)
    alerts_changed = pyqtSignal()

    def __init__(
        self,
        alert_service: "PriceAlertService",
        parent: Optional[QWidget] = None,
        *,
        prefill_item: Optional[str] = None,
        prefill_base_type: Optional[str] = None,
        prefill_price: Optional[float] = None,
    ):
        """
        Initialize the price alerts dialog.

        Args:
            alert_service: The PriceAlertService instance.
            parent: Parent widget.
            prefill_item: Pre-fill item name (from context menu).
            prefill_base_type: Pre-fill base type.
            prefill_price: Pre-fill with current price for threshold suggestion.
        """
        super().__init__(
            parent,
            title="Price Alerts",
            modal=False,
            remember_geometry=True,
            min_width=800,
            min_height=500,
            show_help=True,
            help_text="Monitor item prices and get notified when they cross your thresholds.",
        )

        self._service = alert_service
        self._prefill_item = prefill_item
        self._prefill_base_type = prefill_base_type
        self._prefill_price = prefill_price
        self._selected_alert_id: Optional[int] = None

        # Build UI
        self._build_ui()

        # Load alerts
        self._refresh_alerts()

        # Pre-fill if provided
        if prefill_item:
            self._item_input.setText(prefill_item)
            if prefill_base_type:
                self._base_type_input.setText(prefill_base_type)
            if prefill_price:
                # Suggest 10% below current price for "below" alerts
                self._threshold_input.setValue(prefill_price * 0.9)

        # Connect service signals
        self._service.alerts_changed.connect(self._refresh_alerts)

        # Add close button only (no primary action)
        self.add_button_row(
            primary_text="Close",
            secondary_text="",
            primary_action=self.accept,
        )

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Alerts table
        left_panel = self._build_alerts_table()
        splitter.addWidget(left_panel)

        # Right panel: Add/Edit form
        right_panel = self._build_form_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions (60% table, 40% form)
        splitter.setSizes([500, 300])

        self.add_content(splitter)

    def _build_alerts_table(self) -> QWidget:
        """Build the alerts table panel."""
        panel = QGroupBox("Active Alerts")
        layout = QVBoxLayout(panel)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Item", "Type", "Threshold", "Last Price", "Triggers", "Enabled"
        ])

        # Table settings
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        # Column sizing
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Item
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 70)   # Type
        self._table.setColumnWidth(2, 90)   # Threshold
        self._table.setColumnWidth(3, 90)   # Last Price
        self._table.setColumnWidth(4, 70)   # Triggers
        self._table.setColumnWidth(5, 70)   # Enabled

        # Style
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a35;
                gridline-color: #3a3a45;
                selection-background-color: #4a4a55;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #3a3a45;
                color: #e4e4e7;
                padding: 8px;
                border: none;
            }
        """)

        # Connect selection
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellDoubleClicked.connect(self._on_double_click)

        layout.addWidget(self._table)

        # Table buttons
        btn_layout = QHBoxLayout()

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._edit_selected)
        btn_layout.addWidget(self._edit_btn)

        self._toggle_btn = QPushButton("Toggle")
        self._toggle_btn.setEnabled(False)
        self._toggle_btn.clicked.connect(self._toggle_selected)
        btn_layout.addWidget(self._toggle_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.setProperty("destructive", True)
        self._delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh_alerts)
        btn_layout.addWidget(self._refresh_btn)

        layout.addLayout(btn_layout)

        return panel

    def _build_form_panel(self) -> QWidget:
        """Build the add/edit form panel."""
        panel = QGroupBox("Add Alert")
        layout = QVBoxLayout(panel)

        form = QFormLayout()
        form.setSpacing(Spacing.SM)

        # Item name
        self._item_input = QLineEdit()
        self._item_input.setPlaceholderText("e.g., Divine Orb, Mageblood")
        form.addRow("Item Name:", self._item_input)
        self.register_focusable(self._item_input)

        # Base type (optional)
        self._base_type_input = QLineEdit()
        self._base_type_input.setPlaceholderText("(optional)")
        form.addRow("Base Type:", self._base_type_input)

        # Alert type
        self._type_combo = QComboBox()
        self._type_combo.addItem("Price drops below", "below")
        self._type_combo.addItem("Price rises above", "above")
        form.addRow("Alert When:", self._type_combo)

        # Threshold
        self._threshold_input = QDoubleSpinBox()
        self._threshold_input.setRange(0.1, 1000000.0)
        self._threshold_input.setValue(100.0)
        self._threshold_input.setSuffix(" chaos")
        self._threshold_input.setDecimals(1)
        form.addRow("Threshold:", self._threshold_input)

        # Cooldown
        self._cooldown_input = QSpinBox()
        self._cooldown_input.setRange(10, 1440)
        self._cooldown_input.setValue(30)
        self._cooldown_input.setSuffix(" minutes")
        form.addRow("Cooldown:", self._cooldown_input)

        layout.addLayout(form)

        # Add button
        self._add_btn = QPushButton("Add Alert")
        self._add_btn.setProperty("primary", True)
        self._add_btn.clicked.connect(self._add_alert)
        layout.addWidget(self._add_btn)

        layout.addStretch()

        # Stats section
        stats_group = QGroupBox("Statistics")
        stats_layout = QFormLayout(stats_group)

        self._stats_total = QLabel("0")
        self._stats_active = QLabel("0")
        self._stats_triggers = QLabel("0")

        stats_layout.addRow("Total Alerts:", self._stats_total)
        stats_layout.addRow("Active:", self._stats_active)
        stats_layout.addRow("Total Triggers:", self._stats_triggers)

        layout.addWidget(stats_group)

        return panel

    def _refresh_alerts(self) -> None:
        """Refresh the alerts table from the service."""
        self._table.setRowCount(0)

        alerts = self._service.get_all_alerts()

        for alert in alerts:
            self._add_alert_row(alert)

        # Update stats
        self._update_stats()

    def _add_alert_row(self, alert: Dict[str, Any]) -> None:
        """Add a row to the alerts table."""
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Store alert ID in first column
        item_name = QTableWidgetItem(alert.get("item_name", ""))
        item_name.setData(Qt.ItemDataRole.UserRole, alert.get("id"))
        self._table.setItem(row, 0, item_name)

        # Alert type
        alert_type = alert.get("alert_type", "")
        type_display = "Below" if alert_type == "below" else "Above"
        self._table.setItem(row, 1, QTableWidgetItem(type_display))

        # Threshold
        threshold = alert.get("threshold_chaos", 0)
        self._table.setItem(row, 2, QTableWidgetItem(f"{threshold:.1f}c"))

        # Last price
        last_price = alert.get("last_price_chaos")
        price_str = f"{last_price:.1f}c" if last_price else "-"
        self._table.setItem(row, 3, QTableWidgetItem(price_str))

        # Trigger count
        triggers = alert.get("trigger_count", 0)
        self._table.setItem(row, 4, QTableWidgetItem(str(triggers)))

        # Enabled status
        enabled = alert.get("enabled", True)
        status_item = QTableWidgetItem("Yes" if enabled else "No")
        if not enabled:
            status_item.setForeground(Qt.GlobalColor.gray)
        self._table.setItem(row, 5, status_item)

    def _update_stats(self) -> None:
        """Update the statistics display."""
        alerts = self._service.get_all_alerts()
        active = [a for a in alerts if a.get("enabled", True)]
        total_triggers = sum(a.get("trigger_count", 0) for a in alerts)

        self._stats_total.setText(str(len(alerts)))
        self._stats_active.setText(str(len(active)))
        self._stats_triggers.setText(str(total_triggers))

    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        rows = self._table.selectionModel().selectedRows()
        has_selection = len(rows) > 0

        self._edit_btn.setEnabled(has_selection)
        self._toggle_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

        if has_selection:
            item = self._table.item(rows[0].row(), 0)
            self._selected_alert_id = item.data(Qt.ItemDataRole.UserRole)
        else:
            self._selected_alert_id = None

    def _on_double_click(self, row: int, col: int) -> None:
        """Handle double-click to edit."""
        self._edit_selected()

    def _add_alert(self) -> None:
        """Add a new alert from the form."""
        item_name = self._item_input.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Error", "Please enter an item name.")
            return

        base_type = self._base_type_input.text().strip() or None
        alert_type = self._type_combo.currentData()
        threshold = self._threshold_input.value()
        cooldown = self._cooldown_input.value()

        try:
            self._service.create_alert(
                item_name=item_name,
                alert_type=alert_type,
                threshold_chaos=threshold,
                item_base_type=base_type,
                cooldown_minutes=cooldown,
            )

            # Clear form
            self._item_input.clear()
            self._base_type_input.clear()
            self._threshold_input.setValue(100.0)

            logger.info(f"Created alert: {item_name} {alert_type} {threshold}c")

            # Refresh table
            self._refresh_alerts()
            self.alerts_changed.emit()

        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create alert: {e}")

    def _edit_selected(self) -> None:
        """Edit the selected alert."""
        if self._selected_alert_id is None:
            return

        alert = self._service.get_alert(self._selected_alert_id)
        if not alert:
            return

        # Populate form with existing values
        self._item_input.setText(alert.get("item_name", ""))
        self._base_type_input.setText(alert.get("item_base_type", "") or "")

        alert_type = alert.get("alert_type", "below")
        index = self._type_combo.findData(alert_type)
        if index >= 0:
            self._type_combo.setCurrentIndex(index)

        self._threshold_input.setValue(alert.get("threshold_chaos", 100.0))
        self._cooldown_input.setValue(alert.get("cooldown_minutes", 30))

        # Change button to "Update"
        self._add_btn.setText("Update Alert")
        self._add_btn.clicked.disconnect()
        self._add_btn.clicked.connect(lambda: self._update_alert(self._selected_alert_id))

    def _update_alert(self, alert_id: int) -> None:
        """Update an existing alert."""
        item_name = self._item_input.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Error", "Please enter an item name.")
            return

        alert_type = self._type_combo.currentData()
        threshold = self._threshold_input.value()
        cooldown = self._cooldown_input.value()

        try:
            self._service.update_alert(
                alert_id,
                alert_type=alert_type,
                threshold_chaos=threshold,
                cooldown_minutes=cooldown,
            )

            # Reset form
            self._item_input.clear()
            self._base_type_input.clear()
            self._threshold_input.setValue(100.0)
            self._add_btn.setText("Add Alert")
            self._add_btn.clicked.disconnect()
            self._add_btn.clicked.connect(self._add_alert)

            logger.info(f"Updated alert {alert_id}")

            # Refresh table
            self._refresh_alerts()
            self.alerts_changed.emit()

        except Exception as e:
            logger.error(f"Failed to update alert: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update alert: {e}")

    def _toggle_selected(self) -> None:
        """Toggle the enabled state of the selected alert."""
        if self._selected_alert_id is None:
            return

        try:
            self._service.toggle_alert(self._selected_alert_id)
            self._refresh_alerts()
            self.alerts_changed.emit()
        except Exception as e:
            logger.error(f"Failed to toggle alert: {e}")
            QMessageBox.critical(self, "Error", f"Failed to toggle alert: {e}")

    def _delete_selected(self) -> None:
        """Delete the selected alert."""
        if self._selected_alert_id is None:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this alert?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._service.delete_alert(self._selected_alert_id)
            self._selected_alert_id = None
            self._refresh_alerts()
            self.alerts_changed.emit()
        except Exception as e:
            logger.error(f"Failed to delete alert: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete alert: {e}")
