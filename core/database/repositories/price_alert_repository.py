"""
Price alert repository for monitoring item prices.

Handles database operations for:
- Creating and managing price alerts
- Recording alert triggers
- Cooldown enforcement
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.database.repositories.base_repository import BaseRepository


class PriceAlertRepository(BaseRepository):
    """Repository for price alert database operations."""

    def create_alert(
        self,
        item_name: str,
        league: str,
        game_version: str,
        alert_type: str,
        threshold_chaos: float,
        item_base_type: Optional[str] = None,
        cooldown_minutes: int = 30,
    ) -> int:
        """
        Create a new price alert.

        Args:
            item_name: Name of the item to monitor.
            league: League name (e.g., "Standard", "Dawn of the Hunt").
            game_version: "poe1" or "poe2".
            alert_type: "above" or "below".
            threshold_chaos: Price threshold in chaos orbs.
            item_base_type: Optional base type for the item.
            cooldown_minutes: Minutes between triggers (default 30).

        Returns:
            ID of the created alert.
        """
        cursor = self._execute(
            """
            INSERT INTO price_alerts (
                item_name, item_base_type, league, game_version,
                alert_type, threshold_chaos, cooldown_minutes,
                enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                item_name,
                item_base_type,
                league,
                game_version,
                alert_type,
                threshold_chaos,
                cooldown_minutes,
            ),
        )
        return cursor.lastrowid or 0

    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single alert by ID.

        Args:
            alert_id: The alert's ID.

        Returns:
            Dict with alert data or None if not found.
        """
        row = self._execute_fetchone(
            "SELECT * FROM price_alerts WHERE id = ?",
            (alert_id,),
        )
        if row:
            return dict(row)
        return None

    def get_active_alerts(
        self,
        league: str,
        game_version: str = "poe1",
    ) -> List[Dict[str, Any]]:
        """
        Get all enabled alerts for a league.

        Args:
            league: League name.
            game_version: "poe1" or "poe2".

        Returns:
            List of enabled alert dicts.
        """
        rows = self._execute_fetchall(
            """
            SELECT * FROM price_alerts
            WHERE league = ? AND game_version = ? AND enabled = 1
            ORDER BY item_name ASC
            """,
            (league, game_version),
        )
        return [dict(row) for row in rows]

    def get_all_alerts(
        self,
        league: Optional[str] = None,
        game_version: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all alerts with optional filtering.

        Args:
            league: Filter by league (optional).
            game_version: Filter by game version (optional).
            enabled_only: If True, only return enabled alerts.

        Returns:
            List of alert dicts.
        """
        sql = "SELECT * FROM price_alerts WHERE 1=1"
        params: List[Any] = []

        if league:
            sql += " AND league = ?"
            params.append(league)

        if game_version:
            sql += " AND game_version = ?"
            params.append(game_version)

        if enabled_only:
            sql += " AND enabled = 1"

        sql += " ORDER BY created_at DESC"

        rows = self._execute_fetchall(sql, tuple(params))
        return [dict(row) for row in rows]

    def update_alert(
        self,
        alert_id: int,
        threshold_chaos: Optional[float] = None,
        alert_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        cooldown_minutes: Optional[int] = None,
    ) -> bool:
        """
        Update an existing alert.

        Args:
            alert_id: The alert's ID.
            threshold_chaos: New threshold (optional).
            alert_type: New alert type (optional).
            enabled: New enabled state (optional).
            cooldown_minutes: New cooldown (optional).

        Returns:
            True if updated, False if alert not found.
        """
        updates: List[str] = []
        params: List[Any] = []

        if threshold_chaos is not None:
            updates.append("threshold_chaos = ?")
            params.append(threshold_chaos)

        if alert_type is not None:
            updates.append("alert_type = ?")
            params.append(alert_type)

        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)

        if cooldown_minutes is not None:
            updates.append("cooldown_minutes = ?")
            params.append(cooldown_minutes)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(alert_id)

        cursor = self._execute(
            f"UPDATE price_alerts SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        return cursor.rowcount > 0

    def delete_alert(self, alert_id: int) -> bool:
        """
        Delete an alert.

        Args:
            alert_id: The alert's ID.

        Returns:
            True if deleted, False if not found.
        """
        cursor = self._execute(
            "DELETE FROM price_alerts WHERE id = ?",
            (alert_id,),
        )
        return cursor.rowcount > 0

    def record_trigger(
        self,
        alert_id: int,
        current_price: float,
    ) -> None:
        """
        Record that an alert was triggered.

        Updates last_triggered_at, last_price_chaos, and increments trigger_count.

        Args:
            alert_id: The alert's ID.
            current_price: The price that triggered the alert.
        """
        self._execute(
            """
            UPDATE price_alerts
            SET last_triggered_at = CURRENT_TIMESTAMP,
                last_price_chaos = ?,
                trigger_count = trigger_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (current_price, alert_id),
        )

    def should_trigger(
        self,
        alert_id: int,
        current_price: float,
    ) -> bool:
        """
        Check if an alert should trigger based on threshold and cooldown.

        Args:
            alert_id: The alert's ID.
            current_price: The current item price.

        Returns:
            True if alert should fire, False otherwise.
        """
        alert = self.get_alert(alert_id)
        if not alert or not alert.get("enabled"):
            return False

        alert_type = alert.get("alert_type", "")
        threshold = alert.get("threshold_chaos", 0.0)

        # Check threshold condition
        threshold_met = False
        if alert_type == "above" and current_price > threshold:
            threshold_met = True
        elif alert_type == "below" and current_price < threshold:
            threshold_met = True

        if not threshold_met:
            return False

        # Check cooldown
        last_triggered = alert.get("last_triggered_at")
        cooldown_minutes = alert.get("cooldown_minutes", 30)

        if last_triggered:
            # Parse the timestamp
            if isinstance(last_triggered, str):
                try:
                    last_dt = datetime.fromisoformat(last_triggered)
                except ValueError:
                    try:
                        last_dt = datetime.strptime(last_triggered, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # Can't parse, assume cooldown passed
                        return True
            else:
                last_dt = last_triggered

            elapsed_minutes = (datetime.now() - last_dt).total_seconds() / 60
            if elapsed_minutes < cooldown_minutes:
                return False

        return True

    def update_last_price(
        self,
        alert_id: int,
        price: float,
    ) -> None:
        """
        Update the last known price for an alert (without triggering).

        Args:
            alert_id: The alert's ID.
            price: The current price.
        """
        self._execute(
            """
            UPDATE price_alerts
            SET last_price_chaos = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (price, alert_id),
        )

    def get_alerts_for_item(
        self,
        item_name: str,
        league: str,
        game_version: str = "poe1",
    ) -> List[Dict[str, Any]]:
        """
        Get all alerts for a specific item.

        Args:
            item_name: The item name.
            league: League name.
            game_version: "poe1" or "poe2".

        Returns:
            List of alert dicts for the item.
        """
        rows = self._execute_fetchall(
            """
            SELECT * FROM price_alerts
            WHERE item_name = ? AND league = ? AND game_version = ?
            ORDER BY created_at DESC
            """,
            (item_name, league, game_version),
        )
        return [dict(row) for row in rows]

    def clear_alerts(
        self,
        league: Optional[str] = None,
        game_version: Optional[str] = None,
    ) -> int:
        """
        Clear all alerts, optionally filtered by league/game.

        Args:
            league: Filter by league (optional).
            game_version: Filter by game version (optional).

        Returns:
            Number of alerts deleted.
        """
        if league and game_version:
            cursor = self._execute(
                "DELETE FROM price_alerts WHERE league = ? AND game_version = ?",
                (league, game_version),
            )
        elif league:
            cursor = self._execute(
                "DELETE FROM price_alerts WHERE league = ?",
                (league,),
            )
        elif game_version:
            cursor = self._execute(
                "DELETE FROM price_alerts WHERE game_version = ?",
                (game_version,),
            )
        else:
            cursor = self._execute("DELETE FROM price_alerts")

        return cursor.rowcount

    def get_alert_statistics(
        self,
        league: Optional[str] = None,
        game_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for alerts.

        Args:
            league: Filter by league (optional).
            game_version: Filter by game version (optional).

        Returns:
            Dict with total_alerts, enabled_alerts, total_triggers, etc.
        """
        sql = """
            SELECT
                COUNT(*) as total_alerts,
                COALESCE(SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END), 0) as enabled_alerts,
                COALESCE(SUM(CASE WHEN alert_type = 'above' THEN 1 ELSE 0 END), 0) as above_alerts,
                COALESCE(SUM(CASE WHEN alert_type = 'below' THEN 1 ELSE 0 END), 0) as below_alerts,
                COALESCE(SUM(trigger_count), 0) as total_triggers
            FROM price_alerts
            WHERE 1=1
        """
        params: List[Any] = []

        if league:
            sql += " AND league = ?"
            params.append(league)

        if game_version:
            sql += " AND game_version = ?"
            params.append(game_version)

        row = self._execute_fetchone(sql, tuple(params))
        if row:
            return {
                "total_alerts": row["total_alerts"] or 0,
                "enabled_alerts": row["enabled_alerts"] or 0,
                "above_alerts": row["above_alerts"] or 0,
                "below_alerts": row["below_alerts"] or 0,
                "total_triggers": row["total_triggers"] or 0,
            }
        return {
            "total_alerts": 0,
            "enabled_alerts": 0,
            "above_alerts": 0,
            "below_alerts": 0,
            "total_triggers": 0,
        }
