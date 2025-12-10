"""
AI Advisor Screen - Build optimization and upgrade recommendations.

This screen consolidates build-related features:
- PoB panel (moved from main view)
- AI upgrade analysis
- Build comparison, BiS search, upgrade finder
- Analysis history
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QFrame,
    QLabel,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui_qt.screens.base_screen import BaseScreen

if TYPE_CHECKING:
    from core.interfaces import IAppContext
    from core.pob_integration import CharacterManager
    from gui_qt.views.upgrade_advisor_view import UpgradeAdvisorView

logger = logging.getLogger(__name__)


class BuildActionsPanel(QFrame):
    """
    Quick actions panel for build-related operations.

    Provides buttons for common build actions like compare, BiS search, etc.
    """

    compare_clicked = pyqtSignal()
    bis_clicked = pyqtSignal()
    library_clicked = pyqtSignal()
    upgrade_finder_clicked = pyqtSignal()
    item_compare_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Build Actions")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        # Compare Builds
        self._compare_btn = QPushButton("Compare Builds")
        self._compare_btn.setToolTip("Compare passive tree builds")
        self._compare_btn.clicked.connect(self.compare_clicked.emit)
        layout.addWidget(self._compare_btn)

        # BiS Search
        self._bis_btn = QPushButton("Find BiS Item")
        self._bis_btn.setToolTip("Search for best-in-slot items")
        self._bis_btn.clicked.connect(self.bis_clicked.emit)
        layout.addWidget(self._bis_btn)

        # Upgrade Finder
        self._upgrade_btn = QPushButton("Upgrade Finder")
        self._upgrade_btn.setToolTip("Find gear upgrades within budget")
        self._upgrade_btn.clicked.connect(self.upgrade_finder_clicked.emit)
        layout.addWidget(self._upgrade_btn)

        # Item Comparison
        self._item_compare_btn = QPushButton("Compare Items")
        self._item_compare_btn.setToolTip("Side-by-side item comparison")
        self._item_compare_btn.clicked.connect(self.item_compare_clicked.emit)
        layout.addWidget(self._item_compare_btn)

        # Build Library
        self._library_btn = QPushButton("Build Library")
        self._library_btn.setToolTip("Manage saved build profiles")
        self._library_btn.clicked.connect(self.library_clicked.emit)
        layout.addWidget(self._library_btn)

        layout.addStretch()


class AIAdvisorScreen(BaseScreen):
    """
    AI Advisor screen for build optimization.

    Layout:
    +------------------------------------------+
    | +------------------+ +------------------+ |
    | | PoB Panel        | | Upgrade Advisor  | |
    | | - Profile Select | | - Equipment Tree | |
    | | - Build Stats    | | - AI Analysis    | |
    | | - Equipment Tree | | - History Panel  | |
    | +------------------+ +------------------+ |
    | +------------------+                      |
    | | Build Actions    |                      |
    | | - Compare Builds |                      |
    | | - Find BiS       |                      |
    | +------------------+                      |
    +------------------------------------------+
    """

    # Signals for parent window to handle
    upgrade_analysis_requested = pyqtSignal(str, bool)  # slot, include_stash
    compare_builds_requested = pyqtSignal()
    bis_search_requested = pyqtSignal()
    library_requested = pyqtSignal()
    upgrade_finder_requested = pyqtSignal()
    item_compare_requested = pyqtSignal()
    price_check_requested = pyqtSignal(str)

    def __init__(
        self,
        ctx: "IAppContext",
        character_manager: Optional["CharacterManager"] = None,
        on_status: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the AI Advisor screen."""
        super().__init__(ctx, on_status, parent)
        self._character_manager = character_manager
        self._upgrade_advisor: Optional["UpgradeAdvisorView"] = None
        self._actions_panel: Optional[BuildActionsPanel] = None

        self._create_ui()

    def _create_ui(self) -> None:
        """Create the AI Advisor UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ========== LEFT SIDE: Build Actions Panel ==========
        # Build Actions Panel (PoB Panel removed - UpgradeAdvisorView has equipment display)
        self._actions_panel = BuildActionsPanel()
        self._actions_panel.compare_clicked.connect(self.compare_builds_requested.emit)
        self._actions_panel.bis_clicked.connect(self.bis_search_requested.emit)
        self._actions_panel.library_clicked.connect(self.library_requested.emit)
        self._actions_panel.upgrade_finder_clicked.connect(self.upgrade_finder_requested.emit)
        self._actions_panel.item_compare_clicked.connect(self.item_compare_requested.emit)
        self._actions_panel.setMinimumWidth(180)
        self._actions_panel.setMaximumWidth(220)
        main_splitter.addWidget(self._actions_panel)

        # ========== RIGHT SIDE: Upgrade Advisor View ==========
        from gui_qt.views.upgrade_advisor_view import UpgradeAdvisorView

        self._upgrade_advisor = UpgradeAdvisorView(
            ctx=self.ctx,
            character_manager=self._character_manager,
            on_status=self._on_status,
            parent=self,
        )
        # Hide the back button since we're in a screen, not a modal
        self._upgrade_advisor.back_btn.hide()
        self._upgrade_advisor.close_btn.hide()

        # Connect signals
        self._upgrade_advisor.upgrade_analysis_requested.connect(
            self.upgrade_analysis_requested.emit
        )

        main_splitter.addWidget(self._upgrade_advisor)

        # Set splitter sizes
        main_splitter.setSizes([200, 1000])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

        layout.addWidget(main_splitter)

    def _on_upgrade_slot_selected(self, slot: str) -> None:
        """Handle slot selection from PoB panel for upgrade analysis."""
        if self._upgrade_advisor:
            self._upgrade_advisor.select_slot(slot)

    def set_character_manager(self, character_manager: "CharacterManager") -> None:
        """Set the character manager after initialization."""
        self._character_manager = character_manager
        # Recreate UI with the manager
        # Clear existing layout
        layout = self.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item and item.widget():
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
        self._create_ui()

    def get_upgrade_advisor(self):
        """Get the upgrade advisor view for external control."""
        return self._upgrade_advisor

    def show_analysis_result(self, slot: str, result: str, provider: str) -> None:
        """Display analysis result in the upgrade advisor."""
        if self._upgrade_advisor:
            self._upgrade_advisor.show_analysis_result(slot, result, provider)

    def show_analysis_error(self, slot: str, error: str) -> None:
        """Display analysis error in the upgrade advisor."""
        if self._upgrade_advisor:
            self._upgrade_advisor.show_analysis_error(slot, error)

    @property
    def screen_name(self) -> str:
        """Return the screen display name."""
        return "AI Advisor"

    def on_enter(self) -> None:
        """Called when entering this screen."""
        self.set_status("AI Advisor - Select a build slot to analyze")
        if self._upgrade_advisor:
            self._upgrade_advisor.refresh()

    def on_leave(self) -> None:
        """Called when leaving this screen."""
        pass

    def refresh(self) -> None:
        """Refresh screen data."""
        if self._upgrade_advisor:
            self._upgrade_advisor.refresh()
