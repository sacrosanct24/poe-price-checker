"""
Progress Indicators - Circular and linear progress widgets.

Provides Material Design 3 style progress indicators with determinate
and indeterminate states, supporting accessibility requirements.

Usage:
    from gui_qt.widgets.progress_indicator import (
        CircularProgress,
        LinearProgress,
        SmartLoadingIndicator,
    )

    # Indeterminate (spinning)
    spinner = CircularProgress()
    spinner.start()

    # Determinate (percentage)
    progress = LinearProgress()
    progress.set_progress(0.75)  # 75%

    # Smart loading (appears after delay)
    loader = SmartLoadingIndicator("Loading prices...")
    loader.start()
"""

from typing import Optional

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRectF,
)
from PyQt6.QtCore import pyqtProperty  # type: ignore[import-not-found,attr-defined]
from PyQt6.QtGui import QPainter, QColor, QPen, QPaintEvent, QConicalGradient
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QGraphicsOpacityEffect,
)

from gui_qt.design_system import (
    Spacing,
    Duration,
    BorderRadius,
    get_animation_duration,
    AnimationPreset,
    should_reduce_motion,
)


class CircularProgress(QWidget):
    """
    Circular progress indicator.

    Supports both determinate (percentage) and indeterminate (spinning) modes.
    Follows Material Design 3 specifications.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        size: int = 40,
        stroke_width: int = 4,
        color: str = "#8b5cf6",
        track_color: str = "#3a3a45",
        determinate: bool = False,
    ):
        """
        Initialize circular progress.

        Args:
            parent: Parent widget
            size: Diameter in pixels
            stroke_width: Line thickness
            color: Progress color (hex)
            track_color: Background track color (hex)
            determinate: If True, shows percentage; if False, spins
        """
        super().__init__(parent)

        self._size = size
        self._stroke_width = stroke_width
        self._color = QColor(color)
        self._track_color = QColor(track_color)
        self._determinate = determinate
        self._progress = 0.0  # 0.0 to 1.0
        self._rotation = 0.0  # For indeterminate animation

        self.setFixedSize(size, size)

        # Animation for indeterminate mode
        self._spin_timer: Optional[QTimer] = None
        self._spin_animation: Optional[QPropertyAnimation] = None

        # Accessibility
        self.setAccessibleName("Progress indicator")
        self.setAccessibleDescription("Loading in progress")

    def _get_rotation(self) -> float:
        return self._rotation

    def _set_rotation(self, value: float) -> None:
        self._rotation = value
        self.update()

    rotation = pyqtProperty(float, _get_rotation, _set_rotation)

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, value))
        self.update()

    progress = pyqtProperty(float, _get_progress, _set_progress)

    def set_progress(self, value: float) -> None:
        """
        Set progress value (0.0 to 1.0).

        Args:
            value: Progress percentage (0.0 = 0%, 1.0 = 100%)
        """
        self._set_progress(value)
        self.setAccessibleDescription(f"Progress: {int(value * 100)}%")

    def start(self) -> None:
        """Start the progress animation (indeterminate mode)."""
        if self._determinate:
            return

        if should_reduce_motion():
            # Just show static arc for reduced motion
            self._rotation = 0
            self.update()
            return

        # Create smooth rotation animation
        self._spin_animation = QPropertyAnimation(self, b"rotation")
        self._spin_animation.setDuration(Duration.SKELETON)
        self._spin_animation.setStartValue(0.0)
        self._spin_animation.setEndValue(360.0)
        self._spin_animation.setLoopCount(-1)  # Infinite
        self._spin_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._spin_animation.start()

    def stop(self) -> None:
        """Stop the progress animation."""
        if self._spin_animation:
            self._spin_animation.stop()
            self._spin_animation = None

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the circular progress."""
        if event is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate drawing area (account for stroke width)
        margin = self._stroke_width / 2
        rect = QRectF(
            margin,
            margin,
            self._size - self._stroke_width,
            self._size - self._stroke_width,
        )

        # Draw track (background circle)
        track_pen = QPen(self._track_color, self._stroke_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Draw progress arc
        progress_pen = QPen(self._color, self._stroke_width)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)

        if self._determinate:
            # Determinate: draw arc based on progress
            span_angle = int(-self._progress * 360 * 16)  # Qt uses 1/16 degree
            start_angle = 90 * 16  # Start from top
            painter.drawArc(rect, start_angle, span_angle)
        else:
            # Indeterminate: draw rotating arc segment
            painter.translate(self._size / 2, self._size / 2)
            painter.rotate(self._rotation)
            painter.translate(-self._size / 2, -self._size / 2)

            # Draw 270-degree arc (3/4 circle)
            span_angle = -270 * 16
            start_angle = 90 * 16
            painter.drawArc(rect, start_angle, span_angle)

    def hideEvent(self, event) -> None:
        """Stop animation when hidden."""
        super().hideEvent(event)
        self.stop()

    def showEvent(self, event) -> None:
        """Restart animation when shown."""
        super().showEvent(event)
        if not self._determinate:
            self.start()


class LinearProgress(QWidget):
    """
    Linear progress bar.

    Supports both determinate and indeterminate modes with smooth animations.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        height: int = 4,
        color: str = "#8b5cf6",
        track_color: str = "#3a3a45",
        determinate: bool = True,
        rounded: bool = True,
    ):
        """
        Initialize linear progress.

        Args:
            parent: Parent widget
            height: Bar height in pixels
            color: Progress color (hex)
            track_color: Background track color (hex)
            determinate: If True, shows percentage; if False, animates
            rounded: If True, use rounded caps
        """
        super().__init__(parent)

        self._height = height
        self._color = QColor(color)
        self._track_color = QColor(track_color)
        self._determinate = determinate
        self._rounded = rounded
        self._progress = 0.0
        self._indeterminate_pos = 0.0

        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._animation: Optional[QPropertyAnimation] = None

        # Accessibility
        self.setAccessibleName("Progress bar")

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, value))
        self.update()

    progress = pyqtProperty(float, _get_progress, _set_progress)

    def _get_indeterminate_pos(self) -> float:
        return self._indeterminate_pos

    def _set_indeterminate_pos(self, value: float) -> None:
        self._indeterminate_pos = value
        self.update()

    indeterminate_pos = pyqtProperty(float, _get_indeterminate_pos, _set_indeterminate_pos)

    def set_progress(self, value: float, animate: bool = True) -> None:
        """
        Set progress value with optional animation.

        Args:
            value: Progress percentage (0.0 to 1.0)
            animate: Whether to animate the transition
        """
        if animate and not should_reduce_motion():
            if self._animation:
                self._animation.stop()

            self._animation = QPropertyAnimation(self, b"progress")
            self._animation.setDuration(Duration.NORMAL)
            self._animation.setStartValue(self._progress)
            self._animation.setEndValue(value)
            self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation.start()
        else:
            self._set_progress(value)

        self.setAccessibleDescription(f"Progress: {int(value * 100)}%")

    def start(self) -> None:
        """Start indeterminate animation."""
        if self._determinate:
            return

        if should_reduce_motion():
            self._indeterminate_pos = 0.3
            self.update()
            return

        self._animation = QPropertyAnimation(self, b"indeterminate_pos")
        self._animation.setDuration(Duration.SKELETON)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._animation.start()

    def stop(self) -> None:
        """Stop indeterminate animation."""
        if self._animation:
            self._animation.stop()
            self._animation = None

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint the linear progress bar."""
        if event is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self._height
        radius = height / 2 if self._rounded else 0

        # Draw track
        painter.setBrush(self._track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, width, height, radius, radius)

        # Draw progress
        painter.setBrush(self._color)

        if self._determinate:
            progress_width = int(width * self._progress)
            if progress_width > 0:
                painter.drawRoundedRect(0, 0, progress_width, height, radius, radius)
        else:
            # Indeterminate: sliding segment
            segment_width = int(width * 0.3)
            pos = int((width + segment_width) * self._indeterminate_pos - segment_width)
            painter.drawRoundedRect(pos, 0, segment_width, height, radius, radius)

    def hideEvent(self, event) -> None:
        """Stop animation when hidden."""
        super().hideEvent(event)
        self.stop()


class SmartLoadingIndicator(QWidget):
    """
    Smart loading indicator that appears after a delay.

    Prevents flicker for fast operations by only showing after 300ms.
    Includes spinner, message, and optional progress percentage.
    """

    # Delay before showing (prevents flicker for fast operations)
    SHOW_DELAY_MS = 300

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        message: str = "Loading...",
        show_spinner: bool = True,
        show_progress: bool = False,
    ):
        """
        Initialize smart loading indicator.

        Args:
            parent: Parent widget
            message: Loading message to display
            show_spinner: Whether to show circular spinner
            show_progress: Whether to show progress percentage
        """
        super().__init__(parent)

        self._message = message
        self._show_progress = show_progress
        self._progress = 0.0
        self._show_delay_timer: Optional[QTimer] = None

        # Declare optional widgets
        self._spinner: Optional[CircularProgress] = None
        self._progress_label: Optional[QLabel] = None

        # Initially hidden
        self.hide()

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Spinner
        if show_spinner:
            self._spinner = CircularProgress(size=24, stroke_width=3)
            layout.addWidget(self._spinner)

        # Message label
        self._label = QLabel(message)
        self._label.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        layout.addWidget(self._label)

        # Progress percentage
        if show_progress:
            self._progress_label = QLabel("0%")
            self._progress_label.setStyleSheet("color: #8b5cf6; font-size: 13px; font-weight: 500;")
            layout.addWidget(self._progress_label)

        layout.addStretch()

        # Fade-in effect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_animation: Optional[QPropertyAnimation] = None

    def set_message(self, message: str) -> None:
        """Update the loading message."""
        self._message = message
        self._label.setText(message)

    def set_progress(self, value: float) -> None:
        """
        Update progress percentage.

        Args:
            value: Progress (0.0 to 1.0)
        """
        self._progress = value
        if self._progress_label:
            self._progress_label.setText(f"{int(value * 100)}%")

    def start(self) -> None:
        """
        Start the loading indicator.

        The indicator will appear after SHOW_DELAY_MS to prevent flicker.
        """
        # Cancel any existing timer
        if self._show_delay_timer:
            self._show_delay_timer.stop()

        # Start delay timer
        self._show_delay_timer = QTimer()
        self._show_delay_timer.setSingleShot(True)
        self._show_delay_timer.timeout.connect(self._show_with_animation)
        self._show_delay_timer.start(self.SHOW_DELAY_MS)

    def stop(self) -> None:
        """Stop and hide the loading indicator."""
        # Cancel show timer if pending
        if self._show_delay_timer:
            self._show_delay_timer.stop()
            self._show_delay_timer = None

        # Stop spinner
        if self._spinner:
            self._spinner.stop()

        # Hide with animation
        if self.isVisible() and not should_reduce_motion():
            self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
            self._fade_animation.setDuration(Duration.FAST)
            self._fade_animation.setStartValue(1.0)
            self._fade_animation.setEndValue(0.0)
            self._fade_animation.finished.connect(self.hide)
            self._fade_animation.start()
        else:
            self.hide()

    def _show_with_animation(self) -> None:
        """Show the indicator with fade-in animation."""
        if should_reduce_motion():
            self._opacity_effect.setOpacity(1.0)
            self.show()
        else:
            self._opacity_effect.setOpacity(0.0)
            self.show()

            self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
            self._fade_animation.setDuration(Duration.FAST)
            self._fade_animation.setStartValue(0.0)
            self._fade_animation.setEndValue(1.0)
            self._fade_animation.start()

        # Start spinner
        if self._spinner:
            self._spinner.start()


class LoadingOverlay(QWidget):
    """
    Semi-transparent overlay with loading indicator.

    Use to block interaction during long operations.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        message: str = "Please wait...",
        background_color: str = "rgba(0, 0, 0, 0.5)",
    ):
        """
        Initialize loading overlay.

        Args:
            parent: Widget to overlay
            message: Loading message
            background_color: Overlay background (supports alpha)
        """
        super().__init__(parent)

        self._background_color = background_color
        self.hide()

        # Fill parent
        if parent:
            self.setGeometry(parent.rect())

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Center layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Container for spinner and message
        container = QWidget()
        container.setStyleSheet(f"""
            background-color: #1e1e2e;
            border-radius: {BorderRadius.MD}px;
            padding: {Spacing.LG}px;
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setSpacing(Spacing.MD)

        # Spinner
        spinner = CircularProgress(size=48, stroke_width=4)
        spinner.start()
        container_layout.addWidget(spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        # Message
        label = QLabel(message)
        label.setStyleSheet("color: #e4e4e7; font-size: 14px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(label)

        layout.addWidget(container)

        # Store for later access
        self._spinner = spinner
        self._label = label

    def set_message(self, message: str) -> None:
        """Update the overlay message."""
        self._label.setText(message)

    def show_overlay(self) -> None:
        """Show the overlay with animation."""
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            self.setGeometry(parent.rect())

        self.raise_()
        self.show()
        self._spinner.start()

    def hide_overlay(self) -> None:
        """Hide the overlay."""
        self._spinner.stop()
        self.hide()

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint semi-transparent background."""
        if event is None:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))

    def resizeEvent(self, event) -> None:
        """Resize with parent."""
        super().resizeEvent(event)
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            self.setGeometry(parent.rect())
