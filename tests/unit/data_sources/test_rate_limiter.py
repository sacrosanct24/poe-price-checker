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
        # record and advance
        self.sleeps.append(dt)
        self.now += dt


def test_rate_limiter_no_wait_when_interval_passed(monkeypatch):
    ft = FakeTime(start=100.0)
    # Deterministic jitter
    monkeypatch.setattr("data_sources.base_api.time.time", ft.time)
    monkeypatch.setattr("data_sources.base_api.time.sleep", ft.sleep)
    monkeypatch.setattr("data_sources.base_api.random.uniform", lambda a, b: 0.0)

    rl = RateLimiter(calls_per_second=2.0)  # min_interval = 0.5
    # Pretend last call was long ago
    rl.last_call_time = ft.time() - 10.0

    rl.wait_if_needed()

    # No sleep expected
    assert ft.sleeps == []
    # last_call_time updated to current time
    assert rl.last_call_time == pytest.approx(ft.time(), rel=0, abs=1e-9)


def test_rate_limiter_waits_when_called_too_soon(monkeypatch):
    ft = FakeTime(start=200.0)
    monkeypatch.setattr("data_sources.base_api.time.time", ft.time)
    monkeypatch.setattr("data_sources.base_api.time.sleep", ft.sleep)
    # No jitter to make assertion exact
    monkeypatch.setattr("data_sources.base_api.random.uniform", lambda a, b: 0.0)

    rl = RateLimiter(calls_per_second=4.0)  # min_interval = 0.25
    # Simulate a call just 0.05s ago
    rl.last_call_time = ft.time() - 0.05

    rl.wait_if_needed()

    # Should have slept for at least 0.20s (0.25 - 0.05), exactly due to zero jitter
    assert len(ft.sleeps) == 1
    assert ft.sleeps[0] == pytest.approx(0.20, rel=1e-6)
    # last_call_time updated to time after sleep
    assert rl.last_call_time == pytest.approx(ft.time(), rel=0, abs=1e-9)


def test_rate_limiter_back_to_back_calls_trigger_second_sleep(monkeypatch):
    ft = FakeTime(start=300.0)
    monkeypatch.setattr("data_sources.base_api.time.time", ft.time)
    monkeypatch.setattr("data_sources.base_api.time.sleep", ft.sleep)
    monkeypatch.setattr("data_sources.base_api.random.uniform", lambda a, b: 0.0)

    rl = RateLimiter(calls_per_second=5.0)  # min_interval = 0.2

    # First call — no sleep (last_call_time = 0 initially)
    rl.wait_if_needed()
    assert ft.sleeps == []

    # Immediate second call — should sleep full 0.2s
    rl.wait_if_needed()
    assert ft.sleeps == [pytest.approx(0.2, rel=1e-6)]
