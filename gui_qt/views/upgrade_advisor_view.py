"""
Full-Screen Upgrade Advisor View.

Replaces the main window content when active, providing a 3-panel layout
for equipment analysis with historical tracking.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data_sources.ai import SUPPORTED_PROVIDERS, get_provider_display_name, is_local_provider
from gui_qt.widgets.upgrade_history_panel import UpgradeHistoryPanel

if TYPE_CHECKING:
    from core.app_context import AppContext
    from core.pob_integration import CharacterManager, CharacterProfile

logger = logging.getLogger(__name__)

# Equipment slots to analyze
EQUIPMENT_SLOTS = [
    "Helmet",
    "Body Armour",
    "Gloves",
    "Boots",
    "Belt",
    "Amulet",
    "Ring 1",
    "Ring 2",
    "Weapon 1",
    "Weapon 2",
]


class UpgradeAdvisorView(QWidget):
    """
    Full-screen upgrade advisor with 3-panel layout.

    Layout:
    - Left: Equipment tree (slot selection)
    - Center: Results panel (current analysis)
    - Right: History panel (previous analyses)

    Signals:
        close_requested: Emitted when user wants to return to main view.
        upgrade_analysis_requested(slot, include_stash): Request analysis for a slot.
        analysis_complete(slot, result): Emitted when analysis completes.
    """

    close_requested = pyqtSignal()
    upgrade_analysis_requested = pyqtSignal(str, bool)  # slot, include_stash
    analysis_complete = pyqtSignal(str, str)  # slot, result

    def __init__(
        self,
        ctx: "AppContext",
        character_manager: Optional["CharacterManager"] = None,
        on_close: Optional[Callable[[], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize the upgrade advisor view.

        Args:
            ctx: Application context with config, db, etc.
            character_manager: PoB character manager.
            on_close: Callback when view is closed.
            on_status: Callback for status messages.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._ctx = ctx
        self._character_manager = character_manager
        self._on_close = on_close
        self._on_status = on_status or (lambda s: None)

        # State
        self._current_profile: Optional["CharacterProfile"] = None
        self._selected_slot: Optional[str] = None
        self._analyzing_slot: Optional[str] = None
        self._analysis_results: Dict[str, str] = {}
        self._item_hashes: Dict[str, str] = {}

        self._create_widgets()
        self._load_profile()

    def _create_widgets(self) -> None:
        """Create the 3-panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Header bar
        header = self._create_header()
        layout.addWidget(header)

        # Main 3-panel splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Equipment tree (~250px)
        self._equipment_panel = self._create_equipment_panel()
        main_splitter.addWidget(self._equipment_panel)

        # Center: Results panel (flexible)
        self._results_panel = self._create_results_panel()
        main_splitter.addWidget(self._results_panel)

        # Right: History panel (~300px)
        self._history_panel = UpgradeHistoryPanel()
        self._history_panel.history_selected.connect(self._on_history_selected)
        self._history_panel.use_cached.connect(self._on_use_cached)
        main_splitter.addWidget(self._history_panel)

        # Set initial sizes
        main_splitter.setSizes([250, 650, 300])
        main_splitter.setStretchFactor(0, 0)  # Equipment - fixed
        main_splitter.setStretchFactor(1, 1)  # Results - stretches
        main_splitter.setStretchFactor(2, 0)  # History - fixed

        layout.addWidget(main_splitter, stretch=1)

        # Footer bar
        footer = self._create_footer()
        layout.addWidget(footer)

    def _create_header(self) -> QFrame:
        """Create the header bar with profile info and AI selector."""
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.StyledPanel)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        # Back button
        self.back_btn = QPushButton("< Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.clicked.connect(self._on_close_clicked)
        header_layout.addWidget(self.back_btn)

        header_layout.addSpacing(16)

        # Profile label
        self.profile_label = QLabel("No profile loaded")
        self.profile_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.profile_label)

        header_layout.addStretch()

        # AI Provider selector
        header_layout.addWidget(QLabel("AI:"))
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumWidth(140)
        for provider in SUPPORTED_PROVIDERS:
            display = get_provider_display_name(provider)
            self.provider_combo.addItem(display, provider)
        # Set current from config
        current = self._ctx.config.ai_provider
        if current:
            idx = self.provider_combo.findData(current)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        header_layout.addWidget(self.provider_combo)

        header_layout.addSpacing(16)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Reload profile and equipment data")
        self.refresh_btn.clicked.connect(self._on_refresh)
        header_layout.addWidget(self.refresh_btn)

        return header

    def _create_equipment_panel(self) -> QGroupBox:
        """Create the equipment tree panel."""
        group = QGroupBox("Equipment Slots")
        layout = QVBoxLayout(group)

        # Equipment tree
        self.equipment_tree = QTreeWidget()
        self.equipment_tree.setHeaderLabels(["Slot", "Item", "Status"])
        self.equipment_tree.setColumnWidth(0, 80)
        self.equipment_tree.setColumnWidth(1, 100)
        self.equipment_tree.setColumnWidth(2, 60)
        self.equipment_tree.setRootIsDecorated(False)
        self.equipment_tree.itemClicked.connect(self._on_slot_clicked)
        self.equipment_tree.itemDoubleClicked.connect(self._on_slot_double_clicked)
        layout.addWidget(self.equipment_tree)

        # Analyze button
        self.analyze_btn = QPushButton("Analyze Selected Slot")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self.analyze_btn)

        return group

    def _create_results_panel(self) -> QGroupBox:
        """Create the center results panel."""
        group = QGroupBox("Analysis Results")
        layout = QVBoxLayout(group)

        # Slot label
        self.result_slot_label = QLabel("Select a slot to analyze")
        self.result_slot_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.result_slot_label)

        # Options row
        options_layout = QHBoxLayout()

        self.include_stash_cb = QCheckBox("Include Stash Scan")
        self.include_stash_cb.setToolTip(
            "Scan stash cache for potential upgrades.\n"
            "Requires stash to be fetched first."
        )
        self.include_stash_cb.setChecked(False)
        options_layout.addWidget(self.include_stash_cb)

        options_layout.addStretch()

        layout.addLayout(options_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results text
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText(
            "Select an equipment slot from the tree on the left,\n"
            "then click 'Analyze Selected Slot' to get AI recommendations.\n\n"
            "Previous analyses are shown in the History panel on the right."
        )
        layout.addWidget(self.results_text, stretch=1)

        # Viewing history indicator
        self.viewing_history_frame = QFrame()
        self.viewing_history_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.viewing_history_frame.setVisible(False)
        vh_layout = QHBoxLayout(self.viewing_history_frame)
        vh_layout.setContentsMargins(8, 4, 8, 4)
        self.viewing_history_label = QLabel("Viewing cached analysis")
        self.viewing_history_label.setStyleSheet("color: #888;")
        vh_layout.addWidget(self.viewing_history_label)
        vh_layout.addStretch()
        layout.addWidget(self.viewing_history_frame)

        return group

    def _create_footer(self) -> QFrame:
        """Create the footer bar with status and close button."""
        footer = QFrame()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(8, 4, 8, 4)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        footer_layout.addWidget(self.status_label)

        footer_layout.addStretch()

        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self._on_close_clicked)
        footer_layout.addWidget(self.close_btn)

        return footer

    # -------------------------------------------------------------------------
    # Profile Loading
    # -------------------------------------------------------------------------

    def _load_profile(self) -> None:
        """Load the active profile and populate equipment tree."""
        self._current_profile = None
        self._analysis_results.clear()
        self._item_hashes.clear()
        self.equipment_tree.clear()

        if not self._character_manager:
            self.profile_label.setText("No character manager")
            return

        profile = self._character_manager.get_active_profile()
        if not profile:
            self.profile_label.setText("No build loaded - import a build first")
            return

        self._current_profile = profile

        # Update header
        build = profile.build
        ascendancy = build.ascendancy or build.class_name
        skill = build.main_skill or "Unknown"
        level = build.level or "?"
        self.profile_label.setText(f"{profile.name} - Lv{level} {ascendancy} ({skill})")

        # Populate equipment tree
        self._populate_equipment_tree()

        # Load cached history
        self._load_all_history()

    def _populate_equipment_tree(self) -> None:
        """Populate the equipment tree with current items."""
        if not self._current_profile:
            return

        build = self._current_profile.build

        for slot in EQUIPMENT_SLOTS:
            item = build.items.get(slot)

            tree_item = QTreeWidgetItem()
            tree_item.setText(0, slot)

            if item:
                # Item name
                name = item.display_name or item.base_type or "Unknown"
                tree_item.setText(1, name[:20])

                # Color by rarity
                rarity = (item.rarity or "").upper()
                color = self._get_rarity_color(rarity)
                if color:
                    tree_item.setForeground(1, color)

                # Compute hash
                item_hash = self._compute_item_hash(item)
                self._item_hashes[slot] = item_hash

                # Store item data
                tree_item.setData(0, Qt.ItemDataRole.UserRole, item)
            else:
                tree_item.setText(1, "(empty)")
                tree_item.setForeground(1, QColor("#888"))

            # Status column (will be updated when history loads)
            tree_item.setText(2, "-")
            tree_item.setData(0, Qt.ItemDataRole.UserRole + 1, slot)

            self.equipment_tree.addTopLevelItem(tree_item)

    def _compute_item_hash(self, item: Any) -> str:
        """Compute a hash to detect item changes."""
        parts = [
            item.display_name or "",
            item.base_type or "",
            item.rarity or "",
            str(item.item_level or 0),
        ]
        parts.extend(item.implicit_mods or [])
        parts.extend(item.explicit_mods or [])
        content = "|".join(parts)
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _get_rarity_color(self, rarity: str) -> Optional[QColor]:
        """Get color for item rarity."""
        colors = {
            "UNIQUE": QColor("#AF6025"),
            "RARE": QColor("#FFFF77"),
            "MAGIC": QColor("#8888FF"),
            "NORMAL": QColor("#C8C8C8"),
        }
        return colors.get(rarity.upper())

    # -------------------------------------------------------------------------
    # History Loading
    # -------------------------------------------------------------------------

    def _load_all_history(self) -> None:
        """Load history status for all slots."""
        if not self._current_profile or not self._ctx.db:
            return

        # Get latest history for all slots
        all_history = self._ctx.db.get_all_slots_latest_history(
            self._current_profile.name
        )

        # Update tree status
        for i in range(self.equipment_tree.topLevelItemCount()):
            item = self.equipment_tree.topLevelItem(i)
            if not item:
                continue

            slot = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if slot in all_history:
                entry = all_history[slot]
                # Check if item changed
                current_hash = self._item_hashes.get(slot, "")
                cached_hash = entry.get("item_hash", "")
                if current_hash == cached_hash:
                    item.setText(2, "Cached")
                    item.setForeground(2, QColor("#4A90D9"))  # Accent blue
                else:
                    item.setText(2, "Stale")
                    item.setForeground(2, QColor("#888"))
            else:
                item.setText(2, "-")

    def _load_slot_history(self, slot: str) -> None:
        """Load history for a specific slot into the history panel."""
        if not self._current_profile or not self._ctx.db:
            self._history_panel.clear()
            return

        history = self._ctx.db.get_upgrade_advice_history(
            self._current_profile.name,
            slot,
            limit=5,
        )
        self._history_panel.load_history(slot, history)

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_slot_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle slot selection in equipment tree."""
        slot = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not slot:
            return

        self._selected_slot = slot
        self.result_slot_label.setText(f"Selected: {slot}")
        self.analyze_btn.setEnabled(self._is_ai_configured())
        self.viewing_history_frame.setVisible(False)

        # Show current item or previous result
        if slot in self._analysis_results:
            self.results_text.setMarkdown(self._analysis_results[slot])
        else:
            # Show item info
            pob_item = item.data(0, Qt.ItemDataRole.UserRole)
            if pob_item:
                self._show_item_info(pob_item)
            else:
                self.results_text.clear()

        # Load history for this slot
        self._load_slot_history(slot)

    def _on_slot_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double-click - start analysis."""
        if self._is_ai_configured() and self._selected_slot:
            self._start_analysis()

    def _on_analyze_clicked(self) -> None:
        """Handle analyze button click."""
        if self._selected_slot:
            self._start_analysis()

    def _on_history_selected(self, history_id: int) -> None:
        """Handle history entry selection - show preview."""
        # The panel handles the preview display
        pass

    def _on_use_cached(self, history_id: int) -> None:
        """Handle 'use cached' - display historical analysis."""
        entry = self._history_panel.get_entry_by_id(history_id)
        if not entry:
            return

        advice = entry.get("advice_text", "")
        self.results_text.setMarkdown(advice)

        # Show viewing history indicator
        self.viewing_history_frame.setVisible(True)
        created = entry.get("created_at", "")[:16]
        provider = entry.get("ai_provider", "AI")
        self.viewing_history_label.setText(
            f"Viewing cached analysis from {created} ({provider})"
        )

        self._set_status(f"Showing cached analysis for {self._selected_slot}")

    def _on_refresh(self) -> None:
        """Handle refresh button click."""
        self._load_profile()
        self._set_status("Profile refreshed")

    def _on_close_clicked(self) -> None:
        """Handle close/back button click."""
        if self._on_close:
            self._on_close()
        self.close_requested.emit()

    # -------------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------------

    def _start_analysis(self) -> None:
        """Start AI analysis for the selected slot."""
        if not self._selected_slot:
            return

        if not self._is_ai_configured():
            self._set_status("AI not configured - select a provider")
            return

        slot = self._selected_slot
        include_stash = self.include_stash_cb.isChecked()

        # Update UI
        self._analyzing_slot = slot
        self.progress_bar.setVisible(True)
        self.analyze_btn.setEnabled(False)
        self.result_slot_label.setText(f"Analyzing {slot}...")
        self.viewing_history_frame.setVisible(False)

        # Emit signal for main window to handle
        self.upgrade_analysis_requested.emit(slot, include_stash)

    def show_analysis_result(
        self,
        slot: str,
        result: str,
        ai_provider: Optional[str] = None,
    ) -> None:
        """
        Display analysis result and save to history.

        Called by main window when analysis completes.

        Args:
            slot: Equipment slot that was analyzed.
            result: Markdown-formatted AI response.
            ai_provider: Provider that generated the result.
        """
        # Clear analyzing state
        self._analyzing_slot = None
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)

        # Store result
        self._analysis_results[slot] = result

        # Display
        if slot == self._selected_slot:
            self.results_text.setMarkdown(result)
            self.result_slot_label.setText(f"Analysis: {slot}")
            self.viewing_history_frame.setVisible(False)

        # Update tree status
        self._update_slot_status(slot, "Analyzed", QColor("#50C878"))

        # Save to history
        self._save_to_history(slot, result, ai_provider)

        # Reload history panel
        if slot == self._selected_slot:
            self._load_slot_history(slot)

        self._set_status(f"Analysis complete for {slot}")
        self.analysis_complete.emit(slot, result)

    def show_analysis_error(self, slot: str, error: str) -> None:
        """
        Display analysis error.

        Args:
            slot: Equipment slot that failed.
            error: Error message.
        """
        self._analyzing_slot = None
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)

        if slot == self._selected_slot:
            self.results_text.setPlainText(f"Analysis failed:\n\n{error}")
            self.result_slot_label.setText(f"Error: {slot}")

        self._update_slot_status(slot, "Error", QColor("#FF6B6B"))
        self._set_status(f"Analysis failed: {error}")

    def _save_to_history(
        self,
        slot: str,
        result: str,
        ai_provider: Optional[str] = None,
    ) -> None:
        """Save analysis result to history database."""
        if not self._current_profile or not self._ctx.db:
            return

        item_hash = self._item_hashes.get(slot, "")
        include_stash = self.include_stash_cb.isChecked()

        # Get model from provider
        ai_model = None
        if ai_provider:
            # Could look up default model per provider
            pass

        self._ctx.db.save_upgrade_advice_history(
            profile_name=self._current_profile.name,
            slot=slot,
            item_hash=item_hash,
            advice_text=result,
            ai_model=ai_model,
            ai_provider=ai_provider,
            include_stash=include_stash,
            stash_candidates_count=0,  # Could be passed from controller
        )

    def _update_slot_status(
        self, slot: str, status: str, color: Optional[QColor] = None
    ) -> None:
        """Update the status column for a slot in the tree."""
        for i in range(self.equipment_tree.topLevelItemCount()):
            item = self.equipment_tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole + 1) == slot:
                item.setText(2, status)
                if color:
                    item.setForeground(2, color)
                break

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _show_item_info(self, item: Any) -> None:
        """Show basic item info in the results panel."""
        lines = []
        lines.append(f"**{item.display_name or 'Unknown'}**")
        if item.base_type:
            lines.append(f"Base: {item.base_type}")
        if item.rarity:
            lines.append(f"Rarity: {item.rarity}")
        if item.item_level:
            lines.append(f"Item Level: {item.item_level}")

        if item.implicit_mods:
            lines.append("\n**Implicits:**")
            for mod in item.implicit_mods:
                lines.append(f"- {mod}")

        if item.explicit_mods:
            lines.append("\n**Explicits:**")
            for mod in item.explicit_mods:
                lines.append(f"- {mod}")

        self.results_text.setMarkdown("\n".join(lines))

    def _is_ai_configured(self) -> bool:
        """Check if AI is configured for analysis."""
        provider = self.get_selected_provider()
        if not provider:
            return False

        if is_local_provider(provider):
            return True

        return bool(self._ctx.config.get_ai_api_key(provider))

    def get_selected_provider(self) -> str:
        """Get the currently selected AI provider."""
        return self.provider_combo.currentData() or ""

    def _set_status(self, message: str) -> None:
        """Update status label and callback."""
        self.status_label.setText(message)
        self._on_status(message)

    # -------------------------------------------------------------------------
    # Public Interface
    # -------------------------------------------------------------------------

    def refresh(self) -> None:
        """Refresh the view with current data."""
        self._load_profile()

    def select_slot(self, slot: str) -> None:
        """
        Select and analyze a specific slot.

        Args:
            slot: Equipment slot to select.
        """
        for i in range(self.equipment_tree.topLevelItemCount()):
            item = self.equipment_tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole + 1) == slot:
                self.equipment_tree.setCurrentItem(item)
                self._on_slot_clicked(item, 0)
                break
