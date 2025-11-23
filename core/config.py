"""
Configuration management for the PoE Price Checker.
Handles user settings, game preferences, and persistence.
"""

import json
import logging
import copy
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from core.game_version import GameVersion, GameConfig

logger = logging.getLogger(__name__)


class Config:
    """
    Application configuration with JSON persistence.

    Key ideas:
    - Settings are stored per game version (PoE1 / PoE2) under the "games" key.
    - A single "current_game" string selects which game is "active" for league/UI.
    - The backing store is a JSON file on disk (user config file).
    """

    # NOTE: This structure is treated as immutable. Always use
    # _default_config_deepcopy() when you need a fresh copy of defaults.
    DEFAULT_CONFIG: Dict[str, Any] = {
        "current_game": "poe1",
        "games": {
            "poe1": {
                "league": "Standard",
                # 0.0 = "unknown", will fall back to poe.ninja or be set later
                "divine_chaos_rate": 0.0,
                "last_price_update": None,
            },
            "poe2": {
                "league": "Standard",
                "divine_chaos_rate": 0.0,
                "last_price_update": None,
            },
        },
        "ui": {
            "min_value_chaos": 0.0,
            "show_vendor_items": True,
            "window_width": 1200,
            "window_height": 800,
        },
        "api": {
            "auto_detect_league": True,
            "cache_ttl_seconds": 3600,
            "rate_limit_per_second": 0.33,
        },
        "plugins": {
            "enabled": [],
        },
    }

    def __init__(self, config_file: Optional[Path] = None) -> None:
        """
        Initialize configuration.

        Args:
            config_file: Optional path to config JSON file. When omitted,
                         the default path under ~/.poe_price_checker/config.json
                         is used.
        """
        self.config_file: Path = self._resolve_config_path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load data from disk (or defaults)
        self.data: Dict[str, Any] = self._load()
        logger.info(f"Config loaded from {self.config_file}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_config_path(config_file: Optional[Path]) -> Path:
        """
        Resolve the config file path, applying the default location when None.

        This keeps the path resolution logic in one place and allows
        tests / callers to always pass an explicit path for isolation.
        """
        if config_file is not None:
            return config_file
        return Path.home() / ".poe_price_checker" / "config.json"

    def _load(self) -> Dict[str, Any]:
        """Load configuration from JSON file, merging with defaults."""
        if self.config_file.exists():
            try:
                with self.config_file.open("r", encoding="utf-8") as f:
                    raw = json.load(f)

                # Merge with defaults (in case new keys were added)
                merged = self._merge_with_defaults(raw)
                logger.info("Configuration loaded successfully")
                return merged
            except Exception as exc:  # defensive
                logger.error(f"Failed to load config: {exc}. Using defaults.")
                return self._default_config_deepcopy()
        else:
            logger.info("No config file found, using defaults")
            return self._default_config_deepcopy()

    @classmethod
    def _default_config_deepcopy(cls) -> Dict[str, Any]:
        """
        Return a deep copy of the DEFAULT_CONFIG to avoid state leakage
        between instances or tests.

        This MUST be used whenever initializing config state from defaults.
        """
        return copy.deepcopy(cls.DEFAULT_CONFIG)

    def _merge_with_defaults(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user config with defaults to handle new keys.

        This is a shallow-merge per top-level section, but nested dictionaries
        are merged so new keys under e.g. "ui" or "api" will appear without
        discarding user-provided values.
        """
        merged = self._default_config_deepcopy()

        for key, value in user_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key].update(value)
            else:
                merged[key] = value

        return merged

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist the current configuration to the config file."""
        try:
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logger.info("Configuration saved")
        except Exception as exc:  # defensive
            logger.error(f"Failed to save config: {exc}")

    # ------------------------------------------------------------------
    # Current Game
    # ------------------------------------------------------------------

    @property
    def current_game(self) -> GameVersion:
        """Get the currently selected game version."""
        game_str = self.data.get("current_game", "poe1")
        return GameVersion.from_string(game_str) or GameVersion.POE1

    @current_game.setter
    def current_game(self, value: GameVersion) -> None:
        """
        Set the current game version and persist.

        This does NOT alter any per-game settings; it only switches which
        game's settings are considered "current".
        """
        self.data["current_game"] = value.value
        self.save()

    # ------------------------------------------------------------------
    # Game-specific configuration
    # ------------------------------------------------------------------

    def get_game_config(self, game: Optional[GameVersion] = None) -> GameConfig:
        """
        Get configuration for a specific game.

        Args:
            game: Game version, or None for the current game.

        Returns:
            GameConfig object representing the game-specific settings.
        """
        if game is None:
            game = self.current_game

        game_data = self.data["games"].get(game.value, {})

        return GameConfig(
            game_version=game,
            league=game_data.get("league", "Standard"),
            divine_chaos_rate=game_data.get("divine_chaos_rate", 1.0),
        )

    def set_game_config(self, game_config: GameConfig) -> None:
        """
        Update configuration for a game and persist changes.

        Args:
            game_config: GameConfig object with updated values.
        """
        game_key = game_config.game_version.value

        if game_key not in self.data["games"]:
            self.data["games"][game_key] = {}

        self.data["games"][game_key]["league"] = game_config.league
        self.data["games"][game_key]["divine_chaos_rate"] = game_config.divine_chaos_rate
        # NOTE: last_price_update is maintained as a "last update timestamp"
        self.data["games"][game_key]["last_price_update"] = datetime.now().isoformat()

        self.save()

    # ------------------------------------------------------------------
    # League Management
    # ------------------------------------------------------------------

    @property
    def league(self) -> str:
        """Get the league for the current game."""
        return self.get_game_config().league

    @league.setter
    def league(self, value: str) -> None:
        """Set the league for the current game and persist."""
        cfg = self.get_game_config()
        cfg.league = value
        self.set_game_config(cfg)

    # ------------------------------------------------------------------
    # UI Settings
    # ------------------------------------------------------------------

    @property
    def min_value_chaos(self) -> float:
        """Minimum chaos value filter."""
        return self.data["ui"].get("min_value_chaos", 0.0)

    @min_value_chaos.setter
    def min_value_chaos(self, value: float) -> None:
        """Set the minimum chaos value filter and persist."""
        self.data["ui"]["min_value_chaos"] = value
        self.save()

    @property
    def show_vendor_items(self) -> bool:
        """Whether to show items below minimum value."""
        return self.data["ui"].get("show_vendor_items", True)

    @show_vendor_items.setter
    def show_vendor_items(self, value: bool) -> None:
        """Set whether to show vendor items and persist."""
        self.data["ui"]["show_vendor_items"] = value
        self.save()

    @property
    def window_size(self) -> tuple[int, int]:
        """Get window size as (width, height)."""
        return (
            self.data["ui"].get("window_width", 1200),
            self.data["ui"].get("window_height", 800),
        )

    @window_size.setter
    def window_size(self, value: tuple[int, int]) -> None:
        """Set window size and persist."""
        width, height = value
        self.data["ui"]["window_width"] = width
        self.data["ui"]["window_height"] = height
        self.save()

    # ------------------------------------------------------------------
    # API Settings
    # ------------------------------------------------------------------

    @property
    def auto_detect_league(self) -> bool:
        """Whether to auto-detect the current league from external APIs."""
        return self.data["api"].get("auto_detect_league", True)

    @auto_detect_league.setter
    def auto_detect_league(self, value: bool) -> None:
        """Set auto-detect league behavior and persist."""
        self.data["api"]["auto_detect_league"] = bool(value)
        self.save()

    # ------------------------------------------------------------------
    # Plugin Management
    # ------------------------------------------------------------------

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled."""
        return plugin_name in self.data["plugins"].get("enabled", [])

    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a plugin and persist."""
        enabled = self.data["plugins"].setdefault("enabled", [])
        if plugin_name not in enabled:
            enabled.append(plugin_name)
            self.save()

    def disable_plugin(self, plugin_name: str) -> None:
        """Disable a plugin and persist."""
        enabled = self.data["plugins"].setdefault("enabled", [])
        if plugin_name in enabled:
            enabled.remove(plugin_name)
            self.save()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults and persist."""
        self.data = self._default_config_deepcopy()
        self.save()
        logger.warning("Configuration reset to defaults")

    def export_config(self, export_path: Path) -> None:
        """Export config to a different file."""
        import shutil

        shutil.copy(self.config_file, export_path)
        logger.info(f"Config exported to {export_path}")

    def __repr__(self) -> str:
        """Readable representation for debugging/logging."""
        return f"Config(game={self.current_game}, league={self.league})"


if __name__ == "__main__":  # pragma: no cover - manual smoke-test
    print("=== Config System Test ===")

    cfg = Config()
    print(f"Current config: {cfg}")
    print(f"League: {cfg.league}")
    print(f"Min value: {cfg.min_value_chaos}c")
    print(f"Auto-detect league: {cfg.auto_detect_league}")
    print(f"Config file: {cfg.config_file}")
