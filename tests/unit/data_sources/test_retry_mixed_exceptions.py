from __future__ import annotations

import pytest
import requests

from data_sources.base_api import retry_with_backoff, RateLimitExceeded


pytestmark = pytest.mark.unit


def test_retry_mixed_exceptions_429_then_request_exception(monkeypatch):
    """
    Ensure the decorator handles a 429 (using retry_after) followed by a generic
    RequestException (using exponential backoff), and that sleep capping via
    pytest default (1.0s) applies when use_env_cap=True.
    """
    # Simulate running under pytest so the default cap (1.0s) engages
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x::y")

    sleeps: list[float] = []

    def fake_sleep(dt: float):
        sleeps.append(dt)

    monkeypatch.setattr("data_sources.base_api.time.sleep", fake_sleep)

    calls = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=2.0, use_env_cap=True)
    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            # First attempt → 429 with retry_after=5 should sleep capped to 1.0
            raise RateLimitExceeded(retry_after=5)
        if calls["n"] == 2:
            # Second attempt → generic request error → backoff of 2.0, capped to 1.0
            raise requests.RequestException("net")
        return "ok"

    result = flaky()
    assert result == "ok"

    # We expect two sleeps, each capped to 1.0s under pytest
    assert sleeps == [pytest.approx(1.0), pytest.approx(1.0)]
    assert calls["n"] == 3


def test_retry_mixed_exceptions_429_req_429_sequence(monkeypatch):
    """
    Extended sequence: 429 -> RequestException -> 429 -> success.
    With use_env_cap=True under pytest, all sleeps should be capped at 1.0s.
    Expect three sleeps of 1.0s each before eventual success.
    """
    # Engage pytest default cap
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x::y")

    sleeps: list[float] = []

    def fake_sleep(dt: float):
        sleeps.append(dt)

    monkeypatch.setattr("data_sources.base_api.time.sleep", fake_sleep)

    calls = {"n": 0}

    @retry_with_backoff(max_retries=4, base_delay=2.0, use_env_cap=True)
    def flaky_longer():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RateLimitExceeded(retry_after=5)
        if calls["n"] == 2:
            raise requests.RequestException("net")
        if calls["n"] == 3:
            raise RateLimitExceeded(retry_after=10)
        return "ok"

    result = flaky_longer()
    assert result == "ok"
    assert sleeps == [pytest.approx(1.0), pytest.approx(1.0), pytest.approx(1.0)]
    assert calls["n"] == 4
