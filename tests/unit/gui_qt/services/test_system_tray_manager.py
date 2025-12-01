"""Tests for SystemTrayManager."""

import pytest
from unittest.mock import patch

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QSystemTrayIcon


class TestSystemTrayManagerInit:
    """Tests for SystemTrayManager initialization."""

    def test_init_with_defaults(self, qtbot):
        """Can initialize with default parameters."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        manager = SystemTrayManager()
        assert manager._app_name == "PoE Price Checker"
        assert manager._tray_icon is None
        assert not manager._is_initialized

    def test_init_with_custom_name(self, qtbot):
        """Can initialize with custom app name."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        manager = SystemTrayManager(app_name="Custom App")
        assert manager._app_name == "Custom App"

    def test_init_with_parent(self, qtbot):
        """Can initialize with parent window."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        window = QMainWindow()
        qtbot.addWidget(window)

        manager = SystemTrayManager(parent=window)
        assert manager._parent is window

    def test_init_with_icon(self, qtbot):
        """Can initialize with custom icon."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        icon = QIcon()
        manager = SystemTrayManager(icon=icon)
        assert manager._icon is icon


class TestSystemTrayAvailability:
    """Tests for system tray availability checking."""

    def test_is_available_returns_bool(self, qtbot):
        """is_available returns boolean."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        manager = SystemTrayManager()
        result = manager.is_available()
        assert isinstance(result, bool)

    def test_is_initialized_false_before_init(self, qtbot):
        """is_initialized returns False before initialization."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        manager = SystemTrayManager()
        assert manager.is_initialized() is False


class TestSystemTrayInitialize:
    """Tests for initialize method."""

    def test_initialize_when_available(self, qtbot):
        """Initialize succeeds when tray is available."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        with patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=True):
            manager = SystemTrayManager()
            result = manager.initialize()

            # On systems with tray support, this should succeed
            if QSystemTrayIcon.isSystemTrayAvailable():
                assert result is True
                assert manager.is_initialized() is True
                assert manager._tray_icon is not None
                manager.cleanup()

    def test_initialize_when_not_available(self, qtbot):
        """Initialize returns False when tray not available."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        with patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=False):
            manager = SystemTrayManager()
            result = manager.initialize()

            assert result is False
            assert manager.is_initialized() is False

    def test_initialize_idempotent(self, qtbot):
        """Initialize can be called multiple times safely."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        with patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=True):
            manager = SystemTrayManager()

            if QSystemTrayIcon.isSystemTrayAvailable():
                result1 = manager.initialize()
                result2 = manager.initialize()

                assert result1 == result2
                manager.cleanup()


class TestContextMenu:
    """Tests for context menu functionality."""

    def test_context_menu_created(self, qtbot):
        """Context menu is created on initialize."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        manager = SystemTrayManager()
        manager.initialize()

        assert manager._context_menu is not None
        assert manager._show_action is not None
        assert manager._settings_action is not None
        assert manager._quit_action is not None

        manager.cleanup()

    def test_context_menu_actions_connected(self, qtbot):
        """Context menu actions emit correct signals."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        window = QMainWindow()
        qtbot.addWidget(window)

        manager = SystemTrayManager(parent=window)
        manager.initialize()

        # Test quit signal
        quit_received = []
        manager.quit_requested.connect(lambda: quit_received.append(True))
        manager._quit_action.trigger()
        assert len(quit_received) == 1

        manager.cleanup()


class TestNotifications:
    """Tests for notification functionality."""

    def test_show_notification_when_not_initialized(self, qtbot):
        """show_notification returns False when not initialized."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        manager = SystemTrayManager()
        result = manager.show_notification("Title", "Message")
        assert result is False

    def test_show_price_alert_formats_message(self, qtbot):
        """show_price_alert formats message correctly."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        manager = SystemTrayManager()
        manager.initialize()

        # Mock the show_notification to capture args
        calls = []
        manager.show_notification = lambda *args, **kwargs: calls.append((args, kwargs)) or True

        # Test with chaos only
        manager.show_price_alert("Headhunter", 15000.0)
        assert len(calls) == 1
        # Args may be positional or keyword
        message = calls[0][1].get('message', calls[0][0][1] if len(calls[0][0]) > 1 else '')
        assert "Headhunter" in message
        assert "15000c" in message

        # Test with divine value
        calls.clear()
        manager.show_price_alert("Mageblood", 50000.0, 250.0)
        assert len(calls) == 1
        message = calls[0][1].get('message', calls[0][0][1] if len(calls[0][0]) > 1 else '')
        assert "250.0 div" in message

        manager.cleanup()


class TestWindowManagement:
    """Tests for window show/hide functionality."""

    def test_hide_to_tray(self, qtbot):
        """hide_to_tray hides the parent window."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        window = QMainWindow()
        qtbot.addWidget(window)
        window.show()

        manager = SystemTrayManager(parent=window)
        manager.initialize()

        assert window.isVisible()
        manager.hide_to_tray()
        assert not window.isVisible()

        manager.cleanup()

    def test_show_window_via_signal(self, qtbot):
        """Show action emits show_requested signal."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        window = QMainWindow()
        qtbot.addWidget(window)

        manager = SystemTrayManager(parent=window)
        manager.initialize()

        signals_received = []
        manager.show_requested.connect(lambda: signals_received.append(True))

        manager._show_action.trigger()
        assert len(signals_received) == 1

        manager.cleanup()


class TestTooltip:
    """Tests for tooltip functionality."""

    def test_set_tooltip(self, qtbot):
        """Can set tooltip text."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        manager = SystemTrayManager()
        manager.initialize()

        manager.set_tooltip("Custom Tooltip")
        assert manager._tray_icon.toolTip() == "Custom Tooltip"

        manager.cleanup()

    def test_update_tooltip_with_stats(self, qtbot):
        """Can update tooltip with statistics."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        manager = SystemTrayManager(app_name="Test App")
        manager.initialize()

        manager.update_tooltip_with_stats(items_checked=10, pending_sales=5)
        tooltip = manager._tray_icon.toolTip()
        assert "Test App" in tooltip
        assert "10 checked" in tooltip
        assert "5 pending" in tooltip

        manager.cleanup()


class TestCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_hides_icon(self, qtbot):
        """cleanup hides the tray icon."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        if not QSystemTrayIcon.isSystemTrayAvailable():
            pytest.skip("System tray not available")

        manager = SystemTrayManager()
        manager.initialize()

        assert manager._tray_icon is not None

        manager.cleanup()

        assert manager._tray_icon is None
        assert not manager.is_initialized()

    def test_cleanup_safe_when_not_initialized(self, qtbot):
        """cleanup is safe to call when not initialized."""
        from gui_qt.services.system_tray_manager import SystemTrayManager

        manager = SystemTrayManager()
        # Should not raise
        manager.cleanup()
        assert not manager.is_initialized()
