"""
Tests for gui_qt.controllers.pob_controller - PoBController.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


from gui_qt.controllers.pob_controller import (
    PoBController,
    get_pob_controller,
)


@pytest.fixture
def mock_ctx():
    """Create mock AppContext."""
    ctx = MagicMock()
    return ctx


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def status_callback():
    """Create mock status callback."""
    return MagicMock()


@pytest.fixture
def controller(mock_ctx, mock_logger, status_callback):
    """Create PoBController with mocked dependencies."""
    return PoBController(
        ctx=mock_ctx,
        logger=mock_logger,
        on_status=status_callback,
    )


class TestPoBControllerInit:
    """Tests for PoBController initialization."""

    def test_init_stores_dependencies(self, mock_ctx, mock_logger, status_callback):
        """Controller should store all dependencies."""
        controller = PoBController(
            ctx=mock_ctx,
            logger=mock_logger,
            on_status=status_callback,
        )

        assert controller._ctx is mock_ctx
        assert controller._logger is mock_logger
        assert controller._on_status is status_callback
        assert controller._character_manager is None
        assert controller._upgrade_checker is None

    def test_init_without_optional_params(self, mock_ctx):
        """Controller should work without optional params."""
        controller = PoBController(ctx=mock_ctx)

        assert controller._ctx is mock_ctx
        assert controller._logger is not None  # Default logger
        assert controller._on_status is None


class TestPoBControllerInitialize:
    """Tests for character manager initialization."""

    def test_initialize_creates_character_manager(self, controller):
        """Initialize should create CharacterManager."""
        with patch("core.pob_integration.CharacterManager") as mock_cm_class:
            mock_cm = MagicMock()
            mock_cm_class.return_value = mock_cm

            result = controller.initialize()

            assert result is True
            assert controller._character_manager is mock_cm
            mock_cm_class.assert_called_once()

    def test_initialize_returns_false_on_error(self, controller):
        """Initialize should return False on error."""
        with patch("core.pob_integration.CharacterManager") as mock_cm_class:
            mock_cm_class.side_effect = Exception("Test error")

            result = controller.initialize()

            assert result is False
            assert controller._character_manager is None

    def test_character_manager_property(self, controller):
        """character_manager property should return the manager."""
        mock_cm = MagicMock()
        controller._character_manager = mock_cm

        assert controller.character_manager is mock_cm

    def test_upgrade_checker_property(self, controller):
        """upgrade_checker property should return the checker."""
        mock_checker = MagicMock()
        controller._upgrade_checker = mock_checker

        assert controller.upgrade_checker is mock_checker


class TestPoBControllerBuildStats:
    """Tests for build stats functionality."""

    def test_get_build_stats_returns_none_without_manager(self, controller):
        """get_build_stats should return None without character manager."""
        result = controller.get_build_stats()

        assert result is None

    def test_get_build_stats_returns_stats_tuple(self, controller):
        """get_build_stats should return (BuildStats, DPSStats) tuple."""
        mock_cm = MagicMock()
        mock_profile = MagicMock()
        mock_profile.build.stats = {"Life": 5000}
        mock_cm.get_active_profile.return_value = mock_profile
        controller._character_manager = mock_cm

        with patch("gui_qt.widgets.item_inspector.BuildStats") as mock_bs_class:
            with patch("core.dps_impact_calculator.DPSStats") as mock_dps_class:
                mock_build_stats = MagicMock()
                mock_dps_stats = MagicMock()
                mock_bs_class.from_pob_stats.return_value = mock_build_stats
                mock_dps_class.from_pob_stats.return_value = mock_dps_stats

                result = controller.get_build_stats()

                assert result == (mock_build_stats, mock_dps_stats)

    def test_get_build_stats_returns_none_when_no_profile(self, controller):
        """get_build_stats should return None when no active profile."""
        mock_cm = MagicMock()
        mock_cm.get_active_profile.return_value = None
        controller._character_manager = mock_cm

        result = controller.get_build_stats()

        assert result is None

    def test_update_inspector_stats_sets_stats(self, controller):
        """update_inspector_stats should set build and DPS stats."""
        mock_cm = MagicMock()
        mock_profile = MagicMock()
        mock_profile.build.stats = {"Life": 5000}
        mock_cm.get_active_profile.return_value = mock_profile
        controller._character_manager = mock_cm

        mock_inspector = MagicMock()

        with patch("gui_qt.widgets.item_inspector.BuildStats") as mock_bs_class:
            with patch("core.dps_impact_calculator.DPSStats") as mock_dps_class:
                mock_build_stats = MagicMock()
                mock_build_stats.total_life = 5000
                mock_build_stats.life_inc = 150
                mock_dps_stats = MagicMock()
                mock_dps_stats.combined_dps = 100000
                mock_dps_stats.primary_damage_type.value = "Physical"
                mock_bs_class.from_pob_stats.return_value = mock_build_stats
                mock_dps_class.from_pob_stats.return_value = mock_dps_stats

                controller.update_inspector_stats(mock_inspector)

                mock_inspector.set_build_stats.assert_called_once_with(mock_build_stats)
                mock_inspector.set_dps_stats.assert_called_once_with(mock_dps_stats)

    def test_update_inspector_stats_clears_when_no_manager(self, controller):
        """update_inspector_stats should not clear stats when no manager."""
        mock_inspector = MagicMock()

        controller.update_inspector_stats(mock_inspector)

        # Should not be called when no manager
        mock_inspector.set_build_stats.assert_not_called()


class TestPoBControllerProfileSelection:
    """Tests for profile selection handling."""

    def test_on_profile_selected_creates_upgrade_checker(self, controller, status_callback):
        """on_profile_selected should create UpgradeChecker."""
        mock_cm = MagicMock()
        mock_profile = MagicMock()
        mock_profile.build = MagicMock()
        mock_cm.get_profile.return_value = mock_profile
        controller._character_manager = mock_cm

        mock_price_controller = MagicMock()

        with patch("core.pob_integration.UpgradeChecker") as mock_uc_class:
            mock_checker = MagicMock()
            mock_uc_class.return_value = mock_checker

            controller.on_profile_selected("TestBuild", mock_price_controller)

            mock_uc_class.assert_called_once_with(mock_profile.build)
            mock_price_controller.set_upgrade_checker.assert_called_once_with(mock_checker)
            status_callback.assert_called_once()

    def test_on_profile_changed_updates_build_stats(self, controller):
        """on_profile_changed should update build stats."""
        mock_cm = MagicMock()
        mock_profile = MagicMock()
        mock_profile.build.stats = {"Life": 5000}
        mock_cm.get_active_profile.return_value = mock_profile
        controller._character_manager = mock_cm

        mock_inspector = MagicMock()

        with patch("gui_qt.widgets.item_inspector.BuildStats") as mock_bs_class:
            with patch("core.dps_impact_calculator.DPSStats") as mock_dps_class:
                mock_build_stats = MagicMock()
                mock_build_stats.total_life = 5000
                mock_build_stats.life_inc = 150
                mock_dps_stats = MagicMock()
                mock_dps_stats.combined_dps = 0
                mock_bs_class.from_pob_stats.return_value = mock_build_stats
                mock_dps_class.from_pob_stats.return_value = mock_dps_stats

                controller.on_profile_changed("TestBuild", mock_inspector)

                mock_cm.set_active_profile.assert_called_once_with("TestBuild")
                mock_inspector.set_build_stats.assert_called_once()

    def test_on_profile_changed_clears_stats_for_invalid_selection(self, controller):
        """on_profile_changed should clear stats for invalid selections."""
        mock_inspector = MagicMock()

        controller.on_profile_changed("", mock_inspector)
        mock_inspector.set_build_stats.assert_called_once_with(None)

        mock_inspector.reset_mock()
        controller.on_profile_changed("(No profiles)", mock_inspector)
        mock_inspector.set_build_stats.assert_called_once_with(None)


class TestPoBControllerPriceCheck:
    """Tests for PoB price check handling."""

    def test_handle_pob_price_check_sets_input_and_brings_to_front(self, controller):
        """handle_pob_price_check should set input and bring window to front."""
        mock_input = MagicMock()
        mock_window = MagicMock()
        mock_callback = MagicMock()

        with patch.object(PoBController, "bring_window_to_front") as mock_bring:
            with patch("gui_qt.controllers.pob_controller.QTimer") as mock_timer:
                controller.handle_pob_price_check(
                    item_text="Test Item",
                    input_text_widget=mock_input,
                    main_window=mock_window,
                    check_callback=mock_callback,
                )

                mock_input.setPlainText.assert_called_once_with("Test Item")
                mock_bring.assert_called_once_with(mock_window)
                mock_timer.singleShot.assert_called_once()


class TestBringWindowToFront:
    """Tests for window focus management."""

    def test_bring_window_to_front_activates_window(self):
        """bring_window_to_front should activate the window."""
        mock_window = MagicMock()
        mock_window.windowState.return_value = 0  # Normal state

        # Just verify the Qt methods are called - ctypes is optional
        PoBController.bring_window_to_front(mock_window)

        mock_window.showNormal.assert_called_once()
        mock_window.raise_.assert_called_once()
        mock_window.activateWindow.assert_called_once()

    def test_bring_window_to_front_restores_maximized_state(self):
        """bring_window_to_front should restore maximized state."""
        from PyQt6.QtCore import Qt

        mock_window = MagicMock()
        mock_window.windowState.return_value = Qt.WindowState.WindowMaximized

        PoBController.bring_window_to_front(mock_window)

        mock_window.showMaximized.assert_called_once()


class TestGetPoBController:
    """Tests for factory function."""

    def test_get_pob_controller_returns_instance(self, mock_ctx):
        """Factory should return a PoBController."""
        controller = get_pob_controller(ctx=mock_ctx)

        assert isinstance(controller, PoBController)

    def test_get_pob_controller_with_all_params(
        self, mock_ctx, mock_logger, status_callback
    ):
        """Factory should pass all parameters."""
        controller = get_pob_controller(
            ctx=mock_ctx,
            logger=mock_logger,
            on_status=status_callback,
        )

        assert controller._ctx is mock_ctx
        assert controller._logger is mock_logger
        assert controller._on_status is status_callback
