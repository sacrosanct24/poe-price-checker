"""
Unit tests for data_sources.base_api module - Base API client infrastructure.

Tests cover:
- RateLimiter (token bucket algorithm)
- ResponseCache (TTL-based caching)
- retry_with_backoff decorator
- BaseAPIClient (rate limiting, caching, retries)
- Thread safety
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
import requests

from data_sources.base_api import (
    RateLimiter,
    ResponseCache,
    retry_with_backoff,
    BaseAPIClient,
    RateLimitExceeded,
    APIError
)

pytestmark = pytest.mark.unit


# -------------------------
# RateLimiter Tests
# -------------------------

class TestRateLimiter:
    """Test rate limiter functionality."""

    def test_creates_rate_limiter_with_default(self):
        """Should create rate limiter with default rate."""
        limiter = RateLimiter()

        assert limiter.calls_per_second == 1.0
        assert limiter.min_interval == 1.0

    def test_creates_rate_limiter_with_custom_rate(self):
        """Should create rate limiter with custom rate."""
        limiter = RateLimiter(calls_per_second=2.0)

        assert limiter.calls_per_second == 2.0
        assert limiter.min_interval == 0.5

    def test_calculates_min_interval_correctly(self):
        """Should calculate minimum interval from calls_per_second."""
        limiter = RateLimiter(calls_per_second=0.5)  # 1 call per 2 seconds

        assert limiter.min_interval == 2.0

    def test_wait_if_needed_allows_first_call_immediately(self):
        """First call should not wait."""
        limiter = RateLimiter(calls_per_second=1.0)

        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should be nearly instant (< 0.1s)
        assert elapsed < 0.1

    def test_wait_if_needed_enforces_delay_on_rapid_calls(self):
        """Rapid consecutive calls should be rate limited."""
        limiter = RateLimiter(calls_per_second=2.0)  # 0.5s minimum interval

        limiter.wait_if_needed()  # First call

        start = time.time()
        limiter.wait_if_needed()  # Second call (should wait)
        elapsed = time.time() - start

        # Should wait approximately 0.5 seconds
        assert 0.4 < elapsed < 0.7

    def test_wait_if_needed_no_delay_after_interval(self):
        """No delay needed if enough time has passed."""
        limiter = RateLimiter(calls_per_second=10.0)  # 0.1s minimum interval

        limiter.wait_if_needed()
        time.sleep(0.15)  # Wait longer than minimum interval

        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should not wait (< 0.05s tolerance)
        assert elapsed < 0.05

    def test_rate_limiter_thread_safety(self):
        """Rate limiter should be thread-safe."""
        limiter = RateLimiter(calls_per_second=5.0)
        call_times = []

        def make_call():
            limiter.wait_if_needed()
            call_times.append(time.time())

        # Create 10 threads that all try to call at once
        threads = [threading.Thread(target=make_call) for _ in range(10)]

        time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 10 calls should have completed
        assert len(call_times) == 10

        # Calls should be spread out over time (not all instant)
        duration = max(call_times) - min(call_times)
        assert duration > 0.5  # At least some delay enforced


# -------------------------
# ResponseCache Tests
# -------------------------

class TestResponseCache:
    """Test response caching with TTL."""

    def test_creates_cache_with_default_ttl(self):
        """Should create cache with default TTL."""
        cache = ResponseCache()

        assert cache.default_ttl == 3600

    def test_creates_cache_with_custom_ttl(self):
        """Should create cache with custom TTL."""
        cache = ResponseCache(default_ttl=300)

        assert cache.default_ttl == 300

    def test_get_returns_none_for_missing_key(self):
        """Should return None for key that doesn't exist."""
        cache = ResponseCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_set_and_get_value(self):
        """Should store and retrieve value."""
        cache = ResponseCache()

        cache.set("key1", {"data": "value"})
        result = cache.get("key1")

        assert result == {"data": "value"}

    def test_get_returns_value_before_expiry(self):
        """Should return value while not expired."""
        cache = ResponseCache(default_ttl=10)

        cache.set("key1", "value1")
        time.sleep(0.1)  # Wait a bit but not expired
        result = cache.get("key1")

        assert result == "value1"

    def test_get_returns_none_after_expiry(self):
        """Should return None for expired value."""
        cache = ResponseCache(default_ttl=1)

        cache.set("key1", "value1", ttl=1)
        time.sleep(1.2)  # Wait for expiration
        result = cache.get("key1")

        assert result is None

    def test_set_with_custom_ttl(self):
        """Should accept custom TTL for individual keys."""
        cache = ResponseCache(default_ttl=3600)

        cache.set("key1", "value1", ttl=1)  # 1 second TTL
        time.sleep(1.2)

        assert cache.get("key1") is None

    def test_clear_removes_all_cached_items(self):
        """Should clear entire cache."""
        cache = ResponseCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
        assert cache.size() == 0

    def test_size_returns_number_of_cached_items(self):
        """Should return correct cache size."""
        cache = ResponseCache()

        assert cache.size() == 0

        cache.set("key1", "value1")
        assert cache.size() == 1

        cache.set("key2", "value2")
        assert cache.size() == 2

        cache.get("key1")  # Access doesn't change size
        assert cache.size() == 2

    def test_expired_items_removed_on_get(self):
        """Expired items should be removed when accessed."""
        cache = ResponseCache(default_ttl=1)

        cache.set("key1", "value1", ttl=1)
        time.sleep(1.2)

        # Access expired key
        result = cache.get("key1")
        assert result is None

        # Size should reflect removal
        assert cache.size() == 0

    def test_cache_thread_safety(self):
        """Cache should be thread-safe."""
        cache = ResponseCache()
        results = []

        def set_value(key, value):
            cache.set(key, value)

        def get_value(key):
            result = cache.get(key)
            results.append(result)

        # Multiple threads setting and getting
        threads = []
        for i in range(10):
            t1 = threading.Thread(target=set_value, args=(f"key{i}", f"value{i}"))
            t2 = threading.Thread(target=get_value, args=(f"key{i}",))
            threads.extend([t1, t2])

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors
        assert len(results) <= 10  # Some gets might be before sets

    def test_creates_cache_with_default_max_size(self):
        """Should create cache with default max size."""
        cache = ResponseCache()

        from core.constants import CACHE_MAX_SIZE
        assert cache.max_size == CACHE_MAX_SIZE

    def test_creates_cache_with_custom_max_size(self):
        """Should create cache with custom max size."""
        cache = ResponseCache(max_size=100)

        assert cache.max_size == 100

    def test_evicts_oldest_when_at_capacity(self):
        """Should evict oldest entries when cache is full."""
        cache = ResponseCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Cache is now full, adding key4 should evict key1
        cache.set("key4", "value4")

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        assert cache.size() == 3

    def test_lru_ordering_on_access(self):
        """Accessing a value should move it to most recently used."""
        cache = ResponseCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1, making it most recently used
        cache.get("key1")

        # Add key4, should evict key2 (oldest) not key1
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_respects_max_size_under_load(self):
        """Cache should never exceed max_size under heavy use."""
        cache = ResponseCache(max_size=10)

        # Add many more items than max_size
        for i in range(100):
            cache.set(f"key{i}", f"value{i}")

        # Size should never exceed max_size
        assert cache.size() <= 10


# -------------------------
# retry_with_backoff Tests
# -------------------------

class TestRetryWithBackoff:
    """Test retry decorator with exponential backoff."""

    def test_decorator_succeeds_on_first_try(self):
        """Should return result on first successful attempt."""
        @retry_with_backoff(max_retries=3)
        def successful_func():
            return "success"

        result = successful_func()

        assert result == "success"

    def test_decorator_retries_on_exception(self):
        """Should retry on RequestException."""
        call_count = []

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def failing_func():
            call_count.append(1)
            if len(call_count) < 3:
                raise requests.RequestException("Temporary failure")
            return "success"

        result = failing_func()

        assert result == "success"
        assert len(call_count) == 3

    def test_decorator_respects_max_retries(self):
        """Should raise exception after max retries."""
        call_count = []

        @retry_with_backoff(max_retries=2, base_delay=0.1)
        def always_failing():
            call_count.append(1)
            raise requests.RequestException("Always fails")

        with pytest.raises(requests.RequestException):
            always_failing()

        assert len(call_count) == 3  # Initial + 2 retries

    def test_decorator_uses_exponential_backoff(self):
        """Should use exponential backoff delay."""
        call_times = []

        @retry_with_backoff(max_retries=3, base_delay=0.2)
        def failing_func():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise requests.RequestException("Retry")
            return "success"

        failing_func()

        # Check delays between attempts
        # Attempt 1: no delay
        # Attempt 2: 0.2s delay
        # Attempt 3: 0.4s delay
        # Attempt 4: 0.8s delay

        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert 0.1 < delay1 < 0.5  # ~0.2s (relaxed for CI variability)

        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert 0.25 < delay2 < 0.7  # ~0.4s (relaxed for CI variability)

    def test_decorator_handles_rate_limit_exceeded(self):
        """Should handle RateLimitExceeded with custom retry_after."""
        call_count = []

        @retry_with_backoff(max_retries=2, base_delay=0.1)
        def rate_limited_func():
            call_count.append(1)
            if len(call_count) == 1:
                raise RateLimitExceeded(retry_after=0.2)
            return "success"

        start = time.time()
        result = rate_limited_func()
        elapsed = time.time() - start

        assert result == "success"
        assert len(call_count) == 2
        # Should have waited ~0.2s for rate limit (relaxed for CI variability)
        assert 0.1 < elapsed < 0.6


# -------------------------
# BaseAPIClient Tests
# -------------------------

class DummyAPIClient(BaseAPIClient):
    """Concrete implementation for testing."""

    def _get_cache_key(self, endpoint: str, params=None):
        param_str = str(sorted(params.items())) if params else ""
        return f"{endpoint}:{param_str}"


class TestBaseAPIClientInitialization:
    """Test BaseAPIClient initialization."""

    def test_creates_client_with_defaults(self):
        """Should create client with default settings."""
        client = DummyAPIClient(base_url="https://api.example.com")

        assert client.base_url == "https://api.example.com"
        assert client.rate_limiter.calls_per_second == 1.0
        assert client.cache.default_ttl == 3600
        assert client.timeout == 10

    def test_creates_client_with_custom_settings(self):
        """Should create client with custom settings."""
        client = DummyAPIClient(
            base_url="https://api.example.com/",  # Trailing slash
            rate_limit=2.0,
            cache_ttl=300,
            timeout=30
        )

        assert client.base_url == "https://api.example.com"  # Stripped
        assert client.rate_limiter.calls_per_second == 2.0
        assert client.cache.default_ttl == 300
        assert client.timeout == 30

    def test_sets_user_agent_header(self):
        """Should set User-Agent header."""
        client = DummyAPIClient(
            base_url="https://api.example.com",
            user_agent="Custom User Agent"
        )

        assert client.session.headers['User-Agent'] == "Custom User Agent"

    def test_uses_default_user_agent(self):
        """Should use default user agent if not provided."""
        client = DummyAPIClient(base_url="https://api.example.com")

        assert "PoE-Price-Checker" in client.session.headers['User-Agent']


# -------------------------
# BaseAPIClient Request Tests
# -------------------------

class TestBaseAPIClientRequests:
    """Test HTTP request functionality."""

    @patch('data_sources.base_api.requests.Session.request')
    def test_make_request_success(self, mock_request):
        """Should make successful GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")
        result = client._make_request('GET', '/endpoint')

        assert result == {"data": "value"}
        mock_request.assert_called_once()

    @patch('data_sources.base_api.requests.Session.request')
    def test_make_request_builds_url_correctly(self, mock_request):
        """Should build URL from base_url and endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")
        client._make_request('GET', '/path/to/resource')

        call_args = mock_request.call_args
        assert call_args[1]['url'] == "https://api.example.com/path/to/resource"

    @patch('data_sources.base_api.requests.Session.request')
    def test_make_request_handles_429_rate_limit(self, mock_request):
        """Should raise RateLimitExceeded on 429."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        with pytest.raises(RateLimitExceeded) as exc_info:
            client._make_request('GET', '/endpoint')

        assert exc_info.value.retry_after == 60

    @patch('data_sources.base_api.requests.Session.request')
    def test_make_request_handles_4xx_errors(self, mock_request):
        """Should raise APIError on 4xx status."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        with pytest.raises(APIError, match="404"):
            client._make_request('GET', '/nonexistent')

    @patch('data_sources.base_api.requests.Session.request')
    def test_make_request_handles_5xx_errors(self, mock_request):
        """Should raise APIError on 5xx status."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        with pytest.raises(APIError, match="500"):
            client._make_request('GET', '/endpoint')

    @patch('data_sources.base_api.requests.Session.request')
    def test_make_request_handles_network_errors(self, mock_request):
        """Should raise APIError on network failures."""
        mock_request.side_effect = requests.ConnectionError("Network error")

        client = DummyAPIClient(base_url="https://api.example.com")

        with pytest.raises(APIError, match="Request failed"):
            client._make_request('GET', '/endpoint')


# -------------------------
# BaseAPIClient Caching Tests
# -------------------------

class TestBaseAPIClientCaching:
    """Test response caching functionality."""

    @patch('data_sources.base_api.requests.Session.request')
    def test_caches_get_requests(self, mock_request):
        """Should cache successful GET requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        # First request
        result1 = client.get('/endpoint')

        # Second request (should use cache)
        result2 = client.get('/endpoint')

        assert result1 == result2
        # Should only make one actual HTTP request
        assert mock_request.call_count == 1

    @patch('data_sources.base_api.requests.Session.request')
    def test_cache_respects_use_cache_flag(self, mock_request):
        """Should bypass cache when use_cache=False."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        # First request
        client.get('/endpoint', use_cache=True)

        # Second request with use_cache=False
        client.get('/endpoint', use_cache=False)

        # Should make two HTTP requests
        assert mock_request.call_count == 2

    @patch('data_sources.base_api.requests.Session.request')
    def test_cache_distinguishes_different_endpoints(self, mock_request):
        """Should cache different endpoints separately."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        client.get('/endpoint1')
        client.get('/endpoint2')

        # Should make two requests (different endpoints)
        assert mock_request.call_count == 2

    @patch('data_sources.base_api.requests.Session.request')
    def test_cache_distinguishes_different_params(self, mock_request):
        """Should cache requests with different params separately."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        client.get('/endpoint', params={"key": "value1"})
        client.get('/endpoint', params={"key": "value2"})

        # Should make two requests (different params)
        assert mock_request.call_count == 2

    def test_clear_cache_removes_all_cached_responses(self):
        """Should clear all cached responses."""
        client = DummyAPIClient(base_url="https://api.example.com")

        client.cache.set("key1", "value1")
        client.cache.set("key2", "value2")

        client.clear_cache()

        assert client.get_cache_size() == 0

    def test_get_cache_size_returns_count(self):
        """Should return number of cached items."""
        client = DummyAPIClient(base_url="https://api.example.com")

        assert client.get_cache_size() == 0

        client.cache.set("key1", "value1")
        assert client.get_cache_size() == 1


# -------------------------
# BaseAPIClient Wrapper Methods Tests
# -------------------------

class TestBaseAPIClientWrappers:
    """Test GET/POST wrapper methods."""

    @patch('data_sources.base_api.requests.Session.request')
    def test_get_wrapper_calls_make_request(self, mock_request):
        """get() should call _make_request with GET."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")
        client.get('/endpoint', params={"key": "value"})

        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'GET'
        assert call_args[1]['params'] == {"key": "value"}

    @patch('data_sources.base_api.requests.Session.request')
    def test_post_wrapper_calls_make_request(self, mock_request):
        """post() should call _make_request with POST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")
        client.post('/endpoint', data={"key": "value"})

        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert call_args[1]['json'] == {"key": "value"}

    @patch('data_sources.base_api.requests.Session.request')
    def test_post_does_not_cache(self, mock_request):
        """POST requests should not be cached."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_request.return_value = mock_response

        client = DummyAPIClient(base_url="https://api.example.com")

        client.post('/endpoint', data={"key": "value"})
        client.post('/endpoint', data={"key": "value"})

        # Should make two requests (POST not cached)
        assert mock_request.call_count == 2


# -------------------------
# BaseAPIClient Cleanup Tests
# -------------------------

class TestBaseAPIClientCleanup:
    """Test resource cleanup."""

    def test_close_closes_session(self):
        """close() should close the requests session."""
        client = DummyAPIClient(base_url="https://api.example.com")
        client.session.close = Mock()

        client.close()

        client.session.close.assert_called_once()

    def test_context_manager_enter_returns_self(self):
        """__enter__ should return the client instance."""
        client = DummyAPIClient(base_url="https://api.example.com")

        result = client.__enter__()

        assert result is client
        client.close()

    def test_context_manager_exit_closes_session(self):
        """__exit__ should close the session."""
        client = DummyAPIClient(base_url="https://api.example.com")
        client.session.close = Mock()

        client.__exit__(None, None, None)

        client.session.close.assert_called_once()

    def test_context_manager_with_statement(self):
        """Client should work with 'with' statement."""
        with DummyAPIClient(base_url="https://api.example.com") as client:
            assert client is not None
            assert isinstance(client, DummyAPIClient)

    def test_context_manager_closes_on_exception(self):
        """Client should close even when exception occurs."""
        client = DummyAPIClient(base_url="https://api.example.com")
        client.session.close = Mock()

        try:
            with client:
                raise ValueError("Test exception")
        except ValueError:
            pass

        client.session.close.assert_called_once()

    def test_context_manager_does_not_suppress_exceptions(self):
        """__exit__ should not suppress exceptions."""
        client = DummyAPIClient(base_url="https://api.example.com")

        with pytest.raises(ValueError, match="Test exception"):
            with client:
                raise ValueError("Test exception")
