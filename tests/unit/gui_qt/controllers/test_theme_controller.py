"""Tests for ThemeController."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMainWindow

from gui_qt.controllers.theme_controller import ThemeController
from gui_qt.styles import Theme


@pytest.fixture
def mock_config():
    """Create mock config object."""
    config = MagicMock()
    config.theme = "dark"
    config.accent_color = None
    return config


@pytest.fixture
def mock_window(qtbot):
    """Create mock main window."""
    window = QMainWindow()
    qtbot.addWidget(window)
    # Don't mock setStyleSheet - it needs to work with real strings
    return window


@pytest.fixture
def mock_theme_manager():
    """Create mock theme manager that returns real strings."""
    mock_tm = MagicMock()
    mock_tm.get_stylesheet.return_value = "/* mock stylesheet */"
    mock_tm.current_theme = Theme.DARK
    mock_tm.toggle_theme.return_value = Theme.LIGHT
    return mock_tm


@pytest.fixture
def status_messages():
    """Track status messages."""
    messages = []
    return messages


@pytest.fixture
def controller(mock_config, status_messages):
    """Create ThemeController with mocks."""
    return ThemeController(
        config=mock_config,
        on_status=lambda msg: status_messages.append(msg),
    )


class TestThemeControllerInit:
    """Tests for ThemeController initialization."""

    def test_init_with_config(self, mock_config):
        """Can initialize with config."""
        controller = ThemeController(config=mock_config)
        assert controller._config is mock_config

    def test_init_without_config(self):
        """Can initialize without config."""
        controller = ThemeController(config=None)
        assert controller._config is None

    def test_init_with_status_callback(self, status_messages):
        """Status callback is stored."""
        controller = ThemeController(
            config=None,
            on_status=lambda msg: status_messages.append(msg),
        )
        controller._on_status("test")
        assert "test" in status_messages


class TestThemeActions:
    """Tests for theme/accent action management."""

    def test_set_theme_actions(self, controller):
        """Can set theme actions dict."""
        actions = {Theme.DARK: MagicMock(), Theme.LIGHT: MagicMock()}
        controller.set_theme_actions(actions)
        assert controller._theme_actions == actions

    def test_set_accent_actions(self, controller):
        """Can set accent actions dict."""
        actions = {None: MagicMock(), "chaos": MagicMock()}
        controller.set_accent_actions(actions)
        assert controller._accent_actions == actions


class TestInitialize:
    """Tests for theme initialization."""

    def test_initialize_loads_theme_from_config(self, controller, mock_window, mock_config, mock_theme_manager):
        """Initialize loads theme from config."""
        mock_config.theme = "light"

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.initialize(mock_window)

            mock_theme_manager.set_theme.assert_called_once_with(Theme.LIGHT)

    def test_initialize_defaults_to_dark_on_invalid_theme(self, controller, mock_window, mock_config, mock_theme_manager):
        """Initialize defaults to DARK on invalid theme value."""
        mock_config.theme = "invalid_theme"

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.initialize(mock_window)

            mock_theme_manager.set_theme.assert_called_once_with(Theme.DARK)

    def test_initialize_loads_accent_from_config(self, controller, mock_window, mock_config, mock_theme_manager):
        """Initialize loads accent color from config."""
        mock_config.accent_color = "chaos"

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.initialize(mock_window)

            mock_theme_manager.set_accent_color.assert_called_once_with("chaos")

    def test_initialize_applies_stylesheet(self, controller, mock_window, mock_theme_manager):
        """Initialize applies stylesheet to window."""
        mock_theme_manager.get_stylesheet.return_value = "/* init stylesheet */"

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.initialize(mock_window)

            assert mock_window.styleSheet() == "/* init stylesheet */"


class TestSetTheme:
    """Tests for set_theme method."""

    def test_set_theme_updates_manager(self, controller, mock_window, mock_theme_manager):
        """set_theme updates the theme manager."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_theme(Theme.SOLARIZED_DARK, mock_window)

            mock_theme_manager.set_theme.assert_called_once_with(Theme.SOLARIZED_DARK)

    def test_set_theme_saves_to_config(self, controller, mock_window, mock_config, mock_theme_manager):
        """set_theme saves theme value to config."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_theme(Theme.LIGHT, mock_window)

            assert mock_config.theme == "light"

    def test_set_theme_applies_stylesheet(self, controller, mock_window, mock_theme_manager):
        """set_theme applies stylesheet."""
        mock_theme_manager.get_stylesheet.return_value = "/* test style */"

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_theme(Theme.DARK, mock_window)

            assert mock_window.styleSheet() == "/* test style */"

    def test_set_theme_sends_status(self, controller, mock_window, status_messages, mock_theme_manager):
        """set_theme sends status message."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_theme(Theme.DARK, mock_window)

            assert len(status_messages) == 1
            assert "Theme changed" in status_messages[0]

    def test_set_theme_updates_menu_checks(self, controller, mock_window, mock_theme_manager):
        """set_theme updates menu checkmarks."""
        dark_action = MagicMock()
        light_action = MagicMock()
        controller.set_theme_actions({Theme.DARK: dark_action, Theme.LIGHT: light_action})

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_theme(Theme.DARK, mock_window)

            dark_action.setChecked.assert_called_with(True)
            light_action.setChecked.assert_called_with(False)


class TestToggleTheme:
    """Tests for toggle_theme method."""

    def test_toggle_theme_calls_manager(self, controller, mock_window, mock_theme_manager):
        """toggle_theme calls theme manager toggle."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            result = controller.toggle_theme(mock_window)

            mock_theme_manager.toggle_theme.assert_called_once()
            assert result == Theme.LIGHT

    def test_toggle_theme_saves_to_config(self, controller, mock_window, mock_config, mock_theme_manager):
        """toggle_theme saves new theme to config."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.toggle_theme(mock_window)

            assert mock_config.theme == "light"


class TestCycleTheme:
    """Tests for cycle_theme method."""

    def test_cycle_theme_advances_to_next(self, controller, mock_window, mock_theme_manager):
        """cycle_theme advances to next theme."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.cycle_theme(mock_window)

            # Should call set_theme with next theme
            mock_theme_manager.set_theme.assert_called()


class TestSetAccentColor:
    """Tests for set_accent_color method."""

    def test_set_accent_color_updates_manager(self, controller, mock_window, mock_theme_manager):
        """set_accent_color updates theme manager."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_accent_color("chaos", mock_window)

            mock_theme_manager.set_accent_color.assert_called_once_with("chaos")

    def test_set_accent_color_saves_to_config(self, controller, mock_window, mock_config, mock_theme_manager):
        """set_accent_color saves to config."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_accent_color("divine", mock_window)

            assert mock_config.accent_color == "divine"

    def test_set_accent_color_none_for_default(self, controller, mock_window, mock_config, mock_theme_manager):
        """set_accent_color with None uses theme default."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_accent_color(None, mock_window)

            mock_theme_manager.set_accent_color.assert_called_once_with(None)
            assert mock_config.accent_color is None

    def test_set_accent_color_sends_status(self, controller, mock_window, status_messages, mock_theme_manager):
        """set_accent_color sends status message."""
        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_accent_color("chaos", mock_window)

            assert len(status_messages) == 1
            assert "Accent color" in status_messages[0]

    def test_set_accent_color_updates_menu_checks(self, controller, mock_window, mock_theme_manager):
        """set_accent_color updates menu checkmarks."""
        none_action = MagicMock()
        chaos_action = MagicMock()
        controller.set_accent_actions({None: none_action, "chaos": chaos_action})

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            controller.set_accent_color("chaos", mock_window)

            none_action.setChecked.assert_called_with(False)
            chaos_action.setChecked.assert_called_with(True)


class TestNoConfig:
    """Tests for behavior without config."""

    def test_set_theme_without_config(self, mock_window, mock_theme_manager):
        """set_theme works without config."""
        controller = ThemeController(config=None)

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            # Should not raise
            controller.set_theme(Theme.DARK, mock_window)

    def test_set_accent_without_config(self, mock_window, mock_theme_manager):
        """set_accent_color works without config."""
        controller = ThemeController(config=None)

        with patch('gui_qt.controllers.theme_controller.get_theme_manager') as mock_get_tm:
            mock_get_tm.return_value = mock_theme_manager

            # Should not raise
            controller.set_accent_color("chaos", mock_window)
