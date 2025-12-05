"""
gui_qt.widgets.ai_analysis_panel

Collapsible panel for displaying AI item analysis results.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QTextEdit,
    QPushButton,
    QSizePolicy,
)

from gui_qt.styles import COLORS
from data_sources.ai import AIResponse, get_provider_display_name


class AIAnalysisPanelWidget(QGroupBox):
    """
    Collapsible panel that displays AI item analysis results.

    Shows:
    - Provider badge
    - Loading indicator during analysis
    - AI response text
    - Close/dismiss button

    Signals:
        dismissed: Emitted when user clicks dismiss button
        retry_requested: Emitted when user wants to retry analysis
    """

    dismissed = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("AI Analysis", parent)

        self._response: Optional[AIResponse] = None
        self._is_loading = False
        self._error_message: Optional[str] = None

        self._create_widgets()
        self.clear()

        # Start hidden - will be shown when analysis requested
        self.setVisible(False)

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Row 1: Header with provider badge and controls
        header_row = QHBoxLayout()

        # Provider badge
        self.provider_label = QLabel()
        provider_font = QFont()
        provider_font.setPointSize(11)
        provider_font.setBold(True)
        self.provider_label.setFont(provider_font)
        header_row.addWidget(self.provider_label)

        # Status label (loading, tokens used, etc.)
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header_row.addWidget(self.status_label)

        header_row.addStretch()

        # Retry button
        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setFixedWidth(60)
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.clicked.connect(self.retry_requested.emit)
        self.retry_btn.setVisible(False)
        header_row.addWidget(self.retry_btn)

        # Dismiss button
        self.dismiss_btn = QPushButton("x")
        self.dismiss_btn.setFixedSize(24, 24)
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.setToolTip("Dismiss AI analysis")
        self.dismiss_btn.clicked.connect(self._on_dismiss)
        self.dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {COLORS['text']};
            }}
        """)
        header_row.addWidget(self.dismiss_btn)

        layout.addLayout(header_row)

        # Row 2: Content area
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setMinimumHeight(100)
        self.content_text.setMaximumHeight(200)
        self.content_text.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.content_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                line-height: 1.4;
            }}
        """)
        layout.addWidget(self.content_text)

        # Style the group box
        self.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                color: {COLORS['text']};
            }}
        """)

    def _on_dismiss(self) -> None:
        """Handle dismiss button click."""
        self.clear()
        self.setVisible(False)
        self.dismissed.emit()

    def show_loading(self, provider: str = "") -> None:
        """Show loading state.

        Args:
            provider: The provider being used (for display).
        """
        self._is_loading = True
        self._error_message = None
        self._response = None

        if provider:
            display_name = get_provider_display_name(provider)
            self.provider_label.setText(display_name)
            self.provider_label.setStyleSheet(f"color: {COLORS['accent']};")
        else:
            self.provider_label.setText("AI Analysis")
            self.provider_label.setStyleSheet(f"color: {COLORS['text']};")

        self.status_label.setText("Analyzing...")
        self.content_text.setPlainText("Asking AI for analysis...\n\nThis may take a few seconds.")
        self.retry_btn.setVisible(False)
        self.setVisible(True)

    def show_response(self, response: AIResponse) -> None:
        """Display AI response.

        Args:
            response: The AIResponse from the AI provider.
        """
        self._is_loading = False
        self._error_message = None
        self._response = response

        # Update provider badge
        display_name = get_provider_display_name(response.provider)
        self.provider_label.setText(display_name)
        self.provider_label.setStyleSheet(f"color: {COLORS['accent']};")

        # Update status with token info
        if response.tokens_used > 0:
            self.status_label.setText(f"({response.tokens_used} tokens)")
        else:
            self.status_label.setText("")

        # Display content
        self.content_text.setPlainText(response.content)
        self.retry_btn.setVisible(False)
        self.setVisible(True)

    def show_error(self, error_message: str, provider: str = "") -> None:
        """Display error state.

        Args:
            error_message: The error message to display.
            provider: The provider that failed.
        """
        self._is_loading = False
        self._error_message = error_message
        self._response = None

        if provider:
            display_name = get_provider_display_name(provider)
            self.provider_label.setText(display_name)
        else:
            self.provider_label.setText("AI Analysis")
        self.provider_label.setStyleSheet(f"color: {COLORS['error']};")

        self.status_label.setText("Failed")
        self.content_text.setPlainText(f"Error: {error_message}\n\nClick 'Retry' to try again.")
        self.retry_btn.setVisible(True)
        self.setVisible(True)

    def clear(self) -> None:
        """Clear the panel and reset state."""
        self._is_loading = False
        self._error_message = None
        self._response = None

        self.provider_label.setText("")
        self.status_label.setText("")
        self.content_text.setPlainText("")
        self.retry_btn.setVisible(False)

    @property
    def is_loading(self) -> bool:
        """Check if panel is in loading state."""
        return self._is_loading

    @property
    def has_response(self) -> bool:
        """Check if panel has a response."""
        return self._response is not None

    @property
    def has_error(self) -> bool:
        """Check if panel is showing an error."""
        return self._error_message is not None
