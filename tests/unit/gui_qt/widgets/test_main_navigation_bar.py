# tests/unit/gui_qt/widgets/test_main_navigation_bar.py
"""Tests for MainNavigationBar widget."""

import pytest

from PyQt6.QtWidgets import QWidget

from gui_qt.widgets.main_navigation_bar import MainNavigationBar
from gui_qt.screens.screen_controller import ScreenType


class TestMainNavigationBar:
    """Tests for MainNavigationBar class."""

    @pytest.fixture
    def nav_bar(self, qtbot):
        """Create MainNavigationBar instance."""
        bar = MainNavigationBar()
        qtbot.addWidget(bar)
        return bar

    def test_inherits_from_qwidget(self, nav_bar):
        """MainNavigationBar should be a QWidget."""
        assert isinstance(nav_bar, QWidget)

    def test_has_three_buttons(self, nav_bar):
        """Navigation bar should have 3 buttons."""
        assert len(nav_bar._buttons) == 3

    def test_buttons_for_all_screen_types(self, nav_bar):
        """Should have buttons for all screen types."""
        assert ScreenType.ITEM_EVALUATOR in nav_bar._buttons
        assert ScreenType.AI_ADVISOR in nav_bar._buttons
        assert ScreenType.DAYTRADER in nav_bar._buttons

    def test_buttons_are_checkable(self, nav_bar):
        """All buttons should be checkable."""
        for button in nav_bar._buttons.values():
            assert button.isCheckable()

    def test_button_group_is_exclusive(self, nav_bar):
        """Button group should be exclusive (only one checked)."""
        assert nav_bar._button_group.exclusive()

    def test_default_selection_is_item_evaluator(self, nav_bar):
        """Item Evaluator should be selected by default."""
        assert nav_bar._buttons[ScreenType.ITEM_EVALUATOR].isChecked()
        assert not nav_bar._buttons[ScreenType.AI_ADVISOR].isChecked()
        assert not nav_bar._buttons[ScreenType.DAYTRADER].isChecked()

    def test_button_labels(self, nav_bar):
        """Buttons should have correct labels."""
        assert nav_bar._buttons[ScreenType.ITEM_EVALUATOR].text() == "Item Evaluator"
        assert nav_bar._buttons[ScreenType.AI_ADVISOR].text() == "AI Advisor"
        assert nav_bar._buttons[ScreenType.DAYTRADER].text() == "Daytrader"


class TestMainNavigationBarSignals:
    """Tests for navigation bar signals."""

    @pytest.fixture
    def nav_bar(self, qtbot):
        """Create MainNavigationBar instance."""
        bar = MainNavigationBar()
        qtbot.addWidget(bar)
        return bar

    def test_screen_selected_signal_on_click(self, qtbot, nav_bar):
        """screen_selected should emit when button is clicked."""
        with qtbot.waitSignal(nav_bar.screen_selected, timeout=1000) as blocker:
            nav_bar._buttons[ScreenType.AI_ADVISOR].click()
        assert blocker.args == [ScreenType.AI_ADVISOR.value]

    def test_screen_selected_signal_for_each_screen(self, qtbot, nav_bar):
        """screen_selected should emit correct value for each screen."""
        for screen_type in ScreenType:
            with qtbot.waitSignal(nav_bar.screen_selected, timeout=1000) as blocker:
                nav_bar._buttons[screen_type].click()
            assert blocker.args == [screen_type.value]

    def test_clicking_checked_button_still_emits(self, qtbot, nav_bar):
        """Clicking already-checked button should still emit signal."""
        # Item evaluator is checked by default
        with qtbot.waitSignal(nav_bar.screen_selected, timeout=1000):
            nav_bar._buttons[ScreenType.ITEM_EVALUATOR].click()


class TestMainNavigationBarSetActiveScreen:
    """Tests for set_active_screen method."""

    @pytest.fixture
    def nav_bar(self, qtbot):
        """Create MainNavigationBar instance."""
        bar = MainNavigationBar()
        qtbot.addWidget(bar)
        return bar

    def test_set_active_screen_checks_button(self, nav_bar):
        """set_active_screen should check the correct button."""
        nav_bar.set_active_screen(ScreenType.AI_ADVISOR)
        assert nav_bar._buttons[ScreenType.AI_ADVISOR].isChecked()

    def test_set_active_screen_unchecks_others(self, nav_bar):
        """set_active_screen should uncheck other buttons."""
        nav_bar.set_active_screen(ScreenType.AI_ADVISOR)
        assert not nav_bar._buttons[ScreenType.ITEM_EVALUATOR].isChecked()
        assert not nav_bar._buttons[ScreenType.DAYTRADER].isChecked()

    def test_set_active_screen_all_types(self, nav_bar):
        """set_active_screen should work for all screen types."""
        for screen_type in ScreenType:
            nav_bar.set_active_screen(screen_type)
            assert nav_bar._buttons[screen_type].isChecked()


class TestMainNavigationBarGetActiveScreen:
    """Tests for get_active_screen method."""

    @pytest.fixture
    def nav_bar(self, qtbot):
        """Create MainNavigationBar instance."""
        bar = MainNavigationBar()
        qtbot.addWidget(bar)
        return bar

    def test_get_active_screen_default(self, nav_bar):
        """get_active_screen should return ITEM_EVALUATOR by default."""
        assert nav_bar.get_active_screen() == ScreenType.ITEM_EVALUATOR

    def test_get_active_screen_after_set(self, nav_bar):
        """get_active_screen should return correct type after set."""
        nav_bar.set_active_screen(ScreenType.DAYTRADER)
        assert nav_bar.get_active_screen() == ScreenType.DAYTRADER

    def test_get_active_screen_after_click(self, nav_bar):
        """get_active_screen should return correct type after click."""
        nav_bar._buttons[ScreenType.AI_ADVISOR].click()
        assert nav_bar.get_active_screen() == ScreenType.AI_ADVISOR


class TestMainNavigationBarStyling:
    """Tests for navigation bar styling."""

    @pytest.fixture
    def nav_bar(self, qtbot):
        """Create MainNavigationBar instance."""
        bar = MainNavigationBar()
        qtbot.addWidget(bar)
        return bar

    def test_stylesheet_applied(self, nav_bar):
        """Navigation bar should have stylesheet."""
        assert nav_bar.styleSheet() != ""

    def test_buttons_have_minimum_width(self, nav_bar):
        """Buttons should have minimum width."""
        for button in nav_bar._buttons.values():
            assert button.minimumWidth() >= 140

    def test_buttons_have_minimum_height(self, nav_bar):
        """Buttons should have minimum height."""
        for button in nav_bar._buttons.values():
            assert button.minimumHeight() >= 36

    def test_button_stores_screen_type_property(self, nav_bar):
        """Buttons should store screen_type property."""
        for screen_type, button in nav_bar._buttons.items():
            assert button.property("screen_type") == screen_type.value
