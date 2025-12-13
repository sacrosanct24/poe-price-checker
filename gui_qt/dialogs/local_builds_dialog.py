"""
Dialog for browsing and importing local Path of Building builds.

Allows users to scan their local PoB installation and import builds
for AI context and upgrade comparison.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QProgressBar,
    QGroupBox,
    QCheckBox,
)

if TYPE_CHECKING:
    from core.pob_local_scanner import LocalBuildInfo, PoBLocalScanner

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Background worker for scanning PoB builds folder."""

    finished = pyqtSignal(list)  # List[LocalBuildInfo]
    progress = pyqtSignal(str)

    def __init__(self, scanner: "PoBLocalScanner", load_metadata: bool = True) -> None:
        super().__init__()
        self._scanner = scanner
        self._load_metadata = load_metadata

    def run(self) -> None:
        """Scan for builds in background."""
        self.progress.emit("Scanning for builds...")

        builds = self._scanner.scan_builds(force_refresh=True)

        if self._load_metadata:
            self.progress.emit(f"Loading metadata for {len(builds)} builds...")
            for i, build in enumerate(builds):
                self._scanner.load_build_metadata(build)
                if i % 10 == 0:
                    self.progress.emit(f"Loading metadata... ({i}/{len(builds)})")

        self.finished.emit(builds)


class LocalBuildsDialog(QDialog):
    """
    Dialog for browsing and importing local PoB builds.

    Signals:
        build_imported: Emitted when a build is imported (profile_name, build_data).
    """

    build_imported = pyqtSignal(str, dict)  # name, build_data

    def __init__(self, parent: Optional["QDialog"] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Local PoB Build")
        self.setMinimumSize(800, 500)
        self.resize(900, 600)

        self._scanner: Optional["PoBLocalScanner"] = None
        self._builds: List["LocalBuildInfo"] = []
        self._worker: Optional[ScanWorker] = None

        self._setup_ui()
        self._connect_signals()

        # Auto-scan on open
        self._init_scanner()

    def _setup_ui(self) -> None:
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Path section
        path_group = QGroupBox("PoB Builds Folder")
        path_layout = QHBoxLayout(path_group)

        self._path_label = QLabel("Not detected")
        self._path_label.setWordWrap(True)
        path_layout.addWidget(self._path_label, stretch=1)

        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.setFixedWidth(80)
        path_layout.addWidget(self._browse_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedWidth(80)
        path_layout.addWidget(self._refresh_btn)

        layout.addWidget(path_group)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter by name, class, or skill...")
        search_layout.addWidget(self._search_input)
        layout.addLayout(search_layout)

        # Builds table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Build Name", "Ascendancy", "Level", "Main Skill", "Last Modified"
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)

        # Column widths
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        self._progress.setFormat("Ready")
        self._progress.setMaximum(0)  # Indeterminate
        self._progress.hide()
        layout.addWidget(self._progress)

        # Options
        options_layout = QHBoxLayout()
        self._set_active_cb = QCheckBox("Set as active build for AI context")
        self._set_active_cb.setChecked(True)
        options_layout.addWidget(self._set_active_cb)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._import_btn = QPushButton("Import Selected")
        self._import_btn.setEnabled(False)
        self._import_btn.setDefault(True)
        button_layout.addWidget(self._import_btn)

        self._cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(self._cancel_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect signal handlers."""
        self._browse_btn.clicked.connect(self._browse_folder)
        self._refresh_btn.clicked.connect(self._refresh_builds)
        self._search_input.textChanged.connect(self._filter_builds)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemDoubleClicked.connect(self._on_double_click)
        self._import_btn.clicked.connect(self._import_selected)
        self._cancel_btn.clicked.connect(self.reject)

    def _init_scanner(self) -> None:
        """Initialize the scanner and start scanning."""
        from core.pob_local_scanner import get_pob_scanner

        self._scanner = get_pob_scanner()

        if self._scanner.builds_path:
            self._path_label.setText(str(self._scanner.builds_path))
            self._start_scan()
        else:
            self._path_label.setText("PoB folder not found - click Browse to locate")

    def _browse_folder(self) -> None:
        """Let user browse for PoB builds folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select PoB Builds Folder",
            str(Path.home() / "Documents"),
        )

        if folder:
            from core.pob_local_scanner import PoBLocalScanner

            self._scanner = PoBLocalScanner(Path(folder))
            if self._scanner.builds_path:
                self._path_label.setText(str(self._scanner.builds_path))
                self._start_scan()
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Folder",
                    "The selected folder does not appear to contain PoB builds.",
                )

    def _refresh_builds(self) -> None:
        """Refresh the builds list."""
        if self._scanner:
            self._start_scan()

    def _start_scan(self) -> None:
        """Start background scan for builds."""
        if not self._scanner:
            return

        # Show progress
        self._progress.show()
        self._progress.setFormat("Scanning...")
        self._table.setEnabled(False)
        self._refresh_btn.setEnabled(False)

        # Start worker
        self._worker = ScanWorker(self._scanner)
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.start()

    def _on_scan_progress(self, message: str) -> None:
        """Handle scan progress update."""
        self._progress.setFormat(message)

    def _on_scan_finished(self, builds: List["LocalBuildInfo"]) -> None:
        """Handle scan completion."""
        self._builds = builds
        self._populate_table(builds)

        self._progress.hide()
        self._table.setEnabled(True)
        self._refresh_btn.setEnabled(True)

        self._worker = None

    def _populate_table(self, builds: List["LocalBuildInfo"]) -> None:
        """Populate the table with builds."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(builds))

        for row, build in enumerate(builds):
            # Build name
            name_item = QTableWidgetItem(build.display_name)
            name_item.setData(Qt.ItemDataRole.UserRole, row)  # Store index
            self._table.setItem(row, 0, name_item)

            # Ascendancy
            asc = build._ascendancy or build._class_name or ""
            self._table.setItem(row, 1, QTableWidgetItem(asc))

            # Level
            level = str(build._level) if build._level else ""
            level_item = QTableWidgetItem(level)
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, level_item)

            # Main skill
            skill = build._main_skill or ""
            self._table.setItem(row, 3, QTableWidgetItem(skill))

            # Last modified
            modified = build.last_modified.strftime("%Y-%m-%d %H:%M")
            self._table.setItem(row, 4, QTableWidgetItem(modified))

        self._table.setSortingEnabled(True)

    def _filter_builds(self, query: str) -> None:
        """Filter the builds table by search query."""
        if not query:
            # Show all rows
            for row in range(self._table.rowCount()):
                self._table.setRowHidden(row, False)
            return

        query_lower = query.lower()

        for row in range(self._table.rowCount()):
            # Check all columns for match
            match = False
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item and query_lower in item.text().lower():
                    match = True
                    break

            self._table.setRowHidden(row, not match)

    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        selected = self._table.selectedItems()
        self._import_btn.setEnabled(len(selected) > 0)

    def _on_double_click(self, item: QTableWidgetItem) -> None:
        """Handle double-click to import."""
        self._import_selected()

    def _import_selected(self) -> None:
        """Import the selected build."""
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        name_item = self._table.item(row, 0)
        if not name_item:
            return

        build_idx = name_item.data(Qt.ItemDataRole.UserRole)
        if build_idx is None or build_idx >= len(self._builds):
            return

        build_info = self._builds[build_idx]

        # Import the build
        if self._scanner:
            build_data = self._scanner.import_to_app(build_info)
            if build_data:
                # Add to CharacterManager
                from core.pob import CharacterManager
                from core.build_summarizer import BuildSummarizer, cache_build_summary

                manager = CharacterManager()

                # Check if already exists
                name = build_data["name"]
                if manager.get_profile(name):
                    reply = QMessageBox.question(
                        self,
                        "Build Exists",
                        f"A build named '{name}' already exists.\n\nReplace it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                # Add or update the profile
                from datetime import datetime

                profile_data = {
                    "name": name,
                    "build": build_data["build"],
                    "pob_code": "",  # Local import, no code
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "notes": f"Imported from: {build_data.get('file_path', 'local')}",
                    "categories": ["my_builds"],
                    "is_upgrade_target": self._set_active_cb.isChecked(),
                }

                # Use import_profile to handle properly
                imported_name = manager.import_profile(profile_data, overwrite=True)

                if imported_name and self._set_active_cb.isChecked():
                    manager.set_active_profile(imported_name)
                    manager.set_upgrade_target(imported_name, True)

                    # Generate and cache build summary
                    profile = manager.get_profile(imported_name)
                    if profile:
                        summarizer = BuildSummarizer()
                        summary = summarizer.summarize_profile(profile)
                        cache_build_summary(imported_name, summary)

                        logger.info(f"Imported and cached build summary for: {imported_name}")

                self.build_imported.emit(
                    imported_name or name,
                    build_data,
                )

                QMessageBox.information(
                    self,
                    "Build Imported",
                    f"Successfully imported '{name}'.\n\n"
                    f"The build is now available for AI context.",
                )

                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    f"Could not parse the build file:\n{build_info.file_path}",
                )

    def closeEvent(self, event) -> None:
        """Clean up on close."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)
        super().closeEvent(event)
