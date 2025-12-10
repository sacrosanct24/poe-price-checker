"""
gui_qt.widgets.pob_panel

Embedded PoB character panel for the integrated main window.
Shows characters and equipment in a compact sidebar format.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QHeaderView,
    QMenu,
)

from gui_qt.styles import COLORS, get_rarity_color
from gui_qt.widgets.item_context_menu import ItemContext, ItemContextMenuManager


class PoBPanel(QWidget):
    """Embedded PoB character panel for the main window sidebar."""

    # Signals
    item_selected = pyqtSignal(str, dict)  # Emits (item_text, item_data)
    price_check_requested = pyqtSignal(str)  # Emits item text
    ai_analysis_requested = pyqtSignal(str, list)  # item_text, price_results
    upgrade_analysis_requested = pyqtSignal(str, str)  # slot, item_text

    def __init__(
        self,
        character_manager: Any,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self._profiles_cache: Dict[str, Dict[str, Any]] = {}
        self._selected_profile: Optional[str] = None

        # Context menu manager
        self._context_menu_manager = ItemContextMenuManager(self)
        self._context_menu_manager.set_options(
            show_inspect=False,  # PoB items don't have an inspect dialog
            show_price_check=True,
            show_ai=True,
            show_copy=True,
            show_upgrade_analysis=True,  # Enable upgrade analysis for PoB equipment
        )
        self._context_menu_manager.ai_analysis_requested.connect(self.ai_analysis_requested.emit)
        self._context_menu_manager.price_check_requested.connect(self.price_check_requested.emit)
        self._context_menu_manager.upgrade_analysis_requested.connect(self.upgrade_analysis_requested.emit)

        self._create_widgets()
        self._load_profiles()

    def set_ai_configured_callback(self, callback: Callable[[], bool]) -> None:
        """Set callback to check if AI is configured.

        Args:
            callback: Function returning True if AI is ready to use.
        """
        self._context_menu_manager.set_ai_configured_callback(callback)

    def _create_widgets(self) -> None:
        """Create the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header with profile selector
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Character:"))

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(150)
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        header_layout.addWidget(self.profile_combo, stretch=1)

        layout.addLayout(header_layout)

        # Character info (compact)
        info_layout = QHBoxLayout()
        self.class_label = QLabel("")
        self.class_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_layout.addWidget(self.class_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Equipment tree
        self.equipment_tree = QTreeWidget()
        self.equipment_tree.setHeaderLabels(["Slot", "Item"])
        self.equipment_tree.setRootIsDecorated(False)
        self.equipment_tree.setAlternatingRowColors(True)
        self.equipment_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        # Column sizing
        header = self.equipment_tree.header()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.equipment_tree.itemClicked.connect(self._on_item_clicked)
        self.equipment_tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        # Context menu
        self.equipment_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.equipment_tree.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.equipment_tree, stretch=1)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.check_selected_btn = QPushButton("Check Selected")
        self.check_selected_btn.setEnabled(False)
        self.check_selected_btn.clicked.connect(self._on_check_selected)
        btn_layout.addWidget(self.check_selected_btn)

        self.check_all_btn = QPushButton("Check All")
        self.check_all_btn.clicked.connect(self._on_check_all)
        btn_layout.addWidget(self.check_all_btn)

        layout.addLayout(btn_layout)

    def _load_profiles(self) -> None:
        """Load available character profiles."""
        self.profile_combo.clear()

        if not self.character_manager:
            self.profile_combo.addItem("(No profiles)")
            return

        try:
            # list_profiles() returns a list of profile names (strings)
            profile_names = self.character_manager.list_profiles()

            if not profile_names:
                self.profile_combo.addItem("(No profiles)")
                return

            # Load full profile data for each name
            self._profiles_cache = {}
            for name in profile_names:
                try:
                    profile = self.character_manager.get_profile(name)
                    if profile:
                        self._profiles_cache[name] = profile
                except Exception as e:
                    logger.debug(f"Failed to load profile '{name}': {e}")

            # Get active profile (returns CharacterProfile object, not dict)
            active = self.character_manager.get_active_profile()
            active_name = getattr(active, "name", None) if active else None

            # Populate combo
            for name in profile_names:
                self.profile_combo.addItem(name)

            # Select active profile
            if active_name:
                idx = self.profile_combo.findText(active_name)
                if idx >= 0:
                    self.profile_combo.setCurrentIndex(idx)

        except Exception as e:
            self.profile_combo.addItem(f"(Error: {e})")

    def _on_profile_changed(self, name: str) -> None:
        """Handle profile selection change."""
        if not name or name.startswith("("):
            self._clear_equipment()
            return

        self._selected_profile = name
        profile = self._profiles_cache.get(name)

        if profile:
            self._display_profile(profile)

    def _display_profile(self, profile: Any) -> None:
        """Display profile info and equipment."""
        # Profile is a CharacterProfile object with .build attribute
        build = getattr(profile, "build", None)
        if not build:
            self._clear_equipment()
            return

        # Update class label - build is a PoBBuild object
        class_name = getattr(build, "class_name", "?")
        ascendancy = getattr(build, "ascendancy", "")
        level = getattr(build, "level", "?")

        if ascendancy:
            self.class_label.setText(f"Lvl {level} {ascendancy}")
        else:
            self.class_label.setText(f"Lvl {level} {class_name}")

        # Update equipment tree - items is a dict of slot -> PoBItem
        self.equipment_tree.clear()
        items = getattr(build, "items", {}) or {}

        # Define slot order
        slot_order = [
            "Weapon 1", "Weapon 2",
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Amulet", "Ring 1", "Ring 2", "Belt",
        ]

        for slot in slot_order:
            if slot in items:
                item_data = items[slot]
                self._add_equipment_item(slot, item_data)

    def _add_equipment_item(self, slot: str, item_data: Any) -> None:
        """Add an equipment item to the tree (item_data is a PoBItem object)."""
        name = getattr(item_data, "name", "Unknown")
        rarity = getattr(item_data, "rarity", "NORMAL")
        base_type = getattr(item_data, "base_type", "")

        item = QTreeWidgetItem([slot, name])

        # Set color based on rarity
        color = get_rarity_color(rarity)
        item.setForeground(1, QColor(color))

        # Store item data
        item.setData(0, Qt.ItemDataRole.UserRole, item_data)
        item.setData(1, Qt.ItemDataRole.UserRole, slot)

        # Tooltip with more info
        tooltip = f"{name}\n{base_type}\nRarity: {rarity}"
        item.setToolTip(0, tooltip)
        item.setToolTip(1, tooltip)

        self.equipment_tree.addTopLevelItem(item)

    def _clear_equipment(self) -> None:
        """Clear equipment display."""
        self.equipment_tree.clear()
        self.class_label.setText("")
        self.check_selected_btn.setEnabled(False)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item click - enable check button."""
        self.check_selected_btn.setEnabled(True)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item double-click - trigger price check."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data:
            item_text = self._generate_item_text(item_data)
            self.price_check_requested.emit(item_text)

    def _show_context_menu(self, position) -> None:
        """Show context menu for equipment items."""
        tree_item = self.equipment_tree.itemAt(position)
        if not tree_item:
            return

        item_data = tree_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        # Get slot name from UserRole
        slot = tree_item.data(1, Qt.ItemDataRole.UserRole) or ""

        # Get item text and name
        item_text = self._generate_item_text(item_data)
        item_name = getattr(item_data, "name", "Unknown") or "Unknown"

        # Build item context
        item_context = ItemContext(
            item_name=item_name,
            item_text=item_text,
            chaos_value=0,  # PoB items don't have prices yet
            divine_value=0,
            source="",
        )

        # Show the menu with slot for upgrade analysis
        viewport = self.equipment_tree.viewport()
        if viewport:
            self._context_menu_manager.show_menu(
                viewport.mapToGlobal(position),
                item_context,
                self.equipment_tree,
                slot=slot,
            )

    def _on_check_selected(self) -> None:
        """Check price of selected item."""
        item = self.equipment_tree.currentItem()
        if not item:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data:
            item_text = self._generate_item_text(item_data)
            self.price_check_requested.emit(item_text)

    def _on_check_all(self) -> None:
        """Check prices of all equipment (emits first item for now)."""
        # For batch checking, emit items one at a time
        for i in range(self.equipment_tree.topLevelItemCount()):
            item = self.equipment_tree.topLevelItem(i)
            if item:
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                if item_data:
                    item_text = self._generate_item_text(item_data)
                    self.price_check_requested.emit(item_text)
                    break  # For now, just check first - full batch needs different handling

    def _generate_item_text(self, item_data: Any) -> str:
        """Generate PoE clipboard format text from PoBItem object."""
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

        # Influences (PoBItem may not have this attribute)
        influences = getattr(item_data, "influences", []) or []
        for influence in influences:
            lines.append(f"{influence} Item")

        if influences:
            lines.append("--------")

        # Item level
        ilvl = getattr(item_data, "item_level", None)
        if ilvl:
            lines.append(f"Item Level: {ilvl}")

        # Quality
        quality = getattr(item_data, "quality", 0) or 0
        if quality > 0:
            lines.append(f"Quality: +{quality}%")

        # Sockets
        sockets = getattr(item_data, "sockets", "") or ""
        if sockets:
            lines.append(f"Sockets: {sockets}")

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
                # Skip metadata lines
                if mod.startswith("Armour:") or mod.startswith("ArmourBasePercentile:"):
                    continue
                if mod.startswith("Energy Shield:") or mod.startswith("EnergyShieldBasePercentile:"):
                    continue
                lines.append(mod)

        return "\n".join(lines)

    def refresh(self) -> None:
        """Refresh the profile list."""
        self._load_profiles()

    def get_selected_item_text(self) -> Optional[str]:
        """Get the item text for the currently selected equipment."""
        item = self.equipment_tree.currentItem()
        if not item:
            return None

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data:
            return self._generate_item_text(item_data)
        return None

    def get_all_equipment(self) -> List[Dict[str, Any]]:
        """Get all equipment items as a list of dicts with text."""
        equipment = []
        for i in range(self.equipment_tree.topLevelItemCount()):
            item = self.equipment_tree.topLevelItem(i)
            if item:
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                slot = item.data(1, Qt.ItemDataRole.UserRole)
                if item_data:
                    equipment.append({
                        "slot": slot,
                        "data": item_data,
                        "text": self._generate_item_text(item_data),
                    })
        return equipment
