"""
Rate Limit Indicator - Visual rate limit status indicator.

Provides a widget to display API rate limit status, cooldown
timers, and request queue status.

Usage:
    from gui_qt.feedback.rate_limit_indicator import (
        RateLimitIndicator,
        RateLimitStatus,
    )

    # Create indicator
    indicator = RateLimitIndicator()
    status_bar.addWidget(indicator)

    # Update status
    indicator.set_status(RateLimitStatus.COOLING_DOWN, remaining_seconds=30)
    indicator.set_queue_size(3)
"""

from enum import Enum
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
    QProgressBar,
)

from gui_qt.styles import COLORS
from gui_qt.design_system import (
    Spacing,
    BorderRadius,
    FontSize,
)


class RateLimitStatus(Enum):
    """Rate limit status states."""
    READY = "ready"           # Can make requests immediately
    ACTIVE = "active"         # Request in progress
    COOLING_DOWN = "cooling"  # Waiting for cooldown
    RATE_LIMITED = "limited"  # Hit rate limit, longer wait


STATUS_CONFIGS = {
    RateLimitStatus.READY: {
        "icon": "\u2713",  # Checkmark
        "color": "#4CAF50",
        "label": "Ready",
        "tooltip": "Ready to make API requests",
    },
    RateLimitStatus.ACTIVE: {
        "icon": "\u27F3",  # Circular arrow
        "color": "#2196F3",
        "label": "Working...",
        "tooltip": "Request in progress",
    },
    RateLimitStatus.COOLING_DOWN: {
        "icon": "\u23F1",  # Stopwatch
        "color": "#FF9800",
        "label": "Cooling down...",
        "tooltip": "Waiting for rate limit cooldown",
    },
    RateLimitStatus.RATE_LIMITED: {
        "icon": "\u26A0",  # Warning
        "color": "#F44336",
        "label": "Rate limited",
        "tooltip": "Rate limit reached, please wait",
    },
}


class CooldownProgressBar(QProgressBar):
    """
    Custom progress bar for cooldown visualization.

    Shows remaining cooldown time with smooth animation.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize cooldown progress bar."""
        super().__init__(parent)

        self.setFixedHeight(4)
        self.setTextVisible(False)
        self.setRange(0, 100)
        self.setValue(100)

        self._apply_style()

    def _apply_style(self) -> None:
        """Apply progress bar styling."""
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['surface_variant']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 2px;
            }}
        """)

    def set_color(self, color: str) -> None:
        """Set the progress bar color."""
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['surface_variant']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)


class RateLimitIndicator(QFrame):
    """
    Visual indicator for API rate limit status.

    Shows current status, cooldown progress, and request queue size.
    """

    status_changed = pyqtSignal(RateLimitStatus)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize rate limit indicator."""
        super().__init__(parent)

        self._status = RateLimitStatus.READY
        self._remaining_seconds = 0
        self._total_seconds = 0
        self._queue_size = 0

        self._timer: Optional[QTimer] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the indicator UI."""
        self.setObjectName("rateLimitIndicator")
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, 2, Spacing.SM, 2)
        layout.setSpacing(Spacing.XS)

        # Status icon
        self._icon_label = QLabel()
        self._icon_label.setObjectName("statusIcon")
        self._icon_label.setFixedWidth(16)
        layout.addWidget(self._icon_label)

        # Status/time label
        self._status_label = QLabel()
        self._status_label.setObjectName("statusLabel")
        self._status_label.setMinimumWidth(80)
        layout.addWidget(self._status_label)

        # Progress bar (for cooldown)
        self._progress = CooldownProgressBar()
        self._progress.setFixedWidth(60)
        self._progress.hide()
        layout.addWidget(self._progress)

        # Queue indicator
        self._queue_label = QLabel()
        self._queue_label.setObjectName("queueLabel")
        self._queue_label.hide()
        layout.addWidget(self._queue_label)

        # Initial state
        self._update_display()
        self._apply_style()

    def _apply_style(self) -> None:
        """Apply indicator styling."""
        config = STATUS_CONFIGS[self._status]
        color = config["color"]

        self.setStyleSheet(f"""
            QFrame#rateLimitIndicator {{
                background-color: {color}1A;
                border: 1px solid {color}40;
                border-radius: {BorderRadius.SM}px;
            }}
            QLabel#statusIcon {{
                color: {color};
                font-size: 12px;
            }}
            QLabel#statusLabel {{
                color: {COLORS['text']};
                font-size: {FontSize.XS}px;
            }}
            QLabel#queueLabel {{
                color: {COLORS['text_secondary']};
                font-size: {FontSize.XS}px;
                padding-left: {Spacing.XS}px;
            }}
        """)

        self._progress.set_color(color)

    def _update_display(self) -> None:
        """Update the display based on current status."""
        config = STATUS_CONFIGS[self._status]

        # Update icon
        self._icon_label.setText(config["icon"])

        # Update label
        if self._status in (RateLimitStatus.COOLING_DOWN, RateLimitStatus.RATE_LIMITED):
            if self._remaining_seconds > 0:
                self._status_label.setText(f"{self._remaining_seconds}s")
            else:
                self._status_label.setText(config["label"])
        else:
            self._status_label.setText(config["label"])

        # Update tooltip
        tooltip = config["tooltip"]
        if self._queue_size > 0:
            tooltip += f"\n{self._queue_size} request(s) queued"
        self.setToolTip(tooltip)

        # Show/hide progress bar
        show_progress = self._status in (
            RateLimitStatus.COOLING_DOWN,
            RateLimitStatus.RATE_LIMITED,
        ) and self._total_seconds > 0
        self._progress.setVisible(show_progress)

        if show_progress:
            progress = int((self._remaining_seconds / self._total_seconds) * 100)
            self._progress.setValue(progress)

        # Show/hide queue indicator
        self._queue_label.setVisible(self._queue_size > 0)
        if self._queue_size > 0:
            self._queue_label.setText(f"({self._queue_size} queued)")

        # Update style for current status
        self._apply_style()

    def set_status(
        self,
        status: RateLimitStatus,
        *,
        remaining_seconds: int = 0,
        total_seconds: int = 0,
    ) -> None:
        """
        Set the current rate limit status.

        Args:
            status: New status
            remaining_seconds: Remaining cooldown time
            total_seconds: Total cooldown time (for progress calculation)
        """
        old_status = self._status
        self._status = status
        self._remaining_seconds = remaining_seconds
        self._total_seconds = total_seconds or remaining_seconds

        self._update_display()

        # Start countdown timer if cooling down
        if status in (RateLimitStatus.COOLING_DOWN, RateLimitStatus.RATE_LIMITED):
            self._start_countdown()
        else:
            self._stop_countdown()

        if old_status != status:
            self.status_changed.emit(status)

    def _start_countdown(self) -> None:
        """Start countdown timer."""
        self._stop_countdown()

        if self._remaining_seconds <= 0:
            return

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_countdown_tick)
        self._timer.start(1000)  # 1 second interval

    def _stop_countdown(self) -> None:
        """Stop countdown timer."""
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _on_countdown_tick(self) -> None:
        """Handle countdown tick."""
        self._remaining_seconds -= 1

        if self._remaining_seconds <= 0:
            self._stop_countdown()
            self.set_status(RateLimitStatus.READY)
        else:
            self._update_display()

    def set_queue_size(self, size: int) -> None:
        """
        Set the request queue size.

        Args:
            size: Number of queued requests
        """
        self._queue_size = size
        self._update_display()

    def status(self) -> RateLimitStatus:
        """Get the current status."""
        return self._status

    def is_ready(self) -> bool:
        """Check if ready to make requests."""
        return self._status == RateLimitStatus.READY


class DetailedRateLimitDisplay(QFrame):
    """
    Detailed rate limit display for settings/status panels.

    Shows more detailed information about rate limits
    including per-API breakdowns and history.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize detailed display."""
        super().__init__(parent)

        self._api_limits: dict[str, dict] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the display UI."""
        self.setObjectName("detailedRateLimitDisplay")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Header
        header = QLabel("API Rate Limits")
        header.setStyleSheet(f"""
            font-size: {FontSize.BASE}px;
            font-weight: 600;
            color: {COLORS['text']};
        """)
        layout.addWidget(header)

        # API limits container
        self._limits_container = QWidget()
        self._limits_layout = QVBoxLayout(self._limits_container)
        self._limits_layout.setContentsMargins(0, 0, 0, 0)
        self._limits_layout.setSpacing(Spacing.XS)
        layout.addWidget(self._limits_container)

        # No data label (shown when empty)
        self._no_data_label = QLabel("No rate limit data available")
        self._no_data_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: {FontSize.SM}px;
            padding: {Spacing.MD}px;
        """)
        self._no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._no_data_label)

        self.setStyleSheet(f"""
            QFrame#detailedRateLimitDisplay {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {BorderRadius.MD}px;
            }}
        """)

    def set_api_limits(self, limits: dict[str, dict]) -> None:
        """
        Set API rate limit information.

        Args:
            limits: Dictionary mapping API name to limit info
                   e.g., {"poe.ninja": {"remaining": 50, "total": 100, "reset_at": "..."}}
        """
        self._api_limits = limits

        # Clear existing
        while self._limits_layout.count():
            item = self._limits_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Show/hide no data label
        self._no_data_label.setVisible(len(limits) == 0)

        # Add API rows
        for api_name, info in limits.items():
            row = self._create_api_row(api_name, info)
            self._limits_layout.addWidget(row)

    def _create_api_row(self, api_name: str, info: dict) -> QWidget:
        """Create a row for an API's rate limit info."""
        row = QFrame()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        row_layout.setSpacing(Spacing.SM)

        # API name
        name_label = QLabel(api_name)
        name_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-size: {FontSize.SM}px;
        """)
        name_label.setFixedWidth(100)
        row_layout.addWidget(name_label)

        # Progress bar
        progress = QProgressBar()
        progress.setFixedHeight(8)
        progress.setTextVisible(False)

        remaining = info.get("remaining", 0)
        total = info.get("total", 100)
        progress.setRange(0, total)
        progress.setValue(remaining)

        # Color based on remaining
        pct = remaining / total if total > 0 else 0
        if pct > 0.5:
            color = "#4CAF50"
        elif pct > 0.2:
            color = "#FF9800"
        else:
            color = "#F44336"

        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['surface_variant']};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        row_layout.addWidget(progress)

        # Count label
        count_label = QLabel(f"{remaining}/{total}")
        count_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FontSize.XS}px;
        """)
        count_label.setFixedWidth(60)
        row_layout.addWidget(count_label)

        return row
