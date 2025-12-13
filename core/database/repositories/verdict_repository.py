"""
Verdict statistics repository for price check verdict tracking.

Handles database operations for:
- Verdict statistics (keep/vendor/maybe counts and values)
- Session-based statistics tracking
- Aggregated summaries
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.database.repositories.base_repository import BaseRepository


class VerdictRepository(BaseRepository):
    """Repository for verdict statistics database operations."""

    def save_verdict_statistics(
        self,
        league: str,
        game_version: str,
        session_date: str,
        stats: Dict[str, Any],
    ) -> int:
        """
        Save or update verdict statistics for a session.

        Uses UPSERT to update existing stats for the same league/date.

        Args:
            league: League name (e.g., "Settlers").
            game_version: "poe1" or "poe2".
            session_date: Date string (YYYY-MM-DD format).
            stats: Dict containing verdict statistics fields.

        Returns:
            Row ID of the upserted record.
        """
        cursor = self._execute(
            """
            INSERT INTO verdict_statistics (
                league, game_version, session_date,
                keep_count, vendor_count, maybe_count,
                keep_value, vendor_value, maybe_value,
                items_with_meta_bonus, total_meta_bonus,
                high_confidence_count, medium_confidence_count, low_confidence_count,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(league, game_version, session_date) DO UPDATE SET
                keep_count = excluded.keep_count,
                vendor_count = excluded.vendor_count,
                maybe_count = excluded.maybe_count,
                keep_value = excluded.keep_value,
                vendor_value = excluded.vendor_value,
                maybe_value = excluded.maybe_value,
                items_with_meta_bonus = excluded.items_with_meta_bonus,
                total_meta_bonus = excluded.total_meta_bonus,
                high_confidence_count = excluded.high_confidence_count,
                medium_confidence_count = excluded.medium_confidence_count,
                low_confidence_count = excluded.low_confidence_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                league,
                game_version,
                session_date,
                stats.get("keep_count", 0),
                stats.get("vendor_count", 0),
                stats.get("maybe_count", 0),
                stats.get("keep_value", 0.0),
                stats.get("vendor_value", 0.0),
                stats.get("maybe_value", 0.0),
                stats.get("items_with_meta_bonus", 0),
                stats.get("total_meta_bonus", 0.0),
                stats.get("high_confidence_count", 0),
                stats.get("medium_confidence_count", 0),
                stats.get("low_confidence_count", 0),
            ),
        )
        return cursor.lastrowid or 0

    def get_verdict_statistics(
        self,
        league: str,
        game_version: str = "poe1",
        session_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get verdict statistics for a specific session.

        Args:
            league: League name.
            game_version: "poe1" or "poe2".
            session_date: Date string (YYYY-MM-DD). If None, gets today's.

        Returns:
            Dict with statistics or None if not found.
        """
        if session_date is None:
            session_date = datetime.now().strftime("%Y-%m-%d")

        row = self._execute_fetchone(
            """
            SELECT * FROM verdict_statistics
            WHERE league = ? AND game_version = ? AND session_date = ?
            """,
            (league, game_version, session_date),
        )
        if row:
            return dict(row)
        return None

    def get_verdict_statistics_history(
        self,
        league: str,
        game_version: str = "poe1",
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get verdict statistics history for a league.

        Args:
            league: League name.
            game_version: "poe1" or "poe2".
            days: Number of days of history to retrieve.

        Returns:
            List of statistics records, newest first.
        """
        rows = self._execute_fetchall(
            """
            SELECT * FROM verdict_statistics
            WHERE league = ? AND game_version = ?
              AND session_date >= DATE('now', ?)
            ORDER BY session_date DESC
            """,
            (league, game_version, f"-{days} days"),
        )
        return [dict(row) for row in rows]

    def get_verdict_statistics_summary(
        self,
        league: str,
        game_version: str = "poe1",
    ) -> Dict[str, Any]:
        """
        Get aggregated verdict statistics for a league.

        Args:
            league: League name.
            game_version: "poe1" or "poe2".

        Returns:
            Dict with total counts and values across all sessions.
        """
        row = self._execute_fetchone(
            """
            SELECT
                COUNT(*) as session_count,
                COALESCE(SUM(keep_count), 0) as total_keep,
                COALESCE(SUM(vendor_count), 0) as total_vendor,
                COALESCE(SUM(maybe_count), 0) as total_maybe,
                COALESCE(SUM(keep_value), 0.0) as total_keep_value,
                COALESCE(SUM(vendor_value), 0.0) as total_vendor_value,
                COALESCE(SUM(maybe_value), 0.0) as total_maybe_value,
                COALESCE(SUM(items_with_meta_bonus), 0) as total_items_with_meta,
                COALESCE(SUM(total_meta_bonus), 0.0) as total_meta_bonus,
                COALESCE(SUM(high_confidence_count), 0) as total_high_confidence,
                COALESCE(SUM(medium_confidence_count), 0) as total_medium_confidence,
                COALESCE(SUM(low_confidence_count), 0) as total_low_confidence,
                MIN(session_date) as first_date,
                MAX(session_date) as last_date
            FROM verdict_statistics
            WHERE league = ? AND game_version = ?
            """,
            (league, game_version),
        )
        if row:
            return {
                "session_count": row["session_count"] or 0,
                "total_keep": row["total_keep"] or 0,
                "total_vendor": row["total_vendor"] or 0,
                "total_maybe": row["total_maybe"] or 0,
                "total_keep_value": row["total_keep_value"] or 0.0,
                "total_vendor_value": row["total_vendor_value"] or 0.0,
                "total_maybe_value": row["total_maybe_value"] or 0.0,
                "total_items_with_meta": row["total_items_with_meta"] or 0,
                "total_meta_bonus": row["total_meta_bonus"] or 0.0,
                "total_high_confidence": row["total_high_confidence"] or 0,
                "total_medium_confidence": row["total_medium_confidence"] or 0,
                "total_low_confidence": row["total_low_confidence"] or 0,
                "first_date": row["first_date"],
                "last_date": row["last_date"],
            }
        return {
            "session_count": 0,
            "total_keep": 0,
            "total_vendor": 0,
            "total_maybe": 0,
            "total_keep_value": 0.0,
            "total_vendor_value": 0.0,
            "total_maybe_value": 0.0,
            "total_items_with_meta": 0,
            "total_meta_bonus": 0.0,
            "total_high_confidence": 0,
            "total_medium_confidence": 0,
            "total_low_confidence": 0,
            "first_date": None,
            "last_date": None,
        }

    def clear_verdict_statistics(
        self,
        league: Optional[str] = None,
        game_version: Optional[str] = None,
    ) -> int:
        """
        Clear verdict statistics.

        Args:
            league: If provided, only clear for this league.
            game_version: If provided with league, also filter by game version.

        Returns:
            Number of rows deleted.
        """
        if league and game_version:
            cursor = self._execute(
                "DELETE FROM verdict_statistics WHERE league = ? AND game_version = ?",
                (league, game_version),
            )
        elif league:
            cursor = self._execute(
                "DELETE FROM verdict_statistics WHERE league = ?",
                (league,),
            )
        else:
            cursor = self._execute("DELETE FROM verdict_statistics")

        return cursor.rowcount
