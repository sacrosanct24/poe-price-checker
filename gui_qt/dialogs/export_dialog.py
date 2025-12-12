"""
Export dialog for data export options.

Allows users to select data type, format, and date range for export.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QGroupBox,
)

from gui_qt.styles import apply_window_icon

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class ExportDialog(QDialog):
    """Dialog for exporting data to CSV or JSON."""

    DATA_TYPES = [
        ("sales", "Sales History"),
        ("price_checks", "Price Checks"),
        ("loot", "Loot Session"),
        ("rankings", "Price Rankings"),
    ]

    FORMATS = [
        ("csv", "CSV (.csv)"),
        ("json", "JSON (.json)"),
    ]

    DATE_RANGES = [
        (None, "All Time"),
        (7, "Last 7 Days"),
        (30, "Last 30 Days"),
        (90, "Last 90 Days"),
    ]

    def __init__(self, ctx: "AppContext", parent: Optional[object] = None):
        super().__init__(parent)
        self.ctx = ctx
        self._export_service = None

        self.setWindowTitle("Export Data")
        self.setMinimumWidth(400)
        apply_window_icon(self)

        self._setup_ui()

    def _get_export_service(self):
        """Get or create the export service."""
        if self._export_service is None:
            from core.services.export_service import ExportService
            self._export_service = ExportService(self.ctx.db)
        return self._export_service

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Options group
        options_group = QGroupBox("Export Options")
        options_layout = QFormLayout(options_group)

        # Data type selector
        self._data_type_combo = QComboBox()
        for key, label in self.DATA_TYPES:
            self._data_type_combo.addItem(label, key)
        self._data_type_combo.currentIndexChanged.connect(self._on_data_type_changed)
        options_layout.addRow("Data Type:", self._data_type_combo)

        # Format selector
        self._format_combo = QComboBox()
        for key, label in self.FORMATS:
            self._format_combo.addItem(label, key)
        options_layout.addRow("Format:", self._format_combo)

        # Date range selector
        self._date_range_combo = QComboBox()
        for days, label in self.DATE_RANGES:
            self._date_range_combo.addItem(label, days)
        options_layout.addRow("Date Range:", self._date_range_combo)

        layout.addWidget(options_group)

        # Rankings options (shown only for rankings data type)
        self._rankings_group = QGroupBox("Rankings Options")
        rankings_layout = QFormLayout(self._rankings_group)

        self._category_combo = QComboBox()
        self._category_combo.addItem("Currency", "currency")
        self._category_combo.addItem("Divination Cards", "divination_cards")
        self._category_combo.addItem("Unique Weapons", "unique_weapons")
        self._category_combo.addItem("Unique Armours", "unique_armours")
        self._category_combo.addItem("Unique Accessories", "unique_accessories")
        self._category_combo.addItem("Scarabs", "scarabs")
        self._category_combo.addItem("Fragments", "fragments")
        rankings_layout.addRow("Category:", self._category_combo)

        self._rankings_group.setVisible(False)
        layout.addWidget(self._rankings_group)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: palette(mid);")
        layout.addWidget(self._status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._export_btn = QPushButton("Export...")
        self._export_btn.setDefault(True)
        self._export_btn.clicked.connect(self._do_export)
        button_layout.addWidget(self._export_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _on_data_type_changed(self, index: int) -> None:
        """Handle data type selection change."""
        data_type = self._data_type_combo.currentData()

        # Show/hide rankings options
        self._rankings_group.setVisible(data_type == "rankings")

        # Disable date range for rankings
        self._date_range_combo.setEnabled(data_type != "rankings")

    def _do_export(self) -> None:
        """Perform the export."""
        data_type = self._data_type_combo.currentData()
        format = self._format_combo.currentData()
        days = self._date_range_combo.currentData()

        # Get file extension
        ext = ".csv" if format == "csv" else ".json"

        # Get default filename
        default_name = f"{data_type}_export{ext}"

        # Show file dialog
        file_filter = f"{'CSV' if format == 'csv' else 'JSON'} Files (*{ext})"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            default_name,
            file_filter
        )

        if not file_path:
            return

        # Ensure correct extension
        if not file_path.endswith(ext):
            file_path += ext

        # Show progress
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # Indeterminate
        self._export_btn.setEnabled(False)
        self._status_label.setText("Exporting...")

        try:
            service = self._get_export_service()

            # Build kwargs for export
            kwargs = {}
            if data_type == "rankings":
                kwargs["league"] = self.ctx.config.league or "Standard"
                kwargs["category"] = self._category_combo.currentData()

            result = service.export_data(
                data_type=data_type,
                format=format,
                file_path=Path(file_path),
                days=days,
                **kwargs
            )

            if result.success:
                self._status_label.setText(
                    f"Exported {result.record_count} records to {result.file_path.name}"
                )
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Successfully exported {result.record_count} records.\n\n"
                    f"File: {file_path}"
                )
                self.accept()
            else:
                self._status_label.setText(f"Export failed: {result.error}")
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    f"Failed to export data:\n{result.error}"
                )

        except Exception as e:
            logger.error(f"Export error: {e}")
            self._status_label.setText(f"Error: {e}")
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred during export:\n{str(e)}"
            )

        finally:
            self._progress.setVisible(False)
            self._export_btn.setEnabled(True)

    def set_data_type(self, data_type: str) -> None:
        """Set the data type programmatically."""
        for i in range(self._data_type_combo.count()):
            if self._data_type_combo.itemData(i) == data_type:
                self._data_type_combo.setCurrentIndex(i)
                break
