"""
Application-wide constants for the PoE Price Checker.

Centralizes magic numbers and configuration values to improve maintainability.
"""

# =============================================================================
# Network Timeouts (seconds)
# =============================================================================

# Default timeout for API requests (general use)
API_TIMEOUT_DEFAULT = 10

# Standard timeout for most external API calls
API_TIMEOUT_STANDARD = 15

# Extended timeout for stash/OAuth operations
API_TIMEOUT_STASH = 30

# Extended timeout for large data fetches (e.g., RePoE data, skill trees)
API_TIMEOUT_EXTENDED = 60

# Local AI inference timeout (Ollama)
API_TIMEOUT_LOCAL_AI = 120

# Quick health check timeout
API_TIMEOUT_HEALTH_CHECK = 5

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

# Maximum cache entries to prevent unbounded memory growth
CACHE_MAX_SIZE = 1000


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


# =============================================================================
# Session Management
# =============================================================================

# Maximum number of concurrent sessions
MAX_SESSIONS = 10

# Default session name prefix
SESSION_NAME_PREFIX = "Session"


# =============================================================================
# UI Configuration
# =============================================================================

# Toast notification display duration (milliseconds)
TOAST_DURATION_MS = 3000

# Search input debounce delay (milliseconds)
DEBOUNCE_DELAY_MS = 300

# Tooltip show delay (milliseconds)
TOOLTIP_DELAY_MS = 500

# History deque maximum size
HISTORY_MAX_ENTRIES = 100


# =============================================================================
# Connection Pool Configuration
# =============================================================================

# Number of connection pools to cache
POOL_CONNECTIONS = 10

# Maximum connections per pool
POOL_MAXSIZE = 20

# Retry status codes for connection errors
RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})


# =============================================================================
# Loot Tracking
# =============================================================================

# Client.txt polling interval (seconds)
CLIENT_TXT_POLL_INTERVAL = 1.0

# Stash snapshot cooldown to prevent spam (seconds)
STASH_SNAPSHOT_COOLDOWN = 5.0

# Default high-value loot notification threshold (chaos)
LOOT_HIGH_VALUE_THRESHOLD = 50.0

# Session auto-end timeout after inactivity (minutes)
SESSION_IDLE_TIMEOUT_MINUTES = 30

# Maximum drops to keep in memory per session before DB flush
LOOT_MAX_DROPS_IN_MEMORY = 500

# Minimum value to track as loot (chaos)
LOOT_MIN_VALUE = 1.0


# =============================================================================
# Meta-Based Affix Weighting
# =============================================================================

# Cache staleness threshold (days)
# Weights older than this are considered stale and log a warning
# Stale data is still used if no fresher data available
META_CACHE_EXPIRY_DAYS = 7

# Threshold for applying meta popularity bonus
# If calculated meta_weight >= threshold, apply bonus to affix weight
# meta_weight = 5.0 + (popularity_percent * 0.1)
# So 50% popularity => meta_weight = 10.0 (meets threshold)
META_BONUS_THRESHOLD = 10

# Weight boost amount for meta-popular affixes
# Added to base weight when affix meets META_BONUS_THRESHOLD
# Final weight is capped at max affix weight (10)
META_BONUS_AMOUNT = 2

# Maximum affix weight (weights are capped to prevent score overflow)
MAX_AFFIX_WEIGHT = 10
