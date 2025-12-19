"""
Export service for exporting data to CSV and JSON formats.

Provides data export functionality for sales history, price checks, and loot sessions.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    file_path: Optional[Path] = None
    record_count: int = 0
    error: Optional[str] = None


class ExportService:
    """Service for exporting data to various formats."""

    SUPPORTED_FORMATS = ["csv", "json"]

    def __init__(self, db: Optional["Database"] = None):
        self.db = db

    def export_to_json(
        self,
        data: List[Dict[str, Any]],
        file_path: Path,
        pretty: bool = True
    ) -> ExportResult:
        """
        Export data to JSON file.

        Args:
            data: List of dictionaries to export
            file_path: Output file path
            pretty: Whether to format JSON with indentation

        Returns:
            ExportResult with success status
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                else:
                    json.dump(data, f, default=str, ensure_ascii=False)

            return ExportResult(
                success=True,
                file_path=file_path,
                record_count=len(data)
            )

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return ExportResult(success=False, error=str(e))

    def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        file_path: Path,
        columns: Optional[List[str]] = None
    ) -> ExportResult:
        """
        Export data to CSV file.

        Args:
            data: List of dictionaries to export
            file_path: Output file path
            columns: Optional list of columns to include (uses all if None)

        Returns:
            ExportResult with success status
        """
        try:
            if not data:
                return ExportResult(
                    success=True,
                    file_path=file_path,
                    record_count=0
                )

            # Determine columns
            if columns is None:
                columns = list(data[0].keys())

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)

            return ExportResult(
                success=True,
                file_path=file_path,
                record_count=len(data)
            )

        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return ExportResult(success=False, error=str(e))

    def get_exportable_sales(
        self,
        days: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales data formatted for export.

        Args:
            days: Number of days to include (None = all)
            limit: Maximum number of records

        Returns:
            List of sale dictionaries
        """
        if not self.db:
            return []

        try:
            query = """
                SELECT
                    id,
                    item_name,
                    sale_price,
                    buyer_name,
                    notes,
                    sold_at,
                    created_at
                FROM sales
            """
            params: List[Any] = []

            if days:
                cutoff = datetime.now() - timedelta(days=days)
                query += " WHERE sold_at >= ?"
                params.append(cutoff.isoformat())

            query += " ORDER BY sold_at DESC"

            if limit:
                query += f" LIMIT {limit}"

            cursor = self.db.conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get sales for export: {e}")
            return []

    def get_exportable_price_checks(
        self,
        days: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get price check data formatted for export.

        Args:
            days: Number of days to include (None = all)
            limit: Maximum number of records

        Returns:
            List of price check dictionaries
        """
        if not self.db:
            return []

        try:
            query = """
                SELECT
                    pc.id,
                    pc.item_name,
                    pc.item_base_type,
                    pc.league,
                    pc.game_version,
                    pc.checked_at,
                    pc.source,
                    pq.price_chaos,
                    pq.original_currency
                FROM price_checks pc
                LEFT JOIN price_quotes pq ON pc.id = pq.price_check_id
            """
            params: List[Any] = []

            if days:
                cutoff = datetime.now() - timedelta(days=days)
                query += " WHERE pc.checked_at >= ?"
                params.append(cutoff.isoformat())

            query += " ORDER BY pc.checked_at DESC"

            if limit:
                query += f" LIMIT {limit}"

            cursor = self.db.conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get price checks for export: {e}")
            return []

    def get_exportable_loot_session(
        self,
        session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get loot session data formatted for export.

        Args:
            session_id: Specific session ID (None = latest session)

        Returns:
            List of loot item dictionaries
        """
        if not self.db:
            return []

        try:
            # Get session ID if not specified
            if session_id is None:
                cursor = self.db.conn.execute("""
                    SELECT id FROM loot_sessions
                    ORDER BY created_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    session_id = row[0]
                else:
                    return []

            # Get session items
            cursor = self.db.conn.execute("""
                SELECT
                    li.id,
                    li.item_name,
                    li.item_base_type,
                    li.chaos_value,
                    li.divine_value,
                    li.stack_size,
                    li.created_at,
                    ls.name as session_name,
                    ls.created_at as session_start
                FROM loot_items li
                JOIN loot_sessions ls ON li.session_id = ls.id
                WHERE li.session_id = ?
                ORDER BY li.created_at DESC
            """, (session_id,))

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get loot session for export: {e}")
            return []

    def get_exportable_rankings(
        self,
        league: str,
        category: str = "currency"
    ) -> List[Dict[str, Any]]:
        """
        Get price rankings data formatted for export.

        Args:
            league: League name
            category: Item category

        Returns:
            List of ranking dictionaries
        """
        if not self.db:
            return []

        try:
            from core.price_rankings import PriceRankingCache, Top20Calculator
            from data_sources.pricing.poe_ninja import PoeNinjaAPI

            api = PoeNinjaAPI(league=league)
            cache = PriceRankingCache(league=league)
            calculator = Top20Calculator(cache, poe_ninja_api=api)

            ranking = calculator.get_category(category)
            if not ranking:
                return []

            return [
                {
                    "rank": item.rank,
                    "name": item.name,
                    "chaos_value": item.chaos_value,
                    "divine_value": getattr(item, "divine_value", None),
                    "icon": getattr(item, "icon", ""),
                    "rarity": getattr(item, "rarity", "normal"),
                }
                for item in ranking.items
            ]

        except Exception as e:
            logger.error(f"Failed to get rankings for export: {e}")
            return []

    def export_data(
        self,
        data_type: str,
        format: str,
        file_path: Path,
        days: Optional[int] = None,
        **kwargs
    ) -> ExportResult:
        """
        High-level export function.

        Args:
            data_type: Type of data ("sales", "price_checks", "loot", "rankings")
            format: Output format ("csv" or "json")
            file_path: Output file path
            days: Number of days to include
            **kwargs: Additional arguments for specific data types

        Returns:
            ExportResult with success status
        """
        # Get data based on type
        if data_type == "sales":
            data = self.get_exportable_sales(days=days)
        elif data_type == "price_checks":
            data = self.get_exportable_price_checks(days=days)
        elif data_type == "loot":
            session_id = kwargs.get("session_id")
            data = self.get_exportable_loot_session(session_id=session_id)
        elif data_type == "rankings":
            league = kwargs.get("league", "Standard")
            category = kwargs.get("category", "currency")
            data = self.get_exportable_rankings(league=league, category=category)
        else:
            return ExportResult(success=False, error=f"Unknown data type: {data_type}")

        # Export to format
        if format == "json":
            return self.export_to_json(data, file_path)
        elif format == "csv":
            return self.export_to_csv(data, file_path)
        else:
            return ExportResult(success=False, error=f"Unknown format: {format}")
