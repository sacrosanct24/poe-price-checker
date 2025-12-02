from __future__ import annotations

import threading
import pytest

from data_sources.base_api import RateLimiter


pytestmark = pytest.mark.unit


class ThreadSafeFakeTime:
    def __init__(self, start: float = 0.0):
        self._now = start
        self._sleeps: list[float] = []
        self._lock = threading.Lock()

    def time(self) -> float:
        with self._lock:
            return self._now

    def sleep(self, dt: float):
        # Record and advance atomically; no real delay
        with self._lock:
            self._sleeps.append(dt)
            self._now += dt

    @property
    def sleeps(self) -> list[float]:
        with self._lock:
            return list(self._sleeps)


def test_rate_limiter_two_threads_spacing(monkeypatch):
    ft = ThreadSafeFakeTime(start=100.0)
    # Deterministic jitter
    monkeypatch.setattr("data_sources.base_api.time.time", ft.time)
    monkeypatch.setattr("data_sources.base_api.time.sleep", ft.sleep)
    monkeypatch.setattr("data_sources.base_api.random.uniform", lambda a, b: 0.0)

    rl = RateLimiter(calls_per_second=2.0)  # min_interval = 0.5s
    # Ensure first call from either thread does not sleep
    rl.last_call_time = ft.time() - 10.0

    # Start two threads that each make two calls
    start_barrier = threading.Barrier(3)  # 2 workers + main to release

    def worker(calls_done: list[int]):
        start_barrier.wait()
        rl.wait_if_needed()
        rl.wait_if_needed()
        calls_done.append(1)

    done1: list[int] = []
    done2: list[int] = []

    t1 = threading.Thread(target=worker, args=(done1,), daemon=True)
    t2 = threading.Thread(target=worker, args=(done2,), daemon=True)
    t1.start()
    t2.start()

    # Release both workers
    start_barrier.wait()

    t1.join(timeout=2)
    t2.join(timeout=2)

    assert done1 and done2, "workers did not finish"

    sleeps = ft.sleeps
    # Across 4 total calls, first should be free, the remaining 3 should sleep 0.5s each
    assert len(sleeps) == 3
    for s in sleeps:
        assert s == pytest.approx(0.5, rel=1e-6)
