"""
Tests for gui_qt.controllers.navigation_controller - NavigationController service.
"""

import pytest
from unittest.mock import MagicMock, patch

from gui_qt.controllers.navigation_controller import (
    NavigationController,
    get_navigation_controller,
)


@pytest.fixture
def mock_window_manager():
    """Create mock WindowManager."""
    manager = MagicMock()
    manager._factories = {}
    manager.show_window = MagicMock(return_value=MagicMock())
    manager.register_factory = MagicMock()
    return manager


@pytest.fixture
def mock_ctx():
    """Create mock AppContext."""
    ctx = MagicMock()
    ctx.config = MagicMock()
    ctx.db = MagicMock()
    ctx.parser = MagicMock()
    ctx.price_service = MagicMock()
    return ctx


@pytest.fixture
def mock_main_window():
    """Create mock main window."""
    return MagicMock()


@pytest.fixture
def mock_character_manager():
    """Create mock character manager."""
    return MagicMock()


@pytest.fixture
def controller(mock_window_manager, mock_ctx, mock_main_window, mock_character_manager):
    """Create NavigationController with mocked dependencies."""
    return NavigationController(
        window_manager=mock_window_manager,
        ctx=mock_ctx,
        main_window=mock_main_window,
        character_manager=mock_character_manager,
        callbacks={
            "on_pob_profile_selected": MagicMock(),
            "on_pob_price_check": MagicMock(),
            "on_loadout_selected": MagicMock(),
            "on_ranking_price_check": MagicMock(),
            "on_reload_rare_evaluator": MagicMock(),
        },
    )


class TestNavigationControllerInit:
    """Tests for NavigationController initialization."""

    def test_init_stores_dependencies(
        self, mock_window_manager, mock_ctx, mock_main_window
    ):
        """NavigationController should store all dependencies."""
        controller = NavigationController(
            window_manager=mock_window_manager,
            ctx=mock_ctx,
            main_window=mock_main_window,
        )

        assert controller._wm is mock_window_manager
        assert controller._ctx is mock_ctx
        assert controller._main_window is mock_main_window
        assert controller._character_manager is None
        assert controller._callbacks == {}

    def test_init_with_character_manager(
        self, mock_window_manager, mock_ctx, mock_main_window, mock_character_manager
    ):
        """NavigationController should accept character manager."""
        controller = NavigationController(
            window_manager=mock_window_manager,
            ctx=mock_ctx,
            main_window=mock_main_window,
            character_manager=mock_character_manager,
        )

        assert controller._character_manager is mock_character_manager

    def test_init_with_callbacks(
        self, mock_window_manager, mock_ctx, mock_main_window
    ):
        """NavigationController should accept callbacks dict."""
        callback = MagicMock()
        controller = NavigationController(
            window_manager=mock_window_manager,
            ctx=mock_ctx,
            main_window=mock_main_window,
            callbacks={"test_callback": callback},
        )

        assert "test_callback" in controller._callbacks
        assert controller._callbacks["test_callback"] is callback


class TestNavigationControllerCallbacks:
    """Tests for callback management."""

    def test_set_character_manager(self, controller, mock_character_manager):
        """set_character_manager should update the character manager."""
        new_manager = MagicMock()
        controller.set_character_manager(new_manager)
        assert controller._character_manager is new_manager

    def test_set_callback(self, controller):
        """set_callback should register a new callback."""
        callback = MagicMock()
        controller.set_callback("new_callback", callback)
        assert controller._callbacks["new_callback"] is callback


class TestNavigationControllerPriceWindows:
    """Tests for price-related window methods."""

    def test_show_recent_sales(self, controller, mock_window_manager):
        """show_recent_sales should call window manager with correct params."""
        controller.show_recent_sales()

        mock_window_manager.show_window.assert_called_once()
        call_args = mock_window_manager.show_window.call_args
        assert call_args[0][0] == "recent_sales"

    def test_show_sales_dashboard(self, controller, mock_window_manager):
        """show_sales_dashboard should call window manager with correct params."""
        controller.show_sales_dashboard()

        mock_window_manager.show_window.assert_called_once()
        call_args = mock_window_manager.show_window.call_args
        assert call_args[0][0] == "sales_dashboard"

    def test_show_price_rankings(self, controller, mock_window_manager):
        """show_price_rankings should register factory if needed."""
        controller.show_price_rankings()

        # Should register factory since not in _factories
        mock_window_manager.register_factory.assert_called_once()
        call_args = mock_window_manager.register_factory.call_args
        assert call_args[0][0] == "price_rankings"

        mock_window_manager.show_window.assert_called_once()

    def test_show_price_rankings_factory_already_registered(
        self, controller, mock_window_manager
    ):
        """show_price_rankings should not re-register factory if exists."""
        mock_window_manager._factories["price_rankings"] = MagicMock()

        controller.show_price_rankings()

        mock_window_manager.register_factory.assert_not_called()
        mock_window_manager.show_window.assert_called_once()


class TestNavigationControllerBuildWindows:
    """Tests for build-related window methods."""

    def test_show_pob_characters_no_character_manager(
        self, mock_window_manager, mock_ctx, mock_main_window
    ):
        """show_pob_characters should show warning if no character manager."""
        controller = NavigationController(
            window_manager=mock_window_manager,
            ctx=mock_ctx,
            main_window=mock_main_window,
            character_manager=None,
        )

        with patch("PyQt6.QtWidgets.QMessageBox") as mock_box:
            result = controller.show_pob_characters()
            mock_box.warning.assert_called_once()
            assert result is None

    def test_show_pob_characters_with_manager(self, controller, mock_window_manager):
        """show_pob_characters should show window when manager exists."""
        mock_window = MagicMock()
        mock_window_manager.show_window.return_value = mock_window

        result = controller.show_pob_characters()

        mock_window_manager.register_factory.assert_called_once()
        mock_window_manager.show_window.assert_called_with("pob_characters")
        mock_window.activateWindow.assert_called_once()
        assert result is mock_window

    def test_show_build_comparison(self, controller, mock_window_manager):
        """show_build_comparison should register factory and show window."""
        controller.show_build_comparison()

        mock_window_manager.register_factory.assert_called_once()
        call_args = mock_window_manager.register_factory.call_args
        assert call_args[0][0] == "build_comparison"

        mock_window_manager.show_window.assert_called_with("build_comparison")

    def test_show_loadout_selector(self, controller, mock_window_manager):
        """show_loadout_selector should register factory with callback."""
        controller.show_loadout_selector()

        mock_window_manager.register_factory.assert_called_once()
        call_args = mock_window_manager.register_factory.call_args
        assert call_args[0][0] == "loadout_selector"

        mock_window_manager.show_window.assert_called_with("loadout_selector")

    def test_show_bis_search(self, controller, mock_window_manager):
        """show_bis_search should show BiS search dialog."""
        controller.show_bis_search()

        mock_window_manager.register_factory.assert_called_once()
        mock_window_manager.show_window.assert_called_with("bis_search")

    def test_show_upgrade_finder(self, controller, mock_window_manager):
        """show_upgrade_finder should show upgrade finder dialog."""
        controller.show_upgrade_finder()

        mock_window_manager.register_factory.assert_called_once()
        mock_window_manager.show_window.assert_called_with("upgrade_finder")

    def test_show_build_library(self, controller, mock_window_manager):
        """show_build_library should show build library dialog."""
        controller.show_build_library()

        mock_window_manager.register_factory.assert_called_once()
        mock_window_manager.show_window.assert_called_with("build_library")

    def test_show_item_comparison(self, controller, mock_window_manager):
        """show_item_comparison should show item comparison dialog."""
        controller.show_item_comparison()

        mock_window_manager.show_window.assert_called_once()
        call_args = mock_window_manager.show_window.call_args
        assert call_args[0][0] == "item_comparison"

    def test_show_rare_eval_config(self, controller, mock_window_manager):
        """show_rare_eval_config should show rare eval config window."""
        controller.show_rare_eval_config()

        mock_window_manager.register_factory.assert_called_once()
        mock_window_manager.show_window.assert_called_with("rare_eval_config")


class TestNavigationControllerViewerWindows:
    """Tests for viewer window methods."""

    def test_show_stash_viewer(self, controller, mock_window_manager):
        """show_stash_viewer should call window manager with correct params."""
        controller.show_stash_viewer()

        mock_window_manager.show_window.assert_called_once()
        call_args = mock_window_manager.show_window.call_args
        assert call_args[0][0] == "stash_viewer"


class TestGetNavigationController:
    """Tests for factory function."""

    def test_get_navigation_controller_returns_instance(
        self, mock_window_manager, mock_ctx, mock_main_window
    ):
        """get_navigation_controller should return a NavigationController."""
        controller = get_navigation_controller(
            window_manager=mock_window_manager,
            ctx=mock_ctx,
            main_window=mock_main_window,
        )

        assert isinstance(controller, NavigationController)

    def test_get_navigation_controller_with_all_params(
        self, mock_window_manager, mock_ctx, mock_main_window, mock_character_manager
    ):
        """get_navigation_controller should pass all parameters."""
        callbacks = {"test": MagicMock()}
        controller = get_navigation_controller(
            window_manager=mock_window_manager,
            ctx=mock_ctx,
            main_window=mock_main_window,
            character_manager=mock_character_manager,
            callbacks=callbacks,
        )

        assert controller._character_manager is mock_character_manager
        assert controller._callbacks == callbacks


class TestNavigationControllerFactoryReuse:
    """Tests that factories are not re-registered."""

    def test_factories_not_re_registered(self, controller, mock_window_manager):
        """Calling show methods twice should not re-register factories."""
        # Pre-register factories
        mock_window_manager._factories = {
            "build_comparison": MagicMock(),
            "loadout_selector": MagicMock(),
            "pob_characters": MagicMock(),
            "bis_search": MagicMock(),
            "upgrade_finder": MagicMock(),
            "build_library": MagicMock(),
            "rare_eval_config": MagicMock(),
            "price_rankings": MagicMock(),
        }

        # Call all show methods
        controller.show_build_comparison()
        controller.show_loadout_selector()
        controller.show_pob_characters()
        controller.show_bis_search()
        controller.show_upgrade_finder()
        controller.show_build_library()
        controller.show_rare_eval_config()
        controller.show_price_rankings()

        # No factories should be registered since they all already exist
        mock_window_manager.register_factory.assert_not_called()
