"""
Item Planning Hub Dialog.

Unified dialog for item planning that combines:
- Upgrade Finder: Find gear upgrades within budget
- BiS Guide: Best-in-slot recommendations and trade search
- Ideal Rare: See ideal affix tiers for each slot

This replaces the separate BiSSearchDialog and UpgradeFinderDialog
with a unified experience sharing profile/priority state.
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QWidget,
    QGroupBox,
    QTabWidget,
)

from gui_qt.styles import COLORS, apply_window_icon
from gui_qt.dialogs.tabs.upgrade_finder_tab import UpgradeFinderTab
from gui_qt.dialogs.tabs.bis_guide_tab import BiSGuideTab

if TYPE_CHECKING:
    from core.pob import CharacterManager

logger = logging.getLogger(__name__)


class ItemPlanningHub(QDialog):
    """
    Unified dialog for item planning.

    Combines Upgrade Finder and BiS Guide into a single tabbed interface
    with shared profile selection and build priorities.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        character_manager: Optional["CharacterManager"] = None,
    ):
        super().__init__(parent)
        logger.info("ItemPlanningHub.__init__ started")

        self.character_manager = character_manager
        self._current_profile: Optional[str] = None

        self.setWindowTitle("Item Planning Hub")
        self.setMinimumWidth(950)
        self.setMinimumHeight(700)
        self.resize(1050, 850)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_profiles()

        logger.info("ItemPlanningHub.__init__ completed")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === Profile Selection (shared across all tabs) ===
        profile_group = QGroupBox("Build Profile")
        profile_layout = QHBoxLayout(profile_group)

        profile_layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
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
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS["accent"]};
                color: black;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS["surface_hover"]};
            }}
        """)

        # Upgrade Finder Tab
        self.upgrade_finder_tab = UpgradeFinderTab(
            character_manager=self.character_manager,
            parent=self,
        )
        self.tab_widget.addTab(self.upgrade_finder_tab, "Upgrade Finder")

        # BiS Guide Tab
        self.bis_guide_tab = BiSGuideTab(
            character_manager=self.character_manager,
            parent=self,
        )
        self.tab_widget.addTab(self.bis_guide_tab, "BiS Guide")

        layout.addWidget(self.tab_widget, stretch=1)

        # === Bottom Buttons ===
        button_row = QHBoxLayout()
        button_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)

        layout.addLayout(button_row)

    def _load_profiles(self) -> None:
        """Load saved profiles into combo box."""
        self.profile_combo.blockSignals(True)

        try:
            if not self.character_manager:
                self.profile_combo.addItem("No profiles available")
                self.profile_combo.setEnabled(False)
                self.edit_priorities_btn.setEnabled(False)
                return

            profiles = self.character_manager.list_profiles()
            if not profiles:
                self.profile_combo.addItem("No profiles saved")
                self.profile_combo.setEnabled(False)
                self.edit_priorities_btn.setEnabled(False)
                return

            for profile_name in profiles:
                self.profile_combo.addItem(profile_name)

            # Select active profile
            active_profile = self.character_manager.get_active_profile()
            if active_profile:
                idx = self.profile_combo.findText(active_profile.name)
                if idx >= 0:
                    self.profile_combo.setCurrentIndex(idx)

        finally:
            self.profile_combo.blockSignals(False)

        # Trigger initial profile load
        current = self.profile_combo.currentText()
        if current and current not in ("No profiles available", "No profiles saved"):
            self._on_profile_changed(current)

    def _on_profile_changed(self, profile_name: str) -> None:
        """Handle profile selection change - broadcast to all tabs."""
        if not profile_name or profile_name in ("No profiles available", "No profiles saved"):
            self._current_profile = None
            self.upgrade_finder_tab.set_profile(None)
            self.bis_guide_tab.set_profile(None)
            self.edit_priorities_btn.setEnabled(False)
            return

        self._current_profile = profile_name
        self.edit_priorities_btn.setEnabled(True)

        # Broadcast to all tabs
        self.upgrade_finder_tab.set_profile(profile_name)
        self.bis_guide_tab.set_profile(profile_name)

    def _open_priorities_editor(self) -> None:
        """Open the build priorities editor dialog."""
        if not self._current_profile or not self.character_manager:
            return

        try:
            from gui_qt.dialogs.build_priorities_dialog import BuildPrioritiesDialog

            profile = self.character_manager.get_profile(self._current_profile)
            if not profile:
                return

            dialog = BuildPrioritiesDialog(
                priorities=profile.priorities,
                parent=self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_priorities = dialog.get_priorities()

                # Save to profile (update_profile sets attribute and saves)
                self.character_manager.update_profile(
                    self._current_profile, priorities=new_priorities
                )

                # Broadcast to tabs
                self.bis_guide_tab.set_priorities(new_priorities)

                logger.info(f"Updated priorities for profile: {self._current_profile}")

        except ImportError:
            logger.warning("BuildPrioritiesDialog not available")
        except Exception as e:
            logger.exception(f"Failed to open priorities editor: {e}")

    def set_initial_tab(self, tab_name: str) -> None:
        """Set the initial tab to display."""
        tab_map = {
            "upgrade_finder": 0,
            "bis_guide": 1,
        }
        if tab_name in tab_map:
            self.tab_widget.setCurrentIndex(tab_map[tab_name])

    def set_profile(self, profile_name: str) -> None:
        """Set the current profile programmatically."""
        idx = self.profile_combo.findText(profile_name)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
