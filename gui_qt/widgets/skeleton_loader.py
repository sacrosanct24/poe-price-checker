"""
Skeleton Loader - Placeholder widgets for loading states.

Skeleton screens reduce perceived load time by showing the page structure
before content arrives. This follows Material Design 3 guidelines.

Usage:
    from gui_qt.widgets.skeleton_loader import (
        SkeletonText,
        SkeletonRect,
        SkeletonCircle,
        SkeletonTableRow,
        SkeletonCard,
    )

    # Show skeleton while loading
    skeleton = SkeletonCard()
    layout.addWidget(skeleton)

    # Replace with real content when ready
    skeleton.cross_fade_to(real_widget)
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPaintEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QGraphicsOpacityEffect,
)

from gui_qt.design_system import (
    Spacing,
    BorderRadius,
    Duration,
    get_animation_duration,
    AnimationPreset,
    should_reduce_motion,
)


class SkeletonBase(QWidget):
    """
    Base class for skeleton placeholder widgets.

    Provides shimmer animation and common styling.
    """

    # Class-level animation timer (shared across all skeletons)
    _shimmer_timer: Optional[QTimer] = None
    _shimmer_offset: float = 0.0
    _instances: list["SkeletonBase"] = []

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        animate: bool = True,
        color: str = "#3a3a45",
        highlight_color: str = "#4a4a55",
    ):
        """
        Initialize skeleton base.

        Args:
            parent: Parent widget
            animate: Whether to show shimmer animation
            color: Base skeleton color
            highlight_color: Shimmer highlight color
        """
        super().__init__(parent)

        self._animate = animate and not should_reduce_motion()
        self._base_color = QColor(color)
        self._highlight_color = QColor(highlight_color)

        # Register for shimmer updates
        if self._animate:
            SkeletonBase._instances.append(self)
            self._ensure_timer_running()

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def _ensure_timer_running(self) -> None:
        """Start the shared shimmer timer if not already running."""
        if SkeletonBase._shimmer_timer is None:
            SkeletonBase._shimmer_timer = QTimer()
            SkeletonBase._shimmer_timer.timeout.connect(SkeletonBase._update_shimmer)
            SkeletonBase._shimmer_timer.start(50)  # ~20 FPS

    @classmethod
    def _update_shimmer(cls) -> None:
        """Update shimmer animation offset."""
        # Complete one cycle in ~1.5 seconds (Duration.SKELETON)
        cls._shimmer_offset += 0.033  # ~50ms per frame
        if cls._shimmer_offset > 1.0:
            cls._shimmer_offset = 0.0

        # Update all instances
        for instance in cls._instances:
            if instance.isVisible():
                instance.update()

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        """Paint skeleton with optional shimmer."""
        if event is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        if self._animate:
            # Create shimmer gradient
            gradient = QLinearGradient(0, 0, rect.width(), 0)

            # Position shimmer based on offset
            shimmer_pos = SkeletonBase._shimmer_offset
            shimmer_width = 0.3

            gradient.setColorAt(0, self._base_color)
            gradient.setColorAt(max(0, shimmer_pos - shimmer_width), self._base_color)
            gradient.setColorAt(shimmer_pos, self._highlight_color)
            gradient.setColorAt(min(1, shimmer_pos + shimmer_width), self._base_color)
            gradient.setColorAt(1, self._base_color)

            painter.setBrush(gradient)
        else:
            painter.setBrush(self._base_color)

        painter.setPen(Qt.PenStyle.NoPen)
        self._paint_shape(painter, rect)

    def _paint_shape(self, painter: QPainter, rect) -> None:
        """Paint the skeleton shape. Override in subclasses."""
        painter.drawRoundedRect(rect, BorderRadius.SM, BorderRadius.SM)

    def cross_fade_to(
        self,
        target_widget: QWidget,
        duration: int | None = None,
    ) -> None:
        """
        Cross-fade from skeleton to target widget.

        Args:
            target_widget: Widget to fade in
            duration: Animation duration (uses default if None)
        """
        if should_reduce_motion():
            self.hide()
            target_widget.show()
            return

        duration = duration or get_animation_duration(AnimationPreset.FADE_IN)

        # Fade out skeleton
        skeleton_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(skeleton_effect)

        skeleton_anim = QPropertyAnimation(skeleton_effect, b"opacity")
        skeleton_anim.setDuration(duration)
        skeleton_anim.setStartValue(1.0)
        skeleton_anim.setEndValue(0.0)
        skeleton_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade in target
        target_effect = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(target_effect)
        target_widget.show()

        target_anim = QPropertyAnimation(target_effect, b"opacity")
        target_anim.setDuration(duration)
        target_anim.setStartValue(0.0)
        target_anim.setEndValue(1.0)
        target_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Hide skeleton when done
        skeleton_anim.finished.connect(self.hide)

        skeleton_anim.start()
        target_anim.start()

        # Store references to prevent garbage collection
        self._fade_out_anim = skeleton_anim
        self._target_fade_anim = target_anim

    def hideEvent(self, event) -> None:
        """Clean up when hidden."""
        super().hideEvent(event)
        if self in SkeletonBase._instances:
            SkeletonBase._instances.remove(self)

    def showEvent(self, event) -> None:
        """Re-register when shown."""
        super().showEvent(event)
        if self._animate and self not in SkeletonBase._instances:
            SkeletonBase._instances.append(self)
            self._ensure_timer_running()


class SkeletonText(SkeletonBase):
    """
    Skeleton placeholder for text lines.

    Renders as a rounded rectangle with configurable width.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        width: int | None = None,
        height: int = 16,
        width_percent: float = 1.0,
        **kwargs,
    ):
        """
        Initialize text skeleton.

        Args:
            parent: Parent widget
            width: Fixed width (pixels)
            height: Height (pixels)
            width_percent: Width as percentage of parent (0.0-1.0)
        """
        super().__init__(parent, **kwargs)

        self._width_percent = width_percent

        if width:
            self.setFixedSize(width, height)
        else:
            self.setFixedHeight(height)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _paint_shape(self, painter: QPainter, rect) -> None:
        """Paint text skeleton as rounded rect."""
        if self._width_percent < 1.0:
            rect.setWidth(int(rect.width() * self._width_percent))
        painter.drawRoundedRect(rect, BorderRadius.XS, BorderRadius.XS)


class SkeletonRect(SkeletonBase):
    """
    Skeleton placeholder for rectangular content.

    Use for images, cards, or any rectangular area.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        width: int | None = None,
        height: int | None = None,
        radius: int = BorderRadius.SM,
        **kwargs,
    ):
        """
        Initialize rect skeleton.

        Args:
            parent: Parent widget
            width: Fixed width (pixels)
            height: Fixed height (pixels)
            radius: Border radius
        """
        super().__init__(parent, **kwargs)

        self._radius = radius

        if width and height:
            self.setFixedSize(width, height)
        elif width:
            self.setFixedWidth(width)
        elif height:
            self.setFixedHeight(height)

    def _paint_shape(self, painter: QPainter, rect) -> None:
        """Paint rectangular skeleton."""
        painter.drawRoundedRect(rect, self._radius, self._radius)


class SkeletonCircle(SkeletonBase):
    """
    Skeleton placeholder for circular content.

    Use for avatars, icons, or circular buttons.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        diameter: int = 40,
        **kwargs,
    ):
        """
        Initialize circle skeleton.

        Args:
            parent: Parent widget
            diameter: Circle diameter (pixels)
        """
        super().__init__(parent, **kwargs)
        self.setFixedSize(diameter, diameter)

    def _paint_shape(self, painter: QPainter, rect) -> None:
        """Paint circular skeleton."""
        painter.drawEllipse(rect)


class SkeletonTableRow(QWidget):
    """
    Skeleton placeholder for a table row.

    Renders multiple columns with appropriate spacing.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        columns: int = 4,
        height: int = 32,
        column_widths: list[float] | None = None,
        **kwargs,
    ):
        """
        Initialize table row skeleton.

        Args:
            parent: Parent widget
            columns: Number of columns
            height: Row height
            column_widths: Relative widths (e.g., [0.3, 0.2, 0.3, 0.2])
        """
        super().__init__(parent)

        self.setFixedHeight(height)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        if column_widths is None:
            column_widths = [1.0 / columns] * columns

        for i, width in enumerate(column_widths):
            col = SkeletonText(height=height - Spacing.SM, width_percent=0.8, **kwargs)
            layout.addWidget(col, int(width * 100))


class SkeletonCard(QWidget):
    """
    Skeleton placeholder for a card/panel.

    Renders a card-like structure with title, subtitle, and content area.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        show_image: bool = False,
        show_title: bool = True,
        show_subtitle: bool = True,
        show_content: bool = True,
        content_lines: int = 3,
        **kwargs,
    ):
        """
        Initialize card skeleton.

        Args:
            parent: Parent widget
            show_image: Show image placeholder
            show_title: Show title placeholder
            show_subtitle: Show subtitle placeholder
            show_content: Show content lines
            content_lines: Number of content lines
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        if show_image:
            image = SkeletonRect(height=120, radius=BorderRadius.MD, **kwargs)
            layout.addWidget(image)

        if show_title:
            title = SkeletonText(height=20, width_percent=0.7, **kwargs)
            layout.addWidget(title)

        if show_subtitle:
            subtitle = SkeletonText(height=14, width_percent=0.5, **kwargs)
            layout.addWidget(subtitle)

        if show_content:
            for i in range(content_lines):
                # Vary line lengths for natural look
                percent = 1.0 if i < content_lines - 1 else 0.6
                line = SkeletonText(height=14, width_percent=percent, **kwargs)
                layout.addWidget(line)

        layout.addStretch()


class SkeletonResultsTable(QWidget):
    """
    Skeleton placeholder for the results table.

    Renders header row + multiple data rows.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        rows: int = 5,
        columns: int = 5,
        **kwargs,
    ):
        """
        Initialize results table skeleton.

        Args:
            parent: Parent widget
            rows: Number of data rows
            columns: Number of columns
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)  # 1px gap between rows

        # Header row (slightly different styling)
        header = SkeletonTableRow(
            columns=columns,
            height=36,
            color="#404050",
            highlight_color="#505060",
            **kwargs,
        )
        layout.addWidget(header)

        # Data rows
        for i in range(rows):
            row = SkeletonTableRow(columns=columns, height=32, **kwargs)
            layout.addWidget(row)

        layout.addStretch()


class SkeletonItemInspector(QWidget):
    """
    Skeleton placeholder for the item inspector panel.

    Renders item name, stats, and mod lines.
    """

    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        """Initialize item inspector skeleton."""
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Item name (larger)
        name = SkeletonText(height=24, width_percent=0.8, **kwargs)
        layout.addWidget(name)

        # Base type
        base = SkeletonText(height=16, width_percent=0.5, **kwargs)
        layout.addWidget(base)

        layout.addSpacing(Spacing.SM)

        # Separator line
        sep = SkeletonRect(height=1, **kwargs)
        layout.addWidget(sep)

        layout.addSpacing(Spacing.SM)

        # Mod lines
        for i in range(6):
            mod = SkeletonText(height=14, width_percent=0.7 + (i % 3) * 0.1, **kwargs)
            layout.addWidget(mod)

        layout.addStretch()
