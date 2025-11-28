"""
gui_qt.dialogs.build_comparison_dialog

Dialog for comparing passive trees between builds.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from PyQt6.QtCore import Qt
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
    QRadioButton,
    QButtonGroup,
    QTextBrowser,
    QFrame,
    QStackedWidget,
)

from gui_qt.styles import COLORS, apply_window_icon
from core.tree_comparison import TreeComparisonService, TreeComparisonResult
from core.pob_integration import CharacterManager, PoBDecoder
from core.build_comparison import GuideBuildParser

logger = logging.getLogger(__name__)


class BuildComparisonDialog(QDialog):
    """Dialog for comparing passive trees between builds."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        character_manager: Optional[CharacterManager] = None,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self.comparison_service = TreeComparisonService(character_manager)
        self._last_result: Optional[TreeComparisonResult] = None

        # Store parsed tree specs for loadout selection
        self._your_tree_specs: List[dict] = []
        self._target_tree_specs: List[dict] = []
        self._your_pob_xml: Optional[str] = None
        self._target_pob_xml: Optional[str] = None

        self.setWindowTitle("Compare Build Trees")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.resize(650, 550)  # Good default size
        self.setSizeGripEnabled(True)  # Show resize grip
        apply_window_icon(self)

        self._create_widgets()
        self._load_profiles()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === Your Build Section ===
        your_build_group = QGroupBox("Your Build")
        your_build_layout = QVBoxLayout(your_build_group)

        # Input method selection
        your_method_layout = QHBoxLayout()
        self.your_method_group = QButtonGroup(self)
        self.your_pob_radio = QRadioButton("Paste PoB Code")
        self.your_profile_radio = QRadioButton("Select Saved Profile")
        self.your_method_group.addButton(self.your_pob_radio, 0)
        self.your_method_group.addButton(self.your_profile_radio, 1)
        your_method_layout.addWidget(self.your_pob_radio)
        your_method_layout.addWidget(self.your_profile_radio)
        your_method_layout.addStretch()
        your_build_layout.addLayout(your_method_layout)

        # Stacked widget for your build input
        self.your_input_stack = QStackedWidget()

        # PoB code input
        your_pob_widget = QWidget()
        your_pob_layout = QVBoxLayout(your_pob_widget)
        your_pob_layout.setContentsMargins(0, 0, 0, 0)
        self.your_pob_input = QPlainTextEdit()
        self.your_pob_input.setPlaceholderText("Paste your PoB share code here...")
        self.your_pob_input.setMaximumHeight(60)
        your_pob_layout.addWidget(self.your_pob_input)

        # Tree spec selector row
        your_spec_row = QHBoxLayout()
        self.your_load_btn = QPushButton("Load")
        self.your_load_btn.setFixedWidth(60)
        self.your_load_btn.clicked.connect(self._on_load_your_build)
        your_spec_row.addWidget(self.your_load_btn)

        self.your_spec_combo = QComboBox()
        self.your_spec_combo.setPlaceholderText("Tree Spec (click Load first)")
        self.your_spec_combo.setEnabled(False)
        your_spec_row.addWidget(self.your_spec_combo, 1)
        your_pob_layout.addLayout(your_spec_row)

        self.your_input_stack.addWidget(your_pob_widget)

        # Profile selector
        your_profile_widget = QWidget()
        your_profile_layout = QVBoxLayout(your_profile_widget)
        your_profile_layout.setContentsMargins(0, 0, 0, 0)
        self.your_profile_combo = QComboBox()
        your_profile_layout.addWidget(self.your_profile_combo)
        your_profile_layout.addStretch()
        self.your_input_stack.addWidget(your_profile_widget)

        your_build_layout.addWidget(self.your_input_stack)
        layout.addWidget(your_build_group)

        # Connect radio buttons
        self.your_pob_radio.toggled.connect(lambda checked: self.your_input_stack.setCurrentIndex(0) if checked else None)
        self.your_profile_radio.toggled.connect(lambda checked: self.your_input_stack.setCurrentIndex(1) if checked else None)
        self.your_profile_radio.setChecked(True)

        # === Target Build Section ===
        target_build_group = QGroupBox("Target Build (Compare Against)")
        target_build_layout = QVBoxLayout(target_build_group)

        # Input method selection
        target_method_layout = QHBoxLayout()
        self.target_method_group = QButtonGroup(self)
        self.target_pob_radio = QRadioButton("Paste PoB Code")
        self.target_profile_radio = QRadioButton("Select Saved Profile")
        self.target_method_group.addButton(self.target_pob_radio, 0)
        self.target_method_group.addButton(self.target_profile_radio, 1)
        target_method_layout.addWidget(self.target_pob_radio)
        target_method_layout.addWidget(self.target_profile_radio)
        target_method_layout.addStretch()
        target_build_layout.addLayout(target_method_layout)

        # Stacked widget for target build input
        self.target_input_stack = QStackedWidget()

        # PoB code input
        target_pob_widget = QWidget()
        target_pob_layout = QVBoxLayout(target_pob_widget)
        target_pob_layout.setContentsMargins(0, 0, 0, 0)
        self.target_pob_input = QPlainTextEdit()
        self.target_pob_input.setPlaceholderText("Paste target PoB share code here...")
        self.target_pob_input.setMaximumHeight(60)
        target_pob_layout.addWidget(self.target_pob_input)

        # Tree spec selector row
        target_spec_row = QHBoxLayout()
        self.target_load_btn = QPushButton("Load")
        self.target_load_btn.setFixedWidth(60)
        self.target_load_btn.clicked.connect(self._on_load_target_build)
        target_spec_row.addWidget(self.target_load_btn)

        self.target_spec_combo = QComboBox()
        self.target_spec_combo.setPlaceholderText("Tree Spec (click Load first)")
        self.target_spec_combo.setEnabled(False)
        target_spec_row.addWidget(self.target_spec_combo, 1)
        target_pob_layout.addLayout(target_spec_row)

        self.target_input_stack.addWidget(target_pob_widget)

        # Profile selector
        target_profile_widget = QWidget()
        target_profile_layout = QVBoxLayout(target_profile_widget)
        target_profile_layout.setContentsMargins(0, 0, 0, 0)
        self.target_profile_combo = QComboBox()
        target_profile_layout.addWidget(self.target_profile_combo)
        target_profile_layout.addStretch()
        self.target_input_stack.addWidget(target_profile_widget)

        target_build_layout.addWidget(self.target_input_stack)
        layout.addWidget(target_build_group)

        # Connect radio buttons
        self.target_pob_radio.toggled.connect(lambda checked: self.target_input_stack.setCurrentIndex(0) if checked else None)
        self.target_profile_radio.toggled.connect(lambda checked: self.target_input_stack.setCurrentIndex(1) if checked else None)
        self.target_pob_radio.setChecked(True)

        # === Compare Button ===
        compare_row = QHBoxLayout()
        compare_row.addStretch()
        self.compare_btn = QPushButton("Compare Trees")
        self.compare_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: black;
                font-weight: bold;
                padding: 10px 30px;
            }}
            QPushButton:hover {{
                background-color: {COLORS["accent_hover"]};
            }}
        """)
        self.compare_btn.clicked.connect(self._on_compare)
        compare_row.addWidget(self.compare_btn)
        compare_row.addStretch()
        layout.addLayout(compare_row)

        # === Results Section ===
        results_group = QGroupBox("Comparison Results")
        results_layout = QVBoxLayout(results_group)

        # Similarity display (large and prominent)
        self.similarity_label = QLabel("--")
        self.similarity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.similarity_label.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                font-weight: bold;
                color: {COLORS["accent_blue"]};
                padding: 10px;
            }}
        """)
        results_layout.addWidget(self.similarity_label)

        self.similarity_subtext = QLabel("Tree Similarity")
        self.similarity_subtext.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.similarity_subtext.setStyleSheet(f"color: {COLORS['text_secondary']};")
        results_layout.addWidget(self.similarity_subtext)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        results_layout.addWidget(separator)

        # Stats grid
        stats_layout = QHBoxLayout()

        # Shared nodes
        shared_frame = self._create_stat_frame("Shared", "0", COLORS["high_value"])
        stats_layout.addWidget(shared_frame)

        # Missing nodes
        missing_frame = self._create_stat_frame("Missing", "0", COLORS["corrupted"])
        stats_layout.addWidget(missing_frame)

        # Extra nodes
        extra_frame = self._create_stat_frame("Extra", "0", COLORS["currency"])
        stats_layout.addWidget(extra_frame)

        results_layout.addLayout(stats_layout)

        # Store references to update later
        self.shared_value_label = shared_frame.findChild(QLabel, "value_label")
        self.missing_value_label = missing_frame.findChild(QLabel, "value_label")
        self.extra_value_label = extra_frame.findChild(QLabel, "value_label")

        # Detailed results browser
        self.results_browser = QTextBrowser()
        self.results_browser.setMaximumHeight(120)
        self.results_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
        """)
        results_layout.addWidget(self.results_browser)

        layout.addWidget(results_group)

        # === Close Button ===
        button_row = QHBoxLayout()
        button_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

    def _create_stat_frame(self, label: str, value: str, color: str) -> QFrame:
        """Create a framed stat display."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {color};
        """)
        layout.addWidget(value_label)

        text_label = QLabel(label)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(text_label)

        return frame

    def _load_profiles(self) -> None:
        """Load saved profiles into combo boxes."""
        if not self.character_manager:
            self.your_profile_combo.addItem("No profiles available")
            self.target_profile_combo.addItem("No profiles available")
            self.your_profile_combo.setEnabled(False)
            self.target_profile_combo.setEnabled(False)
            return

        profiles = self.character_manager.list_profiles()
        if not profiles:
            self.your_profile_combo.addItem("No profiles saved")
            self.target_profile_combo.addItem("No profiles saved")
            self.your_profile_combo.setEnabled(False)
            self.target_profile_combo.setEnabled(False)
            return

        for profile_name in profiles:
            self.your_profile_combo.addItem(profile_name)
            self.target_profile_combo.addItem(profile_name)

        # Select active profile for "your build" if available
        active_profile = self.character_manager.get_active_profile()
        active = active_profile.name if active_profile else None
        if active:
            idx = self.your_profile_combo.findText(active)
            if idx >= 0:
                self.your_profile_combo.setCurrentIndex(idx)

    def _on_compare(self) -> None:
        """Handle compare button click."""
        try:
            # Get your build input
            if self.your_pob_radio.isChecked():
                your_code = self.your_pob_input.toPlainText().strip()
                if not your_code:
                    self._show_error("Please paste your PoB code")
                    return
                your_from_code = True

                # Get selected tree spec name
                your_spec_idx = self.your_spec_combo.currentIndex()
                if your_spec_idx >= 0 and your_spec_idx < len(self._your_tree_specs):
                    spec = self._your_tree_specs[your_spec_idx]
                    your_name = spec.get("title", "Your Build")
                else:
                    your_name = "Your Build"
            else:
                your_name = self.your_profile_combo.currentText()
                if not your_name or your_name in ("No profiles available", "No profiles saved"):
                    self._show_error("Please select a profile")
                    return
                your_from_code = False

            # Get target build input
            if self.target_pob_radio.isChecked():
                target_code = self.target_pob_input.toPlainText().strip()
                if not target_code:
                    self._show_error("Please paste target PoB code")
                    return
                target_from_code = True

                # Get selected tree spec name
                target_spec_idx = self.target_spec_combo.currentIndex()
                if target_spec_idx >= 0 and target_spec_idx < len(self._target_tree_specs):
                    spec = self._target_tree_specs[target_spec_idx]
                    target_name = spec.get("title", "Target Build")
                else:
                    target_name = "Target Build"
            else:
                target_name = self.target_profile_combo.currentText()
                if not target_name or target_name in ("No profiles available", "No profiles saved"):
                    self._show_error("Please select a target profile")
                    return
                target_from_code = False

            # Perform comparison
            if your_from_code and target_from_code:
                # Use selected tree specs if available
                your_spec_idx = max(0, self.your_spec_combo.currentIndex())
                target_spec_idx = max(0, self.target_spec_combo.currentIndex())

                result = self._compare_with_specs(
                    your_code, target_code, your_name, target_name,
                    your_spec_idx, target_spec_idx
                )
            elif your_from_code and not target_from_code:
                # Compare pasted code to saved profile - need to get profile's code
                profile = self.character_manager.get_profile(target_name)
                if not profile or not profile.pob_code:
                    self._show_error(f"Profile '{target_name}' has no PoB code")
                    return

                your_spec_idx = max(0, self.your_spec_combo.currentIndex())
                result = self._compare_with_specs(
                    your_code, profile.pob_code, your_name, target_name,
                    your_spec_idx, 0  # Use default spec for saved profile
                )
            elif not your_from_code and target_from_code:
                profile = self.character_manager.get_profile(your_name)
                if not profile or not profile.pob_code:
                    self._show_error(f"Profile '{your_name}' has no PoB code")
                    return

                target_spec_idx = max(0, self.target_spec_combo.currentIndex())
                result = self._compare_with_specs(
                    profile.pob_code, target_code, your_name, target_name,
                    0, target_spec_idx  # Use default spec for saved profile
                )
            else:
                result = self.comparison_service.compare_profiles(your_name, target_name)

            self._last_result = result
            self._display_result(result)

        except Exception as e:
            logger.exception("Error comparing builds")
            self._show_error(f"Error: {str(e)}")

    def _compare_with_specs(
        self,
        your_code: str,
        target_code: str,
        your_name: str,
        target_name: str,
        your_spec_idx: int,
        target_spec_idx: int,
    ) -> TreeComparisonResult:
        """Compare builds using specific tree spec indices."""
        # Decode both builds
        decoder = PoBDecoder()

        your_xml = decoder.decode(your_code)
        target_xml = decoder.decode(target_code)

        # Use the comparison service's spec-aware comparison
        return self.comparison_service.compare_xml_with_specs(
            your_xml, target_xml, your_name, target_name,
            your_spec_idx, target_spec_idx
        )

    def _display_result(self, result: TreeComparisonResult) -> None:
        """Display comparison result."""
        # Update similarity
        self.similarity_label.setText(f"{result.similarity_percent}%")

        # Color code similarity
        if result.similarity_percent >= 80:
            color = COLORS["high_value"]
        elif result.similarity_percent >= 50:
            color = COLORS["currency"]
        else:
            color = COLORS["corrupted"]
        self.similarity_label.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                font-weight: bold;
                color: {color};
                padding: 10px;
            }}
        """)

        # Update stats
        self.shared_value_label.setText(str(result.shared_count))
        self.missing_value_label.setText(str(result.missing_count))
        self.extra_value_label.setText(str(result.extra_count))

        # Update detailed results
        html = f"""
        <p style="color: {COLORS['text']};">
            <b>{result.your_build_name}</b>: {result.your_node_count} nodes<br>
            <b>{result.target_build_name}</b>: {result.target_node_count} nodes
        </p>
        """

        if result.missing_masteries:
            html += f"""
            <p style="color: {COLORS['text_secondary']};">
                Missing {len(result.missing_masteries)} mastery effect(s) from target
            </p>
            """

        if result.missing_count > 0:
            html += f"""
            <p style="color: {COLORS['corrupted']};">
                You need {result.missing_count} more nodes to match target tree
            </p>
            """

        if result.extra_count > 0:
            html += f"""
            <p style="color: {COLORS['currency']};">
                You have {result.extra_count} nodes not in target tree
            </p>
            """

        self.results_browser.setHtml(html)

    def _show_error(self, message: str) -> None:
        """Show error in results area."""
        self.similarity_label.setText("--")
        self.similarity_label.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                font-weight: bold;
                color: {COLORS["text_secondary"]};
                padding: 10px;
            }}
        """)
        self.results_browser.setHtml(
            f'<p style="color: {COLORS["corrupted"]};">{message}</p>'
        )

    def _on_load_your_build(self) -> None:
        """Load and parse the your build PoB code to extract tree specs."""
        code = self.your_pob_input.toPlainText().strip()
        if not code:
            self._show_error("Please paste a PoB code first")
            return

        try:
            # Decode PoB code
            decoder = PoBDecoder()
            xml_str = decoder.decode(code)
            self._your_pob_xml = xml_str

            # Parse tree specs
            parser = GuideBuildParser(xml_str)
            self._your_tree_specs = parser.parse_tree_specs()

            # Populate combo box
            self.your_spec_combo.clear()
            if len(self._your_tree_specs) <= 1:
                self.your_spec_combo.addItem("Default Tree")
                self.your_spec_combo.setEnabled(False)
            else:
                for i, spec in enumerate(self._your_tree_specs):
                    title = spec.get("title", f"Tree {i+1}")
                    level = spec.get("level")
                    if level:
                        title = f"{title} (Lvl {level})"
                    self.your_spec_combo.addItem(title)
                self.your_spec_combo.setEnabled(True)

            self.your_spec_combo.setCurrentIndex(len(self._your_tree_specs) - 1)
            self.results_browser.setHtml(
                f'<p style="color: {COLORS["high_value"]};">Loaded {len(self._your_tree_specs)} tree spec(s)</p>'
            )

        except Exception as e:
            logger.exception("Error loading your build")
            self._show_error(f"Failed to load: {str(e)}")

    def _on_load_target_build(self) -> None:
        """Load and parse the target build PoB code to extract tree specs."""
        code = self.target_pob_input.toPlainText().strip()
        if not code:
            self._show_error("Please paste a PoB code first")
            return

        try:
            # Decode PoB code
            decoder = PoBDecoder()
            xml_str = decoder.decode(code)
            self._target_pob_xml = xml_str

            # Parse tree specs
            parser = GuideBuildParser(xml_str)
            self._target_tree_specs = parser.parse_tree_specs()

            # Populate combo box
            self.target_spec_combo.clear()
            if len(self._target_tree_specs) <= 1:
                self.target_spec_combo.addItem("Default Tree")
                self.target_spec_combo.setEnabled(False)
            else:
                for i, spec in enumerate(self._target_tree_specs):
                    title = spec.get("title", f"Tree {i+1}")
                    level = spec.get("level")
                    if level:
                        title = f"{title} (Lvl {level})"
                    self.target_spec_combo.addItem(title)
                self.target_spec_combo.setEnabled(True)

            self.target_spec_combo.setCurrentIndex(len(self._target_tree_specs) - 1)
            self.results_browser.setHtml(
                f'<p style="color: {COLORS["high_value"]};">Loaded {len(self._target_tree_specs)} tree spec(s)</p>'
            )

        except Exception as e:
            logger.exception("Error loading target build")
            self._show_error(f"Failed to load: {str(e)}")

    def _get_tree_url_for_spec(self, xml_str: str, spec_index: int) -> Optional[str]:
        """Extract tree URL for a specific tree spec index."""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_str)
            tree_elem = root.find(".//Tree")
            if tree_elem is None:
                return None

            specs = tree_elem.findall("Spec")
            if spec_index < len(specs):
                url = specs[spec_index].find("URL")
                if url is not None and url.text:
                    return url.text.strip()
            return None
        except Exception:
            return None
