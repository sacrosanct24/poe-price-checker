"""
Tests for gui_qt.controllers.view_menu_controller - ViewMenuController.
"""

import pytest
from unittest.mock import MagicMock, patch

from gui_qt.controllers.view_menu_controller import (
    ViewMenuController,
    get_view_menu_controller,
)
from gui_qt.styles import Theme


@pytest.fixture
def mock_callbacks():
    """Create mock callbacks for the controller."""
    return {
        "on_history": MagicMock(),
        "on_stash_viewer": MagicMock(),
        "on_set_theme": MagicMock(),
        "on_toggle_theme": MagicMock(),
        "on_set_accent": MagicMock(),
        "on_toggle_column": MagicMock(),
    }


@pytest.fixture
def mock_parent():
    """Create mock parent widget."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def controller(mock_callbacks, mock_parent, mock_logger):
    """Create ViewMenuController with mocked dependencies."""
    return ViewMenuController(
        on_history=mock_callbacks["on_history"],
        on_stash_viewer=mock_callbacks["on_stash_viewer"],
        on_set_theme=mock_callbacks["on_set_theme"],
        on_toggle_theme=mock_callbacks["on_toggle_theme"],
        on_set_accent=mock_callbacks["on_set_accent"],
        on_toggle_column=mock_callbacks["on_toggle_column"],
        parent=mock_parent,
        logger=mock_logger,
    )


class TestViewMenuControllerInit:
    """Tests for ViewMenuController initialization."""

    def test_init_stores_callbacks(self, controller, mock_callbacks):
        """Controller should store all callbacks."""
        assert controller._on_history is mock_callbacks["on_history"]
        assert controller._on_stash_viewer is mock_callbacks["on_stash_viewer"]
        assert controller._on_set_theme is mock_callbacks["on_set_theme"]
        assert controller._on_toggle_theme is mock_callbacks["on_toggle_theme"]
        assert controller._on_set_accent is mock_callbacks["on_set_accent"]
        assert controller._on_toggle_column is mock_callbacks["on_toggle_column"]

    def test_init_empty_action_dicts(self, controller):
        """Controller should start with empty action dictionaries."""
        assert controller.theme_actions == {}
        assert controller.accent_actions == {}
        assert controller.column_actions == {}

    def test_init_without_optional_params(self, mock_callbacks):
        """Controller should work without optional params."""
        controller = ViewMenuController(
            on_history=mock_callbacks["on_history"],
            on_stash_viewer=mock_callbacks["on_stash_viewer"],
            on_set_theme=mock_callbacks["on_set_theme"],
            on_toggle_theme=mock_callbacks["on_toggle_theme"],
            on_set_accent=mock_callbacks["on_set_accent"],
            on_toggle_column=mock_callbacks["on_toggle_column"],
        )
        assert controller._parent is None
        assert controller._logger is not None  # Default logger


class TestViewMenuControllerCreateViewMenu:
    """Tests for View menu creation."""

    def test_create_view_menu_adds_menu(self, controller):
        """create_view_menu should add a View menu to menubar."""
        mock_menubar = MagicMock()
        mock_menu = MagicMock()
        mock_menubar.addMenu.return_value = mock_menu

        with patch("gui_qt.controllers.view_menu_controller.QAction"):
            controller.create_view_menu(mock_menubar)

        mock_menubar.addMenu.assert_called_once_with("&View")

    def test_create_view_menu_adds_history_action(self, controller, mock_callbacks):
        """create_view_menu should add Session History action."""
        mock_menubar = MagicMock()
        mock_menu = MagicMock()
        mock_menubar.addMenu.return_value = mock_menu

        with patch("gui_qt.controllers.view_menu_controller.QAction"):
            controller.create_view_menu(mock_menubar)

        # Check that addAction was called (history action is first)
        assert mock_menu.addAction.called

    def test_create_view_menu_returns_action_dicts(self, controller):
        """create_view_menu should return action dictionaries."""
        mock_menubar = MagicMock()
        mock_menu = MagicMock()
        mock_submenu = MagicMock()
        mock_menubar.addMenu.return_value = mock_menu
        mock_menu.addMenu.return_value = mock_submenu

        with patch("gui_qt.controllers.view_menu_controller.QAction") as mock_action:
            mock_action.return_value = MagicMock()
            theme_actions, accent_actions, column_actions = controller.create_view_menu(mock_menubar)

        # Should have created actions for themes, accents, and columns
        assert isinstance(theme_actions, dict)
        assert isinstance(accent_actions, dict)
        assert isinstance(column_actions, dict)

    def test_create_view_menu_populates_theme_actions(self, controller):
        """create_view_menu should populate theme_actions dict."""
        mock_menubar = MagicMock()
        mock_menu = MagicMock()
        mock_submenu = MagicMock()
        mock_menubar.addMenu.return_value = mock_menu
        mock_menu.addMenu.return_value = mock_submenu

        with patch("gui_qt.controllers.view_menu_controller.QAction") as mock_action:
            mock_action.return_value = MagicMock()
            controller.create_view_menu(mock_menubar)

        # Should have created theme actions
        assert len(controller.theme_actions) > 0
        # Check that at least DARK theme has an action
        assert Theme.DARK in controller.theme_actions or Theme.LIGHT in controller.theme_actions

    def test_create_view_menu_populates_accent_actions(self, controller):
        """create_view_menu should populate accent_actions dict."""
        mock_menubar = MagicMock()
        mock_menu = MagicMock()
        mock_submenu = MagicMock()
        mock_menubar.addMenu.return_value = mock_menu
        mock_menu.addMenu.return_value = mock_submenu

        with patch("gui_qt.controllers.view_menu_controller.QAction") as mock_action:
            mock_action.return_value = MagicMock()
            controller.create_view_menu(mock_menubar)

        # Should have created accent actions (including None for default)
        assert len(controller.accent_actions) > 0
        assert None in controller.accent_actions  # Default option

    def test_create_view_menu_populates_column_actions(self, controller):
        """create_view_menu should populate column_actions dict."""
        mock_menubar = MagicMock()
        mock_menu = MagicMock()
        mock_submenu = MagicMock()
        mock_menubar.addMenu.return_value = mock_menu
        mock_menu.addMenu.return_value = mock_submenu

        with patch("gui_qt.controllers.view_menu_controller.QAction") as mock_action:
            mock_action.return_value = MagicMock()
            controller.create_view_menu(mock_menubar)

        # Should have created column actions for default columns
        assert len(controller.column_actions) == len(ViewMenuController.DEFAULT_COLUMNS)
        for col in ViewMenuController.DEFAULT_COLUMNS:
            assert col in controller.column_actions


class TestViewMenuControllerProperties:
    """Tests for action property getters."""

    def test_theme_actions_property(self, controller):
        """theme_actions property should return internal dict."""
        test_dict = {Theme.DARK: MagicMock()}
        controller._theme_actions = test_dict
        assert controller.theme_actions is test_dict

    def test_accent_actions_property(self, controller):
        """accent_actions property should return internal dict."""
        test_dict = {None: MagicMock()}
        controller._accent_actions = test_dict
        assert controller.accent_actions is test_dict

    def test_column_actions_property(self, controller):
        """column_actions property should return internal dict."""
        test_dict = {"item_name": MagicMock()}
        controller._column_actions = test_dict
        assert controller.column_actions is test_dict


class TestGetViewMenuController:
    """Tests for factory function."""

    def test_get_view_menu_controller_returns_instance(self, mock_callbacks):
        """Factory should return a ViewMenuController."""
        controller = get_view_menu_controller(
            on_history=mock_callbacks["on_history"],
            on_stash_viewer=mock_callbacks["on_stash_viewer"],
            on_set_theme=mock_callbacks["on_set_theme"],
            on_toggle_theme=mock_callbacks["on_toggle_theme"],
            on_set_accent=mock_callbacks["on_set_accent"],
            on_toggle_column=mock_callbacks["on_toggle_column"],
        )

        assert isinstance(controller, ViewMenuController)

    def test_get_view_menu_controller_with_all_params(
        self, mock_callbacks, mock_parent, mock_logger
    ):
        """Factory should pass all parameters."""
        controller = get_view_menu_controller(
            on_history=mock_callbacks["on_history"],
            on_stash_viewer=mock_callbacks["on_stash_viewer"],
            on_set_theme=mock_callbacks["on_set_theme"],
            on_toggle_theme=mock_callbacks["on_toggle_theme"],
            on_set_accent=mock_callbacks["on_set_accent"],
            on_toggle_column=mock_callbacks["on_toggle_column"],
            parent=mock_parent,
            logger=mock_logger,
        )

        assert controller._parent is mock_parent
        assert controller._logger is mock_logger
