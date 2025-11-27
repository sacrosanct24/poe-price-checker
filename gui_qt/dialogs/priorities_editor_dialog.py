"""
gui_qt.dialogs.priorities_editor_dialog

Dialog for editing build stat priorities for BiS item searching.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QWidget,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QFrame,
    QMessageBox,
    QLineEdit,
)

from gui_qt.styles import COLORS, apply_window_icon
from core.build_priorities import (
    BuildPriorities,
    StatPriority,
    PriorityTier,
    AVAILABLE_STATS,
    suggest_priorities_from_build,
)
from core.pob_integration import CharacterManager

logger = logging.getLogger(__name__)


class PrioritiesEditorDialog(QDialog):
    """Dialog for editing build stat priorities."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        character_manager: Optional[CharacterManager] = None,
        profile_name: Optional[str] = None,
        on_save: Optional[Callable[[BuildPriorities], None]] = None,
    ):
        super().__init__(parent)

        self.character_manager = character_manager
        self.profile_name = profile_name
        self.on_save = on_save
        self._priorities: Optional[BuildPriorities] = None

        self.setWindowTitle("Edit Build Priorities")
        self.setMinimumWidth(500)
        self.setMinimumHeight(650)
        self.resize(550, 750)  # Good default size for vertical layout
        self.setSizeGripEnabled(True)  # Show resize grip
        apply_window_icon(self)

        self._create_widgets()
        self._load_profile()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === Header ===
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(f"<b>Profile:</b> {self.profile_name or 'None'}"))
        header_layout.addStretch()

        self.auto_suggest_btn = QPushButton("Auto-Suggest from Build")
        self.auto_suggest_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent_blue"]};
                color: white;
                padding: 8px 16px;
            }}
        """)
        self.auto_suggest_btn.clicked.connect(self._auto_suggest)
        header_layout.addWidget(self.auto_suggest_btn)

        layout.addLayout(header_layout)

        # === Stat Picker ===
        picker_group = QGroupBox("Add Stat")
        picker_layout = QHBoxLayout(picker_group)

        self.stat_combo = QComboBox()
        self.stat_combo.setMinimumWidth(200)
        for stat_type, stat_name in sorted(AVAILABLE_STATS.items(), key=lambda x: x[1]):
            self.stat_combo.addItem(stat_name, stat_type)
        picker_layout.addWidget(self.stat_combo)

        self.tier_combo = QComboBox()
        self.tier_combo.addItem("Critical", PriorityTier.CRITICAL.value)
        self.tier_combo.addItem("Important", PriorityTier.IMPORTANT.value)
        self.tier_combo.addItem("Nice to Have", PriorityTier.NICE_TO_HAVE.value)
        picker_layout.addWidget(self.tier_combo)

        picker_layout.addWidget(QLabel("Min:"))
        self.min_value_input = QLineEdit()
        self.min_value_input.setPlaceholderText("Optional")
        self.min_value_input.setMaximumWidth(80)
        picker_layout.addWidget(self.min_value_input)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_stat)
        picker_layout.addWidget(add_btn)

        picker_layout.addStretch()
        layout.addWidget(picker_group)

        # === Priority Lists (stacked vertically for better readability) ===
        lists_layout = QVBoxLayout()

        # Critical
        critical_group = QGroupBox("Critical (Must-Have)")
        critical_group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {COLORS["corrupted"]};
            }}
            QGroupBox::title {{
                color: {COLORS["corrupted"]};
            }}
        """)
        critical_layout = QVBoxLayout(critical_group)
        self.critical_list = QListWidget()
        self.critical_list.setMaximumHeight(120)
        self.critical_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.critical_list.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.critical_list, pos)
        )
        critical_layout.addWidget(self.critical_list)
        lists_layout.addWidget(critical_group)

        # Important
        important_group = QGroupBox("Important (High Priority)")
        important_group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {COLORS["currency"]};
            }}
            QGroupBox::title {{
                color: {COLORS["currency"]};
            }}
        """)
        important_layout = QVBoxLayout(important_group)
        self.important_list = QListWidget()
        self.important_list.setMaximumHeight(120)
        self.important_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.important_list.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.important_list, pos)
        )
        important_layout.addWidget(self.important_list)
        lists_layout.addWidget(important_group)

        # Nice to Have
        nice_group = QGroupBox("Nice to Have (Optional)")
        nice_group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {COLORS["text_secondary"]};
            }}
            QGroupBox::title {{
                color: {COLORS["text_secondary"]};
            }}
        """)
        nice_layout = QVBoxLayout(nice_group)
        self.nice_list = QListWidget()
        self.nice_list.setMaximumHeight(120)
        self.nice_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.nice_list.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.nice_list, pos)
        )
        nice_layout.addWidget(self.nice_list)
        lists_layout.addWidget(nice_group)

        layout.addLayout(lists_layout, stretch=1)

        # === Build Type ===
        type_group = QGroupBox("Build Type")
        type_layout = QHBoxLayout(type_group)

        self.life_build_btn = QPushButton("Life Build")
        self.life_build_btn.setCheckable(True)
        self.life_build_btn.clicked.connect(lambda: self._set_build_type("life"))
        type_layout.addWidget(self.life_build_btn)

        self.es_build_btn = QPushButton("ES Build")
        self.es_build_btn.setCheckable(True)
        self.es_build_btn.clicked.connect(lambda: self._set_build_type("es"))
        type_layout.addWidget(self.es_build_btn)

        self.hybrid_btn = QPushButton("Hybrid")
        self.hybrid_btn.setCheckable(True)
        self.hybrid_btn.clicked.connect(lambda: self._set_build_type("hybrid"))
        type_layout.addWidget(self.hybrid_btn)

        type_layout.addStretch()
        layout.addWidget(type_group)

        # === Buttons ===
        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: black;
                font-weight: bold;
                padding: 10px 30px;
            }}
        """)
        save_btn.clicked.connect(self._save)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

    def _load_profile(self) -> None:
        """Load profile and existing priorities."""
        if not self.character_manager or not self.profile_name:
            return

        profile = self.character_manager.get_profile(self.profile_name)
        if not profile:
            return

        # Load existing priorities or create new
        if profile.priorities:
            self._priorities = profile.priorities
        else:
            self._priorities = BuildPriorities()

        self._refresh_lists()
        self._update_build_type_buttons()

    def _refresh_lists(self) -> None:
        """Refresh the priority lists from current data."""
        self.critical_list.clear()
        self.important_list.clear()
        self.nice_list.clear()

        if not self._priorities:
            return

        for p in self._priorities.critical:
            self._add_item_to_list(self.critical_list, p)

        for p in self._priorities.important:
            self._add_item_to_list(self.important_list, p)

        for p in self._priorities.nice_to_have:
            self._add_item_to_list(self.nice_list, p)

    def _add_item_to_list(self, list_widget: QListWidget, priority: StatPriority) -> None:
        """Add a priority item to a list widget."""
        name = AVAILABLE_STATS.get(priority.stat_type, priority.stat_type)
        text = name
        if priority.min_value:
            text += f" (min: {priority.min_value})"
        if priority.notes:
            text += f" - {priority.notes}"

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, priority.stat_type)
        list_widget.addItem(item)

    def _update_build_type_buttons(self) -> None:
        """Update build type button states."""
        if not self._priorities:
            return

        self.life_build_btn.setChecked(self._priorities.is_life_build)
        self.es_build_btn.setChecked(self._priorities.is_es_build)
        self.hybrid_btn.setChecked(self._priorities.is_hybrid)

    def _set_build_type(self, build_type: str) -> None:
        """Set the build type."""
        if not self._priorities:
            self._priorities = BuildPriorities()

        self._priorities.is_life_build = build_type == "life"
        self._priorities.is_es_build = build_type == "es"
        self._priorities.is_hybrid = build_type == "hybrid"
        self._update_build_type_buttons()

    def _add_stat(self) -> None:
        """Add a stat to priorities."""
        if not self._priorities:
            self._priorities = BuildPriorities()

        stat_type = self.stat_combo.currentData()
        tier_value = self.tier_combo.currentData()
        tier = PriorityTier(tier_value)

        min_value = None
        min_text = self.min_value_input.text().strip()
        if min_text:
            try:
                min_value = int(min_text)
            except ValueError:
                pass

        self._priorities.add_priority(stat_type, tier, min_value)
        self._refresh_lists()
        self.min_value_input.clear()

    def _show_context_menu(self, list_widget: QListWidget, pos) -> None:
        """Show context menu for removing items."""
        item = list_widget.itemAt(pos)
        if not item:
            return

        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)

        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self._remove_stat(item))

        # Move to different tier
        move_menu = menu.addMenu("Move to...")

        if list_widget != self.critical_list:
            to_critical = move_menu.addAction("Critical")
            to_critical.triggered.connect(
                lambda: self._move_stat(item, PriorityTier.CRITICAL)
            )

        if list_widget != self.important_list:
            to_important = move_menu.addAction("Important")
            to_important.triggered.connect(
                lambda: self._move_stat(item, PriorityTier.IMPORTANT)
            )

        if list_widget != self.nice_list:
            to_nice = move_menu.addAction("Nice to Have")
            to_nice.triggered.connect(
                lambda: self._move_stat(item, PriorityTier.NICE_TO_HAVE)
            )

        menu.exec(list_widget.mapToGlobal(pos))

    def _remove_stat(self, item: QListWidgetItem) -> None:
        """Remove a stat from priorities."""
        if not self._priorities:
            return

        stat_type = item.data(Qt.ItemDataRole.UserRole)
        self._priorities.remove_priority(stat_type)
        self._refresh_lists()

    def _move_stat(self, item: QListWidgetItem, new_tier: PriorityTier) -> None:
        """Move a stat to a different tier."""
        if not self._priorities:
            return

        stat_type = item.data(Qt.ItemDataRole.UserRole)
        existing = self._priorities.get_priority(stat_type)
        if existing:
            self._priorities.add_priority(
                stat_type, new_tier, existing.min_value, existing.notes
            )
            self._refresh_lists()

    def _auto_suggest(self) -> None:
        """Auto-suggest priorities from build analysis."""
        if not self.character_manager or not self.profile_name:
            return

        profile = self.character_manager.get_profile(self.profile_name)
        if not profile or not profile.build or not profile.build.stats:
            QMessageBox.warning(
                self, "No Build Data",
                "This profile doesn't have build stats to analyze."
            )
            return

        # Confirm before overwriting
        if self._priorities and (
            self._priorities.critical or
            self._priorities.important or
            self._priorities.nice_to_have
        ):
            result = QMessageBox.question(
                self, "Replace Priorities?",
                "This will replace your current priorities with auto-suggested ones.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        # Generate suggestions
        self._priorities = suggest_priorities_from_build(profile.build.stats)
        self._refresh_lists()
        self._update_build_type_buttons()

        QMessageBox.information(
            self, "Priorities Suggested",
            f"Added {len(self._priorities.critical)} critical, "
            f"{len(self._priorities.important)} important, and "
            f"{len(self._priorities.nice_to_have)} nice-to-have stats based on your build."
        )

    def _save(self) -> None:
        """Save priorities."""
        if not self._priorities:
            self._priorities = BuildPriorities()

        if self.character_manager and self.profile_name:
            self.character_manager.set_priorities(self.profile_name, self._priorities)

        if self.on_save:
            self.on_save(self._priorities)

        self.accept()

    def get_priorities(self) -> Optional[BuildPriorities]:
        """Get the current priorities."""
        return self._priorities
