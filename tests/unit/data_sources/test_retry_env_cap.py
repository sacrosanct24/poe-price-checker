from __future__ import annotations

import pytest
import requests

from data_sources.base_api import retry_with_backoff


pytestmark = pytest.mark.unit


def test_retry_with_backoff_caps_sleep_via_env(monkeypatch):
    # Ensure cap is read from env var
    monkeypatch.setenv("RETRY_MAX_SLEEP", "0.3")

    sleeps: list[float] = []

    def fake_sleep(dt: float):
        sleeps.append(dt)

    monkeypatch.setattr("data_sources.base_api.time.sleep", fake_sleep)

    calls = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=1.0, use_env_cap=True)
    def always_fails():
        calls["n"] += 1
        raise requests.RequestException("boom")

    with pytest.raises(requests.RequestException):
        always_fails()

    # Would have been [1.0, 2.0, 4.0] without cap. With cap=0.3, all sleeps are 0.3
    assert sleeps == [pytest.approx(0.3), pytest.approx(0.3), pytest.approx(0.3)]
    assert calls["n"] == 4  # initial + 3 retries


def test_retry_with_backoff_caps_sleep_under_pytest(monkeypatch):
    # No env var set; simulate running under pytest by setting PYTEST_CURRENT_TEST
    monkeypatch.delenv("RETRY_MAX_SLEEP", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "some::test")

    sleeps: list[float] = []

    def fake_sleep(dt: float):
        sleeps.append(dt)

    monkeypatch.setattr("data_sources.base_api.time.sleep", fake_sleep)

    calls = {"n": 0}

    @retry_with_backoff(max_retries=2, base_delay=5.0, use_env_cap=True)
    def sometimes_fails():
        calls["n"] += 1
        # Fail first two times, then succeed
        if calls["n"] < 3:
            raise requests.RequestException("nope")
        return "ok"

    result = sometimes_fails()
    assert result == "ok"

    # Default cap under pytest is 1.0s; would have been [5.0, 10.0] otherwise
    assert sleeps == [pytest.approx(1.0), pytest.approx(1.0)]
    assert calls["n"] == 3
