"""
Unit tests for core.config module - FIXED VERSION WITH PROPER ISOLATION

All tests now use unique file paths to prevent state leakage.
"""

import pytest
import json
import time
from pathlib import Path

from core.config import Config
from core.game_version import GameVersion, GameConfig
# tests/unit/core/test_price_multi.py
import pytest
pytestmark = pytest.mark.unit


def get_unique_config_path(tmp_path):
    """Generate a unique config file path to prevent test interference"""
    return tmp_path / f"config_{time.time_ns()}.json"


class TestConfigInitialization:
    """Tests for config initialization."""

    def test_creates_config_file(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)
        config = Config(config_file)
        config.save()  # Must call save() to create file

        assert config_file.exists()

    def test_loads_defaults_for_new_config(self, temp_config):
        assert temp_config.current_game == GameVersion.POE1
        assert temp_config.min_value_chaos == 0.0
        assert temp_config.show_vendor_items is True

    def test_creates_default_path_if_none(self):
        config = Config()

        expected_path = Path.home() / '.poe_price_checker' / 'config.json'
        assert config.config_file == expected_path

    def test_loads_existing_config(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        # Create config with custom values
        config1 = Config(config_file)
        config1.min_value_chaos = 50.0
        config1.league = "Custom League"

        # Load same config file
        config2 = Config(config_file)

        assert config2.min_value_chaos == 50.0
        assert config2.league == "Custom League"

    def test_merges_with_defaults_on_load(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        # Write partial config (missing some keys)
        partial_config = {
            "current_game": "poe1",
            "games": {
                "poe1": {
                    "league": "Test League"
                    # Missing other fields
                }
            }
            # Missing ui, api, plugins sections
        }

        with open(config_file, 'w') as f:
            json.dump(partial_config, f)

        # Load should merge with defaults
        config = Config(config_file)

        assert config.league == "Test League"  # Custom value preserved
        assert config.min_value_chaos == 0.0  # Default value added


class TestGameVersionManagement:
    """Tests for game version and league management."""

    def test_current_game_property(self, temp_config):
        assert temp_config.current_game == GameVersion.POE1

    def test_set_current_game(self, temp_config):
        temp_config.current_game = GameVersion.POE2

        assert temp_config.current_game == GameVersion.POE2

    def test_set_current_game_persists(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        config = Config(config_file)
        config.current_game = GameVersion.POE2

        # Reload config
        config2 = Config(config_file)
        assert config2.current_game == GameVersion.POE2

    def test_get_game_config_for_current_game(self, temp_config):
        game_config = temp_config.get_game_config()

        assert game_config.game_version == GameVersion.POE1
        assert game_config.league == "Standard"

    def test_get_game_config_for_specific_game(self, temp_config):
        poe2_config = temp_config.get_game_config(GameVersion.POE2)

        assert poe2_config.game_version == GameVersion.POE2

    def test_set_game_config(self, temp_config):
        new_config = GameConfig(
            game_version=GameVersion.POE1,
            league="Custom League",
            divine_chaos_rate=350.0
        )

        temp_config.set_game_config(new_config)

        retrieved = temp_config.get_game_config(GameVersion.POE1)
        assert retrieved.league == "Custom League"
        assert retrieved.divine_chaos_rate == 350.0

    def test_default_config_isolation_between_files(self, tmp_path):
        file1 = get_unique_config_path(tmp_path)
        file2 = get_unique_config_path(tmp_path)

        cfg1 = Config(file1)
        cfg2 = Config(file2)

        # Change a nested value via cfg1
        cfg1.min_value_chaos = 123.0
        cfg1.save()

        # Reload cfg2 from its own file
        cfg2_reloaded = Config(file2)

        # Must NOT see cfg1's change
        assert cfg2_reloaded.min_value_chaos == 0.0

    def test_reset_to_defaults_resets_all_sections(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)
        cfg = Config(config_file)

        cfg.current_game = GameVersion.POE2
        cfg.league = "League X"
        cfg.min_value_chaos = 42.0
        cfg.show_vendor_items = False
        cfg.enable_plugin("price_alert")

        cfg.reset_to_defaults()

        reloaded = Config(config_file)
        assert reloaded.current_game == GameVersion.POE1
        assert reloaded.league == "Standard"
        assert reloaded.min_value_chaos == 0.0
        assert reloaded.show_vendor_items is True
        assert reloaded.is_plugin_enabled("price_alert") is False

    def test_auto_detect_league_default_and_persist(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)
        cfg = Config(config_file)

        # Default should be True
        assert cfg.auto_detect_league is True

        cfg.auto_detect_league = False
        reloaded = Config(config_file)

        assert reloaded.auto_detect_league is False

    def test_league_property_gets_current_game_league(self, temp_config):
        temp_config.current_game = GameVersion.POE1
        assert temp_config.league == "Standard"

    def test_league_property_sets_current_game_league(self, temp_config):
        temp_config.current_game = GameVersion.POE1
        temp_config.league = "Keepers of the Flame"

        poe1_config = temp_config.get_game_config(GameVersion.POE1)
        assert poe1_config.league == "Keepers of the Flame"

        # PoE2 league should be unchanged
        poe2_config = temp_config.get_game_config(GameVersion.POE2)
        assert poe2_config.league == "Standard"

    def test_separate_leagues_per_game(self, temp_config):
        # Set PoE1 league
        temp_config.current_game = GameVersion.POE1
        temp_config.league = "PoE1 League"

        # Set PoE2 league
        temp_config.current_game = GameVersion.POE2
        temp_config.league = "PoE2 League"

        # Verify both are stored separately
        poe1_cfg = temp_config.get_game_config(GameVersion.POE1)
        poe2_cfg = temp_config.get_game_config(GameVersion.POE2)

        assert poe1_cfg.league == "PoE1 League"
        assert poe2_cfg.league == "PoE2 League"


class TestUISettings:
    """Tests for UI settings properties."""

    def test_min_value_chaos_property(self, temp_config):
        assert temp_config.min_value_chaos == 0.0

        temp_config.min_value_chaos = 25.5
        assert temp_config.min_value_chaos == 25.5

    def test_show_vendor_items_property(self, temp_config):
        assert temp_config.show_vendor_items is True

        temp_config.show_vendor_items = False
        assert temp_config.show_vendor_items is False

    def test_window_size_property(self, temp_config):
        default_size = temp_config.window_size
        assert default_size == (1200, 800)

        temp_config.window_size = (1920, 1080)
        assert temp_config.window_size == (1920, 1080)

    def test_ui_settings_persist(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        config = Config(config_file)
        config.min_value_chaos = 100.0
        config.show_vendor_items = False
        config.window_size = (1600, 900)

        # Reload
        config2 = Config(config_file)

        assert config2.min_value_chaos == 100.0
        assert config2.show_vendor_items is False
        assert config2.window_size == (1600, 900)


class TestAPISettings:
    """Tests for API settings properties."""

    def test_auto_detect_league_property(self, temp_config):
        assert temp_config.auto_detect_league is True

        temp_config.auto_detect_league = False
        assert temp_config.auto_detect_league is False


class TestPluginManagement:
    """Tests for plugin state management."""

    def test_is_plugin_enabled_false_by_default(self, temp_config):
        assert temp_config.is_plugin_enabled("test_plugin") is False

    def test_enable_plugin(self, temp_config):
        temp_config.enable_plugin("price_alert")

        assert temp_config.is_plugin_enabled("price_alert") is True

    def test_disable_plugin(self, temp_config):
        temp_config.enable_plugin("test_plugin")
        temp_config.disable_plugin("test_plugin")

        assert temp_config.is_plugin_enabled("test_plugin") is False

    def test_enable_plugin_idempotent(self, temp_config):
        temp_config.enable_plugin("test")
        temp_config.enable_plugin("test")

        # Should only be in list once
        enabled = temp_config.data["plugins"]["enabled"]
        assert enabled.count("test") == 1

    def test_disable_plugin_that_was_never_enabled(self, temp_config):
        # Should not raise error
        temp_config.disable_plugin("nonexistent")

        assert temp_config.is_plugin_enabled("nonexistent") is False

    def test_multiple_plugins(self, temp_config):
        temp_config.enable_plugin("plugin1")
        temp_config.enable_plugin("plugin2")
        temp_config.enable_plugin("plugin3")

        assert temp_config.is_plugin_enabled("plugin1") is True
        assert temp_config.is_plugin_enabled("plugin2") is True
        assert temp_config.is_plugin_enabled("plugin3") is True

        temp_config.disable_plugin("plugin2")

        assert temp_config.is_plugin_enabled("plugin1") is True
        assert temp_config.is_plugin_enabled("plugin2") is False
        assert temp_config.is_plugin_enabled("plugin3") is True


class TestConfigPersistence:
    """Tests for config save/load behavior."""

    def test_save_creates_json_file(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        config = Config(config_file)
        config.min_value_chaos = 50.0
        config.save()

        # Read raw JSON
        with open(config_file) as f:
            data = json.load(f)

        assert data["ui"]["min_value_chaos"] == 50.0

    def test_json_is_readable(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        config = Config(config_file)
        config.min_value_chaos = 100.0
        config.save()

        # Verify it's valid JSON with proper formatting
        with open(config_file) as f:
            content = f.read()
            data = json.loads(content)

        # Should be indented
        assert "\n" in content
        assert data["ui"]["min_value_chaos"] == 100.0

    def test_auto_save_on_property_changes(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        config = Config(config_file)
        config.min_value_chaos = 75.0
        # Don't call save() explicitly

        # Should have auto-saved
        config2 = Config(config_file)
        assert config2.min_value_chaos == 75.0


class TestConfigUtilities:
    """Tests for utility methods."""

    def test_reset_to_defaults(self, temp_config):
        # Modify config
        temp_config.min_value_chaos = 100.0
        temp_config.league = "Custom"
        temp_config.enable_plugin("test")

        # Reset
        temp_config.reset_to_defaults()

        # Should be back to defaults
        assert temp_config.min_value_chaos == 0.0
        assert temp_config.league == "Standard"
        assert temp_config.is_plugin_enabled("test") is False

    def test_export_config(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)
        export_file = tmp_path / f"exported_{time.time_ns()}.json"

        config = Config(config_file)
        config.min_value_chaos = 123.45

        config.export_config(export_file)

        # Verify export exists and is identical
        assert export_file.exists()

        with open(export_file) as f:
            exported_data = json.load(f)

        assert exported_data["ui"]["min_value_chaos"] == 123.45

    def test_repr(self, temp_config):
        temp_config.current_game = GameVersion.POE1
        temp_config.league = "Test League"

        repr_str = repr(temp_config)

        assert "POE1" in repr_str or "poe1" in repr_str
        assert "Test League" in repr_str


class TestConfigEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_corrupted_json(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        # Write invalid JSON
        with open(config_file, 'w') as f:
            f.write("{ invalid json }")

        # Should fall back to defaults without crashing
        config = Config(config_file)

        assert config.min_value_chaos == 0.0  # Default value

    def test_handles_empty_file(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        # Create empty file
        config_file.touch()

        # Should fall back to defaults
        config = Config(config_file)

        assert config.min_value_chaos == 0.0


class TestConfigIntegration:
    """Integration tests combining multiple features."""

    def test_switch_games_preserves_settings(self, temp_config):
        # Configure PoE1
        temp_config.current_game = GameVersion.POE1
        temp_config.league = "PoE1 League"

        # Configure PoE2
        temp_config.current_game = GameVersion.POE2
        temp_config.league = "PoE2 League"

        # Switch back to PoE1
        temp_config.current_game = GameVersion.POE1

        # PoE1 settings should be preserved
        assert temp_config.league == "PoE1 League"

    def test_full_workflow(self, tmp_path):
        config_file = get_unique_config_path(tmp_path)

        # Create config
        config = Config(config_file)

        # Set up PoE1
        config.current_game = GameVersion.POE1
        config.league = "Keepers of the Flame"

        # Set UI preferences
        config.min_value_chaos = 50.0
        config.show_vendor_items = False
        config.window_size = (1920, 1080)

        # Enable plugins
        config.enable_plugin("price_alert")
        config.enable_plugin("export")

        # Reload config
        config2 = Config(config_file)

        # Verify everything persisted
        assert config2.current_game == GameVersion.POE1
        assert config2.league == "Keepers of the Flame"
        assert config2.min_value_chaos == 50.0
        assert config2.show_vendor_items is False
        assert config2.window_size == (1920, 1080)
        assert config2.is_plugin_enabled("price_alert") is True
        assert config2.is_plugin_enabled("export") is True


if __name__ == "__main__":
    # Run tests with: pytest tests/test_config.py -v
    pytest.main([__file__, "-v"])