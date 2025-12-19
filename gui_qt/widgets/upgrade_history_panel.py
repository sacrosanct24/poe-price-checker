"""
Upgrade Advice History Panel Widget.

Shows historical AI analyses for equipment slots, allowing users to
view and compare previous recommendations without spending tokens.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class UpgradeHistoryPanel(QWidget):
    """
    Panel showing history of AI analyses for an equipment slot.

    Displays the last 5 analyses with timestamps, AI model info,
    and stash scan status. Allows clicking to view/use cached analysis.

    Signals:
        history_selected(int): Emitted with history ID when user clicks an entry.
        use_cached(int): Emitted when user wants to use a cached analysis.

    Example:
        panel = UpgradeHistoryPanel()
        panel.history_selected.connect(on_history_selected)
        panel.load_history("Helmet", history_data)
    """

    history_selected = pyqtSignal(int)  # history record ID
    use_cached = pyqtSignal(int)  # history record ID to use

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the history panel."""
        super().__init__(parent)

        self._current_slot: Optional[str] = None
        self._history_items: List[Dict[str, Any]] = []
        self._selected_id: Optional[int] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout widgets."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Slot label / header
        self.slot_label = QLabel("Select a slot")
        self.slot_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.slot_label)

        # History list
        self.history_list = QListWidget()
        self.history_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self.history_list.setMaximumHeight(180)
        self.history_list.itemClicked.connect(self._on_item_clicked)
        self.history_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.history_list)

        # Preview area
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(8, 8, 8, 8)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setPlaceholderText("Click an entry to preview...")
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.use_btn = QPushButton("Use This Analysis")
        self.use_btn.setEnabled(False)
        self.use_btn.setToolTip("Display the selected cached analysis in the results panel")
        self.use_btn.clicked.connect(self._on_use_clicked)
        btn_layout.addWidget(self.use_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Spacer at bottom
        layout.addStretch()

    def load_history(self, slot: str, history: List[Dict[str, Any]]) -> None:
        """
        Load history entries for a slot.

        Args:
            slot: Equipment slot name (e.g., "Helmet").
            history: List of history records from database.
        """
        self._current_slot = slot
        self._history_items = history
        self._selected_id = None

        # Update header
        count = len(history)
        self.slot_label.setText(f"{slot} History ({count})")

        # Clear and populate list
        self.history_list.clear()
        self.preview_text.clear()
        self.use_btn.setEnabled(False)

        if not history:
            # Show empty state
            item = QListWidgetItem("No previous analyses")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.history_list.addItem(item)
            return

        for i, entry in enumerate(history, 1):
            # Format timestamp
            created = entry.get("created_at", "")
            if created:
                try:
                    # Parse SQLite timestamp format
                    dt = datetime.strptime(created[:19], "%Y-%m-%d %H:%M:%S")
                    time_str = dt.strftime("%b %d, %H:%M")
                except (ValueError, TypeError):
                    time_str = created[:16]
            else:
                time_str = "Unknown"

            # Get model/provider info
            provider = entry.get("ai_provider", "")
            model = entry.get("ai_model", "")
            if provider:
                model_str = provider.title()
            elif model:
                model_str = model.split("-")[0].title()
            else:
                model_str = "AI"

            # Stash indicator
            stash = entry.get("include_stash", False)
            stash_str = "+stash" if stash else "trade"

            # Create list item
            item_text = f"[{i}] {time_str} - {model_str}, {stash_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, entry.get("id"))
            item.setToolTip("Click to preview, double-click to use")
            self.history_list.addItem(item)

    def clear(self) -> None:
        """Clear the panel."""
        self._current_slot = None
        self._history_items = []
        self._selected_id = None
        self.slot_label.setText("Select a slot")
        self.history_list.clear()
        self.preview_text.clear()
        self.use_btn.setEnabled(False)

    def get_selected_id(self) -> Optional[int]:
        """Get the currently selected history ID."""
        return self._selected_id

    def get_entry_by_id(self, history_id: int) -> Optional[Dict[str, Any]]:
        """Get a history entry by its ID."""
        for entry in self._history_items:
            if entry.get("id") == history_id:
                return entry
        return None

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle history item click - show preview."""
        history_id = item.data(Qt.ItemDataRole.UserRole)
        if history_id is None:
            return

        self._selected_id = history_id

        # Find the entry and show preview
        for entry in self._history_items:
            if entry.get("id") == history_id:
                # Show truncated preview
                advice = entry.get("advice_text", "")
                preview = advice[:500]
                if len(advice) > 500:
                    preview += "\n\n... (truncated)"
                self.preview_text.setMarkdown(preview)
                self.use_btn.setEnabled(True)
                self.history_selected.emit(history_id)
                break

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click - use the cached analysis."""
        history_id = item.data(Qt.ItemDataRole.UserRole)
        if history_id is not None:
            self._selected_id = history_id
            self.use_cached.emit(history_id)

    def _on_use_clicked(self) -> None:
        """Handle 'Use This Analysis' button click."""
        if self._selected_id is not None:
            self.use_cached.emit(self._selected_id)
