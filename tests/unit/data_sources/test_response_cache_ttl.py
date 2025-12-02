from __future__ import annotations

import datetime as realdt
import threading
import queue
import faulthandler

import pytest

from data_sources.base_api import ResponseCache


pytestmark = pytest.mark.unit


def test_response_cache_ttl_expiry_and_eviction_behavior(monkeypatch):
    # Freeze time for the cache by monkeypatching the datetime used in ResponseCache
    class FrozenDateTime(realdt.datetime):
        current = realdt.datetime(2025, 1, 1, 0, 0, 0)

        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                # naive but sufficient for tests
                return cls.current.replace(tzinfo=tz)
            return cls.current

    # Patch only the datetime symbol used inside data_sources.base_api
    monkeypatch.setattr("data_sources.base_api.datetime", FrozenDateTime, raising=False)

    # Execute the body in a worker thread so we can enforce a timeout even if an internal lock deadlocks
    result_q: queue.Queue[Exception | None] = queue.Queue()

    def worker():
        try:
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

            # Advance frozen time beyond the TTL to trigger expiry without real sleeping
            FrozenDateTime.current += realdt.timedelta(seconds=2)

            # Now b and c should be expired and return None
            assert cache.get("b") is None
            assert cache.get("c") is None

            # Check stats include hits/misses accounting
            stats = cache.stats()
            assert stats["misses"] >= 2  # at least the two expired lookups
            assert stats["hits"] >= 2    # initial hits for a/b
            result_q.put(None)
        except Exception as e:  # pragma: no cover - only on failures
            result_q.put(e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=10)
    if t.is_alive():
        # Dump stacks to aid diagnosis and fail deterministically
        faulthandler.dump_traceback()
        pytest.fail("test_response_cache_ttl_expiry_and_eviction_behavior timed out (10s)")
    # Propagate any exception raised in the worker
    err = result_q.get()
    if err is not None:
        raise err
