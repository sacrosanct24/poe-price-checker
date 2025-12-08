"""
Loot Dashboard Window - Analytics for loot tracking sessions.

Displays:
- Session controls (start/stop, auto-track toggle)
- Live stats (duration, maps, drops, chaos/hour)
- Top drops table
- Session history
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from gui_qt.styles import apply_window_icon

if TYPE_CHECKING:
    from core.interfaces import IAppContext
    from core.loot_session import LootDrop, LootSession, MapRun
    from gui_qt.controllers.loot_tracking_controller import LootTrackingController

logger = logging.getLogger(__name__)


class TopDropsModel(QAbstractTableModel):
    """Table model for top drops."""

    COLUMNS = [
        ("item_name", "Item", 200),
        ("stack_size", "Qty", 50),
        ("chaos_value", "Value (c)", 80),
        ("rarity", "Rarity", 80),
        ("detected_at", "Time", 100),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row_data = self._data[index.row()]
        col_key = self.COLUMNS[index.column()][0]
        value = row_data.get(col_key, "")

        if role == Qt.ItemDataRole.DisplayRole:
            if col_key == "chaos_value":
                try:
                    total = float(value) * row_data.get("stack_size", 1)
                    return f"{total:.1f}"
                except (ValueError, TypeError):
                    return "0.0"
            elif col_key == "detected_at":
                if isinstance(value, datetime):
                    return value.strftime("%H:%M:%S")
                elif isinstance(value, str):
                    try:
                        dt = datetime.fromisoformat(value)
                        return dt.strftime("%H:%M:%S")
                    except ValueError:
                        return value
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("stack_size", "chaos_value"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ToolTipRole:
            # Show full item details on hover
            return f"{row_data.get('item_name', '')} - {row_data.get('rarity', '')}"

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.COLUMNS[section][1]
        return None

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Set the table data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def clear(self):
        """Clear all data."""
        self.beginResetModel()
        self._data = []
        self.endResetModel()


class MapRunsModel(QAbstractTableModel):
    """Table model for map runs."""

    COLUMNS = [
        ("map_name", "Map", 150),
        ("area_level", "Level", 50),
        ("drop_count", "Drops", 60),
        ("total_chaos_value", "Value (c)", 80),
        ("duration", "Duration", 80),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row_data = self._data[index.row()]
        col_key = self.COLUMNS[index.column()][0]
        value = row_data.get(col_key, "")

        if role == Qt.ItemDataRole.DisplayRole:
            if col_key == "total_chaos_value":
                try:
                    return f"{float(value):.1f}"
                except (ValueError, TypeError):
                    return "0.0"
            elif col_key == "duration":
                seconds = row_data.get("duration_seconds", 0)
                if seconds:
                    minutes = int(seconds // 60)
                    secs = int(seconds % 60)
                    return f"{minutes}:{secs:02d}"
                return "-"
            elif col_key == "area_level":
                return str(value) if value else "-"
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("area_level", "drop_count", "total_chaos_value"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.COLUMNS[section][1]
        return None

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Set the table data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def clear(self):
        """Clear all data."""
        self.beginResetModel()
        self._data = []
        self.endResetModel()


class LootDashboardWindow(QDialog):
    """Window for loot tracking dashboard."""

    def __init__(
        self,
        ctx: "IAppContext",
        controller: "LootTrackingController",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._ctx = ctx
        self._controller = controller

        self.setWindowTitle("Loot Tracking Dashboard")
        self.setMinimumSize(700, 550)
        self.resize(900, 700)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._connect_signals()
        self._start_timer()
        self._update_ui()

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Session controls
        self._create_controls(layout)

        # Main content area with tabs
        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        # Current Session tab
        current_tab = QWidget()
        self._create_current_session_tab(current_tab)
        tabs.addTab(current_tab, "Current Session")

        # History tab
        history_tab = QWidget()
        self._create_history_tab(history_tab)
        tabs.addTab(history_tab, "Session History")

        # Status bar
        self._status_label = QLabel()
        self._status_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._status_label)

    def _create_controls(self, parent_layout: QVBoxLayout) -> None:
        """Create session control widgets."""
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 8, 8, 8)

        # Start button
        self._start_btn = QPushButton("Start Session")
        self._start_btn.setMinimumWidth(100)
        self._start_btn.clicked.connect(self._on_start_clicked)
        controls_layout.addWidget(self._start_btn)

        # Stop button
        self._stop_btn = QPushButton("Stop Session")
        self._stop_btn.setMinimumWidth(100)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        controls_layout.addWidget(self._stop_btn)

        controls_layout.addSpacing(20)

        # Auto-track checkbox
        self._auto_track_cb = QCheckBox("Auto-track (zone detection)")
        self._auto_track_cb.setToolTip(
            "Automatically start tracking when entering maps\n"
            "and take snapshots on hideout transitions"
        )
        self._auto_track_cb.toggled.connect(self._on_auto_track_toggled)
        controls_layout.addWidget(self._auto_track_cb)

        controls_layout.addStretch()

        # Monitoring indicator
        self._monitoring_label = QLabel()
        self._monitoring_label.setStyleSheet("font-weight: bold;")
        controls_layout.addWidget(self._monitoring_label)

        # Manual snapshot button
        self._snapshot_btn = QPushButton("Take Snapshot")
        self._snapshot_btn.setToolTip("Manually take a stash snapshot")
        self._snapshot_btn.clicked.connect(self._on_snapshot_clicked)
        controls_layout.addWidget(self._snapshot_btn)

        parent_layout.addWidget(controls_frame)

    def _create_current_session_tab(self, tab: QWidget) -> None:
        """Create the current session tab content."""
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # Live stats panel
        stats_group = QGroupBox("Live Statistics")
        stats_layout = QHBoxLayout(stats_group)

        # Stats columns
        self._create_stat_display(stats_layout, "Duration", "_duration_label")
        self._add_stat_separator(stats_layout)
        self._create_stat_display(stats_layout, "Maps", "_maps_label")
        self._add_stat_separator(stats_layout)
        self._create_stat_display(stats_layout, "Drops", "_drops_label")
        self._add_stat_separator(stats_layout)
        self._create_stat_display(stats_layout, "Total Value", "_value_label")
        self._add_stat_separator(stats_layout)
        self._create_stat_display(stats_layout, "Chaos/Hour", "_rate_label")
        stats_layout.addStretch()

        layout.addWidget(stats_group)

        # Splitter for tables
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # Top drops table
        drops_group = QGroupBox("Top Drops")
        drops_layout = QVBoxLayout(drops_group)

        self._drops_model = TopDropsModel(self)
        self._drops_table = QTableView()
        self._drops_table.setModel(self._drops_model)
        self._drops_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._drops_table.setAlternatingRowColors(True)
        self._drops_table.setSortingEnabled(True)

        # Column widths
        for i, (_, _, width) in enumerate(TopDropsModel.COLUMNS):
            self._drops_table.setColumnWidth(i, width)
        self._drops_table.horizontalHeader().setStretchLastSection(True)

        drops_layout.addWidget(self._drops_table)
        splitter.addWidget(drops_group)

        # Map runs table
        maps_group = QGroupBox("Map Runs")
        maps_layout = QVBoxLayout(maps_group)

        self._maps_model = MapRunsModel(self)
        self._maps_table = QTableView()
        self._maps_table.setModel(self._maps_model)
        self._maps_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._maps_table.setAlternatingRowColors(True)

        # Column widths
        for i, (_, _, width) in enumerate(MapRunsModel.COLUMNS):
            self._maps_table.setColumnWidth(i, width)
        self._maps_table.horizontalHeader().setStretchLastSection(True)

        maps_layout.addWidget(self._maps_table)
        splitter.addWidget(maps_group)

        # Set initial splitter sizes
        splitter.setSizes([500, 400])

    def _create_history_tab(self, tab: QWidget) -> None:
        """Create the session history tab content."""
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # Controls
        controls = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_history)
        controls.addWidget(refresh_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # History list
        self._history_list = QListWidget()
        self._history_list.setAlternatingRowColors(True)
        self._history_list.itemDoubleClicked.connect(self._on_history_item_clicked)
        layout.addWidget(self._history_list)

        # Selected session details
        details_group = QGroupBox("Session Details")
        details_layout = QFormLayout(details_group)

        self._hist_name_label = QLabel("-")
        details_layout.addRow("Name:", self._hist_name_label)

        self._hist_date_label = QLabel("-")
        details_layout.addRow("Date:", self._hist_date_label)

        self._hist_duration_label = QLabel("-")
        details_layout.addRow("Duration:", self._hist_duration_label)

        self._hist_maps_label = QLabel("-")
        details_layout.addRow("Maps:", self._hist_maps_label)

        self._hist_drops_label = QLabel("-")
        details_layout.addRow("Drops:", self._hist_drops_label)

        self._hist_value_label = QLabel("-")
        details_layout.addRow("Total Value:", self._hist_value_label)

        self._hist_rate_label = QLabel("-")
        details_layout.addRow("Chaos/Hour:", self._hist_rate_label)

        layout.addWidget(details_group)

        # Load initial history
        self._load_history()

    def _create_stat_display(
        self,
        layout: QHBoxLayout,
        label: str,
        attr_name: str,
    ) -> None:
        """Create a stat display widget."""
        container = QVBoxLayout()
        container.setSpacing(2)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: gray; font-size: 11px;")
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container.addWidget(label_widget)

        value_widget = QLabel("--")
        value_widget.setStyleSheet("font-size: 18px; font-weight: bold;")
        value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setattr(self, attr_name, value_widget)
        container.addWidget(value_widget)

        layout.addLayout(container)

    def _add_stat_separator(self, layout: QHBoxLayout) -> None:
        """Add a visual separator between stats."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #555;")
        layout.addWidget(sep)

    def _connect_signals(self) -> None:
        """Connect controller signals to UI updates."""
        self._controller.session_started.connect(self._on_session_started)
        self._controller.session_ended.connect(self._on_session_ended)
        self._controller.session_state_changed.connect(self._on_state_changed)
        self._controller.drops_detected.connect(self._on_drops_detected)
        self._controller.stats_updated.connect(self._on_stats_updated)
        self._controller.status_message.connect(self._on_status_message)
        self._controller.snapshot_started.connect(self._on_snapshot_started)
        self._controller.snapshot_completed.connect(self._on_snapshot_completed)
        self._controller.snapshot_error.connect(self._on_snapshot_error)
        self._controller.high_value_drop.connect(self._on_high_value_drop)

    def _start_timer(self) -> None:
        """Start the UI update timer."""
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_live_stats)
        self._update_timer.start(1000)  # Update every second

    def _update_ui(self) -> None:
        """Update UI to reflect current state."""
        session = self._controller.get_current_session()
        is_active = session is not None

        self._start_btn.setEnabled(not is_active)
        self._stop_btn.setEnabled(is_active)

        self._auto_track_cb.setChecked(self._controller.is_auto_tracking_enabled())

        # Update monitoring indicator
        if self._controller.is_monitoring():
            self._monitoring_label.setText("Monitoring Active")
            self._monitoring_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self._monitoring_label.setText("Monitoring Stopped")
            self._monitoring_label.setStyleSheet("color: gray; font-weight: bold;")

        self._update_live_stats()

    def _update_live_stats(self) -> None:
        """Update live statistics display."""
        session = self._controller.get_current_session()

        if not session:
            self._duration_label.setText("--")
            self._maps_label.setText("--")
            self._drops_label.setText("--")
            self._value_label.setText("--")
            self._rate_label.setText("--")
            return

        # Duration
        duration = session.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours:
                self._duration_label.setText(f"{hours}h {minutes}m")
            else:
                self._duration_label.setText(f"{minutes}:{seconds:02d}")
        else:
            self._duration_label.setText("0:00")

        # Maps
        self._maps_label.setText(str(session.total_maps))

        # Drops
        self._drops_label.setText(str(session.total_drops))

        # Value
        total_value = session.total_chaos_value
        if total_value >= 1000:
            self._value_label.setText(f"{total_value / 1000:.1f}k c")
        else:
            self._value_label.setText(f"{total_value:.0f}c")

        # Rate
        rate = session.chaos_per_hour
        if rate >= 1000:
            self._rate_label.setText(f"{rate / 1000:.1f}k")
        else:
            self._rate_label.setText(f"{rate:.0f}")

        # Update tables
        self._update_drops_table(session)
        self._update_maps_table(session)

    def _update_drops_table(self, session: "LootSession") -> None:
        """Update the top drops table."""
        drops_data = []
        for drop in session.top_drops[:20]:
            drops_data.append({
                "item_name": drop.item_name,
                "stack_size": drop.stack_size,
                "chaos_value": drop.chaos_value,
                "rarity": drop.rarity,
                "detected_at": drop.detected_at,
            })
        self._drops_model.set_data(drops_data)

    def _update_maps_table(self, session: "LootSession") -> None:
        """Update the map runs table."""
        maps_data = []
        for run in reversed(session.map_runs[-20:]):  # Most recent first
            maps_data.append({
                "map_name": run.map_name,
                "area_level": run.area_level,
                "drop_count": run.drop_count,
                "total_chaos_value": run.total_chaos_value,
                "duration_seconds": run.duration_seconds,
            })
        self._maps_model.set_data(maps_data)

    def _load_history(self) -> None:
        """Load session history into the list."""
        self._history_list.clear()

        history = self._controller.load_session_history(limit=50)
        for session in history:
            # Format display text
            name = session.get("name", "Unknown")
            date = session.get("started_at", "")
            if isinstance(date, str) and date:
                try:
                    dt = datetime.fromisoformat(date)
                    date = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass

            total_chaos = session.get("total_chaos_value", 0)
            maps = session.get("total_maps", 0)

            text = f"{name} - {date} - {maps} maps - {total_chaos:.0f}c"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, session)
            self._history_list.addItem(item)

    def _on_history_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on history item."""
        session = item.data(Qt.ItemDataRole.UserRole)
        if not session:
            return

        # Update details panel
        self._hist_name_label.setText(session.get("name", "-"))

        date = session.get("started_at", "")
        if isinstance(date, str) and date:
            try:
                dt = datetime.fromisoformat(date)
                self._hist_date_label.setText(dt.strftime("%Y-%m-%d %H:%M"))
            except ValueError:
                self._hist_date_label.setText(date)
        else:
            self._hist_date_label.setText("-")

        # Calculate duration
        started = session.get("started_at")
        ended = session.get("ended_at")
        if started and ended:
            try:
                start_dt = datetime.fromisoformat(started)
                end_dt = datetime.fromisoformat(ended)
                duration = end_dt - start_dt
                total_mins = int(duration.total_seconds() // 60)
                hours = total_mins // 60
                mins = total_mins % 60
                if hours:
                    self._hist_duration_label.setText(f"{hours}h {mins}m")
                else:
                    self._hist_duration_label.setText(f"{mins}m")
            except ValueError:
                self._hist_duration_label.setText("-")
        else:
            self._hist_duration_label.setText("-")

        self._hist_maps_label.setText(str(session.get("total_maps", 0)))
        self._hist_drops_label.setText(str(session.get("total_drops", 0)))

        total_chaos = session.get("total_chaos_value", 0)
        self._hist_value_label.setText(f"{total_chaos:.0f}c")

        rate = session.get("chaos_per_hour", 0)
        self._hist_rate_label.setText(f"{rate:.0f}c/hr")

    # =========================================================================
    # Button Handlers
    # =========================================================================

    def _on_start_clicked(self) -> None:
        """Handle start button click."""
        result = self._controller.start_session()
        if result.is_err():
            self._status_label.setText(f"Error: {result.error}")
        else:
            self._update_ui()

    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        result = self._controller.end_session()
        if result.is_err():
            self._status_label.setText(f"Error: {result.error}")
        else:
            self._update_ui()
            self._load_history()  # Refresh history

    def _on_auto_track_toggled(self, checked: bool) -> None:
        """Handle auto-track checkbox toggle."""
        self._controller.enable_auto_tracking(checked)

    def _on_snapshot_clicked(self) -> None:
        """Handle manual snapshot button click."""
        self._controller.take_manual_snapshot()

    # =========================================================================
    # Signal Handlers
    # =========================================================================

    def _on_session_started(self, session: "LootSession") -> None:
        """Handle session started signal."""
        self._update_ui()
        self._drops_model.clear()
        self._maps_model.clear()
        self._status_label.setText(f"Session started: {session.name}")

    def _on_session_ended(self, session: "LootSession") -> None:
        """Handle session ended signal."""
        self._update_ui()
        self._status_label.setText(
            f"Session ended: {session.total_maps} maps, "
            f"{session.total_chaos_value:.0f}c total"
        )

    def _on_state_changed(self, state: str) -> None:
        """Handle session state change signal."""
        self._status_label.setText(f"Session state: {state}")

    def _on_drops_detected(self, drops: List["LootDrop"]) -> None:
        """Handle drops detected signal."""
        self._update_live_stats()
        if drops:
            total_value = sum(d.chaos_value * d.stack_size for d in drops)
            self._status_label.setText(
                f"Detected {len(drops)} drops worth {total_value:.0f}c"
            )

    def _on_stats_updated(self, stats: Dict[str, Any]) -> None:
        """Handle stats updated signal."""
        # Stats are already updated by the timer
        pass

    def _on_status_message(self, message: str) -> None:
        """Handle status message signal."""
        self._status_label.setText(message)

    def _on_snapshot_started(self) -> None:
        """Handle snapshot started signal."""
        self._snapshot_btn.setEnabled(False)
        self._snapshot_btn.setText("Fetching...")

    def _on_snapshot_completed(self, item_count: int) -> None:
        """Handle snapshot completed signal."""
        self._snapshot_btn.setEnabled(True)
        self._snapshot_btn.setText("Take Snapshot")
        self._status_label.setText(f"Snapshot complete: {item_count} items")

    def _on_snapshot_error(self, message: str) -> None:
        """Handle snapshot error signal."""
        self._snapshot_btn.setEnabled(True)
        self._snapshot_btn.setText("Take Snapshot")
        self._status_label.setText(f"Snapshot error: {message}")

    def _on_high_value_drop(self, drop: "LootDrop") -> None:
        """Handle high value drop signal."""
        # Could show a toast notification here
        self._status_label.setText(
            f"High value drop: {drop.item_name} ({drop.chaos_value:.0f}c)"
        )

    def closeEvent(self, event) -> None:
        """Handle window close."""
        self._update_timer.stop()
        super().closeEvent(event)
