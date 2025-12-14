"""
Default configuration values for PoE Price Checker.

This module contains the default configuration structure and utility functions
for locating the config directory.
"""

from pathlib import Path
from typing import Any, Dict


def get_config_dir() -> Path:
    """
    Get the application config directory.

    Returns:
        Path to the config directory (~/.poe_price_checker/)
    """
    config_dir = Path.home() / ".poe_price_checker"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


# Default configuration structure
# NOTE: This structure is treated as immutable. Always use deep copy
# when initializing from defaults.
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
            # PoE2 uses Exalted Orbs as base currency (not Chaos)
            # divine_exalted_rate: How many Exalts per Divine (~70-100)
            "divine_exalted_rate": 80.0,
            # chaos_exalted_rate: How many Exalts per Chaos (~7)
            "chaos_exalted_rate": 7.0,
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
    "verdict": {
        # Quick Verdict thresholds for keep/vendor decisions
        # Items below vendor_threshold = VENDOR
        # Items above keep_threshold = KEEP
        # Items between = MAYBE
        "vendor_threshold": 2.0,
        "keep_threshold": 15.0,
        # League timing preset: "default", "league_start", "mid_league", "late_league", "ssf"
        "preset": "default",
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
    "alerts": {
        # Whether price alerts are enabled
        "enabled": True,
        # Polling interval for price checks (5-60 minutes)
        "polling_interval_minutes": 15,
        # Default cooldown between alert triggers (minutes)
        "default_cooldown_minutes": 30,
        # Show system tray notifications when alerts trigger
        "show_tray_notifications": True,
        # Show in-app toast notifications when alerts trigger
        "show_toast_notifications": True,
    },
}
