"""Listing lifecycle tracking for ML collection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class LifecycleUpdateStats:
    updated_visible: int = 0
    updated_missing: int = 0


class ListingLifecycleTracker:
    """
    Updates listing states after each polling cycle.

    State transitions:
    - LIVE -> STALE: listing age > 7 days, still visible
    - LIVE/STALE -> DISAPPEARED_FAST: not seen, first_seen_at < 24h ago
    - LIVE/STALE -> DISAPPEARED_SLOW: not seen, first_seen_at >= 24h ago
    - Any -> EXCLUDED: age > 14 days
    """

    def __init__(
        self,
        db: Database,
        league: str,
        game_id: str = "poe1",
        logger_override: Optional[logging.Logger] = None,
    ) -> None:
        self.db = db
        self.league = league
        self.game_id = game_id
        self.logger = logger_override or logger

    def update_listing_states(
        self,
        seen_listing_ids: Iterable[str],
        now: Optional[datetime] = None,
    ) -> LifecycleUpdateStats:
        now = now or datetime.now(timezone.utc)
        seen_set = {listing_id for listing_id in seen_listing_ids if listing_id}
        stats = LifecycleUpdateStats()

        with self.db.transaction() as conn:
            rows = conn.execute(
                """
                SELECT listing_id, first_seen_at, listing_state
                FROM ml_listings
                WHERE league = ? AND game_id = ?
                """,
                (self.league, self.game_id),
            ).fetchall()

            for row in rows:
                listing_id = row["listing_id"]
                first_seen = _parse_timestamp(row["first_seen_at"])
                if not first_seen:
                    continue

                age_days = (now - first_seen).total_seconds() / 86400
                if listing_id in seen_set:
                    state = _visible_state(age_days)
                    conn.execute(
                        """
                        UPDATE ml_listings
                        SET listing_state = ?, disappeared_at = NULL
                        WHERE listing_id = ?
                        """,
                        (state, listing_id),
                    )
                    stats.updated_visible += 1
                    continue

                if row["listing_state"] not in {"LIVE", "STALE"}:
                    continue

                state = _missing_state(age_days)
                conn.execute(
                    """
                    UPDATE ml_listings
                    SET listing_state = ?, disappeared_at = ?
                    WHERE listing_id = ?
                    """,
                    (state, now.isoformat(timespec="seconds"), listing_id),
                )
                stats.updated_missing += 1

        return stats


def _visible_state(age_days: float) -> str:
    if age_days > 14:
        return "EXCLUDED"
    if age_days >= 7:
        return "STALE"
    return "LIVE"


def _missing_state(age_days: float) -> str:
    if age_days < 1:
        return "DISAPPEARED_FAST"
    return "DISAPPEARED_SLOW"


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
