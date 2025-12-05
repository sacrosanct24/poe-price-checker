"""
Feedback Collector - In-app feedback submission form.

Provides a user-friendly way to collect feedback, bug reports,
and feature requests directly from within the application.

Usage:
    from gui_qt.feedback.feedback_collector import (
        FeedbackCollector,
        FeedbackDialog,
        FeedbackType,
    )

    # Show feedback dialog
    dialog = FeedbackDialog(parent)
    dialog.exec()

    # Or use the collector programmatically
    collector = FeedbackCollector()
    feedback = collector.collect(
        type=FeedbackType.BUG,
        message="Description of the bug...",
    )
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import platform
import sys

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDialog,
    QTextEdit,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QFrame,
    QGroupBox,
    QSizePolicy,
    QMessageBox,
)

from gui_qt.styles import COLORS
from gui_qt.design_system import (
    Spacing,
    BorderRadius,
    FontSize,
    FontWeight,
)

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback that can be submitted."""
    BUG = "bug"
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    OTHER = "other"


FEEDBACK_TYPE_LABELS = {
    FeedbackType.BUG: "Bug Report",
    FeedbackType.FEATURE: "Feature Request",
    FeedbackType.IMPROVEMENT: "Improvement Suggestion",
    FeedbackType.OTHER: "Other Feedback",
}

FEEDBACK_TYPE_HINTS = {
    FeedbackType.BUG: "Please describe what happened, what you expected, and steps to reproduce.",
    FeedbackType.FEATURE: "Describe the feature you'd like to see and how it would help you.",
    FeedbackType.IMPROVEMENT: "Describe what could be improved and how.",
    FeedbackType.OTHER: "Share your thoughts, questions, or anything else.",
}


@dataclass
class SystemInfo:
    """System information for feedback context."""
    os: str = field(default_factory=lambda: platform.system())
    os_version: str = field(default_factory=lambda: platform.version())
    python_version: str = field(default_factory=lambda: sys.version)
    app_version: str = "unknown"

    @classmethod
    def collect(cls, app_version: str = "unknown") -> "SystemInfo":
        """Collect current system information."""
        return cls(app_version=app_version)


@dataclass
class FeedbackEntry:
    """A feedback entry with all relevant information."""
    id: str
    type: FeedbackType
    message: str
    timestamp: str
    system_info: Optional[SystemInfo] = None
    context: Optional[str] = None  # What the user was doing
    contact: Optional[str] = None  # Optional email for follow-up
    include_logs: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "id": self.id,
            "type": self.type.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "contact": self.contact,
            "include_logs": self.include_logs,
        }
        if self.context:
            data["context"] = self.context
        if self.system_info:
            data["system_info"] = asdict(self.system_info)
        return data


class FeedbackCollector:
    """
    Collects and stores user feedback.

    Handles feedback collection, storage, and optional submission.
    """

    FEEDBACK_FILE = "feedback.json"

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize feedback collector.

        Args:
            storage_dir: Directory for storing feedback (default: app config dir)
        """
        if storage_dir is None:
            try:
                from core.config import get_config_dir
                storage_dir = get_config_dir()
            except ImportError:
                storage_dir = Path.home() / ".poe-price-checker"

        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._feedback_file = self._storage_dir / self.FEEDBACK_FILE

    def collect(
        self,
        type: FeedbackType,
        message: str,
        *,
        context: Optional[str] = None,
        contact: Optional[str] = None,
        include_system_info: bool = True,
        include_logs: bool = False,
        app_version: str = "unknown",
    ) -> FeedbackEntry:
        """
        Collect a feedback entry.

        Args:
            type: Type of feedback
            message: The feedback message
            context: What the user was doing
            contact: Optional contact email
            include_system_info: Whether to include system info
            include_logs: Whether to include logs
            app_version: Current app version

        Returns:
            The created feedback entry
        """
        # Generate unique ID
        timestamp = datetime.now().isoformat()
        feedback_id = f"{type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Collect system info if requested
        system_info = None
        if include_system_info:
            system_info = SystemInfo.collect(app_version)

        entry = FeedbackEntry(
            id=feedback_id,
            type=type,
            message=message,
            timestamp=timestamp,
            system_info=system_info,
            context=context,
            contact=contact,
            include_logs=include_logs,
        )

        # Store locally
        self._store_feedback(entry)

        return entry

    def _store_feedback(self, entry: FeedbackEntry) -> None:
        """Store feedback entry to disk."""
        try:
            # Load existing feedback
            feedback_list = []
            if self._feedback_file.exists():
                with open(self._feedback_file, "r", encoding="utf-8") as f:
                    feedback_list = json.load(f)

            # Append new entry
            feedback_list.append(entry.to_dict())

            # Save
            with open(self._feedback_file, "w", encoding="utf-8") as f:
                json.dump(feedback_list, f, indent=2)

            logger.info(f"Feedback stored: {entry.id}")
        except Exception as e:
            logger.error(f"Failed to store feedback: {e}")

    def get_stored_feedback(self) -> List[Dict[str, Any]]:
        """Get all stored feedback entries."""
        try:
            if self._feedback_file.exists():
                with open(self._feedback_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load feedback: {e}")
        return []


class FeedbackDialog(QDialog):
    """
    Dialog for collecting user feedback.

    Provides a form for users to submit feedback with
    type selection, message, and optional contact info.
    """

    feedback_submitted = pyqtSignal(FeedbackEntry)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        initial_type: FeedbackType = FeedbackType.BUG,
        app_version: str = "unknown",
    ):
        """
        Initialize feedback dialog.

        Args:
            parent: Parent widget
            initial_type: Initial feedback type selection
            app_version: Current app version
        """
        super().__init__(parent)

        self._app_version = app_version
        self._collector = FeedbackCollector()

        self._setup_ui(initial_type)

    def _setup_ui(self, initial_type: FeedbackType) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Send Feedback")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)

        # Header
        header = QLabel("We'd love to hear from you!")
        header.setStyleSheet(f"""
            font-size: {FontSize.LG}px;
            font-weight: {FontWeight.SEMIBOLD};
            color: {COLORS['text']};
        """)
        layout.addWidget(header)

        subheader = QLabel("Your feedback helps us improve the app.")
        subheader.setStyleSheet(f"""
            font-size: {FontSize.SM}px;
            color: {COLORS['text_secondary']};
        """)
        layout.addWidget(subheader)

        layout.addSpacing(Spacing.SM)

        # Feedback type selector
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        type_label.setFixedWidth(80)
        type_layout.addWidget(type_label)

        self._type_combo = QComboBox()
        for fb_type in FeedbackType:
            self._type_combo.addItem(
                FEEDBACK_TYPE_LABELS[fb_type],
                fb_type,
            )
        self._type_combo.setCurrentIndex(list(FeedbackType).index(initial_type))
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self._type_combo)

        layout.addLayout(type_layout)

        # Hint text
        self._hint_label = QLabel(FEEDBACK_TYPE_HINTS[initial_type])
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: {FontSize.XS}px;
            padding: {Spacing.XS}px;
            background-color: {COLORS['surface_variant']};
            border-radius: {BorderRadius.SM}px;
        """)
        layout.addWidget(self._hint_label)

        # Message input
        message_label = QLabel("Your Feedback:")
        layout.addWidget(message_label)

        self._message_edit = QTextEdit()
        self._message_edit.setPlaceholderText("Describe your feedback here...")
        self._message_edit.setMinimumHeight(150)
        self._message_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {BorderRadius.SM}px;
                padding: {Spacing.SM}px;
                font-size: {FontSize.BASE}px;
            }}
            QTextEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)
        layout.addWidget(self._message_edit)

        # Context input (optional)
        context_layout = QHBoxLayout()
        context_label = QLabel("Context:")
        context_label.setFixedWidth(80)
        context_label.setToolTip("What were you doing when the issue occurred?")
        context_layout.addWidget(context_label)

        self._context_edit = QLineEdit()
        self._context_edit.setPlaceholderText("What were you doing? (optional)")
        context_layout.addWidget(self._context_edit)

        layout.addLayout(context_layout)

        # Contact input (optional)
        contact_layout = QHBoxLayout()
        contact_label = QLabel("Email:")
        contact_label.setFixedWidth(80)
        contact_label.setToolTip("Optional - for follow-up questions")
        contact_layout.addWidget(contact_label)

        self._contact_edit = QLineEdit()
        self._contact_edit.setPlaceholderText("your@email.com (optional)")
        contact_layout.addWidget(self._contact_edit)

        layout.addLayout(contact_layout)

        # Options
        options_layout = QHBoxLayout()

        self._include_system_cb = QCheckBox("Include system info")
        self._include_system_cb.setChecked(True)
        self._include_system_cb.setToolTip(
            "Include OS, Python version, and app version"
        )
        options_layout.addWidget(self._include_system_cb)

        self._include_logs_cb = QCheckBox("Include recent logs")
        self._include_logs_cb.setToolTip(
            "Include recent log entries (may contain item names)"
        )
        options_layout.addWidget(self._include_logs_cb)

        options_layout.addStretch()

        layout.addLayout(options_layout)

        # Buttons
        layout.addStretch()

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        submit_btn = QPushButton("Submit Feedback")
        submit_btn.setObjectName("primaryButton")
        submit_btn.clicked.connect(self._submit)
        submit_btn.setStyleSheet(f"""
            QPushButton#primaryButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['on_primary']};
                border: none;
                border-radius: {BorderRadius.SM}px;
                padding: 8px 20px;
                font-weight: {FontWeight.MEDIUM};
            }}
            QPushButton#primaryButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
        """)
        buttons_layout.addWidget(submit_btn)

        layout.addLayout(buttons_layout)

    def _on_type_changed(self, index: int) -> None:
        """Handle feedback type change."""
        fb_type = self._type_combo.currentData()
        self._hint_label.setText(FEEDBACK_TYPE_HINTS[fb_type])

    def _submit(self) -> None:
        """Submit the feedback."""
        message = self._message_edit.toPlainText().strip()

        if not message:
            QMessageBox.warning(
                self,
                "Missing Feedback",
                "Please enter your feedback before submitting.",
            )
            return

        fb_type = self._type_combo.currentData()
        context = self._context_edit.text().strip() or None
        contact = self._contact_edit.text().strip() or None

        entry = self._collector.collect(
            type=fb_type,
            message=message,
            context=context,
            contact=contact,
            include_system_info=self._include_system_cb.isChecked(),
            include_logs=self._include_logs_cb.isChecked(),
            app_version=self._app_version,
        )

        self.feedback_submitted.emit(entry)

        QMessageBox.information(
            self,
            "Thank You!",
            "Your feedback has been saved. Thank you for helping us improve!",
        )

        self.accept()
