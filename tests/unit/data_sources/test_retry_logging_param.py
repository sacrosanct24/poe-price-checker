from __future__ import annotations

import pytest
import requests
from unittest.mock import MagicMock

from data_sources.base_api import (
    retry_with_backoff,
    set_retry_logging_verbosity,
)
import data_sources.base_api as base_api_mod


pytestmark = pytest.mark.unit


def _make_flaky_func(exc: Exception, result: str = "ok"):
    calls = {"n": 0}

    @retry_with_backoff(max_retries=2, base_delay=2.0, use_env_cap=True)
    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise exc
        return result

    return flaky, calls


def test_retry_logging_is_parameterized_minimal(monkeypatch):
    # Engage test sleep cap and capture sleeps
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x::y")
    sleeps: list[float] = []
    monkeypatch.setattr(base_api_mod.time, "sleep", lambda dt: sleeps.append(dt))

    # Minimal verbosity path
    set_retry_logging_verbosity("minimal")

    # Mock logger.warning to inspect call signature (format string + args)
    mock_warning = MagicMock()
    monkeypatch.setattr(base_api_mod, "logger", MagicMock(warning=mock_warning))

    flaky, calls = _make_flaky_func(requests.RequestException("boom"))
    assert flaky() == "ok"
    assert calls["n"] == 2

    # Ensure parameterized logging: first arg is the format string, not an f-string
    assert mock_warning.call_count >= 1
    fmt, *args = mock_warning.call_args.args
    assert isinstance(fmt, str) and "%s" in fmt
    # We expect attempt number and exception type to be passed separately
    assert len(args) >= 2
    assert args[1] == "RequestException"


def test_retry_logging_is_parameterized_detailed(monkeypatch):
    # Engage test sleep cap and capture sleeps
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x::y")
    sleeps: list[float] = []
    monkeypatch.setattr(base_api_mod.time, "sleep", lambda dt: sleeps.append(dt))

    # Detailed verbosity path
    set_retry_logging_verbosity("detailed")

    mock_warning = MagicMock()
    mock_debug = MagicMock()
    mock_error = MagicMock()
    monkeypatch.setattr(
        base_api_mod,
        "logger",
        MagicMock(warning=mock_warning, debug=mock_debug, error=mock_error),
    )

    flaky, calls = _make_flaky_func(requests.ReadTimeout("rt"))
    assert flaky() == "ok"
    assert calls["n"] == 2

    # debug should be called for attempt 1
    assert mock_debug.call_count >= 1
    dbg_fmt, *dbg_args = mock_debug.call_args.args
    assert isinstance(dbg_fmt, str) and "%s" in dbg_fmt

    # warning should include delay placeholder and be parameterized
    assert mock_warning.call_count >= 1
    wfmt, *wargs = mock_warning.call_args.args
    assert isinstance(wfmt, str) and "%s" in wfmt
    # Ensure delay value was provided as an argument (capped to 1.0 in pytest)
    assert any(abs(float(arg) - 1.0) < 1e-6 for arg in wargs if isinstance(arg, (int, float, str)))
