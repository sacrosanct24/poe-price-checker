"""
gui_qt.windows.pob_character_window

PyQt6 window for managing Path of Building character imports.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QFormLayout,
    QMessageBox,
    QHeaderView,
)

from gui_qt.styles import COLORS, get_rarity_color

# Try to import BuildCategory
try:
    from core.pob_integration import BuildCategory
    BUILD_CATEGORIES = list(BuildCategory)
except ImportError:
    BUILD_CATEGORIES = []


class PoBCharacterWindow(QDialog):
    """Window for managing PoB character profiles."""

    profile_selected = pyqtSignal(str)  # Emits profile name
    price_check_requested = pyqtSignal(str)  # Emits item text for price checking

    def __init__(
        self,
        character_manager: Any,
        parent: Optional[QWidget] = None,
        on_profile_selected: Optional[Callable[[str], None]] = None,
        on_price_check: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self.on_profile_selected = on_profile_selected
        self.on_price_check = on_price_check

        self._selected_profile: Optional[str] = None
        self._profiles_cache: Dict[str, Dict[str, Any]] = {}

        self.setWindowTitle("PoB Character Manager")
        self.setMinimumSize(850, 550)
        self.resize(900, 600)

        self._create_widgets()
        self._load_profiles()

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Character list
        left_panel = QGroupBox("Characters")
        left_layout = QVBoxLayout(left_panel)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All")
        self.filter_combo.addItem("---")
        for cat in BUILD_CATEGORIES:
            self.filter_combo.addItem(cat.value.replace("_", " ").title())
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_combo)
        left_layout.addLayout(filter_row)

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self.profile_list)

        # Button row 1
        btn_row1 = QHBoxLayout()
        self.import_btn = QPushButton("Import...")
        self.import_btn.clicked.connect(self._on_import)
        btn_row1.addWidget(self.import_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row1.addWidget(self.delete_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_profiles)
        btn_row1.addWidget(self.refresh_btn)
        left_layout.addLayout(btn_row1)

        # Button row 2
        btn_row2 = QHBoxLayout()
        self.set_active_btn = QPushButton("Set Active")
        self.set_active_btn.clicked.connect(self._on_set_active)
        btn_row2.addWidget(self.set_active_btn)

        self.categories_btn = QPushButton("Categories...")
        self.categories_btn.clicked.connect(self._on_manage_categories)
        btn_row2.addWidget(self.categories_btn)

        btn_row2.addStretch()
        left_layout.addLayout(btn_row2)

        splitter.addWidget(left_panel)

        # Right panel: Character details
        right_panel = QGroupBox("Character Details")
        right_layout = QVBoxLayout(right_panel)

        # Info grid
        info_form = QFormLayout()
        self.info_labels: Dict[str, QLabel] = {}
        for field in ["Name", "Class", "Level", "Items", "Categories", "Status"]:
            label = QLabel("-")
            self.info_labels[field] = label
            info_form.addRow(f"{field}:", label)
        right_layout.addLayout(info_form)

        # Equipment tree
        right_layout.addWidget(QLabel("Equipment:"))
        self.equipment_tree = QTreeWidget()
        self.equipment_tree.setHeaderLabels(["Slot", "Item Name", "Base Type", "Rarity"])
        self.equipment_tree.setRootIsDecorated(False)
        self.equipment_tree.setAlternatingRowColors(True)
        self.equipment_tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        header = self.equipment_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        right_layout.addWidget(self.equipment_tree)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

        # Bottom: Active character label
        self.active_label = QLabel("Active Character: None")
        self.active_label.setStyleSheet("font-weight: bold; padding: 8px;")
        layout.addWidget(self.active_label)

    def _load_profiles(self) -> None:
        """Load all profiles from the character manager."""
        self.profile_list.clear()
        self._profiles_cache.clear()

        profile_names = self.character_manager.list_profiles()
        active = self.character_manager.get_active_profile()
        active_name = active.name if active else None

        upgrade_target = self.character_manager.get_upgrade_target()
        upgrade_target_name = upgrade_target.name if upgrade_target else None

        # Get filter
        filter_text = self.filter_combo.currentText()
        filter_category = None
        if filter_text not in ("All", "---"):
            filter_category = filter_text.lower().replace(" ", "_")

        for name in profile_names:
            profile = self.character_manager.get_profile(name)
            if not profile:
                continue

            # Cache profile
            self._profiles_cache[name] = self._build_profile_cache(profile)

            # Get categories
            categories = getattr(profile, 'categories', []) or []

            # Apply filter
            if filter_category and filter_category not in categories:
                continue

            # Build display text
            tags = []
            if active_name and name == active_name:
                tags.append("active")
            if upgrade_target_name and name == upgrade_target_name:
                tags.append("upgrade")

            # Category abbreviations
            abbrev_map = {
                "league_starter": "LS",
                "endgame": "EG",
                "boss_killer": "BK",
                "mapper": "MAP",
                "budget": "BUD",
                "meta": "META",
                "experimental": "EXP",
                "reference": "REF",
            }
            for cat in categories[:3]:
                tags.append(abbrev_map.get(cat, cat[:3].upper()))

            display = name
            if tags:
                display = f"{name} [{', '.join(tags)}]"

            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, name)  # Store actual name
            self.profile_list.addItem(item)

        # Update active label
        if active:
            self.active_label.setText(f"Active Character: {active.name}")
        else:
            self.active_label.setText("Active Character: None")

    def _build_profile_cache(self, profile: Any) -> Dict[str, Any]:
        """Build cache dict for a profile."""
        return {
            "name": profile.name,
            "build_info": {
                "class_name": profile.build.class_name if profile.build else "",
                "ascendancy": profile.build.ascendancy if profile.build else "",
                "level": profile.build.level if profile.build else 0,
            },
            "items": {
                slot: {
                    "name": item.name,
                    "base_type": item.base_type,
                    "rarity": item.rarity,
                    "implicit_mods": item.implicit_mods,
                    "explicit_mods": item.explicit_mods,
                }
                for slot, item in (profile.build.items.items() if profile.build else {})
            },
            "categories": getattr(profile, 'categories', []) or [],
            "is_upgrade_target": getattr(profile, 'is_upgrade_target', False),
        }

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._load_profiles()

    def _on_profile_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle profile selection."""
        if not current:
            return

        name = current.data(Qt.ItemDataRole.UserRole)
        self._selected_profile = name
        self._show_profile_details(name)

    def _show_profile_details(self, name: str) -> None:
        """Show details for selected profile."""
        profile = self._profiles_cache.get(name)
        if not profile:
            self._clear_details()
            return

        # Update info labels
        self.info_labels["Name"].setText(profile.get("name", "-"))

        build_info = profile.get("build_info", {})
        class_name = build_info.get("class_name", "-")
        ascendancy = build_info.get("ascendancy", "")
        if ascendancy:
            class_name = f"{class_name} ({ascendancy})"
        self.info_labels["Class"].setText(class_name)

        self.info_labels["Level"].setText(str(build_info.get("level", "-")))

        items = profile.get("items", {})
        self.info_labels["Items"].setText(f"{len(items)} equipped")

        # Categories
        categories = profile.get("categories", [])
        if categories:
            cat_display = ", ".join(cat.replace("_", " ").title() for cat in categories)
            self.info_labels["Categories"].setText(cat_display)
        else:
            self.info_labels["Categories"].setText("None")

        # Status
        status_parts = []
        if profile.get("is_upgrade_target"):
            status_parts.append("Upgrade Target")
        active = self.character_manager.get_active_profile()
        if active and name == active.name:
            status_parts.append("Active")
        self.info_labels["Status"].setText(", ".join(status_parts) if status_parts else "None")

        # Update equipment tree
        self.equipment_tree.clear()

        slot_order = [
            "Weapon 1", "Weapon 2", "Weapon 1 Swap", "Weapon 2 Swap",
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Amulet", "Ring 1", "Ring 2", "Belt",
            "Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5",
        ]

        sorted_slots = sorted(
            items.keys(),
            key=lambda s: slot_order.index(s) if s in slot_order else 999
        )

        for slot in sorted_slots:
            item_data = items[slot]
            tree_item = QTreeWidgetItem([
                slot,
                item_data.get("name", "-"),
                item_data.get("base_type", "-"),
                item_data.get("rarity", "-"),
            ])

            # Color by rarity
            rarity = item_data.get("rarity", "").lower()
            color = get_rarity_color(rarity)
            for col in range(4):
                tree_item.setForeground(col, QColor(color))

            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)
            self.equipment_tree.addTopLevelItem(tree_item)

    def _clear_details(self) -> None:
        """Clear the details panel."""
        for label in self.info_labels.values():
            label.setText("-")
        self.equipment_tree.clear()

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Show item details on double click."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        dialog = ItemDetailsDialog(
            self,
            item.text(0),
            item_data,
            on_price_check=self._request_price_check,
        )
        dialog.exec()

    def _request_price_check(self, item_text: str) -> None:
        """Request price check for an item."""
        self.price_check_requested.emit(item_text)
        if self.on_price_check:
            self.on_price_check(item_text)

    def _on_import(self) -> None:
        """Open import dialog."""
        dialog = ImportPoBDialog(self, self.character_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_profiles()

    def _on_delete(self) -> None:
        """Delete selected profile."""
        if not self._selected_profile:
            QMessageBox.information(self, "Delete Profile", "No profile selected.")
            return

        result = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to delete '{self._selected_profile}'?",
        )

        if result == QMessageBox.StandardButton.Yes:
            try:
                self.character_manager.delete_profile(self._selected_profile)
                self._selected_profile = None
                self._load_profiles()
                self._clear_details()
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Failed to delete profile:\n{e}")

    def _on_set_active(self) -> None:
        """Set selected profile as active."""
        if not self._selected_profile:
            QMessageBox.information(self, "Set Active", "No profile selected.")
            return

        try:
            self.character_manager.set_active_profile(self._selected_profile)
            self._load_profiles()

            if self.on_profile_selected:
                self.on_profile_selected(self._selected_profile)

            self.profile_selected.emit(self._selected_profile)

            QMessageBox.information(
                self,
                "Active Profile",
                f"'{self._selected_profile}' is now the active character.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set active profile:\n{e}")

    def _on_manage_categories(self) -> None:
        """Open categories dialog."""
        if not self._selected_profile:
            QMessageBox.information(self, "Manage Categories", "No profile selected.")
            return

        dialog = ManageCategoriesDialog(
            self,
            self.character_manager,
            self._selected_profile,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_profiles()


class ItemDetailsDialog(QDialog):
    """Dialog showing full item details."""

    def __init__(
        self,
        parent: Optional[QWidget],
        slot: str,
        item_data: Dict[str, Any],
        on_price_check: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)

        self.item_data = item_data
        self.on_price_check = on_price_check

        self.setWindowTitle(f"Item Details: {slot}")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Item header
        name = item_data.get("name", "Unknown")
        base = item_data.get("base_type", "")
        rarity = item_data.get("rarity", "")

        name_label = QLabel(name)
        name_font = QFont()
        name_font.setPointSize(12)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {get_rarity_color(rarity)};")
        layout.addWidget(name_label)

        if base and base != name:
            base_label = QLabel(base)
            layout.addWidget(base_label)

        rarity_label = QLabel(f"Rarity: {rarity}")
        rarity_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(rarity_label)

        # Separator
        layout.addSpacing(8)

        # Implicit mods
        implicit_mods = item_data.get("implicit_mods", [])
        if implicit_mods:
            impl_label = QLabel("Implicit Mods:")
            impl_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(impl_label)
            for mod in implicit_mods:
                mod_label = QLabel(f"  {mod}")
                mod_label.setStyleSheet(f"color: {COLORS['magic']};")
                layout.addWidget(mod_label)

        # Explicit mods
        explicit_mods = item_data.get("explicit_mods", [])
        if explicit_mods:
            if implicit_mods:
                layout.addSpacing(4)
            expl_label = QLabel("Explicit Mods:")
            expl_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(expl_label)
            for mod in explicit_mods:
                mod_label = QLabel(f"  {mod}")
                if "(crafted)" in mod.lower():
                    mod_label.setStyleSheet("color: #b4b4ff;")
                layout.addWidget(mod_label)

        # Buttons
        layout.addSpacing(8)
        btn_layout = QHBoxLayout()

        price_check_btn = QPushButton("Price Check")
        price_check_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: black;")
        price_check_btn.clicked.connect(self._on_price_check)
        btn_layout.addWidget(price_check_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _on_price_check(self) -> None:
        """Handle price check button click."""
        item_text = self._generate_item_text()
        if self.on_price_check:
            self.on_price_check(item_text)
        self.accept()

    def _generate_item_text(self) -> str:
        """Generate PoE-format item text from item data."""
        lines = []

        name = self.item_data.get("name", "Unknown")
        base = self.item_data.get("base_type", "")
        rarity = self.item_data.get("rarity", "RARE").upper()

        # Rarity line
        lines.append(f"Rarity: {rarity.title()}")

        # Name and base
        if rarity == "UNIQUE":
            lines.append(name)
            if base and base != name:
                lines.append(base)
        elif rarity == "RARE":
            lines.append(name)
            if base:
                lines.append(base)
        else:
            if base:
                lines.append(base)
            else:
                lines.append(name)

        # Separator
        lines.append("--------")

        # Implicit mods
        implicit_mods = self.item_data.get("implicit_mods", [])
        if implicit_mods:
            for mod in implicit_mods:
                lines.append(mod)
            lines.append("--------")

        # Explicit mods
        explicit_mods = self.item_data.get("explicit_mods", [])
        for mod in explicit_mods:
            lines.append(mod)

        return "\n".join(lines)


class ManageCategoriesDialog(QDialog):
    """Dialog for managing profile categories."""

    def __init__(
        self,
        parent: Optional[QWidget],
        character_manager: Any,
        profile_name: str,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self.profile_name = profile_name

        self.setWindowTitle(f"Categories: {profile_name}")
        self.setMinimumWidth(300)

        # Get current categories
        profile = character_manager.get_profile(profile_name)
        current_categories = set(getattr(profile, 'categories', []) or [])

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Select categories for this build:"))

        # Category checkboxes
        self.category_checks: Dict[str, QCheckBox] = {}
        for cat in BUILD_CATEGORIES:
            checkbox = QCheckBox(cat.value.replace("_", " ").title())
            checkbox.setChecked(cat.value in current_categories)
            self.category_checks[cat.value] = checkbox
            layout.addWidget(checkbox)

        # Buttons
        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        """Save categories."""
        selected = [
            cat_value
            for cat_value, checkbox in self.category_checks.items()
            if checkbox.isChecked()
        ]

        try:
            self.character_manager.set_build_categories(self.profile_name, selected)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save categories:\n{e}")


class ImportPoBDialog(QDialog):
    """Dialog for importing PoB builds."""

    def __init__(
        self,
        parent: Optional[QWidget],
        character_manager: Any,
    ):
        super().__init__(parent)

        self.character_manager = character_manager

        self.setWindowTitle("Import PoB Character")
        self.setMinimumSize(450, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Character name
        layout.addWidget(QLabel("Character Name:"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        # PoB code/URL
        layout.addWidget(QLabel("Pastebin URL or PoB Code:"))
        self.code_input = QPlainTextEdit()
        self.code_input.setMaximumHeight(100)
        layout.addWidget(self.code_input)

        help_label = QLabel(
            "Enter a Pastebin URL (e.g., https://pastebin.com/abc123)\n"
            "or paste the raw PoB build code directly."
        )
        help_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(help_label)

        # Notes
        layout.addWidget(QLabel("Notes (optional):"))
        self.notes_input = QLineEdit()
        layout.addWidget(self.notes_input)

        # Categories
        layout.addWidget(QLabel("Categories (optional):"))

        cat_row = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()

        self.category_checks: Dict[str, QCheckBox] = {}
        categories = list(BUILD_CATEGORIES)
        mid = (len(categories) + 1) // 2

        for i, cat in enumerate(categories):
            checkbox = QCheckBox(cat.value.replace("_", " ").title())
            self.category_checks[cat.value] = checkbox
            if i < mid:
                left_col.addWidget(checkbox)
            else:
                right_col.addWidget(checkbox)

        cat_row.addLayout(left_col)
        cat_row.addLayout(right_col)
        layout.addLayout(cat_row)

        # Buttons
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self.import_btn)

        layout.addLayout(btn_row)

        # Focus name input
        self.name_input.setFocus()

    def _on_import(self) -> None:
        """Attempt to import the build."""
        name = self.name_input.text().strip()
        code = self.code_input.toPlainText().strip()
        notes = self.notes_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Import Error", "Please enter a character name.")
            self.name_input.setFocus()
            return

        if not code:
            QMessageBox.warning(self, "Import Error", "Please enter a PoB code or Pastebin URL.")
            self.code_input.setFocus()
            return

        # Get selected categories
        selected_categories = [
            cat_value
            for cat_value, checkbox in self.category_checks.items()
            if checkbox.isChecked()
        ]

        # Check for duplicate
        existing = self.character_manager.list_profiles()
        if name in existing:
            result = QMessageBox.question(
                self,
                "Duplicate Name",
                f"A profile named '{name}' already exists.\n\nOverwrite it?",
            )
            if result != QMessageBox.StandardButton.Yes:
                return
            self.character_manager.delete_profile(name)

        # Import
        self.import_btn.setEnabled(False)

        try:
            profile = self.character_manager.add_from_pob_code(
                name=name,
                pob_code=code,
                notes=notes or None,
            )

            if profile:
                build = profile.build
                item_count = len(build.items) if build else 0

                # Apply categories
                if selected_categories:
                    self.character_manager.set_build_categories(name, selected_categories)

                cat_info = ""
                if selected_categories:
                    cat_display = ", ".join(
                        cat.replace("_", " ").title() for cat in selected_categories
                    )
                    cat_info = f"\nCategories: {cat_display}"

                QMessageBox.information(
                    self,
                    "Import Success",
                    f"Successfully imported '{name}'!\n\n"
                    f"Class: {build.class_name if build else 'Unknown'} "
                    f"({build.ascendancy if build else ''})\n"
                    f"Level: {build.level if build else '?'}\n"
                    f"Items: {item_count} equipped{cat_info}",
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    "Failed to import the character.\n\n"
                    "Please check that the PoB code or URL is valid.",
                )
                self.import_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"An error occurred while importing:\n\n{e}",
            )
            self.import_btn.setEnabled(True)
