"""
Tests for core/database/utils.py

Tests database utility functions for timestamp parsing and timezone handling.
"""
import pytest
from datetime import datetime, timezone

from core.database.utils import parse_db_timestamp, ensure_utc

pytestmark = pytest.mark.unit


class TestParseDbTimestamp:
    """Tests for parse_db_timestamp function."""

    def test_returns_none_for_none(self):
        """Should return None for None input."""
        assert parse_db_timestamp(None) is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        assert parse_db_timestamp("") is None

    def test_parses_iso_format(self):
        """Should parse ISO format timestamps."""
        result = parse_db_timestamp("2024-01-15T12:34:56")
        assert result == datetime(2024, 1, 15, 12, 34, 56)

    def test_parses_sqlite_format(self):
        """Should parse SQLite CURRENT_TIMESTAMP format."""
        result = parse_db_timestamp("2024-01-15 12:34:56")
        assert result == datetime(2024, 1, 15, 12, 34, 56)

    def test_returns_none_for_invalid_format(self):
        """Should return None for unparseable format."""
        result = parse_db_timestamp("not a timestamp")
        assert result is None

    def test_returns_none_for_partial_format(self):
        """Should return None for partial/invalid timestamps."""
        result = parse_db_timestamp("2024-01")
        assert result is None


class TestEnsureUtc:
    """Tests for ensure_utc function."""

    def test_converts_naive_datetime_to_utc(self):
        """Should convert naive datetime to UTC."""
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)
        result = ensure_utc(naive_dt)

        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_converts_aware_datetime_to_utc(self):
        """Should convert aware datetime to UTC."""
        # Create aware datetime in a different timezone
        from datetime import timedelta
        eastern = timezone(timedelta(hours=-5))
        aware_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=eastern)

        result = ensure_utc(aware_dt)

        assert result.tzinfo == timezone.utc
        # 12:00 EST = 17:00 UTC
        assert result.hour == 17

    def test_preserves_utc_datetime(self):
        """Should preserve datetime already in UTC."""
        utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(utc_dt)

        assert result == utc_dt
        assert result.tzinfo == timezone.utc
