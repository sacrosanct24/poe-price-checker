"""
Application-wide constants for the PoE Price Checker.

Centralizes magic numbers and configuration values to improve maintainability.
"""

# =============================================================================
# Network Timeouts (seconds)
# =============================================================================

# Default timeout for API requests
API_TIMEOUT_DEFAULT = 10

# Extended timeout for large data fetches (e.g., RePoE data)
API_TIMEOUT_EXTENDED = 60

# Timeout for thread/worker joins
THREAD_JOIN_TIMEOUT = 2.0


# =============================================================================
# Rate Limiting
# =============================================================================

# Default rate limit for API requests (requests per second)
RATE_LIMIT_DEFAULT = 1.0

# Conservative rate limit for official PoE API
RATE_LIMIT_POE_API = 0.33  # ~1 request per 3 seconds

# Rate limit for poe.ninja (more lenient)
RATE_LIMIT_POE_NINJA = 2.0

# Default retry delay (seconds)
RETRY_DELAY_DEFAULT = 60


# =============================================================================
# Caching
# =============================================================================

# Default cache TTL (seconds) - 1 hour
CACHE_TTL_DEFAULT = 3600

# Short cache TTL for frequently changing data - 5 minutes
CACHE_TTL_SHORT = 300

# Long cache TTL for stable data - 24 hours
CACHE_TTL_LONG = 86400


# =============================================================================
# Item Level Thresholds for Mod Tiers
# =============================================================================

# Top tier item level requirements
ILVL_T1 = 84  # Highest tier mods
ILVL_T2 = 75
ILVL_T3 = 68
ILVL_T4 = 60
ILVL_T5 = 54
ILVL_T6 = 45

# Minimum item level for endgame crafting
ILVL_ENDGAME_MIN = 75


# =============================================================================
# Price Thresholds
# =============================================================================

# Minimum chaos value to show item (default filter)
PRICE_MIN_DISPLAY = 1.0

# Value threshold for "valuable" items
PRICE_VALUABLE_THRESHOLD = 10.0

# Undercut factor for suggested pricing (90% of market price)
UNDERCUT_FACTOR_DEFAULT = 0.9


# =============================================================================
# Windows API Constants
# =============================================================================

# ShowWindow commands
SW_RESTORE = 9
SW_SHOW = 5
SW_HIDE = 0


# =============================================================================
# Polling Intervals (seconds)
# =============================================================================

# Clipboard polling interval
CLIPBOARD_POLL_INTERVAL = 0.5

# Price update check interval - 15 minutes
PRICE_UPDATE_INTERVAL = 900


# =============================================================================
# Retry Configuration
# =============================================================================

# Maximum retry attempts for API calls
MAX_RETRIES = 3

# Base delay for exponential backoff (seconds)
BACKOFF_BASE_DELAY = 1.0

# Maximum delay cap for backoff (seconds)
BACKOFF_MAX_DELAY = 60.0
