"""
gui_qt.dialogs.loadout_selector_dialog

Dialog for browsing and selecting PoB loadouts (tree specs, skill sets, item sets).
Supports builds with multiple progression stages like the RF Phox build.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QComboBox,
    QPushButton,
    QWidget,
    QGroupBox,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QSplitter,
    QTextBrowser,
    QMessageBox,
)

from gui_qt.styles import COLORS, apply_window_icon

logger = logging.getLogger(__name__)

# Try to import the build comparison module
try:
    from core.build_comparison import (
        GuideBuildParser,
        MaxrollBuildFetcher,
        TreeSpec,
        SkillSetSpec,
    )
    from core.pob_integration import PoBDecoder
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Build comparison imports not available: {e}")
    IMPORTS_AVAILABLE = False


class LoadoutSelectorDialog(QDialog):
    """
    Dialog for browsing and selecting PoB loadouts.

    Shows all available tree specs, skill sets, and item sets from a PoB build,
    allowing users to select the appropriate loadout for their current level.
    """

    loadout_selected = pyqtSignal(dict)  # Emits selected loadout config

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("PoB Loadout Selector")
        self.setMinimumSize(700, 500)
        self.resize(850, 600)
        apply_window_icon(self)

        # State
        self._raw_xml: Optional[str] = None
        self._tree_specs: List[Any] = []
        self._skill_sets: List[Any] = []
        self._item_sets: List[Dict] = []
        self._parser: Optional[Any] = None
        self._fetcher: Optional[Any] = None

        if IMPORTS_AVAILABLE:
            self._parser = GuideBuildParser()
            self._fetcher = MaxrollBuildFetcher()

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # === Input Section ===
        input_group = QGroupBox("Build Source")
        input_layout = QVBoxLayout(input_group)

        # PoB code input
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("PoB Code/URL:"))
        self.pob_input = QPlainTextEdit()
        self.pob_input.setPlaceholderText(
            "Paste PoB share code, pastebin URL, pobb.in URL, or Maxroll URL...\n"
            "Example: https://maxroll.gg/poe/pob/0nws0aiy"
        )
        self.pob_input.setMaximumHeight(60)
        code_layout.addWidget(self.pob_input, stretch=1)
        input_layout.addLayout(code_layout)

        # Load button and level selector
        load_row = QHBoxLayout()
        self.load_btn = QPushButton("Load Build")
        self.load_btn.clicked.connect(self._on_load_build)
        load_row.addWidget(self.load_btn)

        load_row.addSpacing(20)
        load_row.addWidget(QLabel("Your Level:"))
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 100)
        self.level_spin.setValue(90)
        self.level_spin.valueChanged.connect(self._on_level_changed)
        load_row.addWidget(self.level_spin)

        self.auto_select_btn = QPushButton("Auto-Select for Level")
        self.auto_select_btn.clicked.connect(self._on_auto_select)
        self.auto_select_btn.setEnabled(False)
        load_row.addWidget(self.auto_select_btn)

        load_row.addStretch()
        input_layout.addLayout(load_row)

        layout.addWidget(input_group)

        # === Build Info ===
        self.build_info_label = QLabel("No build loaded")
        self.build_info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.build_info_label)

        # === Loadout Tabs ===
        self.tabs = QTabWidget()

        # Tree Specs Tab
        tree_tab = QWidget()
        tree_layout = QHBoxLayout(tree_tab)
        self.tree_list = QListWidget()
        self.tree_list.currentItemChanged.connect(self._on_tree_selected)
        tree_layout.addWidget(self.tree_list, stretch=1)
        self.tree_details = QTextBrowser()
        self.tree_details.setOpenExternalLinks(True)
        tree_layout.addWidget(self.tree_details, stretch=1)
        self.tabs.addTab(tree_tab, "Passive Trees (0)")

        # Skill Sets Tab
        skill_tab = QWidget()
        skill_layout = QHBoxLayout(skill_tab)
        self.skill_list = QListWidget()
        self.skill_list.currentItemChanged.connect(self._on_skill_selected)
        skill_layout.addWidget(self.skill_list, stretch=1)
        self.skill_details = QTextBrowser()
        skill_layout.addWidget(self.skill_details, stretch=1)
        self.tabs.addTab(skill_tab, "Skill Sets (0)")

        # Item Sets Tab
        item_tab = QWidget()
        item_layout = QHBoxLayout(item_tab)
        self.item_list = QListWidget()
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        item_layout.addWidget(self.item_list, stretch=1)
        self.item_details = QTextBrowser()
        item_layout.addWidget(self.item_details, stretch=1)
        self.tabs.addTab(item_tab, "Item Sets (0)")

        layout.addWidget(self.tabs, stretch=1)

        # === Selection Summary ===
        summary_group = QGroupBox("Selected Loadout")
        summary_layout = QFormLayout(summary_group)
        self.selected_tree_label = QLabel("-")
        self.selected_skill_label = QLabel("-")
        self.selected_item_label = QLabel("-")
        summary_layout.addRow("Tree:", self.selected_tree_label)
        summary_layout.addRow("Skills:", self.selected_skill_label)
        summary_layout.addRow("Items:", self.selected_item_label)
        layout.addWidget(summary_group)

        # === Buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.apply_btn = QPushButton("Apply Selection")
        self.apply_btn.clicked.connect(self._on_apply)
        self.apply_btn.setEnabled(False)
        btn_layout.addWidget(self.apply_btn)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def _on_load_build(self) -> None:
        """Load a build from the input."""
        if not IMPORTS_AVAILABLE:
            QMessageBox.warning(
                self,
                "Not Available",
                "Build comparison module not available.\n"
                "Please check that core/build_comparison.py exists."
            )
            return

        code = self.pob_input.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "No Input", "Please enter a PoB code or URL.")
            return

        try:
            # Handle Maxroll URLs
            if "maxroll.gg" in code:
                build_id = self._fetcher.extract_build_id(code)
                if not build_id:
                    QMessageBox.warning(
                        self, "Invalid URL",
                        "Could not extract build ID from Maxroll URL."
                    )
                    return
                self._raw_xml = self._fetcher.fetch_and_decode(build_id)
            else:
                # Regular PoB code or pastebin/pobb.in URL
                self._raw_xml = PoBDecoder.decode_pob_code(code)

            self._parse_loadouts()
            self._populate_lists()
            self._update_build_info()
            self.auto_select_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)

        except Exception as e:
            logger.exception("Failed to load build")
            QMessageBox.critical(
                self, "Load Error",
                f"Failed to load build:\n{str(e)}"
            )

    def _parse_loadouts(self) -> None:
        """Parse all loadouts from the XML."""
        if not self._raw_xml or not self._parser:
            return

        # Parse tree specs
        self._tree_specs = self._parser.parse_tree_specs(self._raw_xml)

        # Parse skill sets
        self._skill_sets = self._parser.parse_skill_sets(self._raw_xml)

        # Parse item sets from raw XML
        self._item_sets = self._parse_item_sets(self._raw_xml)

    def _parse_item_sets(self, xml_string: str) -> List[Dict]:
        """Parse item sets from PoB XML."""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_string)
            items_elem = root.find("Items")
            if items_elem is None:
                return []

            item_sets = []
            active_set = items_elem.get("activeItemSet", "1")

            for item_set in items_elem.findall("ItemSet"):
                set_id = item_set.get("id", "?")
                raw_title = item_set.get("title", "Unnamed")
                # Clean PoB color codes
                title = self._parser.clean_title(raw_title) if self._parser else raw_title
                slots = len(item_set.findall("Slot"))

                item_sets.append({
                    "id": set_id,
                    "title": title,
                    "raw_title": raw_title,
                    "slot_count": slots,
                    "is_active": set_id == active_set,
                })

            return item_sets

        except Exception as e:
            logger.warning(f"Failed to parse item sets: {e}")
            return []

    def _populate_lists(self) -> None:
        """Populate the list widgets with loadout data."""
        # Update tab titles with counts
        self.tabs.setTabText(0, f"Passive Trees ({len(self._tree_specs)})")
        self.tabs.setTabText(1, f"Skill Sets ({len(self._skill_sets)})")
        self.tabs.setTabText(2, f"Item Sets ({len(self._item_sets)})")

        # Populate tree specs
        self.tree_list.clear()
        for i, spec in enumerate(self._tree_specs):
            level_str = f"Lvl {spec.inferred_level}" if spec.inferred_level else "?"
            item = QListWidgetItem(f"[{level_str}] {spec.title}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.tree_list.addItem(item)

        # Populate skill sets
        self.skill_list.clear()
        for i, ss in enumerate(self._skill_sets):
            level_str = f"Lvl {ss.inferred_level}" if ss.inferred_level else "?"
            item = QListWidgetItem(f"[{level_str}] {ss.title}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.skill_list.addItem(item)

        # Populate item sets
        self.item_list.clear()
        for i, item_set in enumerate(self._item_sets):
            active_marker = " *" if item_set.get("is_active") else ""
            item = QListWidgetItem(f"{item_set['title']}{active_marker}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.item_list.addItem(item)

    def _update_build_info(self) -> None:
        """Update the build info label."""
        info_parts = []
        if self._tree_specs:
            info_parts.append(f"{len(self._tree_specs)} tree specs")
        if self._skill_sets:
            info_parts.append(f"{len(self._skill_sets)} skill sets")
        if self._item_sets:
            info_parts.append(f"{len(self._item_sets)} item sets")

        if info_parts:
            self.build_info_label.setText("Build loaded: " + ", ".join(info_parts))
            self.build_info_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.build_info_label.setText("Build loaded but no loadouts found")
            self.build_info_label.setStyleSheet("color: orange;")

    def _on_tree_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle tree spec selection."""
        if not current:
            return

        idx = current.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self._tree_specs):
            return

        spec = self._tree_specs[idx]
        self.selected_tree_label.setText(spec.title)

        # Build details HTML
        html = f"<h3>{spec.title}</h3>"
        html += f"<p><b>Inferred Level:</b> {spec.inferred_level or 'Unknown'}</p>"
        html += f"<p><b>Nodes:</b> {len(spec.nodes)}</p>"
        html += f"<p><b>Masteries:</b> {len(spec.mastery_effects)}</p>"

        if spec.url:
            html += f"<p><a href='{spec.url}'>View on PoE Planner</a></p>"

        self.tree_details.setHtml(html)

    def _on_skill_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle skill set selection."""
        if not current:
            return

        idx = current.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self._skill_sets):
            return

        ss = self._skill_sets[idx]
        self.selected_skill_label.setText(ss.title)

        # Build details HTML
        html = f"<h3>{ss.title}</h3>"
        html += f"<p><b>Inferred Level:</b> {ss.inferred_level or 'Unknown'}</p>"
        html += f"<p><b>Skill Groups:</b> {len(ss.skills)}</p>"

        # List skills
        html += "<h4>Skills:</h4><ul>"
        for skill in ss.skills[:10]:  # Limit to first 10
            label = skill.get("label", "")
            gems = skill.get("gems", [])
            gem_names = [g.get("name", "?") for g in gems[:5]]
            if label:
                html += f"<li><b>{label}:</b> {', '.join(gem_names)}</li>"
            else:
                html += f"<li>{', '.join(gem_names)}</li>"

        if len(ss.skills) > 10:
            html += f"<li><i>...and {len(ss.skills) - 10} more</i></li>"
        html += "</ul>"

        self.skill_details.setHtml(html)

    def _on_item_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle item set selection."""
        if not current:
            return

        idx = current.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self._item_sets):
            return

        item_set = self._item_sets[idx]
        self.selected_item_label.setText(item_set["title"])

        # Build details HTML
        html = f"<h3>{item_set['title']}</h3>"
        html += f"<p><b>ID:</b> {item_set['id']}</p>"
        html += f"<p><b>Slots Defined:</b> {item_set['slot_count']}</p>"

        if item_set.get("is_active"):
            html += "<p><b style='color: green;'>Currently Active</b></p>"

        self.item_details.setHtml(html)

    def _on_level_changed(self, level: int) -> None:
        """Handle level change."""
        pass  # Could auto-select here if desired

    def _on_auto_select(self) -> None:
        """Auto-select loadouts for the current level."""
        if not self._parser:
            return

        level = self.level_spin.value()

        # Find best tree spec
        if self._tree_specs:
            best_tree = self._parser.find_spec_for_level(self._tree_specs, level)
            if best_tree:
                idx = self._tree_specs.index(best_tree)
                self.tree_list.setCurrentRow(idx)

        # Find best skill set
        if self._skill_sets:
            best_skill = self._parser.find_skill_set_for_level(self._skill_sets, level)
            if best_skill:
                idx = self._skill_sets.index(best_skill)
                self.skill_list.setCurrentRow(idx)

        # For item sets, select the active one or first
        if self._item_sets:
            for i, item_set in enumerate(self._item_sets):
                if item_set.get("is_active"):
                    self.item_list.setCurrentRow(i)
                    break
            else:
                self.item_list.setCurrentRow(0)

    def _on_apply(self) -> None:
        """Apply the selected loadout."""
        result = {
            "tree_spec": None,
            "skill_set": None,
            "item_set": None,
            "level": self.level_spin.value(),
        }

        # Get selected tree
        tree_item = self.tree_list.currentItem()
        if tree_item:
            idx = tree_item.data(Qt.ItemDataRole.UserRole)
            if idx is not None and idx < len(self._tree_specs):
                result["tree_spec"] = self._tree_specs[idx]

        # Get selected skill set
        skill_item = self.skill_list.currentItem()
        if skill_item:
            idx = skill_item.data(Qt.ItemDataRole.UserRole)
            if idx is not None and idx < len(self._skill_sets):
                result["skill_set"] = self._skill_sets[idx]

        # Get selected item set
        item_item = self.item_list.currentItem()
        if item_item:
            idx = item_item.data(Qt.ItemDataRole.UserRole)
            if idx is not None and idx < len(self._item_sets):
                result["item_set"] = self._item_sets[idx]

        self.loadout_selected.emit(result)
        self.accept()

    def get_selected_loadout(self) -> Dict:
        """Get the currently selected loadout configuration."""
        result = {
            "tree_spec_title": self.selected_tree_label.text(),
            "skill_set_title": self.selected_skill_label.text(),
            "item_set_title": self.selected_item_label.text(),
            "level": self.level_spin.value(),
        }
        return result
