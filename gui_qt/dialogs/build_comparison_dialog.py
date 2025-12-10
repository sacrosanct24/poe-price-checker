"""
gui_qt.dialogs.build_comparison_dialog

Dialog for comparing passive trees between builds.
Side-by-side layout with detailed notable/keystone differences.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
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
    QSplitter,
)

from gui_qt.styles import COLORS, apply_window_icon
from gui_qt.widgets.build_filter_widget import BuildFilterWidget
from core.tree_comparison import TreeComparisonService, TreeComparisonResult
from core.pob_integration import CharacterManager, PoBDecoder
from core.build_comparison import GuideBuildParser, TreeSpec
from core.passive_tree_data import get_passive_tree_provider, PassiveNode

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
        self._tree_provider = get_passive_tree_provider()

        # Store parsed tree specs for loadout selection
        self._your_tree_specs: List[TreeSpec] = []
        self._target_tree_specs: List[TreeSpec] = []
        self._your_pob_xml: Optional[str] = None
        self._target_pob_xml: Optional[str] = None

        # Store specs for profile-loaded builds
        self._your_profile_tree_specs: List[TreeSpec] = []
        self._target_profile_tree_specs: List[TreeSpec] = []

        # Store profile metadata for filtering
        self._profile_metadata: dict = {}  # name -> {class, ascendancy}

        self.setWindowTitle("Compare Build Trees")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        self.resize(1200, 800)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_profiles()

    def _create_widgets(self) -> None:
        """Create dialog widgets with side-by-side layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(12)

        # Create splitter for left (selector) and right (results) panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT PANEL: Build Selectors ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Filter Section
        filter_group = QGroupBox("Filter Builds")
        filter_layout = QVBoxLayout(filter_group)
        self.build_filter = BuildFilterWidget(
            show_labels=True,
            horizontal=False,
            include_all_option=True,
        )
        self.build_filter.filter_changed.connect(self._on_filter_changed)
        filter_layout.addWidget(self.build_filter)
        left_layout.addWidget(filter_group)

        # Your Build Section
        your_build_group = self._create_your_build_section()
        left_layout.addWidget(your_build_group)

        # Target Build Section
        target_build_group = self._create_target_build_section()
        left_layout.addWidget(target_build_group)

        # Compare Button
        compare_row = QHBoxLayout()
        compare_row.addStretch()
        self.compare_btn = QPushButton("Compare Trees")
        self.compare_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: black;
                font-weight: bold;
                padding: 12px 40px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS["accent_hover"]};
            }}
        """)
        self.compare_btn.clicked.connect(self._on_compare)
        compare_row.addWidget(self.compare_btn)
        compare_row.addStretch()
        left_layout.addLayout(compare_row)

        left_layout.addStretch()

        # Close button at bottom
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        left_layout.addWidget(close_btn)

        splitter.addWidget(left_widget)

        # === RIGHT PANEL: Results ===
        right_widget = self._create_results_panel()
        splitter.addWidget(right_widget)

        # Set splitter proportions (left narrower, right wider)
        splitter.setSizes([400, 800])

        main_layout.addWidget(splitter)

    def _create_your_build_section(self) -> QGroupBox:
        """Create the Your Build selector section."""
        group = QGroupBox("Your Build")
        layout = QVBoxLayout(group)

        # Input method selection
        method_layout = QHBoxLayout()
        self.your_method_group = QButtonGroup(self)
        self.your_pob_radio = QRadioButton("Paste PoB Code")
        self.your_profile_radio = QRadioButton("Select Saved Profile")
        self.your_method_group.addButton(self.your_pob_radio, 0)
        self.your_method_group.addButton(self.your_profile_radio, 1)
        method_layout.addWidget(self.your_pob_radio)
        method_layout.addWidget(self.your_profile_radio)
        method_layout.addStretch()
        layout.addLayout(method_layout)

        # Stacked widget for your build input
        self.your_input_stack = QStackedWidget()

        # PoB code input
        your_pob_widget = QWidget()
        your_pob_layout = QVBoxLayout(your_pob_widget)
        your_pob_layout.setContentsMargins(0, 0, 0, 0)
        self.your_pob_input = QPlainTextEdit()
        self.your_pob_input.setPlaceholderText("Paste your PoB share code here...")
        self.your_pob_input.setMaximumHeight(50)
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

        # Tree spec selector row for profile
        your_profile_spec_row = QHBoxLayout()
        self.your_profile_load_btn = QPushButton("Load")
        self.your_profile_load_btn.setFixedWidth(60)
        self.your_profile_load_btn.clicked.connect(self._on_load_your_profile)
        your_profile_spec_row.addWidget(self.your_profile_load_btn)

        self.your_profile_spec_combo = QComboBox()
        self.your_profile_spec_combo.setPlaceholderText("Tree Spec (click Load first)")
        self.your_profile_spec_combo.setEnabled(False)
        your_profile_spec_row.addWidget(self.your_profile_spec_combo, 1)
        your_profile_layout.addLayout(your_profile_spec_row)

        self.your_input_stack.addWidget(your_profile_widget)

        layout.addWidget(self.your_input_stack)

        # Connect radio buttons
        self.your_pob_radio.toggled.connect(
            lambda checked: self.your_input_stack.setCurrentIndex(0) if checked else None
        )
        self.your_profile_radio.toggled.connect(
            lambda checked: self.your_input_stack.setCurrentIndex(1) if checked else None
        )
        self.your_profile_radio.setChecked(True)

        return group

    def _create_target_build_section(self) -> QGroupBox:
        """Create the Target Build selector section."""
        group = QGroupBox("Target Build (Compare Against)")
        layout = QVBoxLayout(group)

        # Input method selection
        method_layout = QHBoxLayout()
        self.target_method_group = QButtonGroup(self)
        self.target_pob_radio = QRadioButton("Paste PoB Code")
        self.target_profile_radio = QRadioButton("Select Saved Profile")
        self.target_method_group.addButton(self.target_pob_radio, 0)
        self.target_method_group.addButton(self.target_profile_radio, 1)
        method_layout.addWidget(self.target_pob_radio)
        method_layout.addWidget(self.target_profile_radio)
        method_layout.addStretch()
        layout.addLayout(method_layout)

        # Stacked widget for target build input
        self.target_input_stack = QStackedWidget()

        # PoB code input
        target_pob_widget = QWidget()
        target_pob_layout = QVBoxLayout(target_pob_widget)
        target_pob_layout.setContentsMargins(0, 0, 0, 0)
        self.target_pob_input = QPlainTextEdit()
        self.target_pob_input.setPlaceholderText("Paste target PoB share code here...")
        self.target_pob_input.setMaximumHeight(50)
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

        # Tree spec selector row for profile
        target_profile_spec_row = QHBoxLayout()
        self.target_profile_load_btn = QPushButton("Load")
        self.target_profile_load_btn.setFixedWidth(60)
        self.target_profile_load_btn.clicked.connect(self._on_load_target_profile)
        target_profile_spec_row.addWidget(self.target_profile_load_btn)

        self.target_profile_spec_combo = QComboBox()
        self.target_profile_spec_combo.setPlaceholderText("Tree Spec (click Load first)")
        self.target_profile_spec_combo.setEnabled(False)
        target_profile_spec_row.addWidget(self.target_profile_spec_combo, 1)
        target_profile_layout.addLayout(target_profile_spec_row)

        self.target_input_stack.addWidget(target_profile_widget)

        layout.addWidget(self.target_input_stack)

        # Connect radio buttons
        self.target_pob_radio.toggled.connect(
            lambda checked: self.target_input_stack.setCurrentIndex(0) if checked else None
        )
        self.target_profile_radio.toggled.connect(
            lambda checked: self.target_input_stack.setCurrentIndex(1) if checked else None
        )
        self.target_pob_radio.setChecked(True)

        return group

    def _create_results_panel(self) -> QWidget:
        """Create the results panel showing comparison details."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with similarity
        header = QWidget()
        header_layout = QVBoxLayout(header)

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
        header_layout.addWidget(self.similarity_label)

        self.similarity_subtext = QLabel("Tree Similarity")
        self.similarity_subtext.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.similarity_subtext.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header_layout.addWidget(self.similarity_subtext)

        layout.addWidget(header)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(separator)

        # Side-by-side node comparison
        comparison_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Your Build Panel
        your_panel = self._create_build_comparison_panel("Your Build", "extra")
        self.your_notables_list = your_panel.findChild(QTextBrowser, "notables_list")
        self.your_keystones_list = your_panel.findChild(QTextBrowser, "keystones_list")
        self.your_small_count = your_panel.findChild(QLabel, "small_count")
        comparison_splitter.addWidget(your_panel)

        # Target Build Panel
        target_panel = self._create_build_comparison_panel("Target Build", "missing")
        self.target_notables_list = target_panel.findChild(QTextBrowser, "notables_list")
        self.target_keystones_list = target_panel.findChild(QTextBrowser, "keystones_list")
        self.target_small_count = target_panel.findChild(QLabel, "small_count")
        comparison_splitter.addWidget(target_panel)

        layout.addWidget(comparison_splitter, 1)  # Give it stretch

        # Shared nodes summary at bottom
        shared_group = QGroupBox("Shared Nodes")
        shared_layout = QVBoxLayout(shared_group)
        self.shared_summary = QLabel("--")
        self.shared_summary.setStyleSheet(f"color: {COLORS['high_value']}; font-size: 13px;")
        self.shared_summary.setWordWrap(True)
        shared_layout.addWidget(self.shared_summary)
        layout.addWidget(shared_group)

        return widget

    def _create_build_comparison_panel(self, title: str, diff_type: str) -> QWidget:
        """
        Create a panel showing nodes unique to one build.

        Args:
            title: Panel title
            diff_type: "extra" (nodes you have) or "missing" (nodes you need)
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS['text']};
            padding: 5px;
        """)
        layout.addWidget(title_label)

        if diff_type == "extra":
            subtitle = "Nodes you have that target doesn't"
            color = COLORS["currency"]
        else:
            subtitle = "Nodes you're missing from target"
            color = COLORS["corrupted"]

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        layout.addWidget(subtitle_label)

        # Keystones section
        keystones_label = QLabel("Keystones:")
        keystones_label.setStyleSheet(f"font-weight: bold; color: {COLORS['unique']};")
        layout.addWidget(keystones_label)

        keystones_list = QTextBrowser()
        keystones_list.setObjectName("keystones_list")
        keystones_list.setMaximumHeight(80)
        keystones_list.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(keystones_list)

        # Notables section
        notables_label = QLabel("Notables:")
        notables_label.setStyleSheet(f"font-weight: bold; color: {COLORS['accent']};")
        layout.addWidget(notables_label)

        notables_list = QTextBrowser()
        notables_list.setObjectName("notables_list")
        notables_list.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(notables_list, 1)  # Stretch

        # Small nodes count
        small_frame = QFrame()
        small_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        small_layout = QHBoxLayout(small_frame)
        small_label = QLabel("Small Nodes:")
        small_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        small_layout.addWidget(small_label)

        small_count = QLabel("0")
        small_count.setObjectName("small_count")
        small_count.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 16px;")
        small_layout.addWidget(small_count)
        small_layout.addStretch()

        layout.addWidget(small_frame)

        return widget

    def _load_profiles(self) -> None:
        """Load saved profiles into combo boxes with metadata for filtering."""
        self._all_profiles = []  # Store full list for filtering
        self._profile_metadata.clear()

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

        # Collect metadata for each profile
        for profile_name in profiles:
            profile = self.character_manager.get_profile(profile_name)
            if profile and profile.build:
                self._profile_metadata[profile_name] = {
                    "class": profile.build.class_name,
                    "ascendancy": profile.build.ascendancy,
                }
            else:
                self._profile_metadata[profile_name] = {
                    "class": "",
                    "ascendancy": "",
                }
            self._all_profiles.append(profile_name)

        # Populate combos (will be filtered by _on_filter_changed)
        self._update_profile_combos()

        # Select active profile for "your build" if available
        active_profile = self.character_manager.get_active_profile()
        active = active_profile.name if active_profile else None
        if active:
            idx = self.your_profile_combo.findText(active)
            if idx >= 0:
                self.your_profile_combo.setCurrentIndex(idx)

    def _on_filter_changed(self) -> None:
        """Handle filter changes - update profile combo boxes."""
        self._update_profile_combos()

    def _update_profile_combos(self) -> None:
        """Update profile combo boxes based on current filter."""
        if not hasattr(self, '_all_profiles'):
            return

        # Get current filter (reserved for future filtering)
        _filter_data = self.build_filter.get_filter()

        # Remember current selections
        your_current = self.your_profile_combo.currentText()
        target_current = self.target_profile_combo.currentText()

        # Clear and repopulate
        self.your_profile_combo.clear()
        self.target_profile_combo.clear()

        matching_count = 0
        for profile_name in self._all_profiles:
            meta = self._profile_metadata.get(profile_name, {})
            build_class = meta.get("class", "")
            build_asc = meta.get("ascendancy", "")

            # Check if this profile matches the filter
            if self.build_filter.matches_build(build_class, build_asc):
                # Add display text with class/ascendancy info
                if build_asc:
                    display = f"{profile_name} ({build_asc})"
                elif build_class:
                    display = f"{profile_name} ({build_class})"
                else:
                    display = profile_name

                self.your_profile_combo.addItem(display, profile_name)
                self.target_profile_combo.addItem(display, profile_name)
                matching_count += 1

        # Handle no matches
        if matching_count == 0:
            self.your_profile_combo.addItem("No matching profiles")
            self.target_profile_combo.addItem("No matching profiles")
            self.your_profile_combo.setEnabled(False)
            self.target_profile_combo.setEnabled(False)
        else:
            self.your_profile_combo.setEnabled(True)
            self.target_profile_combo.setEnabled(True)

            # Restore previous selections if still valid
            for i in range(self.your_profile_combo.count()):
                if self.your_profile_combo.itemData(i) == your_current or \
                   self.your_profile_combo.itemText(i).startswith(your_current):
                    self.your_profile_combo.setCurrentIndex(i)
                    break

            for i in range(self.target_profile_combo.count()):
                if self.target_profile_combo.itemData(i) == target_current or \
                   self.target_profile_combo.itemText(i).startswith(target_current):
                    self.target_profile_combo.setCurrentIndex(i)
                    break

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
                    your_name = spec.title or "Your Build"
                else:
                    your_name = "Your Build"
            else:
                # Get profile name from itemData (text includes ascendancy info)
                your_name = self.your_profile_combo.currentData()
                if not your_name:
                    your_name = self.your_profile_combo.currentText()
                if not your_name or your_name in ("No profiles available", "No profiles saved", "No matching profiles"):
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
                    target_name = spec.title or "Target Build"
                else:
                    target_name = "Target Build"
            else:
                # Get profile name from itemData (text includes ascendancy info)
                target_name = self.target_profile_combo.currentData()
                if not target_name:
                    target_name = self.target_profile_combo.currentText()
                if not target_name or target_name in ("No profiles available", "No profiles saved", "No matching profiles"):
                    self._show_error("Please select a target profile")
                    return
                target_from_code = False

            # Perform comparison
            if your_from_code and target_from_code:
                your_spec_idx = max(0, self.your_spec_combo.currentIndex())
                target_spec_idx = max(0, self.target_spec_combo.currentIndex())

                result = self._compare_with_specs(
                    your_code, target_code, your_name, target_name,
                    your_spec_idx, target_spec_idx
                )
            elif your_from_code and not target_from_code:
                profile = self.character_manager.get_profile(target_name)
                if not profile or not profile.pob_code:
                    self._show_error(f"Profile '{target_name}' has no PoB code")
                    return

                your_spec_idx = max(0, self.your_spec_combo.currentIndex())
                target_spec_idx = max(0, self.target_profile_spec_combo.currentIndex()) if self._target_profile_tree_specs else 0
                result = self._compare_with_specs(
                    your_code, profile.pob_code, your_name, target_name,
                    your_spec_idx, target_spec_idx
                )
            elif not your_from_code and target_from_code:
                profile = self.character_manager.get_profile(your_name)
                if not profile or not profile.pob_code:
                    self._show_error(f"Profile '{your_name}' has no PoB code")
                    return

                your_spec_idx = max(0, self.your_profile_spec_combo.currentIndex()) if self._your_profile_tree_specs else 0
                target_spec_idx = max(0, self.target_spec_combo.currentIndex())
                result = self._compare_with_specs(
                    profile.pob_code, target_code, your_name, target_name,
                    your_spec_idx, target_spec_idx
                )
            else:
                your_profile = self.character_manager.get_profile(your_name)
                target_profile = self.character_manager.get_profile(target_name)

                if not your_profile or not your_profile.pob_code:
                    self._show_error(f"Profile '{your_name}' has no PoB code")
                    return
                if not target_profile or not target_profile.pob_code:
                    self._show_error(f"Profile '{target_name}' has no PoB code")
                    return

                your_spec_idx = max(0, self.your_profile_spec_combo.currentIndex()) if self._your_profile_tree_specs else 0
                target_spec_idx = max(0, self.target_profile_spec_combo.currentIndex()) if self._target_profile_tree_specs else 0

                result = self._compare_with_specs(
                    your_profile.pob_code, target_profile.pob_code, your_name, target_name,
                    your_spec_idx, target_spec_idx
                )

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
        your_xml = PoBDecoder.decode_pob_code(your_code)
        target_xml = PoBDecoder.decode_pob_code(target_code)

        return self.comparison_service.compare_xml_with_specs(
            your_xml, target_xml, your_name, target_name,
            your_spec_idx, target_spec_idx
        )

    def _display_result(self, result: TreeComparisonResult) -> None:
        """Display comparison result with detailed node breakdown."""
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

        # Categorize nodes using the tree provider
        your_notables, your_keystones, your_small = self._tree_provider.categorize_nodes(
            result.extra_nodes
        )
        target_notables, target_keystones, target_small = self._tree_provider.categorize_nodes(
            result.missing_nodes
        )

        # Update Your Build panel (extra nodes)
        self._update_node_list(self.your_keystones_list, your_keystones, COLORS["unique"])
        self._update_node_list(self.your_notables_list, your_notables, COLORS["currency"])
        self.your_small_count.setText(str(len(your_small)))

        # Update Target Build panel (missing nodes)
        self._update_node_list(self.target_keystones_list, target_keystones, COLORS["unique"])
        self._update_node_list(self.target_notables_list, target_notables, COLORS["corrupted"])
        self.target_small_count.setText(str(len(target_small)))

        # Update shared summary
        shared_notables, shared_keystones, shared_small = self._tree_provider.categorize_nodes(
            result.shared_nodes
        )
        unique_color = COLORS["unique"]
        accent_color = COLORS["accent"]
        secondary_color = COLORS["text_secondary"]
        self.shared_summary.setText(
            f"<b>{result.shared_count}</b> shared nodes: "
            f"<span style='color:{unique_color}'>{len(shared_keystones)} keystones</span>, "
            f"<span style='color:{accent_color}'>{len(shared_notables)} notables</span>, "
            f"<span style='color:{secondary_color}'>{len(shared_small)} small</span>"
        )

    def _update_node_list(
        self,
        browser: QTextBrowser,
        nodes: List[PassiveNode],
        color: str
    ) -> None:
        """Update a text browser with a list of nodes."""
        if not nodes:
            browser.setHtml(f'<span style="color: {COLORS["text_secondary"]};">None</span>')
            return

        # Sort by name
        nodes.sort(key=lambda n: n.name)

        html_parts = []
        for node in nodes:
            # Show node name and first stat if available
            name = node.name
            html_parts.append(f'<div style="color: {color}; margin: 2px 0;">• {name}</div>')

        browser.setHtml("".join(html_parts))

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

        # Clear the node lists
        self.your_keystones_list.setHtml(f'<span style="color: {COLORS["corrupted"]};">{message}</span>')
        self.your_notables_list.setHtml("")
        self.your_small_count.setText("0")
        self.target_keystones_list.setHtml("")
        self.target_notables_list.setHtml("")
        self.target_small_count.setText("0")
        self.shared_summary.setText("--")

    def _on_load_your_build(self) -> None:
        """Load and parse the your build PoB code to extract tree specs."""
        code = self.your_pob_input.toPlainText().strip()
        if not code:
            self._show_error("Please paste a PoB code first")
            return

        try:
            xml_str = PoBDecoder.decode_pob_code(code)
            self._your_pob_xml = xml_str

            parser = GuideBuildParser()
            self._your_tree_specs = parser.parse_tree_specs(xml_str)

            self.your_spec_combo.clear()
            if len(self._your_tree_specs) <= 1:
                self.your_spec_combo.addItem("Default Tree")
                self.your_spec_combo.setEnabled(False)
            else:
                for i, spec in enumerate(self._your_tree_specs):
                    title = spec.title or f"Tree {i+1}"
                    level = spec.inferred_level
                    if level:
                        title = f"{title} (Lvl {level})"
                    self.your_spec_combo.addItem(title)
                self.your_spec_combo.setEnabled(True)

            self.your_spec_combo.setCurrentIndex(len(self._your_tree_specs) - 1)

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
            xml_str = PoBDecoder.decode_pob_code(code)
            self._target_pob_xml = xml_str

            parser = GuideBuildParser()
            self._target_tree_specs = parser.parse_tree_specs(xml_str)

            self.target_spec_combo.clear()
            if len(self._target_tree_specs) <= 1:
                self.target_spec_combo.addItem("Default Tree")
                self.target_spec_combo.setEnabled(False)
            else:
                for i, spec in enumerate(self._target_tree_specs):
                    title = spec.title or f"Tree {i+1}"
                    level = spec.inferred_level
                    if level:
                        title = f"{title} (Lvl {level})"
                    self.target_spec_combo.addItem(title)
                self.target_spec_combo.setEnabled(True)

            self.target_spec_combo.setCurrentIndex(len(self._target_tree_specs) - 1)

        except Exception as e:
            logger.exception("Error loading target build")
            self._show_error(f"Failed to load: {str(e)}")

    def _on_load_your_profile(self) -> None:
        """Load tree specs from selected your profile."""
        profile_name = self.your_profile_combo.currentText()
        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            self._show_error("Please select a profile first")
            return

        if not self.character_manager:
            self._show_error("Character manager not available")
            return

        try:
            profile = self.character_manager.get_profile(profile_name)
            if not profile or not profile.pob_code:
                self._show_error(f"Profile '{profile_name}' has no PoB code")
                return

            xml_str = PoBDecoder.decode_pob_code(profile.pob_code)

            parser = GuideBuildParser()
            self._your_profile_tree_specs = parser.parse_tree_specs(xml_str)

            self.your_profile_spec_combo.clear()
            if len(self._your_profile_tree_specs) <= 1:
                self.your_profile_spec_combo.addItem("Default Tree")
                self.your_profile_spec_combo.setEnabled(False)
            else:
                for i, spec in enumerate(self._your_profile_tree_specs):
                    title = spec.title or f"Tree {i+1}"
                    level = spec.inferred_level
                    if level:
                        title = f"{title} (Lvl {level})"
                    self.your_profile_spec_combo.addItem(title)
                self.your_profile_spec_combo.setEnabled(True)

            self.your_profile_spec_combo.setCurrentIndex(len(self._your_profile_tree_specs) - 1)

        except Exception as e:
            logger.exception("Error loading profile tree specs")
            self._show_error(f"Failed to load: {str(e)}")

    def _on_load_target_profile(self) -> None:
        """Load tree specs from selected target profile."""
        profile_name = self.target_profile_combo.currentText()
        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            self._show_error("Please select a profile first")
            return

        if not self.character_manager:
            self._show_error("Character manager not available")
            return

        try:
            profile = self.character_manager.get_profile(profile_name)
            if not profile or not profile.pob_code:
                self._show_error(f"Profile '{profile_name}' has no PoB code")
                return

            xml_str = PoBDecoder.decode_pob_code(profile.pob_code)

            parser = GuideBuildParser()
            self._target_profile_tree_specs = parser.parse_tree_specs(xml_str)

            self.target_profile_spec_combo.clear()
            if len(self._target_profile_tree_specs) <= 1:
                self.target_profile_spec_combo.addItem("Default Tree")
                self.target_profile_spec_combo.setEnabled(False)
            else:
                for i, spec in enumerate(self._target_profile_tree_specs):
                    title = spec.title or f"Tree {i+1}"
                    level = spec.inferred_level
                    if level:
                        title = f"{title} (Lvl {level})"
                    self.target_profile_spec_combo.addItem(title)
                self.target_profile_spec_combo.setEnabled(True)

            self.target_profile_spec_combo.setCurrentIndex(len(self._target_profile_tree_specs) - 1)

        except Exception as e:
            logger.exception("Error loading profile tree specs")
            self._show_error(f"Failed to load: {str(e)}")
