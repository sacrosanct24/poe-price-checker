from __future__ import annotations

import pytest

from data_sources.base_api import RateLimiter


pytestmark = pytest.mark.unit


class FakeTime:
    def __init__(self, start: float = 0.0):
        self.now = start
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, dt: float):
        self.sleeps.append(dt)
        self.now += dt


def test_rate_limiter_metrics_increment_on_sleep(monkeypatch):
    ft = FakeTime(start=100.0)
    # Deterministic jitter: none
    monkeypatch.setattr("data_sources.base_api.time.time", ft.time)
    monkeypatch.setattr("data_sources.base_api.time.sleep", ft.sleep)
    monkeypatch.setattr("data_sources.base_api.random.uniform", lambda a, b: 0.0)

    rl = RateLimiter(calls_per_second=2.0)  # min_interval = 0.5s

    # First call far in the past: no sleep
    rl.last_call_time = ft.time() - 10.0
    rl.wait_if_needed()

    m1 = rl.metrics()
    assert m1["total_sleeps"] == 0
    assert m1["total_slept_seconds"] == pytest.approx(0.0)
    assert m1["last_call_time"] == pytest.approx(ft.time(), rel=0, abs=1e-9)

    # Immediate second call: should sleep exactly 0.5s
    rl.wait_if_needed()

    m2 = rl.metrics()
    assert m2["total_sleeps"] == 1
    assert m2["total_slept_seconds"] == pytest.approx(0.5, rel=1e-6)
    assert m2["min_interval"] == pytest.approx(0.5)
    assert m2["calls_per_second"] == pytest.approx(2.0)
