from __future__ import annotations

import pytest

import requests

from data_sources.base_api import retry_with_backoff, RateLimitExceeded


pytestmark = pytest.mark.unit


def test_retry_with_backoff_succeeds_after_retries(monkeypatch):
    calls = {"n": 0}
    sleeps: list[float] = []

    def fake_sleep(dt: float):
        sleeps.append(dt)

    monkeypatch.setattr("data_sources.base_api.time.sleep", fake_sleep)

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def sometimes_fails():
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.RequestException("boom")
        return "ok"

    result = sometimes_fails()
    assert result == "ok"
    # Two failures → two sleeps with 1s, 2s (base_delay * 2**attempt)
    assert sleeps == [pytest.approx(1.0), pytest.approx(2.0)]
    assert calls["n"] == 3


def test_retry_with_backoff_obeys_rate_limit_exceeded_retry_after(monkeypatch):
    calls = {"n": 0}
    sleeps: list[float] = []

    def fake_sleep(dt: float):
        sleeps.append(dt)

    monkeypatch.setattr("data_sources.base_api.time.sleep", fake_sleep)

    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def always_rate_limited():
        calls["n"] += 1
        raise RateLimitExceeded(retry_after=7)

    with pytest.raises(RateLimitExceeded):
        always_rate_limited()

    # Should have slept twice with the provided retry_after (7) each time
    assert sleeps == [pytest.approx(7.0), pytest.approx(7.0)]
    assert calls["n"] == 3  # initial + 2 retries


def test_retry_with_backoff_raises_after_max_retries(monkeypatch):
    sleeps: list[float] = []

    def fake_sleep(dt: float):
        sleeps.append(dt)

    monkeypatch.setattr("data_sources.base_api.time.sleep", fake_sleep)

    @retry_with_backoff(max_retries=1, base_delay=0.5)
    def always_fails():
        raise requests.RequestException("nope")

    with pytest.raises(requests.RequestException):
        always_fails()

    # One retry only → single sleep at 0.5s
    assert sleeps == [pytest.approx(0.5)]
