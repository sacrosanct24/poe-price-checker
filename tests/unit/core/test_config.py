from __future__ import annotations

"""
Unit tests for core.config module (finalized + isolated)
"""

import pytest
import json
import uuid
from pathlib import Path

from core.config import Config
from core.game_version import GameVersion, GameConfig

pytestmark = pytest.mark.unit


# -------------------------
# Helper
# -------------------------

def get_unique_config_path(tmp_path):
    """Generate a unique config file path to prevent test interference"""
    return tmp_path / f"config_{uuid.uuid4().hex}.json"


# -------------------------
# Initialization Tests
# -------------------------

class TestConfigInitialization:
    def test_creates_config_file(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)
        config = Config(config_file)
        config.save()

        assert config_file.exists()

    def test_loads_defaults_for_new_config(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)
        cfg = Config(config_file)

        assert cfg.current_game == GameVersion.POE1
        assert cfg.min_value_chaos == 0.0
        assert cfg.show_vendor_items is True

    def test_creates_default_path_if_none(self):
        cfg = Config()
        expected = Path.home() / '.poe_price_checker' / 'config.json'
        assert cfg.config_file == expected

    def test_loads_existing_config(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        cfg1 = Config(config_file)
        cfg1.min_value_chaos = 50.0
        cfg1.league = "Custom League"

        cfg2 = Config(config_file)
        assert cfg2.min_value_chaos == 50.0
        assert cfg2.league == "Custom League"

    def test_merges_with_defaults_on_load(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        partial = {
            "current_game": "poe1",
            "games": {"poe1": {"league": "Test League"}}
        }
        with open(config_file, "w") as f:
            json.dump(partial, f)

        cfg = Config(config_file)

        assert cfg.league == "Test League"
        assert cfg.min_value_chaos == 0.0


# -------------------------
# Game Version Tests
# -------------------------

class TestGameVersionManagement:
    def test_current_game_property(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.current_game == GameVersion.POE1

    def test_set_current_game(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.current_game = GameVersion.POE2
        assert cfg.current_game == GameVersion.POE2

    def test_set_current_game_persists(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        cfg = Config(path)
        cfg.current_game = GameVersion.POE2

        cfg2 = Config(path)
        assert cfg2.current_game == GameVersion.POE2

    def test_get_game_config_current(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        gc = cfg.get_game_config()
        assert gc.game_version == GameVersion.POE1
        assert gc.league == "Standard"

    def test_get_game_config_specific(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        gc2 = cfg.get_game_config(GameVersion.POE2)
        assert gc2.game_version == GameVersion.POE2

    def test_set_game_config(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        new = GameConfig(
            game_version=GameVersion.POE1,
            league="Custom League",
            divine_chaos_rate=350.0
        )
        cfg.set_game_config(new)

        got = cfg.get_game_config(GameVersion.POE1)
        assert got.league == "Custom League"
        assert got.divine_chaos_rate == 350.0

    def test_default_config_isolation_between_files(self, tmp_path):
        file1 = get_unique_config_path(tmp_path)
        file2 = get_unique_config_path(tmp_path)

        cfg1 = Config(file1)
        cfg2 = Config(file2)

        cfg1.min_value_chaos = 123.0
        cfg1.save()

        cfg2_reloaded = Config(file2)
        assert cfg2_reloaded.min_value_chaos == 0.0

    def test_reset_to_defaults_resets_all_sections(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        cfg = Config(path)

        cfg.current_game = GameVersion.POE2
        cfg.league = "League X"
        cfg.min_value_chaos = 42.0
        cfg.show_vendor_items = False
        cfg.enable_plugin("price_alert")

        cfg.reset_to_defaults()

        reloaded = Config(path)
        assert reloaded.current_game == GameVersion.POE1
        assert reloaded.league == "Standard"
        assert reloaded.min_value_chaos == 0.0
        assert reloaded.show_vendor_items is True
        assert reloaded.is_plugin_enabled("price_alert") is False

    def test_auto_detect_league_default_and_persist(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        cfg = Config(path)

        assert cfg.auto_detect_league is True
        cfg.auto_detect_league = False

        reload = Config(path)
        assert reload.auto_detect_league is False

    def test_league_getter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.current_game = GameVersion.POE1
        assert cfg.league == "Standard"

    def test_league_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.current_game = GameVersion.POE1
        cfg.league = "Keepers of the Flame"

        cfg1 = cfg.get_game_config(GameVersion.POE1)
        assert cfg1.league == "Keepers of the Flame"

        cfg2 = cfg.get_game_config(GameVersion.POE2)
        assert cfg2.league == "Standard"

    def test_separate_leagues_per_game(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))

        cfg.current_game = GameVersion.POE1
        cfg.league = "PoE1 League"

        cfg.current_game = GameVersion.POE2
        cfg.league = "PoE2 League"

        a = cfg.get_game_config(GameVersion.POE1)
        b = cfg.get_game_config(GameVersion.POE2)

        assert a.league == "PoE1 League"
        assert b.league == "PoE2 League"


# -------------------------
# UI Settings Tests
# -------------------------

class TestUISettings:
    def test_min_value_chaos_property(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.min_value_chaos == 0.0

        cfg.min_value_chaos = 25.5
        assert cfg.min_value_chaos == 25.5

    def test_show_vendor_items_property(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.show_vendor_items is True

        cfg.show_vendor_items = False
        assert cfg.show_vendor_items is False

    def test_window_size_property(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.window_size == (1200, 800)

        cfg.window_size = (1920, 1080)
        assert cfg.window_size == (1920, 1080)

    def test_ui_settings_persist(self, tmp_path):
        p = get_unique_config_path(tmp_path)
        cfg = Config(p)

        cfg.min_value_chaos = 100.0
        cfg.show_vendor_items = False
        cfg.window_size = (1600, 900)

        cfg2 = Config(p)
        assert cfg2.min_value_chaos == 100.0
        assert cfg2.show_vendor_items is False
        assert cfg2.window_size == (1600, 900)


# -------------------------
# API Settings Tests
# -------------------------

class TestAPISettings:
    def test_auto_detect_league_property(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.auto_detect_league is True

        cfg.auto_detect_league = False
        assert cfg.auto_detect_league is False


# -------------------------
# Plugin Management Tests
# -------------------------

class TestPluginManagement:
    def test_is_plugin_enabled_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.is_plugin_enabled("test_plugin") is False

    def test_enable_plugin(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.enable_plugin("price_alert")
        assert cfg.is_plugin_enabled("price_alert") is True

    def test_disable_plugin(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.enable_plugin("test_plugin")
        cfg.disable_plugin("test_plugin")
        assert cfg.is_plugin_enabled("test_plugin") is False

    def test_enable_plugin_idempotent(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.enable_plugin("test")
        cfg.enable_plugin("test")

        enabled = cfg.data["plugins"]["enabled"]
        assert enabled.count("test") == 1

    def test_disable_plugin_unknown(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.disable_plugin("nothing")
        assert cfg.is_plugin_enabled("nothing") is False

    def test_multiple_plugins(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.enable_plugin("a")
        cfg.enable_plugin("b")
        cfg.enable_plugin("c")

        assert cfg.is_plugin_enabled("a")
        assert cfg.is_plugin_enabled("b")
        assert cfg.is_plugin_enabled("c")

        cfg.disable_plugin("b")
        assert cfg.is_plugin_enabled("b") is False


# -------------------------
# Persistence Tests
# -------------------------

class TestConfigPersistence:
    def test_save_creates_json_file(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        cfg = Config(path)
        cfg.min_value_chaos = 50.0
        cfg.save()

        with open(path) as f:
            data = json.load(f)

        assert data["ui"]["min_value_chaos"] == 50.0

    def test_json_is_pretty_formatted(self, tmp_path):
        path = get_unique_config_path(tmp_path)

        cfg = Config(path)
        cfg.min_value_chaos = 100.0
        cfg.save()

        with open(path) as f:
            content = f.read()
            data = json.loads(content)

        assert "\n" in content
        assert data["ui"]["min_value_chaos"] == 100.0

    def test_auto_save_on_property_change(self, tmp_path):
        path = get_unique_config_path(tmp_path)

        cfg = Config(path)
        cfg.min_value_chaos = 75.0

        cfg2 = Config(path)
        assert cfg2.min_value_chaos == 75.0


# -------------------------
# Utility Tests
# -------------------------

class TestConfigUtilities:
    def test_reset_to_defaults(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        cfg = Config(path)

        cfg.min_value_chaos = 100.0
        cfg.league = "Custom"
        cfg.enable_plugin("test")

        cfg.reset_to_defaults()

        assert cfg.min_value_chaos == 0.0
        assert cfg.league == "Standard"
        assert cfg.is_plugin_enabled("test") is False

    def test_export_config(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        out = tmp_path / f"export_{uuid.uuid4().hex}.json"

        cfg = Config(path)
        cfg.min_value_chaos = 123.45
        cfg.export_config(out)

        assert out.exists()
        with open(out) as f:
            data = json.load(f)
        assert data["ui"]["min_value_chaos"] == 123.45

    def test_repr(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.current_game = GameVersion.POE1
        cfg.league = "Test League"

        r = repr(cfg)
        assert "POE1" in r or "poe1" in r
        assert "Test League" in r


# -------------------------
# Edge Case Tests
# -------------------------

class TestConfigEdgeCases:
    def test_handles_corrupted_json(self, tmp_path):
        path = get_unique_config_path(tmp_path)

        with open(path, "w") as f:
            f.write("{ invalid json }")

        cfg = Config(path)
        assert cfg.min_value_chaos == 0.0

    def test_handles_empty_file(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        path.touch()

        cfg = Config(path)
        assert cfg.min_value_chaos == 0.0


# -------------------------
# Integration Tests
# -------------------------

class TestConfigIntegration:
    def test_switch_games_preserves_settings(self, tmp_path):
        p = get_unique_config_path(tmp_path)
        cfg = Config(p)

        cfg.current_game = GameVersion.POE1
        cfg.league = "PoE1 League"

        cfg.current_game = GameVersion.POE2
        cfg.league = "PoE2 League"

        cfg.current_game = GameVersion.POE1
        assert cfg.league == "PoE1 League"

    def test_full_workflow(self, tmp_path):
        p = get_unique_config_path(tmp_path)
        cfg = Config(p)

        cfg.current_game = GameVersion.POE1
        cfg.league = "Keepers of the Flame"
        cfg.min_value_chaos = 50.0
        cfg.show_vendor_items = False
        cfg.window_size = (1920, 1080)
        cfg.enable_plugin("price_alert")
        cfg.enable_plugin("export")

        cfg2 = Config(p)

        assert cfg2.current_game == GameVersion.POE1
        assert cfg2.league == "Keepers of the Flame"
        assert cfg2.min_value_chaos == 50.0
        assert cfg2.show_vendor_items is False
        assert cfg2.window_size == (1920, 1080)
        assert cfg2.is_plugin_enabled("price_alert")
        assert cfg2.is_plugin_enabled("export")


# -------------------------
# Theme Settings Tests
# -------------------------

class TestThemeSettings:
    def test_theme_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.theme == "dark"

    def test_theme_setter_valid(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.theme = "light"
        assert cfg.theme == "light"

        cfg.theme = "system"
        assert cfg.theme == "system"

    def test_theme_setter_invalid_falls_back(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.theme = "invalid_theme"
        assert cfg.theme == "dark"

    def test_theme_persists(self, tmp_path):
        path = get_unique_config_path(tmp_path)
        cfg = Config(path)
        cfg.theme = "light"

        cfg2 = Config(path)
        assert cfg2.theme == "light"

    def test_accent_color_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.accent_color is None

    def test_accent_color_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.accent_color = "divine"
        assert cfg.accent_color == "divine"

    def test_accent_color_none(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.accent_color = "chaos"
        cfg.accent_color = None
        assert cfg.accent_color is None


# -------------------------
# System Tray Settings Tests
# -------------------------

class TestSystemTraySettings:
    def test_minimize_to_tray_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.minimize_to_tray is True

    def test_minimize_to_tray_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.minimize_to_tray = False
        assert cfg.minimize_to_tray is False

    def test_start_minimized_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.start_minimized is False

    def test_start_minimized_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.start_minimized = True
        assert cfg.start_minimized is True

    def test_show_tray_notifications_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.show_tray_notifications is True

    def test_show_tray_notifications_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.show_tray_notifications = False
        assert cfg.show_tray_notifications is False

    def test_tray_alert_threshold_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.tray_alert_threshold == 50.0

    def test_tray_alert_threshold_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.tray_alert_threshold = 100.0
        assert cfg.tray_alert_threshold == 100.0

    def test_tray_alert_threshold_clamps_negative(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.tray_alert_threshold = -10.0
        assert cfg.tray_alert_threshold == 0.0


# -------------------------
# Verdict Settings Tests
# -------------------------

class TestVerdictSettings:
    def test_verdict_vendor_threshold_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.verdict_vendor_threshold == 2.0

    def test_verdict_vendor_threshold_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.verdict_vendor_threshold = 5.0
        assert cfg.verdict_vendor_threshold == 5.0

    def test_verdict_vendor_threshold_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.verdict_vendor_threshold = 0.01  # Below min
        assert cfg.verdict_vendor_threshold == 0.1

        cfg.verdict_vendor_threshold = 100.0  # Above max
        assert cfg.verdict_vendor_threshold == 50.0

    def test_verdict_keep_threshold_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.verdict_keep_threshold == 15.0

    def test_verdict_keep_threshold_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.verdict_keep_threshold = 25.0
        assert cfg.verdict_keep_threshold == 25.0

    def test_verdict_keep_threshold_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.verdict_keep_threshold = 0.5  # Below min
        assert cfg.verdict_keep_threshold == 1.0

        cfg.verdict_keep_threshold = 1000.0  # Above max
        assert cfg.verdict_keep_threshold == 500.0

    def test_verdict_preset_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.verdict_preset == "default"

    def test_verdict_preset_setter_valid(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.verdict_preset = "league_start"
        assert cfg.verdict_preset == "league_start"

        cfg.verdict_preset = "ssf"
        assert cfg.verdict_preset == "ssf"

    def test_verdict_preset_setter_invalid_ignored(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.verdict_preset = "league_start"
        cfg.verdict_preset = "invalid_preset"
        # Should remain unchanged
        assert cfg.verdict_preset == "league_start"


# -------------------------
# Accessibility Settings Tests
# -------------------------

class TestAccessibilitySettings:
    def test_font_scale_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.font_scale == 1.0

    def test_font_scale_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.font_scale = 1.2
        assert cfg.font_scale == 1.2

    def test_font_scale_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.font_scale = 0.5  # Below min
        assert cfg.font_scale == 0.8

        cfg.font_scale = 2.0  # Above max
        assert cfg.font_scale == 1.5

    def test_tooltip_delay_ms_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.tooltip_delay_ms == 500

    def test_tooltip_delay_ms_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.tooltip_delay_ms = 1000
        assert cfg.tooltip_delay_ms == 1000

    def test_tooltip_delay_ms_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.tooltip_delay_ms = 50  # Below min
        assert cfg.tooltip_delay_ms == 100

        cfg.tooltip_delay_ms = 5000  # Above max
        assert cfg.tooltip_delay_ms == 2000

    def test_reduce_animations_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.reduce_animations is False

    def test_reduce_animations_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.reduce_animations = True
        assert cfg.reduce_animations is True


# -------------------------
# Performance Settings Tests
# -------------------------

class TestPerformanceSettings:
    def test_rankings_cache_hours_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.rankings_cache_hours == 24

    def test_rankings_cache_hours_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.rankings_cache_hours = 48
        assert cfg.rankings_cache_hours == 48

    def test_rankings_cache_hours_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.rankings_cache_hours = 0  # Below min
        assert cfg.rankings_cache_hours == 1

        cfg.rankings_cache_hours = 500  # Above max
        assert cfg.rankings_cache_hours == 168

    def test_price_cache_ttl_seconds_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.price_cache_ttl_seconds == 3600

    def test_price_cache_ttl_seconds_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.price_cache_ttl_seconds = 1800
        assert cfg.price_cache_ttl_seconds == 1800

    def test_price_cache_ttl_seconds_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.price_cache_ttl_seconds = 100  # Below min
        assert cfg.price_cache_ttl_seconds == 300

        cfg.price_cache_ttl_seconds = 10000  # Above max
        assert cfg.price_cache_ttl_seconds == 7200

    def test_toast_duration_ms_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.toast_duration_ms == 3000

    def test_toast_duration_ms_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.toast_duration_ms = 5000
        assert cfg.toast_duration_ms == 5000

    def test_toast_duration_ms_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.toast_duration_ms = 500  # Below min
        assert cfg.toast_duration_ms == 1000

        cfg.toast_duration_ms = 20000  # Above max
        assert cfg.toast_duration_ms == 10000

    def test_history_max_entries_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.history_max_entries == 100

    def test_history_max_entries_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.history_max_entries = 200
        assert cfg.history_max_entries == 200

    def test_history_max_entries_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.history_max_entries = 5  # Below min
        assert cfg.history_max_entries == 10

        cfg.history_max_entries = 1000  # Above max
        assert cfg.history_max_entries == 500


# -------------------------
# API Rate Limit Settings Tests
# -------------------------

class TestAPIRateLimitSettings:
    def test_api_rate_limit_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.api_rate_limit == 0.33

    def test_api_rate_limit_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.api_rate_limit = 0.5
        assert cfg.api_rate_limit == 0.5

    def test_api_rate_limit_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.api_rate_limit = 0.1  # Below min
        assert cfg.api_rate_limit == 0.2

        cfg.api_rate_limit = 2.0  # Above max
        assert cfg.api_rate_limit == 1.0

    def test_api_retry_logging_verbosity_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.api_retry_logging_verbosity == "minimal"

    def test_api_retry_logging_verbosity_detailed(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.data["api"]["retry_logging_verbosity"] = "detailed"
        assert cfg.api_retry_logging_verbosity == "detailed"


# -------------------------
# API Pricing TTLs and Timeouts Tests
# -------------------------

class TestAPIPricingSettings:
    def test_get_pricing_ttls_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        ttls = cfg.get_pricing_ttls()
        assert isinstance(ttls, dict)

    def test_set_pricing_ttl(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_pricing_ttl("poe_ninja:currencyoverview", 1800)
        ttls = cfg.get_pricing_ttls()
        assert ttls["poe_ninja:currencyoverview"] == 1800

    def test_set_pricing_ttl_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_pricing_ttl("test_endpoint", 30)  # Below min
        assert cfg.get_pricing_ttls()["test_endpoint"] == 60

        cfg.set_pricing_ttl("test_endpoint", 100000)  # Above max
        assert cfg.get_pricing_ttls()["test_endpoint"] == 86400

    def test_price_cache_ttl_for_with_endpoint(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_pricing_ttl("custom_endpoint", 1200)
        assert cfg.price_cache_ttl_for("custom_endpoint") == 1200

    def test_price_cache_ttl_for_unknown_endpoint(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        # Should fall back to performance.price_cache_ttl_seconds
        ttl = cfg.price_cache_ttl_for("unknown_endpoint")
        assert ttl == 3600

    def test_price_cache_ttl_for_with_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        ttl = cfg.price_cache_ttl_for(None, default=600)
        assert ttl == 3600  # Still uses performance setting

    def test_get_api_timeouts_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        connect, read = cfg.get_api_timeouts()
        assert connect == 10
        assert read == 10

    def test_set_api_timeouts(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_api_timeouts(15, 30)
        connect, read = cfg.get_api_timeouts()
        assert connect == 15
        assert read == 30

    def test_set_api_timeouts_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_api_timeouts(0, 500)  # Out of bounds
        connect, read = cfg.get_api_timeouts()
        assert connect == 1  # Min clamped
        assert read == 300  # Max clamped


# -------------------------
# Display Policy Tests
# -------------------------

class TestDisplayPolicy:
    def test_display_policy_returns_dict(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        dp = cfg.display_policy
        assert isinstance(dp, dict)

    def test_set_display_policy(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_display_policy({"show_confidence": False})
        dp = cfg.display_policy
        assert dp.get("show_confidence") is False

    def test_set_display_policy_invalid_type_ignored(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_display_policy("not a dict")  # type: ignore
        # Should not crash, policy should still work
        assert isinstance(cfg.display_policy, dict)


# -------------------------
# Cross-Source Arbitration Tests
# -------------------------

class TestCrossSourceArbitration:
    def test_use_cross_source_arbitration_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.use_cross_source_arbitration is False

    def test_use_cross_source_arbitration_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.use_cross_source_arbitration = True
        assert cfg.use_cross_source_arbitration is True

    def test_enabled_sources_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        sources = cfg.enabled_sources
        assert isinstance(sources, dict)

    def test_set_enabled_sources(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_enabled_sources({"poe_ninja": True, "poe_watch": False})
        sources = cfg.enabled_sources
        assert sources["poe_ninja"] is True
        assert sources["poe_watch"] is False

    def test_set_enabled_sources_invalid_type_ignored(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.set_enabled_sources("not a dict")  # type: ignore
        # Should not crash
        assert isinstance(cfg.enabled_sources, dict)


# -------------------------
# Stash Settings Tests
# -------------------------

class TestStashSettings:
    def test_account_name_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.account_name == ""

    def test_account_name_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.account_name = "TestAccount"
        assert cfg.account_name == "TestAccount"

    def test_stash_last_fetch_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.stash_last_fetch is None

    def test_stash_last_fetch_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.stash_last_fetch = "2024-01-01T12:00:00"
        assert cfg.stash_last_fetch == "2024-01-01T12:00:00"

    def test_has_stash_credentials_false(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.has_stash_credentials() is False

    def test_has_stash_credentials_partial(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.account_name = "TestAccount"
        # No poesessid
        assert cfg.has_stash_credentials() is False


# -------------------------
# AI Settings Tests
# -------------------------

class TestAISettings:
    def test_ai_provider_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.ai_provider == ""

    def test_ai_provider_setter_valid(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_provider = "gemini"
        assert cfg.ai_provider == "gemini"

        cfg.ai_provider = "claude"
        assert cfg.ai_provider == "claude"

        cfg.ai_provider = "ollama"
        assert cfg.ai_provider == "ollama"

    def test_ai_provider_setter_invalid(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_provider = "invalid_provider"
        assert cfg.ai_provider == ""

    def test_ai_max_tokens_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.ai_max_tokens == 500

    def test_ai_max_tokens_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_max_tokens = 1000
        assert cfg.ai_max_tokens == 1000

    def test_ai_max_tokens_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_max_tokens = 50  # Below min
        assert cfg.ai_max_tokens == 100

        cfg.ai_max_tokens = 5000  # Above max
        assert cfg.ai_max_tokens == 2000

    def test_ai_timeout_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        # Default is 30 for non-ollama
        assert cfg.ai_timeout == 30

    def test_ai_timeout_ollama_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_provider = "ollama"
        # Clear any stored timeout to test dynamic default
        if "timeout_seconds" in cfg.data.get("ai", {}):
            del cfg.data["ai"]["timeout_seconds"]
        # Ollama gets higher default when no stored value
        assert cfg.ai_timeout == 180

    def test_ai_timeout_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_timeout = 60
        assert cfg.ai_timeout == 60

    def test_ai_timeout_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_timeout = 5  # Below min
        assert cfg.ai_timeout == 10

        cfg.ai_timeout = 500  # Above max
        assert cfg.ai_timeout == 300

    def test_has_ai_configured_false(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.has_ai_configured() is False

    def test_has_ai_configured_ollama(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_provider = "ollama"
        # Ollama doesn't need API key
        assert cfg.has_ai_configured() is True

    def test_ollama_host_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.ollama_host == "http://localhost:11434"

    def test_ollama_host_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ollama_host = "http://192.168.1.100:11434"
        assert cfg.ollama_host == "http://192.168.1.100:11434"

    def test_ollama_host_empty_resets(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ollama_host = ""
        assert cfg.ollama_host == "http://localhost:11434"

    def test_ollama_model_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.ollama_model == "deepseek-r1:14b"

    def test_ollama_model_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ollama_model = "llama2:7b"
        assert cfg.ollama_model == "llama2:7b"

    def test_ai_custom_prompt_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.ai_custom_prompt == ""

    def test_ai_custom_prompt_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_custom_prompt = "Custom prompt {item_text}"
        assert cfg.ai_custom_prompt == "Custom prompt {item_text}"

    def test_ai_build_name_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.ai_build_name == ""

    def test_ai_build_name_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.ai_build_name = "Lightning Arrow Deadeye"
        assert cfg.ai_build_name == "Lightning Arrow Deadeye"


# -------------------------
# Loot Tracking Tests
# -------------------------

class TestLootTrackingSettings:
    def test_loot_tracking_enabled_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.loot_tracking_enabled is False

    def test_loot_tracking_enabled_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_tracking_enabled = True
        assert cfg.loot_tracking_enabled is True

    def test_loot_client_txt_path_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.loot_client_txt_path == ""

    def test_loot_client_txt_path_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_client_txt_path = "C:/Games/PoE/logs/Client.txt"
        assert cfg.loot_client_txt_path == "C:/Games/PoE/logs/Client.txt"

    def test_loot_tracked_tabs_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.loot_tracked_tabs == []

    def test_loot_tracked_tabs_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_tracked_tabs = ["Dump", "Currency"]
        assert cfg.loot_tracked_tabs == ["Dump", "Currency"]

    def test_loot_min_value_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.loot_min_value == 1.0

    def test_loot_min_value_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_min_value = 5.0
        assert cfg.loot_min_value == 5.0

    def test_loot_min_value_clamps_negative(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_min_value = -10.0
        assert cfg.loot_min_value == 0.0

    def test_loot_notify_high_value_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.loot_notify_high_value is True

    def test_loot_notify_high_value_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_notify_high_value = False
        assert cfg.loot_notify_high_value is False

    def test_loot_high_value_threshold_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.loot_high_value_threshold == 50.0

    def test_loot_high_value_threshold_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_high_value_threshold = 100.0
        assert cfg.loot_high_value_threshold == 100.0

    def test_loot_poll_interval_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.loot_poll_interval == 1.0

    def test_loot_poll_interval_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_poll_interval = 2.0
        assert cfg.loot_poll_interval == 2.0

    def test_loot_poll_interval_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.loot_poll_interval = 0.1  # Below min
        assert cfg.loot_poll_interval == 0.5

        cfg.loot_poll_interval = 10.0  # Above max
        assert cfg.loot_poll_interval == 5.0


# -------------------------
# Background Refresh Tests
# -------------------------

class TestBackgroundRefreshSettings:
    def test_background_refresh_enabled_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.background_refresh_enabled is True

    def test_background_refresh_enabled_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.background_refresh_enabled = False
        assert cfg.background_refresh_enabled is False

    def test_price_refresh_interval_minutes_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.price_refresh_interval_minutes == 30

    def test_price_refresh_interval_minutes_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.price_refresh_interval_minutes = 60
        assert cfg.price_refresh_interval_minutes == 60

    def test_price_refresh_interval_minutes_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.price_refresh_interval_minutes = 2  # Below min
        assert cfg.price_refresh_interval_minutes == 5

        cfg.price_refresh_interval_minutes = 500  # Above max
        assert cfg.price_refresh_interval_minutes == 240

    def test_price_change_threshold_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.price_change_threshold == 0.10

    def test_price_change_threshold_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.price_change_threshold = 0.25
        assert cfg.price_change_threshold == 0.25

    def test_price_change_threshold_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.price_change_threshold = 0.01  # Below min
        assert cfg.price_change_threshold == 0.05

        cfg.price_change_threshold = 1.0  # Above max
        assert cfg.price_change_threshold == 0.50


# -------------------------
# Item Cache Tests
# -------------------------

class TestItemCacheSettings:
    def test_item_cache_enabled_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.item_cache_enabled is True

    def test_item_cache_enabled_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.item_cache_enabled = False
        assert cfg.item_cache_enabled is False

    def test_item_cache_ttl_seconds_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.item_cache_ttl_seconds == 300

    def test_item_cache_ttl_seconds_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.item_cache_ttl_seconds = 120
        assert cfg.item_cache_ttl_seconds == 120

    def test_item_cache_ttl_seconds_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.item_cache_ttl_seconds = 30  # Below min
        assert cfg.item_cache_ttl_seconds == 60

        cfg.item_cache_ttl_seconds = 1000  # Above max
        assert cfg.item_cache_ttl_seconds == 600

    def test_item_cache_max_size_default(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        assert cfg.item_cache_max_size == 500

    def test_item_cache_max_size_setter(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.item_cache_max_size = 1000
        assert cfg.item_cache_max_size == 1000

    def test_item_cache_max_size_guardrails(self, tmp_path):
        cfg = Config(get_unique_config_path(tmp_path))
        cfg.item_cache_max_size = 50  # Below min
        assert cfg.item_cache_max_size == 100

        cfg.item_cache_max_size = 5000  # Above max
        assert cfg.item_cache_max_size == 2000
