"""
Upgrade advice repository for AI-generated build recommendations.

Handles database operations for:
- Upgrade advice cache (temporary storage per profile/slot)
- Upgrade advice history (persistent history with automatic pruning)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.repositories.base_repository import BaseRepository


class UpgradeAdviceRepository(BaseRepository):
    """Repository for upgrade advice database operations."""

    # ------------------------------------------------------------------
    # Upgrade Advice Cache
    # ------------------------------------------------------------------

    def save_upgrade_advice(
        self,
        profile_name: str,
        slot: str,
        item_hash: str,
        advice_text: str,
        ai_model: Optional[str] = None,
    ) -> None:
        """
        Save or update upgrade advice for a profile/slot.

        Uses UPSERT to replace existing advice for the same profile+slot.

        Args:
            profile_name: Character profile name.
            slot: Equipment slot (e.g., "Helmet", "Body Armour").
            item_hash: Hash of current item to detect changes.
            advice_text: AI-generated advice (markdown).
            ai_model: AI model used (e.g., "gemini", "claude").
        """
        self._execute(
            """
            INSERT INTO upgrade_advice_cache
                (profile_name, slot, item_hash, advice_text, ai_model, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_name, slot) DO UPDATE SET
                item_hash = excluded.item_hash,
                advice_text = excluded.advice_text,
                ai_model = excluded.ai_model,
                created_at = CURRENT_TIMESTAMP
            """,
            (profile_name, slot, item_hash, advice_text, ai_model),
        )

    def get_upgrade_advice(
        self,
        profile_name: str,
        slot: str,
        item_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached upgrade advice for a profile/slot.

        Args:
            profile_name: Character profile name.
            slot: Equipment slot.
            item_hash: If provided, only return if hash matches (item unchanged).

        Returns:
            Dict with advice_text, ai_model, created_at, item_hash if found.
            None if not found or item_hash doesn't match.
        """
        if item_hash:
            row = self._execute_fetchone(
                """
                SELECT advice_text, ai_model, created_at, item_hash
                FROM upgrade_advice_cache
                WHERE profile_name = ? AND slot = ? AND item_hash = ?
                """,
                (profile_name, slot, item_hash),
            )
        else:
            row = self._execute_fetchone(
                """
                SELECT advice_text, ai_model, created_at, item_hash
                FROM upgrade_advice_cache
                WHERE profile_name = ? AND slot = ?
                """,
                (profile_name, slot),
            )

        if row:
            return {
                "advice_text": row["advice_text"],
                "ai_model": row["ai_model"],
                "created_at": row["created_at"],
                "item_hash": row["item_hash"],
            }
        return None

    def get_all_upgrade_advice(
        self,
        profile_name: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all cached upgrade advice for a profile.

        Args:
            profile_name: Character profile name.

        Returns:
            Dict mapping slot -> advice data.
        """
        rows = self._execute_fetchall(
            """
            SELECT slot, advice_text, ai_model, created_at, item_hash
            FROM upgrade_advice_cache
            WHERE profile_name = ?
            """,
            (profile_name,),
        )

        result = {}
        for row in rows:
            result[row["slot"]] = {
                "advice_text": row["advice_text"],
                "ai_model": row["ai_model"],
                "created_at": row["created_at"],
                "item_hash": row["item_hash"],
            }
        return result

    def clear_upgrade_advice(
        self,
        profile_name: Optional[str] = None,
        slot: Optional[str] = None,
    ) -> int:
        """
        Clear cached upgrade advice.

        Args:
            profile_name: If provided, only clear for this profile.
            slot: If provided with profile_name, only clear this slot.

        Returns:
            Number of rows deleted.
        """
        if profile_name and slot:
            cursor = self._execute(
                "DELETE FROM upgrade_advice_cache WHERE profile_name = ? AND slot = ?",
                (profile_name, slot),
            )
        elif profile_name:
            cursor = self._execute(
                "DELETE FROM upgrade_advice_cache WHERE profile_name = ?",
                (profile_name,),
            )
        else:
            cursor = self._execute("DELETE FROM upgrade_advice_cache")

        return cursor.rowcount

    # ------------------------------------------------------------------
    # Upgrade Advice History
    # ------------------------------------------------------------------

    def save_upgrade_advice_history(
        self,
        profile_name: str,
        slot: str,
        item_hash: str,
        advice_text: str,
        ai_model: Optional[str] = None,
        ai_provider: Optional[str] = None,
        include_stash: bool = False,
        stash_candidates_count: int = 0,
    ) -> int:
        """
        Save upgrade advice to history, keeping last 5 per profile+slot.

        Args:
            profile_name: Character profile name.
            slot: Equipment slot (e.g., "Helmet", "Body Armour").
            item_hash: Hash of current item.
            advice_text: AI-generated advice (markdown).
            ai_model: AI model used (e.g., "grok-4-1-fast-reasoning").
            ai_provider: AI provider (e.g., "xai", "gemini", "claude").
            include_stash: Whether stash was scanned for this analysis.
            stash_candidates_count: Number of stash candidates found.

        Returns:
            ID of the inserted record.
        """
        # Insert new record
        cursor = self._execute(
            """
            INSERT INTO upgrade_advice_history
                (profile_name, slot, item_hash, advice_text, ai_model,
                 ai_provider, include_stash, stash_candidates_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                profile_name,
                slot,
                item_hash,
                advice_text,
                ai_model,
                ai_provider,
                1 if include_stash else 0,
                stash_candidates_count,
            ),
        )
        row_id = cursor.lastrowid or 0

        # Cleanup old records, keep last 5 per profile+slot
        self._execute(
            """
            DELETE FROM upgrade_advice_history
            WHERE profile_name = ? AND slot = ?
            AND id NOT IN (
                SELECT id FROM upgrade_advice_history
                WHERE profile_name = ? AND slot = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 5
            )
            """,
            (profile_name, slot, profile_name, slot),
        )

        return row_id

    def get_upgrade_advice_history(
        self,
        profile_name: str,
        slot: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get upgrade advice history for a profile+slot.

        Args:
            profile_name: Character profile name.
            slot: Equipment slot.
            limit: Maximum entries to return (default 5).

        Returns:
            List of advice records, newest first.
        """
        rows = self._execute_fetchall(
            """
            SELECT id, item_hash, advice_text, ai_model, ai_provider,
                   include_stash, stash_candidates_count, created_at
            FROM upgrade_advice_history
            WHERE profile_name = ? AND slot = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (profile_name, slot, limit),
        )

        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "item_hash": row["item_hash"],
                "advice_text": row["advice_text"],
                "ai_model": row["ai_model"],
                "ai_provider": row["ai_provider"],
                "include_stash": bool(row["include_stash"]),
                "stash_candidates_count": row["stash_candidates_count"],
                "created_at": row["created_at"],
            })
        return results

    def get_latest_advice_from_history(
        self,
        profile_name: str,
        slot: str,
        item_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent advice from history for a slot.

        Args:
            profile_name: Character profile name.
            slot: Equipment slot.
            item_hash: If provided, only return if hash matches (item unchanged).

        Returns:
            Most recent advice record, or None if not found.
        """
        if item_hash:
            row = self._execute_fetchone(
                """
                SELECT id, item_hash, advice_text, ai_model, ai_provider,
                       include_stash, stash_candidates_count, created_at
                FROM upgrade_advice_history
                WHERE profile_name = ? AND slot = ? AND item_hash = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (profile_name, slot, item_hash),
            )
        else:
            row = self._execute_fetchone(
                """
                SELECT id, item_hash, advice_text, ai_model, ai_provider,
                       include_stash, stash_candidates_count, created_at
                FROM upgrade_advice_history
                WHERE profile_name = ? AND slot = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (profile_name, slot),
            )

        if row:
            return {
                "id": row["id"],
                "item_hash": row["item_hash"],
                "advice_text": row["advice_text"],
                "ai_model": row["ai_model"],
                "ai_provider": row["ai_provider"],
                "include_stash": bool(row["include_stash"]),
                "stash_candidates_count": row["stash_candidates_count"],
                "created_at": row["created_at"],
            }
        return None

    def get_all_slots_latest_history(
        self,
        profile_name: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get the latest history entry for all slots of a profile.

        Args:
            profile_name: Character profile name.

        Returns:
            Dict mapping slot -> latest advice data.
        """
        rows = self._execute_fetchall(
            """
            SELECT h1.*
            FROM upgrade_advice_history h1
            INNER JOIN (
                SELECT slot, MAX(created_at) as max_created
                FROM upgrade_advice_history
                WHERE profile_name = ?
                GROUP BY slot
            ) h2 ON h1.slot = h2.slot AND h1.created_at = h2.max_created
            WHERE h1.profile_name = ?
            """,
            (profile_name, profile_name),
        )

        result = {}
        for row in rows:
            result[row["slot"]] = {
                "id": row["id"],
                "item_hash": row["item_hash"],
                "advice_text": row["advice_text"],
                "ai_model": row["ai_model"],
                "ai_provider": row["ai_provider"],
                "include_stash": bool(row["include_stash"]),
                "stash_candidates_count": row["stash_candidates_count"],
                "created_at": row["created_at"],
            }
        return result

    def clear_upgrade_advice_history(
        self,
        profile_name: Optional[str] = None,
        slot: Optional[str] = None,
    ) -> int:
        """
        Clear upgrade advice history.

        Args:
            profile_name: If provided, only clear for this profile.
            slot: If provided with profile_name, only clear this slot.

        Returns:
            Number of rows deleted.
        """
        if profile_name and slot:
            cursor = self._execute(
                "DELETE FROM upgrade_advice_history WHERE profile_name = ? AND slot = ?",
                (profile_name, slot),
            )
        elif profile_name:
            cursor = self._execute(
                "DELETE FROM upgrade_advice_history WHERE profile_name = ?",
                (profile_name,),
            )
        else:
            cursor = self._execute("DELETE FROM upgrade_advice_history")

        return cursor.rowcount
