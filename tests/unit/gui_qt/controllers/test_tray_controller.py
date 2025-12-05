"""
Tests for gui_qt.controllers.tray_controller - TrayController.
"""

import pytest
from unittest.mock import MagicMock, patch

from gui_qt.controllers.tray_controller import (
    TrayController,
    get_tray_controller,
)


@pytest.fixture
def mock_parent():
    """Create mock parent window."""
    parent = MagicMock()
    parent.windowIcon.return_value = MagicMock()
    return parent


@pytest.fixture
def mock_ctx():
    """Create mock AppContext with config."""
    ctx = MagicMock()
    ctx.config = MagicMock()
    ctx.config.minimize_to_tray = True
    ctx.config.show_tray_notifications = True
    ctx.config.tray_alert_threshold = 100
    ctx.config.divine_chaos_rate = 200
    return ctx


@pytest.fixture
def settings_callback():
    """Create mock settings callback."""
    return MagicMock()


@pytest.fixture
def cleanup_callback():
    """Create mock cleanup callback."""
    return MagicMock()


@pytest.fixture
def controller(mock_parent, mock_ctx, settings_callback, cleanup_callback):
    """Create TrayController with mocked dependencies."""
    return TrayController(
        parent=mock_parent,
        ctx=mock_ctx,
        on_settings=settings_callback,
        on_cleanup=cleanup_callback,
    )


class TestTrayControllerInit:
    """Tests for TrayController initialization."""

    def test_init_stores_dependencies(self, mock_parent, mock_ctx):
        """Controller should store all dependencies."""
        controller = TrayController(
            parent=mock_parent,
            ctx=mock_ctx,
        )

        assert controller._parent is mock_parent
        assert controller._ctx is mock_ctx
        assert controller._tray_manager is None

    def test_init_with_callbacks(
        self, mock_parent, mock_ctx, settings_callback, cleanup_callback
    ):
        """Controller should store callbacks."""
        controller = TrayController(
            parent=mock_parent,
            ctx=mock_ctx,
            on_settings=settings_callback,
            on_cleanup=cleanup_callback,
        )

        assert controller._on_settings is settings_callback
        assert controller._on_cleanup is cleanup_callback


class TestTrayControllerInitialize:
    """Tests for tray initialization."""

    def test_initialize_creates_tray_manager(self, controller):
        """Initialize should create SystemTrayManager."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray_class.return_value = mock_tray

            result = controller.initialize()

            assert result is True
            mock_tray_class.assert_called_once()

    def test_initialize_returns_false_when_tray_unavailable(self, controller):
        """Initialize should return False when tray is unavailable."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = False
            mock_tray_class.return_value = mock_tray

            result = controller.initialize()

            assert result is False

    def test_initialize_connects_settings_callback(
        self, controller, settings_callback
    ):
        """Initialize should connect settings callback."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()

            mock_tray.settings_requested.connect.assert_called_once_with(settings_callback)


class TestTrayControllerMinimize:
    """Tests for minimize to tray behavior."""

    def test_should_minimize_to_tray_when_config_enabled(self, controller, mock_ctx):
        """should_minimize_to_tray returns True when config enabled."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray.is_initialized.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()
            mock_ctx.config.minimize_to_tray = True

            assert controller.should_minimize_to_tray() is True

    def test_should_minimize_to_tray_false_when_not_initialized(self, controller):
        """should_minimize_to_tray returns False when tray not initialized."""
        assert controller.should_minimize_to_tray() is False

    def test_handle_minimize_returns_true_when_should_minimize(self, controller):
        """handle_minimize returns True and schedules hide."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray.is_initialized.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()

            with patch("gui_qt.controllers.tray_controller.QTimer") as mock_timer:
                result = controller.handle_minimize()

                assert result is True
                mock_timer.singleShot.assert_called_once()


class TestTrayControllerNotifications:
    """Tests for tray notification functionality."""

    def test_show_notification_when_initialized(self, controller):
        """show_notification should call tray manager."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray.is_initialized.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()
            controller.show_notification("Test Item", 100.0, 0.5)

            mock_tray.show_price_alert.assert_called_once_with("Test Item", 100.0, 0.5)

    def test_show_notification_skipped_when_disabled(self, controller, mock_ctx):
        """show_notification should skip when disabled in config."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray.is_initialized.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()
            mock_ctx.config.show_tray_notifications = False

            controller.show_notification("Test Item", 100.0)

            mock_tray.show_price_alert.assert_not_called()

    def test_maybe_show_alert_when_above_threshold(self, controller, mock_ctx):
        """maybe_show_alert should show alert when price exceeds threshold."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray.is_initialized.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()
            mock_ctx.config.tray_alert_threshold = 100

            # Create mock data with high price
            data = MagicMock()
            data.best_price = 150.0
            data.parsed_item = MagicMock()
            data.parsed_item.name = "Expensive Item"

            controller.maybe_show_alert(data)

            mock_tray.show_price_alert.assert_called_once()

    def test_maybe_show_alert_skipped_when_below_threshold(self, controller, mock_ctx):
        """maybe_show_alert should skip when price below threshold."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray.is_initialized.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()
            mock_ctx.config.tray_alert_threshold = 100

            # Create mock data with low price
            data = MagicMock()
            data.best_price = 50.0

            controller.maybe_show_alert(data)

            mock_tray.show_price_alert.assert_not_called()


class TestTrayControllerCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_calls_tray_manager_cleanup(self, controller):
        """cleanup should call tray manager cleanup."""
        with patch("gui_qt.services.SystemTrayManager") as mock_tray_class:
            mock_tray = MagicMock()
            mock_tray.initialize.return_value = True
            mock_tray_class.return_value = mock_tray

            controller.initialize()
            controller.cleanup()

            mock_tray.cleanup.assert_called_once()

    def test_quit_application_calls_cleanup_callback(
        self, controller, cleanup_callback
    ):
        """_quit_application should call cleanup callback."""
        with patch("gui_qt.controllers.tray_controller.QApplication") as mock_app:
            controller._quit_application()

            cleanup_callback.assert_called_once()
            mock_app.instance().quit.assert_called_once()


class TestGetTrayController:
    """Tests for factory function."""

    def test_get_tray_controller_returns_instance(self, mock_parent, mock_ctx):
        """Factory should return a TrayController."""
        controller = get_tray_controller(
            parent=mock_parent,
            ctx=mock_ctx,
        )

        assert isinstance(controller, TrayController)

    def test_get_tray_controller_with_callbacks(
        self, mock_parent, mock_ctx, settings_callback, cleanup_callback
    ):
        """Factory should pass all parameters."""
        controller = get_tray_controller(
            parent=mock_parent,
            ctx=mock_ctx,
            on_settings=settings_callback,
            on_cleanup=cleanup_callback,
        )

        assert controller._on_settings is settings_callback
        assert controller._on_cleanup is cleanup_callback
