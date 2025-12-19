"""
BiS Guide Tab for Item Planning Hub.

Tab widget for viewing best-in-slot recommendations and searching trade.
Combines Guide Gear and Trade Search from BiSSearchDialog.
"""
from __future__ import annotations

import logging
import webbrowser
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QGroupBox,
    QTextBrowser,
    QProgressBar,
    QMessageBox,
    QSpinBox,
    QTabWidget,
)

from gui_qt.styles import COLORS

if TYPE_CHECKING:
    from core.pob import CharacterManager
    from core.bis_calculator import BiSCalculator, BiSRequirements
    from core.build_priorities import BuildPriorities

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


class BiSGuideTab(QWidget):
    """
    Tab widget for BiS guide and trade search.

    Receives profile name from parent hub when profile changes.
    """

    def __init__(
        self,
        character_manager: Optional["CharacterManager"] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self._calculator: Optional["BiSCalculator"] = None
        self._current_requirements: Optional["BiSRequirements"] = None
        self._current_priorities: Optional["BuildPriorities"] = None
        self._search_worker: Optional[TradeSearchWorker] = None
        self._current_profile: Optional[str] = None
        self._league = "Standard"

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create tab widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

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

        # === Sub-tabs for Trade Search and Ideal Rare ===
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                background-color: {COLORS["background"]};
            }}
            QTabBar::tab {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS["accent_blue"]};
                color: white;
            }}
        """)

        # Trade Search sub-tab
        self._create_trade_search_subtab()

        # Ideal Rare sub-tab
        self._create_ideal_rare_subtab()

        layout.addWidget(self.sub_tabs, stretch=1)

        # Initial state
        self._show_no_profile_message()

    def _create_trade_search_subtab(self) -> None:
        """Create the Trade Search sub-tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        # Slot Selection
        slot_row = QHBoxLayout()
        slot_row.addWidget(QLabel("Equipment Slot:"))
        self.slot_combo = QComboBox()
        self.slot_combo.currentTextChanged.connect(self._on_slot_changed)
        slot_row.addWidget(self.slot_combo, stretch=1)
        layout.addLayout(slot_row)

        # Requirements Preview
        req_group = QGroupBox("Search Requirements")
        req_layout = QVBoxLayout(req_group)
        self.requirements_browser = QTextBrowser()
        self.requirements_browser.setMaximumHeight(120)
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
                padding: 8px 16px;
            }}
            QPushButton:hover {{ background-color: #4bb5e8; }}
            QPushButton:disabled {{ background-color: {COLORS["surface"]}; }}
        """)
        self.browser_btn.clicked.connect(self._open_in_browser)
        self.browser_btn.setEnabled(False)
        button_row.addWidget(self.browser_btn)

        self.search_btn = QPushButton("Search In-App")
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: black;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{ background-color: {COLORS["accent_hover"]}; }}
            QPushButton:disabled {{ background-color: {COLORS["surface"]}; }}
        """)
        self.search_btn.clicked.connect(self._search_in_app)
        self.search_btn.setEnabled(False)
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

        self.sub_tabs.addTab(tab, "Trade Search")

    def _create_ideal_rare_subtab(self) -> None:
        """Create the Ideal Rare sub-tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        # Controls row
        controls_row = QHBoxLayout()

        controls_row.addWidget(QLabel("Equipment Slot:"))
        self.ideal_slot_combo = QComboBox()
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

        self.sub_tabs.addTab(tab, "Ideal Rare")

    def set_profile(self, profile_name: Optional[str]) -> None:
        """Set the current profile (called by parent hub)."""
        self._current_profile = profile_name

        if not profile_name:
            self._show_no_profile_message()
            return

        self._load_profile(profile_name)

    def set_priorities(self, priorities: Optional["BuildPriorities"]) -> None:
        """Set build priorities (called by parent hub)."""
        self._current_priorities = priorities
        if self._current_profile:
            self._on_slot_changed(self.slot_combo.currentText())

    def _load_profile(self, profile_name: str) -> None:
        """Load profile and initialize calculator."""
        if not self.character_manager:
            self._show_no_profile_message()
            return

        try:
            from core.bis_calculator import BiSCalculator, EQUIPMENT_SLOTS
            from core.build_stat_calculator import BuildStats

            profile = self.character_manager.get_profile(profile_name)
            if not profile or not profile.build or not profile.build.stats:
                self.analysis_label.setText(
                    f'<span style="color: {COLORS["corrupted"]};">'
                    f'Profile "{profile_name}" has no build stats.</span>'
                )
                self._calculator = None
                return

            build_stats = BuildStats.from_pob_stats(profile.build.stats)
            self._calculator = BiSCalculator(build_stats)
            self._current_priorities = profile.priorities

            # Populate slot combos
            self.slot_combo.blockSignals(True)
            self.ideal_slot_combo.blockSignals(True)
            self.slot_combo.clear()
            self.ideal_slot_combo.clear()
            for slot in EQUIPMENT_SLOTS.keys():
                self.slot_combo.addItem(slot)
                self.ideal_slot_combo.addItem(slot)
            self.slot_combo.blockSignals(False)
            self.ideal_slot_combo.blockSignals(False)

            # Detect league
            try:
                from data_sources.pricing.poe_ninja import PoeNinjaAPI
                api = PoeNinjaAPI()
                detected = api.detect_current_league()
                if detected:
                    self._league = detected
            except Exception:
                pass

            self._show_build_analysis()
            self._on_slot_changed(self.slot_combo.currentText())
            self._update_ideal_rare()

            self.search_btn.setEnabled(True)
            self.browser_btn.setEnabled(True)

        except Exception as e:
            logger.exception("Failed to load profile")
            self.analysis_label.setText(
                f'<span style="color: {COLORS["corrupted"]};">Error: {str(e)}</span>'
            )

    def _show_no_profile_message(self) -> None:
        """Show message when no profile is available."""
        self.analysis_label.setText(
            'Select a profile above to see BiS recommendations and search trade.'
        )
        self.search_btn.setEnabled(False)
        self.browser_btn.setEnabled(False)

    def _show_build_analysis(self) -> None:
        """Show build analysis in the label."""
        if not self._calculator:
            return

        stats = self._calculator.stats
        build_type = 'Life' if self._calculator.is_life_build else 'ES' if self._calculator.is_es_build else 'Hybrid'

        parts = [
            f"<b>{build_type} Build</b> ({int(stats.total_life)} life, {int(stats.total_es)} ES)",
            f"<b>Res:</b> F:{int(stats.fire_res)}% C:{int(stats.cold_res)}% L:{int(stats.lightning_res)}%",
        ]

        if self._current_priorities:
            parts.append(
                f"<b>Priorities:</b> {len(self._current_priorities.critical)}C / "
                f"{len(self._current_priorities.important)}I"
            )

        self.analysis_label.setText(" | ".join(parts))

    def _on_slot_changed(self, slot: str) -> None:
        """Handle slot selection change."""
        if not self._calculator or not slot:
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
                f'<span style="color: {COLORS["corrupted"]};">Error: {str(e)}</span>'
            )

    def _show_requirements(self, requirements: "BiSRequirements") -> None:
        """Display requirements in the browser."""
        html = """
        <p><b>Required Stats:</b></p>
        <ul style="margin: 4px 0;">
        """
        for stat_req in requirements.required_stats:
            html += f'<li style="color: {COLORS["high_value"]};">{stat_req.stat_type}: {stat_req.min_value}</li>'

        html += "</ul><p><b>Desired Stats:</b></p><ul style='margin: 4px 0;'>"
        for stat_req in requirements.desired_stats:
            html += f'<li style="color: {COLORS["text_secondary"]};">{stat_req.stat_type}: {stat_req.min_value}</li>'

        html += "</ul>"
        self.requirements_browser.setHtml(html)

    def _open_in_browser(self) -> None:
        """Open trade search in browser."""
        if not self._current_requirements:
            return

        try:
            from core.bis_calculator import build_trade_query
            query = build_trade_query(self._current_requirements)
            import json
            import urllib.parse
            query_str = json.dumps(query)
            encoded = urllib.parse.quote(query_str)
            url = f"https://www.pathofexile.com/trade/search/{self._league}?q={encoded}"
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open browser: {e}")

    def _search_in_app(self) -> None:
        """Perform in-app trade search."""
        if not self._current_requirements:
            return

        if self._search_worker and self._search_worker.isRunning():
            return

        try:
            from core.bis_calculator import build_trade_query
            query = build_trade_query(self._current_requirements)

            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.search_btn.setEnabled(False)

            self._search_worker = TradeSearchWorker(query, self._league, self)
            self._search_worker.finished.connect(self._on_search_finished)
            self._search_worker.error.connect(self._on_search_error)
            self._search_worker.progress.connect(self._on_search_progress)
            self._search_worker.start()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start search: {e}")

    def _on_search_progress(self, message: str) -> None:
        """Handle search progress."""
        self.progress_bar.setFormat(message)

    def _on_search_finished(self, results: List[Dict]) -> None:
        """Handle search completion."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)

        if not results:
            self.results_browser.setHtml(
                f'<p style="color: {COLORS["text_secondary"]};">No items found matching requirements.</p>'
            )
            return

        html = f"<p><b>Found {len(results)} items:</b></p>"
        for item in results[:20]:
            html += f"""
            <div style="margin: 8px 0; padding: 8px; background-color: {COLORS['background']}; border-radius: 4px;">
                <p style="color: {COLORS['rare']}; margin: 0; font-weight: bold;">{item['name']}</p>
                <p style="color: {COLORS['currency']}; margin: 4px 0;">Price: {item['price']}</p>
                <p style="color: {COLORS['text_secondary']}; margin: 0; font-size: 11px;">iLvl: {item['ilvl']}</p>
            </div>
            """

        self.results_browser.setHtml(html)

    def _on_search_error(self, error: str) -> None:
        """Handle search error."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        QMessageBox.critical(self, "Search Error", f"Trade search failed:\n{error}")

    def _update_ideal_rare(self) -> None:
        """Update the ideal rare display."""
        if not self._calculator:
            return

        slot = self.ideal_slot_combo.currentText()
        ilvl = self.ilvl_spin.value()

        if not slot:
            return

        try:
            from core.affix_tier_calculator import AffixTierCalculator

            tier_calc = AffixTierCalculator()

            # Get priorities from current profile
            priorities = None
            if self._current_profile and self.character_manager:
                profile = self.character_manager.get_profile(self._current_profile)
                if profile and hasattr(profile, 'priorities'):
                    priorities = profile.priorities

            if priorities:
                # Use calculate_ideal_rare with priorities
                ideal_spec = tier_calc.calculate_ideal_rare(
                    slot=slot,
                    priorities=priorities,
                    target_ilvl=ilvl,
                )
                html = f"<h3>Ideal Rare {slot} (iLvl {ilvl})</h3>"
                html += "<p><b>Target Affixes:</b></p><ul>"

                for affix in ideal_spec.affixes[:8]:
                    tier_name = getattr(affix, 'tier_name', '')
                    stat_name = getattr(affix, 'stat_name', str(affix))
                    html += f'<li style="color: {COLORS["magic"]};">{stat_name} {tier_name}</li>'

                html += "</ul>"
            else:
                # No priorities - show available stats for slot
                available_stats = tier_calc.get_available_stats_for_slot(slot)
                html = f"<h3>Available Stats for {slot}</h3>"
                html += "<p>Set up build priorities to see ideal affixes.</p>"
                html += "<p><b>Available:</b></p><ul>"
                for stat in available_stats[:10]:
                    html += f'<li style="color: {COLORS["text_secondary"]};">{stat}</li>'
                html += "</ul>"

            self.ideal_rare_browser.setHtml(html)

        except Exception as e:
            logger.debug(f"Failed to calculate ideal rare: {e}")
            self.ideal_rare_browser.setHtml(
                f'<p style="color: {COLORS["text_secondary"]};">Select a slot to see ideal affixes.</p>'
            )
