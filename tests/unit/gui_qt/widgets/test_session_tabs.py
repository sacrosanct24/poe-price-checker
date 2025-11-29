"""
Tests for the Session Tabs widget.
"""

import pytest
from unittest.mock import MagicMock, patch

from gui_qt.widgets.session_tabs import SessionState, SessionPanel, SessionTabWidget


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_default_values(self):
        """Test that SessionState has correct defaults."""
        state = SessionState(name="Test Session")
        assert state.name == "Test Session"
        assert state.input_text == ""
        assert state.results == []
        assert state.filter_text == ""
        assert state.source_filter == "All sources"
        assert state.created_at is not None

    def test_with_values(self):
        """Test SessionState with custom values."""
        results = [{"item_name": "Test Item", "chaos_value": 10.0}]
        state = SessionState(
            name="Custom Session",
            input_text="Item text",
            results=results,
            filter_text="filter",
            source_filter="poe.ninja",
        )
        assert state.name == "Custom Session"
        assert state.input_text == "Item text"
        assert state.results == results
        assert state.filter_text == "filter"
        assert state.source_filter == "poe.ninja"


@pytest.fixture
def qapp():
    """Create QApplication for Qt tests."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def session_panel(qapp):
    """Create a SessionPanel for testing."""
    return SessionPanel("Test Session")


@pytest.fixture
def session_tab_widget(qapp):
    """Create a SessionTabWidget for testing."""
    return SessionTabWidget()


class TestSessionPanel:
    """Tests for SessionPanel widget."""

    def test_initial_state(self, session_panel):
        """Test that SessionPanel initializes correctly."""
        assert session_panel.session_name == "Test Session"
        assert session_panel._all_results == []
        assert session_panel.input_text is not None
        assert session_panel.item_inspector is not None
        assert session_panel.results_table is not None
        assert session_panel.filter_input is not None
        assert session_panel.source_filter is not None
        assert session_panel.rare_eval_panel is not None

    def test_set_results(self, session_panel):
        """Test setting results updates the panel."""
        results = [
            {"item_name": "Item 1", "chaos_value": 10.0, "source": "poe.ninja"},
            {"item_name": "Item 2", "chaos_value": 20.0, "source": "poe.watch"},
        ]
        session_panel.set_results(results)

        assert session_panel._all_results == results
        # Source filter should have been updated
        assert session_panel.source_filter.count() == 3  # All sources + 2 sources

    def test_get_state(self, session_panel):
        """Test getting the session state."""
        session_panel.input_text.setPlainText("Test input")
        session_panel.filter_input.setText("filter text")
        results = [{"item_name": "Item", "chaos_value": 5.0}]
        session_panel._all_results = results

        state = session_panel.get_state()

        assert state.name == "Test Session"
        assert state.input_text == "Test input"
        assert state.filter_text == "filter text"
        assert state.results == results

    def test_restore_state(self, session_panel):
        """Test restoring session state."""
        state = SessionState(
            name="Restored Session",
            input_text="Restored text",
            results=[{"item_name": "Restored Item", "chaos_value": 15.0}],
            filter_text="restored filter",
        )

        session_panel.restore_state(state)

        assert session_panel.session_name == "Restored Session"
        assert session_panel.input_text.toPlainText() == "Restored text"
        assert session_panel.filter_input.text() == "restored filter"
        assert session_panel._all_results == state.results

    def test_on_clear(self, session_panel):
        """Test clearing the session."""
        session_panel.input_text.setPlainText("Some text")
        session_panel._all_results = [{"item_name": "Item"}]

        session_panel._on_clear()

        assert session_panel.input_text.toPlainText() == ""
        assert session_panel._all_results == []

    def test_check_price_signal(self, session_panel, qtbot):
        """Test that check price button emits signal."""
        session_panel.input_text.setPlainText("Test item")

        # Use qtbot to capture signal
        with qtbot.waitSignal(session_panel.check_price_requested, timeout=1000) as blocker:
            session_panel._on_check_price()

        assert blocker.args == ["Test item"]

    def test_check_price_empty_text_no_signal(self, session_panel, qtbot):
        """Test that check price with empty text doesn't emit signal."""
        session_panel.input_text.setPlainText("")

        # Signal should NOT be emitted - use assertNotEmitted pattern
        signal_emitted = False

        def on_signal(text):
            nonlocal signal_emitted
            signal_emitted = True

        session_panel.check_price_requested.connect(on_signal)
        session_panel._on_check_price()

        assert not signal_emitted


class TestSessionTabWidget:
    """Tests for SessionTabWidget."""

    def test_initial_state(self, session_tab_widget):
        """Test that SessionTabWidget initializes with one tab."""
        assert session_tab_widget.count() == 1
        assert session_tab_widget.tabText(0) == "Session 1"

    def test_add_session(self, session_tab_widget):
        """Test adding a new session."""
        session_tab_widget._add_session("New Session")

        assert session_tab_widget.count() == 2
        assert session_tab_widget.tabText(1) == "New Session"
        assert session_tab_widget.currentIndex() == 1

    def test_max_sessions(self, session_tab_widget):
        """Test that max sessions limit is enforced."""
        # Add sessions up to the limit
        for i in range(session_tab_widget.MAX_SESSIONS - 1):
            session_tab_widget._add_session()

        assert session_tab_widget.count() == session_tab_widget.MAX_SESSIONS

        # Try to add one more
        result = session_tab_widget._add_session()
        assert result is None
        assert session_tab_widget.count() == session_tab_widget.MAX_SESSIONS

    def test_close_tab(self, session_tab_widget):
        """Test closing a tab."""
        session_tab_widget._add_session("Session 2")
        assert session_tab_widget.count() == 2

        session_tab_widget._on_tab_close_requested(1)
        assert session_tab_widget.count() == 1

    def test_cannot_close_last_tab(self, session_tab_widget):
        """Test that closing the last tab just clears it."""
        # Put some text in the input
        panel = session_tab_widget.get_panel(0)
        panel.input_text.setPlainText("Some text")

        # Try to close the last tab
        session_tab_widget._on_tab_close_requested(0)

        # Tab should still exist but be cleared
        assert session_tab_widget.count() == 1
        assert panel.input_text.toPlainText() == ""

    def test_rename_tab(self, session_tab_widget):
        """Test renaming a tab."""
        with patch('PyQt6.QtWidgets.QInputDialog.getText') as mock_input:
            mock_input.return_value = ("Renamed Session", True)
            session_tab_widget._rename_tab(0)

        assert session_tab_widget.tabText(0) == "Renamed Session"
        panel = session_tab_widget.get_panel(0)
        assert panel.session_name == "Renamed Session"

    def test_duplicate_tab(self, session_tab_widget):
        """Test duplicating a tab."""
        panel = session_tab_widget.get_panel(0)
        panel.input_text.setPlainText("Original text")
        panel._all_results = [{"item_name": "Original Item"}]

        session_tab_widget._duplicate_tab(0)

        assert session_tab_widget.count() == 2
        new_panel = session_tab_widget.get_panel(1)
        assert "copy" in session_tab_widget.tabText(1)
        assert new_panel.input_text.toPlainText() == "Original text"
        assert new_panel._all_results == panel._all_results

    def test_close_other_tabs(self, session_tab_widget):
        """Test closing all tabs except one."""
        session_tab_widget._add_session("Session 2")
        session_tab_widget._add_session("Session 3")
        assert session_tab_widget.count() == 3

        session_tab_widget._close_other_tabs(1)  # Keep Session 2

        assert session_tab_widget.count() == 1
        assert session_tab_widget.tabText(0) == "Session 2"

    def test_get_current_panel(self, session_tab_widget):
        """Test getting the current panel."""
        panel = session_tab_widget.get_current_panel()
        assert panel is not None
        assert isinstance(panel, SessionPanel)

    def test_get_panel_by_index(self, session_tab_widget):
        """Test getting a panel by index."""
        session_tab_widget._add_session("Session 2")

        panel0 = session_tab_widget.get_panel(0)
        panel1 = session_tab_widget.get_panel(1)

        assert panel0 is not None
        assert panel1 is not None
        assert panel0 != panel1

    def test_get_panel_invalid_index(self, session_tab_widget):
        """Test getting a panel with invalid index returns None."""
        panel = session_tab_widget.get_panel(99)
        assert panel is None

    def test_set_results_for_session(self, session_tab_widget):
        """Test setting results for a specific session."""
        results = [{"item_name": "Test Item", "chaos_value": 10.0}]
        session_tab_widget.set_results_for_session(0, results)

        panel = session_tab_widget.get_panel(0)
        assert panel._all_results == results

    def test_check_price_signal_includes_index(self, session_tab_widget, qtbot):
        """Test that check price signal includes session index."""
        # Add a second session and switch to it
        session_tab_widget._add_session("Session 2")
        panel = session_tab_widget.get_panel(1)
        panel.input_text.setPlainText("Test item")

        # Use qtbot to capture signal
        with qtbot.waitSignal(session_tab_widget.check_price_requested, timeout=1000) as blocker:
            # Trigger check price from the second session
            panel._on_check_price()

        assert blocker.args[0] == "Test item"
        assert blocker.args[1] == 1  # Session index
