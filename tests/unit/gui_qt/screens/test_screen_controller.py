# tests/unit/gui_qt/screens/test_screen_controller.py
"""Tests for ScreenController and ScreenType."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QStackedWidget, QWidget

from gui_qt.screens.screen_controller import ScreenController, ScreenType
from gui_qt.screens.base_screen import BaseScreen


class MockScreen(BaseScreen):
    """Mock screen for testing."""

    def __init__(self, name="Mock", ctx=None, on_status=None, parent=None):
        super().__init__(ctx or MagicMock(), on_status, parent)
        self._name = name
        self.enter_count = 0
        self.leave_count = 0

    @property
    def screen_name(self) -> str:
        return self._name

    def on_enter(self) -> None:
        self.enter_count += 1

    def on_leave(self) -> None:
        self.leave_count += 1


class TestScreenType:
    """Tests for ScreenType enum."""

    def test_item_evaluator_value(self):
        """ITEM_EVALUATOR should be 0."""
        assert ScreenType.ITEM_EVALUATOR == 0
        assert ScreenType.ITEM_EVALUATOR.value == 0

    def test_ai_advisor_value(self):
        """AI_ADVISOR should be 1."""
        assert ScreenType.AI_ADVISOR == 1
        assert ScreenType.AI_ADVISOR.value == 1

    def test_daytrader_value(self):
        """DAYTRADER should be 2."""
        assert ScreenType.DAYTRADER == 2
        assert ScreenType.DAYTRADER.value == 2

    def test_iteration_order(self):
        """ScreenType should iterate in order."""
        types = list(ScreenType)
        assert types == [
            ScreenType.ITEM_EVALUATOR,
            ScreenType.AI_ADVISOR,
            ScreenType.DAYTRADER,
        ]

    def test_from_int(self):
        """ScreenType should be constructible from int."""
        assert ScreenType(0) == ScreenType.ITEM_EVALUATOR
        assert ScreenType(1) == ScreenType.AI_ADVISOR
        assert ScreenType(2) == ScreenType.DAYTRADER


class TestScreenController:
    """Tests for ScreenController class."""

    @pytest.fixture
    def stacked_widget(self, qtbot):
        """Create a QStackedWidget for testing."""
        widget = QStackedWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def controller(self, stacked_widget):
        """Create a ScreenController instance."""
        return ScreenController(stacked_widget)

    @pytest.fixture
    def mock_screens(self, qtbot):
        """Create mock screens for all types."""
        screens = {}
        for screen_type in ScreenType:
            screen = MockScreen(name=screen_type.name)
            qtbot.addWidget(screen)
            screens[screen_type] = screen
        return screens

    def test_init_stores_stacked_widget(self, controller, stacked_widget):
        """Controller should store the stacked widget."""
        assert controller._stacked_widget is stacked_widget

    def test_init_no_current_screen(self, controller):
        """Controller should start with no current screen."""
        assert controller.current_screen is None

    def test_register_screen(self, controller, mock_screens):
        """register_screen should add screen to controller."""
        screen = mock_screens[ScreenType.ITEM_EVALUATOR]
        controller.register_screen(ScreenType.ITEM_EVALUATOR, screen)
        assert controller.get_screen(ScreenType.ITEM_EVALUATOR) is screen

    def test_register_screen_adds_to_stacked_widget(self, controller, mock_screens, stacked_widget):
        """register_screen should add widget to stacked widget at correct index."""
        screen = mock_screens[ScreenType.ITEM_EVALUATOR]
        controller.register_screen(ScreenType.ITEM_EVALUATOR, screen)
        assert stacked_widget.widget(0) is screen

    def test_register_multiple_screens(self, controller, mock_screens):
        """Controller should handle multiple registered screens."""
        for screen_type, screen in mock_screens.items():
            controller.register_screen(screen_type, screen)

        for screen_type in ScreenType:
            assert controller.get_screen(screen_type) is mock_screens[screen_type]

    def test_switch_to_unregistered_screen_returns_false(self, controller):
        """switch_to should return False for unregistered screen."""
        result = controller.switch_to(ScreenType.ITEM_EVALUATOR)
        assert result is False

    def test_switch_to_registered_screen_returns_true(self, controller, mock_screens):
        """switch_to should return True for registered screen."""
        controller.register_screen(ScreenType.ITEM_EVALUATOR, mock_screens[ScreenType.ITEM_EVALUATOR])
        result = controller.switch_to(ScreenType.ITEM_EVALUATOR)
        assert result is True

    def test_switch_to_calls_on_enter(self, controller, mock_screens):
        """switch_to should call on_enter on new screen."""
        screen = mock_screens[ScreenType.ITEM_EVALUATOR]
        controller.register_screen(ScreenType.ITEM_EVALUATOR, screen)
        controller.switch_to(ScreenType.ITEM_EVALUATOR)
        assert screen.enter_count == 1

    def test_switch_to_calls_on_leave(self, controller, mock_screens):
        """switch_to should call on_leave on previous screen."""
        screen1 = mock_screens[ScreenType.ITEM_EVALUATOR]
        screen2 = mock_screens[ScreenType.AI_ADVISOR]
        controller.register_screen(ScreenType.ITEM_EVALUATOR, screen1)
        controller.register_screen(ScreenType.AI_ADVISOR, screen2)

        controller.switch_to(ScreenType.ITEM_EVALUATOR)
        controller.switch_to(ScreenType.AI_ADVISOR)

        assert screen1.leave_count == 1

    def test_switch_to_same_screen_is_noop(self, controller, mock_screens):
        """switch_to same screen should not call lifecycle methods again."""
        screen = mock_screens[ScreenType.ITEM_EVALUATOR]
        controller.register_screen(ScreenType.ITEM_EVALUATOR, screen)

        controller.switch_to(ScreenType.ITEM_EVALUATOR)
        controller.switch_to(ScreenType.ITEM_EVALUATOR)

        assert screen.enter_count == 1  # Not 2

    def test_switch_to_updates_current_screen(self, controller, mock_screens):
        """switch_to should update current_screen property."""
        controller.register_screen(ScreenType.ITEM_EVALUATOR, mock_screens[ScreenType.ITEM_EVALUATOR])
        controller.switch_to(ScreenType.ITEM_EVALUATOR)
        assert controller.current_screen == ScreenType.ITEM_EVALUATOR

    def test_switch_to_emits_screen_changed_signal(self, qtbot, controller, mock_screens):
        """switch_to should emit screen_changed signal."""
        controller.register_screen(ScreenType.ITEM_EVALUATOR, mock_screens[ScreenType.ITEM_EVALUATOR])

        with qtbot.waitSignal(controller.screen_changed, timeout=1000) as blocker:
            controller.switch_to(ScreenType.ITEM_EVALUATOR)

        assert blocker.args == [ScreenType.ITEM_EVALUATOR.value]

    def test_switch_to_emits_screen_entering_signal(self, qtbot, controller, mock_screens):
        """switch_to should emit screen_entering signal before entering."""
        controller.register_screen(ScreenType.AI_ADVISOR, mock_screens[ScreenType.AI_ADVISOR])

        with qtbot.waitSignal(controller.screen_entering, timeout=1000) as blocker:
            controller.switch_to(ScreenType.AI_ADVISOR)

        assert blocker.args == [ScreenType.AI_ADVISOR.value]

    def test_switch_to_emits_screen_leaving_signal(self, qtbot, controller, mock_screens):
        """switch_to should emit screen_leaving signal before leaving."""
        controller.register_screen(ScreenType.ITEM_EVALUATOR, mock_screens[ScreenType.ITEM_EVALUATOR])
        controller.register_screen(ScreenType.AI_ADVISOR, mock_screens[ScreenType.AI_ADVISOR])
        controller.switch_to(ScreenType.ITEM_EVALUATOR)

        with qtbot.waitSignal(controller.screen_leaving, timeout=1000) as blocker:
            controller.switch_to(ScreenType.AI_ADVISOR)

        assert blocker.args == [ScreenType.ITEM_EVALUATOR.value]


class TestScreenControllerShortcuts:
    """Tests for screen switching shortcut methods."""

    @pytest.fixture
    def controller_with_screens(self, qtbot):
        """Create controller with all screens registered."""
        stacked = QStackedWidget()
        qtbot.addWidget(stacked)
        controller = ScreenController(stacked)

        for screen_type in ScreenType:
            screen = MockScreen(name=screen_type.name)
            qtbot.addWidget(screen)
            controller.register_screen(screen_type, screen)

        return controller

    def test_switch_to_evaluator(self, controller_with_screens):
        """switch_to_evaluator should switch to ITEM_EVALUATOR."""
        controller_with_screens.switch_to_evaluator()
        assert controller_with_screens.current_screen == ScreenType.ITEM_EVALUATOR

    def test_switch_to_advisor(self, controller_with_screens):
        """switch_to_advisor should switch to AI_ADVISOR."""
        controller_with_screens.switch_to_advisor()
        assert controller_with_screens.current_screen == ScreenType.AI_ADVISOR

    def test_switch_to_daytrader(self, controller_with_screens):
        """switch_to_daytrader should switch to DAYTRADER."""
        controller_with_screens.switch_to_daytrader()
        assert controller_with_screens.current_screen == ScreenType.DAYTRADER


class TestScreenControllerStatusCallback:
    """Tests for status callback functionality."""

    @pytest.fixture
    def controller(self, qtbot):
        """Create controller with callback."""
        stacked = QStackedWidget()
        qtbot.addWidget(stacked)
        return ScreenController(stacked)

    def test_set_status_callback(self, controller):
        """set_status_callback should store callback."""
        callback = MagicMock()
        controller.set_status_callback(callback)
        assert controller._on_status is callback

    def test_status_callback_called_on_switch(self, qtbot, controller):
        """Status callback should be called when switching screens."""
        callback = MagicMock()
        controller.set_status_callback(callback)

        screen = MockScreen(name="Test Screen")
        qtbot.addWidget(screen)
        controller.register_screen(ScreenType.ITEM_EVALUATOR, screen)

        controller.switch_to(ScreenType.ITEM_EVALUATOR)
        callback.assert_called_with("Test Screen")


class TestScreenControllerRefresh:
    """Tests for refresh functionality."""

    def test_refresh_current_is_callable(self, qtbot):
        """refresh_current should be callable on controller."""
        stacked = QStackedWidget()
        qtbot.addWidget(stacked)
        controller = ScreenController(stacked)

        screen = MockScreen()
        qtbot.addWidget(screen)

        controller.register_screen(ScreenType.ITEM_EVALUATOR, screen)
        controller.switch_to(ScreenType.ITEM_EVALUATOR)

        # Should not raise
        controller.refresh_current()

    def test_refresh_current_no_screen_is_safe(self, qtbot):
        """refresh_current with no current screen should not error."""
        stacked = QStackedWidget()
        qtbot.addWidget(stacked)
        controller = ScreenController(stacked)

        # Should not raise
        controller.refresh_current()
