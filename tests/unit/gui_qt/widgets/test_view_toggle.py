# tests/unit/gui_qt/widgets/test_view_toggle.py
"""Tests for ViewToggle widget."""

import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QWidget, QPushButton, QFrame, QButtonGroup

from gui_qt.widgets.view_toggle import (
    ViewMode,
    ViewToggleButton,
    ViewToggle,
    ResultsViewSwitcher,
)


# =============================================================================
# ViewMode Tests
# =============================================================================


class TestViewMode:
    """Tests for ViewMode enum."""

    def test_table_value(self):
        """TABLE should have 'table' value."""
        assert ViewMode.TABLE.value == "table"

    def test_cards_value(self):
        """CARDS should have 'cards' value."""
        assert ViewMode.CARDS.value == "cards"

    def test_enum_members(self):
        """ViewMode should have exactly two members."""
        members = list(ViewMode)
        assert len(members) == 2
        assert ViewMode.TABLE in members
        assert ViewMode.CARDS in members


# =============================================================================
# ViewToggleButton Tests
# =============================================================================


class TestViewToggleButton:
    """Tests for ViewToggleButton widget."""

    @pytest.fixture
    def button(self, qtbot):
        """Create ViewToggleButton instance."""
        btn = ViewToggleButton(
            mode=ViewMode.TABLE,
            icon_char="\u2630",
            tooltip="Table View",
        )
        qtbot.addWidget(btn)
        return btn

    def test_inherits_from_qpushbutton(self, button):
        """ViewToggleButton should be a QPushButton."""
        assert isinstance(button, QPushButton)

    def test_is_checkable(self, button):
        """Button should be checkable."""
        assert button.isCheckable()

    def test_has_tooltip(self, button):
        """Button should have tooltip."""
        assert button.toolTip() == "Table View"

    def test_has_fixed_size(self, button):
        """Button should have fixed size."""
        assert button.width() == 32
        assert button.height() == 28

    def test_mode_property(self, button):
        """mode property should return the view mode."""
        assert button.mode == ViewMode.TABLE

    def test_mode_property_cards(self, qtbot):
        """mode property should work for cards mode."""
        btn = ViewToggleButton(
            mode=ViewMode.CARDS,
            icon_char="\u25A6",
            tooltip="Cards View",
        )
        qtbot.addWidget(btn)
        assert btn.mode == ViewMode.CARDS


# =============================================================================
# ViewToggle Tests
# =============================================================================


class TestViewToggle:
    """Tests for ViewToggle widget."""

    @pytest.fixture
    def toggle(self, qtbot):
        """Create ViewToggle instance."""
        t = ViewToggle()
        qtbot.addWidget(t)
        return t

    def test_inherits_from_qframe(self, toggle):
        """ViewToggle should be a QFrame."""
        assert isinstance(toggle, QFrame)

    def test_initial_mode_is_table(self, toggle):
        """Default mode should be TABLE."""
        assert toggle.current_view() == ViewMode.TABLE

    def test_has_buttons_for_all_modes(self, toggle):
        """Toggle should have buttons for all view modes."""
        assert ViewMode.TABLE in toggle._buttons
        assert ViewMode.CARDS in toggle._buttons

    def test_table_button_is_checked_initially(self, toggle):
        """TABLE button should be checked initially."""
        assert toggle._buttons[ViewMode.TABLE].isChecked()
        assert not toggle._buttons[ViewMode.CARDS].isChecked()

    def test_set_view_to_cards(self, toggle):
        """set_view should switch to cards mode."""
        toggle.set_view(ViewMode.CARDS)
        assert toggle.current_view() == ViewMode.CARDS
        assert toggle._buttons[ViewMode.CARDS].isChecked()

    def test_set_view_to_table(self, toggle):
        """set_view should switch to table mode."""
        toggle.set_view(ViewMode.CARDS)
        toggle.set_view(ViewMode.TABLE)
        assert toggle.current_view() == ViewMode.TABLE
        assert toggle._buttons[ViewMode.TABLE].isChecked()

    def test_toggle_view_from_table(self, toggle):
        """toggle_view should switch from TABLE to CARDS."""
        result = toggle.toggle_view()
        assert result == ViewMode.CARDS
        assert toggle.current_view() == ViewMode.CARDS

    def test_toggle_view_from_cards(self, toggle):
        """toggle_view should switch from CARDS to TABLE."""
        toggle.set_view(ViewMode.CARDS)
        result = toggle.toggle_view()
        assert result == ViewMode.TABLE
        assert toggle.current_view() == ViewMode.TABLE

    def test_view_changed_signal_emitted(self, qtbot, toggle):
        """view_changed should emit when mode changes."""
        with qtbot.waitSignal(toggle.view_changed, timeout=1000) as blocker:
            toggle.set_view(ViewMode.CARDS)
        assert blocker.args == [ViewMode.CARDS]

    def test_view_changed_not_emitted_for_same_mode(self, qtbot, toggle):
        """view_changed should not emit when setting same mode."""
        from PyQt6.QtWidgets import QApplication

        # Set to TABLE (already TABLE) - should not emit
        signals_emitted = []
        toggle.view_changed.connect(lambda m: signals_emitted.append(m))
        toggle.set_view(ViewMode.TABLE)
        # Process any pending events
        QApplication.processEvents()
        assert len(signals_emitted) == 0

    def test_button_group_is_exclusive(self, toggle):
        """Button group should be exclusive."""
        assert toggle._button_group.exclusive()

    def test_view_configs_defined(self, toggle):
        """VIEW_CONFIGS should define all modes."""
        assert ViewMode.TABLE in toggle.VIEW_CONFIGS
        assert ViewMode.CARDS in toggle.VIEW_CONFIGS
        assert "icon" in toggle.VIEW_CONFIGS[ViewMode.TABLE]
        assert "tooltip" in toggle.VIEW_CONFIGS[ViewMode.TABLE]


# =============================================================================
# ResultsViewSwitcher Tests
# =============================================================================


class TestResultsViewSwitcher:
    """Tests for ResultsViewSwitcher widget."""

    @pytest.fixture
    def table_widget(self, qtbot):
        """Create mock table widget."""
        w = QWidget()
        w.set_data = MagicMock()
        w.get_selected_rows = MagicMock(return_value=[{"id": 1}])
        w.select_all = MagicMock()
        w.clear_selection = MagicMock()
        qtbot.addWidget(w)
        return w

    @pytest.fixture
    def cards_widget(self, qtbot):
        """Create mock cards widget."""
        w = QWidget()
        w.set_data = MagicMock()
        w.get_selected_data = MagicMock(return_value=[{"id": 2}])
        w.select_all = MagicMock()
        w.clear_selection = MagicMock()
        qtbot.addWidget(w)
        return w

    @pytest.fixture
    def switcher(self, qtbot, table_widget, cards_widget):
        """Create ResultsViewSwitcher instance."""
        s = ResultsViewSwitcher(table_widget, cards_widget)
        qtbot.addWidget(s)
        return s

    def test_inherits_from_qwidget(self, switcher):
        """ResultsViewSwitcher should be a QWidget."""
        assert isinstance(switcher, QWidget)

    def test_initial_mode_is_table(self, switcher):
        """Default mode should be TABLE."""
        assert switcher.current_view() == ViewMode.TABLE

    def test_table_visible_initially(self, switcher, table_widget, cards_widget):
        """Table should be visible, cards hidden initially."""
        # Note: isVisible() requires parent to be shown, so check isHidden() instead
        assert not table_widget.isHidden()
        assert cards_widget.isHidden()

    def test_set_view_to_cards(self, switcher, table_widget, cards_widget):
        """set_view to CARDS should show cards, hide table."""
        switcher.set_view(ViewMode.CARDS)
        assert table_widget.isHidden()
        assert not cards_widget.isHidden()
        assert switcher.current_view() == ViewMode.CARDS

    def test_set_view_to_table(self, switcher, table_widget, cards_widget):
        """set_view to TABLE should show table, hide cards."""
        switcher.set_view(ViewMode.CARDS)
        switcher.set_view(ViewMode.TABLE)
        assert not table_widget.isHidden()
        assert cards_widget.isHidden()
        assert switcher.current_view() == ViewMode.TABLE

    def test_set_view_same_mode_noop(self, switcher, table_widget):
        """set_view with same mode should be no-op."""
        switcher.set_view(ViewMode.TABLE)  # Already TABLE
        assert not table_widget.isHidden()

    def test_view_changed_signal_emitted(self, qtbot, switcher):
        """view_changed should emit when view changes."""
        with qtbot.waitSignal(switcher.view_changed, timeout=1000) as blocker:
            switcher.set_view(ViewMode.CARDS)
        assert blocker.args == [ViewMode.CARDS]

    def test_table_widget_accessor(self, switcher, table_widget):
        """table_widget() should return the table."""
        assert switcher.table_widget() is table_widget

    def test_cards_widget_accessor(self, switcher, cards_widget):
        """cards_widget() should return the cards."""
        assert switcher.cards_widget() is cards_widget

    def test_set_data_calls_both_widgets(self, switcher, table_widget, cards_widget):
        """set_data should call set_data on both widgets."""
        data = [{"item": "test"}]
        switcher.set_data(data)
        table_widget.set_data.assert_called_once_with(data)
        cards_widget.set_data.assert_called_once_with(data)

    def test_get_selected_rows_from_table(self, switcher, table_widget):
        """get_selected_rows should get from table when in table mode."""
        result = switcher.get_selected_rows()
        assert result == [{"id": 1}]
        table_widget.get_selected_rows.assert_called_once()

    def test_get_selected_rows_from_cards(self, switcher, cards_widget):
        """get_selected_rows should get from cards when in cards mode."""
        switcher.set_view(ViewMode.CARDS)
        result = switcher.get_selected_rows()
        assert result == [{"id": 2}]
        cards_widget.get_selected_data.assert_called_once()

    def test_select_all_in_table_mode(self, switcher, table_widget):
        """select_all should call table's select_all in table mode."""
        switcher.select_all()
        table_widget.select_all.assert_called_once()

    def test_select_all_in_cards_mode(self, switcher, cards_widget):
        """select_all should call cards' select_all in cards mode."""
        switcher.set_view(ViewMode.CARDS)
        switcher.select_all()
        cards_widget.select_all.assert_called_once()

    def test_clear_selection_in_table_mode(self, switcher, table_widget):
        """clear_selection should call table's clear_selection in table mode."""
        switcher.clear_selection()
        table_widget.clear_selection.assert_called_once()

    def test_clear_selection_in_cards_mode(self, switcher, cards_widget):
        """clear_selection should call cards' clear_selection in cards mode."""
        switcher.set_view(ViewMode.CARDS)
        switcher.clear_selection()
        cards_widget.clear_selection.assert_called_once()

    def test_get_selected_rows_without_method(self, qtbot):
        """get_selected_rows should return [] if widget lacks method."""
        table = QWidget()  # No get_selected_rows
        cards = QWidget()  # No get_selected_data
        qtbot.addWidget(table)
        qtbot.addWidget(cards)

        switcher = ResultsViewSwitcher(table, cards)
        qtbot.addWidget(switcher)

        assert switcher.get_selected_rows() == []
