from __future__ import annotations

import time
from typing import Any, Dict, Optional

import pytest

from data_sources.base_api import BaseAPIClient


pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, status_code: int = 200, json_data: Dict[str, Any] | None = None):
        self.status_code = status_code
        self._json_data = json_data or {"ok": True}
        self.headers: Dict[str, str] = {}

    def json(self) -> Dict[str, Any]:
        return self._json_data


class FakeSession:
    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, params: Optional[Dict[str, Any]] = None,
                json: Optional[Dict[str, Any]] = None, timeout: Any = None) -> FakeResponse:  # type: ignore[override]
        self.calls.append({
            "method": method,
            "url": url,
            "params": params,
            "json": json,
            "timeout": timeout,
        })
        return FakeResponse(200, {"echo": params or {}, "ok": True})


class DummyClient(BaseAPIClient):
    def __init__(self, base_url: str = "https://example.test", cache_ttl: int = 60):
        super().__init__(base_url=base_url, rate_limit=1000.0, cache_ttl=cache_ttl)
        # inject fake session
        self.session = FakeSession()

    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        return f"{endpoint}:{sorted((params or {}).items())}"


def test_per_request_ttl_override_expires_quickly():
    client = DummyClient(cache_ttl=60)
    # First call hits network and caches with ttl_override=1
    data1 = client.get("/x", params={"a": 1}, ttl_override=1)
    assert data1["ok"] is True

    # Second call should hit cache immediately
    data2 = client.get("/x", params={"a": 1})
    assert data2 == data1

    # After >1s, cache entry should expire
    time.sleep(1.1)
    data3 = client.get("/x", params={"a": 1})
    # New response object (cache miss -> network)
    assert data3 == {"echo": {"a": 1}, "ok": True}


def test_endpoint_ttl_map_is_used_when_no_override():
    client = DummyClient(cache_ttl=60)
    client.endpoint_ttls = {"/foo": 1}

    # Cache with endpoint-specific TTL=1
    _ = client.get("/foo", params=None)
    # Ensure cached now
    _ = client.get("/foo", params=None)
    # Wait and ensure expired
    time.sleep(1.1)
    _ = client.get("/foo", params=None)
    # We expect at least two network calls for /foo due to expiry
    calls = [c for c in client.session.calls if c["url"].endswith("/foo")]
    assert len(calls) >= 2

    # For a different endpoint without mapping, should not expire in 1s (default ttl=60)
    _ = client.get("/bar", params=None)
    time.sleep(1.1)
    _ = client.get("/bar", params=None)
    calls_bar = [c for c in client.session.calls if c["url"].endswith("/bar")]
    # Only the first call should have hit the network; second should be cached
    assert len(calls_bar) == 1


def test_timeout_tuple_and_override_propagate_to_requests():
    client = DummyClient()
    # Set global tuple timeout
    client.timeout = (2, 3)
    _ = client.get("/tuple", params=None)
    assert client.session.calls[-1]["timeout"] == (2, 3)

    # Override per request
    _ = client.get("/override", params=None, timeout_override=(5, 6))
    assert client.session.calls[-1]["timeout"] == (5, 6)
