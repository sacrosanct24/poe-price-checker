"""
gui_qt.widgets.loading_screen

Loading screen displayed during application startup.
Prevents user interaction until initialization is complete.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QApplication,
)

from gui_qt.styles import COLORS

logger = logging.getLogger(__name__)


class LoadingScreen(QWidget):
    """
    Loading screen widget displayed during application startup.

    Shows a progress bar and status message while the application
    initializes. Blocks interaction with other windows until complete.

    Signals:
        loading_complete: Emitted when loading is finished.

    Example:
        loading = LoadingScreen()
        loading.show()
        loading.set_status("Loading configuration...")
        loading.set_progress(25)
        # ... do work ...
        loading.finish()
    """

    loading_complete = pyqtSignal()

    # Loading steps with their progress percentages
    LOADING_STEPS = [
        ("Initializing configuration...", 5),
        ("Connecting to database...", 15),
        ("Setting up pricing services...", 30),
        ("Initializing poe.ninja API...", 45),
        ("Initializing poe.watch API...", 55),
        ("Setting up item parser...", 65),
        ("Loading rare item evaluator...", 75),
        ("Creating main window...", 85),
        ("Finalizing setup...", 95),
        ("Ready!", 100),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_step = 0

        # Window setup - frameless, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Fixed size
        self.setFixedSize(450, 200)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Create the loading screen UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)

        # App icon (if available)
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(48, 48)
        title_layout.addWidget(self._icon_label)

        # Title text
        self._title_label = QLabel("PoE Price Checker")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Status message
        self._status_label = QLabel("Starting...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(10)
        self._status_label.setFont(status_font)
        layout.addWidget(self._status_label)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        layout.addWidget(self._progress_bar)

        # Version info
        self._version_label = QLabel("Loading...")
        self._version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_font = QFont()
        version_font.setPointSize(8)
        self._version_label.setFont(version_font)
        layout.addWidget(self._version_label)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply dark theme styling."""
        self.setStyleSheet(f"""
            LoadingScreen {{
                background-color: {COLORS["surface"]};
                border: 2px solid {COLORS["accent"]};
                border-radius: 10px;
            }}
            QLabel {{
                color: {COLORS["text"]};
                background: transparent;
            }}
            QProgressBar {{
                border: 1px solid {COLORS["border"]};
                border-radius: 5px;
                background-color: {COLORS["background"]};
                text-align: center;
                color: {COLORS["text"]};
                height: 25px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS["accent"]};
                border-radius: 4px;
            }}
        """)

    def set_icon(self, icon: QIcon) -> None:
        """Set the application icon.

        Args:
            icon: QIcon to display.
        """
        pixmap = icon.pixmap(48, 48)
        self._icon_label.setPixmap(pixmap)

    def set_version(self, version: str) -> None:
        """Set the version text.

        Args:
            version: Version string to display.
        """
        self._version_label.setText(f"Version {version}")

    def set_status(self, message: str) -> None:
        """Set the status message.

        Args:
            message: Status message to display.
        """
        self._status_label.setText(message)
        # Process events to update UI immediately
        QApplication.processEvents()

    def set_progress(self, value: int) -> None:
        """Set the progress bar value.

        Args:
            value: Progress percentage (0-100).
        """
        self._progress_bar.setValue(min(100, max(0, value)))
        QApplication.processEvents()

    def advance_step(self) -> None:
        """Advance to the next loading step."""
        if self._current_step < len(self.LOADING_STEPS):
            message, progress = self.LOADING_STEPS[self._current_step]
            self.set_status(message)
            self.set_progress(progress)
            self._current_step += 1

    def finish(self) -> None:
        """Complete loading and emit signal."""
        self.set_status("Ready!")
        self.set_progress(100)
        self.loading_complete.emit()
        # Small delay before hiding
        QTimer.singleShot(200, self.close)

    def center_on_screen(self) -> None:
        """Center the loading screen on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(screen_geometry.x() + x, screen_geometry.y() + y)

    def showEvent(self, event) -> None:
        """Handle show event to center on screen."""
        super().showEvent(event)
        self.center_on_screen()


class LoadingOverlay(QWidget):
    """
    Semi-transparent overlay for blocking interaction during loading.

    Can be placed over the main window to prevent clicks while
    background initialization continues.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the overlay UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Loading message
        self._message_label = QLabel("Loading...")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        self._message_label.setFont(font)
        self._message_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS["text"]};
                background-color: rgba(30, 30, 35, 200);
                padding: 20px 40px;
                border-radius: 10px;
            }}
        """)
        layout.addWidget(self._message_label)

        # Progress indicator
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(0)  # Indeterminate
        self._progress_bar.setFixedWidth(200)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS["border"]};
                border-radius: 5px;
                background-color: {COLORS["background"]};
                height: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS["accent"]};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self._progress_bar)

    def set_message(self, message: str) -> None:
        """Set the loading message."""
        self._message_label.setText(message)

    def paintEvent(self, event) -> None:
        """Paint semi-transparent background."""
        from PyQt6.QtGui import QPainter, QColor as QC

        painter = QPainter(self)
        painter.fillRect(self.rect(), QC(0, 0, 0, 128))
        super().paintEvent(event)
