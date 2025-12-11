"""
Upgrade Finder Dialog.

Dialog for finding gear upgrades within a budget constraint.
Shows current gear, finds upgrades via trade API, and ranks by impact.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QWidget,
    QGroupBox,
    QTextBrowser,
    QProgressBar,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QCheckBox,
)

from gui_qt.styles import COLORS, apply_window_icon
from core.pob import CharacterManager
from core.upgrade_finder import (
    UpgradeFinderService,
    UpgradeFinderResult,
    UpgradeCandidate,
)

logger = logging.getLogger(__name__)


class UpgradeSearchWorker(QThread):
    """Worker thread for performing upgrade searches."""

    finished = pyqtSignal(object)  # UpgradeFinderResult
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    slot_progress = pyqtSignal(str, int, int)  # slot_name, current, total

    def __init__(
        self,
        service: UpgradeFinderService,
        profile_name: str,
        budget_chaos: float,
        slots: List[str],
        max_results: int,
        parent=None,
    ):
        super().__init__(parent)
        self.service = service
        self.profile_name = profile_name
        self.budget_chaos = budget_chaos
        self.slots = slots
        self.max_results = max_results

    def run(self):
        """Perform the upgrade search."""
        try:
            self.progress.emit("Starting upgrade search...")

            result = self.service.find_upgrades(
                profile_name=self.profile_name,
                budget_chaos=self.budget_chaos,
                slots=self.slots,
                max_results_per_slot=self.max_results,
            )

            self.finished.emit(result)

        except Exception as e:
            logger.exception("Upgrade search failed")
            self.error.emit(str(e))


class UpgradeFinderDialog(QDialog):
    """Dialog for finding gear upgrades within a budget."""

    # Default slots to search
    SEARCHABLE_SLOTS = [
        "Helmet", "Body Armour", "Gloves", "Boots",
        "Belt", "Ring", "Amulet"
    ]

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        character_manager: Optional[CharacterManager] = None,
    ):
        super().__init__(parent)
        logger.info("UpgradeFinderDialog.__init__ started")

        self.character_manager = character_manager
        self._service: Optional[UpgradeFinderService] = None
        self._search_worker: Optional[UpgradeSearchWorker] = None
        self._current_result: Optional[UpgradeFinderResult] = None
        self._slot_checkboxes: Dict[str, QCheckBox] = {}

        self.setWindowTitle("Upgrade Finder")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        self.resize(1000, 800)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_profiles()

        logger.info("UpgradeFinderDialog.__init__ completed")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === Top Controls ===
        controls_group = QGroupBox("Search Settings")
        controls_layout = QVBoxLayout(controls_group)

        # Profile and budget row
        top_row = QHBoxLayout()

        top_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        top_row.addWidget(self.profile_combo)

        top_row.addSpacing(20)

        top_row.addWidget(QLabel("Budget (chaos):"))
        self.budget_spin = QSpinBox()
        self.budget_spin.setRange(1, 100000)
        self.budget_spin.setValue(500)
        self.budget_spin.setSingleStep(50)
        self.budget_spin.setMinimumWidth(100)
        top_row.addWidget(self.budget_spin)

        top_row.addSpacing(20)

        top_row.addWidget(QLabel("Max Results:"))
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(5, 50)
        self.max_results_spin.setValue(10)
        self.max_results_spin.setMinimumWidth(60)
        top_row.addWidget(self.max_results_spin)

        top_row.addStretch()
        controls_layout.addLayout(top_row)

        # Slot selection row
        slots_row = QHBoxLayout()
        slots_row.addWidget(QLabel("Slots:"))

        for slot in self.SEARCHABLE_SLOTS:
            checkbox = QCheckBox(slot)
            checkbox.setChecked(True)
            self._slot_checkboxes[slot] = checkbox
            slots_row.addWidget(checkbox)

        slots_row.addStretch()

        # Select all / none buttons
        select_all_btn = QPushButton("All")
        select_all_btn.setMaximumWidth(50)
        select_all_btn.clicked.connect(self._select_all_slots)
        slots_row.addWidget(select_all_btn)

        select_none_btn = QPushButton("None")
        select_none_btn.setMaximumWidth(50)
        select_none_btn.clicked.connect(self._select_no_slots)
        slots_row.addWidget(select_none_btn)

        controls_layout.addLayout(slots_row)

        layout.addWidget(controls_group)

        # === Search Button ===
        search_row = QHBoxLayout()
        search_row.addStretch()

        self.search_btn = QPushButton("Find Upgrades")
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: black;
                font-weight: bold;
                padding: 12px 30px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {COLORS["accent_hover"]}; }}
            QPushButton:disabled {{ background-color: {COLORS["surface"]}; color: {COLORS["text_secondary"]}; }}
        """)
        self.search_btn.clicked.connect(self._start_search)
        search_row.addWidget(self.search_btn)

        search_row.addStretch()
        layout.addLayout(search_row)

        # === Progress Bar ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # === Results Area (Splitter) ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Results table
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        results_label = QLabel("Best Upgrades")
        results_label.setStyleSheet(f"font-weight: bold; color: {COLORS['accent']};")
        results_layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Slot", "Item", "Price", "Life", "Res", "Score"
        ])
        header = self.results_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.results_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.results_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                gridline-color: {COLORS["border"]};
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS["accent_blue"]};
            }}
            QHeaderView::section {{
                background-color: {COLORS["background"]};
                padding: 6px;
                border: 1px solid {COLORS["border"]};
                font-weight: bold;
            }}
        """)
        results_layout.addWidget(self.results_table)

        splitter.addWidget(results_widget)

        # Right: Item details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)

        details_label = QLabel("Item Details")
        details_label.setStyleSheet(f"font-weight: bold; color: {COLORS['accent']};")
        details_layout.addWidget(details_label)

        self.details_browser = QTextBrowser()
        self.details_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        details_layout.addWidget(self.details_browser)

        splitter.addWidget(details_widget)

        # Set splitter sizes (60% table, 40% details)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, stretch=1)

        # === Summary ===
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # === Bottom Buttons ===
        button_row = QHBoxLayout()
        button_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)

        layout.addLayout(button_row)

        # Initial state
        self._show_no_results()

    def _load_profiles(self) -> None:
        """Load saved profiles into combo box."""
        self.profile_combo.blockSignals(True)

        if not self.character_manager:
            self.profile_combo.addItem("No profiles available")
            self.profile_combo.setEnabled(False)
            self.search_btn.setEnabled(False)
            self.profile_combo.blockSignals(False)
            return

        profiles = self.character_manager.list_profiles()
        if not profiles:
            self.profile_combo.addItem("No profiles saved")
            self.profile_combo.setEnabled(False)
            self.search_btn.setEnabled(False)
            self.profile_combo.blockSignals(False)
            return

        for profile_name in profiles:
            self.profile_combo.addItem(profile_name)

        # Select active profile
        active_profile = self.character_manager.get_active_profile()
        if active_profile:
            idx = self.profile_combo.findText(active_profile.name)
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)

        self.profile_combo.blockSignals(False)

        # Initialize service
        self._init_service()

    def _init_service(self) -> None:
        """Initialize the upgrade finder service."""
        if not self.character_manager:
            return

        try:
            # Try to detect current league
            league = "Standard"
            try:
                from data_sources.pricing.poe_ninja import PoeNinjaAPI
                api = PoeNinjaAPI()
                detected = api.detect_current_league()
                if detected:
                    league = detected
            except Exception as e:
                logger.debug(f"Failed to detect league: {e}")

            self._service = UpgradeFinderService(
                character_manager=self.character_manager,
                league=league,
            )
            logger.info(f"Initialized UpgradeFinderService for league: {league}")

        except Exception as e:
            logger.exception("Failed to initialize upgrade finder service")

    def _on_profile_changed(self, profile_name: str) -> None:
        """Handle profile selection change."""
        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            self.search_btn.setEnabled(False)
            return

        self.search_btn.setEnabled(True)
        self._show_no_results()

    def _select_all_slots(self) -> None:
        """Select all slot checkboxes."""
        for checkbox in self._slot_checkboxes.values():
            checkbox.setChecked(True)

    def _select_no_slots(self) -> None:
        """Deselect all slot checkboxes."""
        for checkbox in self._slot_checkboxes.values():
            checkbox.setChecked(False)

    def _get_selected_slots(self) -> List[str]:
        """Get list of selected slots."""
        return [
            slot for slot, checkbox in self._slot_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _start_search(self) -> None:
        """Start the upgrade search."""
        if self._search_worker and self._search_worker.isRunning():
            return

        if not self._service:
            QMessageBox.warning(self, "Error", "Upgrade finder service not initialized.")
            return

        profile_name = self.profile_combo.currentText()
        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            return

        selected_slots = self._get_selected_slots()
        if not selected_slots:
            QMessageBox.warning(self, "No Slots", "Please select at least one equipment slot.")
            return

        budget = self.budget_spin.value()
        max_results = self.max_results_spin.value()

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Searching for upgrades...")
        self.search_btn.setEnabled(False)

        # Clear previous results
        self.results_table.setRowCount(0)
        self.details_browser.clear()

        # Start worker
        self._search_worker = UpgradeSearchWorker(
            service=self._service,
            profile_name=profile_name,
            budget_chaos=budget,
            slots=selected_slots,
            max_results=max_results,
            parent=self,
        )
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.progress.connect(self._on_search_progress)
        self._search_worker.start()

    def _on_search_progress(self, message: str) -> None:
        """Handle search progress update."""
        self.progress_bar.setFormat(message)

    def _on_search_finished(self, result: UpgradeFinderResult) -> None:
        """Handle search completion."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)

        self._current_result = result
        self._display_results(result)

    def _on_search_error(self, error: str) -> None:
        """Handle search error."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)

        QMessageBox.critical(self, "Search Error", f"Upgrade search failed:\n{error}")
        self._show_no_results()

    def _display_results(self, result: UpgradeFinderResult) -> None:
        """Display search results in the table."""
        # Get best upgrades across all slots
        best_upgrades = result.get_best_upgrades(limit=50)

        if not best_upgrades:
            self._show_no_results()
            self.summary_label.setText(
                f"No upgrades found under {int(result.budget_chaos)} chaos. "
                "Try increasing budget or relaxing stat requirements."
            )
            return

        self.results_table.setRowCount(len(best_upgrades))

        for row, (slot, candidate) in enumerate(best_upgrades):
            # Slot
            slot_item = QTableWidgetItem(slot)
            slot_item.setData(Qt.ItemDataRole.UserRole, (slot, candidate))
            self.results_table.setItem(row, 0, slot_item)

            # Item name
            name_item = QTableWidgetItem(candidate.name[:40])
            name_item.setToolTip(candidate.name)
            self.results_table.setItem(row, 1, name_item)

            # Price
            price_item = QTableWidgetItem(candidate.price_display)
            price_item.setForeground(
                Qt.GlobalColor.yellow if "divine" in candidate.price_display.lower()
                else Qt.GlobalColor.white
            )
            self.results_table.setItem(row, 2, price_item)

            # Life delta
            life_delta: float = 0.0
            if candidate.upgrade_impact:
                life_delta = candidate.upgrade_impact.effective_life_delta
            life_text = f"+{int(life_delta)}" if life_delta > 0 else str(int(life_delta))
            life_item = QTableWidgetItem(life_text)
            if life_delta > 0:
                life_item.setForeground(Qt.GlobalColor.green)
            elif life_delta < 0:
                life_item.setForeground(Qt.GlobalColor.red)
            self.results_table.setItem(row, 3, life_item)

            # Res delta
            res_delta: float = 0.0
            if candidate.upgrade_impact:
                res_delta = (
                    candidate.upgrade_impact.fire_res_delta +
                    candidate.upgrade_impact.cold_res_delta +
                    candidate.upgrade_impact.lightning_res_delta +
                    candidate.upgrade_impact.chaos_res_delta
                )
            res_text = f"+{int(res_delta)}%" if res_delta > 0 else f"{int(res_delta)}%"
            res_item = QTableWidgetItem(res_text)
            if res_delta > 0:
                res_item.setForeground(Qt.GlobalColor.green)
            elif res_delta < 0:
                res_item.setForeground(Qt.GlobalColor.red)
            self.results_table.setItem(row, 4, res_item)

            # Score
            score_item = QTableWidgetItem(f"{candidate.total_score:.0f}")
            if candidate.total_score > 50:
                score_item.setForeground(Qt.GlobalColor.green)
            elif candidate.total_score > 20:
                score_item.setForeground(Qt.GlobalColor.yellow)
            self.results_table.setItem(row, 5, score_item)

        # Summary
        self.summary_label.setText(
            f"Found {result.total_candidates} potential upgrades across "
            f"{len(result.slot_results)} slots in {result.search_time_seconds:.1f}s. "
            f"Budget: {int(result.budget_chaos)} chaos."
        )

        # Select first row
        if self.results_table.rowCount() > 0:
            self.results_table.selectRow(0)

    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        selected = self.results_table.selectedItems()
        if not selected:
            self.details_browser.clear()
            return

        # Get data from first column of selected row
        row = selected[0].row()
        first_item = self.results_table.item(row, 0)
        if not first_item:
            return
        data = first_item.data(Qt.ItemDataRole.UserRole)

        if data:
            slot, candidate = data
            self._show_candidate_details(slot, candidate)

    def _show_candidate_details(self, slot: str, candidate: UpgradeCandidate) -> None:
        """Show detailed info for a candidate."""
        html = f"""
        <h3 style="color: {COLORS['rare']}; margin: 0;">{candidate.name}</h3>
        <p style="color: {COLORS['text_secondary']}; margin: 4px 0;">
            {candidate.base_type} | iLvl {candidate.item_level} | {slot}
        </p>
        <p style="color: {COLORS['currency']}; font-weight: bold; margin: 8px 0;">
            Price: {candidate.price_display}
        </p>
        """

        # Show current item if available
        if self._current_result:
            slot_result = self._current_result.slot_results.get(slot)
            if slot_result and slot_result.current_item:
                current = slot_result.current_item
                html += f"""
                <h4 style="color: {COLORS['text_secondary']}; margin: 12px 0 4px 0;">
                    Current: {current.display_name}
                </h4>
                """

        # Mods
        html += f'<h4 style="color: {COLORS["accent"]}; margin: 12px 0 4px 0;">Mods:</h4>'

        if candidate.implicit_mods:
            for mod in candidate.implicit_mods:
                html += f'<p style="color: {COLORS["magic"]}; margin: 2px 0 2px 8px;">• {mod} (implicit)</p>'

        for mod in candidate.explicit_mods:
            html += f'<p style="color: {COLORS["magic"]}; margin: 2px 0 2px 8px;">• {mod}</p>'

        # Upgrade impact
        if candidate.upgrade_impact:
            impact = candidate.upgrade_impact
            html += f'<h4 style="color: {COLORS["accent"]}; margin: 12px 0 4px 0;">Upgrade Impact:</h4>'

            if impact.improvements:
                html += f'<p style="color: {COLORS["high_value"]}; margin: 4px 0;">Improvements:</p>'
                for imp in impact.improvements:
                    html += f'<p style="color: {COLORS["high_value"]}; margin: 2px 0 2px 16px;">+ {imp}</p>'

            if impact.losses:
                html += f'<p style="color: {COLORS["corrupted"]}; margin: 4px 0;">Losses:</p>'
                for loss in impact.losses:
                    html += f'<p style="color: {COLORS["corrupted"]}; margin: 2px 0 2px 16px;">{loss}</p>'

            html += f'<p style="margin: 8px 0;"><b>Upgrade Score:</b> {impact.upgrade_score:.0f}</p>'

        # DPS impact
        if candidate.dps_impact and candidate.dps_percent_change != 0:
            html += f'<h4 style="color: {COLORS["accent"]}; margin: 12px 0 4px 0;">DPS Impact:</h4>'
            sign = "+" if candidate.dps_percent_change > 0 else ""
            color = COLORS["high_value"] if candidate.dps_percent_change > 0 else COLORS["corrupted"]
            html += f'<p style="color: {color}; margin: 4px 0;">{sign}{candidate.dps_percent_change:.1f}% DPS</p>'

        # Total score
        html += f"""
        <div style="margin-top: 16px; padding: 8px; background-color: {COLORS['background']}; border-radius: 4px;">
            <p style="font-weight: bold; margin: 0;">
                Total Score: <span style="color: {COLORS['accent']};">{candidate.total_score:.0f}</span>
            </p>
        </div>
        """

        self.details_browser.setHtml(html)

    def _show_no_results(self) -> None:
        """Show empty state."""
        self.results_table.setRowCount(0)
        self.details_browser.setHtml(f"""
            <p style="color: {COLORS['text_secondary']}; text-align: center; margin-top: 40px;">
                Select a profile and click "Find Upgrades" to search for gear improvements.
            </p>
        """)
        self.summary_label.setText(
            "Configure your search and click Find Upgrades to begin."
        )
