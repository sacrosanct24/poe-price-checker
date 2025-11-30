"""
gui_qt.dialogs.settings_dialog

Dialog for application settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        self.setMinimumWidth(450)
        self.setMinimumHeight(400)
        self.resize(500, 450)
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

        # System Tray tab
        tray_tab = self._create_tray_tab()
        self._tabs.addTab(tray_tab, "System Tray")

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
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

        # Spacer
        layout.addStretch()

        return tab

    def _load_settings(self) -> None:
        """Load current settings into the widgets."""
        self._minimize_to_tray_cb.setChecked(self._config.minimize_to_tray)
        self._start_minimized_cb.setChecked(self._config.start_minimized)
        self._show_notifications_cb.setChecked(self._config.show_tray_notifications)
        self._threshold_spin.setValue(self._config.tray_alert_threshold)

        # Update threshold enabled state
        self._on_notifications_toggled()

    def _on_notifications_toggled(self) -> None:
        """Handle notifications checkbox state change."""
        enabled = self._show_notifications_cb.isChecked()
        self._threshold_spin.setEnabled(enabled)

    def _reset_to_defaults(self) -> None:
        """Reset settings to their default values."""
        self._minimize_to_tray_cb.setChecked(True)
        self._start_minimized_cb.setChecked(False)
        self._show_notifications_cb.setChecked(True)
        self._threshold_spin.setValue(50.0)
        self._on_notifications_toggled()

    def _save_and_accept(self) -> None:
        """Save settings and close the dialog."""
        self._config.minimize_to_tray = self._minimize_to_tray_cb.isChecked()
        self._config.start_minimized = self._start_minimized_cb.isChecked()
        self._config.show_tray_notifications = self._show_notifications_cb.isChecked()
        self._config.tray_alert_threshold = self._threshold_spin.value()
        self.accept()
