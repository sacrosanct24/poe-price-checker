"""
Statistics repository for aggregate statistics and database maintenance.

Handles database operations for:
- Aggregate counts across all tables
- Database maintenance (wipe, vacuum)
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Dict

from core.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class StatsRepository(BaseRepository):
    """Repository for statistics and maintenance operations."""

    def get_stats(self) -> Dict[str, int]:
        """
        Return aggregate statistics from all tables.

        Returns:
            Dictionary with counts for:
                - checked_items
                - sales
                - completed_sales
                - price_snapshots
                - price_checks
                - price_quotes
        """
        stats: Dict[str, int] = {}

        row = self._execute_fetchone("SELECT COUNT(*) FROM checked_items")
        stats["checked_items"] = row[0] if row else 0

        row = self._execute_fetchone("SELECT COUNT(*) FROM sales")
        stats["sales"] = row[0] if row else 0

        row = self._execute_fetchone(
            "SELECT COUNT(*) FROM sales WHERE sold_at IS NOT NULL"
        )
        stats["completed_sales"] = row[0] if row else 0

        row = self._execute_fetchone("SELECT COUNT(*) FROM price_history")
        stats["price_snapshots"] = row[0] if row else 0

        row = self._execute_fetchone("SELECT COUNT(*) FROM price_checks")
        stats["price_checks"] = row[0] if row else 0

        row = self._execute_fetchone("SELECT COUNT(*) FROM price_quotes")
        stats["price_quotes"] = row[0] if row else 0

        return stats

    def wipe_all_data(self) -> None:
        """
        Delete all rows from the main data tables.

        This preserves:
            - schema_version entries
            - table structure

        Effectively resets the app's data: checked items, sales, price history,
        price checks/quotes, plugin state, currency_rates.
        """
        logger.warning(
            "Wiping all database data (checked_items, sales, price_history, "
            "price_checks, price_quotes, plugin_state, currency_rates)."
        )

        with self.transaction() as conn:
            conn.execute("DELETE FROM checked_items")
            conn.execute("DELETE FROM sales")
            conn.execute("DELETE FROM price_history")
            conn.execute("DELETE FROM price_checks")
            conn.execute("DELETE FROM price_quotes")
            conn.execute("DELETE FROM plugin_state")
            try:
                conn.execute("DELETE FROM currency_rates")
            except sqlite3.OperationalError:
                pass  # Table may not exist in older schemas

        # Optional: shrink file; safe but may be slow on huge DBs
        try:
            self._conn.execute("VACUUM")
        except Exception as exc:  # non-fatal
            logger.error(f"VACUUM after wipe_all_data failed: {exc}")

    def vacuum(self) -> None:
        """Perform SQLite VACUUM for file-size maintenance."""
        self._execute("VACUUM")
