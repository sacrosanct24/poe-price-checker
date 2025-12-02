from datetime import timedelta
import time

from data_sources.base_api import ResponseCache


def test_response_cache_hits_misses_sets_and_evictions():
    cache = ResponseCache(default_ttl=60, max_size=2)

    # Initially empty
    assert cache.size() == 0
    assert cache.stats()["hits"] == 0

    # Set two items
    cache.set("a", 1)
    cache.set("b", 2)
    s = cache.stats()
    assert s["sets"] == 2
    assert cache.size() == 2

    # Get hit
    assert cache.get("a") == 1
    assert cache.stats()["hits"] == 1

    # Insert third to trigger eviction (LRU should evict 'b' or 'a' depending on access order)
    cache.set("c", 3)
    s2 = cache.stats()
    assert s2["evictions"] == 1
    assert cache.size() == 2

    # One of a/b must be missing now; ensure misses increase
    _ = cache.get("b")
    _ = cache.get("a")
    s3 = cache.stats()
    assert s3["misses"] >= 1


def test_response_cache_ttl_expiry():
    cache = ResponseCache(default_ttl=1, max_size=10)
    cache.set("x", 42)
    assert cache.get("x") == 42  # immediate hit
    time.sleep(1.1)
    # After TTL, should be expired and return None and count as a miss
    assert cache.get("x") is None
    s = cache.stats()
    assert s["misses"] >= 1