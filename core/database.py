"""
SQLite-backed persistence layer for the PoE Price Checker.

Responsibilities:
- Checked items (recent item lookups)
- Sales tracking (listed → sold/unsold)
- Price history snapshots
- Plugin state (enabled/config)
- Aggregate statistics
- Schema initialization + versioning
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Iterator

from core.game_version import GameVersion

logger = logging.getLogger(__name__)


class Database:
    """
    Manages all persistent application data through SQLite.

    A Database instance is associated with one database file.
    The schema includes:
    - checked_items
    - sales
    - price_history
    - plugin_state
    - stats views (via queries)
    """

    # Current schema version. Increment if schema structure changes.
    SCHEMA_VERSION = 2

    def __init__(self, db_path: Optional[Path] = None):
        """
        Create a Database instance.

        If db_path is None, use the default location:
        ~/.poe_price_checker/data.db
        """
        if db_path is None:
            db_path = Path.home() / ".poe_price_checker" / "data.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        logger.info(f"Database initialized: {db_path}")

        # Initialize or migrate schema
        self._initialize_schema()
    # ----------------------------------------------------------------------
    # Context manager for transactions
    # ----------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Provide a transaction scope:

            with db.transaction() as conn:
                conn.execute(...)

        Commits on success, rolls back on error.
        """
        try:
            yield self.conn
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            logger.error(f"Transaction failed: {exc}")
            raise

    # ----------------------------------------------------------------------
    # Schema Management
    # ----------------------------------------------------------------------

    def _initialize_schema(self) -> None:
        """Create tables if they don't exist or run migrations."""
        current_version = self._get_schema_version()

        if current_version == 0:
            logger.info("No schema detected — creating schema.")
            self._create_schema()
            self._set_schema_version(self.SCHEMA_VERSION)

        elif current_version < self.SCHEMA_VERSION:
            logger.info(f"Migrating schema from v{current_version} to v{self.SCHEMA_VERSION}")
            self._migrate_schema(current_version, self.SCHEMA_VERSION)

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
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS checked_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_version TEXT NOT NULL,
                    league TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_base_type TEXT,
                    chaos_value REAL NOT NULL,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    item_name TEXT NOT NULL,
                    item_base_type TEXT,
                    source TEXT,
                    listed_price_chaos REAL NOT NULL,
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sold_at TIMESTAMP,
                    actual_price_chaos REAL,
                    time_to_sale_hours REAL,
                    relisted BOOLEAN DEFAULT 0,
                    notes TEXT
                );


                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_version TEXT NOT NULL,
                    league TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_base_type TEXT,
                    chaos_value REAL NOT NULL,
                    divine_value REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS plugin_state (
                    plugin_name TEXT PRIMARY KEY,
                    enabled BOOLEAN,
                    config_json TEXT
                );                
                CREATE TABLE IF NOT EXISTS price_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_version TEXT NOT NULL,
                    league TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_base_type TEXT,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,                 -- e.g. "poe_trade", "poe_ninja"
                    query_hash TEXT              -- optional deterministic hash of query params
                );

                CREATE TABLE IF NOT EXISTS price_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    price_check_id INTEGER NOT NULL REFERENCES price_checks(id) ON DELETE CASCADE,
                    source TEXT NOT NULL,        -- which endpoint / plugin
                    price_chaos REAL NOT NULL,   -- normalized to chaos
                    original_currency TEXT,      -- e.g. "chaos", "divine"
                    stack_size INTEGER,
                    listing_id TEXT,             -- API listing id if any
                    seller_account TEXT,
                    listed_at TIMESTAMP,         -- listing’s own timestamp if available
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                """
            )

    def _migrate_schema(self, old: int, new: int) -> None:
        """
        Migration path between schema versions.

        v1 -> v2:
            - Add `source` column to `sales`.
        v2 -> v3:
            - Add `price_checks` + `price_quotes` tables for raw price data.
        """
        logger.info(f"Starting schema migration v{old} → v{new}")

        with self.transaction() as conn:
            if old < 2 <= new:
                logger.info("Applying v2 migration: adding `source` column to `sales`.")
                conn.execute("ALTER TABLE sales ADD COLUMN source TEXT;")

            if old < 3 <= new:
                logger.info("Applying v3 migration: creating price_checks and price_quotes tables.")
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS price_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_version TEXT NOT NULL,
                        league TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_base_type TEXT,
                        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source TEXT,
                        query_hash TEXT
                    );

                    CREATE TABLE IF NOT EXISTS price_quotes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        price_check_id INTEGER NOT NULL REFERENCES price_checks(id) ON DELETE CASCADE,
                        source TEXT NOT NULL,
                        price_chaos REAL NOT NULL,
                        original_currency TEXT,
                        stack_size INTEGER,
                        listing_id TEXT,
                        seller_account TEXT,
                        listed_at TIMESTAMP,
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )

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
                from datetime import datetime as _dt
                return _dt.strptime(value, "%Y-%m-%d %H:%M:%S")
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
        cursor = self.conn.execute(
            """
            INSERT INTO checked_items
                (game_version, league, item_name, item_base_type, chaos_value)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_version.value, league, item_name, item_base_type, chaos_value),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_checked_items(
        self,
        game_version: Optional[GameVersion] = None,
        league: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return recent checked items.

        Results are ordered newest-first by:
        1. checked_at DESC
        2. id DESC   (tie-breaker for identical timestamps)
        """
        query = "SELECT * FROM checked_items WHERE 1=1"
        params: List[Any] = []

        if game_version:
            query += " AND game_version = ?"
            params.append(game_version.value)

        if league:
            query += " AND league = ?"
            params.append(league)

        query += " ORDER BY checked_at DESC, id DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

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
        cursor = self.conn.execute(
            """
            INSERT INTO sales
                (item_name, item_base_type, listed_price_chaos, item_id)
            VALUES (?, ?, ?, ?)
            """,
            (item_name, item_base_type, listed_price_chaos, item_id),
        )
        self.conn.commit()
        return cursor.lastrowid

    def record_instant_sale(
            self,
            item_name: str,
            chaos_value: float | None = None,
            item_base_type: str | None = None,
            notes: str | None = None,
            source: str | None = None,
            price_chaos: float | None = None,
    ) -> int:
        """
        Convenience helper: record a sale where listing and sale happen
        at essentially the same time.

        This:
        - Inserts into `sales` with listed_at = sold_at = CURRENT_TIMESTAMP
        - Sets listed_price_chaos = actual_price_chaos = effective chaos value
        - Leaves item_id NULL (we're not linking to checked_items yet)
        - Sets time_to_sale_hours = 0.0 and relisted = 0

        Parameters:
            item_name: item name
            chaos_value: chaos value (legacy positional / keyword)
            price_chaos: chaos value (new keyword used by GUI)
            item_base_type: optional base type
            notes: optional notes
            source: where the sale came from (trade site, manual, loot, etc.)
        """
        # Support both chaos_value and price_chaos, prefer explicit chaos_value
        effective_chaos = chaos_value if chaos_value is not None else price_chaos

        if effective_chaos is None:
            raise ValueError(
                "record_instant_sale requires either chaos_value or price_chaos"
            )

        cursor = self.conn.execute(
            """
            INSERT INTO sales (item_id,
                               item_name,
                               item_base_type,
                               source,
                               listed_price_chaos,
                               listed_at,
                               sold_at,
                               actual_price_chaos,
                               time_to_sale_hours,
                               relisted,
                               notes)
            VALUES (NULL,
                    ?,
                    ?,
                    ?,
                    ?,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    ?,
                    0.0,
                    0,
                    ?)
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
        self.conn.commit()
        return int(cursor.lastrowid)

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
        """
        if sold_at is None:
            sold_at = datetime.now()

        sold_at_utc = self._ensure_utc(sold_at)

        # Retrieve listed_at
        cursor = self.conn.execute(
            "SELECT listed_at FROM sales WHERE id = ?", (sale_id,)
        )
        row = cursor.fetchone()
        listed_at_str = row[0] if row else None

        listed_at = self._parse_db_timestamp(listed_at_str) or sold_at_utc
        listed_at_utc = self._ensure_utc(listed_at)

        # Compute hours to sale, clamp negative to zero
        time_to_sale = (
            sold_at_utc - listed_at_utc
        ).total_seconds() / 3600.0
        if time_to_sale < 0:
            time_to_sale = 0.0

        self.conn.execute(
            """
            UPDATE sales
            SET sold_at = ?, actual_price_chaos = ?, time_to_sale_hours = ?
            WHERE id = ?
            """,
            (sold_at_utc.isoformat(), actual_price_chaos, time_to_sale, sale_id),
        )
        self.conn.commit()

        logger.info(
            f"Sale completed: ID {sale_id}, sold for {actual_price_chaos}c "
            f"in {time_to_sale:.1f}h"
        )

    def mark_sale_unsold(self, sale_id: int) -> None:
        """Mark a sale as unsold (notes only)."""
        now_utc = self._ensure_utc(datetime.now())

        self.conn.execute(
            """
            UPDATE sales
            SET sold_at = ?, notes = 'Did not sell'
            WHERE id = ?
            """,
            (now_utc.isoformat(), sale_id),
        )
        self.conn.commit()

    def get_sales(
        self,
        sold_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return sales entries, newest-first by listed_at DESC.
        """
        query = "SELECT * FROM sales WHERE 1=1"

        if sold_only:
            query += " AND sold_at IS NOT NULL"

        query += " ORDER BY listed_at DESC LIMIT ?"

        cursor = self.conn.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # ----------------------------------------------------------------------
    # Price History
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
        return cursor.lastrowid
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
        return int(cursor.lastrowid)

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
            if isinstance(listed_at, datetime):
                listed_at_str = listed_at.isoformat(timespec="seconds")
            else:
                listed_at_str = listed_at

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
        self.conn.execute(
            """
            INSERT INTO plugin_state (plugin_name, enabled)
            VALUES (?, ?)
            ON CONFLICT(plugin_name)
            DO UPDATE SET enabled = ?
            """,
            (plugin_name, enabled, enabled),
        )
        self.conn.commit()

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled."""
        cursor = self.conn.execute(
            "SELECT enabled FROM plugin_state WHERE plugin_name = ?",
            (plugin_name,),
        )
        row = cursor.fetchone()
        return bool(row[0]) if row else False

    def set_plugin_config(self, plugin_name: str, config_json: str) -> None:
        """
        Store plugin-specific JSON configuration.
        """
        self.conn.execute(
            """
            INSERT INTO plugin_state (plugin_name, config_json)
            VALUES (?, ?)
            ON CONFLICT(plugin_name)
            DO UPDATE SET config_json = ?
            """,
            (plugin_name, config_json, config_json),
        )
        self.conn.commit()

    def get_plugin_config(self, plugin_name: str) -> Optional[str]:
        """Return stored plugin configuration JSON, if any."""
        cursor = self.conn.execute(
            "SELECT config_json FROM plugin_state WHERE plugin_name = ?",
            (plugin_name,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # ----------------------------------------------------------------------
    # Statistics
    # ----------------------------------------------------------------------

    def get_stats(self) -> Dict[str, int]:
        """
        Return aggregate statistics from all tables.
        """
        stats = {}

        cursor = self.conn.execute("SELECT COUNT(*) FROM checked_items")
        stats["checked_items"] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM sales")
        stats["sales"] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM sales WHERE sold_at IS NOT NULL")
        stats["completed_sales"] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM price_history")
        stats["price_snapshots"] = cursor.fetchone()[0]

        return stats
    def get_recent_sales(
        self,
        limit: int = 50,
        search_text: str | None = None,
        source: str | None = None,
    ) -> List[sqlite3.Row]:
        """
        Return recent sales rows, ordered by most recent activity, with optional filters.

        Filters:
            search_text: case-insensitive substring match against
                         item_name, item_base_type, source, notes
            source: if provided and not blank/'All', filter by exact source

        Fields returned:
            id,
            item_name,
            item_base_type,
            source,
            listed_at,
            sold_at,
            listed_price_chaos,
            actual_price_chaos,
            price_chaos   (derived: COALESCE(actual, listed)),
            time_to_sale_hours,
            relisted,
            notes
        """
        clauses: list[str] = []
        params: list[Any] = []

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
        """
        params.append(limit)

        cursor = self.conn.execute(sql, params)
        return list(cursor.fetchall())

    def get_distinct_sale_sources(self) -> List[str]:
        """
        Return a list of distinct non-empty sources from the sales table,
        sorted alphabetically.
        """
        cursor = self.conn.execute(
            """
            SELECT DISTINCT source
            FROM sales
            WHERE source IS NOT NULL AND TRIM(source) <> ''
            ORDER BY source COLLATE NOCASE
            """
        )
        return [row[0] for row in cursor.fetchall()]

    # ----------------------------------------------------------------------
    # Maintenance
    # ----------------------------------------------------------------------
    def get_sales_summary(self) -> Dict[str, Any]:
        """
        Return overall sales summary:
            - total_sales: number of sales rows
            - total_chaos: sum of effective chaos price
            - avg_chaos: average effective chaos price per sale

        Effective chaos price is:
            COALESCE(actual_price_chaos, listed_price_chaos)
        """
        cursor = self.conn.execute(
            """
            SELECT COUNT(*) AS total_sales,
                   COALESCE(
                           SUM(COALESCE(actual_price_chaos, listed_price_chaos)),
                           0
                   )        AS total_chaos,
                   CASE
                       WHEN COUNT(*) > 0 THEN
                           COALESCE(AVG(COALESCE(actual_price_chaos, listed_price_chaos)), 0)
                       ELSE
                           0
                       END  AS avg_chaos
            FROM sales
            """
        )
        row = cursor.fetchone()
        if row is None:
            return {"total_sales": 0, "total_chaos": 0.0, "avg_chaos": 0.0}

        return {
            "total_sales": row["total_sales"],
            "total_chaos": float(row["total_chaos"] or 0.0),
            "avg_chaos": float(row["avg_chaos"] or 0.0),
        }

    def get_daily_sales_summary(self, days: int = 30) -> List[sqlite3.Row]:
        """
        Return daily sales summary for the last `days` days (including today).

        Each row has:
            day (YYYY-MM-DD),
            sale_count,
            total_chaos,
            avg_chaos

        Effective chaos price is:
            COALESCE(actual_price_chaos, listed_price_chaos)
        The day is based on COALESCE(sold_at, listed_at).
        """
        cursor = self.conn.execute(
            """
            SELECT
                DATE (COALESCE (sold_at, listed_at)) AS day, COUNT (*) AS sale_count, COALESCE (
                SUM (COALESCE (actual_price_chaos, listed_price_chaos)), 0
                ) AS total_chaos, CASE WHEN COUNT (*) > 0 THEN
                COALESCE (
                AVG (COALESCE (actual_price_chaos, listed_price_chaos)), 0
                )
                ELSE
                0
            END
            AS avg_chaos
            FROM sales
            WHERE COALESCE(sold_at, listed_at) >= DATE('now', ?)
            GROUP BY DATE(COALESCE(sold_at, listed_at))
            ORDER BY DATE(COALESCE(sold_at, listed_at)) DESC
            """,
            (f"-{int(days)} days",),
        )
        return list(cursor.fetchall())
    def wipe_all_data(self) -> None:
        """
        Delete all rows from the main data tables.

        This preserves:
            - schema_version entries
            - table structure

        Effectively resets the app's data: checked items, sales, price history,
        plugin state.
        """
        logger.warning("Wiping all database data (checked_items, sales, price_history, plugin_state).")

        with self.transaction() as conn:
            conn.execute("DELETE FROM checked_items")
            conn.execute("DELETE FROM sales")
            conn.execute("DELETE FROM price_history")
            conn.execute("DELETE FROM plugin_state")

        # Optional: shrink file; safe but may be slow on huge DBs
        try:
            self.conn.execute("VACUUM")
        except Exception as exc:  # non-fatal
            logger.error(f"VACUUM after wipe_all_data failed: {exc}")

    def vacuum(self) -> None:
        """Perform SQLite VACUUM for file-size maintenance."""
        self.conn.execute("VACUUM")
        self.conn.commit()
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
