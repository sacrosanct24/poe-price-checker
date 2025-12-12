"""
Chart data service for price history visualization.

Provides data aggregation from database tables for chart rendering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class PriceDataPoint:
    """A single data point for price charts."""
    date: datetime
    chaos_value: float
    divine_value: Optional[float] = None


@dataclass
class ChartSeries:
    """A complete series of data for charting."""
    name: str
    data_points: List[PriceDataPoint]
    color: Optional[str] = None

    @property
    def dates(self) -> List[datetime]:
        """Get list of dates."""
        return [p.date for p in self.data_points]

    @property
    def chaos_values(self) -> List[float]:
        """Get list of chaos values."""
        return [p.chaos_value for p in self.data_points]

    @property
    def divine_values(self) -> List[Optional[float]]:
        """Get list of divine values."""
        return [p.divine_value for p in self.data_points]


class ChartDataService:
    """Service for retrieving and aggregating chart data."""

    def __init__(self, db: "Database"):
        self.db = db

    def get_item_price_series(
        self,
        item_name: str,
        league: str,
        days: int = 30
    ) -> Optional[ChartSeries]:
        """
        Get price history for a specific item.

        Args:
            item_name: Name of the item to query
            league: League name
            days: Number of days of history (0 = all time)

        Returns:
            ChartSeries with price data points, or None if no data
        """
        try:
            query = """
                SELECT recorded_at, chaos_value, divine_value
                FROM price_history
                WHERE item_name = ? AND league = ?
            """
            params: list = [item_name, league]

            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)
                query += " AND recorded_at >= ?"
                params.append(cutoff.isoformat())

            query += " ORDER BY recorded_at ASC"

            cursor = self.db.conn.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return None

            data_points = []
            for row in rows:
                recorded_at = row[0]
                if isinstance(recorded_at, str):
                    recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))

                data_points.append(PriceDataPoint(
                    date=recorded_at,
                    chaos_value=float(row[1]) if row[1] else 0.0,
                    divine_value=float(row[2]) if row[2] else None
                ))

            return ChartSeries(name=item_name, data_points=data_points)

        except Exception as e:
            logger.error(f"Failed to get price series for {item_name}: {e}")
            return None

    def get_currency_rate_series(
        self,
        currency: str,
        league: str,
        days: int = 30
    ) -> Optional[ChartSeries]:
        """
        Get currency rate history.

        Args:
            currency: Currency name (e.g., "Divine Orb", "Exalted Orb")
            league: League name
            days: Number of days of history (0 = all time)

        Returns:
            ChartSeries with rate data points, or None if no data
        """
        try:
            # Map currency names to column names
            column_map = {
                "Divine Orb": "divine_to_chaos",
                "divine": "divine_to_chaos",
                "Exalted Orb": "exalt_to_chaos",
                "exalt": "exalt_to_chaos",
            }

            column = column_map.get(currency)
            if not column:
                # Try to get from league_economy_rates table
                return self._get_currency_from_economy_rates(currency, league, days)

            query = f"""
                SELECT recorded_at, {column}
                FROM currency_rates
                WHERE league = ? AND {column} IS NOT NULL
            """
            params: list = [league]

            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)
                query += " AND recorded_at >= ?"
                params.append(cutoff.isoformat())

            query += " ORDER BY recorded_at ASC"

            cursor = self.db.conn.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return None

            data_points = []
            for row in rows:
                recorded_at = row[0]
                if isinstance(recorded_at, str):
                    recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))

                data_points.append(PriceDataPoint(
                    date=recorded_at,
                    chaos_value=float(row[1]) if row[1] else 0.0
                ))

            return ChartSeries(name=currency, data_points=data_points)

        except Exception as e:
            logger.error(f"Failed to get currency series for {currency}: {e}")
            return None

    def _get_currency_from_economy_rates(
        self,
        currency: str,
        league: str,
        days: int
    ) -> Optional[ChartSeries]:
        """Get currency data from league_economy_rates table."""
        try:
            query = """
                SELECT rate_date, chaos_value
                FROM league_economy_rates
                WHERE league = ? AND currency_name = ?
            """
            params: list = [league, currency]

            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)
                query += " AND rate_date >= ?"
                params.append(cutoff.strftime("%Y-%m-%d"))

            query += " ORDER BY rate_date ASC"

            cursor = self.db.conn.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return None

            data_points = []
            for row in rows:
                rate_date = row[0]
                if isinstance(rate_date, str):
                    # Handle date string (YYYY-MM-DD)
                    rate_date = datetime.strptime(rate_date[:10], "%Y-%m-%d")

                data_points.append(PriceDataPoint(
                    date=rate_date,
                    chaos_value=float(row[1]) if row[1] else 0.0
                ))

            return ChartSeries(name=currency, data_points=data_points)

        except Exception as e:
            logger.error(f"Failed to get economy rates for {currency}: {e}")
            return None

    def get_item_from_economy_items(
        self,
        item_name: str,
        league: str,
        days: int = 30
    ) -> Optional[ChartSeries]:
        """
        Get item price history from league_economy_items table.

        Args:
            item_name: Name of the item to query
            league: League name
            days: Number of days of history (0 = all time)

        Returns:
            ChartSeries with price data points, or None if no data
        """
        try:
            query = """
                SELECT item_date, chaos_value, divine_value
                FROM league_economy_items
                WHERE league = ? AND item_name = ?
            """
            params: list = [league, item_name]

            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)
                query += " AND item_date >= ?"
                params.append(cutoff.strftime("%Y-%m-%d"))

            query += " ORDER BY item_date ASC"

            cursor = self.db.conn.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                # Fall back to price_history table
                return self.get_item_price_series(item_name, league, days)

            data_points = []
            for row in rows:
                item_date = row[0]
                if isinstance(item_date, str):
                    item_date = datetime.strptime(item_date[:10], "%Y-%m-%d")

                data_points.append(PriceDataPoint(
                    date=item_date,
                    chaos_value=float(row[1]) if row[1] else 0.0,
                    divine_value=float(row[2]) if row[2] else None
                ))

            return ChartSeries(name=item_name, data_points=data_points)

        except Exception as e:
            logger.error(f"Failed to get economy items for {item_name}: {e}")
            return None

    def get_available_currencies(self, league: str) -> List[str]:
        """Get list of currencies with data for a league."""
        try:
            cursor = self.db.conn.execute("""
                SELECT DISTINCT currency_name
                FROM league_economy_rates
                WHERE league = ?
                ORDER BY currency_name
            """, (league,))
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get available currencies: {e}")
            return []

    def get_available_items(self, league: str, limit: int = 100) -> List[str]:
        """Get list of items with price history for a league."""
        try:
            cursor = self.db.conn.execute("""
                SELECT DISTINCT item_name
                FROM league_economy_items
                WHERE league = ?
                ORDER BY item_name
                LIMIT ?
            """, (league, limit))
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get available items: {e}")
            return []
