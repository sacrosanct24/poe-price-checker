# tests/unit/gui_qt/feedback/test_rate_limit_indicator.py
"""Tests for RateLimitIndicator widget."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QFrame, QProgressBar, QLabel

from gui_qt.feedback.rate_limit_indicator import (
    RateLimitStatus,
    STATUS_CONFIGS,
    CooldownProgressBar,
    RateLimitIndicator,
    DetailedRateLimitDisplay,
)


# =============================================================================
# RateLimitStatus Tests
# =============================================================================


class TestRateLimitStatus:
    """Tests for RateLimitStatus enum."""

    def test_ready_value(self):
        """READY should have 'ready' value."""
        assert RateLimitStatus.READY.value == "ready"

    def test_active_value(self):
        """ACTIVE should have 'active' value."""
        assert RateLimitStatus.ACTIVE.value == "active"

    def test_cooling_down_value(self):
        """COOLING_DOWN should have 'cooling' value."""
        assert RateLimitStatus.COOLING_DOWN.value == "cooling"

    def test_rate_limited_value(self):
        """RATE_LIMITED should have 'limited' value."""
        assert RateLimitStatus.RATE_LIMITED.value == "limited"

    def test_all_statuses_in_configs(self):
        """All statuses should have configuration."""
        for status in RateLimitStatus:
            assert status in STATUS_CONFIGS
            assert "icon" in STATUS_CONFIGS[status]
            assert "color" in STATUS_CONFIGS[status]
            assert "label" in STATUS_CONFIGS[status]
            assert "tooltip" in STATUS_CONFIGS[status]


# =============================================================================
# CooldownProgressBar Tests
# =============================================================================


class TestCooldownProgressBar:
    """Tests for CooldownProgressBar widget."""

    @pytest.fixture
    def progress(self, qtbot):
        """Create CooldownProgressBar instance."""
        p = CooldownProgressBar()
        qtbot.addWidget(p)
        return p

    def test_inherits_from_qprogressbar(self, progress):
        """CooldownProgressBar should be a QProgressBar."""
        assert isinstance(progress, QProgressBar)

    def test_fixed_height(self, progress):
        """Progress bar should have fixed height."""
        assert progress.height() == 4

    def test_text_not_visible(self, progress):
        """Text should not be visible."""
        assert not progress.isTextVisible()

    def test_range_is_0_to_100(self, progress):
        """Range should be 0 to 100."""
        assert progress.minimum() == 0
        assert progress.maximum() == 100

    def test_initial_value_is_100(self, progress):
        """Initial value should be 100 (full)."""
        assert progress.value() == 100

    def test_set_color(self, progress):
        """set_color should update stylesheet."""
        progress.set_color("#FF0000")
        stylesheet = progress.styleSheet()
        assert "#FF0000" in stylesheet


# =============================================================================
# RateLimitIndicator Tests
# =============================================================================


class TestRateLimitIndicator:
    """Tests for RateLimitIndicator widget."""

    @pytest.fixture
    def indicator(self, qtbot):
        """Create RateLimitIndicator instance."""
        ind = RateLimitIndicator()
        qtbot.addWidget(ind)
        return ind

    def test_inherits_from_qframe(self, indicator):
        """RateLimitIndicator should be a QFrame."""
        assert isinstance(indicator, QFrame)

    def test_initial_status_is_ready(self, indicator):
        """Initial status should be READY."""
        assert indicator.status() == RateLimitStatus.READY
        assert indicator.is_ready()

    def test_has_icon_label(self, indicator):
        """Indicator should have icon label."""
        assert indicator._icon_label is not None
        assert isinstance(indicator._icon_label, QLabel)

    def test_has_status_label(self, indicator):
        """Indicator should have status label."""
        assert indicator._status_label is not None
        assert isinstance(indicator._status_label, QLabel)

    def test_has_progress_bar(self, indicator):
        """Indicator should have progress bar."""
        assert indicator._progress is not None
        assert isinstance(indicator._progress, CooldownProgressBar)

    def test_progress_hidden_initially(self, indicator):
        """Progress bar should be hidden when READY."""
        assert not indicator._progress.isVisible()

    def test_set_status_to_active(self, indicator):
        """set_status should update to ACTIVE."""
        indicator.set_status(RateLimitStatus.ACTIVE)
        assert indicator.status() == RateLimitStatus.ACTIVE
        assert not indicator.is_ready()

    def test_set_status_to_cooling_down(self, indicator):
        """set_status should update to COOLING_DOWN."""
        indicator.set_status(RateLimitStatus.COOLING_DOWN, remaining_seconds=30)
        assert indicator.status() == RateLimitStatus.COOLING_DOWN
        assert indicator._remaining_seconds == 30

    def test_set_status_to_rate_limited(self, indicator):
        """set_status should update to RATE_LIMITED."""
        indicator.set_status(RateLimitStatus.RATE_LIMITED, remaining_seconds=60)
        assert indicator.status() == RateLimitStatus.RATE_LIMITED
        assert indicator._remaining_seconds == 60

    def test_progress_visible_when_cooling(self, indicator):
        """Progress bar should be visible when cooling down."""
        indicator.set_status(
            RateLimitStatus.COOLING_DOWN,
            remaining_seconds=30,
            total_seconds=60,
        )
        # Check not hidden (isVisible requires parent shown)
        assert not indicator._progress.isHidden()

    def test_progress_value_calculated(self, indicator):
        """Progress value should be calculated from remaining/total."""
        indicator.set_status(
            RateLimitStatus.COOLING_DOWN,
            remaining_seconds=30,
            total_seconds=60,
        )
        # 30/60 = 50%
        assert indicator._progress.value() == 50

    def test_status_label_shows_seconds(self, indicator):
        """Status label should show seconds when cooling down."""
        indicator.set_status(
            RateLimitStatus.COOLING_DOWN,
            remaining_seconds=45,
        )
        assert "45s" in indicator._status_label.text()

    def test_set_queue_size(self, indicator):
        """set_queue_size should update queue display."""
        indicator.set_queue_size(3)
        assert indicator._queue_size == 3
        assert not indicator._queue_label.isHidden()
        assert "3" in indicator._queue_label.text()

    def test_queue_hidden_when_zero(self, indicator):
        """Queue label should be hidden when size is 0."""
        indicator.set_queue_size(0)
        assert indicator._queue_label.isHidden()

    def test_status_changed_signal_emitted(self, qtbot, indicator):
        """status_changed should emit when status changes."""
        with qtbot.waitSignal(indicator.status_changed, timeout=1000) as blocker:
            indicator.set_status(RateLimitStatus.ACTIVE)
        assert blocker.args == [RateLimitStatus.ACTIVE]

    def test_status_changed_not_emitted_for_same_status(self, qtbot, indicator):
        """status_changed should not emit when setting same status."""
        from PyQt6.QtWidgets import QApplication

        signals = []
        indicator.status_changed.connect(lambda s: signals.append(s))
        indicator.set_status(RateLimitStatus.READY)  # Already READY
        QApplication.processEvents()
        assert len(signals) == 0

    def test_tooltip_includes_queue_info(self, indicator):
        """Tooltip should include queue info when queued."""
        indicator.set_queue_size(5)
        tooltip = indicator.toolTip()
        assert "5" in tooltip
        assert "queued" in tooltip.lower()

    def test_countdown_timer_created_when_cooling(self, indicator):
        """Timer should be created when cooling down."""
        indicator.set_status(
            RateLimitStatus.COOLING_DOWN,
            remaining_seconds=10,
        )
        assert indicator._timer is not None
        assert isinstance(indicator._timer, QTimer)

    def test_countdown_timer_stopped_when_ready(self, indicator):
        """Timer should be stopped when status becomes READY."""
        indicator.set_status(
            RateLimitStatus.COOLING_DOWN,
            remaining_seconds=10,
        )
        indicator.set_status(RateLimitStatus.READY)
        assert indicator._timer is None

    def test_is_ready_true_when_ready(self, indicator):
        """is_ready should return True when READY."""
        assert indicator.is_ready() is True

    def test_is_ready_false_when_active(self, indicator):
        """is_ready should return False when ACTIVE."""
        indicator.set_status(RateLimitStatus.ACTIVE)
        assert indicator.is_ready() is False

    def test_is_ready_false_when_limited(self, indicator):
        """is_ready should return False when RATE_LIMITED."""
        indicator.set_status(RateLimitStatus.RATE_LIMITED)
        assert indicator.is_ready() is False


@pytest.mark.skipif(
    "sys.platform == 'win32'",
    reason="QTimer + qtbot.wait() causes crashes on Windows CI"
)
class TestRateLimitIndicatorCountdown:
    """Tests for countdown functionality.

    Note: Skipped on Windows due to QTimer + qtbot.wait() compatibility issues.
    """

    @pytest.fixture
    def indicator(self, qtbot):
        """Create indicator."""
        ind = RateLimitIndicator()
        qtbot.addWidget(ind)
        return ind

    def test_countdown_decrements(self, qtbot, indicator):
        """Countdown should decrement each second."""
        indicator.set_status(
            RateLimitStatus.COOLING_DOWN,
            remaining_seconds=3,
        )

        # Wait for one tick
        qtbot.wait(1100)

        assert indicator._remaining_seconds == 2

    def test_countdown_reaches_ready(self, qtbot, indicator):
        """Countdown should set READY when reaching 0."""
        indicator.set_status(
            RateLimitStatus.COOLING_DOWN,
            remaining_seconds=1,
        )

        # Wait for countdown to complete
        qtbot.wait(1200)

        assert indicator.status() == RateLimitStatus.READY
        assert indicator._timer is None


# =============================================================================
# DetailedRateLimitDisplay Tests
# =============================================================================


class TestDetailedRateLimitDisplay:
    """Tests for DetailedRateLimitDisplay widget."""

    @pytest.fixture
    def display(self, qtbot):
        """Create DetailedRateLimitDisplay instance."""
        d = DetailedRateLimitDisplay()
        qtbot.addWidget(d)
        return d

    def test_inherits_from_qframe(self, display):
        """DetailedRateLimitDisplay should be a QFrame."""
        assert isinstance(display, QFrame)

    def test_no_data_label_visible_initially(self, display):
        """No data label should be visible when empty."""
        assert not display._no_data_label.isHidden()

    def test_set_api_limits_hides_no_data(self, display):
        """set_api_limits should hide no data label."""
        display.set_api_limits({
            "poe.ninja": {"remaining": 50, "total": 100},
        })
        assert display._no_data_label.isHidden()

    def test_set_api_limits_creates_rows(self, display):
        """set_api_limits should create rows for each API."""
        display.set_api_limits({
            "poe.ninja": {"remaining": 50, "total": 100},
            "poe.watch": {"remaining": 25, "total": 50},
        })

        # Should have 2 rows
        assert display._limits_layout.count() == 2

    def test_set_api_limits_clears_previous(self, display):
        """set_api_limits should clear previous rows."""
        display.set_api_limits({
            "api1": {"remaining": 50, "total": 100},
            "api2": {"remaining": 50, "total": 100},
        })
        display.set_api_limits({
            "api3": {"remaining": 50, "total": 100},
        })

        assert display._limits_layout.count() == 1

    def test_empty_limits_shows_no_data(self, display):
        """Empty limits should show no data label."""
        display.set_api_limits({
            "api": {"remaining": 50, "total": 100},
        })
        display.set_api_limits({})

        assert not display._no_data_label.isHidden()

    def test_api_row_contains_progress(self, display):
        """API row should contain progress bar."""
        display.set_api_limits({
            "test_api": {"remaining": 75, "total": 100},
        })

        row = display._limits_layout.itemAt(0).widget()
        # Find progress bar in row
        progress_bars = row.findChildren(QProgressBar)
        assert len(progress_bars) == 1
        assert progress_bars[0].value() == 75


# =============================================================================
# STATUS_CONFIGS Tests
# =============================================================================


class TestStatusConfigs:
    """Tests for STATUS_CONFIGS dictionary."""

    def test_ready_config(self):
        """READY config should have green color."""
        config = STATUS_CONFIGS[RateLimitStatus.READY]
        assert "#4CAF50" in config["color"]  # Green
        assert "Ready" in config["label"]

    def test_active_config(self):
        """ACTIVE config should have blue color."""
        config = STATUS_CONFIGS[RateLimitStatus.ACTIVE]
        assert "#2196F3" in config["color"]  # Blue
        assert "Working" in config["label"]

    def test_cooling_config(self):
        """COOLING_DOWN config should have orange color."""
        config = STATUS_CONFIGS[RateLimitStatus.COOLING_DOWN]
        assert "#FF9800" in config["color"]  # Orange
        assert "Cooling" in config["label"]

    def test_limited_config(self):
        """RATE_LIMITED config should have red color."""
        config = STATUS_CONFIGS[RateLimitStatus.RATE_LIMITED]
        assert "#F44336" in config["color"]  # Red
        assert "limited" in config["label"].lower()
