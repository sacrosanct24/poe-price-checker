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
        out = tmp_path / f"export_{time.time_ns()}.json"

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
