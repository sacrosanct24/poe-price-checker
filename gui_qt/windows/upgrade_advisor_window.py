"""
gui_qt.windows.upgrade_advisor_window

AI-powered gear upgrade advisor window.

Analyzes each equipment slot and recommends:
- Upgrades from player's stash
- Trade search suggestions for external upgrades
- Good/Better/Best tier classification
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QHeaderView,
    QProgressBar,
    QFrame,
    QComboBox,
)

from gui_qt.styles import apply_window_icon, COLORS, get_rarity_color

if TYPE_CHECKING:
    from core.config import Config
    from core.database import Database
    from core.pob_integration import CharacterManager, CharacterProfile

logger = logging.getLogger(__name__)


# Equipment slots in display order
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


class UpgradeAdvisorWindow(QDialog):
    """
    Window for AI-powered gear upgrade recommendations.

    Shows all equipment slots with current items and allows
    per-slot or full-build upgrade analysis.

    Signals:
        upgrade_analysis_requested: Emitted with (slot, item_text) when analysis requested.
        analysis_complete: Emitted when an analysis finishes.
    """

    # Signals
    upgrade_analysis_requested = pyqtSignal(str, str)  # slot, item_text
    analysis_complete = pyqtSignal(str, str)  # slot, result_text

    def __init__(
        self,
        config: "Config",
        character_manager: "CharacterManager",
        parent: Optional[QWidget] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the upgrade advisor window.

        Args:
            config: Application configuration.
            character_manager: Character/build manager.
            parent: Parent widget.
            on_status: Callback for status messages.
        """
        super().__init__(parent)

        self._config = config
        self._character_manager = character_manager
        self._on_status = on_status or (lambda msg: None)

        # Current profile and items
        self._current_profile: Optional["CharacterProfile"] = None
        self._equipment_items: Dict[str, Any] = {}

        # Analysis state
        self._analyzing_slot: Optional[str] = None
        self._analysis_results: Dict[str, str] = {}

        # AI configured callback
        self._ai_configured_callback: Optional[Callable[[], bool]] = None

        # Database for caching (set via set_database)
        self._db: Optional["Database"] = None

        # Track item hashes for cache invalidation
        self._item_hashes: Dict[str, str] = {}

        # Track which results are from cache
        self._cached_slots: set = set()

        self.setWindowTitle("Upgrade Advisor")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_profile()

    def set_ai_configured_callback(self, callback: Callable[[], bool]) -> None:
        """Set callback to check if AI is configured."""
        self._ai_configured_callback = callback
        self._update_button_states()

    def set_database(self, db: "Database") -> None:
        """Set database for caching upgrade advice."""
        self._db = db

    def get_selected_provider(self) -> str:
        """Get the currently selected AI provider."""
        return self.provider_combo.currentData() or ""

    def _is_ai_configured(self) -> bool:
        """Check if the selected AI provider is configured.

        First checks the callback (for external control/testing),
        then falls back to checking the provider's API key.
        """
        # If callback is set and returns False, AI is not configured
        if self._ai_configured_callback and not self._ai_configured_callback():
            return False

        from data_sources.ai import is_local_provider

        provider = self.get_selected_provider()
        if not provider:
            return False
        # Ollama is local - no API key needed
        if is_local_provider(provider):
            return True
        # Check if API key is configured for this provider
        return bool(self._config.get_ai_api_key(provider))

    def _on_provider_changed(self, index: int) -> None:
        """Handle AI provider selection change."""
        provider = self.get_selected_provider()
        configured = self._is_ai_configured()

        # Update button states
        self._update_button_states()

        # Update tooltip with configuration status
        if not configured and provider:
            from data_sources.ai import is_local_provider
            if is_local_provider(provider):
                self.provider_combo.setToolTip(
                    f"{provider.title()} server not reachable.\n"
                    "Start Ollama or check host in Settings > AI."
                )
            else:
                self.provider_combo.setToolTip(
                    f"No API key configured for {provider}.\n"
                    "Add your API key in Settings > AI."
                )
        else:
            self.provider_combo.setToolTip(
                "Select AI provider for analysis.\n"
                "API key must be configured in Settings > AI."
            )

    def _sync_provider_combo(self) -> None:
        """Sync the provider combo box with the config setting."""
        current_provider = self._config.ai_provider
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == current_provider:
                self.provider_combo.setCurrentIndex(i)
                break

    def _compute_item_hash(self, item_data: Any) -> str:
        """Compute a hash of item data to detect changes.

        Args:
            item_data: Item data from PoB.

        Returns:
            MD5 hash string of key item properties.
        """
        if not item_data:
            return "empty"

        # Build a string of key properties
        parts = [
            getattr(item_data, "name", "") or "",
            getattr(item_data, "base_type", "") or "",
            getattr(item_data, "rarity", "") or "",
            str(getattr(item_data, "item_level", 0)),
        ]

        # Add mods
        for mod in getattr(item_data, "implicit_mods", []) or []:
            parts.append(mod)
        for mod in getattr(item_data, "explicit_mods", []) or []:
            parts.append(mod)

        content = "|".join(parts)
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)

        # Header with profile info
        header = self._create_header()
        layout.addWidget(header)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Equipment slots
        left_panel = self._create_equipment_panel()
        splitter.addWidget(left_panel)

        # Right panel: Analysis results
        right_panel = self._create_results_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 600])
        layout.addWidget(splitter, stretch=1)

        # Bottom action bar
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)

    def _create_header(self) -> QWidget:
        """Create the header with profile info and AI provider selector."""
        from data_sources.ai import SUPPORTED_PROVIDERS, get_provider_display_name

        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)

        # Profile name
        self.profile_label = QLabel("No profile loaded")
        self.profile_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.profile_label)

        layout.addStretch()

        # AI Provider selector
        layout.addWidget(QLabel("AI Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumWidth(150)
        for provider in SUPPORTED_PROVIDERS:
            display_name = get_provider_display_name(provider)
            self.provider_combo.addItem(display_name, provider)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.provider_combo.setToolTip(
            "Select AI provider for analysis.\n"
            "API key must be configured in Settings > AI."
        )
        layout.addWidget(self.provider_combo)

        layout.addSpacing(12)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._load_profile)
        layout.addWidget(refresh_btn)

        return frame

    def _create_equipment_panel(self) -> QWidget:
        """Create the equipment slots panel."""
        group = QGroupBox("Equipment Slots")
        layout = QVBoxLayout(group)

        # Equipment tree
        self.equipment_tree = QTreeWidget()
        self.equipment_tree.setHeaderLabels(["Slot", "Current Item", "Status"])
        self.equipment_tree.setRootIsDecorated(False)
        self.equipment_tree.setAlternatingRowColors(True)
        self.equipment_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        # Column sizing
        header = self.equipment_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.equipment_tree.itemClicked.connect(self._on_slot_clicked)
        self.equipment_tree.itemDoubleClicked.connect(self._on_slot_double_clicked)

        layout.addWidget(self.equipment_tree)

        # Analyze selected button
        btn_layout = QHBoxLayout()
        self.analyze_selected_btn = QPushButton("Analyze Selected Slot")
        self.analyze_selected_btn.setEnabled(False)
        self.analyze_selected_btn.clicked.connect(self._on_analyze_selected)
        btn_layout.addWidget(self.analyze_selected_btn)

        layout.addLayout(btn_layout)

        return group

    def _create_results_panel(self) -> QWidget:
        """Create the analysis results panel."""
        group = QGroupBox("Analysis Results")
        layout = QVBoxLayout(group)

        # Current slot label
        self.result_slot_label = QLabel("Select a slot to analyze")
        self.result_slot_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.result_slot_label)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results text
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText(
            "Analysis results will appear here.\n\n"
            "Select a slot and click 'Analyze Selected Slot' to get "
            "AI-powered upgrade recommendations based on:\n"
            "- Your current build stats\n"
            "- Items in your stash cache\n"
            "- Trade search suggestions"
        )
        layout.addWidget(self.results_text, stretch=1)

        return group

    def _create_action_bar(self) -> QHBoxLayout:
        """Create the bottom action bar."""
        layout = QHBoxLayout()

        # Analyze all button
        self.analyze_all_btn = QPushButton("Analyze All Slots")
        self.analyze_all_btn.setToolTip("Analyze all equipment slots (may take a while)")
        self.analyze_all_btn.clicked.connect(self._on_analyze_all)
        layout.addWidget(self.analyze_all_btn)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return layout

    def _load_profile(self) -> None:
        """Load the active character profile and cached advice."""
        self.equipment_tree.clear()
        self._equipment_items.clear()
        self._item_hashes.clear()
        self._cached_slots.clear()
        self._analysis_results.clear()

        # Get active profile
        profile = self._character_manager.get_active_profile()
        if not profile:
            self.profile_label.setText("No active profile")
            self._on_status("No active profile - import a build first")
            return

        self._current_profile = profile

        # Update header
        build = getattr(profile, "build", None)
        if build:
            class_name = getattr(build, "class_name", "?")
            ascendancy = getattr(build, "ascendancy", "")
            level = getattr(build, "level", "?")
            main_skill = getattr(build, "main_skill", "")

            if ascendancy:
                profile_text = f"{profile.name} - Lvl {level} {ascendancy}"
            else:
                profile_text = f"{profile.name} - Lvl {level} {class_name}"

            if main_skill:
                profile_text += f" ({main_skill})"

            self.profile_label.setText(profile_text)
        else:
            self.profile_label.setText(profile.name)

        # Load equipment
        items = getattr(build, "items", {}) or {} if build else {}
        self._equipment_items = items

        # Compute item hashes
        for slot in EQUIPMENT_SLOTS:
            item_data = items.get(slot)
            self._item_hashes[slot] = self._compute_item_hash(item_data)

        # Load cached advice from database
        self._load_cached_advice()

        # Populate tree
        for slot in EQUIPMENT_SLOTS:
            item_data = items.get(slot)
            self._add_slot_row(slot, item_data)

        # Sync provider combo with config
        self._sync_provider_combo()
        self._update_button_states()

    def _load_cached_advice(self) -> None:
        """Load cached advice from database for current profile."""
        if not self._db or not self._current_profile:
            return

        try:
            cached = self._db.get_all_upgrade_advice(self._current_profile.name)

            for slot, data in cached.items():
                cached_hash = data.get("item_hash", "")
                current_hash = self._item_hashes.get(slot, "")

                # Only use cache if item hasn't changed
                if cached_hash == current_hash:
                    self._analysis_results[slot] = data["advice_text"]
                    self._cached_slots.add(slot)
                    logger.debug(f"Loaded cached advice for {slot}")
                else:
                    logger.debug(f"Cache invalidated for {slot} (item changed)")

        except Exception as e:
            logger.warning(f"Failed to load cached advice: {e}")

    def _add_slot_row(self, slot: str, item_data: Any) -> None:
        """Add an equipment slot row to the tree."""
        if item_data:
            name = getattr(item_data, "name", "Unknown") or "Unknown"
            rarity = getattr(item_data, "rarity", "NORMAL")
        else:
            name = "(Empty)"
            rarity = "NORMAL"

        # Check if we have analysis results
        if slot in self._analysis_results:
            if slot in self._cached_slots:
                status_text = "Cached"
                status_color = COLORS.get("accent", "#2196F3")
            else:
                status_text = "Analyzed"
                status_color = COLORS.get("success", "#4CAF50")
        else:
            status_text = "-"
            status_color = COLORS.get("text_secondary", "#888888")

        tree_item = QTreeWidgetItem([slot, name, status_text])

        # Color item name by rarity
        color = get_rarity_color(rarity)
        tree_item.setForeground(1, QColor(color))

        # Color status
        tree_item.setForeground(2, QColor(status_color))

        # Store item data
        tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)
        tree_item.setData(1, Qt.ItemDataRole.UserRole, slot)

        self.equipment_tree.addTopLevelItem(tree_item)

    def _update_button_states(self) -> None:
        """Update button enabled states based on current state."""
        ai_ready = self._is_ai_configured()
        has_profile = self._current_profile is not None
        is_analyzing = self._analyzing_slot is not None

        # Analyze all
        self.analyze_all_btn.setEnabled(ai_ready and has_profile and not is_analyzing)

        # Selected slot button updated in click handler
        if not ai_ready:
            self.analyze_selected_btn.setToolTip("Configure AI in Settings > AI")
            self.analyze_all_btn.setToolTip("Configure AI in Settings > AI")
        else:
            self.analyze_selected_btn.setToolTip("")
            self.analyze_all_btn.setToolTip("Analyze all equipment slots")

    def _on_slot_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle slot selection."""
        slot = item.data(1, Qt.ItemDataRole.UserRole)
        item_data = item.data(0, Qt.ItemDataRole.UserRole)

        # Enable analyze button if AI is configured
        can_analyze = self._is_ai_configured() and self._analyzing_slot is None
        self.analyze_selected_btn.setEnabled(can_analyze)

        # Show previous results if available
        if slot in self._analysis_results:
            if slot in self._cached_slots:
                self.result_slot_label.setText(f"Results for: {slot} (Cached)")
            else:
                self.result_slot_label.setText(f"Results for: {slot}")
            self.results_text.setMarkdown(self._analysis_results[slot])
        else:
            self.result_slot_label.setText(f"Selected: {slot}")
            if item_data:
                # Show current item info
                name = getattr(item_data, "name", "Unknown")
                rarity = getattr(item_data, "rarity", "?")
                base = getattr(item_data, "base_type", "")
                self.results_text.setPlainText(
                    f"Current: {name}\n"
                    f"Base: {base}\n"
                    f"Rarity: {rarity}\n\n"
                    "Click 'Analyze Selected Slot' to get upgrade recommendations."
                )
            else:
                self.results_text.setPlainText(
                    f"Slot is empty.\n\n"
                    "Click 'Analyze Selected Slot' to get item suggestions."
                )

    def _on_slot_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle slot double-click - start analysis."""
        if self._is_ai_configured() and self._analyzing_slot is None:
            self._on_analyze_selected()

    def _on_analyze_selected(self) -> None:
        """Analyze the selected slot."""
        current = self.equipment_tree.currentItem()
        if not current:
            return

        slot = current.data(1, Qt.ItemDataRole.UserRole)
        item_data = current.data(0, Qt.ItemDataRole.UserRole)

        self._start_analysis(slot, item_data)

    def _on_analyze_all(self) -> None:
        """Analyze all equipment slots."""
        # For now, just analyze the first slot
        # Full implementation would queue all slots
        if self.equipment_tree.topLevelItemCount() > 0:
            first = self.equipment_tree.topLevelItem(0)
            if first:
                self.equipment_tree.setCurrentItem(first)
                self._on_analyze_selected()

    def _start_analysis(self, slot: str, item_data: Any) -> None:
        """Start analysis for a slot."""
        if self._analyzing_slot:
            return

        self._analyzing_slot = slot

        # Show loading state
        self.result_slot_label.setText(f"Analyzing: {slot}...")
        self.progress_bar.setVisible(True)
        self.results_text.setPlainText("Scanning stash for upgrade candidates...")

        # Update button states
        self.analyze_selected_btn.setEnabled(False)
        self.analyze_all_btn.setEnabled(False)

        # Generate item text if we have item data
        item_text = ""
        if item_data:
            item_text = self._generate_item_text(item_data)

        # Emit signal for controller to handle
        self.upgrade_analysis_requested.emit(slot, item_text)

        self._on_status(f"Analyzing upgrades for {slot}...")

    def show_analysis_result(
        self,
        slot: str,
        result: str,
        ai_model: Optional[str] = None,
    ) -> None:
        """Display analysis result for a slot.

        Args:
            slot: Equipment slot that was analyzed.
            result: Markdown-formatted result text.
            ai_model: AI model used (for cache metadata).
        """
        self._analyzing_slot = None
        self._analysis_results[slot] = result

        # Remove from cached slots since this is fresh
        self._cached_slots.discard(slot)

        # Save to cache
        self._save_to_cache(slot, result, ai_model)

        # Update UI
        self.progress_bar.setVisible(False)
        self.result_slot_label.setText(f"Results for: {slot}")
        self.results_text.setMarkdown(result)

        # Update tree status
        self._update_slot_status(slot, "Analyzed")

        # Re-enable buttons
        self._update_button_states()
        self.analyze_selected_btn.setEnabled(True)

        self.analysis_complete.emit(slot, result)
        self._on_status(f"Upgrade analysis complete for {slot}")

    def _save_to_cache(
        self,
        slot: str,
        result: str,
        ai_model: Optional[str] = None,
    ) -> None:
        """Save analysis result to database cache."""
        if not self._db or not self._current_profile:
            return

        try:
            item_hash = self._item_hashes.get(slot, "unknown")
            self._db.save_upgrade_advice(
                profile_name=self._current_profile.name,
                slot=slot,
                item_hash=item_hash,
                advice_text=result,
                ai_model=ai_model,
            )
            logger.debug(f"Saved advice for {slot} to cache")
        except Exception as e:
            logger.warning(f"Failed to save advice to cache: {e}")

    def show_analysis_error(self, slot: str, error: str) -> None:
        """Display analysis error for a slot.

        Args:
            slot: Equipment slot that failed.
            error: Error message.
        """
        self._analyzing_slot = None

        # Update UI
        self.progress_bar.setVisible(False)
        self.result_slot_label.setText(f"Error analyzing: {slot}")
        self.results_text.setPlainText(f"Analysis failed:\n\n{error}")

        # Update tree status
        self._update_slot_status(slot, "Error")

        # Re-enable buttons
        self._update_button_states()
        self.analyze_selected_btn.setEnabled(True)

        self._on_status(f"Upgrade analysis failed: {error}")

    def _update_slot_status(self, slot: str, status: str) -> None:
        """Update the status column for a slot."""
        for i in range(self.equipment_tree.topLevelItemCount()):
            item = self.equipment_tree.topLevelItem(i)
            if item and item.data(1, Qt.ItemDataRole.UserRole) == slot:
                item.setText(2, status)
                if status == "Analyzed":
                    item.setForeground(2, QColor(COLORS.get("success", "#4CAF50")))
                elif status == "Error":
                    item.setForeground(2, QColor(COLORS.get("error", "#F44336")))
                break

    def _generate_item_text(self, item_data: Any) -> str:
        """Generate PoE clipboard format text from item data."""
        lines = []

        rarity = getattr(item_data, "rarity", "RARE") or "RARE"
        name = getattr(item_data, "name", "Unknown") or "Unknown"
        base_type = getattr(item_data, "base_type", "") or ""

        # Clean up base_type if it contains "Unique ID:"
        if base_type and base_type.startswith("Unique ID:"):
            base_type = ""

        # Rarity line
        lines.append(f"Rarity: {rarity.title()}")

        # Name and base type
        if rarity.upper() in ("UNIQUE", "RARE"):
            lines.append(name)
            if base_type:
                lines.append(base_type)
        else:
            if base_type:
                lines.append(base_type)
            else:
                lines.append(name)

        lines.append("--------")

        # Item level
        ilvl = getattr(item_data, "item_level", None)
        if ilvl:
            lines.append(f"Item Level: {ilvl}")

        # Implicit mods
        implicits = getattr(item_data, "implicit_mods", []) or []
        if implicits:
            lines.append("--------")
            for mod in implicits:
                lines.append(mod)

        # Explicit mods
        explicits = getattr(item_data, "explicit_mods", []) or []
        if explicits:
            lines.append("--------")
            for mod in explicits:
                if not mod.startswith(("Armour:", "Energy Shield:", "ArmourBase", "EnergyShieldBase")):
                    lines.append(mod)

        return "\n".join(lines)

    def analyze_slot(self, slot: str) -> None:
        """Programmatically analyze a specific slot.

        Args:
            slot: Equipment slot name to analyze.
        """
        # Find and select the slot
        for i in range(self.equipment_tree.topLevelItemCount()):
            item = self.equipment_tree.topLevelItem(i)
            if item and item.data(1, Qt.ItemDataRole.UserRole) == slot:
                self.equipment_tree.setCurrentItem(item)
                self._on_analyze_selected()
                break
