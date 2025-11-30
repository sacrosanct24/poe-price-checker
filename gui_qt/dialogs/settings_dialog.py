"""
gui_qt.dialogs.settings_dialog

Dialog for application settings including accessibility, performance, and system tray options.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui_qt.styles import apply_window_icon

if TYPE_CHECKING:
    from core.config import Config


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(
        self,
        config: Config,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._config = config

        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.resize(550, 550)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_settings()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Tab widget for different setting categories
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Accessibility tab
        accessibility_tab = self._create_accessibility_tab()
        self._tabs.addTab(accessibility_tab, "Accessibility")

        # Performance tab
        performance_tab = self._create_performance_tab()
        self._tabs.addTab(performance_tab, "Performance")

        # System Tray tab
        tray_tab = self._create_tray_tab()
        self._tabs.addTab(tray_tab, "System Tray")

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setToolTip("Reset all settings on the current tab to their default values")
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_row.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_accept)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

    def _create_accessibility_tab(self) -> QWidget:
        """Create the Accessibility settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Font Scaling group
        font_group = QGroupBox("Display")
        font_layout = QVBoxLayout(font_group)
        font_layout.setSpacing(12)

        # Font scale slider
        scale_row = QHBoxLayout()
        scale_label = QLabel("Font scale:")
        scale_row.addWidget(scale_label)

        self._font_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._font_scale_slider.setRange(80, 150)  # 0.8x to 1.5x
        self._font_scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._font_scale_slider.setTickInterval(10)
        self._font_scale_slider.setToolTip(
            "Scale all fonts in the application.\n"
            "Useful for high-DPI displays or visual accessibility."
        )
        self._font_scale_slider.valueChanged.connect(self._on_font_scale_changed)
        scale_row.addWidget(self._font_scale_slider)

        self._font_scale_label = QLabel("100%")
        self._font_scale_label.setMinimumWidth(45)
        scale_row.addWidget(self._font_scale_label)

        font_layout.addLayout(scale_row)

        # Preset buttons
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:"))

        for label, value in [("Small", 80), ("Normal", 100), ("Large", 125), ("Extra Large", 150)]:
            btn = QPushButton(label)
            btn.setFixedWidth(80)
            btn.clicked.connect(lambda checked, v=value: self._font_scale_slider.setValue(v))
            preset_row.addWidget(btn)

        preset_row.addStretch()
        font_layout.addLayout(preset_row)

        layout.addWidget(font_group)

        # Timing & Motion group
        timing_group = QGroupBox("Timing & Motion")
        timing_layout = QVBoxLayout(timing_group)
        timing_layout.setSpacing(8)

        # Tooltip delay
        tooltip_row = QHBoxLayout()
        tooltip_row.addWidget(QLabel("Tooltip delay:"))

        self._tooltip_delay_spin = QSpinBox()
        self._tooltip_delay_spin.setRange(100, 2000)
        self._tooltip_delay_spin.setSingleStep(100)
        self._tooltip_delay_spin.setSuffix(" ms")
        self._tooltip_delay_spin.setToolTip(
            "How long to wait before showing tooltips.\n"
            "Increase if tooltips appear too quickly."
        )
        tooltip_row.addWidget(self._tooltip_delay_spin)
        tooltip_row.addStretch()
        timing_layout.addLayout(tooltip_row)

        # Reduce animations
        self._reduce_animations_cb = QCheckBox("Reduce animations")
        self._reduce_animations_cb.setToolTip(
            "Disable or reduce motion effects in the interface.\n"
            "Recommended for users sensitive to motion."
        )
        timing_layout.addWidget(self._reduce_animations_cb)

        layout.addWidget(timing_group)

        # Info text
        info_label = QLabel(
            "Note: Font scaling changes require restarting the application to take full effect."
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()
        return tab

    def _create_performance_tab(self) -> QWidget:
        """Create the Performance settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Cache Settings group
        cache_group = QGroupBox("Cache Settings")
        cache_layout = QVBoxLayout(cache_group)
        cache_layout.setSpacing(12)

        # Rankings cache
        rankings_row = QHBoxLayout()
        rankings_label = QLabel("Top 20 rankings staleness:")
        rankings_label.setToolTip(
            "How long to cache price rankings before refreshing.\n"
            "Lower = fresher data but more API calls."
        )
        rankings_row.addWidget(rankings_label)

        self._rankings_cache_spin = QSpinBox()
        self._rankings_cache_spin.setRange(1, 168)  # 1 hour to 1 week
        self._rankings_cache_spin.setSuffix(" hours")
        self._rankings_cache_spin.setToolTip(
            "Min: 1 hour, Max: 168 hours (1 week)\n"
            "Recommended: 24 hours for daily fresh data"
        )
        rankings_row.addWidget(self._rankings_cache_spin)
        rankings_row.addStretch()
        cache_layout.addLayout(rankings_row)

        # Price cache TTL
        price_cache_row = QHBoxLayout()
        price_cache_label = QLabel("Price data cache:")
        price_cache_label.setToolTip(
            "How long to cache individual price lookups.\n"
            "Affects how often the app queries external APIs."
        )
        price_cache_row.addWidget(price_cache_label)

        self._price_cache_combo = QComboBox()
        self._price_cache_combo.addItem("5 minutes (frequent updates)", 300)
        self._price_cache_combo.addItem("15 minutes", 900)
        self._price_cache_combo.addItem("30 minutes", 1800)
        self._price_cache_combo.addItem("1 hour (recommended)", 3600)
        self._price_cache_combo.addItem("2 hours (conservative)", 7200)
        self._price_cache_combo.setToolTip(
            "Shorter = more up-to-date prices\n"
            "Longer = fewer API calls, less risk of rate limiting"
        )
        price_cache_row.addWidget(self._price_cache_combo)
        price_cache_row.addStretch()
        cache_layout.addLayout(price_cache_row)

        layout.addWidget(cache_group)

        # API Settings group
        api_group = QGroupBox("API Rate Limiting")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(8)

        # Warning label
        warning_label = QLabel(
            "⚠️ GGG enforces strict rate limits. Setting values too aggressive\n"
            "   may result in temporary API bans (429 errors)."
        )
        warning_label.setStyleSheet("color: #e67e22; font-size: 11px;")
        api_layout.addWidget(warning_label)

        # Rate limit slider
        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("API request rate:"))

        self._rate_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self._rate_limit_slider.setRange(20, 100)  # 0.2 to 1.0 req/s
        self._rate_limit_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._rate_limit_slider.setTickInterval(20)
        self._rate_limit_slider.valueChanged.connect(self._on_rate_limit_changed)
        self._rate_limit_slider.setToolTip(
            "How fast to send API requests.\n"
            "Conservative (left) = safer, slower\n"
            "Aggressive (right) = faster, may hit limits"
        )
        rate_row.addWidget(self._rate_limit_slider)

        self._rate_limit_label = QLabel("1 req/3s")
        self._rate_limit_label.setMinimumWidth(70)
        rate_row.addWidget(self._rate_limit_label)

        api_layout.addLayout(rate_row)

        # Rate limit descriptions
        rate_desc_row = QHBoxLayout()
        rate_desc_row.addWidget(QLabel("Conservative"))
        rate_desc_row.addStretch()
        rate_desc_row.addWidget(QLabel("Aggressive"))
        api_layout.addLayout(rate_desc_row)

        layout.addWidget(api_group)

        # UI Settings group
        ui_group = QGroupBox("UI Feedback")
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setSpacing(8)

        # Toast duration
        toast_row = QHBoxLayout()
        toast_row.addWidget(QLabel("Toast notification duration:"))

        self._toast_duration_spin = QSpinBox()
        self._toast_duration_spin.setRange(1000, 10000)
        self._toast_duration_spin.setSingleStep(500)
        self._toast_duration_spin.setSuffix(" ms")
        self._toast_duration_spin.setToolTip(
            "How long toast notifications remain visible.\n"
            "Default: 3000ms (3 seconds)"
        )
        toast_row.addWidget(self._toast_duration_spin)
        toast_row.addStretch()
        ui_layout.addLayout(toast_row)

        # History entries
        history_row = QHBoxLayout()
        history_row.addWidget(QLabel("History entries to keep:"))

        self._history_max_spin = QSpinBox()
        self._history_max_spin.setRange(10, 500)
        self._history_max_spin.setSingleStep(10)
        self._history_max_spin.setToolTip(
            "Maximum number of price check history entries.\n"
            "Higher = more memory usage"
        )
        history_row.addWidget(self._history_max_spin)
        history_row.addStretch()
        ui_layout.addLayout(history_row)

        layout.addWidget(ui_group)

        layout.addStretch()
        return tab

    def _create_tray_tab(self) -> QWidget:
        """Create the System Tray settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Tray Behavior group
        behavior_group = QGroupBox("Tray Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setSpacing(8)

        self._minimize_to_tray_cb = QCheckBox("Minimize to system tray")
        self._minimize_to_tray_cb.setToolTip(
            "When enabled, minimizing the window will hide it to the system tray\n"
            "instead of the taskbar. Click the tray icon to restore."
        )
        behavior_layout.addWidget(self._minimize_to_tray_cb)

        self._start_minimized_cb = QCheckBox("Start minimized to tray")
        self._start_minimized_cb.setToolTip(
            "When enabled, the application will start minimized to the system tray.\n"
            "Useful if you want it running in the background at startup."
        )
        behavior_layout.addWidget(self._start_minimized_cb)

        layout.addWidget(behavior_group)

        # Notifications group
        notif_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notif_group)
        notif_layout.setSpacing(8)

        self._show_notifications_cb = QCheckBox("Show price alert notifications")
        self._show_notifications_cb.setToolTip(
            "When enabled, system notifications will appear when\n"
            "high-value items are detected during price checks."
        )
        self._show_notifications_cb.stateChanged.connect(self._on_notifications_toggled)
        notif_layout.addWidget(self._show_notifications_cb)

        # Threshold row
        threshold_row = QHBoxLayout()
        threshold_row.setSpacing(8)

        threshold_label = QLabel("Alert threshold:")
        threshold_row.addWidget(threshold_label)

        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0, 999999)
        self._threshold_spin.setDecimals(0)
        self._threshold_spin.setSuffix(" chaos")
        self._threshold_spin.setToolTip(
            "Items worth more than this value will trigger a notification.\n"
            "Set to 0 to be notified for all items."
        )
        self._threshold_spin.setMinimumWidth(120)
        threshold_row.addWidget(self._threshold_spin)

        threshold_row.addStretch()
        notif_layout.addLayout(threshold_row)

        # Help text
        help_label = QLabel(
            "Notifications appear in your system tray when checking items\n"
            "that exceed the threshold value."
        )
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        notif_layout.addWidget(help_label)

        layout.addWidget(notif_group)

        layout.addStretch()
        return tab

    def _on_font_scale_changed(self, value: int) -> None:
        """Update font scale label when slider changes."""
        self._font_scale_label.setText(f"{value}%")

    def _on_rate_limit_changed(self, value: int) -> None:
        """Update rate limit label when slider changes."""
        rate = value / 100.0  # Convert to req/s
        if rate <= 0.25:
            self._rate_limit_label.setText(f"1 req/{int(1/rate)}s")
        elif rate < 1.0:
            self._rate_limit_label.setText(f"1 req/{1/rate:.1f}s")
        else:
            self._rate_limit_label.setText("1 req/s")

    def _on_notifications_toggled(self) -> None:
        """Handle notifications checkbox state change."""
        enabled = self._show_notifications_cb.isChecked()
        self._threshold_spin.setEnabled(enabled)

    def _load_settings(self) -> None:
        """Load current settings into the widgets."""
        # Accessibility
        self._font_scale_slider.setValue(int(self._config.font_scale * 100))
        self._tooltip_delay_spin.setValue(self._config.tooltip_delay_ms)
        self._reduce_animations_cb.setChecked(self._config.reduce_animations)

        # Performance
        self._rankings_cache_spin.setValue(self._config.rankings_cache_hours)

        # Find matching price cache combo item
        price_ttl = self._config.price_cache_ttl_seconds
        for i in range(self._price_cache_combo.count()):
            if self._price_cache_combo.itemData(i) == price_ttl:
                self._price_cache_combo.setCurrentIndex(i)
                break
        else:
            # Default to 1 hour if not found
            self._price_cache_combo.setCurrentIndex(3)

        self._rate_limit_slider.setValue(int(self._config.api_rate_limit * 100))
        self._toast_duration_spin.setValue(self._config.toast_duration_ms)
        self._history_max_spin.setValue(self._config.history_max_entries)

        # System Tray
        self._minimize_to_tray_cb.setChecked(self._config.minimize_to_tray)
        self._start_minimized_cb.setChecked(self._config.start_minimized)
        self._show_notifications_cb.setChecked(self._config.show_tray_notifications)
        self._threshold_spin.setValue(self._config.tray_alert_threshold)

        # Update dependent states
        self._on_font_scale_changed(self._font_scale_slider.value())
        self._on_rate_limit_changed(self._rate_limit_slider.value())
        self._on_notifications_toggled()

    def _reset_to_defaults(self) -> None:
        """Reset settings to their default values based on current tab."""
        current_tab = self._tabs.currentIndex()

        if current_tab == 0:  # Accessibility
            self._font_scale_slider.setValue(100)
            self._tooltip_delay_spin.setValue(500)
            self._reduce_animations_cb.setChecked(False)
        elif current_tab == 1:  # Performance
            self._rankings_cache_spin.setValue(24)
            self._price_cache_combo.setCurrentIndex(3)  # 1 hour
            self._rate_limit_slider.setValue(33)  # 0.33 req/s
            self._toast_duration_spin.setValue(3000)
            self._history_max_spin.setValue(100)
        elif current_tab == 2:  # System Tray
            self._minimize_to_tray_cb.setChecked(True)
            self._start_minimized_cb.setChecked(False)
            self._show_notifications_cb.setChecked(True)
            self._threshold_spin.setValue(50.0)
            self._on_notifications_toggled()

    def _save_and_accept(self) -> None:
        """Save settings and close the dialog."""
        # Accessibility
        self._config.font_scale = self._font_scale_slider.value() / 100.0
        self._config.tooltip_delay_ms = self._tooltip_delay_spin.value()
        self._config.reduce_animations = self._reduce_animations_cb.isChecked()

        # Performance
        self._config.rankings_cache_hours = self._rankings_cache_spin.value()
        self._config.price_cache_ttl_seconds = self._price_cache_combo.currentData()
        self._config.api_rate_limit = self._rate_limit_slider.value() / 100.0
        self._config.toast_duration_ms = self._toast_duration_spin.value()
        self._config.history_max_entries = self._history_max_spin.value()

        # System Tray
        self._config.minimize_to_tray = self._minimize_to_tray_cb.isChecked()
        self._config.start_minimized = self._start_minimized_cb.isChecked()
        self._config.show_tray_notifications = self._show_notifications_cb.isChecked()
        self._config.tray_alert_threshold = self._threshold_spin.value()

        self.accept()
