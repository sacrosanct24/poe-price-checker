"""
Build Manager Window.

Unified window for managing build profiles that combines:
- Build Library: Profile browsing, filtering, metadata editing
- PoB Characters: Equipment viewing, price check integration

This replaces the separate BuildLibraryDialog and PoBCharacterWindow
with a unified experience.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QTabWidget,
    QWidget,
    QMessageBox,
    QHeaderView,
    QFileDialog,
)
from PyQt6.QtCore import QUrl

from gui_qt.styles import COLORS, get_rarity_color, apply_window_icon

logger = logging.getLogger(__name__)

# Try to import BuildCategory
try:
    from core.pob import BuildCategory
    BUILD_CATEGORIES = list(BuildCategory)
except ImportError:
    BUILD_CATEGORIES = []


class BuildManagerWindow(QDialog):
    """
    Unified window for managing build profiles.

    Combines Build Library and PoB Characters into a single interface
    with profile list, details tab, and equipment tab.
    """

    # Signals
    profile_selected = pyqtSignal(str)  # Emits profile name
    active_profile_changed = pyqtSignal(str)  # Emits profile name
    price_check_requested = pyqtSignal(str)  # Emits item text for price checking

    def __init__(
        self,
        character_manager: Any,
        parent: Optional[QWidget] = None,
        on_price_check: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self.on_price_check = on_price_check

        self._selected_profile: Optional[str] = None
        self._profiles_cache: Dict[str, Dict[str, Any]] = {}
        self._unsaved_changes = False

        self.setWindowTitle("Build Manager")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 800)
        apply_window_icon(self)

        self._create_widgets()
        self._load_profiles()

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === Left Panel: Profile List ===
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # === Right Panel: Details/Equipment Tabs ===
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([350, 750])
        layout.addWidget(splitter)

        # Bottom: Active character label and close button
        bottom_row = QHBoxLayout()
        self.active_label = QLabel("Active Build: None")
        self.active_label.setStyleSheet(f"font-weight: bold; padding: 8px; color: {COLORS['accent']};")
        bottom_row.addWidget(self.active_label)

        bottom_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self._on_close)
        bottom_row.addWidget(close_btn)

        layout.addLayout(bottom_row)

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with profile list and filters."""
        panel = QGroupBox("Build Profiles")
        layout = QVBoxLayout(panel)

        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search name, class, skill...")
        self.search_input.textChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Category filter
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "")
        for cat in BUILD_CATEGORIES:
            self.category_combo.addItem(cat.value.replace("_", " ").title(), cat.value)
        self.category_combo.currentIndexChanged.connect(self._on_filter_changed)
        cat_layout.addWidget(self.category_combo)
        layout.addLayout(cat_layout)

        # Quick filters
        filter_row = QHBoxLayout()
        self.favorites_check = QCheckBox("Favorites")
        self.favorites_check.stateChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.favorites_check)

        self.ssf_check = QCheckBox("SSF")
        self.ssf_check.stateChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.ssf_check)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        self.profile_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
            }}
            QListWidget::item {{
                padding: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['accent_blue']};
            }}
        """)
        layout.addWidget(self.profile_list)

        # Button row 1
        btn_row1 = QHBoxLayout()
        self.import_btn = QPushButton("Import...")
        self.import_btn.clicked.connect(self._on_import)
        btn_row1.addWidget(self.import_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setStyleSheet(f"color: {COLORS['error']};")
        btn_row1.addWidget(self.delete_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_profiles)
        btn_row1.addWidget(self.refresh_btn)
        layout.addLayout(btn_row1)

        # Button row 2
        btn_row2 = QHBoxLayout()
        self.set_active_btn = QPushButton("Set Active")
        self.set_active_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: black;
                font-weight: bold;
            }}
        """)
        self.set_active_btn.clicked.connect(self._on_set_active)
        btn_row2.addWidget(self.set_active_btn)

        btn_row2.addStretch()
        layout.addLayout(btn_row2)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with tabbed details/equipment."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['accent']};
                color: black;
            }}
        """)

        # Details Tab
        self.details_tab = self._create_details_tab()
        self.tab_widget.addTab(self.details_tab, "Details")

        # Equipment Tab
        self.equipment_tab = self._create_equipment_tab()
        self.tab_widget.addTab(self.equipment_tab, "Equipment")

        layout.addWidget(self.tab_widget)

        return panel

    def _create_details_tab(self) -> QWidget:
        """Create the Details tab with build info and metadata."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        # Build Info (read-only)
        info_group = QGroupBox("Build Info")
        info_layout = QVBoxLayout(info_group)

        # Name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.name_label = QLabel("-")
        self.name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['rare']};")
        name_row.addWidget(self.name_label)
        name_row.addStretch()
        info_layout.addLayout(name_row)

        # Class
        class_row = QHBoxLayout()
        class_row.addWidget(QLabel("Class:"))
        self.class_label = QLabel("-")
        class_row.addWidget(self.class_label)
        class_row.addStretch()
        info_layout.addLayout(class_row)

        # Main Skill
        skill_row = QHBoxLayout()
        skill_row.addWidget(QLabel("Main Skill:"))
        self.skill_label = QLabel("-")
        self.skill_label.setStyleSheet(f"color: {COLORS['magic']};")
        skill_row.addWidget(self.skill_label)
        skill_row.addStretch()
        info_layout.addLayout(skill_row)

        # Level
        level_row = QHBoxLayout()
        level_row.addWidget(QLabel("Level:"))
        self.level_label = QLabel("-")
        level_row.addWidget(self.level_label)
        level_row.addStretch()
        info_layout.addLayout(level_row)

        layout.addWidget(info_group)

        # Metadata (editable)
        meta_group = QGroupBox("Metadata")
        meta_layout = QVBoxLayout(meta_group)

        # Guide URL
        guide_row = QHBoxLayout()
        guide_row.addWidget(QLabel("Guide URL:"))
        self.guide_input = QLineEdit()
        self.guide_input.setPlaceholderText("https://maxroll.gg/poe/...")
        self.guide_input.textChanged.connect(self._on_metadata_changed)
        guide_row.addWidget(self.guide_input)
        self.open_guide_btn = QPushButton("Open")
        self.open_guide_btn.clicked.connect(self._open_guide_url)
        guide_row.addWidget(self.open_guide_btn)
        meta_layout.addLayout(guide_row)

        # Tags
        tags_row = QHBoxLayout()
        tags_row.addWidget(QLabel("Tags:"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g., fast-clear, tanky, cheap")
        self.tags_input.textChanged.connect(self._on_metadata_changed)
        tags_row.addWidget(self.tags_input)
        meta_layout.addLayout(tags_row)

        # Checkboxes
        check_row = QHBoxLayout()
        self.ssf_friendly_check = QCheckBox("SSF Friendly")
        self.ssf_friendly_check.stateChanged.connect(self._on_metadata_changed)
        check_row.addWidget(self.ssf_friendly_check)

        self.favorite_check = QCheckBox("Favorite")
        self.favorite_check.stateChanged.connect(self._on_metadata_changed)
        check_row.addWidget(self.favorite_check)

        check_row.addStretch()
        meta_layout.addLayout(check_row)

        # Notes
        meta_layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.textChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self.notes_edit)

        layout.addWidget(meta_group)

        # Categories
        cat_group = QGroupBox("Categories")
        cat_layout = QVBoxLayout(cat_group)

        self.category_checks: Dict[str, QCheckBox] = {}
        cat_grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()

        for i, cat in enumerate(BUILD_CATEGORIES):
            check = QCheckBox(cat.value.replace("_", " ").title())
            check.stateChanged.connect(self._on_metadata_changed)
            self.category_checks[cat.value] = check
            if i < len(BUILD_CATEGORIES) // 2:
                col1.addWidget(check)
            else:
                col2.addWidget(check)

        cat_grid.addLayout(col1)
        cat_grid.addLayout(col2)
        cat_layout.addLayout(cat_grid)

        layout.addWidget(cat_group)

        # Save button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: black;
                font-weight: bold;
                padding: 8px 24px;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_secondary']};
            }}
        """)
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        save_row.addWidget(self.save_btn)
        layout.addLayout(save_row)

        layout.addStretch()

        return tab

    def _create_equipment_tab(self) -> QWidget:
        """Create the Equipment tab with item tree."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Equipment tree
        self.equipment_tree = QTreeWidget()
        self.equipment_tree.setHeaderLabels(["Slot", "Item Name", "Base Type", "Rarity"])
        self.equipment_tree.setRootIsDecorated(False)
        self.equipment_tree.setAlternatingRowColors(True)
        self.equipment_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.equipment_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
            }}
            QTreeWidget::item {{
                padding: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {COLORS['accent_blue']};
            }}
        """)

        header = self.equipment_tree.header()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.equipment_tree)

        # Help text
        help_label = QLabel("Double-click an item to price check it")
        help_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        layout.addWidget(help_label)

        return tab

    def _load_profiles(self) -> None:
        """Load all profiles from character manager."""
        self.profile_list.clear()
        self._profiles_cache.clear()

        if not self.character_manager:
            return

        profile_names = self.character_manager.list_profiles()
        active = self.character_manager.get_active_profile()
        active_name = active.name if active else None

        # Get filter values
        search_text = self.search_input.text().lower()
        filter_category = self.category_combo.currentData()
        filter_favorites = self.favorites_check.isChecked()
        filter_ssf = self.ssf_check.isChecked()

        for name in profile_names:
            profile = self.character_manager.get_profile(name)
            if not profile:
                continue

            # Cache profile data
            cache = self._build_profile_cache(profile)
            self._profiles_cache[name] = cache

            # Apply filters
            if search_text:
                searchable = f"{name} {cache.get('class', '')} {cache.get('skill', '')}".lower()
                if search_text not in searchable:
                    continue

            if filter_category:
                categories = cache.get('categories', [])
                if filter_category not in categories:
                    continue

            if filter_favorites and not cache.get('favorite', False):
                continue

            if filter_ssf and not cache.get('ssf_friendly', False):
                continue

            # Build display text
            tags = []
            if active_name and name == active_name:
                tags.append("ACTIVE")
            if cache.get('favorite'):
                tags.append("★")

            display = name
            if tags:
                display = f"{name} [{' '.join(tags)}]"

            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, name)
            if active_name and name == active_name:
                item.setForeground(QColor(COLORS['accent']))
            self.profile_list.addItem(item)

        # Update active label
        if active:
            self.active_label.setText(f"Active Build: {active.name}")
        else:
            self.active_label.setText("Active Build: None")

    def _build_profile_cache(self, profile: Any) -> Dict[str, Any]:
        """Build cache dict for a profile."""
        build = profile.build if profile.build else None

        return {
            "name": profile.name,
            "class": f"{build.class_name} / {build.ascendancy}" if build else "-",
            "skill": build.main_skill if build and hasattr(build, 'main_skill') else "-",
            "level": build.level if build else 0,
            "categories": getattr(profile, 'categories', []) or [],
            "favorite": getattr(profile, 'is_favorite', False),
            "ssf_friendly": getattr(profile, 'ssf_friendly', False),
            "guide_url": getattr(profile, 'guide_url', ''),
            "tags": getattr(profile, 'tags', []) or [],
            "notes": getattr(profile, 'notes', ''),
            "items": {
                slot: {
                    "name": item.name,
                    "base_type": item.base_type,
                    "rarity": item.rarity,
                    "implicit_mods": getattr(item, 'implicit_mods', []),
                    "explicit_mods": getattr(item, 'explicit_mods', []),
                }
                for slot, item in (build.items.items() if build and hasattr(build, 'items') else {})
            },
        }

    def _on_profile_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """Handle profile selection change."""
        if self._unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Discard them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                # Restore previous selection
                if previous:
                    self.profile_list.blockSignals(True)
                    self.profile_list.setCurrentItem(previous)
                    self.profile_list.blockSignals(False)
                return

        if not current:
            self._clear_details()
            return

        profile_name = current.data(Qt.ItemDataRole.UserRole)
        self._selected_profile = profile_name
        self._load_profile_details(profile_name)
        self._unsaved_changes = False
        self.save_btn.setEnabled(False)

        self.profile_selected.emit(profile_name)

    def _load_profile_details(self, profile_name: str) -> None:
        """Load and display profile details."""
        cache = self._profiles_cache.get(profile_name, {})

        # Update Details tab
        self.name_label.setText(profile_name)
        self.class_label.setText(cache.get('class', '-'))
        self.skill_label.setText(cache.get('skill', '-'))
        self.level_label.setText(str(cache.get('level', '-')))

        # Block signals while loading
        self._block_metadata_signals(True)

        self.guide_input.setText(cache.get('guide_url', ''))
        self.tags_input.setText(', '.join(cache.get('tags', [])))
        self.ssf_friendly_check.setChecked(cache.get('ssf_friendly', False))
        self.favorite_check.setChecked(cache.get('favorite', False))
        self.notes_edit.setPlainText(cache.get('notes', ''))

        # Categories
        categories = cache.get('categories', [])
        for cat_value, check in self.category_checks.items():
            check.setChecked(cat_value in categories)

        self._block_metadata_signals(False)

        # Update Equipment tab
        self.equipment_tree.clear()
        items = cache.get('items', {})
        for slot, item_data in items.items():
            tree_item = QTreeWidgetItem([
                slot,
                item_data.get('name', '-'),
                item_data.get('base_type', '-'),
                item_data.get('rarity', '-'),
            ])

            # Color by rarity
            rarity = item_data.get('rarity', '').lower()
            color = get_rarity_color(rarity)
            tree_item.setForeground(1, QColor(color))

            # Store item data for price check
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)

            self.equipment_tree.addTopLevelItem(tree_item)

    def _clear_details(self) -> None:
        """Clear all detail fields."""
        self._selected_profile = None

        self.name_label.setText("-")
        self.class_label.setText("-")
        self.skill_label.setText("-")
        self.level_label.setText("-")

        self._block_metadata_signals(True)
        self.guide_input.clear()
        self.tags_input.clear()
        self.ssf_friendly_check.setChecked(False)
        self.favorite_check.setChecked(False)
        self.notes_edit.clear()
        for check in self.category_checks.values():
            check.setChecked(False)
        self._block_metadata_signals(False)

        self.equipment_tree.clear()
        self._unsaved_changes = False
        self.save_btn.setEnabled(False)

    def _block_metadata_signals(self, block: bool) -> None:
        """Block/unblock metadata change signals."""
        self.guide_input.blockSignals(block)
        self.tags_input.blockSignals(block)
        self.ssf_friendly_check.blockSignals(block)
        self.favorite_check.blockSignals(block)
        self.notes_edit.blockSignals(block)
        for check in self.category_checks.values():
            check.blockSignals(block)

    def _on_metadata_changed(self) -> None:
        """Handle metadata field changes."""
        self._unsaved_changes = True
        self.save_btn.setEnabled(True)

    def _on_filter_changed(self) -> None:
        """Handle filter changes."""
        self._load_profiles()

    def _save_changes(self) -> None:
        """Save metadata changes to profile."""
        if not self._selected_profile or not self.character_manager:
            return

        profile = self.character_manager.get_profile(self._selected_profile)
        if not profile:
            return

        try:
            # Update profile metadata
            profile.guide_url = self.guide_input.text()
            profile.tags = [t.strip() for t in self.tags_input.text().split(',') if t.strip()]
            profile.ssf_friendly = self.ssf_friendly_check.isChecked()
            profile.is_favorite = self.favorite_check.isChecked()
            profile.notes = self.notes_edit.toPlainText()

            # Categories
            categories = []
            for cat_value, check in self.category_checks.items():
                if check.isChecked():
                    categories.append(cat_value)
            profile.categories = categories

            # Save
            self.character_manager.save_profile(profile)

            self._unsaved_changes = False
            self.save_btn.setEnabled(False)

            # Refresh cache and list
            self._profiles_cache[self._selected_profile] = self._build_profile_cache(profile)
            self._load_profiles()

            # Re-select the profile
            for i in range(self.profile_list.count()):
                item = self.profile_list.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == self._selected_profile:
                    self.profile_list.setCurrentItem(item)
                    break

            logger.info(f"Saved changes for profile: {self._selected_profile}")

        except Exception as e:
            logger.exception("Failed to save profile")
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _on_set_active(self) -> None:
        """Set selected profile as active."""
        if not self._selected_profile or not self.character_manager:
            return

        try:
            self.character_manager.set_active_profile(self._selected_profile)
            self._load_profiles()
            self.active_profile_changed.emit(self._selected_profile)
            logger.info(f"Set active profile: {self._selected_profile}")
        except Exception as e:
            logger.exception("Failed to set active profile")
            QMessageBox.critical(self, "Error", f"Failed to set active: {e}")

    def _on_import(self) -> None:
        """Import a build from file or pastebin."""
        # For now, show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Build",
            "", "PoB Files (*.xml *.txt);;All Files (*)"
        )
        if not file_path:
            return

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to import
            profile_name = self.character_manager.import_build(content)
            if profile_name:
                self._load_profiles()
                QMessageBox.information(self, "Success", f"Imported: {profile_name}")
            else:
                QMessageBox.warning(self, "Import Failed", "Could not parse build data")

        except Exception as e:
            logger.exception("Failed to import build")
            QMessageBox.critical(self, "Error", f"Import failed: {e}")

    def _on_delete(self) -> None:
        """Delete selected profile."""
        if not self._selected_profile or not self.character_manager:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete profile '{self._selected_profile}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.character_manager.delete_profile(self._selected_profile)
                self._selected_profile = None
                self._clear_details()
                self._load_profiles()
                logger.info(f"Deleted profile: {self._selected_profile}")
            except Exception as e:
                logger.exception("Failed to delete profile")
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item double-click for price check."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        # Build item text for price check
        item_text = self._build_item_text(item_data)

        if self.on_price_check:
            self.on_price_check(item_text)

        self.price_check_requested.emit(item_text)

    def _build_item_text(self, item_data: Dict) -> str:
        """Build item text for price checking."""
        lines = []

        rarity = item_data.get('rarity', 'Normal')
        lines.append(f"Rarity: {rarity}")

        name = item_data.get('name', '')
        if name:
            lines.append(name)

        base_type = item_data.get('base_type', '')
        if base_type:
            lines.append(base_type)

        lines.append("--------")

        # Implicit mods
        for mod in item_data.get('implicit_mods', []):
            lines.append(mod)

        if item_data.get('implicit_mods'):
            lines.append("--------")

        # Explicit mods
        for mod in item_data.get('explicit_mods', []):
            lines.append(mod)

        return '\n'.join(lines)

    def _open_guide_url(self) -> None:
        """Open guide URL in browser."""
        url = self.guide_input.text()
        if url:
            if not url.startswith('http'):
                url = 'https://' + url
            QDesktopServices.openUrl(QUrl(url))

    def _on_close(self) -> None:
        """Handle close button."""
        if self._unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Discard them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.accept()

    def set_profile(self, profile_name: str) -> None:
        """Select a profile programmatically."""
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == profile_name:
                self.profile_list.setCurrentItem(item)
                break
