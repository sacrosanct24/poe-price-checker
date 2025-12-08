"""
League Economy History Service.

Stores and retrieves historical economic data for PoE leagues:
- Currency exchange rates (Chaos/Divine/Exalted)
- Top unique item prices
- Milestone snapshots (League Start, Week 1, Month 1, End of League)

Data Sources:
- poe.ninja CSV dumps (historical data)
- Live API snapshots (current league)
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.database import Database

logger = logging.getLogger(__name__)


class LeagueMilestone(Enum):
    """League timeline milestones for economic snapshots."""

    LEAGUE_START = "league_start"  # Day 1-3
    WEEK_1_END = "week_1_end"  # Day 7
    MONTH_1_END = "month_1_end"  # Day 30
    LEAGUE_END = "league_end"  # Final snapshot


@dataclass
class CurrencySnapshot:
    """Currency exchange rate snapshot at a point in time."""

    league: str
    date: datetime
    divine_to_chaos: float
    exalt_to_chaos: Optional[float] = None
    mirror_to_chaos: Optional[float] = None
    annul_to_chaos: Optional[float] = None


@dataclass
class UniqueSnapshot:
    """Top unique item prices at a point in time."""

    league: str
    date: datetime
    item_name: str
    base_type: str
    chaos_value: float
    divine_value: Optional[float] = None
    rank: int = 0  # Rank by value (1 = most expensive)


@dataclass
class LeagueEconomySnapshot:
    """Complete economic snapshot for a league milestone."""

    league: str
    milestone: LeagueMilestone
    snapshot_date: datetime
    divine_to_chaos: float
    exalt_to_chaos: Optional[float] = None
    top_uniques: List[UniqueSnapshot] = field(default_factory=list)

    @property
    def display_milestone(self) -> str:
        """Human-readable milestone name."""
        names = {
            LeagueMilestone.LEAGUE_START: "League Start",
            LeagueMilestone.WEEK_1_END: "Week 1",
            LeagueMilestone.MONTH_1_END: "Month 1",
            LeagueMilestone.LEAGUE_END: "End of League",
        }
        return names.get(self.milestone, self.milestone.value)


class LeagueEconomyService:
    """
    Service for managing historical league economy data.

    Usage:
        service = LeagueEconomyService(db)

        # Import from poe.ninja CSV dump
        service.import_currency_csv(csv_content, "Settlers")

        # Save milestone snapshot
        service.save_milestone_snapshot(snapshot)

        # Query historical data
        snapshots = service.get_league_snapshots("Settlers")
    """

    def __init__(self, db: "Database"):
        """Initialize the service with database connection."""
        self._db = db

    # ------------------------------------------------------------------
    # CSV Import (poe.ninja dumps)
    # ------------------------------------------------------------------

    def import_currency_csv(
        self,
        csv_content: str,
        league: str,
        delimiter: str = ";",
    ) -> int:
        """
        Import currency exchange data from poe.ninja CSV dump.

        CSV format (semicolon-delimited):
            League; Date; Get; Pay; Value; Confidence

        Example:
            Abyss; 2017-12-10; Exalted Orb; Chaos Orb; 35.92556; High

        Args:
            csv_content: Raw CSV content string
            league: League name to import (filters CSV)
            delimiter: CSV delimiter (default semicolon for poe.ninja)

        Returns:
            Number of rows imported
        """
        rows_imported = 0

        reader = csv.DictReader(
            io.StringIO(csv_content),
            delimiter=delimiter,
        )

        for row in reader:
            try:
                row_league = row.get("League", "").strip()
                if row_league != league:
                    continue

                date_str = row.get("Date", "").strip()
                get_currency = row.get("Get", "").strip()
                pay_currency = row.get("Pay", "").strip()
                value_str = row.get("Value", "").strip()

                if not all([date_str, get_currency, pay_currency, value_str]):
                    continue

                # Parse date
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    continue

                # Parse value
                try:
                    value = float(value_str)
                except ValueError:
                    continue

                # Only import rates where Pay is Chaos Orb
                if pay_currency != "Chaos Orb":
                    continue

                # Store the rate
                self._db._execute(
                    """
                    INSERT INTO league_economy_rates
                        (league, currency_name, rate_date, chaos_value)
                    VALUES (?, ?, ?, ?)
                    """,
                    (league, get_currency, date.isoformat(), value),
                )
                rows_imported += 1

            except Exception as e:
                logger.warning(f"Failed to import row: {e}")
                continue

        logger.info(f"Imported {rows_imported} currency rates for {league}")
        return rows_imported

    def import_item_csv(
        self,
        csv_content: str,
        league: str,
        item_type: str = "UniqueAccessory",
        delimiter: str = ";",
    ) -> int:
        """
        Import item price data from poe.ninja CSV dump.

        CSV format varies by item type, typically includes:
            League; Date; Name; BaseType; Value; ...

        Args:
            csv_content: Raw CSV content string
            league: League name to import
            item_type: Type of items (UniqueAccessory, UniqueWeapon, etc.)
            delimiter: CSV delimiter

        Returns:
            Number of rows imported
        """
        rows_imported = 0

        reader = csv.DictReader(
            io.StringIO(csv_content),
            delimiter=delimiter,
        )

        for row in reader:
            try:
                row_league = row.get("League", "").strip()
                if row_league != league:
                    continue

                date_str = row.get("Date", "").strip()
                item_name = row.get("Name", "").strip()
                base_type = row.get("BaseType", "").strip()
                value_str = row.get("Value", "").strip()

                if not all([date_str, item_name, value_str]):
                    continue

                # Parse date
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    continue

                # Parse value
                try:
                    value = float(value_str)
                except ValueError:
                    continue

                # Store the item price
                self._db._execute(
                    """
                    INSERT INTO league_economy_items
                        (league, item_name, base_type, item_type, rate_date, chaos_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (league, item_name, base_type, item_type, date.isoformat(), value),
                )
                rows_imported += 1

            except Exception as e:
                logger.warning(f"Failed to import item row: {e}")
                continue

        logger.info(f"Imported {rows_imported} item prices for {league}")
        return rows_imported

    def import_item_csv_file(
        self,
        file_path: Path,
        league: str,
        item_type: str = "UniqueItem",
        delimiter: str = ";",
        batch_size: int = 10000,
        progress_callback: Optional[callable] = None,
    ) -> int:
        """
        Import item prices from a large CSV file using streaming.

        Optimized for large files (100MB+):
        - Reads file line-by-line (no full load into memory)
        - Uses batch inserts for efficiency
        - Reports progress via callback

        Args:
            file_path: Path to CSV file
            league: League name to import
            item_type: Item type category
            delimiter: CSV delimiter
            batch_size: Rows per batch commit
            progress_callback: Optional callback(rows_imported, total_lines)

        Returns:
            Number of rows imported
        """
        rows_imported = 0
        batch = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            for row in reader:
                try:
                    row_league = row.get("League", "").strip()
                    if row_league != league:
                        continue

                    date_str = row.get("Date", "").strip()
                    item_name = row.get("Name", "").strip()
                    base_type = row.get("BaseType", "").strip()
                    value_str = row.get("Value", "").strip()

                    if not all([date_str, item_name, value_str]):
                        continue

                    # Parse date
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        continue

                    # Parse value
                    try:
                        value = float(value_str)
                    except ValueError:
                        continue

                    # Add to batch
                    batch.append((
                        league, item_name, base_type, item_type,
                        date.isoformat(), value
                    ))
                    rows_imported += 1

                    # Commit batch
                    if len(batch) >= batch_size:
                        self._db.conn.executemany(
                            """
                            INSERT INTO league_economy_items
                                (league, item_name, base_type, item_type, rate_date, chaos_value)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            batch,
                        )
                        self._db.conn.commit()
                        batch = []
                        if progress_callback:
                            progress_callback(rows_imported)

                except Exception as e:
                    logger.warning(f"Failed to import item row: {e}")
                    continue

            # Commit remaining batch
            if batch:
                self._db.conn.executemany(
                    """
                    INSERT INTO league_economy_items
                        (league, item_name, base_type, item_type, rate_date, chaos_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    batch,
                )
                self._db.conn.commit()

        logger.info(f"Imported {rows_imported} item prices for {league} from {file_path.name}")
        return rows_imported

    def import_currency_csv_file(
        self,
        file_path: Path,
        league: str,
        delimiter: str = ";",
        batch_size: int = 10000,
        progress_callback: Optional[callable] = None,
    ) -> int:
        """
        Import currency rates from a large CSV file using streaming.

        Args:
            file_path: Path to CSV file
            league: League name to import
            delimiter: CSV delimiter
            batch_size: Rows per batch commit
            progress_callback: Optional callback(rows_imported)

        Returns:
            Number of rows imported
        """
        rows_imported = 0
        batch = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            for row in reader:
                try:
                    row_league = row.get("League", "").strip()
                    if row_league != league:
                        continue

                    date_str = row.get("Date", "").strip()
                    get_currency = row.get("Get", "").strip()
                    pay_currency = row.get("Pay", "").strip()
                    value_str = row.get("Value", "").strip()

                    if not all([date_str, get_currency, pay_currency, value_str]):
                        continue

                    # Only import rates where Pay is Chaos Orb
                    if pay_currency != "Chaos Orb":
                        continue

                    # Parse date
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        continue

                    # Parse value
                    try:
                        value = float(value_str)
                    except ValueError:
                        continue

                    # Add to batch
                    batch.append((league, get_currency, date.isoformat(), value))
                    rows_imported += 1

                    # Commit batch
                    if len(batch) >= batch_size:
                        self._db.conn.executemany(
                            """
                            INSERT INTO league_economy_rates
                                (league, currency_name, rate_date, chaos_value)
                            VALUES (?, ?, ?, ?)
                            """,
                            batch,
                        )
                        self._db.conn.commit()
                        batch = []
                        if progress_callback:
                            progress_callback(rows_imported)

                except Exception as e:
                    logger.warning(f"Failed to import row: {e}")
                    continue

            # Commit remaining batch
            if batch:
                self._db.conn.executemany(
                    """
                    INSERT INTO league_economy_rates
                        (league, currency_name, rate_date, chaos_value)
                    VALUES (?, ?, ?, ?)
                    """,
                    batch,
                )
                self._db.conn.commit()

        logger.info(f"Imported {rows_imported} currency rates for {league} from {file_path.name}")
        return rows_imported

    # ------------------------------------------------------------------
    # Milestone Snapshots
    # ------------------------------------------------------------------

    def save_milestone_snapshot(
        self,
        snapshot: LeagueEconomySnapshot,
    ) -> int:
        """
        Save a milestone economic snapshot.

        Args:
            snapshot: Complete economic snapshot

        Returns:
            Row ID of saved snapshot
        """
        # Save main snapshot
        cursor = self._db._execute(
            """
            INSERT INTO league_economy_snapshots
                (league, milestone, snapshot_date, divine_to_chaos, exalt_to_chaos)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                snapshot.league,
                snapshot.milestone.value,
                snapshot.snapshot_date.isoformat(),
                snapshot.divine_to_chaos,
                snapshot.exalt_to_chaos,
            ),
        )
        snapshot_id = cursor.lastrowid or 0

        # Save top uniques
        for unique in snapshot.top_uniques:
            self._db._execute(
                """
                INSERT INTO league_economy_top_uniques
                    (snapshot_id, item_name, base_type, chaos_value, divine_value, rank)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    unique.item_name,
                    unique.base_type,
                    unique.chaos_value,
                    unique.divine_value,
                    unique.rank,
                ),
            )

        logger.info(
            f"Saved {snapshot.display_milestone} snapshot for {snapshot.league}"
        )
        return snapshot_id

    def get_league_snapshots(
        self,
        league: str,
    ) -> List[LeagueEconomySnapshot]:
        """
        Get all milestone snapshots for a league.

        Args:
            league: League name

        Returns:
            List of snapshots ordered by milestone
        """
        rows = self._db._execute_fetchall(
            """
            SELECT id, league, milestone, snapshot_date, divine_to_chaos, exalt_to_chaos
            FROM league_economy_snapshots
            WHERE league = ?
            ORDER BY snapshot_date ASC
            """,
            (league,),
        )

        snapshots = []
        for row in rows:
            # Load top uniques for this snapshot
            unique_rows = self._db._execute_fetchall(
                """
                SELECT item_name, base_type, chaos_value, divine_value, rank
                FROM league_economy_top_uniques
                WHERE snapshot_id = ?
                ORDER BY rank ASC
                """,
                (row["id"],),
            )

            uniques = [
                UniqueSnapshot(
                    league=league,
                    date=datetime.fromisoformat(row["snapshot_date"]),
                    item_name=u["item_name"],
                    base_type=u["base_type"],
                    chaos_value=u["chaos_value"],
                    divine_value=u["divine_value"],
                    rank=u["rank"],
                )
                for u in unique_rows
            ]

            snapshot = LeagueEconomySnapshot(
                league=row["league"],
                milestone=LeagueMilestone(row["milestone"]),
                snapshot_date=datetime.fromisoformat(row["snapshot_date"]),
                divine_to_chaos=row["divine_to_chaos"],
                exalt_to_chaos=row["exalt_to_chaos"],
                top_uniques=uniques,
            )
            snapshots.append(snapshot)

        return snapshots

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_currency_rate_at_date(
        self,
        league: str,
        currency: str,
        date: datetime,
    ) -> Optional[float]:
        """
        Get currency rate closest to a specific date.

        Args:
            league: League name
            currency: Currency name (e.g., "Divine Orb")
            date: Target date

        Returns:
            Chaos value or None
        """
        row = self._db._execute_fetchone(
            """
            SELECT chaos_value
            FROM league_economy_rates
            WHERE league = ? AND currency_name = ?
            ORDER BY ABS(julianday(rate_date) - julianday(?)) ASC
            LIMIT 1
            """,
            (league, currency, date.isoformat()),
        )

        return row["chaos_value"] if row else None

    def get_divine_rate_history(
        self,
        league: str,
    ) -> List[Dict[str, Any]]:
        """
        Get Divine Orb rate history for a league.

        Args:
            league: League name

        Returns:
            List of {date, chaos_value} records
        """
        rows = self._db._execute_fetchall(
            """
            SELECT rate_date, chaos_value
            FROM league_economy_rates
            WHERE league = ? AND currency_name = 'Divine Orb'
            ORDER BY rate_date ASC
            """,
            (league,),
        )

        return [
            {
                "date": datetime.fromisoformat(row["rate_date"]),
                "chaos_value": row["chaos_value"],
            }
            for row in rows
        ]

    def get_top_uniques_at_date(
        self,
        league: str,
        date: datetime,
        limit: int = 10,
    ) -> List[UniqueSnapshot]:
        """
        Get top unique prices closest to a specific date.

        Args:
            league: League name
            date: Target date
            limit: Max items to return

        Returns:
            List of UniqueSnapshot ordered by value descending
        """
        rows = self._db._execute_fetchall(
            """
            SELECT item_name, base_type, chaos_value, rate_date
            FROM league_economy_items
            WHERE league = ?
              AND rate_date = (
                  SELECT rate_date FROM league_economy_items
                  WHERE league = ?
                  ORDER BY ABS(julianday(rate_date) - julianday(?)) ASC
                  LIMIT 1
              )
            ORDER BY chaos_value DESC
            LIMIT ?
            """,
            (league, league, date.isoformat(), limit),
        )

        return [
            UniqueSnapshot(
                league=league,
                date=datetime.fromisoformat(row["rate_date"]),
                item_name=row["item_name"],
                base_type=row["base_type"],
                chaos_value=row["chaos_value"],
                rank=idx + 1,
            )
            for idx, row in enumerate(rows)
        ]

    def get_available_leagues(self) -> List[str]:
        """
        Get list of leagues with economy data.

        Returns:
            List of league names
        """
        rows = self._db._execute_fetchall(
            """
            SELECT DISTINCT league FROM league_economy_rates
            UNION
            SELECT DISTINCT league FROM league_economy_snapshots
            ORDER BY league DESC
            """,
            (),
        )
        return [row["league"] for row in rows]

    def get_league_date_range(
        self,
        league: str,
    ) -> Optional[Dict[str, datetime]]:
        """
        Get the date range of data for a league.

        Args:
            league: League name

        Returns:
            Dict with 'start' and 'end' dates or None
        """
        row = self._db._execute_fetchone(
            """
            SELECT MIN(rate_date) as start_date, MAX(rate_date) as end_date
            FROM league_economy_rates
            WHERE league = ?
            """,
            (league,),
        )

        if row and row["start_date"]:
            return {
                "start": datetime.fromisoformat(row["start_date"]),
                "end": datetime.fromisoformat(row["end_date"]),
            }
        return None


    # ------------------------------------------------------------------
    # Live Data Fetching (poe.ninja API)
    # ------------------------------------------------------------------

    def fetch_and_store_snapshot(
        self,
        league: str,
        milestone: Optional[LeagueMilestone] = None,
    ) -> Optional[LeagueEconomySnapshot]:
        """
        Fetch current economy data from poe.ninja and store it.

        Args:
            league: League name (e.g., "Settlers")
            milestone: Optional milestone to tag this snapshot

        Returns:
            LeagueEconomySnapshot or None if fetch failed
        """
        try:
            from data_sources.poe_ninja_client import get_ninja_client

            client = get_ninja_client()

            # Fetch currency rates
            currency_prices = client.get_currency_prices(league, "Currency")

            divine_rate = 1.0
            exalt_rate = None

            for p in currency_prices:
                name_lower = p.name.lower()
                if name_lower == "divine orb":
                    divine_rate = p.chaos_value
                elif name_lower == "exalted orb":
                    exalt_rate = p.chaos_value

            # Store currency rate
            self._db._execute(
                """
                INSERT INTO league_economy_rates
                    (league, currency_name, rate_date, chaos_value)
                VALUES (?, ?, ?, ?)
                """,
                (league, "Divine Orb", datetime.now().isoformat(), divine_rate),
            )

            if exalt_rate:
                self._db._execute(
                    """
                    INSERT INTO league_economy_rates
                        (league, currency_name, rate_date, chaos_value)
                    VALUES (?, ?, ?, ?)
                    """,
                    (league, "Exalted Orb", datetime.now().isoformat(), exalt_rate),
                )

            # Fetch top uniques
            top_uniques = []
            for item_type in ["UniqueWeapon", "UniqueArmour", "UniqueAccessory"]:
                prices = client.get_item_prices(league, item_type)
                for p in prices:
                    if p.chaos_value > 0:
                        top_uniques.append(
                            UniqueSnapshot(
                                league=league,
                                date=datetime.now(),
                                item_name=p.name,
                                base_type=p.base_type,
                                chaos_value=p.chaos_value,
                                divine_value=p.divine_value,
                            )
                        )

                    # Store in items table
                    self._db._execute(
                        """
                        INSERT INTO league_economy_items
                            (league, item_name, base_type, item_type, rate_date, chaos_value)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            league,
                            p.name,
                            p.base_type,
                            item_type,
                            datetime.now().isoformat(),
                            p.chaos_value,
                        ),
                    )

            # Sort and rank top uniques
            top_uniques.sort(key=lambda x: x.chaos_value, reverse=True)
            for i, u in enumerate(top_uniques[:10]):
                u.rank = i + 1

            # Create snapshot
            snapshot = LeagueEconomySnapshot(
                league=league,
                milestone=milestone or LeagueMilestone.LEAGUE_START,
                snapshot_date=datetime.now(),
                divine_to_chaos=divine_rate,
                exalt_to_chaos=exalt_rate,
                top_uniques=top_uniques[:10],
            )

            # Save milestone snapshot if tagged
            if milestone:
                self.save_milestone_snapshot(snapshot)

            logger.info(
                f"Fetched economy snapshot for {league}: "
                f"Divine={divine_rate:.0f}c, {len(top_uniques)} uniques"
            )
            return snapshot

        except Exception as e:
            logger.error(f"Failed to fetch economy snapshot: {e}")
            return None

    def fetch_current_rates(self, league: str) -> Dict[str, float]:
        """
        Fetch current currency rates from poe.ninja.

        Args:
            league: League name

        Returns:
            Dict with currency names as keys and chaos values
        """
        try:
            from data_sources.poe_ninja_client import get_ninja_client

            client = get_ninja_client()
            prices = client.get_currency_prices(league, "Currency")

            rates = {}
            for p in prices:
                rates[p.name] = p.chaos_value

            return rates

        except Exception as e:
            logger.error(f"Failed to fetch current rates: {e}")
            return {}

    # ------------------------------------------------------------------
    # Aggregation Methods (Pre-compute summaries)
    # ------------------------------------------------------------------

    def aggregate_league(
        self,
        league: str,
        is_finalized: bool = True,
        top_items_limit: int = 100,
    ) -> bool:
        """
        Pre-aggregate all economy data for a league into summary tables.

        This computes currency stats, top items, and overall league summary
        and stores them for fast retrieval. Call this once per league after
        importing historical data.

        Args:
            league: League name to aggregate
            is_finalized: True if league is over (data won't change)
            top_items_limit: Number of top items to store (default 100)

        Returns:
            True if aggregation succeeded
        """
        try:
            logger.info(f"Aggregating economy data for {league}...")

            # Aggregate currency data
            self._aggregate_currency_summary(league)

            # Aggregate top items
            self._aggregate_top_items(league, limit=top_items_limit)

            # Create league summary
            self._aggregate_league_summary(league, is_finalized)

            logger.info(f"Aggregation complete for {league}")
            return True

        except Exception as e:
            logger.error(f"Failed to aggregate {league}: {e}")
            return False

    def _aggregate_currency_summary(self, league: str) -> int:
        """Aggregate currency statistics for a league."""
        # Delete existing summary for this league
        self._db._execute(
            "DELETE FROM league_currency_summary WHERE league = ?",
            (league,),
        )

        # Get distinct currencies for this league
        currencies = self._db._execute_fetchall(
            """
            SELECT DISTINCT currency_name FROM league_economy_rates
            WHERE league = ?
            """,
            (league,),
        )

        count = 0
        for row in currencies:
            currency = row["currency_name"]

            # Get aggregated stats
            stats = self._db._execute_fetchone(
                """
                SELECT
                    MIN(chaos_value) as min_val,
                    MAX(chaos_value) as max_val,
                    AVG(chaos_value) as avg_val,
                    COUNT(*) as data_points
                FROM league_economy_rates
                WHERE league = ? AND currency_name = ?
                """,
                (league, currency),
            )

            # Get start value (first date)
            start = self._db._execute_fetchone(
                """
                SELECT chaos_value FROM league_economy_rates
                WHERE league = ? AND currency_name = ?
                ORDER BY rate_date ASC LIMIT 1
                """,
                (league, currency),
            )

            # Get end value (last date)
            end = self._db._execute_fetchone(
                """
                SELECT chaos_value FROM league_economy_rates
                WHERE league = ? AND currency_name = ?
                ORDER BY rate_date DESC LIMIT 1
                """,
                (league, currency),
            )

            # Get peak date (date of max value)
            peak = self._db._execute_fetchone(
                """
                SELECT rate_date FROM league_economy_rates
                WHERE league = ? AND currency_name = ?
                ORDER BY chaos_value DESC LIMIT 1
                """,
                (league, currency),
            )

            # Insert summary
            self._db._execute(
                """
                INSERT INTO league_currency_summary
                    (league, currency_name, min_value, max_value, avg_value,
                     start_value, end_value, peak_date, data_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    league,
                    currency,
                    stats["min_val"],
                    stats["max_val"],
                    stats["avg_val"],
                    start["chaos_value"] if start else None,
                    end["chaos_value"] if end else None,
                    peak["rate_date"] if peak else None,
                    stats["data_points"],
                ),
            )
            count += 1

        logger.info(f"Aggregated {count} currency summaries for {league}")
        return count

    def _aggregate_top_items(self, league: str, limit: int = 100) -> int:
        """Aggregate top unique items for a league."""
        # Delete existing summary for this league
        self._db._execute(
            "DELETE FROM league_top_items_summary WHERE league = ?",
            (league,),
        )

        # Get top items by average value (with minimum 10 data points)
        items = self._db._execute_fetchall(
            """
            SELECT
                item_name,
                base_type,
                AVG(chaos_value) as avg_val,
                MIN(chaos_value) as min_val,
                MAX(chaos_value) as max_val,
                COUNT(*) as data_points
            FROM league_economy_items
            WHERE league = ?
            GROUP BY item_name
            HAVING COUNT(*) >= 10
            ORDER BY avg_val DESC
            LIMIT ?
            """,
            (league, limit),
        )

        count = 0
        for idx, row in enumerate(items):
            self._db._execute(
                """
                INSERT INTO league_top_items_summary
                    (league, item_name, base_type, avg_value, min_value,
                     max_value, data_points, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    league,
                    row["item_name"],
                    row["base_type"],
                    row["avg_val"],
                    row["min_val"],
                    row["max_val"],
                    row["data_points"],
                    idx + 1,
                ),
            )
            count += 1

        logger.info(f"Aggregated {count} top items for {league}")
        return count

    def _aggregate_league_summary(self, league: str, is_finalized: bool) -> None:
        """Create or update league summary."""
        # Delete existing summary
        self._db._execute(
            "DELETE FROM league_economy_summary WHERE league = ?",
            (league,),
        )

        # Get date range and counts from currency data
        currency_stats = self._db._execute_fetchone(
            """
            SELECT
                MIN(rate_date) as first_date,
                MAX(rate_date) as last_date,
                COUNT(*) as total_snapshots
            FROM league_economy_rates
            WHERE league = ?
            """,
            (league,),
        )

        # Get item count
        item_stats = self._db._execute_fetchone(
            """
            SELECT COUNT(*) as total_items
            FROM league_economy_items
            WHERE league = ?
            """,
            (league,),
        )

        if currency_stats and currency_stats["first_date"]:
            self._db._execute(
                """
                INSERT INTO league_economy_summary
                    (league, first_date, last_date, total_currency_snapshots,
                     total_item_snapshots, is_finalized, computed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    league,
                    currency_stats["first_date"],
                    currency_stats["last_date"],
                    currency_stats["total_snapshots"],
                    item_stats["total_items"] if item_stats else 0,
                    1 if is_finalized else 0,
                    datetime.now().isoformat(),
                ),
            )

        logger.info(f"Created league summary for {league}")

    # ------------------------------------------------------------------
    # Fast Query Methods (from summary tables)
    # ------------------------------------------------------------------

    def get_currency_summary(
        self,
        league: str,
        currencies: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get pre-aggregated currency statistics for a league.

        Args:
            league: League name
            currencies: Optional list of currencies to filter

        Returns:
            List of currency summary dictionaries
        """
        if currencies:
            # placeholders are constructed from list length, all values parameterized
            placeholders = ",".join("?" * len(currencies))
            rows = self._db._execute_fetchall(
                f"""  # nosec
                SELECT * FROM league_currency_summary
                WHERE league = ? AND currency_name IN ({placeholders})
                ORDER BY avg_value DESC
                """,
                (league, *currencies),
            )
        else:
            rows = self._db._execute_fetchall(
                """
                SELECT * FROM league_currency_summary
                WHERE league = ?
                ORDER BY avg_value DESC
                """,
                (league,),
            )

        return [dict(row) for row in rows]

    def get_top_items_summary(
        self,
        league: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get pre-aggregated top items for a league.

        Args:
            league: League name
            limit: Number of items to return

        Returns:
            List of top item dictionaries ordered by rank
        """
        rows = self._db._execute_fetchall(
            """
            SELECT * FROM league_top_items_summary
            WHERE league = ?
            ORDER BY rank ASC
            LIMIT ?
            """,
            (league, limit),
        )

        return [dict(row) for row in rows]

    def get_league_summary(self, league: str) -> Optional[Dict[str, Any]]:
        """
        Get pre-aggregated league summary.

        Args:
            league: League name

        Returns:
            League summary dictionary or None
        """
        row = self._db._execute_fetchone(
            """
            SELECT * FROM league_economy_summary
            WHERE league = ?
            """,
            (league,),
        )

        return dict(row) if row else None

    def is_league_aggregated(self, league: str) -> bool:
        """Check if a league has been aggregated."""
        row = self._db._execute_fetchone(
            "SELECT 1 FROM league_economy_summary WHERE league = ?",
            (league,),
        )
        return row is not None

    def get_aggregated_leagues(self) -> List[str]:
        """Get list of leagues with pre-aggregated data."""
        rows = self._db._execute_fetchall(
            "SELECT league FROM league_economy_summary ORDER BY league DESC",
            (),
        )
        return [row["league"] for row in rows]


# Singleton instance
_service_instance: Optional[LeagueEconomyService] = None


def get_league_economy_service(db: "Database") -> LeagueEconomyService:
    """Get or create the league economy service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = LeagueEconomyService(db)
    return _service_instance


def reset_league_economy_service() -> None:
    """Reset the singleton (for testing)."""
    global _service_instance
    _service_instance = None
