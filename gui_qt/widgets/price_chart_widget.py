"""
Price chart widget using matplotlib.

Displays price history as an interactive line chart.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSizePolicy,
)

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvasQTAgg = None
    Figure = None

if TYPE_CHECKING:
    from core.services.chart_data_service import ChartSeries

logger = logging.getLogger(__name__)

# Chart colors matching PoE theme
CHART_COLORS = {
    "line": "#E6B800",  # Gold
    "fill": "#E6B80033",  # Gold with transparency
    "grid": "#444444",
    "background": "#1a1a1a",
    "text": "#cccccc",
    "axis": "#666666",
}


class PriceChartWidget(QWidget):
    """
    Interactive price chart widget.

    Signals:
        time_range_changed(int): Emitted when time range selector changes.
    """

    time_range_changed = pyqtSignal(int)

    TIME_RANGES = [
        ("7d", "7 Days", 7),
        ("30d", "30 Days", 30),
        ("90d", "90 Days", 90),
        ("all", "All Time", 0),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_series: Optional["ChartSeries"] = None
        self._current_days = 30

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header with controls
        header = QHBoxLayout()
        header.setSpacing(8)

        self._title_label = QLabel("Price History")
        self._title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self._title_label)

        header.addStretch()

        # Time range selector
        header.addWidget(QLabel("Range:"))
        self._range_combo = QComboBox()
        self._range_combo.setMaximumWidth(100)
        for key, label, _ in self.TIME_RANGES:
            self._range_combo.addItem(label, key)
        self._range_combo.setCurrentIndex(1)  # Default to 30 days
        self._range_combo.currentIndexChanged.connect(self._on_range_changed)
        header.addWidget(self._range_combo)

        layout.addLayout(header)

        # Chart area
        if MATPLOTLIB_AVAILABLE:
            self._setup_matplotlib_chart(layout)
        else:
            self._setup_fallback_message(layout)

    def _setup_matplotlib_chart(self, layout: QVBoxLayout) -> None:
        """Set up the matplotlib chart."""
        # Create figure with dark theme
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.figure.patch.set_facecolor(CHART_COLORS["background"])

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.ax = self.figure.add_subplot(111)
        self._style_axes()

        layout.addWidget(self.canvas, 1)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: palette(mid); font-size: 11px;")
        layout.addWidget(self._status_label)

    def _setup_fallback_message(self, layout: QVBoxLayout) -> None:
        """Set up fallback when matplotlib is not available."""
        self.figure = None
        self.canvas = None
        self.ax = None

        fallback = QLabel(
            "Charts require matplotlib.\n"
            "Install with: pip install matplotlib"
        )
        fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fallback.setStyleSheet("color: palette(mid); padding: 40px;")
        layout.addWidget(fallback, 1)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

    def _style_axes(self) -> None:
        """Apply dark theme styling to axes."""
        if not self.ax:
            return

        self.ax.set_facecolor(CHART_COLORS["background"])

        # Style spines
        for spine in self.ax.spines.values():
            spine.set_color(CHART_COLORS["axis"])

        # Style ticks
        self.ax.tick_params(colors=CHART_COLORS["text"], which="both")

        # Style labels
        self.ax.xaxis.label.set_color(CHART_COLORS["text"])
        self.ax.yaxis.label.set_color(CHART_COLORS["text"])

    def _on_range_changed(self, index: int) -> None:
        """Handle time range selection change."""
        if 0 <= index < len(self.TIME_RANGES):
            _, _, days = self.TIME_RANGES[index]
            self._current_days = days
            self.time_range_changed.emit(days)

            # Refresh chart if we have data
            if self._current_series:
                self.plot_series(self._current_series)

    def plot_series(self, series: "ChartSeries", title: Optional[str] = None) -> None:
        """
        Plot a price series on the chart.

        Args:
            series: ChartSeries containing data points
            title: Optional custom title
        """
        if not MATPLOTLIB_AVAILABLE or not self.ax:
            return

        self._current_series = series
        self.ax.clear()
        self._style_axes()

        if not series or not series.data_points:
            self._show_no_data()
            return

        # Filter by time range
        data_points = series.data_points
        if self._current_days > 0:
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=self._current_days)
            data_points = [p for p in data_points if p.date >= cutoff]

        if not data_points:
            self._show_no_data()
            return

        dates = [p.date for p in data_points]
        values = [p.chaos_value for p in data_points]

        # Plot line
        self.ax.plot(
            dates, values,
            color=CHART_COLORS["line"],
            linewidth=2,
            marker="o",
            markersize=4 if len(dates) < 50 else 0
        )

        # Fill under line
        self.ax.fill_between(
            dates, values,
            color=CHART_COLORS["fill"],
            alpha=0.3
        )

        # Configure axes
        self.ax.set_ylabel("Chaos Value", color=CHART_COLORS["text"])
        self.ax.yaxis.set_major_formatter(
            lambda x, p: f"{x:,.0f}" if x >= 1000 else f"{x:.1f}"
        )

        # Format dates
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.figure.autofmt_xdate()

        # Grid
        self.ax.grid(True, color=CHART_COLORS["grid"], alpha=0.3, linestyle="--")
        self.ax.set_axisbelow(True)

        # Title
        chart_title = title or series.name
        self._title_label.setText(f"Price History: {chart_title}")

        # Stats
        if values:
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            self._status_label.setText(
                f"{len(data_points)} data points | "
                f"Min: {min_val:,.0f}c | Max: {max_val:,.0f}c | Avg: {avg_val:,.0f}c"
            )

        self.canvas.draw()

    def _show_no_data(self) -> None:
        """Show no data message on chart."""
        if not self.ax:
            return

        self.ax.text(
            0.5, 0.5,
            "No data available for selected range",
            ha="center", va="center",
            transform=self.ax.transAxes,
            color=CHART_COLORS["text"],
            fontsize=12
        )
        self._status_label.setText("No data")
        self.canvas.draw()

    def clear(self) -> None:
        """Clear the chart."""
        self._current_series = None
        if self.ax:
            self.ax.clear()
            self._style_axes()
            self.canvas.draw()
        self._title_label.setText("Price History")
        self._status_label.setText("")

    def get_current_days(self) -> int:
        """Get the current time range in days."""
        return self._current_days

    def set_time_range(self, days: int) -> None:
        """Set the time range programmatically."""
        for i, (_, _, d) in enumerate(self.TIME_RANGES):
            if d == days:
                self._range_combo.setCurrentIndex(i)
                break
