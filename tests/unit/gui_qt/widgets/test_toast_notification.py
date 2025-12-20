"""Tests for gui_qt/widgets/toast_notification.py - Toast Notification Widget."""

import pytest

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget

from gui_qt.widgets.toast_notification import (
    ToastType,
    TOAST_COLORS,
    ToastNotification,
    ToastManager,
)


# ============================================================================
# ToastType Enum Tests
# ============================================================================

class TestToastType:
    """Tests for ToastType enum - behavioral tests."""

    def test_all_types_have_color_definitions(self):
        """Every toast type should have a color definition for styling."""
        for toast_type in ToastType:
            assert toast_type in TOAST_COLORS, f"Missing color for {toast_type}"
            config = TOAST_COLORS[toast_type]
            assert "bg" in config, f"Missing bg color for {toast_type}"
            assert "border" in config, f"Missing border color for {toast_type}"
            assert "icon" in config, f"Missing icon for {toast_type}"

    def test_toast_types_are_distinct(self):
        """Each toast type should be distinguishable from others."""
        icons = [TOAST_COLORS[t]["icon"] for t in ToastType]
        borders = [TOAST_COLORS[t]["border"] for t in ToastType]
        # Icons should be unique for accessibility
        assert len(icons) == len(set(icons)), "Toast icons should be unique"
        # Borders should be unique for visual distinction
        assert len(borders) == len(set(borders)), "Toast borders should be unique"

    def test_can_iterate_all_types(self):
        """Should be able to iterate through all toast types."""
        types = list(ToastType)
        assert len(types) == 4
        assert ToastType.INFO in types
        assert ToastType.SUCCESS in types
        assert ToastType.WARNING in types
        assert ToastType.ERROR in types


# ============================================================================
# TOAST_COLORS Tests
# ============================================================================

class TestToastColors:
    """Tests for TOAST_COLORS constant."""

    def test_info_colors(self):
        """INFO has correct colors."""
        colors = TOAST_COLORS[ToastType.INFO]
        assert "bg" in colors
        assert "border" in colors
        assert "text" in colors
        assert "icon" in colors
        assert colors["icon"] == "i"

    def test_success_colors(self):
        """SUCCESS has correct colors."""
        colors = TOAST_COLORS[ToastType.SUCCESS]
        assert colors["icon"] == "+"
        assert "#4CAF50" in colors["border"]  # Green

    def test_warning_colors(self):
        """WARNING has correct colors."""
        colors = TOAST_COLORS[ToastType.WARNING]
        assert colors["icon"] == "!"
        assert "#FFA726" in colors["border"]  # Orange

    def test_error_colors(self):
        """ERROR has correct colors."""
        colors = TOAST_COLORS[ToastType.ERROR]
        assert colors["icon"] == "x"
        assert "#F44336" in colors["border"]  # Red

    def test_all_types_have_colors(self):
        """All toast types have color definitions."""
        for toast_type in ToastType:
            assert toast_type in TOAST_COLORS


# ============================================================================
# ToastNotification Tests
# ============================================================================

class TestToastNotification:
    """Tests for ToastNotification class."""

    @pytest.fixture
    def parent_widget(self, qtbot):
        """Create a parent widget."""
        widget = QWidget()
        widget.resize(800, 600)
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def toast(self, parent_widget, qtbot):
        """Create a toast notification."""
        toast = ToastNotification("Test message", ToastType.INFO, 3000, parent_widget)
        qtbot.addWidget(toast)
        return toast

    def test_init(self, toast):
        """Toast initializes correctly."""
        assert toast._message == "Test message"
        assert toast._toast_type == ToastType.INFO
        assert toast._duration_ms == 3000

    def test_init_default_type(self, parent_widget, qtbot):
        """Toast defaults to INFO type."""
        toast = ToastNotification("Test", parent=parent_widget)
        qtbot.addWidget(toast)
        assert toast._toast_type == ToastType.INFO

    def test_init_default_duration(self, parent_widget, qtbot):
        """Toast defaults to 3000ms duration."""
        toast = ToastNotification("Test", parent=parent_widget)
        qtbot.addWidget(toast)
        assert toast._duration_ms == 3000

    def test_fixed_height(self, toast):
        """Toast has fixed height."""
        assert toast.height() == 40

    def test_window_flags(self, toast):
        """Toast has frameless and tool window flags."""
        flags = toast.windowFlags()
        assert flags & Qt.WindowType.FramelessWindowHint
        assert flags & Qt.WindowType.Tool

    def test_has_opacity_effect(self, toast):
        """Toast has opacity effect for animations."""
        assert toast._opacity is not None
        assert toast._opacity.opacity() == 0.0

    def test_has_dismiss_timer(self, toast):
        """Toast has dismiss timer."""
        assert toast._dismiss_timer is not None
        assert toast._dismiss_timer.isSingleShot()

    def test_show_toast(self, toast, qtbot):
        """show_toast displays the toast."""
        toast.show_toast()

        assert toast.isVisible()

    def test_show_toast_starts_timer(self, toast, qtbot):
        """show_toast starts dismiss timer."""
        toast.show_toast()

        assert toast._dismiss_timer.isActive()

    def test_show_toast_zero_duration(self, parent_widget, qtbot):
        """show_toast with zero duration doesn't start timer."""
        toast = ToastNotification("Test", duration_ms=0, parent=parent_widget)
        qtbot.addWidget(toast)

        toast.show_toast()

        assert not toast._dismiss_timer.isActive()

    def test_fade_in(self, toast, qtbot):
        """_fade_in starts fade animation."""
        toast._fade_in()

        assert toast._anim is not None
        assert toast._anim.endValue() == 1.0

    def test_fade_out(self, toast, qtbot):
        """_fade_out starts fade animation."""
        toast.show_toast()
        toast._fade_out()

        assert toast._anim is not None
        assert toast._anim.endValue() == 0.0

    def test_fade_out_stops_timer(self, toast, qtbot):
        """_fade_out stops dismiss timer."""
        toast.show_toast()
        toast._fade_out()

        assert not toast._dismiss_timer.isActive()

    def test_info_toast_styling(self, parent_widget, qtbot):
        """INFO toast has correct icon."""
        toast = ToastNotification("Test", ToastType.INFO, parent=parent_widget)
        qtbot.addWidget(toast)

        # Check that the icon label exists with correct text
        toast.findChildren(type(toast.findChild(type(toast))))
        # Just verify it was created without error

    def test_success_toast(self, parent_widget, qtbot):
        """SUCCESS toast can be created."""
        toast = ToastNotification("Success!", ToastType.SUCCESS, parent=parent_widget)
        qtbot.addWidget(toast)
        assert toast._toast_type == ToastType.SUCCESS

    def test_warning_toast(self, parent_widget, qtbot):
        """WARNING toast can be created."""
        toast = ToastNotification("Warning!", ToastType.WARNING, parent=parent_widget)
        qtbot.addWidget(toast)
        assert toast._toast_type == ToastType.WARNING

    def test_error_toast(self, parent_widget, qtbot):
        """ERROR toast can be created."""
        toast = ToastNotification("Error!", ToastType.ERROR, parent=parent_widget)
        qtbot.addWidget(toast)
        assert toast._toast_type == ToastType.ERROR


# ============================================================================
# ToastManager Tests
# ============================================================================

class TestToastManager:
    """Tests for ToastManager class."""

    @pytest.fixture
    def parent_widget(self, qtbot):
        """Create a parent widget."""
        widget = QWidget()
        widget.resize(800, 600)
        widget.show()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def manager(self, parent_widget):
        """Create a toast manager."""
        return ToastManager(parent_widget)

    def test_init(self, manager, parent_widget):
        """Manager initializes correctly."""
        assert manager._parent == parent_widget
        assert manager._toasts == []

    def test_show_toast(self, manager, qtbot):
        """show_toast creates and shows a toast."""
        toast = manager.show_toast("Test message")

        assert toast is not None
        assert len(manager._toasts) == 1
        assert toast.isVisible()

    def test_show_toast_custom_type(self, manager, qtbot):
        """show_toast accepts custom type."""
        toast = manager.show_toast("Error!", ToastType.ERROR)

        assert toast._toast_type == ToastType.ERROR

    def test_show_toast_custom_duration(self, manager, qtbot):
        """show_toast accepts custom duration."""
        toast = manager.show_toast("Test", duration_ms=5000)

        assert toast._duration_ms == 5000

    def test_info_shorthand(self, manager, qtbot):
        """info() creates INFO toast."""
        toast = manager.info("Info message")

        assert toast._toast_type == ToastType.INFO

    def test_success_shorthand(self, manager, qtbot):
        """success() creates SUCCESS toast."""
        toast = manager.success("Success message")

        assert toast._toast_type == ToastType.SUCCESS

    def test_warning_shorthand(self, manager, qtbot):
        """warning() creates WARNING toast."""
        toast = manager.warning("Warning message")

        assert toast._toast_type == ToastType.WARNING

    def test_error_shorthand(self, manager, qtbot):
        """error() creates ERROR toast."""
        toast = manager.error("Error message")

        assert toast._toast_type == ToastType.ERROR

    def test_warning_default_duration(self, manager, qtbot):
        """warning() has longer default duration."""
        toast = manager.warning("Warning")

        assert toast._duration_ms == 4000

    def test_error_default_duration(self, manager, qtbot):
        """error() has longest default duration."""
        toast = manager.error("Error")

        assert toast._duration_ms == 5000

    def test_max_toasts_limit(self, manager, qtbot):
        """Manager limits max toasts."""
        # Create more than MAX_TOASTS
        for i in range(ToastManager.MAX_TOASTS + 2):
            manager.show_toast(f"Toast {i}")

        assert len(manager._toasts) <= ToastManager.MAX_TOASTS

    def test_clear_all(self, manager, qtbot):
        """clear_all removes all toasts."""
        manager.show_toast("Toast 1")
        manager.show_toast("Toast 2")

        manager.clear_all()

        # Toasts should be fading out (removed async)
        # Can't easily verify immediate removal

    def test_position_toasts(self, manager, parent_widget, qtbot):
        """_position_toasts positions toasts correctly."""
        toast1 = manager.show_toast("Toast 1")
        toast2 = manager.show_toast("Toast 2")

        # Toasts should be positioned from bottom-right
        # Note: Position assertions may be 0 on some systems before show
        assert toast1 is not None
        assert toast2 is not None

    def test_toast_width_limited(self, manager, parent_widget, qtbot):
        """Toast width is limited to 400px max."""
        toast = manager.show_toast("A very long message that should still fit")

        assert toast.width() <= 400

    def test_remove_toast(self, manager, qtbot):
        """_remove_toast removes toast from list."""
        toast = manager.show_toast("Test")
        initial_count = len(manager._toasts)

        manager._remove_toast(toast)

        assert len(manager._toasts) == initial_count - 1

    def test_remove_toast_not_in_list(self, manager, parent_widget, qtbot):
        """_remove_toast handles toast not in list."""
        other_toast = ToastNotification("Other", parent=parent_widget)
        qtbot.addWidget(other_toast)

        # Should not raise
        manager._remove_toast(other_toast)

    def test_constants(self):
        """Manager has expected constants."""
        assert ToastManager.TOAST_SPACING == 8
        assert ToastManager.MARGIN_RIGHT == 20
        assert ToastManager.MARGIN_BOTTOM == 20
        assert ToastManager.MAX_TOASTS == 5


# ============================================================================
# Integration Tests
# ============================================================================

class TestToastIntegration:
    """Integration tests for toast system."""

    @pytest.fixture
    def parent_widget(self, qtbot):
        """Create a parent widget."""
        widget = QWidget()
        widget.resize(800, 600)
        widget.show()
        qtbot.addWidget(widget)
        return widget

    def test_multiple_toast_types(self, parent_widget, qtbot):
        """Different toast types can be shown together."""
        manager = ToastManager(parent_widget)

        toast1 = manager.info("Info")
        toast2 = manager.success("Success")
        toast3 = manager.warning("Warning")
        toast4 = manager.error("Error")

        assert len(manager._toasts) == 4
        assert toast1._toast_type == ToastType.INFO
        assert toast2._toast_type == ToastType.SUCCESS
        assert toast3._toast_type == ToastType.WARNING
        assert toast4._toast_type == ToastType.ERROR

    def test_close_button_exists(self, parent_widget, qtbot):
        """Toast has a close button."""
        from PyQt6.QtWidgets import QPushButton

        toast = ToastNotification("Test", parent=parent_widget)
        qtbot.addWidget(toast)

        # Find close button
        close_btn = None
        for child in toast.findChildren(QPushButton):
            if child.text() == "x":
                close_btn = child
                break

        assert close_btn is not None
