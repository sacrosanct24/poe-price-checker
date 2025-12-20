"""
Tests for the QuickVerdictPanel widget.
"""

import pytest
from unittest.mock import MagicMock

from gui_qt.widgets.quick_verdict_panel import (
    QuickVerdictPanel,
    CompactVerdictWidget,
)
from core.quick_verdict import Verdict


@pytest.fixture
def qapp():
    """Create QApplication for Qt tests."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def verdict_panel(qapp):
    """Create a QuickVerdictPanel for testing."""
    return QuickVerdictPanel()


@pytest.fixture
def compact_widget(qapp):
    """Create a CompactVerdictWidget for testing."""
    return CompactVerdictWidget()


@pytest.fixture
def mock_item():
    """Create a mock item for testing."""
    item = MagicMock()
    item.rarity = "Rare"
    item.name = "Test Item"
    item.base_type = "Test Base"
    item.explicits = []
    item.implicits = []
    item.sockets = 0
    item.links = 0
    item.influences = []
    item.is_fractured = False
    item.is_synthesised = False
    item.item_level = 75
    item.corrupted = False
    return item


# =============================================================================
# QuickVerdictPanel Tests
# =============================================================================


class TestQuickVerdictPanelInit:
    """Tests for QuickVerdictPanel initialization."""

    def test_panel_creates_successfully(self, verdict_panel):
        """Should create panel without error."""
        assert verdict_panel is not None

    def test_panel_has_calculator(self, verdict_panel):
        """Should have internal calculator."""
        assert verdict_panel._calculator is not None

    def test_panel_starts_with_no_result(self, verdict_panel):
        """Should start with no current result."""
        assert verdict_panel._current_result is None

    def test_panel_details_hidden_initially(self, verdict_panel):
        """Should have details hidden initially."""
        assert not verdict_panel._details_visible


class TestQuickVerdictPanelUpdateVerdict:
    """Tests for updating verdict display."""

    def test_update_verdict_with_high_price(self, verdict_panel, mock_item):
        """Should show KEEP for high price items."""
        result = verdict_panel.update_verdict(mock_item, price_chaos=100.0)

        assert result.verdict == Verdict.KEEP
        assert verdict_panel._current_result == result

    def test_update_verdict_with_low_price(self, verdict_panel, mock_item):
        """Should show VENDOR for low price items."""
        result = verdict_panel.update_verdict(mock_item, price_chaos=0.5)

        assert result.verdict == Verdict.VENDOR

    def test_update_verdict_with_mid_price(self, verdict_panel, mock_item):
        """Should show MAYBE for mid-range prices."""
        result = verdict_panel.update_verdict(mock_item, price_chaos=8.0)

        assert result.verdict == Verdict.MAYBE

    def test_update_verdict_returns_result(self, verdict_panel, mock_item):
        """Should return VerdictResult."""
        result = verdict_panel.update_verdict(mock_item, price_chaos=50.0)

        assert result is not None
        assert hasattr(result, 'verdict')
        assert hasattr(result, 'explanation')

    def test_update_verdict_with_multiple_prices(self, verdict_panel, mock_item):
        """Should handle multiple price sources."""
        prices = [("poe.ninja", 50.0), ("trade", 60.0)]
        result = verdict_panel.update_verdict(mock_item, prices=prices)

        assert result is not None
        assert result.confidence == "high"  # Multiple sources = high confidence


class TestQuickVerdictPanelDisplay:
    """Tests for display elements."""

    def test_emoji_updates_on_keep(self, verdict_panel, mock_item):
        """Should show thumbs up emoji for KEEP."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)

        assert verdict_panel._emoji_label.text() == "👍"

    def test_emoji_updates_on_vendor(self, verdict_panel, mock_item):
        """Should show thumbs down emoji for VENDOR."""
        verdict_panel.update_verdict(mock_item, price_chaos=0.5)

        assert verdict_panel._emoji_label.text() == "👎"

    def test_emoji_updates_on_maybe(self, verdict_panel, mock_item):
        """Should show thinking emoji for MAYBE."""
        verdict_panel.update_verdict(mock_item, price_chaos=8.0)

        assert verdict_panel._emoji_label.text() == "🤔"

    def test_verdict_label_updates(self, verdict_panel, mock_item):
        """Should update verdict label text."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)

        assert "KEEP" in verdict_panel._verdict_label.text().upper()

    def test_explanation_label_updates(self, verdict_panel, mock_item):
        """Should update explanation label."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)

        assert verdict_panel._explanation_label.text() != ""
        assert verdict_panel._explanation_label.text() != "Paste an item to get a verdict"

    def test_value_label_shown_with_price(self, verdict_panel, mock_item):
        """Should show value estimate when price is known."""
        verdict_panel.update_verdict(mock_item, price_chaos=50.0)

        # Use isHidden() as isVisible() checks parent chain
        assert not verdict_panel._value_label.isHidden()
        assert "50" in verdict_panel._value_label.text()

    def test_value_label_hidden_without_price(self, verdict_panel, mock_item):
        """Should hide value label when no price."""
        verdict_panel.update_verdict(mock_item, price_chaos=None)

        assert not verdict_panel._value_label.isVisible()


class TestQuickVerdictPanelClear:
    """Tests for clearing the panel."""

    def test_clear_resets_emoji(self, verdict_panel, mock_item):
        """Should reset emoji to question mark."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)
        verdict_panel.clear()

        assert verdict_panel._emoji_label.text() == "❓"

    def test_clear_resets_verdict_label(self, verdict_panel, mock_item):
        """Should reset verdict label."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)
        verdict_panel.clear()

        assert "Waiting" in verdict_panel._verdict_label.text()

    def test_clear_resets_explanation(self, verdict_panel, mock_item):
        """Should reset explanation to default."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)
        verdict_panel.clear()

        assert "Paste an item" in verdict_panel._explanation_label.text()

    def test_clear_hides_details(self, verdict_panel, mock_item):
        """Should hide details section."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)
        verdict_panel._details_visible = True
        verdict_panel.clear()

        assert not verdict_panel._details_visible
        assert not verdict_panel._details_frame.isVisible()

    def test_clear_resets_current_result(self, verdict_panel, mock_item):
        """Should reset current result to None."""
        verdict_panel.update_verdict(mock_item, price_chaos=100.0)
        verdict_panel.clear()

        assert verdict_panel._current_result is None


class TestQuickVerdictPanelToggleDetails:
    """Tests for details toggle functionality."""

    def test_toggle_details_shows_frame(self, verdict_panel, mock_item):
        """Should show details frame when toggled."""
        # Need a verdict with reasons first
        mock_item.explicits = ["+90 to maximum life"]
        verdict_panel.update_verdict(mock_item, price_chaos=None)

        verdict_panel._toggle_details()

        assert verdict_panel._details_visible
        # Use isHidden() as isVisible() checks parent chain
        assert not verdict_panel._details_frame.isHidden()

    def test_toggle_details_hides_frame(self, verdict_panel, mock_item):
        """Should hide details frame when toggled again."""
        mock_item.explicits = ["+90 to maximum life"]
        verdict_panel.update_verdict(mock_item, price_chaos=None)
        verdict_panel._toggle_details()  # Show
        verdict_panel._toggle_details()  # Hide

        assert not verdict_panel._details_visible
        assert not verdict_panel._details_frame.isVisible()

    def test_toggle_button_text_changes(self, verdict_panel, mock_item):
        """Should update button text on toggle."""
        mock_item.explicits = ["+90 to maximum life"]
        verdict_panel.update_verdict(mock_item, price_chaos=None)

        assert "Show" in verdict_panel._toggle_btn.text()
        verdict_panel._toggle_details()
        assert "Hide" in verdict_panel._toggle_btn.text()


class TestQuickVerdictPanelThresholds:
    """Tests for threshold configuration."""

    def test_set_thresholds_updates_calculator(self, verdict_panel):
        """Should update calculator thresholds."""
        verdict_panel.set_thresholds(vendor=5.0, keep=25.0)

        assert verdict_panel._calculator.thresholds.vendor_threshold == 5.0
        assert verdict_panel._calculator.thresholds.keep_threshold == 25.0

    def test_set_thresholds_emits_signal(self, verdict_panel, qtbot):
        """Should emit threshold_changed signal."""
        with qtbot.waitSignal(verdict_panel.threshold_changed, timeout=1000):
            verdict_panel.set_thresholds(vendor=5.0, keep=25.0)

    def test_get_current_result(self, verdict_panel, mock_item):
        """Should return current result."""
        verdict_panel.update_verdict(mock_item, price_chaos=50.0)
        result = verdict_panel.get_current_result()

        assert result is not None
        assert result.verdict == Verdict.KEEP


# =============================================================================
# CompactVerdictWidget Tests
# =============================================================================


class TestCompactVerdictWidget:
    """Tests for CompactVerdictWidget."""

    def test_widget_creates_successfully(self, compact_widget):
        """Should create widget without error."""
        assert compact_widget is not None

    def test_widget_has_calculator(self, compact_widget):
        """Should have internal calculator."""
        assert compact_widget._calculator is not None

    def test_update_verdict_changes_emoji(self, compact_widget, mock_item):
        """Should update emoji on verdict."""
        compact_widget.update_verdict(mock_item, price_chaos=100.0)

        assert compact_widget._emoji_label.text() == "👍"

    def test_update_verdict_changes_text(self, compact_widget, mock_item):
        """Should update text label on verdict."""
        compact_widget.update_verdict(mock_item, price_chaos=100.0)

        assert "KEEP" in compact_widget._text_label.text()

    def test_clear_resets_widget(self, compact_widget, mock_item):
        """Should reset widget on clear."""
        compact_widget.update_verdict(mock_item, price_chaos=100.0)
        compact_widget.clear()

        assert compact_widget._emoji_label.text() == "❓"
        assert "Waiting" in compact_widget._text_label.text()


# =============================================================================
# Integration Tests
# =============================================================================


class TestVerdictPanelIntegration:
    """Integration tests with real item scenarios."""

    def test_influenced_item_shows_keep(self, verdict_panel, mock_item):
        """Should show KEEP for influenced items."""
        mock_item.influences = ["Shaper"]

        result = verdict_panel.update_verdict(mock_item, price_chaos=None)

        assert result.verdict == Verdict.KEEP
        assert any("influenced" in r.lower() for r in result.detailed_reasons)

    def test_fractured_item_shows_keep(self, verdict_panel, mock_item):
        """Should show KEEP for fractured items."""
        mock_item.is_fractured = True

        result = verdict_panel.update_verdict(mock_item, price_chaos=None)

        assert result.verdict == Verdict.KEEP
        assert any("fractured" in r.lower() for r in result.detailed_reasons)

    def test_gem_level_item_shows_keep(self, verdict_panel, mock_item):
        """Should show KEEP for +gem level items."""
        mock_item.explicits = ["+1 to Level of all Skill Gems"]

        result = verdict_panel.update_verdict(mock_item, price_chaos=None)

        assert result.verdict == Verdict.KEEP
        assert any("+level" in r.lower() for r in result.detailed_reasons)

    def test_six_link_shows_keep(self, verdict_panel, mock_item):
        """Should show KEEP for 6-link items."""
        mock_item.links = 6
        mock_item.sockets = 6

        result = verdict_panel.update_verdict(mock_item, price_chaos=0)

        assert result.verdict == Verdict.KEEP
        assert any("6-link" in r.lower() for r in result.detailed_reasons)
