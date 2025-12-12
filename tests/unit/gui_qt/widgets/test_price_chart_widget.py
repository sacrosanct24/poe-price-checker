"""
Tests for PriceChartWidget.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# Check if matplotlib is available
try:
    import matplotlib
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


@pytest.fixture
def mock_chart_series():
    """Create a mock ChartSeries for testing."""
    mock = Mock()
    mock.name = "Test Item"
    mock.data_points = [
        Mock(date=datetime.now() - timedelta(days=2), chaos_value=100.0, divine_value=0.5),
        Mock(date=datetime.now() - timedelta(days=1), chaos_value=110.0, divine_value=0.55),
        Mock(date=datetime.now(), chaos_value=105.0, divine_value=0.52),
    ]
    return mock


@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestPriceChartWidgetWithMatplotlib:
    """Tests for PriceChartWidget when matplotlib is available."""

    def test_import(self):
        """Test that the widget can be imported."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget, MATPLOTLIB_AVAILABLE
        assert MATPLOTLIB_AVAILABLE is True

    def test_time_ranges_defined(self):
        """Test that time ranges are defined."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        assert len(PriceChartWidget.TIME_RANGES) == 4
        # Check expected ranges
        keys = [r[0] for r in PriceChartWidget.TIME_RANGES]
        assert "7d" in keys
        assert "30d" in keys
        assert "90d" in keys
        assert "all" in keys

    def test_chart_colors_defined(self):
        """Test that chart colors are defined."""
        from gui_qt.widgets.price_chart_widget import CHART_COLORS
        assert "line" in CHART_COLORS
        assert "background" in CHART_COLORS
        assert "grid" in CHART_COLORS

    @pytest.mark.unit
    def test_widget_creation(self, qapp):
        """Test creating the widget."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        widget = PriceChartWidget()
        assert widget is not None
        assert widget.figure is not None
        assert widget.canvas is not None
        assert widget.ax is not None

    @pytest.mark.unit
    def test_get_current_days_default(self, qapp):
        """Test default time range is 30 days."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        widget = PriceChartWidget()
        assert widget.get_current_days() == 30

    @pytest.mark.unit
    def test_set_time_range(self, qapp):
        """Test setting time range programmatically."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        widget = PriceChartWidget()

        widget.set_time_range(7)
        assert widget.get_current_days() == 7

        widget.set_time_range(90)
        assert widget.get_current_days() == 90

        widget.set_time_range(0)  # All time
        assert widget.get_current_days() == 0

    @pytest.mark.unit
    def test_clear(self, qapp):
        """Test clearing the chart."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        widget = PriceChartWidget()
        widget.clear()
        # Should not raise any errors
        assert widget._current_series is None

    @pytest.mark.unit
    def test_plot_series(self, qapp, mock_chart_series):
        """Test plotting a series."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        widget = PriceChartWidget()
        widget.plot_series(mock_chart_series)

        # Series should be stored
        assert widget._current_series == mock_chart_series

    @pytest.mark.unit
    def test_plot_empty_series(self, qapp):
        """Test plotting an empty series."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        widget = PriceChartWidget()

        empty_series = Mock()
        empty_series.name = "Empty"
        empty_series.data_points = []

        widget.plot_series(empty_series)
        # Should handle gracefully without errors

    @pytest.mark.unit
    def test_time_range_changed_signal(self, qapp):
        """Test that time_range_changed signal is emitted."""
        from gui_qt.widgets.price_chart_widget import PriceChartWidget
        widget = PriceChartWidget()

        signal_received = []
        widget.time_range_changed.connect(lambda days: signal_received.append(days))

        # Change range via combo box
        widget._range_combo.setCurrentIndex(0)  # 7 days

        assert len(signal_received) > 0


class TestPriceChartWidgetFallback:
    """Tests for PriceChartWidget fallback behavior."""

    def test_matplotlib_flag_exists(self):
        """Test that MATPLOTLIB_AVAILABLE flag exists."""
        from gui_qt.widgets.price_chart_widget import MATPLOTLIB_AVAILABLE
        assert isinstance(MATPLOTLIB_AVAILABLE, bool)


@pytest.mark.unit
class TestChartDataPointProperties:
    """Tests for chart data point validation."""

    def test_data_point_values(self):
        """Test that data points have expected structure."""
        from core.services.chart_data_service import PriceDataPoint

        now = datetime.now()
        point = PriceDataPoint(
            date=now,
            chaos_value=150.5,
            divine_value=0.75
        )

        assert point.date == now
        assert point.chaos_value == 150.5
        assert point.divine_value == 0.75

    def test_data_point_without_divine(self):
        """Test data point without divine value."""
        from core.services.chart_data_service import PriceDataPoint

        point = PriceDataPoint(
            date=datetime.now(),
            chaos_value=100.0
        )

        assert point.divine_value is None
