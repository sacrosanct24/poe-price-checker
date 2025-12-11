"""
Clear Builds Dialog - Dialog for bulk deleting builds with category exclusions.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Set

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QWidget,
    QMessageBox,
)

from gui_qt.styles import COLORS, apply_window_icon

# Import BuildCategory
try:
    from core.pob import BuildCategory
    BUILD_CATEGORIES = list(BuildCategory)
    HAS_BUILD_CATEGORY = True
except ImportError:
    BUILD_CATEGORIES = []
    HAS_BUILD_CATEGORY = False

logger = logging.getLogger(__name__)


# Categories that are protected by default (checked = keep these)
PROTECTED_CATEGORIES = {"my_builds", "reference"}


class ClearBuildsDialog(QDialog):
    """
    Dialog for clearing builds with category exclusions.

    Allows user to select which categories to protect from deletion.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        character_manager=None,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self._category_checkboxes: dict = {}
        self._profiles_to_delete: List[str] = []

        self.setWindowTitle("Clear Builds")
        self.setMinimumWidth(400)
        apply_window_icon(self)

        self._create_widgets()
        self._update_preview()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)

        # Warning label
        warning = QLabel(
            "This will permanently delete builds. "
            "Check categories below to KEEP (protect from deletion)."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(f"color: {COLORS['corrupted']}; font-weight: bold;")
        layout.addWidget(warning)

        # Categories group
        categories_group = QGroupBox("Keep builds with these categories:")
        categories_layout = QVBoxLayout(categories_group)

        # Create checkbox for each category
        for cat in BUILD_CATEGORIES:
            checkbox = QCheckBox(cat.value.replace("_", " ").title())
            checkbox.setChecked(cat.value in PROTECTED_CATEGORIES)
            checkbox.stateChanged.connect(self._update_preview)
            self._category_checkboxes[cat.value] = checkbox
            categories_layout.addWidget(checkbox)

        layout.addWidget(categories_group)

        # Also protect active/upgrade target
        self.protect_active = QCheckBox("Keep active profile")
        self.protect_active.setChecked(True)
        self.protect_active.stateChanged.connect(self._update_preview)
        layout.addWidget(self.protect_active)

        self.protect_upgrade_target = QCheckBox("Keep upgrade target profile")
        self.protect_upgrade_target.setChecked(True)
        self.protect_upgrade_target.stateChanged.connect(self._update_preview)
        layout.addWidget(self.protect_upgrade_target)

        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 10px;
            }}
        """)
        layout.addWidget(self.preview_label)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.delete_btn = QPushButton("Delete Builds")
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["corrupted"]};
                color: white;
                font-weight: bold;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: #ff4444;
            }}
            QPushButton:disabled {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text_secondary"]};
            }}
        """)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

    def _get_protected_categories(self) -> Set[str]:
        """Get set of protected category values."""
        protected = set()
        for cat_value, checkbox in self._category_checkboxes.items():
            if checkbox.isChecked():
                protected.add(cat_value)
        return protected

    def _update_preview(self) -> None:
        """Update the preview of what will be deleted."""
        if not self.character_manager:
            self.preview_label.setText("No character manager available")
            self.delete_btn.setEnabled(False)
            return

        protected_categories = self._get_protected_categories()
        profiles = self.character_manager.list_profiles()

        # Get active and upgrade target names
        active_profile = self.character_manager.get_active_profile()
        active_name = active_profile.name if active_profile else None

        upgrade_target = self.character_manager.get_upgrade_target()
        upgrade_target_name = upgrade_target.name if upgrade_target else None

        # Determine which profiles to delete
        to_delete = []
        to_keep = []

        for name in profiles:
            profile = self.character_manager.get_profile(name)
            if not profile:
                continue

            # Check if protected by active/upgrade status
            if self.protect_active.isChecked() and name == active_name:
                to_keep.append(f"{name} (active)")
                continue

            if self.protect_upgrade_target.isChecked() and name == upgrade_target_name:
                to_keep.append(f"{name} (upgrade target)")
                continue

            # Check if protected by category
            categories = getattr(profile, 'categories', []) or []
            protected = False
            for cat in categories:
                if cat in protected_categories:
                    protected = True
                    break

            if protected:
                to_keep.append(name)
            else:
                to_delete.append(name)

        self._profiles_to_delete = to_delete

        # Update preview text
        if not to_delete:
            self.preview_label.setText(
                f"<b>No builds to delete.</b><br>"
                f"All {len(to_keep)} builds are protected."
            )
            self.delete_btn.setEnabled(False)
        else:
            delete_list = ", ".join(to_delete[:5])
            if len(to_delete) > 5:
                delete_list += f", ... (+{len(to_delete) - 5} more)"

            self.preview_label.setText(
                f"<b style='color: {COLORS['corrupted']}'>Will DELETE {len(to_delete)} builds:</b><br>"
                f"{delete_list}<br><br>"
                f"<span style='color: {COLORS['high_value']}'>Keeping {len(to_keep)} protected builds</span>"
            )
            self.delete_btn.setEnabled(True)

    def _on_delete(self) -> None:
        """Handle delete button click."""
        if not self._profiles_to_delete:
            return

        # Confirm deletion
        count = len(self._profiles_to_delete)
        reply = QMessageBox.warning(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {count} builds?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Delete profiles
        deleted = 0
        for name in self._profiles_to_delete:
            try:
                self.character_manager.delete_profile(name)
                deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete profile '{name}': {e}")

        logger.info(f"Deleted {deleted}/{count} builds")
        self.accept()

    def get_deleted_count(self) -> int:
        """Get the number of profiles that were deleted."""
        return len(self._profiles_to_delete)
