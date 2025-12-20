"""Tests for SettingsDialog."""

from unittest.mock import MagicMock



class TestSettingsDialogInit:
    """Tests for SettingsDialog initialization."""

    def test_init_with_config(self, qtbot):
        """Can initialize with config."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Settings"
        assert dialog._config is mock_config

    def test_has_six_tabs(self, qtbot):
        """Dialog has six tabs: Accessibility, Performance, System Tray, AI, Verdict, Alerts."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._tabs.count() == 6
        assert dialog._tabs.tabText(0) == "Accessibility"
        assert dialog._tabs.tabText(1) == "Performance"
        assert dialog._tabs.tabText(2) == "System Tray"
        assert dialog._tabs.tabText(3) == "AI"
        assert dialog._tabs.tabText(4) == "Verdict"
        assert dialog._tabs.tabText(5) == "Alerts"

    def _create_mock_config(self):
        """Create a mock config with all required properties."""
        mock_config = MagicMock()
        # Accessibility
        mock_config.font_scale = 1.0
        mock_config.tooltip_delay_ms = 500
        mock_config.reduce_animations = False
        # Performance
        mock_config.rankings_cache_hours = 24
        mock_config.price_cache_ttl_seconds = 3600
        mock_config.api_rate_limit = 0.33
        mock_config.toast_duration_ms = 3000
        mock_config.history_max_entries = 100
        # System Tray
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0
        # AI
        mock_config.ai_provider = ""
        mock_config.ai_max_tokens = 500
        mock_config.ai_timeout = 30
        mock_config.ai_build_name = ""
        mock_config.ai_custom_prompt = ""
        mock_config.get_ai_api_key = MagicMock(return_value="")
        mock_config.ollama_host = ""
        mock_config.ollama_model = "deepseek-r1:14b"
        # Verdict
        mock_config.verdict_vendor_threshold = 2.0
        mock_config.verdict_keep_threshold = 15.0
        mock_config.verdict_preset = "default"
        # Alerts
        mock_config.alerts_enabled = True
        mock_config.alert_polling_interval_minutes = 15
        mock_config.alert_default_cooldown_minutes = 30
        mock_config.alert_show_tray_notifications = True
        mock_config.alert_show_toast_notifications = True
        return mock_config


class TestAccessibilityTab:
    """Tests for Accessibility settings tab."""

    def _create_mock_config(self):
        """Create a mock config with all required properties."""
        mock_config = MagicMock()
        mock_config.font_scale = 1.0
        mock_config.tooltip_delay_ms = 500
        mock_config.reduce_animations = False
        mock_config.rankings_cache_hours = 24
        mock_config.price_cache_ttl_seconds = 3600
        mock_config.api_rate_limit = 0.33
        mock_config.toast_duration_ms = 3000
        mock_config.history_max_entries = 100
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0
        # AI
        mock_config.ai_provider = ""
        mock_config.ai_max_tokens = 500
        mock_config.ai_timeout = 30
        mock_config.ai_build_name = ""
        mock_config.ai_custom_prompt = ""
        mock_config.get_ai_api_key = MagicMock(return_value="")
        mock_config.ollama_host = ""
        mock_config.ollama_model = "deepseek-r1:14b"
        # Verdict
        mock_config.verdict_vendor_threshold = 2.0
        mock_config.verdict_keep_threshold = 15.0
        mock_config.verdict_preset = "default"
        # Alerts
        mock_config.alerts_enabled = True
        mock_config.alert_polling_interval_minutes = 15
        mock_config.alert_default_cooldown_minutes = 30
        mock_config.alert_show_tray_notifications = True
        mock_config.alert_show_toast_notifications = True
        return mock_config

    def test_font_scale_slider_range(self, qtbot):
        """Font scale slider has correct range (80-150)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._font_scale_slider.minimum() == 80
        assert dialog._font_scale_slider.maximum() == 150

    def test_font_scale_loads_from_config(self, qtbot):
        """Font scale loads correctly from config."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        mock_config.font_scale = 1.25

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._font_scale_slider.value() == 125

    def test_font_scale_label_updates(self, qtbot):
        """Font scale label updates when slider changes."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        dialog._font_scale_slider.setValue(125)
        assert dialog._font_scale_label.text() == "125%"

    def test_tooltip_delay_range(self, qtbot):
        """Tooltip delay has correct range (100-2000)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._tooltip_delay_spin.minimum() == 100
        assert dialog._tooltip_delay_spin.maximum() == 2000


class TestPerformanceTab:
    """Tests for Performance settings tab."""

    def _create_mock_config(self):
        """Create a mock config with all required properties."""
        mock_config = MagicMock()
        mock_config.font_scale = 1.0
        mock_config.tooltip_delay_ms = 500
        mock_config.reduce_animations = False
        mock_config.rankings_cache_hours = 24
        mock_config.price_cache_ttl_seconds = 3600
        mock_config.api_rate_limit = 0.33
        mock_config.toast_duration_ms = 3000
        mock_config.history_max_entries = 100
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0
        # AI
        mock_config.ai_provider = ""
        mock_config.ai_max_tokens = 500
        mock_config.ai_timeout = 30
        mock_config.ai_build_name = ""
        mock_config.ai_custom_prompt = ""
        mock_config.get_ai_api_key = MagicMock(return_value="")
        mock_config.ollama_host = ""
        mock_config.ollama_model = "deepseek-r1:14b"
        # Verdict
        mock_config.verdict_vendor_threshold = 2.0
        mock_config.verdict_keep_threshold = 15.0
        mock_config.verdict_preset = "default"
        return mock_config

    def test_rankings_cache_range(self, qtbot):
        """Rankings cache spinner has correct range (1-168 hours)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._rankings_cache_spin.minimum() == 1
        assert dialog._rankings_cache_spin.maximum() == 168

    def test_rate_limit_slider_range(self, qtbot):
        """Rate limit slider has correct range (20-100 = 0.2-1.0 req/s)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._rate_limit_slider.minimum() == 20
        assert dialog._rate_limit_slider.maximum() == 100

    def test_rate_limit_label_format(self, qtbot):
        """Rate limit label shows human-readable format."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Test conservative (0.2 req/s = 1 req per 5s)
        dialog._rate_limit_slider.setValue(20)
        assert "5s" in dialog._rate_limit_label.text()

        # Test recommended (0.33 req/s = 1 req per 3s)
        dialog._rate_limit_slider.setValue(33)
        assert "3" in dialog._rate_limit_label.text()

        # Test aggressive (1.0 req/s)
        dialog._rate_limit_slider.setValue(100)
        assert "1 req/s" in dialog._rate_limit_label.text()

    def test_toast_duration_range(self, qtbot):
        """Toast duration has correct range (1000-10000 ms)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._toast_duration_spin.minimum() == 1000
        assert dialog._toast_duration_spin.maximum() == 10000

    def test_history_max_range(self, qtbot):
        """History max entries has correct range (10-500)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._history_max_spin.minimum() == 10
        assert dialog._history_max_spin.maximum() == 500


class TestSystemTrayTab:
    """Tests for System Tray settings tab."""

    def _create_mock_config(self):
        """Create a mock config with all required properties."""
        mock_config = MagicMock()
        mock_config.font_scale = 1.0
        mock_config.tooltip_delay_ms = 500
        mock_config.reduce_animations = False
        mock_config.rankings_cache_hours = 24
        mock_config.price_cache_ttl_seconds = 3600
        mock_config.api_rate_limit = 0.33
        mock_config.toast_duration_ms = 3000
        mock_config.history_max_entries = 100
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0
        # AI
        mock_config.ai_provider = ""
        mock_config.ai_max_tokens = 500
        mock_config.ai_timeout = 30
        mock_config.ai_build_name = ""
        mock_config.ai_custom_prompt = ""
        mock_config.get_ai_api_key = MagicMock(return_value="")
        mock_config.ollama_host = ""
        mock_config.ollama_model = "deepseek-r1:14b"
        # Verdict
        mock_config.verdict_vendor_threshold = 2.0
        mock_config.verdict_keep_threshold = 15.0
        mock_config.verdict_preset = "default"
        return mock_config

    def test_loads_settings_from_config(self, qtbot):
        """Tray settings are loaded from config on init."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
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

    def test_threshold_disabled_when_notifications_off(self, qtbot):
        """Threshold spinner disabled when notifications unchecked."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Initially enabled
        assert dialog._threshold_spin.isEnabled() is True

        # Uncheck notifications
        dialog._show_notifications_cb.setChecked(False)
        assert dialog._threshold_spin.isEnabled() is False


class TestSettingsDialogSave:
    """Tests for SettingsDialog save functionality."""

    def _create_mock_config(self):
        """Create a mock config with all required properties."""
        mock_config = MagicMock()
        mock_config.font_scale = 1.0
        mock_config.tooltip_delay_ms = 500
        mock_config.reduce_animations = False
        mock_config.rankings_cache_hours = 24
        mock_config.price_cache_ttl_seconds = 3600
        mock_config.api_rate_limit = 0.33
        mock_config.toast_duration_ms = 3000
        mock_config.history_max_entries = 100
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0
        # AI
        mock_config.ai_provider = ""
        mock_config.ai_max_tokens = 500
        mock_config.ai_timeout = 30
        mock_config.ai_build_name = ""
        mock_config.ai_custom_prompt = ""
        mock_config.get_ai_api_key = MagicMock(return_value="")
        mock_config.ollama_host = ""
        mock_config.ollama_model = "deepseek-r1:14b"
        # Verdict
        mock_config.verdict_vendor_threshold = 2.0
        mock_config.verdict_keep_threshold = 15.0
        mock_config.verdict_preset = "default"
        return mock_config

    def test_save_updates_all_config_values(self, qtbot):
        """Saving updates all config values."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Change values
        dialog._font_scale_slider.setValue(125)
        dialog._tooltip_delay_spin.setValue(1000)
        dialog._reduce_animations_cb.setChecked(True)
        dialog._rankings_cache_spin.setValue(48)
        dialog._rate_limit_slider.setValue(50)
        dialog._toast_duration_spin.setValue(5000)
        dialog._history_max_spin.setValue(200)
        dialog._minimize_to_tray_cb.setChecked(False)
        dialog._threshold_spin.setValue(100.0)

        # Save
        dialog._save_and_accept()

        # Verify config was updated
        assert mock_config.font_scale == 1.25
        assert mock_config.tooltip_delay_ms == 1000
        assert mock_config.reduce_animations is True
        assert mock_config.rankings_cache_hours == 48
        assert mock_config.api_rate_limit == 0.5
        assert mock_config.toast_duration_ms == 5000
        assert mock_config.history_max_entries == 200
        assert mock_config.minimize_to_tray is False
        assert mock_config.tray_alert_threshold == 100.0


class TestSettingsDialogReset:
    """Tests for SettingsDialog reset to defaults."""

    def _create_mock_config(self):
        """Create a mock config with all required properties."""
        mock_config = MagicMock()
        mock_config.font_scale = 1.5
        mock_config.tooltip_delay_ms = 2000
        mock_config.reduce_animations = True
        mock_config.rankings_cache_hours = 168
        mock_config.price_cache_ttl_seconds = 7200
        mock_config.api_rate_limit = 1.0
        mock_config.toast_duration_ms = 10000
        mock_config.history_max_entries = 500
        mock_config.minimize_to_tray = False
        mock_config.start_minimized = True
        mock_config.show_tray_notifications = False
        mock_config.tray_alert_threshold = 999.0
        # AI
        mock_config.ai_provider = ""
        mock_config.ai_max_tokens = 500
        mock_config.ai_timeout = 30
        mock_config.ai_build_name = ""
        mock_config.ai_custom_prompt = ""
        mock_config.get_ai_api_key = MagicMock(return_value="")
        mock_config.ollama_host = ""
        mock_config.ollama_model = "deepseek-r1:14b"
        # Verdict
        mock_config.verdict_vendor_threshold = 2.0
        mock_config.verdict_keep_threshold = 15.0
        mock_config.verdict_preset = "default"
        return mock_config

    def test_reset_accessibility_tab(self, qtbot):
        """Reset restores accessibility defaults."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Select accessibility tab
        dialog._tabs.setCurrentIndex(0)

        # Reset
        dialog._reset_to_defaults()

        # Verify defaults
        assert dialog._font_scale_slider.value() == 100
        assert dialog._tooltip_delay_spin.value() == 500
        assert dialog._reduce_animations_cb.isChecked() is False

    def test_reset_performance_tab(self, qtbot):
        """Reset restores performance defaults."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Select performance tab
        dialog._tabs.setCurrentIndex(1)

        # Reset
        dialog._reset_to_defaults()

        # Verify defaults
        assert dialog._rankings_cache_spin.value() == 24
        assert dialog._rate_limit_slider.value() == 33
        assert dialog._toast_duration_spin.value() == 3000
        assert dialog._history_max_spin.value() == 100

    def test_reset_tray_tab(self, qtbot):
        """Reset restores tray defaults."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Select tray tab
        dialog._tabs.setCurrentIndex(2)

        # Reset
        dialog._reset_to_defaults()

        # Verify defaults (minimize_to_tray defaults to False - use File > Minimize to Tray)
        assert dialog._minimize_to_tray_cb.isChecked() is False
        assert dialog._start_minimized_cb.isChecked() is False
        assert dialog._show_notifications_cb.isChecked() is True
        assert dialog._threshold_spin.value() == 50.0


class TestConfigGuardrails:
    """Tests for config property guardrails."""

    def test_font_scale_guardrails(self, tmp_path):
        """Font scale is clamped to 0.8-1.5."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.font_scale = 0.5  # Below min
        assert config.font_scale == 0.8

        config.font_scale = 2.0  # Above max
        assert config.font_scale == 1.5

        config.font_scale = 1.2  # Within range
        assert config.font_scale == 1.2

    def test_tooltip_delay_guardrails(self, tmp_path):
        """Tooltip delay is clamped to 100-2000."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.tooltip_delay_ms = 50  # Below min
        assert config.tooltip_delay_ms == 100

        config.tooltip_delay_ms = 5000  # Above max
        assert config.tooltip_delay_ms == 2000

    def test_rankings_cache_guardrails(self, tmp_path):
        """Rankings cache hours is clamped to 1-168."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.rankings_cache_hours = 0  # Below min
        assert config.rankings_cache_hours == 1

        config.rankings_cache_hours = 500  # Above max
        assert config.rankings_cache_hours == 168

    def test_price_cache_ttl_guardrails(self, tmp_path):
        """Price cache TTL is clamped to 300-7200."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.price_cache_ttl_seconds = 60  # Below min
        assert config.price_cache_ttl_seconds == 300

        config.price_cache_ttl_seconds = 10000  # Above max
        assert config.price_cache_ttl_seconds == 7200

    def test_api_rate_limit_guardrails(self, tmp_path):
        """API rate limit is clamped to 0.2-1.0 to prevent GGG violations."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.api_rate_limit = 0.1  # Below min - too aggressive
        assert config.api_rate_limit == 0.2

        config.api_rate_limit = 5.0  # Above max - way too aggressive
        assert config.api_rate_limit == 1.0

        config.api_rate_limit = 0.33  # Recommended value
        assert config.api_rate_limit == 0.33

    def test_toast_duration_guardrails(self, tmp_path):
        """Toast duration is clamped to 1000-10000."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.toast_duration_ms = 500  # Below min
        assert config.toast_duration_ms == 1000

        config.toast_duration_ms = 20000  # Above max
        assert config.toast_duration_ms == 10000

    def test_history_max_guardrails(self, tmp_path):
        """History max entries is clamped to 10-500."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.history_max_entries = 5  # Below min
        assert config.history_max_entries == 10

        config.history_max_entries = 1000  # Above max
        assert config.history_max_entries == 500


class TestVerdictTab:
    """Tests for Verdict settings tab."""

    def _create_mock_config(self):
        """Create a mock config with all required properties."""
        mock_config = MagicMock()
        mock_config.font_scale = 1.0
        mock_config.tooltip_delay_ms = 500
        mock_config.reduce_animations = False
        mock_config.rankings_cache_hours = 24
        mock_config.price_cache_ttl_seconds = 3600
        mock_config.api_rate_limit = 0.33
        mock_config.toast_duration_ms = 3000
        mock_config.history_max_entries = 100
        mock_config.minimize_to_tray = True
        mock_config.start_minimized = False
        mock_config.show_tray_notifications = True
        mock_config.tray_alert_threshold = 50.0
        # AI
        mock_config.ai_provider = ""
        mock_config.ai_max_tokens = 500
        mock_config.ai_timeout = 30
        mock_config.ai_build_name = ""
        mock_config.ai_custom_prompt = ""
        mock_config.get_ai_api_key = MagicMock(return_value="")
        mock_config.ollama_host = ""
        mock_config.ollama_model = "deepseek-r1:14b"
        # Verdict
        mock_config.verdict_vendor_threshold = 2.0
        mock_config.verdict_keep_threshold = 15.0
        mock_config.verdict_preset = "default"
        return mock_config

    def test_verdict_tab_exists(self, qtbot):
        """Verdict tab is present in settings dialog."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._tabs.tabText(4) == "Verdict"

    def test_verdict_threshold_spinboxes_exist(self, qtbot):
        """Vendor and keep threshold spinboxes are present."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert hasattr(dialog, '_vendor_threshold_spin')
        assert hasattr(dialog, '_keep_threshold_spin')

    def test_verdict_thresholds_load_from_config(self, qtbot):
        """Verdict thresholds are loaded from config."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        mock_config.verdict_vendor_threshold = 5.0
        mock_config.verdict_keep_threshold = 25.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._vendor_threshold_spin.value() == 5.0
        assert dialog._keep_threshold_spin.value() == 25.0

    def test_vendor_threshold_range(self, qtbot):
        """Vendor threshold has correct range (0.1-50.0)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._vendor_threshold_spin.minimum() == 0.1
        assert dialog._vendor_threshold_spin.maximum() == 50.0

    def test_keep_threshold_range(self, qtbot):
        """Keep threshold has correct range (1.0-500.0)."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._keep_threshold_spin.minimum() == 1.0
        assert dialog._keep_threshold_spin.maximum() == 500.0

    def test_preset_buttons_apply_thresholds(self, qtbot):
        """Preset buttons apply correct threshold values."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Apply league start preset
        dialog._apply_verdict_preset("league_start")
        assert dialog._vendor_threshold_spin.value() == 1.0
        assert dialog._keep_threshold_spin.value() == 5.0

        # Apply late league preset
        dialog._apply_verdict_preset("late_league")
        assert dialog._vendor_threshold_spin.value() == 5.0
        assert dialog._keep_threshold_spin.value() == 20.0

    def test_manual_change_sets_custom_preset(self, qtbot):
        """Manual threshold change updates preset label to Custom."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Apply a known preset first
        dialog._apply_verdict_preset("league_start")
        assert "League Start" in dialog._preset_label.text()

        # Manually change a threshold
        dialog._vendor_threshold_spin.setValue(7.5)
        assert "Custom" in dialog._preset_label.text()

    def test_reset_verdict_tab(self, qtbot):
        """Reset restores verdict defaults."""
        from gui_qt.dialogs.settings_dialog import SettingsDialog

        mock_config = self._create_mock_config()
        mock_config.verdict_vendor_threshold = 10.0
        mock_config.verdict_keep_threshold = 50.0

        dialog = SettingsDialog(mock_config)
        qtbot.addWidget(dialog)

        # Verify non-default values are loaded
        assert dialog._vendor_threshold_spin.value() == 10.0
        assert dialog._keep_threshold_spin.value() == 50.0

        # Select verdict tab and reset
        dialog._tabs.setCurrentIndex(4)
        dialog._reset_to_defaults()

        # Verify defaults are restored
        assert dialog._vendor_threshold_spin.value() == 2.0
        assert dialog._keep_threshold_spin.value() == 15.0


class TestVerdictConfigGuardrails:
    """Tests for verdict config property guardrails."""

    def test_verdict_vendor_threshold_guardrails(self, tmp_path):
        """Vendor threshold is clamped to 0.1-50.0."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.verdict_vendor_threshold = 0.01  # Below min
        assert config.verdict_vendor_threshold == 0.1

        config.verdict_vendor_threshold = 100.0  # Above max
        assert config.verdict_vendor_threshold == 50.0

        config.verdict_vendor_threshold = 5.0  # Within range
        assert config.verdict_vendor_threshold == 5.0

    def test_verdict_keep_threshold_guardrails(self, tmp_path):
        """Keep threshold is clamped to 1.0-500.0."""
        from core.config import Config

        config = Config(config_file=tmp_path / "test_config.json")

        config.verdict_keep_threshold = 0.5  # Below min
        assert config.verdict_keep_threshold == 1.0

        config.verdict_keep_threshold = 1000.0  # Above max
        assert config.verdict_keep_threshold == 500.0

        config.verdict_keep_threshold = 25.0  # Within range
        assert config.verdict_keep_threshold == 25.0
