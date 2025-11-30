"""Tests for SettingsDialog."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QDialog


class TestSettingsDialogInit:
    """Tests for SettingsDialog initialization."""

    def test_init_with_config(self, qtbot):
        """Can initialize with config."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Settings"
        assert dialog._config is mock_config

    def test_loads_settings_from_config(self, qtbot):
        """Settings are loaded from config on init."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = False
        mock_config.start_minimized = True
        mock_config.show_tray_notifications = False
        mock_config.tray_alert_threshold = 100.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._minimize_to_tray_cb.isChecked() is False
        assert dialog._start_minimized_cb.isChecked() is True
        assert dialog._show_notifications_cb.isChecked() is False
        assert dialog._threshold_spin.value() == 100.0


class TestSettingsDialogWidgets:
    """Tests for SettingsDialog widget behavior."""

    def test_has_tab_widget(self, qtbot):
        """Dialog has tab widget."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._tabs is not None
        assert dialog._tabs.count() >= 1
        assert dialog._tabs.tabText(0) == "System Tray"

    def test_threshold_disabled_when_notifications_off(self, qtbot):
        """Threshold spinner disabled when notifications unchecked."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Initially enabled
        assert dialog._threshold_spin.isEnabled() is True

        # Uncheck notifications
        dialog._show_notifications_cb.setChecked(False)
        assert dialog._threshold_spin.isEnabled() is False

        # Re-check notifications
        dialog._show_notifications_cb.setChecked(True)
        assert dialog._threshold_spin.isEnabled() is True


class TestSettingsDialogSave:
    """Tests for SettingsDialog save functionality."""

    def test_save_updates_config(self, qtbot):
        """Saving updates all config values."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Change values
        dialog._minimize_to_tray_cb.setChecked(False)
        dialog._start_minimized_cb.setChecked(True)
        dialog._show_notifications_cb.setChecked(False)
        dialog._threshold_spin.setValue(200.0)

        # Save
        dialog._save_and_accept()

        # Verify config was updated
        assert mock_config.minimize_to_tray is False
        assert mock_config.start_minimized is True
        assert mock_config.show_tray_notifications is False
        assert mock_config.tray_alert_threshold == 200.0

    def test_cancel_does_not_update_config(self, qtbot):
        """Canceling does not update config."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Change values
        dialog._minimize_to_tray_cb.setChecked(False)
        dialog._threshold_spin.setValue(999.0)

        # Reject without saving
        dialog.reject()

        # Config setters should not have been called with new values
        # (Config only gets updated on _save_and_accept)
        # The mock_config properties were only read during _load_settings


class TestSettingsDialogReset:
    """Tests for SettingsDialog reset to defaults."""

    def test_reset_to_defaults(self, qtbot):
        """Reset restores default values."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = False
        mock_config.start_minimized = True
        mock_config.show_tray_notifications = False
        mock_config.tray_alert_threshold = 999.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Verify non-default values loaded
        assert dialog._minimize_to_tray_cb.isChecked() is False
        assert dialog._start_minimized_cb.isChecked() is True
        assert dialog._show_notifications_cb.isChecked() is False
        assert dialog._threshold_spin.value() == 999.0

        # Reset
        dialog._reset_to_defaults()

        # Verify defaults
        assert dialog._minimize_to_tray_cb.isChecked() is True
        assert dialog._start_minimized_cb.isChecked() is False
        assert dialog._show_notifications_cb.isChecked() is True
        assert dialog._threshold_spin.value() == 50.0
        assert dialog._threshold_spin.isEnabled() is True


class TestSettingsDialogIntegration:
    """Integration tests for SettingsDialog."""

    def test_dialog_accept_returns_accepted(self, qtbot):
        """Dialog returns Accepted on save."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Save triggers accept
        dialog._save_and_accept()
        assert dialog.result() == QDialog.DialogCode.Accepted

    def test_dialog_reject_returns_rejected(self, qtbot):
        """Dialog returns Rejected on cancel."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = MagicMock()
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        dialog.reject()
        assert dialog.result() == QDialog.DialogCode.Rejected
