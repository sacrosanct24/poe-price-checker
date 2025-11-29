"""
Base API Client with rate limiting, caching, and error handling.
All API clients (poe.ninja, official trade, etc.) inherit from this.
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Optional, Dict, Any, Callable
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
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Block if necessary to respect rate limit"""
        with self.lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time

            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
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
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired. Moves item to end for LRU ordering."""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if datetime.now() < expiry:
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    logger.debug(f"Cache hit: {key}")
                    return value
                else:
                    # Expired
                    del self.cache[key]
                    logger.debug(f"Cache expired: {key}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store value in cache with expiry. Evicts oldest if at capacity."""
        with self.lock:
            # Evict oldest entries if at capacity
            while len(self.cache) >= self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                logger.debug(f"Cache evicted (LRU): {oldest_key}")

            ttl = ttl or self.default_ttl
            expiry = datetime.now() + timedelta(seconds=ttl)
            self.cache[key] = (value, expiry)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s, size: {len(self.cache)}/{self.max_size})")

    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")

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
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, RateLimitExceeded) as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}")
                        raise

                    if isinstance(e, RateLimitExceeded):
                        delay = e.retry_after
                    else:
                        delay = base_delay * (2 ** attempt)

                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)

            return None  # Should never reach here

        return wrapper

    return decorator


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
            timeout: int = 10
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
        self.timeout = timeout

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
            use_cache: bool = True
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
                timeout=self.timeout
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
                self.cache.set(cache_key, json_data)

            logger.info(f"Request successful: {method} {endpoint}")
            return json_data

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Request failed: {e}")

    def get(self, endpoint: str, params: Optional[Dict] = None, use_cache: bool = True) -> Dict[str, Any]:
        """GET request wrapper"""
        return self._make_request('GET', endpoint, params=params, use_cache=use_cache)

    def post(self, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request wrapper"""
        return self._make_request('POST', endpoint, params=params, data=data, use_cache=False)

    def clear_cache(self):
        """Clear response cache"""
        self.cache.clear()

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
