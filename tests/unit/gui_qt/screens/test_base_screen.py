# tests/unit/gui_qt/screens/test_base_screen.py
"""Tests for BaseScreen abstract class."""

import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QWidget

from gui_qt.screens.base_screen import BaseScreen


class ConcreteScreen(BaseScreen):
    """Concrete implementation for testing."""

    def __init__(self, ctx, on_status=None, parent=None):
        super().__init__(ctx, on_status, parent)
        self.enter_called = False
        self.leave_called = False
        self.refresh_called = False

    @property
    def screen_name(self) -> str:
        return "Test Screen"

    def on_enter(self) -> None:
        self.enter_called = True

    def on_leave(self) -> None:
        self.leave_called = True

    def refresh(self) -> None:
        self.refresh_called = True


class TestBaseScreen:
    """Tests for BaseScreen class."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock application context."""
        return MagicMock()

    @pytest.fixture
    def screen(self, qtbot, mock_ctx):
        """Create concrete screen instance."""
        screen = ConcreteScreen(mock_ctx)
        qtbot.addWidget(screen)
        return screen

    def test_init_stores_context(self, screen, mock_ctx):
        """BaseScreen should store the application context."""
        assert screen.ctx is mock_ctx

    def test_init_with_status_callback(self, qtbot, mock_ctx):
        """BaseScreen should store and connect status callback."""
        callback = MagicMock()
        screen = ConcreteScreen(mock_ctx, on_status=callback)
        qtbot.addWidget(screen)
        assert screen._on_status is callback

    def test_set_status_emits_signal(self, qtbot, screen):
        """set_status should emit status_message signal."""
        with qtbot.waitSignal(screen.status_message, timeout=1000):
            screen.set_status("Test message")

    def test_set_status_calls_callback(self, qtbot, mock_ctx):
        """set_status should call the on_status callback."""
        callback = MagicMock()
        screen = ConcreteScreen(mock_ctx, on_status=callback)
        qtbot.addWidget(screen)

        screen.set_status("Test message")
        callback.assert_called_with("Test message")

    def test_screen_name_property(self, screen):
        """screen_name should return the concrete class name."""
        assert screen.screen_name == "Test Screen"

    def test_on_enter_is_abstract(self):
        """on_enter should be abstract and must be implemented."""
        # ConcreteScreen implements it, so this tests the implementation
        mock_ctx = MagicMock()
        screen = ConcreteScreen(mock_ctx)
        screen.on_enter()
        assert screen.enter_called

    def test_on_leave_is_abstract(self):
        """on_leave should be abstract and must be implemented."""
        mock_ctx = MagicMock()
        screen = ConcreteScreen(mock_ctx)
        screen.on_leave()
        assert screen.leave_called

    def test_refresh_default_implementation(self, screen):
        """refresh should be callable and track calls."""
        screen.refresh()
        assert screen.refresh_called

    def test_inherits_from_qwidget(self, screen):
        """BaseScreen should inherit from QWidget."""
        assert isinstance(screen, QWidget)

    def test_status_signal_defined(self, screen):
        """BaseScreen should have status_message signal."""
        assert hasattr(screen, 'status_message')


class TestBaseScreenAbstract:
    """Tests verifying BaseScreen abstract behavior."""

    def test_on_enter_is_abstract_method(self):
        """on_enter should be marked as abstract."""
        # Check if the method has __isabstractmethod__ attribute
        assert getattr(BaseScreen.on_enter, '__isabstractmethod__', False)

    def test_on_leave_is_abstract_method(self):
        """on_leave should be marked as abstract."""
        assert getattr(BaseScreen.on_leave, '__isabstractmethod__', False)

    def test_base_screen_requires_implementation(self):
        """BaseScreen subclass needs on_enter and on_leave implemented."""
        # If we can create ConcreteScreen (which implements both), it works
        mock_ctx = MagicMock()
        screen = ConcreteScreen(mock_ctx)
        assert screen is not None
