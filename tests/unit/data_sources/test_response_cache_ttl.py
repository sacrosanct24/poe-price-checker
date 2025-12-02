from __future__ import annotations

import time

import pytest

from data_sources.base_api import ResponseCache


pytestmark = pytest.mark.unit


def test_response_cache_ttl_expiry_and_eviction_behavior():
    cache = ResponseCache(default_ttl=60, max_size=2)

    # Insert two items with short TTLs
    cache.set("a", {"v": 1}, ttl=1)
    cache.set("b", {"v": 2}, ttl=1)

    # Both present initially
    assert cache.get("a") == {"v": 1}
    assert cache.get("b") == {"v": 2}

    # Insert third to force LRU eviction of the least recently used (which is 'a' after the last get moved it)
    # Access 'b' to make 'a' LRU
    _ = cache.get("b")
    cache.set("c", {"v": 3}, ttl=1)

    stats_after_eviction = cache.stats()
    assert stats_after_eviction["evictions"] == 1
    assert cache.size() == 2

    # 'a' should be evicted, 'b' and 'c' remain until TTL expiry
    assert cache.get("a") is None
    assert cache.get("b") == {"v": 2}
    assert cache.get("c") == {"v": 3}

    # Wait for TTL to expire
    time.sleep(1.2)

    # Now b and c should be expired and return None
    assert cache.get("b") is None
    assert cache.get("c") is None

    # Check stats include hits/misses accounting
    stats = cache.stats()
    assert stats["misses"] >= 2  # at least the two expired lookups
    assert stats["hits"] >= 2    # initial hits for a/b
