"""
Configuration management for the PoE Price Checker.
Handles user settings, game preferences, and persistence.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from core.game_version import GameVersion, GameConfig

logger = logging.getLogger(__name__)


class Config:
    """
    Application configuration with JSON persistence.
    Stores settings per game version (PoE1 and PoE2 can have different leagues).
    """

    DEFAULT_CONFIG = {
        "current_game": "poe1",
        "games": {
            "poe1": {
                "league": "Standard",
                "divine_chaos_rate": 1.0,
                "last_price_update": None
            },
            "poe2": {
                "league": "Standard",
                "divine_chaos_rate": 1.0,
                "last_price_update": None
            }
        },
        "ui": {
            "min_value_chaos": 0.0,
            "show_vendor_items": True,
            "window_width": 1200,
            "window_height": 800
        },
        "api": {
            "auto_detect_league": True,
            "cache_ttl_seconds": 3600,
            "rate_limit_per_second": 0.33
        },
        "plugins": {
            "enabled": []
        }
    }

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to config JSON file. If None, uses default location.
        """
        if config_file is None:
            config_file = Path.home() / '.poe_price_checker' / 'config.json'

        self.config_file = config_file
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        self.data = self._load()

        logger.info(f"Config loaded from {self.config_file}")

    def _load(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Merge with defaults (in case new keys were added)
                    merged = self._merge_with_defaults(data)
                    logger.info("Configuration loaded successfully")
                    return merged

            except Exception as e:
                logger.error(f"Failed to load config: {e}. Using defaults.")
                return self.DEFAULT_CONFIG.copy()
        else:
            logger.info("No config file found, using defaults")
            return self.DEFAULT_CONFIG.copy()

    def _merge_with_defaults(self, user_config: Dict) -> Dict:
        """Merge user config with defaults to handle new keys"""
        merged = self.DEFAULT_CONFIG.copy()

        # Deep merge
        for key, value in user_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key].update(value)
            else:
                merged[key] = value

        return merged

    def save(self):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    # === Current Game ===

    @property
    def current_game(self) -> GameVersion:
        """Get currently selected game version"""
        game_str = self.data.get("current_game", "poe1")
        return GameVersion.from_string(game_str) or GameVersion.POE1

    @current_game.setter
    def current_game(self, value: GameVersion):
        """Set currently selected game version"""
        self.data["current_game"] = value.value
        self.save()

    def get_game_config(self, game: Optional[GameVersion] = None) -> GameConfig:
        """
        Get configuration for a specific game.

        Args:
            game: Game version, or None for current game

        Returns:
            GameConfig object
        """
        if game is None:
            game = self.current_game

        game_data = self.data["games"].get(game.value, {})

        return GameConfig(
            game_version=game,
            league=game_data.get("league", "Standard"),
            divine_chaos_rate=game_data.get("divine_chaos_rate", 1.0)
        )

    def set_game_config(self, game_config: GameConfig):
        """
        Update configuration for a game.

        Args:
            game_config: GameConfig object with updated values
        """
        game_key = game_config.game_version.value

        if game_key not in self.data["games"]:
            self.data["games"][game_key] = {}

        self.data["games"][game_key]["league"] = game_config.league
        self.data["games"][game_key]["divine_chaos_rate"] = game_config.divine_chaos_rate
        self.data["games"][game_key]["last_price_update"] = datetime.now().isoformat()

        self.save()

    # === League Management ===

    @property
    def league(self) -> str:
        """Get league for current game"""
        return self.get_game_config().league

    @league.setter
    def league(self, value: str):
        """Set league for current game"""
        config = self.get_game_config()
        config.league = value
        self.set_game_config(config)

    # === UI Settings ===

    @property
    def min_value_chaos(self) -> float:
        """Minimum chaos value filter"""
        return self.data["ui"].get("min_value_chaos", 0.0)

    @min_value_chaos.setter
    def min_value_chaos(self, value: float):
        """Set minimum chaos value filter"""
        self.data["ui"]["min_value_chaos"] = value
        self.save()

    @property
    def show_vendor_items(self) -> bool:
        """Whether to show items below minimum value"""
        return self.data["ui"].get("show_vendor_items", True)

    @show_vendor_items.setter
    def show_vendor_items(self, value: bool):
        """Set whether to show vendor items"""
        self.data["ui"]["show_vendor_items"] = value
        self.save()

    @property
    def window_size(self) -> tuple[int, int]:
        """Get window size (width, height)"""
        return (
            self.data["ui"].get("window_width", 1200),
            self.data["ui"].get("window_height", 800)
        )

    @window_size.setter
    def window_size(self, value: tuple[int, int]):
        """Set window size"""
        self.data["ui"]["window_width"] = value[0]
        self.data["ui"]["window_height"] = value[1]
        self.save()

    # === API Settings ===

    @property
    def auto_detect_league(self) -> bool:
        """Whether to auto-detect current league"""
        return self.data["api"].get("auto_detect_league", True)

    @auto_detect_league.setter
    def auto_detect_league(self, value: bool):
        """Set auto-detect league"""
        self.data["api"]["auto_detect_league"] = value
        self.save()

    # === Plugin Management ===

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled"""
        return plugin_name in self.data["plugins"].get("enabled", [])

    def enable_plugin(self, plugin_name: str):
        """Enable a plugin"""
        if plugin_name not in self.data["plugins"]["enabled"]:
            self.data["plugins"]["enabled"].append(plugin_name)
            self.save()

    def disable_plugin(self, plugin_name: str):
        """Disable a plugin"""
        if plugin_name in self.data["plugins"]["enabled"]:
            self.data["plugins"]["enabled"].remove(plugin_name)
            self.save()

    # === Utility ===

    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.data = self.DEFAULT_CONFIG.copy()
        self.save()
        logger.warning("Configuration reset to defaults")

    def export_config(self, export_path: Path):
        """Export config to a different file"""
        import shutil
        shutil.copy(self.config_file, export_path)
        logger.info(f"Config exported to {export_path}")

    def __repr__(self) -> str:
        return f"Config(game={self.current_game}, league={self.league})"


# Testing
if __name__ == "__main__":
    print("=== Config System Test ===\n")

    # Create config
    config = Config()

    print(f"Current config: {config}")
    print(f"League: {config.league}")
    print(f"Min value: {config.min_value_chaos}c")
    print(f"Auto-detect league: {config.auto_detect_league}")

    # Test game switching
    print("\n=== Switching to PoE2 ===")
    config.current_game = GameVersion.POE2
    print(f"Current game: {config.current_game.display_name()}")
    print(f"League: {config.league}")

    # Update league
    config.league = "Standard Settlers"
    print(f"Updated league: {config.league}")

    # Switch back to PoE1
    print("\n=== Switching back to PoE1 ===")
    config.current_game = GameVersion.POE1
    print(f"League: {config.league}")  # Should still be the PoE1 league

    # Test plugin management
    print("\n=== Plugin Management ===")
    config.enable_plugin("price_alert")
    config.enable_plugin("export_plugin")
    print(f"Price Alert enabled: {config.is_plugin_enabled('price_alert')}")
    print(f"Stats Plugin enabled: {config.is_plugin_enabled('stats_plugin')}")

    config.disable_plugin("price_alert")
    print(f"Price Alert enabled (after disable): {config.is_plugin_enabled('price_alert')}")

    print(f"\nConfig file location: {config.config_file}")