"""
Checked items repository for tracking recently price-checked items.

Handles database operations for items that have been looked up
for pricing information.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.repositories.base_repository import BaseRepository
from core.game_version import GameVersion


class CheckedItemsRepository(BaseRepository):
    """Repository for checked items database operations."""

    def add_checked_item(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        chaos_value: float,
        item_base_type: Optional[str] = None,
    ) -> int:
        """
        Insert a checked item and return its ID.

        Args:
            game_version: Game version (POE1 or POE2)
            league: League name
            item_name: Name of the item
            chaos_value: Price in chaos orbs
            item_base_type: Optional base type of the item

        Returns:
            The ID of the inserted record
        """
        cursor = self._execute(
            """
            INSERT INTO checked_items
                (game_version, league, item_name, item_base_type, chaos_value)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_version.value, league, item_name, item_base_type, chaos_value),
        )
        return cursor.lastrowid or 0

    def get_checked_items(
        self,
        game_version: Optional[GameVersion] = None,
        league: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return recent checked items.

        Results are ordered newest-first by:
        1. checked_at DESC
        2. id DESC (tie-breaker for identical timestamps)

        Args:
            game_version: Optional filter by game version
            league: Optional filter by league
            limit: Maximum number of items to return

        Returns:
            List of checked item dictionaries
        """
        query = "SELECT * FROM checked_items WHERE 1=1"
        params: List[Any] = []

        if game_version:
            query += " AND game_version = ?"
            params.append(game_version.value)

        if league:
            query += " AND league = ?"
            params.append(league)

        query += " ORDER BY checked_at DESC, id DESC LIMIT ?"
        params.append(limit)

        rows = self._execute_fetchall(query, tuple(params))
        return [dict(row) for row in rows]
