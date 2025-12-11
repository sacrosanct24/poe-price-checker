"""
Historical price ranking storage.

SQLite-based storage for daily price ranking snapshots.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.rankings.models import RankedItem, CategoryRanking
from core.rankings.cache import PriceRankingCache

logger = logging.getLogger(__name__)


class PriceRankingHistory:
    """
    SQLite-based historical storage for price rankings.

    Stores daily snapshots for trend analysis and historical queries.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize historical storage.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.poe_price_checker/price_rankings.db
        """
        if db_path is None:
            db_path = Path.home() / ".poe_price_checker" / "price_rankings.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path

        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

        logger.info(f"PriceRankingHistory initialized: {db_path}")

    def _initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS ranking_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league TEXT NOT NULL,
                category TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(league, category, snapshot_date)
            );

            CREATE TABLE IF NOT EXISTS ranked_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL REFERENCES ranking_snapshots(id) ON DELETE CASCADE,
                rank INTEGER NOT NULL,
                name TEXT NOT NULL,
                chaos_value REAL NOT NULL,
                divine_value REAL,
                base_type TEXT,
                item_class TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_league_date
                ON ranking_snapshots(league, snapshot_date);

            CREATE INDEX IF NOT EXISTS idx_items_snapshot
                ON ranked_items(snapshot_id);

            CREATE INDEX IF NOT EXISTS idx_items_name
                ON ranked_items(name);
        """)
        self.conn.commit()

    def save_snapshot(self, ranking: CategoryRanking, league: str) -> int:
        """
        Save a ranking snapshot to the database.

        Args:
            ranking: CategoryRanking to save
            league: League name

        Returns:
            Snapshot ID
        """
        today = datetime.now(timezone.utc).date().isoformat()

        cursor = self.conn.cursor()

        # Insert or replace snapshot
        cursor.execute("""
            INSERT OR REPLACE INTO ranking_snapshots (league, category, snapshot_date)
            VALUES (?, ?, ?)
        """, (league, ranking.category, today))

        snapshot_id = cursor.lastrowid or 0

        # Delete old items for this snapshot (in case of replace)
        cursor.execute("DELETE FROM ranked_items WHERE snapshot_id = ?", (snapshot_id,))

        # Insert new items
        for item in ranking.items:
            cursor.execute("""
                INSERT INTO ranked_items (snapshot_id, rank, name, chaos_value, divine_value, base_type, item_class)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (snapshot_id, item.rank, item.name, item.chaos_value, item.divine_value, item.base_type, item.item_class))

        self.conn.commit()
        logger.debug(f"Saved snapshot for {ranking.category} ({league}): {len(ranking.items)} items")
        return snapshot_id

    def save_all_snapshots(self, rankings: Dict[str, CategoryRanking], league: str) -> None:
        """Save all rankings as snapshots."""
        for ranking in rankings.values():
            self.save_snapshot(ranking, league)
        logger.info(f"Saved {len(rankings)} category snapshots for {league}")

    def get_item_history(
        self,
        item_name: str,
        league: str,
        days: int = 30,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get price history for a specific item.

        Args:
            item_name: Item name to look up
            league: League name
            days: Number of days of history
            category: Optional category filter

        Returns:
            List of {date, rank, chaos_value, divine_value}
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

        query = """
            SELECT s.snapshot_date, s.category, i.rank, i.chaos_value, i.divine_value
            FROM ranked_items i
            JOIN ranking_snapshots s ON i.snapshot_id = s.id
            WHERE i.name = ? AND s.league = ? AND s.snapshot_date >= ?
        """
        params: List[Any] = [item_name, league, cutoff]

        if category:
            query += " AND s.category = ?"
            params.append(category)

        query += " ORDER BY s.snapshot_date DESC"

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_trending_items(
        self,
        league: str,
        category: str,
        days: int = 7,
        min_change_percent: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """
        Find items with significant price changes.

        Args:
            league: League name
            category: Category to analyze
            days: Days to compare (compares today vs N days ago)
            min_change_percent: Minimum % change to include

        Returns:
            List of {name, old_price, new_price, change_percent, trend}
        """
        today = datetime.now(timezone.utc).date().isoformat()
        past = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

        # Get current prices
        cursor = self.conn.execute("""
            SELECT i.name, i.chaos_value as new_price
            FROM ranked_items i
            JOIN ranking_snapshots s ON i.snapshot_id = s.id
            WHERE s.league = ? AND s.category = ? AND s.snapshot_date = ?
        """, (league, category, today))
        current_prices = {row["name"]: row["new_price"] for row in cursor.fetchall()}

        # Get past prices
        cursor = self.conn.execute("""
            SELECT i.name, i.chaos_value as old_price
            FROM ranked_items i
            JOIN ranking_snapshots s ON i.snapshot_id = s.id
            WHERE s.league = ? AND s.category = ? AND s.snapshot_date = ?
        """, (league, category, past))
        past_prices = {row["name"]: row["old_price"] for row in cursor.fetchall()}

        # Calculate changes
        trending = []
        for name, new_price in current_prices.items():
            old_price = past_prices.get(name)
            if old_price and old_price > 0:
                change = ((new_price - old_price) / old_price) * 100
                if abs(change) >= min_change_percent:
                    trending.append({
                        "name": name,
                        "old_price": old_price,
                        "new_price": new_price,
                        "change_percent": round(change, 1),
                        "trend": "up" if change > 0 else "down",
                    })

        # Sort by absolute change
        trending.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
        return trending

    def get_snapshot_dates(self, league: str, category: Optional[str] = None) -> List[str]:
        """Get all snapshot dates for a league."""
        query = "SELECT DISTINCT snapshot_date FROM ranking_snapshots WHERE league = ?"
        params: List[Any] = [league]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY snapshot_date DESC"

        cursor = self.conn.execute(query, params)
        return [row[0] for row in cursor.fetchall()]

    def get_category_snapshot(
        self,
        league: str,
        category: str,
        date: Optional[str] = None,
    ) -> Optional[CategoryRanking]:
        """
        Get a historical snapshot for a category.

        Args:
            league: League name
            category: Category key
            date: Snapshot date (YYYY-MM-DD). Defaults to latest.

        Returns:
            CategoryRanking if found
        """
        if date is None:
            # Get latest snapshot
            cursor = self.conn.execute("""
                SELECT id, snapshot_date FROM ranking_snapshots
                WHERE league = ? AND category = ?
                ORDER BY snapshot_date DESC LIMIT 1
            """, (league, category))
        else:
            cursor = self.conn.execute("""
                SELECT id, snapshot_date FROM ranking_snapshots
                WHERE league = ? AND category = ? AND snapshot_date = ?
            """, (league, category, date))

        row = cursor.fetchone()
        if not row:
            return None

        snapshot_id = row["id"]

        # Get items
        cursor = self.conn.execute("""
            SELECT rank, name, chaos_value, divine_value, base_type, item_class
            FROM ranked_items WHERE snapshot_id = ?
            ORDER BY rank
        """, (snapshot_id,))

        items = [
            RankedItem(
                rank=r["rank"],
                name=r["name"],
                chaos_value=r["chaos_value"],
                divine_value=r["divine_value"],
                base_type=r["base_type"],
                item_class=r["item_class"],
            )
            for r in cursor.fetchall()
        ]

        display_name = PriceRankingCache.CATEGORIES.get(category, category)
        return CategoryRanking(
            category=category,
            display_name=display_name,
            items=items,
            updated_at=row["snapshot_date"],
        )

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self) -> "PriceRankingHistory":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensures connection is closed."""
        self.close()
