from __future__ import annotations

import datetime as realdt
import threading
import faulthandler

import pytest

from data_sources.base_api import ResponseCache


pytestmark = pytest.mark.unit


def test_response_cache_churn_two_threads_no_deadlock(monkeypatch):
    """
    Exercise ResponseCache under concurrent get/set churn with TTL expiries
    and LRU evictions. The test runs without real sleeps by freezing the
    datetime used inside ResponseCache and advancing it deterministically.

    Ensures:
      - No deadlocks under contention
      - Size never exceeds capacity
      - Evictions occur when capacity is exceeded
      - Hits and misses are both recorded (> 0)
    """

    # Freeze time for the cache by monkeypatching the datetime used in ResponseCache
    class FrozenDateTime(realdt.datetime):
        current = realdt.datetime(2025, 1, 1, 0, 0, 0)

        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return cls.current.replace(tzinfo=tz)
            return cls.current

    monkeypatch.setattr("data_sources.base_api.datetime", FrozenDateTime, raising=False)

    cache = ResponseCache(default_ttl=5, max_size=8)

    # Worker function performing a mix of sets and gets
    def churn_worker(name: str, ready: threading.Barrier, done_list: list[int]):
        ready.wait()
        for i in range(200):
            # Insert/update a key for this worker with small TTL to force expiry later
            cache.set(f"{name}:{i}", {"v": i}, ttl=2)
            # Access a few recent keys to churn LRU order
            if i >= 2:
                cache.get(f"{name}:{i-1}")
                cache.get(f"{name}:{i-2}")
            # Occasionally cross-access other worker keys to interleave
            if i % 5 == 0 and i > 0:
                cache.get(f"other:{i-1}")

            # Every 25 iterations advance time beyond TTL to trigger expiries
            if i % 25 == 0 and i > 0:
                FrozenDateTime.current += realdt.timedelta(seconds=3)

        done_list.append(1)

    start = threading.Barrier(3)
    done1: list[int] = []
    done2: list[int] = []

    # Run in separate threads and guard with timeout on join to detect deadlocks
    t1 = threading.Thread(target=churn_worker, args=("w1", start, done1), daemon=True)
    t2 = threading.Thread(target=churn_worker, args=("other", start, done2), daemon=True)
    t1.start()
    t2.start()

    # Release both workers
    start.wait()

    # Wait for completion with a hard timeout; dump stacks if stuck
    t1.join(timeout=10)
    t2.join(timeout=10)
    if t1.is_alive() or t2.is_alive():
        faulthandler.dump_traceback()
        pytest.fail("ResponseCache churn workers timed out (10s)")

    # Basic invariants
    st = cache.stats()
    assert cache.size() <= cache.max_size
    # Expect some evictions due to capacity 8 over 400 insertions
    assert st["evictions"] > 0
    # Expect both hits and misses recorded
    assert st["hits"] > 0
    assert st["misses"] > 0
    # Ratios are within bounds
    assert 0.0 <= st["hit_ratio"] <= 1.0
    assert 0.0 <= st["miss_ratio"] <= 1.0
    assert 0.0 <= st["fill_ratio"] <= 1.0
