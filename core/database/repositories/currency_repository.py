"""
Currency rate repository for tracking divine/chaos and exalt/chaos rates.

Handles database operations for currency rate snapshots used in
economy tracking and price calculations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.repositories.base_repository import BaseRepository
from core.database.utils import parse_db_timestamp


class CurrencyRepository(BaseRepository):
    """Repository for currency rate database operations."""

    def record_currency_rate(
        self,
        league: str,
        game_version: str,
        divine_to_chaos: float,
        exalt_to_chaos: Optional[float] = None,
    ) -> int:
        """
        Record a currency rate snapshot.

        Args:
            league: League name
            game_version: "poe1" or "poe2"
            divine_to_chaos: Divine orb value in chaos
            exalt_to_chaos: Exalted orb value in chaos (optional)

        Returns:
            The row ID of the inserted record
        """
        cursor = self._execute(
            """
            INSERT INTO currency_rates (league, game_version, divine_to_chaos, exalt_to_chaos)
            VALUES (?, ?, ?, ?)
            """,
            (league, game_version, divine_to_chaos, exalt_to_chaos),
        )
        return cursor.lastrowid or 0

    def get_latest_currency_rate(
        self, league: str, game_version: str = "poe1"
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent currency rate for a league.

        Args:
            league: League name
            game_version: "poe1" or "poe2"

        Returns:
            Dict with divine_to_chaos, exalt_to_chaos, recorded_at or None
        """
        row = self._execute_fetchone(
            """
            SELECT divine_to_chaos, exalt_to_chaos, recorded_at
            FROM currency_rates
            WHERE league = ? AND game_version = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (league, game_version),
        )
        if row:
            return {
                "divine_to_chaos": row["divine_to_chaos"],
                "exalt_to_chaos": row["exalt_to_chaos"],
                "recorded_at": parse_db_timestamp(row["recorded_at"]),
            }
        return None

    def get_currency_rate_history(
        self, league: str, days: int = 30, game_version: str = "poe1"
    ) -> List[Dict[str, Any]]:
        """
        Get currency rate history for trend analysis.

        Args:
            league: League name
            days: Number of days of history
            game_version: "poe1" or "poe2"

        Returns:
            List of rate records ordered by time descending
        """
        rows = self._execute_fetchall(
            """
            SELECT divine_to_chaos, exalt_to_chaos, recorded_at
            FROM currency_rates
            WHERE league = ? AND game_version = ?
              AND recorded_at >= DATE('now', ?)
            ORDER BY recorded_at DESC
            """,
            (league, game_version, f"-{days} days"),
        )
        return [
            {
                "divine_to_chaos": row["divine_to_chaos"],
                "exalt_to_chaos": row["exalt_to_chaos"],
                "recorded_at": parse_db_timestamp(row["recorded_at"]),
            }
            for row in rows
        ]
