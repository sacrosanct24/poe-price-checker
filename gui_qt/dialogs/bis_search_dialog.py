"""
gui_qt.dialogs.bis_search_dialog

Dialog for searching best-in-slot items based on build requirements.
Features:
- Trade Search: Find items on pathofexile.com/trade
- Guide Gear: See what your reference build recommends
- Ideal Rare: See ideal affix tiers for each slot
"""

from __future__ import annotations

import json
import logging
import webbrowser
from typing import Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal
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
    QTabWidget,
    QSpinBox,
)

from gui_qt.styles import COLORS, apply_window_icon
from core.bis_calculator import BiSCalculator, BiSRequirements, build_trade_query, EQUIPMENT_SLOTS
from core.build_stat_calculator import BuildStats
from core.pob import CharacterManager
from core.build_priorities import BuildPriorities
from core.affix_tier_calculator import AffixTierCalculator
from core.guide_gear_extractor import GuideGearExtractor, GuideGearSummary, ItemSetInfo

logger = logging.getLogger(__name__)


class TradeSearchWorker(QThread):
    """Worker thread for performing trade searches."""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, query: Dict, league: str, parent=None):
        super().__init__(parent)
        self.query = query
        self.league = league

    def run(self):
        """Perform the trade search."""
        try:
            from data_sources.pricing.trade_api import TradeApiSource

            self.progress.emit("Connecting to trade API...")
            source = TradeApiSource(league=self.league)
            self.progress.emit("Searching for items...")

            search_id, result_ids = source._search(self.query, max_results=20)
            if not result_ids:
                self.finished.emit([])
                return

            self.progress.emit(f"Fetching {len(result_ids)} listings...")
            listings = source._fetch_listings(search_id, result_ids)

            results = []
            for listing in listings:
                item_data = listing.get("item", {})
                listing_data = listing.get("listing", {})
                price_data = listing_data.get("price", {})

                item_name = item_data.get("name", "") or ""
                type_line = item_data.get("typeLine", "") or ""
                full_name = f"{item_name} {type_line}".strip()

                amount = price_data.get("amount", 0)
                currency = price_data.get("currency", "")

                results.append({
                    "name": full_name,
                    "price": f"{amount} {currency}",
                    "explicit_mods": item_data.get("explicitMods", []),
                    "implicit_mods": item_data.get("implicitMods", []),
                    "ilvl": item_data.get("ilvl", 0),
                    "listing_id": listing.get("id", ""),
                })

            self.finished.emit(results)

        except Exception as e:
            logger.exception("Trade search failed")
            self.error.emit(str(e))


class BiSSearchDialog(QDialog):
    """Dialog for searching best-in-slot items based on build requirements."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        character_manager: Optional[CharacterManager] = None,
    ):
        super().__init__(parent)
        logger.info("BiSSearchDialog.__init__ started")

        try:
            self.character_manager = character_manager
            self._calculator: Optional[BiSCalculator] = None
            self._current_requirements: Optional[BiSRequirements] = None
            self._current_priorities: Optional[BuildPriorities] = None
            self._search_worker: Optional[TradeSearchWorker] = None
            self._guide_gear: Optional[GuideGearSummary] = None

            logger.info("Creating AffixTierCalculator")
            self._tier_calculator = AffixTierCalculator()

            logger.info("Creating GuideGearExtractor")
            self._gear_extractor = GuideGearExtractor(character_manager)

            self.setWindowTitle("Find BiS Items")
            self.setMinimumWidth(600)
            self.setMinimumHeight(500)
            self.resize(850, 750)  # Good default size
            self.setSizeGripEnabled(True)  # Show resize grip
            apply_window_icon(self)

            logger.info("Creating widgets")
            self._create_widgets()

            logger.info("Loading profiles")
            self._load_profiles()

            logger.info("BiSSearchDialog.__init__ completed")
        except Exception as e:
            logger.exception(f"BiSSearchDialog.__init__ failed: {e}")
            raise

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        logger.info("_create_widgets started")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === Profile Selection ===
        profile_group = QGroupBox("Build Profile")
        profile_layout = QHBoxLayout(profile_group)

        profile_layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_layout.addWidget(self.profile_combo, stretch=1)

        self.edit_priorities_btn = QPushButton("Edit Priorities")
        self.edit_priorities_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["accent_blue"]};
                color: {COLORS["accent_blue"]};
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS["accent_blue"]};
                color: white;
            }}
        """)
        self.edit_priorities_btn.clicked.connect(self._open_priorities_editor)
        profile_layout.addWidget(self.edit_priorities_btn)

        layout.addWidget(profile_group)

        # === Build Analysis (condensed) ===
        self.analysis_label = QLabel()
        self.analysis_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        self.analysis_label.setWordWrap(True)
        layout.addWidget(self.analysis_label)

        # === Tab Widget ===
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                background-color: {COLORS["background"]};
            }}
            QTabBar::tab {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS["accent_blue"]};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS["surface_hover"]};
            }}
        """)

        # Create tabs
        logger.info("Creating search tab")
        self._create_search_tab()
        logger.info("Creating guide gear tab")
        self._create_guide_gear_tab()
        logger.info("Creating ideal rare tab")
        self._create_ideal_rare_tab()
        logger.info("All tabs created")

        layout.addWidget(self.tab_widget, stretch=1)

        # === Close Button ===
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _create_search_tab(self) -> None:
        """Create the Trade Search tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Slot Selection
        slot_row = QHBoxLayout()
        slot_row.addWidget(QLabel("Equipment Slot:"))
        self.slot_combo = QComboBox()
        self.slot_combo.blockSignals(True)
        for slot in EQUIPMENT_SLOTS.keys():
            self.slot_combo.addItem(slot)
        self.slot_combo.blockSignals(False)
        self.slot_combo.currentTextChanged.connect(self._on_slot_changed)
        slot_row.addWidget(self.slot_combo, stretch=1)
        layout.addLayout(slot_row)

        # Requirements Preview
        req_group = QGroupBox("Search Requirements")
        req_layout = QVBoxLayout(req_group)
        self.requirements_browser = QTextBrowser()
        self.requirements_browser.setMaximumHeight(150)
        self.requirements_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        req_layout.addWidget(self.requirements_browser)
        layout.addWidget(req_group)

        # Search Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.browser_btn = QPushButton("Open in Browser")
        self.browser_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent_blue"]};
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{ background-color: #4bb5e8; }}
        """)
        self.browser_btn.clicked.connect(self._open_in_browser)
        button_row.addWidget(self.browser_btn)

        self.search_btn = QPushButton("Search In-App")
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: black;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{ background-color: {COLORS["accent_hover"]}; }}
        """)
        self.search_btn.clicked.connect(self._search_in_app)
        button_row.addWidget(self.search_btn)

        button_row.addStretch()
        layout.addLayout(button_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)
        self.results_browser = QTextBrowser()
        self.results_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
        """)
        results_layout.addWidget(self.results_browser)
        layout.addWidget(results_group, stretch=1)

        self.tab_widget.addTab(tab, "Trade Search")

    def _create_guide_gear_tab(self) -> None:
        """Create the Guide Gear tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Reference build selector
        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel("Reference Build:"))
        self.ref_profile_combo = QComboBox()
        self.ref_profile_combo.currentTextChanged.connect(self._on_ref_profile_changed)
        ref_row.addWidget(self.ref_profile_combo, stretch=1)
        layout.addLayout(ref_row)

        # Item set (loadout) selector row - initially hidden
        self.item_set_row = QWidget()
        item_set_layout = QHBoxLayout(self.item_set_row)
        item_set_layout.setContentsMargins(0, 0, 0, 0)
        item_set_layout.addWidget(QLabel("Item Set (Loadout):"))
        self.item_set_combo = QComboBox()
        self.item_set_combo.currentIndexChanged.connect(self._on_item_set_changed)
        item_set_layout.addWidget(self.item_set_combo, stretch=1)
        self.item_set_row.setVisible(False)
        layout.addWidget(self.item_set_row)

        # Item set info label
        self.item_set_info_label = QLabel("")
        self.item_set_info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        self.item_set_info_label.setVisible(False)
        layout.addWidget(self.item_set_info_label)

        # Guide gear display
        self.guide_gear_browser = QTextBrowser()
        self.guide_gear_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.guide_gear_browser, stretch=1)

        # Help text
        help_label = QLabel(
            "<i>Select a reference build to see recommended gear. "
            "Import builds from View > PoB Characters.</i>"
        )
        help_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self.tab_widget.addTab(tab, "Guide Gear")

    def _create_ideal_rare_tab(self) -> None:
        """Create the Ideal Rare tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Controls row
        controls_row = QHBoxLayout()

        controls_row.addWidget(QLabel("Equipment Slot:"))
        self.ideal_slot_combo = QComboBox()
        # Block signals while populating to avoid premature _update_ideal_rare calls
        self.ideal_slot_combo.blockSignals(True)
        for slot in EQUIPMENT_SLOTS.keys():
            self.ideal_slot_combo.addItem(slot)
        self.ideal_slot_combo.blockSignals(False)
        self.ideal_slot_combo.currentTextChanged.connect(self._update_ideal_rare)
        controls_row.addWidget(self.ideal_slot_combo)

        controls_row.addSpacing(20)

        controls_row.addWidget(QLabel("Target iLvl:"))
        self.ilvl_spin = QSpinBox()
        self.ilvl_spin.setRange(1, 100)
        self.ilvl_spin.setValue(84)
        self.ilvl_spin.valueChanged.connect(self._update_ideal_rare)
        controls_row.addWidget(self.ilvl_spin)

        controls_row.addStretch()
        layout.addLayout(controls_row)

        # Ideal rare display
        self.ideal_rare_browser = QTextBrowser()
        self.ideal_rare_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.ideal_rare_browser, stretch=1)

        # iLvl reference
        ilvl_info = QLabel(
            "<b>iLvl Requirements:</b> T1 life needs 86+, T1 resist needs 84+, "
            "30% MS needs 75+, 35% MS needs 86+"
        )
        ilvl_info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        ilvl_info.setWordWrap(True)
        layout.addWidget(ilvl_info)

        self.tab_widget.addTab(tab, "Ideal Rare")

    def _load_profiles(self) -> None:
        """Load saved profiles into combo boxes."""
        logger.info("_load_profiles started")

        # Block signals during population to prevent cascading calls
        self.profile_combo.blockSignals(True)
        self.ref_profile_combo.blockSignals(True)

        try:
            if not self.character_manager:
                self.profile_combo.addItem("No profiles available")
                self.profile_combo.setEnabled(False)
                self.ref_profile_combo.addItem("No profiles available")
                self.ref_profile_combo.setEnabled(False)
                self._show_no_profile_message()
                return

            profiles = self.character_manager.list_profiles()
            if not profiles:
                self.profile_combo.addItem("No profiles saved")
                self.profile_combo.setEnabled(False)
                self.ref_profile_combo.addItem("No profiles saved")
                self.ref_profile_combo.setEnabled(False)
                self._show_no_profile_message()
                return

            for profile_name in profiles:
                self.profile_combo.addItem(profile_name)
                self.ref_profile_combo.addItem(profile_name)

            # Select active profile
            active_profile = self.character_manager.get_active_profile()
            active = active_profile.name if active_profile else None
            if active:
                idx = self.profile_combo.findText(active)
                if idx >= 0:
                    self.profile_combo.setCurrentIndex(idx)
        finally:
            # Re-enable signals
            self.profile_combo.blockSignals(False)
            self.ref_profile_combo.blockSignals(False)

        # Now manually trigger the profile change handler for the selected profile
        logger.info("_load_profiles triggering initial profile change")
        current_profile = self.profile_combo.currentText()
        if current_profile and current_profile not in ("No profiles available", "No profiles saved"):
            self._on_profile_changed(current_profile)

    def _show_no_profile_message(self) -> None:
        """Show message when no profile is available."""
        self.analysis_label.setText(
            'Import a PoB build from View > PoB Characters to use BiS search.'
        )
        self.search_btn.setEnabled(False)
        self.browser_btn.setEnabled(False)

    def _on_profile_changed(self, profile_name: str) -> None:
        """Handle profile selection change."""
        logger.info(f"_on_profile_changed: {profile_name}")

        # Guard: ensure all required widgets exist
        if not hasattr(self, 'analysis_label') or not hasattr(self, 'search_btn'):
            logger.warning("_on_profile_changed called before widgets exist")
            return

        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            self._show_no_profile_message()
            return

        if not self.character_manager:
            logger.warning("_on_profile_changed: no character_manager")
            return

        try:
            logger.info(f"Getting profile: {profile_name}")
            profile = self.character_manager.get_profile(profile_name)
            if not profile or not profile.build or not profile.build.stats:
                self.analysis_label.setText(
                    f'<span style="color: {COLORS["corrupted"]};">'
                    f'Profile "{profile_name}" has no build stats.</span>'
                )
                self._calculator = None
                self._current_priorities = None
                self.search_btn.setEnabled(False)
                self.browser_btn.setEnabled(False)
                return

            logger.info("Creating BuildStats from profile")
            build_stats = BuildStats.from_pob_stats(profile.build.stats)
            logger.info("Creating BiSCalculator")
            self._calculator = BiSCalculator(build_stats)
            self._current_priorities = profile.priorities

            logger.info("Showing build analysis")
            self._show_build_analysis()

            logger.info("Updating slot")
            if hasattr(self, 'slot_combo'):
                self._on_slot_changed(self.slot_combo.currentText())

            logger.info("Updating ideal rare")
            self._update_ideal_rare()

            self.search_btn.setEnabled(True)
            self.browser_btn.setEnabled(True)
            logger.info("_on_profile_changed completed")

        except Exception as e:
            logger.exception("Failed to load profile")
            self.analysis_label.setText(
                f'<span style="color: {COLORS["corrupted"]};">Error: {str(e)}</span>'
            )

    def _show_build_analysis(self) -> None:
        """Show build analysis in the label."""
        if not self._calculator:
            return

        stats = self._calculator.stats
        build_type = 'Life' if self._calculator.is_life_build else 'ES' if self._calculator.is_es_build else 'Hybrid'

        # Build compact analysis
        parts = [
            f"<b>{build_type} Build</b> ({int(stats.total_life)} life, {int(stats.total_es)} ES)",
            f"<b>Res:</b> F:{int(stats.fire_res)}% C:{int(stats.cold_res)}% L:{int(stats.lightning_res)}% Ch:{int(stats.chaos_res)}%",
        ]

        # Priorities status
        if self._current_priorities:
            parts.append(
                f"<b>Priorities:</b> {len(self._current_priorities.critical)}C / "
                f"{len(self._current_priorities.important)}I / "
                f"{len(self._current_priorities.nice_to_have)}N"
            )
        else:
            parts.append(f'<span style="color: {COLORS["text_secondary"]};">No priorities set</span>')

        # Issues
        issues = []
        if self._calculator.needs_fire_res:
            issues.append("Fire")
        if self._calculator.needs_cold_res:
            issues.append("Cold")
        if self._calculator.needs_lightning_res:
            issues.append("Lightning")
        if self._calculator.needs_chaos_res:
            issues.append("Chaos")

        if issues:
            parts.append(f'<span style="color: {COLORS["corrupted"]};">Low: {", ".join(issues)}</span>')

        self.analysis_label.setText(" | ".join(parts))

    def _on_slot_changed(self, slot: str) -> None:
        """Handle slot selection change."""
        if not self._calculator or not slot:
            return
        if not hasattr(self, 'requirements_browser'):
            return

        try:
            requirements = self._calculator.calculate_requirements(
                slot, custom_priorities=self._current_priorities
            )
            self._current_requirements = requirements
            self._show_requirements(requirements)
        except Exception as e:
            logger.exception("Failed to calculate requirements")
            self.requirements_browser.setHtml(
                f'<p style="color: {COLORS["corrupted"]};">Error: {str(e)}</p>'
            )

    def _show_requirements(self, requirements: BiSRequirements) -> None:
        """Show requirements in the browser."""
        html = f'<p style="color: {COLORS["accent"]}; font-weight: bold;">Searching for: {requirements.slot}</p>'

        if requirements.required_stats:
            html += f'<p style="color: {COLORS["high_value"]}; margin-top: 8px;"><b>Required:</b></p>'
            for stat in requirements.required_stats:
                html += f'''
                <p style="margin-left: 16px; color: {COLORS["text"]};">
                    • {stat.stat_type.replace("_", " ").title()}: min {stat.min_value}
                    <span style="color: {COLORS["text_secondary"]};">({stat.reason})</span>
                </p>
                '''

        if requirements.desired_stats:
            html += f'<p style="color: {COLORS["currency"]}; margin-top: 8px;"><b>Desired:</b></p>'
            for stat in requirements.desired_stats[:4]:
                html += f'''
                <p style="margin-left: 16px; color: {COLORS["text"]};">
                    • {stat.stat_type.replace("_", " ").title()}: min {stat.min_value}
                    <span style="color: {COLORS["text_secondary"]};">({stat.reason})</span>
                </p>
                '''

        self.requirements_browser.setHtml(html)

    def _on_ref_profile_changed(self, profile_name: str) -> None:
        """Handle reference profile selection change."""
        # Hide item set controls initially
        self.item_set_row.setVisible(False)
        self.item_set_info_label.setVisible(False)
        self._current_item_sets: List[ItemSetInfo] = []

        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            self.guide_gear_browser.setHtml(
                f'<p style="color: {COLORS["text_secondary"]};">Select a reference build.</p>'
            )
            return

        try:
            # Check for item sets (loadouts)
            item_sets = self._gear_extractor.get_item_sets_from_profile(profile_name)

            if len(item_sets) > 1:
                # Multiple item sets found - show selector
                self._current_item_sets = item_sets
                self.item_set_combo.blockSignals(True)
                self.item_set_combo.clear()
                for item_set in item_sets:
                    display = item_set.display_name
                    self.item_set_combo.addItem(display, item_set.id)
                    # Select active item set
                    if item_set.is_active:
                        self.item_set_combo.setCurrentIndex(self.item_set_combo.count() - 1)
                self.item_set_combo.blockSignals(False)

                self.item_set_row.setVisible(True)
                self.item_set_info_label.setText(
                    f"This build has {len(item_sets)} item sets. Select one to view its gear."
                )
                self.item_set_info_label.setVisible(True)

                # Load gear from selected item set
                self._load_gear_from_item_set(profile_name)
            else:
                # Single or no item sets - use default extraction
                summary = self._gear_extractor.extract_from_profile(profile_name)
                if not summary:
                    self.guide_gear_browser.setHtml(
                        f'<p style="color: {COLORS["corrupted"]};">Could not extract gear from profile.</p>'
                    )
                    return

                self._guide_gear = summary
                self._show_guide_gear(summary)

        except Exception as e:
            logger.exception("Failed to extract guide gear")
            self.guide_gear_browser.setHtml(
                f'<p style="color: {COLORS["corrupted"]};">Error: {str(e)}</p>'
            )

    def _on_item_set_changed(self, index: int) -> None:
        """Handle item set selection change."""
        profile_name = self.ref_profile_combo.currentText()
        if profile_name:
            self._load_gear_from_item_set(profile_name)

    def _load_gear_from_item_set(self, profile_name: str) -> None:
        """Load gear from the currently selected item set."""
        item_set_id = self.item_set_combo.currentData()
        if not item_set_id:
            return

        try:
            summary = self._gear_extractor.extract_from_profile_with_item_set(
                profile_name, item_set_id
            )
            if not summary:
                self.guide_gear_browser.setHtml(
                    f'<p style="color: {COLORS["corrupted"]};">Could not extract gear from item set.</p>'
                )
                return

            self._guide_gear = summary
            self._show_guide_gear(summary)

        except Exception as e:
            logger.exception("Failed to extract gear from item set")
            self.guide_gear_browser.setHtml(
                f'<p style="color: {COLORS["corrupted"]};">Error: {str(e)}</p>'
            )

    def _show_guide_gear(self, summary: GuideGearSummary) -> None:
        """Show guide gear in the browser."""
        title = summary.guide_name
        if summary.item_set_name:
            title += f" - {summary.item_set_name}"
        html = f'<h3 style="color: {COLORS["accent"]};">Gear from: {title}</h3>'

        # Uniques
        uniques = summary.get_unique_recommendations()
        if uniques:
            html += f'<h4 style="color: {COLORS["unique"]};">Unique Items ({len(uniques)})</h4>'
            for rec in uniques:
                html += f'''
                <div style="margin: 8px 0; padding: 8px; border-left: 3px solid {COLORS["unique"]}; background-color: {COLORS["surface"]};">
                    <p style="color: {COLORS["unique"]}; font-weight: bold; margin: 0;">[{rec.slot}] {rec.item_name}</p>
                    <p style="color: {COLORS["text_secondary"]}; margin: 2px 0;">{rec.base_type}</p>
                '''
                if rec.key_mods:
                    for mod in rec.key_mods[:3]:
                        html += f'<p style="margin-left: 16px; color: {COLORS["magic"]};">• {mod}</p>'
                html += '</div>'

        # Rares
        rares = summary.get_rare_recommendations()
        if rares:
            html += f'<h4 style="color: {COLORS["rare"]};">Rare Items ({len(rares)})</h4>'
            for rec in rares:
                html += f'''
                <div style="margin: 8px 0; padding: 8px; border-left: 3px solid {COLORS["rare"]}; background-color: {COLORS["surface"]};">
                    <p style="color: {COLORS["rare"]}; font-weight: bold; margin: 0;">[{rec.slot}] {rec.base_type}</p>
                '''
                if rec.key_mods:
                    for mod in rec.key_mods[:4]:
                        html += f'<p style="margin-left: 16px; color: {COLORS["magic"]};">• {mod}</p>'
                html += '</div>'

        if not uniques and not rares:
            html += f'<p style="color: {COLORS["text_secondary"]};">No gear found in this build.</p>'

        self.guide_gear_browser.setHtml(html)

    def _update_ideal_rare(self) -> None:
        """Update the ideal rare display."""
        # Guard: check if widgets exist (may not during initialization)
        if not hasattr(self, 'ideal_rare_browser') or not hasattr(self, 'ideal_slot_combo') or not hasattr(self, 'ilvl_spin'):
            logger.debug("_update_ideal_rare: widgets not ready")
            return

        if not self._current_priorities:
            self.ideal_rare_browser.setHtml(f'''
                <p style="color: {COLORS["text_secondary"]};">
                    Set priorities first using the "Edit Priorities" button.
                </p>
                <p style="color: {COLORS["text_secondary"]};">
                    You can also use "Auto-Suggest" to generate priorities from your build.
                </p>
            ''')
            return

        slot = self.ideal_slot_combo.currentText()
        if not slot:
            return
        ilvl = self.ilvl_spin.value()

        spec = self._tier_calculator.calculate_ideal_rare(
            slot, self._current_priorities, target_ilvl=ilvl
        )

        # Get recommended base item
        base_recommendation = None
        try:
            from core.repoe_tier_provider import get_base_item_recommender
            recommender = get_base_item_recommender()
            is_es = self._current_priorities.is_es_build
            base_recommendation = recommender.get_recommended_base(
                slot,
                is_es_build=is_es,
                is_armour_build=not is_es,
            )
        except Exception as e:
            logger.debug(f"Failed to get base item recommendation: {e}")

        # Header with RePoE indicator
        repoe_badge = ""
        if self._tier_calculator.using_repoe:
            repoe_badge = f' <span style="color: {COLORS["high_value"]}; font-size: 10px;">[RePoE Data]</span>'

        html = f'<h3 style="color: {COLORS["accent"]};">Ideal {slot} (iLvl {ilvl}){repoe_badge}</h3>'

        # Recommended base
        if base_recommendation:
            html += f'''
            <p style="margin-bottom: 12px; padding: 8px; background-color: {COLORS["surface"]}; border-radius: 4px;">
                <b>Recommended Base:</b>
                <span style="color: {COLORS["rare"]};">{base_recommendation.name}</span>
                <span style="color: {COLORS["text_secondary"]};">(drop lvl {base_recommendation.drop_level})</span>
            </p>
            '''

        if not spec.affixes:
            html += f'<p style="color: {COLORS["text_secondary"]};">No affixes match this slot from your priorities.</p>'
        else:
            html += '<table style="width: 100%; border-collapse: collapse;">'
            html += f'''
                <tr style="background-color: {COLORS["surface"]};">
                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid {COLORS["border"]};">Stat</th>
                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid {COLORS["border"]};">Mod Name</th>
                    <th style="text-align: center; padding: 8px; border-bottom: 1px solid {COLORS["border"]};">Tier</th>
                    <th style="text-align: center; padding: 8px; border-bottom: 1px solid {COLORS["border"]};">Range</th>
                    <th style="text-align: center; padding: 8px; border-bottom: 1px solid {COLORS["border"]};">Req iLvl</th>
                </tr>
            '''

            for affix in spec.affixes:
                tier_color = COLORS["high_value"] if affix.tier <= 2 else COLORS["currency"] if affix.tier <= 3 else COLORS["text"]
                available = "✓" if affix.ilvl_required <= ilvl else "✗"
                avail_color = COLORS["high_value"] if affix.ilvl_required <= ilvl else COLORS["corrupted"]
                mod_name = affix.mod_name if affix.mod_name else "-"

                html += f'''
                <tr>
                    <td style="padding: 6px; border-bottom: 1px solid {COLORS["border"]};">
                        <span style="color: {COLORS["text"]};">{affix.stat_name}</span>
                    </td>
                    <td style="padding: 6px; border-bottom: 1px solid {COLORS["border"]};">
                        <span style="color: {COLORS["magic"]}; font-style: italic;">{mod_name}</span>
                    </td>
                    <td style="text-align: center; padding: 6px; border-bottom: 1px solid {COLORS["border"]};">
                        <span style="color: {tier_color}; font-weight: bold;">T{affix.tier}</span>
                    </td>
                    <td style="text-align: center; padding: 6px; border-bottom: 1px solid {COLORS["border"]};">
                        <span style="color: {COLORS["text"]};">{affix.display_range}</span>
                    </td>
                    <td style="text-align: center; padding: 6px; border-bottom: 1px solid {COLORS["border"]};">
                        <span style="color: {avail_color};">{affix.ilvl_required} {available}</span>
                    </td>
                </tr>
                '''

            html += '</table>'

            # Summary
            achievable = sum(1 for a in spec.affixes if a.ilvl_required <= ilvl)
            html += f'''
            <p style="margin-top: 12px; color: {COLORS["text_secondary"]};">
                <b>Summary:</b> {achievable}/{len(spec.affixes)} affixes achievable at iLvl {ilvl}
            </p>
            '''

        self.ideal_rare_browser.setHtml(html)

    def _open_in_browser(self) -> None:
        """Open trade search in browser."""
        if not self._current_requirements:
            return

        try:
            query = build_trade_query(self._current_requirements)

            league = "Standard"
            try:
                from data_sources.pricing.poe_ninja import PoeNinjaAPI
                api = PoeNinjaAPI()
                detected = api.detect_current_league()
                if detected:
                    league = detected
            except Exception as e:
                logger.debug(f"Failed to detect current league: {e}")

            import urllib.parse
            base_url = f"https://www.pathofexile.com/trade/search/{urllib.parse.quote(league)}"

            QMessageBox.information(
                self, "Open Trade Site",
                f"Opening {league} trade site...\n\n"
                "Note: The search query will be copied to clipboard.\n"
                "You can paste it into the trade site's search field."
            )

            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(json.dumps(query, indent=2))

            webbrowser.open(base_url)

        except Exception as e:
            logger.exception("Failed to open browser")
            QMessageBox.critical(self, "Error", f"Failed to open browser: {e}")

    def _search_in_app(self) -> None:
        """Perform search within the app."""
        if not self._current_requirements:
            return

        if self._search_worker and self._search_worker.isRunning():
            return

        try:
            query = build_trade_query(self._current_requirements)

            league = "Standard"
            try:
                from data_sources.pricing.poe_ninja import PoeNinjaAPI
                api = PoeNinjaAPI()
                detected = api.detect_current_league()
                if detected:
                    league = detected
            except Exception as e:
                logger.debug(f"Failed to detect current league for in-app search: {e}")

            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("Searching...")
            self.search_btn.setEnabled(False)

            self._search_worker = TradeSearchWorker(query, league, self)
            self._search_worker.finished.connect(self._on_search_finished)
            self._search_worker.error.connect(self._on_search_error)
            self._search_worker.progress.connect(self._on_search_progress)
            self._search_worker.start()

        except Exception as e:
            logger.exception("Failed to start search")
            self._show_search_error(str(e))

    def _on_search_progress(self, message: str) -> None:
        """Handle search progress update."""
        self.progress_bar.setFormat(message)

    def _on_search_finished(self, results: List[Dict]) -> None:
        """Handle search completion."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)

        if not results:
            self.results_browser.setHtml(
                f'<p style="color: {COLORS["text_secondary"]};">No items found matching the requirements.</p>'
            )
            return

        html = f'<p style="color: {COLORS["high_value"]}; font-weight: bold;">Found {len(results)} items:</p>'

        for i, item in enumerate(results[:15], 1):
            name = item.get("name", "Unknown")
            price = item.get("price", "")
            ilvl = item.get("ilvl", 0)
            mods = item.get("explicit_mods", [])

            html += f'''
            <div style="margin: 8px 0; padding: 8px; border: 1px solid {COLORS["border"]}; border-radius: 4px;">
                <p style="color: {COLORS["rare"]}; font-weight: bold; margin: 0;">{i}. {name}</p>
                <p style="color: {COLORS["currency"]}; margin: 4px 0;">Price: {price}</p>
                <p style="color: {COLORS["text_secondary"]}; margin: 2px 0;">iLvl: {ilvl}</p>
            '''

            if mods:
                html += '<p style="margin: 4px 0 0 0;">'
                for mod in mods[:5]:
                    html += f'<br>• <span style="color: {COLORS["magic"]};">{mod}</span>'
                html += '</p>'

            html += '</div>'

        self.results_browser.setHtml(html)

    def _on_search_error(self, error: str) -> None:
        """Handle search error."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        self._show_search_error(error)

    def _show_search_error(self, error: str) -> None:
        """Show search error message."""
        self.results_browser.setHtml(
            f'<p style="color: {COLORS["corrupted"]};">Search failed: {error}</p>'
        )

    def _open_priorities_editor(self) -> None:
        """Open the priorities editor dialog."""
        profile_name = self.profile_combo.currentText()
        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            QMessageBox.warning(self, "No Profile", "Select a profile first to edit priorities.")
            return

        from gui_qt.dialogs.priorities_editor_dialog import PrioritiesEditorDialog

        dialog = PrioritiesEditorDialog(
            parent=self,
            character_manager=self.character_manager,
            profile_name=profile_name,
            on_save=self._on_priorities_saved,
        )
        dialog.exec()

    def _on_priorities_saved(self, priorities: BuildPriorities) -> None:
        """Handle priorities being saved."""
        self._current_priorities = priorities
        self._on_slot_changed(self.slot_combo.currentText())
        self._show_build_analysis()
        self._update_ideal_rare()
