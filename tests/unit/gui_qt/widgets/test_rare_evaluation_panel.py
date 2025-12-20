"""
Tests for the RareEvaluationPanelWidget.
"""

import pytest
from unittest.mock import MagicMock

from gui_qt.widgets.rare_evaluation_panel import RareEvaluationPanelWidget


@pytest.fixture
def qapp():
    """Create QApplication for Qt tests."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def panel(qapp):
    """Create a RareEvaluationPanelWidget for testing."""
    return RareEvaluationPanelWidget()


@pytest.fixture
def mock_evaluation():
    """Create a mock evaluation result."""
    eval_result = MagicMock()
    eval_result.tier = "excellent"
    eval_result.estimated_value = "1div+"
    eval_result.total_score = 85
    eval_result.base_score = 45
    eval_result.affix_score = 80
    eval_result.is_valuable_base = True
    eval_result.has_high_ilvl = True
    eval_result.matched_affixes = []
    return eval_result


@pytest.fixture
def mock_affix_match():
    """Create a mock affix match."""
    match = MagicMock()
    match.affix_type = "life"
    match.mod_text = "+90 to maximum Life"
    match.value = 90
    match.weight = 10
    match.has_meta_bonus = True
    return match


@pytest.fixture
def mock_evaluator():
    """Create a mock evaluator with meta info."""
    evaluator = MagicMock()
    evaluator._meta_cache_info = {
        "league": "Settlers",
        "builds_analyzed": 50,
        "source": "meta_affixes.json"
    }
    evaluator.meta_weights = {
        "life": {"popularity_percent": 80.0},
        "resistances": {"popularity_percent": 75.0},
        "movement_speed": {"popularity_percent": 60.0},
    }
    return evaluator


# =============================================================================
# Initialization Tests
# =============================================================================


class TestRareEvaluationPanelInit:
    """Tests for panel initialization."""

    def test_panel_creates_successfully(self, panel):
        """Should create panel without error."""
        assert panel is not None

    def test_panel_has_tier_label(self, panel):
        """Should have tier label widget."""
        assert panel.tier_label is not None

    def test_panel_has_value_label(self, panel):
        """Should have value label widget."""
        assert panel.value_label is not None

    def test_panel_has_score_labels(self, panel):
        """Should have score label widgets."""
        assert panel.total_score_label is not None
        assert panel.base_score_label is not None
        assert panel.affix_score_label is not None

    def test_panel_has_affixes_text(self, panel):
        """Should have affixes text area."""
        assert panel.affixes_text is not None

    def test_panel_has_meta_label(self, panel):
        """Should have meta info label."""
        assert panel.meta_label is not None

    def test_panel_has_update_button(self, panel):
        """Should have update meta button."""
        assert panel.update_meta_btn is not None

    def test_panel_starts_with_no_evaluation(self, panel):
        """Should start with no evaluation."""
        assert panel._evaluation is None

    def test_panel_starts_with_no_evaluator(self, panel):
        """Should start with no evaluator reference."""
        assert panel._evaluator is None


# =============================================================================
# Set Evaluator Tests
# =============================================================================


class TestSetEvaluator:
    """Tests for setting the evaluator reference."""

    def test_set_evaluator_stores_reference(self, panel, mock_evaluator):
        """Should store evaluator reference."""
        panel.set_evaluator(mock_evaluator)
        assert panel._evaluator == mock_evaluator

    def test_set_evaluator_none_clears_reference(self, panel, mock_evaluator):
        """Should clear evaluator reference when set to None."""
        panel.set_evaluator(mock_evaluator)
        panel.set_evaluator(None)
        assert panel._evaluator is None


# =============================================================================
# Evaluation Display Tests
# =============================================================================


class TestSetEvaluation:
    """Tests for displaying evaluation results."""

    def test_set_evaluation_updates_tier(self, panel, mock_evaluation):
        """Should update tier label."""
        panel.set_evaluation(mock_evaluation)
        assert "EXCELLENT" in panel.tier_label.text()

    def test_set_evaluation_updates_value(self, panel, mock_evaluation):
        """Should update value label."""
        panel.set_evaluation(mock_evaluation)
        assert "1div+" in panel.value_label.text()

    def test_set_evaluation_updates_scores(self, panel, mock_evaluation):
        """Should update score labels."""
        panel.set_evaluation(mock_evaluation)
        assert "85" in panel.total_score_label.text()
        assert "45" in panel.base_score_label.text()
        assert "80" in panel.affix_score_label.text()

    def test_set_evaluation_no_affixes(self, panel, mock_evaluation):
        """Should show message when no affixes."""
        mock_evaluation.matched_affixes = []
        panel.set_evaluation(mock_evaluation)
        assert "No valuable affixes found" in panel.affixes_text.toPlainText()


# =============================================================================
# Meta Bonus Display Tests
# =============================================================================


class TestMetaBonusDisplay:
    """Tests for displaying meta bonus tags."""

    def test_meta_bonus_shown_in_html(self, panel, mock_evaluation, mock_affix_match):
        """Should show META +2 tag in HTML for affixes with bonus."""
        mock_evaluation.matched_affixes = [mock_affix_match]
        panel.set_evaluation(mock_evaluation)

        html = panel.affixes_text.toHtml()
        assert "META +2" in html

    def test_meta_bonus_has_color(self, panel, mock_evaluation, mock_affix_match):
        """META +2 tag should have color styling."""
        mock_evaluation.matched_affixes = [mock_affix_match]
        panel.set_evaluation(mock_evaluation)

        html = panel.affixes_text.toHtml()
        # Check for teal/green color
        assert "#00cc88" in html.lower() or "00cc88" in html.lower()

    def test_no_meta_bonus_without_flag(self, panel, mock_evaluation, mock_affix_match):
        """Should not show META tag when has_meta_bonus is False."""
        mock_affix_match.has_meta_bonus = False
        mock_evaluation.matched_affixes = [mock_affix_match]
        panel.set_evaluation(mock_evaluation)

        html = panel.affixes_text.toHtml()
        assert "META +2" not in html


# =============================================================================
# Meta Info Display Tests
# =============================================================================


class TestMetaInfoDisplay:
    """Tests for meta info section display."""

    def test_meta_info_no_evaluator(self, panel):
        """Should show N/A when no evaluator."""
        panel._update_meta_info()
        assert "N/A" in panel.meta_label.text()

    def test_meta_info_no_cache(self, panel, mock_evaluator):
        """Should show static weights message when no cache."""
        mock_evaluator._meta_cache_info = None
        panel.set_evaluator(mock_evaluator)
        panel._update_meta_info()
        assert "Static weights" in panel.meta_label.text()

    def test_meta_info_shows_league(self, panel, mock_evaluator):
        """Should show league name from cache."""
        panel.set_evaluator(mock_evaluator)
        panel._update_meta_info()
        assert "Settlers" in panel.meta_label.text()

    def test_meta_info_shows_builds_count(self, panel, mock_evaluator):
        """Should show builds analyzed count."""
        panel.set_evaluator(mock_evaluator)
        panel._update_meta_info()
        assert "50" in panel.meta_label.text()

    def test_meta_info_shows_top_affixes(self, panel, mock_evaluator):
        """Should show top meta affixes."""
        panel.set_evaluator(mock_evaluator)
        panel._update_meta_info()
        # Should show "Top:" followed by top affixes
        text = panel.meta_label.text()
        assert "Top:" in text or "life" in text


# =============================================================================
# Update Meta Button Tests
# =============================================================================


class TestUpdateMetaButton:
    """Tests for the update meta weights button."""

    def test_button_emits_signal(self, panel, qtbot):
        """Should emit update_meta_requested signal on click."""
        with qtbot.waitSignal(panel.update_meta_requested, timeout=1000):
            panel.update_meta_btn.click()

    def test_button_has_tooltip(self, panel):
        """Should have tooltip explaining function."""
        assert panel.update_meta_btn.toolTip() != ""


# =============================================================================
# Clear Tests
# =============================================================================


class TestClear:
    """Tests for clearing the panel."""

    def test_clear_resets_tier(self, panel, mock_evaluation):
        """Should reset tier label."""
        panel.set_evaluation(mock_evaluation)
        panel.clear()
        assert panel.tier_label.text() == ""

    def test_clear_resets_value(self, panel, mock_evaluation):
        """Should reset value label."""
        panel.set_evaluation(mock_evaluation)
        panel.clear()
        assert panel.value_label.text() == ""

    def test_clear_resets_scores(self, panel, mock_evaluation):
        """Should reset score labels."""
        panel.set_evaluation(mock_evaluation)
        panel.clear()
        assert panel.total_score_label.text() == ""
        assert panel.base_score_label.text() == ""
        assert panel.affix_score_label.text() == ""

    def test_clear_resets_affixes(self, panel, mock_evaluation):
        """Should reset affixes text."""
        panel.set_evaluation(mock_evaluation)
        panel.clear()
        assert "Paste a rare item" in panel.affixes_text.toPlainText()

    def test_clear_resets_meta_label(self, panel, mock_evaluation):
        """Should reset meta label."""
        panel.set_evaluation(mock_evaluation)
        panel.clear()
        assert "Waiting" in panel.meta_label.text()

    def test_clear_resets_evaluation(self, panel, mock_evaluation):
        """Should reset evaluation reference."""
        panel.set_evaluation(mock_evaluation)
        panel.clear()
        assert panel._evaluation is None


# =============================================================================
# Tier Color Tests
# =============================================================================


class TestTierColors:
    """Tests for tier color styling."""

    def test_excellent_tier_green(self, panel, mock_evaluation):
        """Excellent tier should be green."""
        mock_evaluation.tier = "excellent"
        panel.set_evaluation(mock_evaluation)
        assert "#22dd22" in panel.tier_label.styleSheet()

    def test_good_tier_blue(self, panel, mock_evaluation):
        """Good tier should be blue."""
        mock_evaluation.tier = "good"
        panel.set_evaluation(mock_evaluation)
        assert "#4488ff" in panel.tier_label.styleSheet()

    def test_average_tier_orange(self, panel, mock_evaluation):
        """Average tier should be orange."""
        mock_evaluation.tier = "average"
        panel.set_evaluation(mock_evaluation)
        assert "#ff8800" in panel.tier_label.styleSheet()

    def test_vendor_tier_red(self, panel, mock_evaluation):
        """Vendor tier should be red."""
        mock_evaluation.tier = "vendor"
        panel.set_evaluation(mock_evaluation)
        assert "#dd2222" in panel.tier_label.styleSheet()
