"""
Build Library Dialog.

Dialog for managing saved character build profiles.
Provides browsing, filtering, editing, and import/export functionality.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QWidget,
    QGroupBox,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QCheckBox,
    QMessageBox,
    QFileDialog,
    QMenu,
    QAbstractItemView,
)
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtCore import QUrl

from gui_qt.styles import COLORS, apply_window_icon
from core.pob import CharacterManager, BuildCategory

logger = logging.getLogger(__name__)


class BuildLibraryDialog(QDialog):
    """Dialog for managing build profiles."""

    # Emitted when a profile is selected for viewing/editing
    profile_selected = pyqtSignal(str)  # profile_name

    # Emitted when active profile changes
    active_profile_changed = pyqtSignal(str)  # profile_name

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        character_manager: Optional[CharacterManager] = None,
    ):
        super().__init__(parent)
        self.character_manager = character_manager or CharacterManager()
        self._selected_profile: Optional[str] = None

        self.setWindowTitle("Build Library")
        self.setMinimumSize(1000, 700)
        apply_window_icon(self)

        self._setup_ui()
        self._refresh_build_list()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Create splitter for list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - build list with filters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Search and filters
        filter_group = QGroupBox("Filters")
        filter_layout = QVBoxLayout(filter_group)

        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search name, skill, ascendancy...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)
        filter_layout.addLayout(search_layout)

        # Category filter
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "")
        for cat in BuildCategory:
            self.category_combo.addItem(cat.name.replace("_", " ").title(), cat.value)
        self.category_combo.currentIndexChanged.connect(self._on_filter_changed)
        cat_layout.addWidget(self.category_combo)
        filter_layout.addLayout(cat_layout)

        # Tag filter
        tag_layout = QHBoxLayout()
        tag_layout.addWidget(QLabel("Tag:"))
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("All Tags", "")
        self.tag_combo.currentIndexChanged.connect(self._on_filter_changed)
        tag_layout.addWidget(self.tag_combo)
        filter_layout.addLayout(tag_layout)

        # Checkboxes
        checkbox_layout = QHBoxLayout()
        self.favorites_check = QCheckBox("Favorites")
        self.favorites_check.stateChanged.connect(self._on_filter_changed)
        checkbox_layout.addWidget(self.favorites_check)

        self.ssf_check = QCheckBox("SSF Only")
        self.ssf_check.stateChanged.connect(self._on_filter_changed)
        checkbox_layout.addWidget(self.ssf_check)

        checkbox_layout.addStretch()
        filter_layout.addLayout(checkbox_layout)

        left_layout.addWidget(filter_group)

        # Build list table
        self.build_table = QTableWidget()
        self.build_table.setColumnCount(6)
        self.build_table.setHorizontalHeaderLabels([
            "", "Name", "Class", "Main Skill", "Category", "Tags"
        ])
        self.build_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.build_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.build_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.build_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.build_table.customContextMenuRequested.connect(self._show_context_menu)

        header = self.build_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Favorite star
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Class
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Skill
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Category
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Tags
        self.build_table.setColumnWidth(0, 30)

        self.build_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.build_table.itemDoubleClicked.connect(self._on_double_click)

        left_layout.addWidget(self.build_table)

        # Button row
        button_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._import_build)
        button_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export_build)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        button_layout.addStretch()

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_build)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet(f"color: {COLORS['error']};")
        button_layout.addWidget(self.delete_btn)

        left_layout.addLayout(button_layout)

        splitter.addWidget(left_widget)

        # Right side - details panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Build info group
        info_group = QGroupBox("Build Details")
        info_layout = QVBoxLayout(info_group)

        # Build name (read-only)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_label = QLabel("-")
        self.name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text']};")
        name_layout.addWidget(self.name_label)
        name_layout.addStretch()
        info_layout.addLayout(name_layout)

        # Class/Ascendancy
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("Class:"))
        self.class_label = QLabel("-")
        class_layout.addWidget(self.class_label)
        class_layout.addStretch()
        info_layout.addLayout(class_layout)

        # Main skill
        skill_layout = QHBoxLayout()
        skill_layout.addWidget(QLabel("Main Skill:"))
        self.skill_label = QLabel("-")
        skill_layout.addWidget(self.skill_label)
        skill_layout.addStretch()
        info_layout.addLayout(skill_layout)

        # Level
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Level:"))
        self.level_label = QLabel("-")
        level_layout.addWidget(self.level_label)
        level_layout.addStretch()
        info_layout.addLayout(level_layout)

        right_layout.addWidget(info_group)

        # Metadata group
        meta_group = QGroupBox("Metadata")
        meta_layout = QVBoxLayout(meta_group)

        # Guide URL
        guide_layout = QHBoxLayout()
        guide_layout.addWidget(QLabel("Guide URL:"))
        self.guide_input = QLineEdit()
        self.guide_input.setPlaceholderText("https://maxroll.gg/poe/...")
        self.guide_input.textChanged.connect(self._on_metadata_changed)
        guide_layout.addWidget(self.guide_input)
        self.open_guide_btn = QPushButton("Open")
        self.open_guide_btn.clicked.connect(self._open_guide_url)
        self.open_guide_btn.setEnabled(False)
        guide_layout.addWidget(self.open_guide_btn)
        meta_layout.addLayout(guide_layout)

        # Tags
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("Tags:"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g., fast-clear, tanky, cheap")
        self.tags_input.textChanged.connect(self._on_metadata_changed)
        tags_layout.addWidget(self.tags_input)
        meta_layout.addLayout(tags_layout)

        # Checkboxes
        check_layout = QHBoxLayout()
        self.ssf_friendly_check = QCheckBox("SSF Friendly")
        self.ssf_friendly_check.stateChanged.connect(self._on_metadata_changed)
        check_layout.addWidget(self.ssf_friendly_check)

        self.favorite_check = QCheckBox("Favorite")
        self.favorite_check.stateChanged.connect(self._on_metadata_changed)
        check_layout.addWidget(self.favorite_check)

        check_layout.addStretch()
        meta_layout.addLayout(check_layout)

        # Notes
        meta_layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.textChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self.notes_edit)

        right_layout.addWidget(meta_group)

        # Categories group
        cat_group = QGroupBox("Categories")
        cat_group_layout = QVBoxLayout(cat_group)

        self.category_checks = {}
        cat_grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()

        categories = list(BuildCategory)
        for i, cat in enumerate(categories):
            check = QCheckBox(cat.name.replace("_", " ").title())
            check.stateChanged.connect(self._on_category_changed)
            self.category_checks[cat.value] = check
            if i < len(categories) // 2:
                col1.addWidget(check)
            else:
                col2.addWidget(check)

        cat_grid.addLayout(col1)
        cat_grid.addLayout(col2)
        cat_group_layout.addLayout(cat_grid)

        right_layout.addWidget(cat_group)

        # Action buttons
        action_layout = QHBoxLayout()

        self.set_active_btn = QPushButton("Set as Active")
        self.set_active_btn.clicked.connect(self._set_as_active)
        self.set_active_btn.setEnabled(False)
        action_layout.addWidget(self.set_active_btn)

        self.set_target_btn = QPushButton("Set as Upgrade Target")
        self.set_target_btn.clicked.connect(self._set_as_upgrade_target)
        self.set_target_btn.setEnabled(False)
        action_layout.addWidget(self.set_target_btn)

        action_layout.addStretch()

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(f"background-color: {COLORS['accent']};")
        action_layout.addWidget(self.save_btn)

        right_layout.addLayout(action_layout)
        right_layout.addStretch()

        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

        self._metadata_dirty = False

    def _refresh_build_list(self) -> None:
        """Refresh the build list with current filters."""
        # Get filter values
        query = self.search_input.text()
        category = self.category_combo.currentData()
        tag = self.tag_combo.currentData()
        favorites_only = self.favorites_check.isChecked()
        ssf_only = self.ssf_check.isChecked()

        # Apply filters
        categories = [category] if category else None
        tags = [tag] if tag else None

        profiles = self.character_manager.search_builds(
            query=query,
            categories=categories,
            tags=tags,
            ssf_only=ssf_only,
            favorites_only=favorites_only,
        )

        # Update table
        self.build_table.setRowCount(len(profiles))

        for row, profile in enumerate(profiles):
            # Store profile name in first column
            fav_item = QTableWidgetItem("★" if profile.favorite else "")
            fav_item.setData(Qt.ItemDataRole.UserRole, profile.name)
            fav_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if profile.favorite:
                fav_item.setForeground(Qt.GlobalColor.yellow)
            self.build_table.setItem(row, 0, fav_item)

            # Name with SSF indicator
            name_text = profile.name
            if profile.ssf_friendly:
                name_text += " [SSF]"
            name_item = QTableWidgetItem(name_text)
            if profile.is_upgrade_target:
                name_item.setForeground(Qt.GlobalColor.green)
            self.build_table.setItem(row, 1, name_item)

            # Class/Ascendancy
            class_text = profile.build.ascendancy or profile.build.class_name
            self.build_table.setItem(row, 2, QTableWidgetItem(class_text))

            # Main skill
            self.build_table.setItem(row, 3, QTableWidgetItem(profile.build.main_skill))

            # Primary category
            cat_text = profile.categories[0] if profile.categories else ""
            cat_text = cat_text.replace("_", " ").title()
            self.build_table.setItem(row, 4, QTableWidgetItem(cat_text))

            # Tags
            tags_text = ", ".join(profile.tags) if profile.tags else ""
            self.build_table.setItem(row, 5, QTableWidgetItem(tags_text))

        # Refresh tag filter options
        self._refresh_tag_filter()

    def _refresh_tag_filter(self) -> None:
        """Refresh available tags in filter dropdown."""
        current_tag = self.tag_combo.currentData()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("All Tags", "")
        for tag in self.character_manager.get_all_tags():
            self.tag_combo.addItem(tag, tag)

        # Restore selection
        if current_tag:
            idx = self.tag_combo.findData(current_tag)
            if idx >= 0:
                self.tag_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)

    def _on_search_changed(self, text: str) -> None:
        """Handle search text change."""
        self._refresh_build_list()

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._refresh_build_list()

    def _on_selection_changed(self) -> None:
        """Handle build selection change."""
        selected = self.build_table.selectedItems()
        if not selected:
            self._clear_details()
            self._selected_profile = None
            return

        # Get profile name from first column
        row = selected[0].row()
        first_item = self.build_table.item(row, 0)
        if not first_item:
            return
        profile_name = first_item.data(Qt.ItemDataRole.UserRole)
        self._selected_profile = profile_name
        self._load_profile_details(profile_name)

        # Enable buttons
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.set_active_btn.setEnabled(True)
        self.set_target_btn.setEnabled(True)

    def _on_double_click(self, item: QTableWidgetItem) -> None:
        """Handle double-click on build."""
        row = item.row()
        first_item = self.build_table.item(row, 0)
        if not first_item:
            return
        profile_name = first_item.data(Qt.ItemDataRole.UserRole)
        self.profile_selected.emit(profile_name)

    def _load_profile_details(self, name: str) -> None:
        """Load profile details into the details panel."""
        profile = self.character_manager.get_profile(name)
        if not profile:
            return

        # Block signals while loading
        self._block_detail_signals(True)

        # Build info
        self.name_label.setText(profile.name)
        self.class_label.setText(
            f"{profile.build.ascendancy or profile.build.class_name}"
        )
        self.skill_label.setText(profile.build.main_skill or "-")
        self.level_label.setText(str(profile.build.level))

        # Metadata
        self.guide_input.setText(profile.guide_url)
        self.tags_input.setText(", ".join(profile.tags))
        self.ssf_friendly_check.setChecked(profile.ssf_friendly)
        self.favorite_check.setChecked(profile.favorite)
        self.notes_edit.setPlainText(profile.notes)

        # Open guide button
        self.open_guide_btn.setEnabled(bool(profile.guide_url))

        # Categories
        for cat_value, check in self.category_checks.items():
            check.setChecked(cat_value in profile.categories)

        self._block_detail_signals(False)
        self._metadata_dirty = False
        self.save_btn.setEnabled(False)

    def _block_detail_signals(self, block: bool) -> None:
        """Block or unblock signals from detail widgets."""
        self.guide_input.blockSignals(block)
        self.tags_input.blockSignals(block)
        self.ssf_friendly_check.blockSignals(block)
        self.favorite_check.blockSignals(block)
        self.notes_edit.blockSignals(block)
        for check in self.category_checks.values():
            check.blockSignals(block)

    def _clear_details(self) -> None:
        """Clear the details panel."""
        self._block_detail_signals(True)

        self.name_label.setText("-")
        self.class_label.setText("-")
        self.skill_label.setText("-")
        self.level_label.setText("-")
        self.guide_input.clear()
        self.tags_input.clear()
        self.ssf_friendly_check.setChecked(False)
        self.favorite_check.setChecked(False)
        self.notes_edit.clear()
        self.open_guide_btn.setEnabled(False)

        for check in self.category_checks.values():
            check.setChecked(False)

        self._block_detail_signals(False)

        self.export_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.set_active_btn.setEnabled(False)
        self.set_target_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self._metadata_dirty = False

    def _on_metadata_changed(self) -> None:
        """Handle metadata change."""
        self._metadata_dirty = True
        self.save_btn.setEnabled(True)

        # Enable/disable open guide button
        self.open_guide_btn.setEnabled(bool(self.guide_input.text().strip()))

    def _on_category_changed(self) -> None:
        """Handle category checkbox change."""
        self._metadata_dirty = True
        self.save_btn.setEnabled(True)

    def _save_changes(self) -> None:
        """Save metadata changes to the selected profile."""
        if not self._selected_profile:
            return

        # Parse tags
        tags_text = self.tags_input.text()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]

        # Get selected categories
        categories = [
            cat_val for cat_val, check in self.category_checks.items()
            if check.isChecked()
        ]

        # Update profile
        self.character_manager.update_profile(
            self._selected_profile,
            guide_url=self.guide_input.text().strip(),
            tags=tags,
            ssf_friendly=self.ssf_friendly_check.isChecked(),
            favorite=self.favorite_check.isChecked(),
            notes=self.notes_edit.toPlainText(),
        )

        # Update categories separately
        self.character_manager.set_build_categories(self._selected_profile, categories)

        self._metadata_dirty = False
        self.save_btn.setEnabled(False)
        self._refresh_build_list()

        # Re-select the profile
        self._select_profile(self._selected_profile)

    def _select_profile(self, name: str) -> None:
        """Select a profile in the table by name."""
        for row in range(self.build_table.rowCount()):
            item = self.build_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == name:
                self.build_table.selectRow(row)
                break

    def _open_guide_url(self) -> None:
        """Open the guide URL in a browser."""
        url = self.guide_input.text().strip()
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            QDesktopServices.openUrl(QUrl(url))

    def _set_as_active(self) -> None:
        """Set selected profile as active."""
        if not self._selected_profile:
            return

        self.character_manager.set_active_profile(self._selected_profile)
        self.active_profile_changed.emit(self._selected_profile)
        QMessageBox.information(
            self,
            "Active Profile",
            f"'{self._selected_profile}' is now the active profile."
        )

    def _set_as_upgrade_target(self) -> None:
        """Set selected profile as upgrade target."""
        if not self._selected_profile:
            return

        self.character_manager.set_upgrade_target(self._selected_profile, True)
        self._refresh_build_list()
        self._select_profile(self._selected_profile)
        QMessageBox.information(
            self,
            "Upgrade Target",
            f"'{self._selected_profile}' is now the upgrade target."
        )

    def _import_build(self) -> None:
        """Import a build from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Build",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both single profile and list of profiles
            if isinstance(data, list):
                imported = 0
                for profile_data in data:
                    if self.character_manager.import_profile(profile_data):
                        imported += 1
                QMessageBox.information(
                    self,
                    "Import Complete",
                    f"Imported {imported} build(s)."
                )
            else:
                name = self.character_manager.import_profile(data)
                if name:
                    QMessageBox.information(
                        self,
                        "Import Complete",
                        f"Imported build: {name}"
                    )
                    self._refresh_build_list()
                    self._select_profile(name)
                else:
                    QMessageBox.warning(
                        self,
                        "Import Failed",
                        "Failed to import build. Check the file format."
                    )
                    return

            self._refresh_build_list()

        except Exception as e:
            logger.exception("Import failed")
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import: {e}"
            )

    def _export_build(self) -> None:
        """Export selected build to file."""
        if not self._selected_profile:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Build",
            f"{self._selected_profile}.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            data = self.character_manager.export_profile(self._selected_profile)
            if data:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Build exported to:\n{file_path}"
                )
        except Exception as e:
            logger.exception("Export failed")
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export: {e}"
            )

    def _delete_build(self) -> None:
        """Delete selected build."""
        if not self._selected_profile:
            return

        # Check if it's a protected "my_builds" category
        profile = self.character_manager.get_profile(self._selected_profile)
        if profile and BuildCategory.MY_BUILDS.value in profile.categories:
            result = QMessageBox.warning(
                self,
                "Protected Build",
                f"'{self._selected_profile}' is in 'My Builds' category.\n\n"
                "Are you sure you want to delete it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
        else:
            result = QMessageBox.question(
                self,
                "Delete Build",
                f"Delete '{self._selected_profile}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

        if result == QMessageBox.StandardButton.Yes:
            self.character_manager.delete_profile(self._selected_profile)
            self._selected_profile = None
            self._clear_details()
            self._refresh_build_list()

    def _show_context_menu(self, position) -> None:
        """Show context menu for build list."""
        item = self.build_table.itemAt(position)
        if not item:
            return

        row = item.row()
        first_item = self.build_table.item(row, 0)
        if not first_item:
            return
        profile_name = first_item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        set_active_action = QAction("Set as Active", self)
        set_active_action.triggered.connect(lambda: self._set_profile_active(profile_name))
        menu.addAction(set_active_action)

        set_target_action = QAction("Set as Upgrade Target", self)
        set_target_action.triggered.connect(lambda: self._set_profile_target(profile_name))
        menu.addAction(set_target_action)

        menu.addSeparator()

        toggle_fav_action = QAction("Toggle Favorite", self)
        toggle_fav_action.triggered.connect(lambda: self._toggle_profile_favorite(profile_name))
        menu.addAction(toggle_fav_action)

        menu.addSeparator()

        export_action = QAction("Export...", self)
        export_action.triggered.connect(lambda: self._export_specific_build(profile_name))
        menu.addAction(export_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self._delete_specific_build(profile_name))
        menu.addAction(delete_action)

        viewport = self.build_table.viewport()
        if viewport:
            menu.exec(viewport.mapToGlobal(position))

    def _set_profile_active(self, name: str) -> None:
        """Set a specific profile as active."""
        self.character_manager.set_active_profile(name)
        self.active_profile_changed.emit(name)

    def _set_profile_target(self, name: str) -> None:
        """Set a specific profile as upgrade target."""
        self.character_manager.set_upgrade_target(name, True)
        self._refresh_build_list()

    def _toggle_profile_favorite(self, name: str) -> None:
        """Toggle favorite status for a profile."""
        self.character_manager.toggle_favorite(name)
        self._refresh_build_list()
        if self._selected_profile == name:
            self._load_profile_details(name)

    def _export_specific_build(self, name: str) -> None:
        """Export a specific build."""
        old_selected = self._selected_profile
        self._selected_profile = name
        self._export_build()
        self._selected_profile = old_selected

    def _delete_specific_build(self, name: str) -> None:
        """Delete a specific build."""
        old_selected = self._selected_profile
        self._selected_profile = name
        self._delete_build()
        self._selected_profile = old_selected
