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
from core.secure_storage import encrypt_credential, decrypt_credential

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """
    Get the application config directory.

    Returns:
        Path to the config directory (~/.poe_price_checker/)
    """
    config_dir = Path.home() / ".poe_price_checker"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


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
            "theme": "dark",  # dark, light, or system
            "accent_color": None,  # None = theme default, or currency key like "chaos", "divine"
            "minimize_to_tray": True,  # Minimize to system tray instead of taskbar
            "start_minimized": False,  # Start application minimized to tray
            "show_tray_notifications": True,  # Show system notifications for price alerts
            "tray_alert_threshold": 50.0,  # Chaos value threshold for tray notifications
        },
        "accessibility": {
            "font_scale": 1.0,  # Font scaling factor (0.8 to 1.5)
            "tooltip_delay_ms": 500,  # Delay before showing tooltips
            "reduce_animations": False,  # Reduce motion for accessibility
        },
        "performance": {
            # Rankings cache expiry in hours (min 1, max 168 = 1 week)
            # Lower = fresher data but more API calls
            "rankings_cache_hours": 24,
            # Price data cache TTL in seconds (min 300 = 5 min, max 7200 = 2 hours)
            # GGG rate limits: ~1 request per 3 seconds is safe
            "price_cache_ttl_seconds": 3600,
            # Toast notification duration in milliseconds
            "toast_duration_ms": 3000,
            # Maximum history entries to keep (min 10, max 500)
            "history_max_entries": 100,
        },
        "api": {
            "auto_detect_league": True,
            "cache_ttl_seconds": 3600,
            # Rate limit for PoE API (requests per second)
            # GUARDRAIL: Min 0.2 (1 req/5s), Max 1.0 (1 req/s)
            # GGG recommends ~0.33 (1 req/3s) to avoid 429 errors
            "rate_limit_per_second": 0.33,
            # Verbosity of retry logging for API calls: "minimal" or "detailed"
            "retry_logging_verbosity": "minimal",
            # Per-area API config
            "pricing": {
                # Per-endpoint TTLs in seconds for pricing endpoints. Keys should
                # match client endpoint identifiers or URL paths used in requests.
                # Safe defaults: 1 hour, with guardrails applied in accessors.
                "ttls": {
                    # Examples (can be edited by the app at runtime):
                    # "poe_ninja:currencyoverview": 3600,
                    # "poe_watch:prices": 1800,
                }
            },
            # Explicit timeouts (seconds). Requests supports tuple (connect, read)
            # but we store them separately for clarity and compose as needed.
            "timeouts": {
                "connect": 10,
                "read": 10,
            },
        },
        "plugins": {
            "enabled": [],
        },
        "stash": {
            "poesessid": "",  # Session cookie for stash access
            "account_name": "",  # PoE account name
            "last_fetch": None,  # Last stash fetch timestamp
        },
        "pricing": {
            # Display policy thresholds (tunable)
            "display_policy": {
                "high_count": 20,
                "medium_count": 8,
                "high_spread": 0.35,
                "medium_spread": 0.6,
                "low_conf_spread": 0.8,
                "step_ge_100": 5.0,
                "step_ge_10": 1.0,
            },
            # Cross-source arbitration feature flag (off by default for safety)
            "use_cross_source_arbitration": False,
            # Persist enabled/disabled state of price sources by name
            # Example: {"poe.ninja": true, "poe.watch": false}
            "enabled_sources": {},
        },
        "ai": {
            # AI provider for item analysis: "gemini", "claude", "openai", or ""
            "provider": "",
            # API keys (encrypted) - user must provide their own
            "gemini_api_key": "",
            "claude_api_key": "",
            "openai_api_key": "",
            # Response settings
            "max_response_tokens": 500,  # Max tokens in AI response
            "timeout_seconds": 30,  # Request timeout
        },
        "loot_tracking": {
            # Path to Client.txt (empty = auto-detect)
            "client_txt_path": "",
            # Auto-start session when entering a map
            "auto_start_enabled": False,
            # Tabs to track for loot (empty list = all tabs)
            "tracked_tabs": [],
            # Minimum chaos value to count as loot
            "min_loot_value": 1.0,
            # Show notification on high-value drops
            "notify_high_value": True,
            "high_value_threshold": 50.0,
            # Polling interval for Client.txt in seconds
            "poll_interval": 1.0,
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
    # Pricing policy configuration
    # ------------------------------------------------------------------

    @property
    def display_policy(self) -> Dict[str, Any]:
        """Get the pricing display policy mapping from config.

        Returns a dict with keys matching core.price_estimation.DisplayPolicy.
        """
        pricing = self.data.get("pricing", {}) or {}
        dp = pricing.get("display_policy", {}) or {}
        # Merge with defaults to ensure all keys present
        defaults = self.DEFAULT_CONFIG["pricing"]["display_policy"].copy()
        defaults.update({k: v for k, v in dp.items() if v is not None})
        return defaults

    def set_display_policy(self, policy: Dict[str, Any]) -> None:
        """Update the pricing display policy mapping and persist."""
        if not isinstance(policy, dict):
            return
        self.data.setdefault("pricing", {})
        self.data["pricing"]["display_policy"] = {
            **self.DEFAULT_CONFIG["pricing"]["display_policy"],
            **policy,
        }
        self.save()

    # ------------------------------------------------------------------
    # API logging verbosity
    # ------------------------------------------------------------------

    @property
    def api_retry_logging_verbosity(self) -> str:
        """Return retry logging verbosity: "minimal" or "detailed"."""
        api = self.data.get("api", {}) or {}
        val = str(api.get("retry_logging_verbosity", "minimal")).lower()
        return "detailed" if val == "detailed" else "minimal"

    # ------------------------------------------------------------------
    # Cross-source arbitration & enabled sources persistence
    # ------------------------------------------------------------------

    @property
    def use_cross_source_arbitration(self) -> bool:
        pricing = self.data.get("pricing", {}) or {}
        return bool(pricing.get("use_cross_source_arbitration", False))

    @use_cross_source_arbitration.setter
    def use_cross_source_arbitration(self, enabled: bool) -> None:
        self.data.setdefault("pricing", {})
        self.data["pricing"]["use_cross_source_arbitration"] = bool(enabled)
        self.save()

    @property
    def enabled_sources(self) -> Dict[str, bool]:
        pricing = self.data.get("pricing", {}) or {}
        es = pricing.get("enabled_sources", {}) or {}
        # Coerce values to bools
        return {str(k): bool(v) for k, v in es.items()}

    def set_enabled_sources(self, mapping: Dict[str, Any]) -> None:
        if not isinstance(mapping, dict):
            return
        self.data.setdefault("pricing", {})
        coerced = {str(k): bool(v) for k, v in mapping.items()}
        self.data["pricing"]["enabled_sources"] = coerced
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

    @property
    def theme(self) -> str:
        """Get the UI theme (dark, light, or system)."""
        return self.data["ui"].get("theme", "dark")

    @theme.setter
    def theme(self, value: str) -> None:
        """Set the UI theme and persist."""
        if value not in ("dark", "light", "system"):
            value = "dark"
        self.data["ui"]["theme"] = value
        self.save()

    @property
    def accent_color(self) -> Optional[str]:
        """Get the accent color (None = theme default, or currency key)."""
        return self.data["ui"].get("accent_color")

    @accent_color.setter
    def accent_color(self, value: Optional[str]) -> None:
        """Set the accent color and persist."""
        self.data["ui"]["accent_color"] = value
        self.save()

    # ------------------------------------------------------------------
    # System Tray Settings
    # ------------------------------------------------------------------

    @property
    def minimize_to_tray(self) -> bool:
        """Whether to minimize to system tray instead of taskbar."""
        return self.data["ui"].get("minimize_to_tray", True)

    @minimize_to_tray.setter
    def minimize_to_tray(self, value: bool) -> None:
        """Set minimize to tray behavior and persist."""
        self.data["ui"]["minimize_to_tray"] = value
        self.save()

    @property
    def start_minimized(self) -> bool:
        """Whether to start the application minimized to tray."""
        return self.data["ui"].get("start_minimized", False)

    @start_minimized.setter
    def start_minimized(self, value: bool) -> None:
        """Set start minimized behavior and persist."""
        self.data["ui"]["start_minimized"] = value
        self.save()

    @property
    def show_tray_notifications(self) -> bool:
        """Whether to show system tray notifications for price alerts."""
        return self.data["ui"].get("show_tray_notifications", True)

    @show_tray_notifications.setter
    def show_tray_notifications(self, value: bool) -> None:
        """Set tray notifications behavior and persist."""
        self.data["ui"]["show_tray_notifications"] = value
        self.save()

    @property
    def tray_alert_threshold(self) -> float:
        """Chaos value threshold for triggering tray notifications."""
        return self.data["ui"].get("tray_alert_threshold", 50.0)

    @tray_alert_threshold.setter
    def tray_alert_threshold(self, value: float) -> None:
        """Set tray alert threshold and persist."""
        self.data["ui"]["tray_alert_threshold"] = max(0.0, float(value))
        self.save()

    # ------------------------------------------------------------------
    # Accessibility Settings
    # ------------------------------------------------------------------

    @property
    def font_scale(self) -> float:
        """Font scaling factor (0.8 to 1.5)."""
        return self.data.get("accessibility", {}).get("font_scale", 1.0)

    @font_scale.setter
    def font_scale(self, value: float) -> None:
        """Set font scale with guardrails (0.8 to 1.5)."""
        self.data.setdefault("accessibility", {})["font_scale"] = max(0.8, min(1.5, float(value)))
        self.save()

    @property
    def tooltip_delay_ms(self) -> int:
        """Delay before showing tooltips in milliseconds."""
        return self.data.get("accessibility", {}).get("tooltip_delay_ms", 500)

    @tooltip_delay_ms.setter
    def tooltip_delay_ms(self, value: int) -> None:
        """Set tooltip delay with guardrails (100 to 2000 ms)."""
        self.data.setdefault("accessibility", {})["tooltip_delay_ms"] = max(100, min(2000, int(value)))
        self.save()

    @property
    def reduce_animations(self) -> bool:
        """Whether to reduce animations for accessibility."""
        return self.data.get("accessibility", {}).get("reduce_animations", False)

    @reduce_animations.setter
    def reduce_animations(self, value: bool) -> None:
        """Set reduce animations preference."""
        self.data.setdefault("accessibility", {})["reduce_animations"] = bool(value)
        self.save()

    # ------------------------------------------------------------------
    # Performance Settings
    # ------------------------------------------------------------------

    @property
    def rankings_cache_hours(self) -> int:
        """
        How long to cache Top 20 rankings data in hours.

        Guardrails: Min 1 hour, Max 168 hours (1 week).
        Lower values = fresher data but more API calls.
        Default 24 hours balances freshness with API usage.
        """
        return self.data.get("performance", {}).get("rankings_cache_hours", 24)

    @rankings_cache_hours.setter
    def rankings_cache_hours(self, value: int) -> None:
        """Set rankings cache hours with guardrails (1 to 168)."""
        self.data.setdefault("performance", {})["rankings_cache_hours"] = max(1, min(168, int(value)))
        self.save()

    @property
    def price_cache_ttl_seconds(self) -> int:
        """
        Price data cache TTL in seconds.

        Guardrails: Min 300 (5 min), Max 7200 (2 hours).
        GGG recommends conservative API usage to avoid rate limits.
        """
        return self.data.get("performance", {}).get("price_cache_ttl_seconds", 3600)

    @price_cache_ttl_seconds.setter
    def price_cache_ttl_seconds(self, value: int) -> None:
        """Set price cache TTL with guardrails (300 to 7200 seconds)."""
        self.data.setdefault("performance", {})["price_cache_ttl_seconds"] = max(300, min(7200, int(value)))
        self.save()

    @property
    def toast_duration_ms(self) -> int:
        """Toast notification display duration in milliseconds."""
        return self.data.get("performance", {}).get("toast_duration_ms", 3000)

    @toast_duration_ms.setter
    def toast_duration_ms(self, value: int) -> None:
        """Set toast duration with guardrails (1000 to 10000 ms)."""
        self.data.setdefault("performance", {})["toast_duration_ms"] = max(1000, min(10000, int(value)))
        self.save()

    @property
    def history_max_entries(self) -> int:
        """Maximum number of history entries to keep."""
        return self.data.get("performance", {}).get("history_max_entries", 100)

    @history_max_entries.setter
    def history_max_entries(self, value: int) -> None:
        """Set history max entries with guardrails (10 to 500)."""
        self.data.setdefault("performance", {})["history_max_entries"] = max(10, min(500, int(value)))
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

    @property
    def api_rate_limit(self) -> float:
        """
        API rate limit in requests per second.

        Guardrails: Min 0.2 (1 req/5s), Max 1.0 (1 req/s).
        GGG recommends ~0.33 (1 req/3s) to avoid 429 rate limit errors.
        Setting this too high WILL result in temporary bans from the API.
        """
        return self.data["api"].get("rate_limit_per_second", 0.33)

    @api_rate_limit.setter
    def api_rate_limit(self, value: float) -> None:
        """
        Set API rate limit with strict guardrails.

        IMPORTANT: Values outside 0.2-1.0 are clamped to protect
        against violating GGG's rate limiting rules.
        """
        self.data["api"]["rate_limit_per_second"] = max(0.2, min(1.0, float(value)))
        self.save()

    # ------------------------------------------------------------------
    # API Pricing TTLs and Timeouts
    # ------------------------------------------------------------------

    def get_pricing_ttls(self) -> Dict[str, int]:
        """
        Return per-endpoint TTLs (in seconds) for pricing APIs.
        Keys are endpoint identifiers (e.g., "poe_ninja:currencyoverview").

        Guardrails are applied when setting values; here we just expose stored map.
        """
        return self.data.get("api", {}).get("pricing", {}).get("ttls", {}) or {}

    def set_pricing_ttl(self, endpoint_key: str, ttl_seconds: int) -> None:
        """
        Set TTL for a specific pricing endpoint.

        Guardrails: Min 60s, Max 86400s (1 day). Values outside are clamped.
        """
        ttl = max(60, min(86400, int(ttl_seconds)))
        self.data.setdefault("api", {}).setdefault("pricing", {}).setdefault("ttls", {})[
            endpoint_key
        ] = ttl
        self.save()

    def price_cache_ttl_for(self, endpoint_key: str | None, default: Optional[int] = None) -> int:
        """
        Resolve a TTL (seconds) for the given endpoint key.
        Order of precedence:
        1) api.pricing.ttls[endpoint_key] if provided
        2) performance.price_cache_ttl_seconds (global)
        3) api.cache_ttl_seconds (legacy fallback)
        4) provided default or 3600
        """
        if endpoint_key:
            ttl_map = self.get_pricing_ttls()
            if endpoint_key in ttl_map:
                return int(ttl_map[endpoint_key])
        if default is not None:
            base_default = int(default)
        else:
            base_default = 3600
        return int(self.data.get("performance", {}).get("price_cache_ttl_seconds",
                   self.data.get("api", {}).get("cache_ttl_seconds", base_default)))

    def get_api_timeouts(self) -> tuple[int, int]:
        """
        Return (connect, read) timeouts in seconds for API calls.
        """
        t = self.data.get("api", {}).get("timeouts", {}) or {}
        connect = int(t.get("connect", 10))
        read = int(t.get("read", 10))
        # Guardrails (0.5s .. 120s)
        connect = max(1, min(120, connect))
        read = max(1, min(300, read))
        return connect, read

    def set_api_timeouts(self, connect: int | float, read: int | float) -> None:
        """
        Set API timeouts (seconds). Guardrails applied: connect [1..120], read [1..300].
        """
        c = int(max(1, min(120, int(connect))))
        r = int(max(1, min(300, int(read))))
        self.data.setdefault("api", {}).setdefault("timeouts", {})["connect"] = c
        self.data.setdefault("api", {}).setdefault("timeouts", {})["read"] = r
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
    # Stash Settings
    # ------------------------------------------------------------------

    @property
    def poesessid(self) -> str:
        """Get POESESSID for stash API access (decrypted)."""
        encrypted = self.data.get("stash", {}).get("poesessid", "")
        if not encrypted:
            return ""
        return decrypt_credential(encrypted)

    @poesessid.setter
    def poesessid(self, value: str) -> None:
        """Set POESESSID (encrypted) and persist."""
        if "stash" not in self.data:
            self.data["stash"] = {}
        # Encrypt before storing
        self.data["stash"]["poesessid"] = encrypt_credential(value) if value else ""
        self.save()

    @property
    def account_name(self) -> str:
        """Get PoE account name for stash access."""
        return self.data.get("stash", {}).get("account_name", "")

    @account_name.setter
    def account_name(self, value: str) -> None:
        """Set account name and persist."""
        if "stash" not in self.data:
            self.data["stash"] = {}
        self.data["stash"]["account_name"] = value
        self.save()

    @property
    def stash_last_fetch(self) -> Optional[str]:
        """Get last stash fetch timestamp."""
        return self.data.get("stash", {}).get("last_fetch")

    @stash_last_fetch.setter
    def stash_last_fetch(self, value: Optional[str]) -> None:
        """Set last stash fetch timestamp and persist."""
        if "stash" not in self.data:
            self.data["stash"] = {}
        self.data["stash"]["last_fetch"] = value
        self.save()

    def has_stash_credentials(self) -> bool:
        """Check if stash credentials are configured."""
        return bool(self.poesessid and self.account_name)

    # ------------------------------------------------------------------
    # AI Settings
    # ------------------------------------------------------------------

    @property
    def ai_provider(self) -> str:
        """Get the configured AI provider (gemini, claude, openai, or empty)."""
        return self.data.get("ai", {}).get("provider", "")

    @ai_provider.setter
    def ai_provider(self, value: str) -> None:
        """Set the AI provider and persist."""
        valid_providers = ("", "gemini", "claude", "openai", "groq", "ollama")
        if value.lower() not in valid_providers:
            value = ""
        self.data.setdefault("ai", {})["provider"] = value.lower()
        self.save()

    def get_ai_api_key(self, provider: str) -> str:
        """Get the API key for an AI provider (decrypted).

        Args:
            provider: The provider name (gemini, claude, openai).

        Returns:
            The decrypted API key, or empty string if not set.
        """
        key_name = f"{provider.lower()}_api_key"
        encrypted = self.data.get("ai", {}).get(key_name, "")
        if not encrypted:
            return ""
        return decrypt_credential(encrypted)

    def set_ai_api_key(self, provider: str, api_key: str) -> None:
        """Set the API key for an AI provider (encrypted).

        Args:
            provider: The provider name (gemini, claude, openai).
            api_key: The API key to store (will be encrypted).
        """
        key_name = f"{provider.lower()}_api_key"
        self.data.setdefault("ai", {})[key_name] = (
            encrypt_credential(api_key) if api_key else ""
        )
        self.save()

    @property
    def ai_max_tokens(self) -> int:
        """Maximum tokens in AI response (100-2000)."""
        return self.data.get("ai", {}).get("max_response_tokens", 500)

    @ai_max_tokens.setter
    def ai_max_tokens(self, value: int) -> None:
        """Set max AI response tokens with guardrails."""
        self.data.setdefault("ai", {})["max_response_tokens"] = max(100, min(2000, int(value)))
        self.save()

    @property
    def ai_timeout(self) -> int:
        """AI request timeout in seconds (10-300).

        Default is 30s for cloud providers, but Ollama (local) uses 180s
        since large models like deepseek-r1:70b need time to load and generate.
        """
        default = 180 if self.ai_provider == "ollama" else 30
        return self.data.get("ai", {}).get("timeout_seconds", default)

    @ai_timeout.setter
    def ai_timeout(self, value: int) -> None:
        """Set AI timeout with guardrails (10-300s, higher for local models)."""
        self.data.setdefault("ai", {})["timeout_seconds"] = max(10, min(300, int(value)))
        self.save()

    def has_ai_configured(self) -> bool:
        """Check if AI is configured (provider set and has API key or is local)."""
        provider = self.ai_provider
        if not provider:
            return False
        # Ollama is local - no API key needed
        if provider == "ollama":
            return True
        return bool(self.get_ai_api_key(provider))

    @property
    def ollama_host(self) -> str:
        """Get the Ollama server host URL."""
        return self.data.get("ai", {}).get("ollama_host", "http://localhost:11434")

    @ollama_host.setter
    def ollama_host(self, value: str) -> None:
        """Set the Ollama server host URL."""
        self.data.setdefault("ai", {})["ollama_host"] = value.strip() or "http://localhost:11434"
        self.save()

    @property
    def ollama_model(self) -> str:
        """Get the Ollama model to use."""
        return self.data.get("ai", {}).get("ollama_model", "deepseek-r1:14b")

    @ollama_model.setter
    def ollama_model(self, value: str) -> None:
        """Set the Ollama model to use."""
        self.data.setdefault("ai", {})["ollama_model"] = value.strip() or "deepseek-r1:14b"
        self.save()

    @property
    def ai_custom_prompt(self) -> str:
        """Get the custom AI prompt template.

        Returns empty string if using default prompt.
        Supports placeholders: {item_text}, {price_context}, {league}, {build_name}
        """
        return self.data.get("ai", {}).get("custom_prompt", "")

    @ai_custom_prompt.setter
    def ai_custom_prompt(self, value: str) -> None:
        """Set a custom AI prompt template."""
        self.data.setdefault("ai", {})["custom_prompt"] = value.strip()
        self.save()

    @property
    def ai_build_name(self) -> str:
        """Get the player's current build name for AI context.

        Examples: 'Lightning Arrow Deadeye', 'RF Chieftain', 'Tornado Shot MF'
        """
        return self.data.get("ai", {}).get("build_name", "")

    @ai_build_name.setter
    def ai_build_name(self, value: str) -> None:
        """Set the player's build name."""
        self.data.setdefault("ai", {})["build_name"] = value.strip()
        self.save()

    # ------------------------------------------------------------------
    # Loot Tracking
    # ------------------------------------------------------------------

    @property
    def loot_tracking_enabled(self) -> bool:
        """Check if loot tracking auto-start is enabled."""
        return self.data.get("loot_tracking", {}).get("auto_start_enabled", False)

    @loot_tracking_enabled.setter
    def loot_tracking_enabled(self, value: bool) -> None:
        """Enable/disable loot tracking auto-start."""
        self.data.setdefault("loot_tracking", {})["auto_start_enabled"] = bool(value)
        self.save()

    @property
    def loot_client_txt_path(self) -> str:
        """Get the path to Client.txt for zone detection."""
        return self.data.get("loot_tracking", {}).get("client_txt_path", "")

    @loot_client_txt_path.setter
    def loot_client_txt_path(self, value: str) -> None:
        """Set the path to Client.txt."""
        self.data.setdefault("loot_tracking", {})["client_txt_path"] = str(value).strip()
        self.save()

    @property
    def loot_tracked_tabs(self) -> list:
        """Get the list of tabs to track for loot (empty = all tabs)."""
        return self.data.get("loot_tracking", {}).get("tracked_tabs", [])

    @loot_tracked_tabs.setter
    def loot_tracked_tabs(self, value: list) -> None:
        """Set the list of tabs to track."""
        self.data.setdefault("loot_tracking", {})["tracked_tabs"] = list(value)
        self.save()

    @property
    def loot_min_value(self) -> float:
        """Get the minimum chaos value to count as loot."""
        return self.data.get("loot_tracking", {}).get("min_loot_value", 1.0)

    @loot_min_value.setter
    def loot_min_value(self, value: float) -> None:
        """Set the minimum loot value threshold."""
        self.data.setdefault("loot_tracking", {})["min_loot_value"] = max(0.0, float(value))
        self.save()

    @property
    def loot_notify_high_value(self) -> bool:
        """Check if high-value loot notifications are enabled."""
        return self.data.get("loot_tracking", {}).get("notify_high_value", True)

    @loot_notify_high_value.setter
    def loot_notify_high_value(self, value: bool) -> None:
        """Enable/disable high-value loot notifications."""
        self.data.setdefault("loot_tracking", {})["notify_high_value"] = bool(value)
        self.save()

    @property
    def loot_high_value_threshold(self) -> float:
        """Get the chaos value threshold for high-value loot notifications."""
        return self.data.get("loot_tracking", {}).get("high_value_threshold", 50.0)

    @loot_high_value_threshold.setter
    def loot_high_value_threshold(self, value: float) -> None:
        """Set the high-value loot threshold."""
        self.data.setdefault("loot_tracking", {})["high_value_threshold"] = max(0.0, float(value))
        self.save()

    @property
    def loot_poll_interval(self) -> float:
        """Get the Client.txt polling interval in seconds."""
        return self.data.get("loot_tracking", {}).get("poll_interval", 1.0)

    @loot_poll_interval.setter
    def loot_poll_interval(self, value: float) -> None:
        """Set the Client.txt polling interval (min 0.5s, max 5.0s)."""
        clamped = max(0.5, min(5.0, float(value)))
        self.data.setdefault("loot_tracking", {})["poll_interval"] = clamped
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
