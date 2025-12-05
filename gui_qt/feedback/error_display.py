"""
Error Display - User-friendly error messages with recovery options.

Provides a framework for displaying friendly error messages that
guide users toward solutions rather than showing raw technical errors.

Usage:
    from gui_qt.feedback.error_display import (
        FriendlyError,
        ErrorDisplay,
        show_error,
    )

    # Create a friendly error
    error = FriendlyError(
        title="Price Check Failed",
        message="Couldn't reach poe.ninja",
        details="Connection timeout after 30s",
        retry_action=lambda: retry_price_check(),
        help_link="https://docs.example.com/troubleshooting",
    )

    # Display inline
    display = ErrorDisplay(error)
    layout.addWidget(display)

    # Or show as dialog
    show_error(parent, error)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QDialog,
    QTextEdit,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)

from gui_qt.styles import COLORS
from gui_qt.design_system import (
    Spacing,
    BorderRadius,
    Duration,
    FontSize,
    FontWeight,
    Elevation,
)


class ErrorSeverity(Enum):
    """Severity level for errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Icons for different severity levels
SEVERITY_ICONS = {
    ErrorSeverity.INFO: "\u2139",      # Information symbol
    ErrorSeverity.WARNING: "\u26A0",   # Warning triangle
    ErrorSeverity.ERROR: "\u2716",     # X mark
    ErrorSeverity.CRITICAL: "\u26D4",  # No entry
}

# Colors for different severity levels
SEVERITY_COLORS = {
    ErrorSeverity.INFO: "#2196F3",     # Blue
    ErrorSeverity.WARNING: "#FF9800",  # Orange
    ErrorSeverity.ERROR: "#F44336",    # Red
    ErrorSeverity.CRITICAL: "#D32F2F", # Dark red
}


@dataclass
class FriendlyError:
    """
    User-friendly error with recovery options.

    Encapsulates error information in a way that's helpful
    to users rather than showing raw technical details.
    """

    title: str
    """Short, clear error title (e.g., "Price Check Failed")"""

    message: str
    """User-friendly explanation (e.g., "Couldn't reach poe.ninja")"""

    severity: ErrorSeverity = ErrorSeverity.ERROR
    """Error severity level"""

    details: Optional[str] = None
    """Technical details (expandable, for advanced users)"""

    retry_action: Optional[Callable[[], None]] = None
    """Callback to retry the failed operation"""

    help_link: Optional[str] = None
    """Link to help documentation"""

    suggestions: List[str] = field(default_factory=list)
    """List of suggestions to fix the issue"""

    auto_dismiss: bool = False
    """Whether error should auto-dismiss after a timeout"""

    dismiss_timeout: int = 5000
    """Auto-dismiss timeout in milliseconds"""

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        *,
        title: str = "An Error Occurred",
        suggestions: Optional[List[str]] = None,
    ) -> "FriendlyError":
        """
        Create a friendly error from an exception.

        Args:
            exc: The exception
            title: Custom title override
            suggestions: List of suggestions for the user
        """
        # Map common exception types to user-friendly messages
        exc_type = type(exc).__name__
        exc_message = str(exc)

        message_map = {
            "ConnectionError": "Unable to connect to the server. Check your internet connection.",
            "TimeoutError": "The request timed out. The server might be slow or unavailable.",
            "HTTPError": "The server returned an error. Try again later.",
            "JSONDecodeError": "Received invalid data from the server.",
            "FileNotFoundError": "The requested file could not be found.",
            "PermissionError": "Permission denied. Try running as administrator.",
        }

        message = message_map.get(exc_type, f"An unexpected error occurred: {exc_message}")

        return cls(
            title=title,
            message=message,
            details=f"{exc_type}: {exc_message}",
            suggestions=suggestions or [],
        )


class ErrorDisplay(QFrame):
    """
    Inline error display widget.

    Shows error information with optional retry button,
    expandable details, and help link.
    """

    retry_clicked = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(
        self,
        error: FriendlyError,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize error display.

        Args:
            error: The friendly error to display
            parent: Parent widget
        """
        super().__init__(parent)

        self._error = error
        self._details_visible = False

        self._setup_ui()
        self._apply_style()

        # Auto-dismiss if configured
        if error.auto_dismiss:
            QTimer.singleShot(error.dismiss_timeout, self._dismiss)

    def _setup_ui(self) -> None:
        """Set up the display UI."""
        self.setObjectName("errorDisplay")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        main_layout.setSpacing(Spacing.SM)

        # Header row (icon + title + dismiss)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(Spacing.SM)

        # Icon
        icon = SEVERITY_ICONS[self._error.severity]
        icon_label = QLabel(icon)
        icon_label.setObjectName("errorIcon")
        header_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(self._error.title)
        title_label.setObjectName("errorTitle")
        title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header_layout.addWidget(title_label)

        # Dismiss button
        dismiss_btn = QPushButton("\u2715")  # X symbol
        dismiss_btn.setObjectName("dismissButton")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.clicked.connect(self._dismiss)
        dismiss_btn.setToolTip("Dismiss")
        header_layout.addWidget(dismiss_btn)

        main_layout.addLayout(header_layout)

        # Message
        message_label = QLabel(self._error.message)
        message_label.setObjectName("errorMessage")
        message_label.setWordWrap(True)
        main_layout.addWidget(message_label)

        # Suggestions (if any)
        if self._error.suggestions:
            suggestions_frame = QFrame()
            suggestions_frame.setObjectName("suggestionsFrame")
            suggestions_layout = QVBoxLayout(suggestions_frame)
            suggestions_layout.setContentsMargins(Spacing.SM, Spacing.XS, 0, 0)
            suggestions_layout.setSpacing(Spacing.XS)

            for suggestion in self._error.suggestions:
                sug_label = QLabel(f"\u2022 {suggestion}")
                sug_label.setObjectName("suggestionText")
                sug_label.setWordWrap(True)
                suggestions_layout.addWidget(sug_label)

            main_layout.addWidget(suggestions_frame)

        # Action buttons row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(Spacing.SM)

        # Details toggle (if details available)
        if self._error.details:
            self._details_btn = QPushButton("Show Details")
            self._details_btn.setObjectName("detailsButton")
            self._details_btn.clicked.connect(self._toggle_details)
            actions_layout.addWidget(self._details_btn)

        # Help link (if available)
        if self._error.help_link:
            help_btn = QPushButton("Help")
            help_btn.setObjectName("helpButton")
            help_btn.clicked.connect(self._open_help)
            actions_layout.addWidget(help_btn)

        actions_layout.addStretch()

        # Retry button (if action available)
        if self._error.retry_action:
            retry_btn = QPushButton("Retry")
            retry_btn.setObjectName("retryButton")
            retry_btn.clicked.connect(self._on_retry)
            actions_layout.addWidget(retry_btn)

        main_layout.addLayout(actions_layout)

        # Details section (initially hidden)
        if self._error.details:
            self._details_widget = QTextEdit()
            self._details_widget.setObjectName("detailsText")
            self._details_widget.setReadOnly(True)
            self._details_widget.setPlainText(self._error.details)
            self._details_widget.setMaximumHeight(100)
            self._details_widget.hide()
            main_layout.addWidget(self._details_widget)

    def _apply_style(self) -> None:
        """Apply error styling."""
        color = SEVERITY_COLORS[self._error.severity]
        bg_color = f"{color}1A"  # 10% opacity

        self.setStyleSheet(f"""
            QFrame#errorDisplay {{
                background-color: {bg_color};
                border: 1px solid {color};
                border-left: 4px solid {color};
                border-radius: {BorderRadius.SM}px;
            }}
            QLabel#errorIcon {{
                color: {color};
                font-size: {FontSize.LG}px;
            }}
            QLabel#errorTitle {{
                color: {color};
                font-size: {FontSize.BASE}px;
                font-weight: {FontWeight.SEMIBOLD};
            }}
            QLabel#errorMessage {{
                color: {COLORS['text']};
                font-size: {FontSize.SM}px;
            }}
            QLabel#suggestionText {{
                color: {COLORS['text_secondary']};
                font-size: {FontSize.SM}px;
            }}
            QPushButton#dismissButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 12px;
            }}
            QPushButton#dismissButton:hover {{
                color: {COLORS['text']};
            }}
            QPushButton#retryButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: {BorderRadius.SM}px;
                padding: 6px 16px;
                font-weight: {FontWeight.MEDIUM};
            }}
            QPushButton#retryButton:hover {{
                opacity: 0.9;
            }}
            QPushButton#detailsButton, QPushButton#helpButton {{
                background: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: {BorderRadius.SM}px;
                padding: 4px 12px;
                color: {COLORS['text_secondary']};
            }}
            QPushButton#detailsButton:hover, QPushButton#helpButton:hover {{
                background-color: {COLORS['surface_variant']};
            }}
            QTextEdit#detailsText {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {BorderRadius.SM}px;
                color: {COLORS['text_secondary']};
                font-family: "Consolas", "Monaco", monospace;
                font-size: {FontSize.XS}px;
                padding: {Spacing.XS}px;
            }}
        """)

    def _toggle_details(self) -> None:
        """Toggle details visibility."""
        self._details_visible = not self._details_visible
        self._details_widget.setVisible(self._details_visible)
        self._details_btn.setText(
            "Hide Details" if self._details_visible else "Show Details"
        )

    def _open_help(self) -> None:
        """Open help link in browser."""
        if self._error.help_link:
            QDesktopServices.openUrl(QUrl(self._error.help_link))

    def _on_retry(self) -> None:
        """Handle retry button click."""
        if self._error.retry_action:
            self._error.retry_action()
        self.retry_clicked.emit()

    def _dismiss(self) -> None:
        """Dismiss the error display."""
        self.hide()
        self.dismissed.emit()


class ErrorDialog(QDialog):
    """
    Modal error dialog with friendly messaging.

    Shows error information in a dialog with optional
    retry and help actions.
    """

    retry_clicked = pyqtSignal()

    def __init__(
        self,
        error: FriendlyError,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize error dialog.

        Args:
            error: The friendly error to display
            parent: Parent widget
        """
        super().__init__(parent)

        self._error = error

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(self._error.title)
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)

        # Error display widget
        error_display = ErrorDisplay(self._error, self)
        error_display.retry_clicked.connect(self.retry_clicked.emit)
        error_display.dismissed.connect(self.accept)
        layout.addWidget(error_display)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)


def show_error(
    parent: Optional[QWidget],
    error: FriendlyError,
) -> ErrorDialog:
    """
    Show an error dialog.

    Args:
        parent: Parent widget
        error: The friendly error to display

    Returns:
        The dialog instance
    """
    dialog = ErrorDialog(error, parent)
    dialog.exec()
    return dialog


def show_warning(
    parent: Optional[QWidget],
    title: str,
    message: str,
    *,
    details: Optional[str] = None,
    suggestions: Optional[List[str]] = None,
) -> ErrorDialog:
    """
    Show a warning dialog.

    Args:
        parent: Parent widget
        title: Warning title
        message: Warning message
        details: Optional technical details
        suggestions: Optional suggestions

    Returns:
        The dialog instance
    """
    error = FriendlyError(
        title=title,
        message=message,
        severity=ErrorSeverity.WARNING,
        details=details,
        suggestions=suggestions or [],
    )
    return show_error(parent, error)


def show_info(
    parent: Optional[QWidget],
    title: str,
    message: str,
    *,
    auto_dismiss: bool = True,
) -> ErrorDialog:
    """
    Show an info dialog.

    Args:
        parent: Parent widget
        title: Info title
        message: Info message
        auto_dismiss: Whether to auto-dismiss

    Returns:
        The dialog instance
    """
    error = FriendlyError(
        title=title,
        message=message,
        severity=ErrorSeverity.INFO,
        auto_dismiss=auto_dismiss,
    )
    return show_error(parent, error)
