"""
Feature Spotlight - Contextual feature discovery tooltips.

Highlights specific UI elements with explanatory tooltips to help
users discover features they might have missed.

Usage:
    from gui_qt.onboarding.feature_spotlight import (
        FeatureSpotlight,
        show_feature_tip,
    )

    # Show a spotlight on a specific widget
    spotlight = FeatureSpotlight(
        target=my_button,
        title="New Feature!",
        description="Click here to do something awesome",
    )
    spotlight.show()

    # Or use the convenience function
    show_feature_tip(
        widget,
        "Quick Tip",
        "Press Ctrl+V to check prices",
        position=TipPosition.BOTTOM,
    )
"""

from enum import Enum
from typing import Optional, Callable, cast
from weakref import ref

from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen, QBrush, QRegion
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QApplication,
    QGraphicsOpacityEffect,
)

from gui_qt.design_system import (
    Spacing,
    BorderRadius,
    Duration,
    should_reduce_motion,
)


class TipPosition(Enum):
    """Position for the tooltip relative to target."""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    AUTO = "auto"  # Automatically choose best position


class FeatureSpotlight(QWidget):
    """
    Feature spotlight overlay.

    Highlights a target widget with a tooltip and optional overlay.
    """

    def __init__(
        self,
        target: QWidget,
        title: str,
        description: str,
        *,
        position: TipPosition = TipPosition.AUTO,
        show_overlay: bool = True,
        show_dismiss: bool = True,
        on_dismiss: Optional[Callable[[], None]] = None,
        on_action: Optional[Callable[[], None]] = None,
        action_text: str = "",
    ):
        """
        Initialize feature spotlight.

        Args:
            target: Widget to highlight
            title: Tooltip title
            description: Tooltip description
            position: Where to place tooltip relative to target
            show_overlay: Whether to show semi-transparent overlay
            show_dismiss: Whether to show dismiss button
            on_dismiss: Callback when dismissed
            on_action: Callback for action button
            action_text: Text for action button (if on_action provided)
        """
        # Use the target's window as parent
        parent = target.window()
        super().__init__(parent)

        self._target = ref(target)
        self._title = title
        self._description = description
        self._position = position
        self._show_overlay = show_overlay
        self._on_dismiss = on_dismiss
        self._on_action = on_action

        # Fill parent window
        if parent:
            self.setGeometry(parent.rect())

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Create tooltip widget
        self._tooltip = self._create_tooltip(
            title, description, show_dismiss, action_text
        )

        # Position tooltip
        self._position_tooltip()

        # Hide initially for animation
        self.hide()

    def _create_tooltip(
        self,
        title: str,
        description: str,
        show_dismiss: bool,
        action_text: str,
    ) -> QWidget:
        """Create the tooltip widget."""
        tooltip = QWidget(self)
        tooltip.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a35;
                border: 1px solid #4a4a55;
                border-radius: {BorderRadius.MD}px;
            }}
        """)

        layout = QVBoxLayout(tooltip)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 15px;
            font-weight: 600;
            color: #e4e4e7;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            font-size: 13px;
            color: #a1a1aa;
            background: transparent;
            border: none;
        """)
        layout.addWidget(desc_label)

        # Buttons
        if show_dismiss or self._on_action:
            button_layout = QHBoxLayout()
            button_layout.setSpacing(Spacing.SM)

            if self._on_action and action_text:
                action_btn = QPushButton(action_text)
                action_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #8b5cf6;
                        color: white;
                        border: none;
                        border-radius: {BorderRadius.SM}px;
                        padding: 8px 16px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: #9d6fff;
                    }}
                """)
                action_btn.clicked.connect(self._handle_action)
                button_layout.addWidget(action_btn)

            button_layout.addStretch()

            if show_dismiss:
                dismiss_btn = QPushButton("Got it")
                dismiss_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #3a3a45;
                        color: #e4e4e7;
                        border: none;
                        border-radius: {BorderRadius.SM}px;
                        padding: 8px 16px;
                    }}
                    QPushButton:hover {{
                        background-color: #4a4a55;
                    }}
                """)
                dismiss_btn.clicked.connect(self.dismiss)
                button_layout.addWidget(dismiss_btn)

            layout.addLayout(button_layout)

        tooltip.adjustSize()
        return tooltip

    def _position_tooltip(self) -> None:
        """Position tooltip relative to target."""
        target = self._target()
        if not target:
            return

        # Get target rect in window coordinates
        parent_widget = cast(QWidget, self.parent())
        target_rect = QRect(
            target.mapTo(parent_widget, QPoint(0, 0)),
            target.size()
        )

        tooltip_size = self._tooltip.sizeHint()
        parent_rect = self.rect()

        # Determine position
        position = self._position
        if position == TipPosition.AUTO:
            position = self._calculate_best_position(target_rect, tooltip_size, parent_rect)

        # Calculate tooltip position
        margin = 12  # Gap between target and tooltip

        if position == TipPosition.BOTTOM:
            x = target_rect.center().x() - tooltip_size.width() // 2
            y = target_rect.bottom() + margin
        elif position == TipPosition.TOP:
            x = target_rect.center().x() - tooltip_size.width() // 2
            y = target_rect.top() - tooltip_size.height() - margin
        elif position == TipPosition.RIGHT:
            x = target_rect.right() + margin
            y = target_rect.center().y() - tooltip_size.height() // 2
        else:  # LEFT
            x = target_rect.left() - tooltip_size.width() - margin
            y = target_rect.center().y() - tooltip_size.height() // 2

        # Keep within bounds
        x = max(Spacing.SM, min(x, parent_rect.width() - tooltip_size.width() - Spacing.SM))
        y = max(Spacing.SM, min(y, parent_rect.height() - tooltip_size.height() - Spacing.SM))

        self._tooltip.move(x, y)

    def _calculate_best_position(
        self, target_rect: QRect, tooltip_size: QSize, parent_rect: QRect
    ) -> TipPosition:
        """Calculate the best position for the tooltip."""
        margin = 12

        # Check available space in each direction
        space_below = parent_rect.height() - target_rect.bottom()
        space_above = target_rect.top()
        space_right = parent_rect.width() - target_rect.right()
        space_left = target_rect.left()

        # Prefer bottom, then top, then right, then left
        if space_below >= tooltip_size.height() + margin:
            return TipPosition.BOTTOM
        elif space_above >= tooltip_size.height() + margin:
            return TipPosition.TOP
        elif space_right >= tooltip_size.width() + margin:
            return TipPosition.RIGHT
        else:
            return TipPosition.LEFT

    def paintEvent(self, event) -> None:
        """Paint overlay with cutout for target."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._show_overlay:
            target = self._target()
            if target:
                # Create overlay with hole for target
                target_rect = QRect(
                    target.mapTo(self, QPoint(0, 0)),
                    target.size()
                )

                # Slightly expand the cutout
                cutout = target_rect.adjusted(-4, -4, 4, 4)

                # Fill with semi-transparent overlay
                painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

                # Clear the cutout area
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.fillRect(cutout, Qt.GlobalColor.transparent)

                # Draw highlight border around target
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                pen = QPen(QColor("#8b5cf6"), 2)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(cutout, BorderRadius.SM, BorderRadius.SM)

    def show(self) -> None:
        """Show the spotlight with animation."""
        super().show()
        self.raise_()

        if should_reduce_motion():
            return

        # Fade in
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(Duration.NORMAL)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

        self._fade_animation = anim

    def dismiss(self) -> None:
        """Dismiss the spotlight."""
        if should_reduce_motion():
            self._do_dismiss()
            return

        # Fade out
        effect = self.graphicsEffect()
        if not effect:
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(Duration.FAST)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._do_dismiss)
        anim.start()

        self._fade_animation = anim

    def _do_dismiss(self) -> None:
        """Complete dismissal."""
        self.hide()
        if self._on_dismiss:
            self._on_dismiss()
        self.deleteLater()

    def _handle_action(self) -> None:
        """Handle action button click."""
        if self._on_action:
            self._on_action()
        self.dismiss()

    def mousePressEvent(self, event) -> None:
        """Allow clicking through to target."""
        target = self._target()
        if target:
            target_rect = QRect(
                target.mapTo(self, QPoint(0, 0)),
                target.size()
            )
            if target_rect.contains(event.pos()):
                # Let click through to target
                self.dismiss()
                return

        # Clicking overlay dismisses
        self.dismiss()


class SpotlightManager:
    """
    Manager for coordinating feature spotlights.

    Tracks which features have been shown and provides
    methods for showing spotlights in sequence.
    """

    def __init__(self):
        self._shown_features: set[str] = set()
        self._queue: list[tuple] = []
        self._current: Optional[FeatureSpotlight] = None

    def has_seen(self, feature_id: str) -> bool:
        """Check if user has seen a feature spotlight."""
        return feature_id in self._shown_features

    def mark_seen(self, feature_id: str) -> None:
        """Mark a feature as seen."""
        self._shown_features.add(feature_id)

    def show_spotlight(
        self,
        feature_id: str,
        target: QWidget,
        title: str,
        description: str,
        **kwargs,
    ) -> bool:
        """
        Show a spotlight if not already seen.

        Args:
            feature_id: Unique identifier for this feature
            target: Widget to highlight
            title: Spotlight title
            description: Spotlight description
            **kwargs: Additional FeatureSpotlight arguments

        Returns:
            True if spotlight was shown, False if already seen
        """
        if self.has_seen(feature_id):
            return False

        def on_dismiss():
            self.mark_seen(feature_id)
            self._current = None
            self._show_next()

        self._queue.append((target, title, description, on_dismiss, kwargs))
        self._show_next()
        return True

    def _show_next(self) -> None:
        """Show next spotlight in queue."""
        if self._current or not self._queue:
            return

        target, title, description, on_dismiss, kwargs = self._queue.pop(0)

        self._current = FeatureSpotlight(
            target, title, description,
            on_dismiss=on_dismiss,
            **kwargs,
        )
        self._current.show()

    def clear_queue(self) -> None:
        """Clear all pending spotlights."""
        self._queue.clear()

    def load_seen_features(self, features: set[str]) -> None:
        """Load previously seen features from storage."""
        self._shown_features = features.copy()

    def get_seen_features(self) -> set[str]:
        """Get set of seen feature IDs for storage."""
        return self._shown_features.copy()


# Global spotlight manager
_spotlight_manager: Optional[SpotlightManager] = None


def get_spotlight_manager() -> SpotlightManager:
    """Get the global spotlight manager."""
    global _spotlight_manager
    if _spotlight_manager is None:
        _spotlight_manager = SpotlightManager()
    return _spotlight_manager


def show_feature_tip(
    target: QWidget,
    title: str,
    description: str,
    *,
    position: TipPosition = TipPosition.AUTO,
    auto_dismiss: int = 0,
    on_dismiss: Optional[Callable[[], None]] = None,
) -> FeatureSpotlight:
    """
    Show a simple feature tip tooltip.

    Args:
        target: Widget to highlight
        title: Tip title
        description: Tip description
        position: Tooltip position
        auto_dismiss: Auto-dismiss after N milliseconds (0 = manual)
        on_dismiss: Callback when dismissed

    Returns:
        FeatureSpotlight instance
    """
    spotlight = FeatureSpotlight(
        target,
        title,
        description,
        position=position,
        show_overlay=False,
        on_dismiss=on_dismiss,
    )

    spotlight.show()

    if auto_dismiss > 0:
        QTimer.singleShot(auto_dismiss, spotlight.dismiss)

    return spotlight
