"""
Price repository for price history and price checking operations.

Handles database operations for:
- Price history snapshots
- Price checks and quotes
- Statistical analysis of pricing data
"""
from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.database.repositories.base_repository import BaseRepository
from core.game_version import GameVersion


class PriceRepository(BaseRepository):
    """Repository for price-related database operations."""

    def add_price_snapshot(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        chaos_value: float,
        item_base_type: Optional[str] = None,
        divine_value: Optional[float] = None,
    ) -> int:
        """
        Insert a price history snapshot and return its ID.

        Args:
            game_version: Game version (POE1 or POE2)
            league: League name
            item_name: Name of the item
            chaos_value: Price in chaos orbs
            item_base_type: Optional base type
            divine_value: Optional price in divine orbs

        Returns:
            The ID of the inserted record
        """
        cursor = self._execute(
            """
            INSERT INTO price_history
                (game_version, league, item_name, item_base_type,
                 chaos_value, divine_value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                game_version.value,
                league,
                item_name,
                item_base_type,
                chaos_value,
                divine_value,
            ),
        )
        return cursor.lastrowid or 0

    def create_price_check(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        item_base_type: Optional[str],
        source: Optional[str] = None,
        query_hash: Optional[str] = None,
    ) -> int:
        """
        Insert a new price_checks row and return its ID.

        Args:
            game_version: Game version (POE1 or POE2)
            league: League name
            item_name: Name of the item
            item_base_type: Base type of the item
            source: Data source (e.g., "poe.ninja", "trade")
            query_hash: Hash of the query for deduplication

        Returns:
            The ID of the inserted record
        """
        cursor = self._execute(
            """
            INSERT INTO price_checks (
                game_version,
                league,
                item_name,
                item_base_type,
                source,
                query_hash
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                game_version.value,
                league,
                item_name,
                item_base_type,
                source,
                query_hash,
            ),
        )
        return cursor.lastrowid or 0

    def add_price_quotes_batch(
        self,
        price_check_id: int,
        quotes: List[Dict[str, Any]],
    ) -> None:
        """
        Insert a batch of raw price quotes for a given price_check_id.

        Each quote dict may contain:
            - source (str)
            - price_chaos (float)
            - original_currency (str)
            - stack_size (int)
            - listing_id (str)
            - seller_account (str)
            - listed_at (str or datetime)

        Args:
            price_check_id: The ID of the parent price check
            quotes: List of quote dictionaries
        """
        rows: List[tuple] = []

        for q in quotes:
            source = q.get("source") or "unknown"
            price_chaos = q.get("price_chaos")
            if price_chaos is None:
                # Skip invalid rows rather than failing the whole batch
                continue

            original_currency = q.get("original_currency")
            stack_size = q.get("stack_size")
            listing_id = q.get("listing_id")
            seller_account = q.get("seller_account")
            listed_at = q.get("listed_at")

            # Normalize listed_at to string if it's a datetime
            listed_at_str: Optional[str]
            if isinstance(listed_at, datetime):
                listed_at_str = listed_at.isoformat(timespec="seconds")
            elif isinstance(listed_at, str):
                listed_at_str = listed_at
            else:
                listed_at_str = None

            rows.append(
                (
                    price_check_id,
                    source,
                    float(price_chaos),
                    original_currency,
                    stack_size,
                    listing_id,
                    seller_account,
                    listed_at_str,
                )
            )

        if not rows:
            return

        with self.transaction() as conn:
            conn.executemany(
                """
                INSERT INTO price_quotes (
                    price_check_id,
                    source,
                    price_chaos,
                    original_currency,
                    stack_size,
                    listing_id,
                    seller_account,
                    listed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def get_price_stats_for_check(self, price_check_id: int) -> Dict[str, Any]:
        """
        Compute robust statistics for all price_quotes belonging to a given price_check_id.

        Returns a dict with:
            - count
            - min
            - max
            - mean
            - median
            - p25
            - p75
            - trimmed_mean (middle 50%)
            - stddev (population-style; 0 if < 2 samples)

        Args:
            price_check_id: The ID of the price check to analyze

        Returns:
            Dictionary of statistics
        """
        rows = self._execute_fetchall(
            """
            SELECT price_chaos
            FROM price_quotes
            WHERE price_check_id = ?
            ORDER BY price_chaos ASC
            """,
            (price_check_id,),
        )
        prices = [float(row[0]) for row in rows if row[0] is not None]

        if not prices:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
                "p25": None,
                "p75": None,
                "trimmed_mean": None,
                "stddev": None,
            }

        prices.sort()
        count = len(prices)
        p_min = prices[0]
        p_max = prices[-1]
        mean = sum(prices) / count

        median = statistics.median(prices)

        # percentiles (simple interpolation)
        def percentile(vals: List[float], q: float) -> float:
            if not vals:
                return float("nan")
            idx = (len(vals) - 1) * q
            lo = int(idx)
            hi = min(lo + 1, len(vals) - 1)
            frac = idx - lo
            return vals[lo] * (1 - frac) + vals[hi] * frac

        p25 = percentile(prices, 0.25)
        p75 = percentile(prices, 0.75)

        # trimmed mean: middle 50% (drop lowest 25% and highest 25%)
        if count >= 4:
            start = int(count * 0.25)
            end = max(start + 1, int(count * 0.75))
            trimmed_slice = prices[start:end]
            trimmed_mean = sum(trimmed_slice) / len(trimmed_slice)
        else:
            trimmed_mean = mean

        # simple stddev (population); 0 if < 2 samples
        if count >= 2:
            mean_val = mean
            var = sum((p - mean_val) ** 2 for p in prices) / count
            stddev = var ** 0.5
        else:
            stddev = 0.0

        return {
            "count": count,
            "min": p_min,
            "max": p_max,
            "mean": mean,
            "median": median,
            "p25": p25,
            "p75": p75,
            "trimmed_mean": trimmed_mean,
            "stddev": stddev,
        }

    def get_latest_price_stats_for_item(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        days: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """
        Get robust price stats for the most recent price_check row for a given item
        within the last N days.

        Args:
            game_version: Game version (POE1 or POE2)
            league: League name
            item_name: Name of the item
            days: Number of days to look back

        Returns:
            Statistics dictionary with price_check_id, or None if no checks found
        """
        row = self._execute_fetchone(
            """
            SELECT id
            FROM price_checks
            WHERE game_version = ?
              AND league = ?
              AND item_name = ?
              AND checked_at >= datetime('now', ?)
            ORDER BY checked_at DESC
            LIMIT 1
            """,
            (game_version.value, league, item_name, f"-{int(days)} days"),
        )
        if row is None:
            return None

        price_check_id = row[0]
        stats = self.get_price_stats_for_check(price_check_id)
        stats["price_check_id"] = price_check_id
        return stats

    def get_price_history(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        days: int,
    ) -> List[Dict[str, Any]]:
        """
        Return price snapshots within the last N days, ordered ascending.

        Args:
            game_version: Game version (POE1 or POE2)
            league: League name
            item_name: Name of the item
            days: Number of days of history

        Returns:
            List of price history records
        """
        rows = self._execute_fetchall(
            """
            SELECT * FROM price_history
            WHERE game_version = ?
              AND league = ?
              AND item_name = ?
              AND recorded_at >= datetime('now', ?)
            ORDER BY recorded_at ASC
            """,
            (
                game_version.value,
                league,
                item_name,
                f"-{days} days",
            ),
        )
        return [dict(row) for row in rows]
