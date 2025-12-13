"""
Database utility functions.

Provides reusable helpers for timestamp parsing and timezone normalization
used across database repositories.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_db_timestamp(value: Optional[str]) -> Optional[datetime]:
    """
    Parse a timestamp from SQLite.

    Supports:
    - ISO format strings (e.g., "2024-01-15T12:34:56")
    - "YYYY-MM-DD HH:MM:SS" (SQLite CURRENT_TIMESTAMP format)

    Args:
        value: Timestamp string from database, or None

    Returns:
        Parsed datetime, or None if value is empty or unparseable
    """
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def ensure_utc(dt: datetime) -> datetime:
    """
    Normalize a datetime to UTC.

    If dt is naive (no timezone info), assume it's in the local timezone,
    then convert to UTC.

    Args:
        dt: Datetime to normalize (may be naive or aware)

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        return dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)
