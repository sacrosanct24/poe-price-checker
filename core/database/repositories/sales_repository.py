"""
Sales repository for managing item sales data.

Handles all sales-related database operations including:
- Creating and completing sales
- Recording instant sales
- Querying sales history
- Sales summaries and statistics
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.database.repositories.base_repository import BaseRepository
from core.database.utils import ensure_utc, parse_db_timestamp

logger = logging.getLogger(__name__)


class SalesRepository(BaseRepository):
    """Repository for sales-related database operations."""

    def add_sale(
        self,
        item_name: str,
        listed_price_chaos: float,
        item_base_type: Optional[str] = None,
        item_id: Optional[int] = None,
    ) -> int:
        """
        Create a sale entry and return its ID.

        Args:
            item_name: Name of the item being sold
            listed_price_chaos: Listed price in chaos orbs
            item_base_type: Optional base type of the item
            item_id: Optional link to checked_items table

        Returns:
            The ID of the created sale entry
        """
        cursor = self._execute(
            """
            INSERT INTO sales
                (item_name, item_base_type, listed_price_chaos, item_id)
            VALUES (?, ?, ?, ?)
            """,
            (item_name, item_base_type, listed_price_chaos, item_id),
        )
        return cursor.lastrowid or 0

    def record_instant_sale(
        self,
        item_name: str,
        chaos_value: Optional[float] = None,
        item_base_type: Optional[str] = None,
        notes: Optional[str] = None,
        source: Optional[str] = None,
        price_chaos: Optional[float] = None,
    ) -> int:
        """
        Record a sale where listing and sale happen at essentially the same time.

        This:
        - Inserts into `sales` with listed_at = sold_at = CURRENT_TIMESTAMP
        - Sets listed_price_chaos = actual_price_chaos = effective chaos value
        - Leaves item_id NULL (we're not linking to checked_items yet)
        - Sets time_to_sale_hours = 0.0 and relisted = 0

        Args:
            item_name: Name of the item
            chaos_value: Chaos value (legacy positional/keyword)
            item_base_type: Optional base type
            notes: Optional notes
            source: Where the sale came from (trade site, manual, loot, etc.)
            price_chaos: Chaos value (new keyword used by GUI)

        Returns:
            The ID of the created sale entry

        Raises:
            ValueError: If neither chaos_value nor price_chaos is provided
        """
        # Support both chaos_value and price_chaos, prefer explicit chaos_value
        effective_chaos = chaos_value if chaos_value is not None else price_chaos

        if effective_chaos is None:
            raise ValueError(
                "record_instant_sale requires either chaos_value or price_chaos"
            )

        cursor = self._execute(
            """
            INSERT INTO sales (
                item_id,
                item_name,
                item_base_type,
                source,
                listed_price_chaos,
                listed_at,
                sold_at,
                actual_price_chaos,
                time_to_sale_hours,
                relisted,
                notes
            )
            VALUES (
                NULL,
                ?,
                ?,
                ?,
                ?,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                ?,
                0.0,
                0,
                ?
            )
            """,
            (
                item_name,
                item_base_type,
                source,
                effective_chaos,
                effective_chaos,
                notes,
            ),
        )
        return cursor.lastrowid or 0

    def complete_sale(
        self,
        sale_id: int,
        actual_price_chaos: float,
        sold_at: Optional[datetime] = None,
    ) -> None:
        """
        Mark a sale as completed.

        Normalizes timestamps to UTC to avoid negative durations when
        SQLite uses UTC (CURRENT_TIMESTAMP) and Python uses local time.

        Args:
            sale_id: ID of the sale to complete
            actual_price_chaos: Final sale price in chaos orbs
            sold_at: When the sale completed (defaults to now)
        """
        if sold_at is None:
            sold_at = datetime.now()

        sold_at_utc = ensure_utc(sold_at)

        # Retrieve listed_at
        row = self._execute_fetchone(
            "SELECT listed_at FROM sales WHERE id = ?", (sale_id,)
        )
        listed_at_str = row[0] if row else None

        listed_at = parse_db_timestamp(listed_at_str) or sold_at_utc
        listed_at_utc = ensure_utc(listed_at)

        # Compute hours to sale, clamp negative to zero
        time_to_sale = (
            sold_at_utc - listed_at_utc
        ).total_seconds() / 3600.0
        if time_to_sale < 0:
            time_to_sale = 0.0

        self._execute(
            """
            UPDATE sales
            SET sold_at = ?, actual_price_chaos = ?, time_to_sale_hours = ?
            WHERE id = ?
            """,
            (sold_at_utc.isoformat(), actual_price_chaos, time_to_sale, sale_id),
        )

        logger.info(
            f"Sale completed: ID {sale_id}, sold for {actual_price_chaos}c "
            f"in {time_to_sale:.1f}h"
        )

    def mark_sale_unsold(self, sale_id: int) -> None:
        """
        Mark a sale as unsold.

        Args:
            sale_id: ID of the sale to mark as unsold
        """
        now_utc = ensure_utc(datetime.now())

        self._execute(
            """
            UPDATE sales
            SET sold_at = ?, notes = 'Did not sell'
            WHERE id = ?
            """,
            (now_utc.isoformat(), sale_id),
        )

    def get_sales(
        self,
        sold_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return sales entries, newest-first by listed_at DESC.

        Args:
            sold_only: If True, only return completed sales
            limit: Maximum number of entries to return

        Returns:
            List of sale dictionaries
        """
        query = "SELECT * FROM sales WHERE 1=1"

        if sold_only:
            query += " AND sold_at IS NOT NULL"

        query += " ORDER BY listed_at DESC LIMIT ?"

        rows = self._execute_fetchall(query, (limit,))
        return [dict(row) for row in rows]

    def get_recent_sales(
        self,
        limit: int = 50,
        search_text: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        """
        Return recent sales rows, ordered by most recent activity, with optional filters.

        Args:
            limit: Maximum number of entries to return
            search_text: Case-insensitive substring match against
                        item_name, item_base_type, source, notes
            source: If provided and not blank/'All', filter by exact source

        Returns:
            List of sale rows with fields:
                id, item_name, item_base_type, source, listed_at, sold_at,
                listed_price_chaos, actual_price_chaos, price_chaos (derived),
                time_to_sale_hours, relisted, notes
        """
        clauses: List[str] = []
        params: List[Any] = []

        # Search filter
        if search_text:
            like = f"%{search_text.strip().lower()}%"
            clauses.append(
                """
                (
                    LOWER(item_name) LIKE ?
                    OR LOWER(COALESCE(item_base_type, '')) LIKE ?
                    OR LOWER(COALESCE(source, '')) LIKE ?
                    OR LOWER(COALESCE(notes, '')) LIKE ?
                )
                """
            )
            params.extend([like, like, like, like])

        # Source filter
        if source and source.strip() and source.strip().lower() != "all":
            clauses.append("source = ?")
            params.append(source.strip())

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        # where_sql is constructed from hardcoded clauses, all values use parameterized queries
        sql = f"""
            SELECT
                id,
                item_name,
                item_base_type,
                source,
                listed_at,
                sold_at,
                listed_price_chaos,
                actual_price_chaos,
                COALESCE(actual_price_chaos, listed_price_chaos) AS price_chaos,
                time_to_sale_hours,
                relisted,
                notes
            FROM sales
            {where_sql}
            ORDER BY COALESCE(sold_at, listed_at) DESC
            LIMIT ?
        """  # nosec - SQL is constructed from hardcoded strings, params are safe
        params.append(limit)

        return self._execute_fetchall(sql, tuple(params))

    def get_distinct_sale_sources(self) -> List[str]:
        """
        Return a list of distinct non-empty sources from the sales table.

        Returns:
            Sorted list of unique source names
        """
        rows = self._execute_fetchall(
            """
            SELECT DISTINCT source
            FROM sales
            WHERE source IS NOT NULL AND TRIM(source) <> ''
            ORDER BY source COLLATE NOCASE
            """
        )
        return [row[0] for row in rows]

    def get_sales_summary(self) -> Dict[str, Any]:
        """
        Return overall sales summary.

        Returns:
            Dictionary with:
                - total_sales: number of sales rows
                - total_chaos: sum of effective chaos price
                - avg_chaos: average effective chaos price per sale
        """
        row = self._execute_fetchone(
            """
            SELECT
                COUNT(*) AS total_sales,
                COALESCE(
                    SUM(COALESCE(actual_price_chaos, listed_price_chaos)),
                    0
                ) AS total_chaos,
                CASE
                    WHEN COUNT(*) > 0 THEN
                        COALESCE(
                            AVG(COALESCE(actual_price_chaos, listed_price_chaos)),
                            0
                        )
                    ELSE
                        0
                END AS avg_chaos
            FROM sales
            """
        )
        if row is None:
            return {"total_sales": 0, "total_chaos": 0.0, "avg_chaos": 0.0}

        return {
            "total_sales": row["total_sales"],
            "total_chaos": float(row["total_chaos"] or 0.0),
            "avg_chaos": float(row["avg_chaos"] or 0.0),
        }

    def get_daily_sales_summary(self, days: int = 30) -> List[sqlite3.Row]:
        """
        Return daily sales summary for the last N days (including today).

        Args:
            days: Number of days to include in the summary

        Returns:
            List of rows with fields:
                day (YYYY-MM-DD), sale_count, total_chaos, avg_chaos
        """
        return self._execute_fetchall(
            """
            SELECT
                DATE(COALESCE(sold_at, listed_at)) AS day,
                COUNT(*) AS sale_count,
                COALESCE(
                    SUM(COALESCE(actual_price_chaos, listed_price_chaos)),
                    0
                ) AS total_chaos,
                CASE
                    WHEN COUNT(*) > 0 THEN
                        COALESCE(
                            AVG(COALESCE(actual_price_chaos, listed_price_chaos)),
                            0
                        )
                    ELSE
                        0
                END AS avg_chaos
            FROM sales
            WHERE COALESCE(sold_at, listed_at) >= DATE('now', ?)
            GROUP BY DATE(COALESCE(sold_at, listed_at))
            ORDER BY DATE(COALESCE(sold_at, listed_at)) DESC
            """,
            (f"-{int(days)} days",),
        )
