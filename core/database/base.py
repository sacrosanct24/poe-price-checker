"""
SQLite-backed persistence layer for the PoE Price Checker.

Responsibilities:
- Checked items (recent item lookups)
- Sales tracking (listed → sold/unsold)
- Price history snapshots
- Price checks & raw quotes (for robust pricing)
- Plugin state (enabled/config)
- Aggregate statistics
- Schema initialization + versioning

Thread Safety:
- Uses a threading.Lock for all database operations
- Safe to use from multiple threads (GUI, background workers, etc.)
"""
from __future__ import annotations

import logging
import sqlite3
import statistics
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, cast

from core.game_version import GameVersion

from core.database.repositories.checked_items_repository import CheckedItemsRepository
from core.database.repositories.currency_repository import CurrencyRepository
from core.database.repositories.plugin_repository import PluginRepository
from core.database.repositories.sales_repository import SalesRepository
from core.database.repositories.stats_repository import StatsRepository
from core.database.schema import (
    SCHEMA_VERSION,
    CREATE_SCHEMA_SQL,
    MIGRATION_V2_SQL,
    MIGRATION_V3_SQL,
    MIGRATION_V4_CURRENCY_RATES_SQL,
    MIGRATION_V5_SQL,
    MIGRATION_V6_SQL,
    MIGRATION_V7_SQL,
    MIGRATION_V8_SQL,
    MIGRATION_V9_SQL,
    MIGRATION_V10_SQL,
    MIGRATION_V11_SQL,
    ALLOWED_MIGRATION_COLUMNS,
)

logger = logging.getLogger(__name__)


class Database:
    """
    Manages all persistent application data through SQLite.

    A Database instance is associated with one database file.
    The schema includes:
    - checked_items
    - sales
    - price_history
    - price_checks
    - price_quotes
    - plugin_state
    - stats views (via queries)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Create a Database instance.

        If db_path is None, use the default location:
        ~/.poe_price_checker/data.db
        """
        if db_path is None:
            db_path = Path.home() / ".poe_price_checker" / "data.db"

        self.db_path = db_path

        # Thread safety lock for all database operations
        self._lock = threading.RLock()

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        logger.info(f"Database initialized: {db_path}")

        # Initialize or migrate schema
        self._initialize_schema()

        # Initialize repositories
        self._checked_items_repo = CheckedItemsRepository(self.conn, self._lock)
        self._currency_repo = CurrencyRepository(self.conn, self._lock)
        self._plugin_repo = PluginRepository(self.conn, self._lock)
        self._sales_repo = SalesRepository(self.conn, self._lock)
        self._stats_repo = StatsRepository(self.conn, self._lock)

    # ----------------------------------------------------------------------
    # Context manager for transactions
    # ----------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Provide a transaction scope with thread safety:

            with db.transaction() as conn:
                conn.execute(...)

        Commits on success, rolls back on error.
        Thread-safe: acquires lock for entire transaction.
        """
        with self._lock:
            try:
                yield self.conn
                self.conn.commit()
            except Exception as exc:
                self.conn.rollback()
                logger.error(f"Transaction failed: {exc}")
                raise

    def _execute(
        self, sql: str, params: tuple = (), commit: bool = True
    ) -> sqlite3.Cursor:
        """
        Thread-safe execute helper for single operations.

        Args:
            sql: SQL statement to execute
            params: Parameters for the SQL statement
            commit: Whether to commit after execution (default True)

        Returns:
            The cursor from the execute call
        """
        with self._lock:
            cursor = self.conn.execute(sql, params)
            if commit:
                self.conn.commit()
            return cursor

    def _execute_fetchone(
        self, sql: str, params: tuple = ()
    ) -> Optional[sqlite3.Row]:
        """Thread-safe fetchone helper."""
        with self._lock:
            cursor = self.conn.execute(sql, params)
            result = cursor.fetchone()
            return cast(Optional[sqlite3.Row], result)

    def _execute_fetchall(
        self, sql: str, params: tuple = ()
    ) -> List[sqlite3.Row]:
        """Thread-safe fetchall helper."""
        with self._lock:
            cursor = self.conn.execute(sql, params)
            return cursor.fetchall()

    # ----------------------------------------------------------------------
    # Schema Management
    # ----------------------------------------------------------------------

    def _initialize_schema(self) -> None:
        """Create tables if they don't exist or run migrations."""
        current_version = self._get_schema_version()

        if current_version == 0:
            logger.info("No schema detected — creating schema.")
            self._create_schema()
            self._set_schema_version(SCHEMA_VERSION)
        elif current_version < SCHEMA_VERSION:
            logger.info(
                f"Migrating schema from v{current_version} to v{SCHEMA_VERSION}"
            )
            self._migrate_schema(current_version, SCHEMA_VERSION)
        else:
            logger.debug(f"Schema v{current_version} is up-to-date.")

    def _get_schema_version(self) -> int:
        """Return the schema version stored in the DB."""
        try:
            cursor = self.conn.execute(
                "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.OperationalError:
            # No schema_version table yet
            return 0

    def _set_schema_version(self, version: int) -> None:
        """Record the schema version."""
        self.conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (version,),
        )
        self.conn.commit()

    def _create_schema(self) -> None:
        """Create all necessary tables for a fresh database."""
        logger.info("Creating database schema...")

        with self.transaction() as conn:
            conn.executescript(CREATE_SCHEMA_SQL)

    def _migrate_schema(self, old: int, new: int) -> None:
        """
        Migration path between schema versions.

        v1 -> v2:
            - Add `source` column to `sales`.
        v2 -> v3:
            - Add `price_checks` + `price_quotes` tables for raw price data.
        v3 -> v4:
            - Add `league`, `rarity`, `game_version` columns to `sales`.
            - Add `rarity`, `item_mods_json`, `build_profile` to `checked_items`.
            - Add `currency_rates` table for divine:chaos tracking.
        v4 -> v5:
            - Add `loot_sessions`, `loot_map_runs`, `loot_drops` tables.
            - Add indexes for efficient loot tracking queries.
        v5 -> v6:
            - Add `stash_snapshots` table for persistent stash storage.
            - Stores raw snapshots + valuation results as JSON.
        v6 -> v7:
            - Add `league_economy_rates` for historical currency rates.
            - Add `league_economy_items` for historical item prices.
            - Add `league_economy_snapshots` for milestone snapshots.
            - Add `league_economy_top_uniques` for top uniques per snapshot.
        v7 -> v8:
            - Add `league_economy_summary` for pre-aggregated league stats.
            - Add `league_currency_summary` for currency min/max/avg per league.
            - Add `league_top_items_summary` for pre-computed top items.
        v8 -> v9:
            - Add `upgrade_advice_cache` for AI upgrade recommendations.
            - Persists advice between sessions, keyed by profile + slot + item hash.
        v9 -> v10:
            - Add `upgrade_advice_history` for AI upgrade recommendation history.
            - Stores last 5 analyses per profile + slot combo for comparison.
            - Includes stash scan flag and candidate count.
        v10 -> v11:
            - Add `verdict_statistics` for persistent verdict tracking.
            - Stores daily verdict counts and values per league.
        """
        logger.info(f"Starting schema migration v{old} → v{new}")

        with self.transaction() as conn:
            if old < 2 <= new:
                logger.info(
                    "Applying v2 migration: adding `source` column to `sales`."
                )
                try:
                    conn.execute("ALTER TABLE sales ADD COLUMN source TEXT;")
                except sqlite3.OperationalError as exc:
                    # Column might already exist if created via a previous schema
                    logger.warning(
                        "ALTER TABLE sales ADD COLUMN source failed (possibly already exists): %s",
                        exc,
                    )

            if old < 3 <= new:
                logger.info(
                    "Applying v3 migration: creating price_checks and price_quotes tables."
                )
                conn.executescript(MIGRATION_V3_SQL)

            if old < 4 <= new:
                logger.info(
                    "Applying v4 migration: adding analytics columns and currency_rates table."
                )
                # Add columns to sales table for historical analytics
                for col, col_type in [
                    ("league", "TEXT"),
                    ("rarity", "TEXT"),
                    ("game_version", "TEXT"),
                ]:
                    if col not in ALLOWED_MIGRATION_COLUMNS or ALLOWED_MIGRATION_COLUMNS[col] != col_type:
                        logger.error(f"Invalid column in migration: {col}")
                        continue
                    try:
                        # Column names validated against whitelist in schema.py
                        conn.execute(f"ALTER TABLE sales ADD COLUMN {col} {col_type};")
                    except sqlite3.OperationalError:
                        logger.debug(f"Column sales.{col} already exists")

                # Add columns to checked_items for better analytics
                for col, col_type in [
                    ("rarity", "TEXT"),
                    ("item_mods_json", "TEXT"),
                    ("build_profile", "TEXT"),
                ]:
                    if col not in ALLOWED_MIGRATION_COLUMNS or ALLOWED_MIGRATION_COLUMNS[col] != col_type:
                        logger.error(f"Invalid column in migration: {col}")
                        continue
                    try:
                        # Column names validated against whitelist in schema.py
                        conn.execute(f"ALTER TABLE checked_items ADD COLUMN {col} {col_type};")
                    except sqlite3.OperationalError:
                        logger.debug(f"Column checked_items.{col} already exists")

                # Create currency_rates table for divine:chaos tracking
                conn.executescript(MIGRATION_V4_CURRENCY_RATES_SQL)

            if old < 5 <= new:
                logger.info(
                    "Applying v5 migration: creating loot tracking tables."
                )
                conn.executescript(MIGRATION_V5_SQL)

            if old < 6 <= new:
                logger.info(
                    "Applying v6 migration: creating stash_snapshots table."
                )
                conn.executescript(MIGRATION_V6_SQL)

            if old < 7 <= new:
                logger.info(
                    "Applying v7 migration: creating league economy history tables."
                )
                conn.executescript(MIGRATION_V7_SQL)

            if old < 8 <= new:
                logger.info(
                    "Applying v8 migration: creating economy summary tables."
                )
                conn.executescript(MIGRATION_V8_SQL)

            if old < 9 <= new:
                logger.info(
                    "Applying v9 migration: creating upgrade_advice_cache table."
                )
                conn.executescript(MIGRATION_V9_SQL)

            if old < 10 <= new:
                logger.info(
                    "Applying v10 migration: creating upgrade_advice_history table."
                )
                conn.executescript(MIGRATION_V10_SQL)

            if old < 11 <= new:
                logger.info(
                    "Applying v11 migration: creating verdict_statistics table."
                )
                conn.executescript(MIGRATION_V11_SQL)

        self._set_schema_version(new)
        logger.info(f"Schema migration complete. Now at v{new}.")

    # ----------------------------------------------------------------------
    # Timestamp helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _parse_db_timestamp(value: Optional[str]) -> Optional[datetime]:
        """
        Parse a timestamp from SQLite.

        Supports:
        - ISO format strings
        - "YYYY-MM-DD HH:MM:SS" (SQLite CURRENT_TIMESTAMP)
        """
        if not value:
            return None

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        """
        Normalize a datetime to UTC.

        If dt is naive, assume it's in local timezone, then convert to UTC.
        """
        if dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            return dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
        return dt.astimezone(timezone.utc)

    # ----------------------------------------------------------------------
    # Checked Items
    # ----------------------------------------------------------------------

    def add_checked_item(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        chaos_value: float,
        item_base_type: Optional[str] = None,
    ) -> int:
        """Insert a checked item and return its ID."""
        return self._checked_items_repo.add_checked_item(
            game_version, league, item_name, chaos_value, item_base_type
        )

    def get_checked_items(
        self,
        game_version: Optional[GameVersion] = None,
        league: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return recent checked items, newest-first."""
        return self._checked_items_repo.get_checked_items(game_version, league, limit)

    # ----------------------------------------------------------------------
    # Sales
    # ----------------------------------------------------------------------

    def add_sale(
        self,
        item_name: str,
        listed_price_chaos: float,
        item_base_type: Optional[str] = None,
        item_id: Optional[int] = None,
    ) -> int:
        """Create a sale entry and return its ID."""
        return self._sales_repo.add_sale(
            item_name, listed_price_chaos, item_base_type, item_id
        )

    def record_instant_sale(
        self,
        item_name: str,
        chaos_value: float | None = None,
        item_base_type: str | None = None,
        notes: str | None = None,
        source: str | None = None,
        price_chaos: float | None = None,
    ) -> int:
        """Record a sale where listing and sale happen at essentially the same time."""
        return self._sales_repo.record_instant_sale(
            item_name=item_name,
            chaos_value=chaos_value,
            item_base_type=item_base_type,
            notes=notes,
            source=source,
            price_chaos=price_chaos,
        )

    def complete_sale(
        self,
        sale_id: int,
        actual_price_chaos: float,
        sold_at: Optional[datetime] = None,
    ) -> None:
        """Mark a sale as completed."""
        return self._sales_repo.complete_sale(sale_id, actual_price_chaos, sold_at)

    def mark_sale_unsold(self, sale_id: int) -> None:
        """Mark a sale as unsold (notes only)."""
        return self._sales_repo.mark_sale_unsold(sale_id)

    def get_sales(
        self,
        sold_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return sales entries, newest-first by listed_at DESC."""
        return self._sales_repo.get_sales(sold_only, limit)

    # ----------------------------------------------------------------------
    # Price History + Price Checks / Quotes
    # ----------------------------------------------------------------------

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
        """
        cursor = self.conn.execute(
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
        self.conn.commit()
        return cursor.lastrowid or 0

    def create_price_check(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        item_base_type: str | None,
        source: str | None = None,
        query_hash: str | None = None,
    ) -> int:
        """
        Insert a new price_checks row and return its ID.
        """
        cursor = self.conn.execute(
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
        self.conn.commit()
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
        """
        rows: list[tuple[Any, ...]] = []

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
            listed_at_str: str | None
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
            - stddev  (population-style; 0 if < 2 samples)
        """
        cursor = self.conn.execute(
            """
            SELECT price_chaos
            FROM price_quotes
            WHERE price_check_id = ?
            ORDER BY price_chaos ASC
            """,
            (price_check_id,),
        )
        prices = [float(row[0]) for row in cursor.fetchall() if row[0] is not None]

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
        def percentile(vals: list[float], q: float) -> float:
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
        within the last `days` days. Returns None if no checks found.
        """
        cursor = self.conn.execute(
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
        row = cursor.fetchone()
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
        Return price snapshots within the last `days` days, ordered ascending.
        """
        query = """
            SELECT * FROM price_history
            WHERE game_version = ?
              AND league = ?
              AND item_name = ?
              AND recorded_at >= datetime('now', ?)
            ORDER BY recorded_at ASC
        """
        params = (
            game_version.value,
            league,
            item_name,
            f"-{days} days",
        )

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ----------------------------------------------------------------------
    # Plugin State
    # ----------------------------------------------------------------------

    def set_plugin_enabled(self, plugin_name: str, enabled: bool) -> None:
        """Enable or disable a plugin."""
        return self._plugin_repo.set_plugin_enabled(plugin_name, enabled)

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled."""
        return self._plugin_repo.is_plugin_enabled(plugin_name)

    def set_plugin_config(self, plugin_name: str, config_json: str) -> None:
        """Store plugin-specific JSON configuration."""
        return self._plugin_repo.set_plugin_config(plugin_name, config_json)

    def get_plugin_config(self, plugin_name: str) -> Optional[str]:
        """Return stored plugin configuration JSON, if any."""
        return self._plugin_repo.get_plugin_config(plugin_name)

    # ----------------------------------------------------------------------
    # Statistics
    # ----------------------------------------------------------------------

    def get_stats(self) -> Dict[str, int]:
        """Return aggregate statistics from all tables."""
        return self._stats_repo.get_stats()

    def get_recent_sales(
        self,
        limit: int = 50,
        search_text: str | None = None,
        source: str | None = None,
    ) -> List[sqlite3.Row]:
        """Return recent sales rows with optional filters."""
        return self._sales_repo.get_recent_sales(limit, search_text, source)

    def get_distinct_sale_sources(self) -> List[str]:
        """Return a list of distinct non-empty sources from the sales table."""
        return self._sales_repo.get_distinct_sale_sources()

    # ----------------------------------------------------------------------
    # Maintenance
    # ----------------------------------------------------------------------

    def get_sales_summary(self) -> Dict[str, Any]:
        """Return overall sales summary."""
        return self._sales_repo.get_sales_summary()

    def get_daily_sales_summary(self, days: int = 30) -> List[sqlite3.Row]:
        """Return daily sales summary for the last N days."""
        return self._sales_repo.get_daily_sales_summary(days)

    # ----------------------------------------------------------------------
    # Currency Rate Tracking (v4)
    # ----------------------------------------------------------------------

    def record_currency_rate(
        self,
        league: str,
        game_version: str,
        divine_to_chaos: float,
        exalt_to_chaos: Optional[float] = None,
    ) -> int:
        """Record a currency rate snapshot."""
        return self._currency_repo.record_currency_rate(
            league, game_version, divine_to_chaos, exalt_to_chaos
        )

    def get_latest_currency_rate(
        self, league: str, game_version: str = "poe1"
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent currency rate for a league."""
        return self._currency_repo.get_latest_currency_rate(league, game_version)

    def get_currency_rate_history(
        self, league: str, days: int = 30, game_version: str = "poe1"
    ) -> List[Dict[str, Any]]:
        """Get currency rate history for trend analysis."""
        return self._currency_repo.get_currency_rate_history(league, days, game_version)

    def wipe_all_data(self) -> None:
        """Delete all rows from the main data tables."""
        return self._stats_repo.wipe_all_data()

    def vacuum(self) -> None:
        """Perform SQLite VACUUM for file-size maintenance."""
        return self._stats_repo.vacuum()

    # ----------------------------------------------------------------------
    # Upgrade Advice Cache
    # ----------------------------------------------------------------------

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
            cursor = self._execute(
                """
                SELECT advice_text, ai_model, created_at, item_hash
                FROM upgrade_advice_cache
                WHERE profile_name = ? AND slot = ? AND item_hash = ?
                """,
                (profile_name, slot, item_hash),
            )
        else:
            cursor = self._execute(
                """
                SELECT advice_text, ai_model, created_at, item_hash
                FROM upgrade_advice_cache
                WHERE profile_name = ? AND slot = ?
                """,
                (profile_name, slot),
            )

        row = cursor.fetchone()
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
        cursor = self._execute(
            """
            SELECT slot, advice_text, ai_model, created_at, item_hash
            FROM upgrade_advice_cache
            WHERE profile_name = ?
            """,
            (profile_name,),
        )

        result = {}
        for row in cursor.fetchall():
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

    # ----------------------------------------------------------------------
    # Upgrade Advice History (v10+)
    # ----------------------------------------------------------------------

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
        cursor = self._execute(
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
        for row in cursor.fetchall():
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
            cursor = self._execute(
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
            cursor = self._execute(
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

        row = cursor.fetchone()
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
        cursor = self._execute(
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
        for row in cursor.fetchall():
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

    # ----------------------------------------------------------------------
    # Verdict Statistics Persistence (v11+)
    # ----------------------------------------------------------------------

    def save_verdict_statistics(
        self,
        league: str,
        game_version: str,
        session_date: str,
        stats: Dict[str, Any],
    ) -> int:
        """
        Save or update verdict statistics for a session.

        Uses UPSERT to update existing stats for the same league/date.

        Args:
            league: League name (e.g., "Settlers").
            game_version: "poe1" or "poe2".
            session_date: Date string (YYYY-MM-DD format).
            stats: Dict containing verdict statistics fields.

        Returns:
            Row ID of the upserted record.
        """
        cursor = self._execute(
            """
            INSERT INTO verdict_statistics (
                league, game_version, session_date,
                keep_count, vendor_count, maybe_count,
                keep_value, vendor_value, maybe_value,
                items_with_meta_bonus, total_meta_bonus,
                high_confidence_count, medium_confidence_count, low_confidence_count,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(league, game_version, session_date) DO UPDATE SET
                keep_count = excluded.keep_count,
                vendor_count = excluded.vendor_count,
                maybe_count = excluded.maybe_count,
                keep_value = excluded.keep_value,
                vendor_value = excluded.vendor_value,
                maybe_value = excluded.maybe_value,
                items_with_meta_bonus = excluded.items_with_meta_bonus,
                total_meta_bonus = excluded.total_meta_bonus,
                high_confidence_count = excluded.high_confidence_count,
                medium_confidence_count = excluded.medium_confidence_count,
                low_confidence_count = excluded.low_confidence_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                league,
                game_version,
                session_date,
                stats.get("keep_count", 0),
                stats.get("vendor_count", 0),
                stats.get("maybe_count", 0),
                stats.get("keep_value", 0.0),
                stats.get("vendor_value", 0.0),
                stats.get("maybe_value", 0.0),
                stats.get("items_with_meta_bonus", 0),
                stats.get("total_meta_bonus", 0.0),
                stats.get("high_confidence_count", 0),
                stats.get("medium_confidence_count", 0),
                stats.get("low_confidence_count", 0),
            ),
        )
        return cursor.lastrowid or 0

    def get_verdict_statistics(
        self,
        league: str,
        game_version: str = "poe1",
        session_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get verdict statistics for a specific session.

        Args:
            league: League name.
            game_version: "poe1" or "poe2".
            session_date: Date string (YYYY-MM-DD). If None, gets today's.

        Returns:
            Dict with statistics or None if not found.
        """
        if session_date is None:
            session_date = datetime.now().strftime("%Y-%m-%d")

        cursor = self._execute(
            """
            SELECT * FROM verdict_statistics
            WHERE league = ? AND game_version = ? AND session_date = ?
            """,
            (league, game_version, session_date),
            commit=False,
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_verdict_statistics_history(
        self,
        league: str,
        game_version: str = "poe1",
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get verdict statistics history for a league.

        Args:
            league: League name.
            game_version: "poe1" or "poe2".
            days: Number of days of history to retrieve.

        Returns:
            List of statistics records, newest first.
        """
        cursor = self._execute(
            """
            SELECT * FROM verdict_statistics
            WHERE league = ? AND game_version = ?
              AND session_date >= DATE('now', ?)
            ORDER BY session_date DESC
            """,
            (league, game_version, f"-{days} days"),
            commit=False,
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_verdict_statistics_summary(
        self,
        league: str,
        game_version: str = "poe1",
    ) -> Dict[str, Any]:
        """
        Get aggregated verdict statistics for a league.

        Args:
            league: League name.
            game_version: "poe1" or "poe2".

        Returns:
            Dict with total counts and values across all sessions.
        """
        cursor = self._execute(
            """
            SELECT
                COUNT(*) as session_count,
                COALESCE(SUM(keep_count), 0) as total_keep,
                COALESCE(SUM(vendor_count), 0) as total_vendor,
                COALESCE(SUM(maybe_count), 0) as total_maybe,
                COALESCE(SUM(keep_value), 0.0) as total_keep_value,
                COALESCE(SUM(vendor_value), 0.0) as total_vendor_value,
                COALESCE(SUM(maybe_value), 0.0) as total_maybe_value,
                COALESCE(SUM(items_with_meta_bonus), 0) as total_items_with_meta,
                COALESCE(SUM(total_meta_bonus), 0.0) as total_meta_bonus,
                COALESCE(SUM(high_confidence_count), 0) as total_high_confidence,
                COALESCE(SUM(medium_confidence_count), 0) as total_medium_confidence,
                COALESCE(SUM(low_confidence_count), 0) as total_low_confidence,
                MIN(session_date) as first_date,
                MAX(session_date) as last_date
            FROM verdict_statistics
            WHERE league = ? AND game_version = ?
            """,
            (league, game_version),
            commit=False,
        )
        row = cursor.fetchone()
        if row:
            return {
                "session_count": row["session_count"] or 0,
                "total_keep": row["total_keep"] or 0,
                "total_vendor": row["total_vendor"] or 0,
                "total_maybe": row["total_maybe"] or 0,
                "total_keep_value": row["total_keep_value"] or 0.0,
                "total_vendor_value": row["total_vendor_value"] or 0.0,
                "total_maybe_value": row["total_maybe_value"] or 0.0,
                "total_items_with_meta": row["total_items_with_meta"] or 0,
                "total_meta_bonus": row["total_meta_bonus"] or 0.0,
                "total_high_confidence": row["total_high_confidence"] or 0,
                "total_medium_confidence": row["total_medium_confidence"] or 0,
                "total_low_confidence": row["total_low_confidence"] or 0,
                "first_date": row["first_date"],
                "last_date": row["last_date"],
            }
        return {
            "session_count": 0,
            "total_keep": 0,
            "total_vendor": 0,
            "total_maybe": 0,
            "total_keep_value": 0.0,
            "total_vendor_value": 0.0,
            "total_maybe_value": 0.0,
            "total_items_with_meta": 0,
            "total_meta_bonus": 0.0,
            "total_high_confidence": 0,
            "total_medium_confidence": 0,
            "total_low_confidence": 0,
            "first_date": None,
            "last_date": None,
        }

    def clear_verdict_statistics(
        self,
        league: Optional[str] = None,
        game_version: Optional[str] = None,
    ) -> int:
        """
        Clear verdict statistics.

        Args:
            league: If provided, only clear for this league.
            game_version: If provided with league, also filter by game version.

        Returns:
            Number of rows deleted.
        """
        if league and game_version:
            cursor = self._execute(
                "DELETE FROM verdict_statistics WHERE league = ? AND game_version = ?",
                (league, game_version),
            )
        elif league:
            cursor = self._execute(
                "DELETE FROM verdict_statistics WHERE league = ?",
                (league,),
            )
        else:
            cursor = self._execute("DELETE FROM verdict_statistics")

        return cursor.rowcount

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        try:
            self.conn.close()
        except Exception as exc:
            logger.error(f"Error closing database connection: {exc}")


if __name__ == "__main__":  # pragma: no cover
    print("=== Database Smoke Test ===")
    db = Database(Path("test.db"))
    print("Stats:", db.get_stats())
    print("Done.")
