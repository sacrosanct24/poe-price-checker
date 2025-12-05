"""Tests for gui_qt.widgets.loading_screen."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QIcon

from gui_qt.widgets.loading_screen import (
    LoadingScreen,
    LoadingOverlay,
)


class TestLoadingScreen:
    """Tests for LoadingScreen widget."""

    @pytest.fixture
    def loading_screen(self, qtbot):
        """Create a loading screen widget."""
        screen = LoadingScreen()
        qtbot.addWidget(screen)
        return screen

    def test_init_default_state(self, loading_screen):
        """Test initial state of loading screen."""
        assert loading_screen._current_step == 0
        assert loading_screen._progress_bar.value() == 0

    def test_fixed_size(self, loading_screen):
        """Test loading screen has fixed size."""
        assert loading_screen.width() == 450
        assert loading_screen.height() == 200

    def test_set_status(self, loading_screen):
        """Test setting status message."""
        loading_screen.set_status("Testing...")
        assert loading_screen._status_label.text() == "Testing..."

    def test_set_progress(self, loading_screen):
        """Test setting progress value."""
        loading_screen.set_progress(50)
        assert loading_screen._progress_bar.value() == 50

    def test_set_progress_clamps_max(self, loading_screen):
        """Test progress is clamped to 100 max."""
        loading_screen.set_progress(150)
        assert loading_screen._progress_bar.value() == 100

    def test_set_progress_clamps_min(self, loading_screen):
        """Test progress is clamped to 0 min."""
        loading_screen.set_progress(-10)
        assert loading_screen._progress_bar.value() == 0

    def test_set_version(self, loading_screen):
        """Test setting version text."""
        loading_screen.set_version("1.2.3")
        assert "1.2.3" in loading_screen._version_label.text()

    def test_advance_step(self, loading_screen):
        """Test advancing through loading steps."""
        initial_step = loading_screen._current_step
        loading_screen.advance_step()
        assert loading_screen._current_step == initial_step + 1
        assert loading_screen._progress_bar.value() > 0

    def test_advance_step_updates_status(self, loading_screen):
        """Test advance_step updates the status message."""
        loading_screen.advance_step()
        # Should have a non-empty status from LOADING_STEPS
        assert loading_screen._status_label.text() != ""

    def test_finish_sets_ready(self, loading_screen, qtbot):
        """Test finish sets status to Ready."""
        with qtbot.waitSignal(loading_screen.loading_complete, timeout=1000):
            loading_screen.finish()
        assert loading_screen._status_label.text() == "Ready!"
        assert loading_screen._progress_bar.value() == 100

    def test_loading_complete_signal(self, loading_screen, qtbot):
        """Test loading_complete signal is emitted on finish."""
        with qtbot.waitSignal(loading_screen.loading_complete, timeout=1000):
            loading_screen.finish()

    def test_loading_steps_defined(self, loading_screen):
        """Test that loading steps are properly defined."""
        assert len(LoadingScreen.LOADING_STEPS) > 0
        for message, progress in LoadingScreen.LOADING_STEPS:
            assert isinstance(message, str)
            assert isinstance(progress, int)
            assert 0 <= progress <= 100

    def test_loading_steps_progress_increases(self, loading_screen):
        """Test that loading step progress values increase."""
        previous = 0
        for _, progress in LoadingScreen.LOADING_STEPS:
            assert progress >= previous
            previous = progress


class TestLoadingOverlay:
    """Tests for LoadingOverlay widget."""

    @pytest.fixture
    def overlay(self, qtbot):
        """Create a loading overlay widget."""
        overlay = LoadingOverlay()
        qtbot.addWidget(overlay)
        return overlay

    def test_init(self, overlay):
        """Test overlay initialization."""
        assert overlay._message_label is not None
        assert overlay._progress_bar is not None

    def test_set_message(self, overlay):
        """Test setting overlay message."""
        overlay.set_message("Loading data...")
        assert overlay._message_label.text() == "Loading data..."

    def test_progress_bar_indeterminate(self, overlay):
        """Test overlay progress bar is indeterminate."""
        # Indeterminate means min == max or max == 0
        assert overlay._progress_bar.maximum() == 0
