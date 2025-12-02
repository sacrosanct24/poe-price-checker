"""
Base API Client with rate limiting, caching, and error handling.
All API clients (poe.ninja, official trade, etc.) inherit from this.
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Optional, Dict, Any, Callable, Tuple, Union
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import logging
from datetime import datetime, timedelta
from functools import wraps
import threading

from core.constants import CACHE_MAX_SIZE

# Get logger - configuration should be done by application entrypoint, not library modules
logger = logging.getLogger(__name__)

# Module-level toggle for retry logging verbosity
# Values: "minimal" or "detailed"
_RETRY_LOG_VERBOSITY = "minimal"


def set_retry_logging_verbosity(mode: str) -> None:
    """Set retry logging verbosity for API calls.

    Args:
        mode: "minimal" (default) or "detailed"
    """
    global _RETRY_LOG_VERBOSITY
    _RETRY_LOG_VERBOSITY = "detailed" if str(mode).lower() == "detailed" else "minimal"


class RateLimitExceeded(Exception):
    """Raised when API rate limit is hit"""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


class APIError(Exception):
    """Generic API error"""
    pass


class RateLimiter:
    """Thread-safe rate limiter using token bucket algorithm"""

    def __init__(self, calls_per_second: float = 1.0):
        """
        Args:
            calls_per_second: Maximum requests per second (e.g., 0.33 = 1 req per 3 sec)
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        # Use RLock to allow safe re-entrant acquisition within methods that may
        # call other lock-protected helpers (e.g., set() -> stats()).
        self.lock = threading.RLock()

    def wait_if_needed(self):
        """Block if necessary to respect rate limit"""
        with self.lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time

            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                # Add small jitter to avoid thundering herd across threads/processes
                jitter = min(0.25, 0.1 * self.min_interval)
                sleep_time += random.uniform(0, jitter)
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s (with jitter)")
                time.sleep(sleep_time)

            self.last_call_time = time.time()


class ResponseCache:
    """Thread-safe in-memory cache with TTL and LRU eviction."""

    def __init__(self, default_ttl: int = 3600, max_size: int = CACHE_MAX_SIZE):
        """
        Args:
            default_ttl: Time-to-live in seconds (default 1 hour)
            max_size: Maximum cache entries before LRU eviction
        """
        self.cache: OrderedDict[str, tuple[Any, datetime]] = OrderedDict()
        self.default_ttl = default_ttl
        self.max_size = max_size
        # Use RLock for safe re-entrant access when methods call other
        # lock-protected helpers while holding the lock (e.g., set() -> stats()).
        self.lock = threading.RLock()
        # Simple metrics
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired. Moves item to end for LRU ordering."""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if datetime.now() < expiry:
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    logger.debug(f"Cache hit: {key}")
                    self.hits += 1
                    return value
                else:
                    # Expired
                    del self.cache[key]
                    logger.debug(f"Cache expired: {key}")
            # miss (either absent or expired)
            self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store value in cache with expiry. Evicts oldest if at capacity."""
        with self.lock:
            # Evict oldest entries if at capacity
            while len(self.cache) >= self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                logger.debug(f"Cache evicted (LRU): {oldest_key}")
                self.evictions += 1

            ttl = ttl or self.default_ttl
            expiry = datetime.now() + timedelta(seconds=ttl)
            self.cache[key] = (value, expiry)
            logger.debug(
                "Cache set: %s (TTL: %ss, size: %s/%s)",
                key,
                ttl,
                len(self.cache),
                self.max_size,
            )
            self.sets += 1
            # Emit current stats for observability at debug level. Guard to avoid
            # unnecessary work when DEBUG is disabled.
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Cache stats: %s", self.stats())

    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")

    def stats(self) -> Dict[str, int]:
        """Return simple cache metrics for observability."""
        with self.lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "sets": self.sets,
                "evictions": self.evictions,
                "size": len(self.cache),
                "capacity": self.max_size,
            }

    def size(self) -> int:
        """Get number of cached items"""
        with self.lock:
            return len(self.cache)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for exponential backoff retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (doubles each retry)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            def _context_str() -> str:
                # Best-effort extraction of method/endpoint for _make_request
                try:
                    if func.__name__ == "_make_request":
                        method = kwargs.get("method") if "method" in kwargs else (args[1] if len(args) > 1 else "")
                        endpoint = kwargs.get("endpoint") if "endpoint" in kwargs else (args[2] if len(args) > 2 else "")
                        return f"{func.__qualname__} {method} {endpoint}"
                except Exception:
                    pass
                return func.__qualname__

            for attempt in range(max_retries + 1):
                try:
                    if _RETRY_LOG_VERBOSITY == "detailed":
                        logger.debug(f"API call attempt {attempt + 1}/{max_retries + 1}: {_context_str()}")
                    return func(*args, **kwargs)
                except (requests.RequestException, RateLimitExceeded) as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {_context_str()}: {e}")
                        raise

                    if isinstance(e, RateLimitExceeded):
                        delay = e.retry_after
                    else:
                        delay = base_delay * (2 ** attempt)

                    if _RETRY_LOG_VERBOSITY == "detailed":
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {_context_str()}: {e}. Retrying in {delay}s...")
                    else:
                        logger.warning(
                            f"Attempt {attempt + 1} failed ({type(e).__name__}). Retrying...")
                    time.sleep(delay)

            return None  # Should never reach here

        return wrapper

    return decorator


TimeoutType = Union[int, float, Tuple[int, int], Tuple[float, float]]


class BaseAPIClient(ABC):
    """
    Abstract base class for all API clients.
    Provides rate limiting, caching, error handling, and retry logic.
    """

    # Connection pool settings (shared across instances)
    POOL_CONNECTIONS = 10  # Number of connection pools to cache
    POOL_MAXSIZE = 20      # Max connections per pool
    MAX_RETRIES = 3        # Retries for connection errors
    BACKOFF_FACTOR = 0.5   # Exponential backoff multiplier
    RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})  # Server errors to retry

    def __init__(
            self,
            base_url: str,
            rate_limit: float = 1.0,
            cache_ttl: int = 3600,
            user_agent: Optional[str] = None,
            timeout: TimeoutType = 10,
            endpoint_ttls: Optional[Dict[str, int]] = None,
    ):
        """
        Args:
            base_url: Base URL for the API
            rate_limit: Requests per second (e.g., 0.33 = 1 req per 3 sec)
            cache_ttl: Cache time-to-live in seconds
            user_agent: Custom User-Agent header
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.rate_limiter = RateLimiter(calls_per_second=rate_limit)
        self.cache = ResponseCache(default_ttl=cache_ttl)
        self.timeout: TimeoutType = timeout  # may be int or (connect, read)
        # Optional per-endpoint TTLs. Keys are endpoint identifiers or URL paths.
        self.endpoint_ttls: Dict[str, int] = endpoint_ttls or {}

        # Default user agent (APIs like GGG require this)
        self.user_agent = user_agent or "PoE-Price-Checker/2.5 (contact@example.com)"

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        })

        # Configure connection pooling with retry logic
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=self.BACKOFF_FACTOR,
            status_forcelist=self.RETRY_STATUS_CODES,
            allowed_methods=["GET", "POST"],  # Retry these methods
            raise_on_status=False  # Don't raise, let us handle status codes
        )
        adapter = HTTPAdapter(
            pool_connections=self.POOL_CONNECTIONS,
            pool_maxsize=self.POOL_MAXSIZE,
            max_retries=retry_strategy
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

        logger.info(f"Initialized {self.__class__.__name__} - Rate: {rate_limit} req/s, Cache TTL: {cache_ttl}s, Pool: {self.POOL_MAXSIZE}")

    @abstractmethod
    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """
        Generate unique cache key for request.
        Subclasses must implement this.
        """
        pass

    @retry_with_backoff(max_retries=3)
    def _make_request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict] = None,
            data: Optional[Dict] = None,
            use_cache: bool = True,
            ttl_override: Optional[int] = None,
            timeout_override: Optional[TimeoutType] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting and caching.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            data: Request body (for POST/PUT)
            use_cache: Whether to use cache for this request

        Returns:
            JSON response as dict

        Raises:
            RateLimitExceeded: If API returns 429
            APIError: For other API errors
        """
        # Build full URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Check cache for GET requests
        if method.upper() == 'GET' and use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached_response = self.cache.get(cache_key)
            if cached_response is not None:
                return cached_response

        # Rate limit
        self.rate_limiter.wait_if_needed()

        # Make request
        try:
            logger.debug(f"{method} {url} - params: {params}")

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=(timeout_override if timeout_override is not None else self.timeout)
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited! Retry after {retry_after}s")
                raise RateLimitExceeded(retry_after=retry_after)

            # Handle other errors
            if response.status_code >= 400:
                error_msg = f"API error {response.status_code}: {response.text[:200]}"
                logger.error(error_msg)
                raise APIError(error_msg)

            # Parse JSON
            json_data = response.json()

            # Cache successful GET requests
            if method.upper() == 'GET' and use_cache:
                cache_key = self._get_cache_key(endpoint, params)
                # Determine TTL: per-request override, then per-endpoint map, else default
                ttl_to_use: Optional[int]
                if ttl_override is not None:
                    ttl_to_use = int(ttl_override)
                else:
                    ttl_to_use = self.endpoint_ttls.get(endpoint)
                self.cache.set(cache_key, json_data, ttl=ttl_to_use)
                logger.debug(f"Cache stats after set: {self.cache.stats()}")

            logger.info(f"Request successful: {method} {endpoint}")
            return json_data

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Request failed: {e}")

    def get(self, endpoint: str, params: Optional[Dict] = None, use_cache: bool = True,
            ttl_override: Optional[int] = None, timeout_override: Optional[TimeoutType] = None) -> Dict[str, Any]:
        """GET request wrapper"""
        return self._make_request('GET', endpoint, params=params, use_cache=use_cache,
                                  ttl_override=ttl_override, timeout_override=timeout_override)

    def post(self, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None,
             timeout_override: Optional[TimeoutType] = None) -> Dict[str, Any]:
        """POST request wrapper"""
        return self._make_request('POST', endpoint, params=params, data=data, use_cache=False,
                                  timeout_override=timeout_override)

    def clear_cache(self):
        """Clear response cache"""
        self.cache.clear()
        logger.debug(f"Cache stats after clear: {self.cache.stats()}")

    def get_cache_size(self) -> int:
        """Get number of cached responses"""
        return self.cache.size()

    def close(self):
        """Clean up resources"""
        self.session.close()
        logger.info(f"Closed {self.__class__.__name__}")

    def __enter__(self):
        """Context manager entry - returns self for use in 'with' blocks."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session is closed."""
        self.close()
        return False  # Don't suppress exceptions


# Example usage / testing
if __name__ == "__main__":
    # This is just for testing - we'll create real subclasses in other files

    class DummyAPI(BaseAPIClient):
        """Dummy implementation for testing"""

        def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
            param_str = str(sorted(params.items())) if params else ""
            return f"{endpoint}:{param_str}"

    # Test it
    api = DummyAPI(
        base_url="https://httpbin.org",
        rate_limit=2.0,  # 2 requests per second
        cache_ttl=10
    )

    try:
        # First call - hits API
        response1 = api.get("/get", params={"test": "value"})
        print(f"First call: {response1.get('url')}")

        # Second call - hits cache
        response2 = api.get("/get", params={"test": "value"})
        print(f"Second call (cached): {response2.get('url')}")

        print(f"Cache size: {api.get_cache_size()}")

    finally:
        api.close()
