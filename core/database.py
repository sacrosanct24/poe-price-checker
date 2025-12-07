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
from typing import Any, Dict, Iterator, List, Optional

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
    - price_checks
    - price_quotes
    - plugin_state
    - stats views (via queries)
    """

    # Current schema version. Increment if schema structure changes.
    SCHEMA_VERSION = 8

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
            return cursor.fetchone()

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
            self._set_schema_version(self.SCHEMA_VERSION)
        elif current_version < self.SCHEMA_VERSION:
            logger.info(
                f"Migrating schema from v{current_version} to v{self.SCHEMA_VERSION}"
            )
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
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- v4 columns for analytics
                    rarity TEXT,
                    item_mods_json TEXT,
                    build_profile TEXT
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
                    notes TEXT,
                    -- v4 columns for analytics
                    league TEXT,
                    rarity TEXT,
                    game_version TEXT
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
                    price_check_id INTEGER NOT NULL
                        REFERENCES price_checks(id) ON DELETE CASCADE,
                    source TEXT NOT NULL,        -- which endpoint / plugin
                    price_chaos REAL NOT NULL,   -- normalized to chaos
                    original_currency TEXT,      -- e.g. "chaos", "divine"
                    stack_size INTEGER,
                    listing_id TEXT,             -- API listing id if any
                    seller_account TEXT,
                    listed_at TIMESTAMP,         -- listing's own timestamp if available
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- v4: Currency rate tracking for historical analytics
                CREATE TABLE IF NOT EXISTS currency_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league TEXT NOT NULL,
                    game_version TEXT NOT NULL,
                    divine_to_chaos REAL NOT NULL,
                    exalt_to_chaos REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_currency_rates_league_time
                ON currency_rates (league, recorded_at DESC);

                -- v5: Loot tracking tables
                CREATE TABLE IF NOT EXISTS loot_sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    league TEXT NOT NULL,
                    game_version TEXT NOT NULL DEFAULT 'poe1',
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    state TEXT NOT NULL DEFAULT 'idle',
                    auto_detected BOOLEAN DEFAULT 0,
                    notes TEXT,
                    total_maps INTEGER DEFAULT 0,
                    total_drops INTEGER DEFAULT 0,
                    total_chaos_value REAL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS loot_map_runs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
                    map_name TEXT NOT NULL,
                    area_level INTEGER,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    drop_count INTEGER DEFAULT 0,
                    total_chaos_value REAL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS loot_drops (
                    id TEXT PRIMARY KEY,
                    map_run_id TEXT NOT NULL REFERENCES loot_map_runs(id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
                    item_name TEXT NOT NULL,
                    item_base_type TEXT,
                    stack_size INTEGER DEFAULT 1,
                    chaos_value REAL DEFAULT 0.0,
                    divine_value REAL DEFAULT 0.0,
                    rarity TEXT,
                    item_class TEXT,
                    detected_at TIMESTAMP NOT NULL,
                    source_tab TEXT,
                    item_data_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_loot_sessions_league
                ON loot_sessions (league, started_at DESC);

                CREATE INDEX IF NOT EXISTS idx_loot_map_runs_session
                ON loot_map_runs (session_id, started_at);

                CREATE INDEX IF NOT EXISTS idx_loot_drops_session
                ON loot_drops (session_id, detected_at DESC);

                CREATE INDEX IF NOT EXISTS idx_loot_drops_value
                ON loot_drops (chaos_value DESC);

                -- v6: Stash snapshot storage for persistence
                CREATE TABLE IF NOT EXISTS stash_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT NOT NULL,
                    league TEXT NOT NULL,
                    game_version TEXT NOT NULL DEFAULT 'poe1',
                    total_items INTEGER DEFAULT 0,
                    priced_items INTEGER DEFAULT 0,
                    total_chaos_value REAL DEFAULT 0.0,
                    snapshot_json TEXT,
                    valuation_json TEXT,
                    fetched_at TIMESTAMP NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_stash_snapshots_account_league
                ON stash_snapshots (account_name, league, fetched_at DESC);

                -- v7: League economy history tables
                CREATE TABLE IF NOT EXISTS league_economy_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league TEXT NOT NULL,
                    currency_name TEXT NOT NULL,
                    rate_date TEXT NOT NULL,
                    chaos_value REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_league_economy_rates_lookup
                ON league_economy_rates (league, currency_name, rate_date);

                CREATE TABLE IF NOT EXISTS league_economy_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    base_type TEXT,
                    item_type TEXT,
                    rate_date TEXT NOT NULL,
                    chaos_value REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_league_economy_items_lookup
                ON league_economy_items (league, rate_date, chaos_value DESC);

                CREATE TABLE IF NOT EXISTS league_economy_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league TEXT NOT NULL,
                    milestone TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    divine_to_chaos REAL NOT NULL,
                    exalt_to_chaos REAL
                );

                CREATE INDEX IF NOT EXISTS idx_league_economy_snapshots_league
                ON league_economy_snapshots (league, milestone);

                CREATE TABLE IF NOT EXISTS league_economy_top_uniques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL
                        REFERENCES league_economy_snapshots(id) ON DELETE CASCADE,
                    item_name TEXT NOT NULL,
                    base_type TEXT,
                    chaos_value REAL NOT NULL,
                    divine_value REAL,
                    rank INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_league_economy_top_uniques_snapshot
                ON league_economy_top_uniques (snapshot_id, rank);

                -- v8: Pre-aggregated summary tables for historical leagues
                CREATE TABLE IF NOT EXISTS league_economy_summary (
                    league TEXT PRIMARY KEY,
                    first_date TEXT NOT NULL,
                    last_date TEXT NOT NULL,
                    total_currency_snapshots INTEGER NOT NULL DEFAULT 0,
                    total_item_snapshots INTEGER NOT NULL DEFAULT 0,
                    is_finalized INTEGER NOT NULL DEFAULT 0,
                    computed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS league_currency_summary (
                    league TEXT NOT NULL,
                    currency_name TEXT NOT NULL,
                    min_value REAL NOT NULL,
                    max_value REAL NOT NULL,
                    avg_value REAL NOT NULL,
                    start_value REAL,
                    end_value REAL,
                    peak_date TEXT,
                    data_points INTEGER NOT NULL,
                    PRIMARY KEY (league, currency_name)
                );

                CREATE TABLE IF NOT EXISTS league_top_items_summary (
                    league TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    base_type TEXT,
                    avg_value REAL NOT NULL,
                    min_value REAL NOT NULL,
                    max_value REAL NOT NULL,
                    data_points INTEGER NOT NULL,
                    rank INTEGER NOT NULL,
                    PRIMARY KEY (league, item_name)
                );

                CREATE INDEX IF NOT EXISTS idx_league_top_items_rank
                ON league_top_items_summary (league, rank);
                """
            )

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
                        price_check_id INTEGER NOT NULL
                            REFERENCES price_checks(id) ON DELETE CASCADE,
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

            if old < 4 <= new:
                logger.info(
                    "Applying v4 migration: adding analytics columns and currency_rates table."
                )
                # Whitelist of allowed column names and types for security
                # (prevents any possibility of SQL injection in migrations)
                ALLOWED_COLUMNS = {
                    "league": "TEXT",
                    "rarity": "TEXT",
                    "game_version": "TEXT",
                    "item_mods_json": "TEXT",
                    "build_profile": "TEXT",
                }

                # Add columns to sales table for historical analytics
                for col, col_type in [
                    ("league", "TEXT"),
                    ("rarity", "TEXT"),
                    ("game_version", "TEXT"),
                ]:
                    if col not in ALLOWED_COLUMNS or ALLOWED_COLUMNS[col] != col_type:
                        logger.error(f"Invalid column in migration: {col}")
                        continue
                    try:
                        # Column names validated against whitelist above
                        conn.execute(f"ALTER TABLE sales ADD COLUMN {col} {col_type};")
                    except sqlite3.OperationalError:
                        logger.debug(f"Column sales.{col} already exists")

                # Add columns to checked_items for better analytics
                for col, col_type in [
                    ("rarity", "TEXT"),
                    ("item_mods_json", "TEXT"),
                    ("build_profile", "TEXT"),
                ]:
                    if col not in ALLOWED_COLUMNS or ALLOWED_COLUMNS[col] != col_type:
                        logger.error(f"Invalid column in migration: {col}")
                        continue
                    try:
                        # Column names validated against whitelist above
                        conn.execute(f"ALTER TABLE checked_items ADD COLUMN {col} {col_type};")
                    except sqlite3.OperationalError:
                        logger.debug(f"Column checked_items.{col} already exists")

                # Create currency_rates table for divine:chaos tracking
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS currency_rates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        league TEXT NOT NULL,
                        game_version TEXT NOT NULL,
                        divine_to_chaos REAL NOT NULL,
                        exalt_to_chaos REAL,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                # Create index for efficient rate lookups
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_currency_rates_league_time
                    ON currency_rates (league, recorded_at DESC);
                    """
                )

            if old < 5 <= new:
                logger.info(
                    "Applying v5 migration: creating loot tracking tables."
                )
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS loot_sessions (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        league TEXT NOT NULL,
                        game_version TEXT NOT NULL DEFAULT 'poe1',
                        started_at TIMESTAMP NOT NULL,
                        ended_at TIMESTAMP,
                        state TEXT NOT NULL DEFAULT 'idle',
                        auto_detected BOOLEAN DEFAULT 0,
                        notes TEXT,
                        total_maps INTEGER DEFAULT 0,
                        total_drops INTEGER DEFAULT 0,
                        total_chaos_value REAL DEFAULT 0.0
                    );

                    CREATE TABLE IF NOT EXISTS loot_map_runs (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
                        map_name TEXT NOT NULL,
                        area_level INTEGER,
                        started_at TIMESTAMP NOT NULL,
                        ended_at TIMESTAMP,
                        drop_count INTEGER DEFAULT 0,
                        total_chaos_value REAL DEFAULT 0.0
                    );

                    CREATE TABLE IF NOT EXISTS loot_drops (
                        id TEXT PRIMARY KEY,
                        map_run_id TEXT NOT NULL REFERENCES loot_map_runs(id) ON DELETE CASCADE,
                        session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
                        item_name TEXT NOT NULL,
                        item_base_type TEXT,
                        stack_size INTEGER DEFAULT 1,
                        chaos_value REAL DEFAULT 0.0,
                        divine_value REAL DEFAULT 0.0,
                        rarity TEXT,
                        item_class TEXT,
                        detected_at TIMESTAMP NOT NULL,
                        source_tab TEXT,
                        item_data_json TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_loot_sessions_league
                    ON loot_sessions (league, started_at DESC);

                    CREATE INDEX IF NOT EXISTS idx_loot_map_runs_session
                    ON loot_map_runs (session_id, started_at);

                    CREATE INDEX IF NOT EXISTS idx_loot_drops_session
                    ON loot_drops (session_id, detected_at DESC);

                    CREATE INDEX IF NOT EXISTS idx_loot_drops_value
                    ON loot_drops (chaos_value DESC);
                    """
                )

            if old < 6 <= new:
                logger.info(
                    "Applying v6 migration: creating stash_snapshots table."
                )
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS stash_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_name TEXT NOT NULL,
                        league TEXT NOT NULL,
                        game_version TEXT NOT NULL DEFAULT 'poe1',
                        total_items INTEGER DEFAULT 0,
                        priced_items INTEGER DEFAULT 0,
                        total_chaos_value REAL DEFAULT 0.0,
                        snapshot_json TEXT,
                        valuation_json TEXT,
                        fetched_at TIMESTAMP NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_stash_snapshots_account_league
                    ON stash_snapshots (account_name, league, fetched_at DESC);
                    """
                )

            if old < 7 <= new:
                logger.info(
                    "Applying v7 migration: creating league economy history tables."
                )
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS league_economy_rates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        league TEXT NOT NULL,
                        currency_name TEXT NOT NULL,
                        rate_date TEXT NOT NULL,
                        chaos_value REAL NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_league_economy_rates_lookup
                    ON league_economy_rates (league, currency_name, rate_date);

                    CREATE TABLE IF NOT EXISTS league_economy_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        league TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        base_type TEXT,
                        item_type TEXT,
                        rate_date TEXT NOT NULL,
                        chaos_value REAL NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_league_economy_items_lookup
                    ON league_economy_items (league, rate_date, chaos_value DESC);

                    CREATE TABLE IF NOT EXISTS league_economy_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        league TEXT NOT NULL,
                        milestone TEXT NOT NULL,
                        snapshot_date TEXT NOT NULL,
                        divine_to_chaos REAL NOT NULL,
                        exalt_to_chaos REAL
                    );

                    CREATE INDEX IF NOT EXISTS idx_league_economy_snapshots_league
                    ON league_economy_snapshots (league, milestone);

                    CREATE TABLE IF NOT EXISTS league_economy_top_uniques (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        snapshot_id INTEGER NOT NULL
                            REFERENCES league_economy_snapshots(id) ON DELETE CASCADE,
                        item_name TEXT NOT NULL,
                        base_type TEXT,
                        chaos_value REAL NOT NULL,
                        divine_value REAL,
                        rank INTEGER NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_league_economy_top_uniques_snapshot
                    ON league_economy_top_uniques (snapshot_id, rank);
                    """
                )

            if old < 8 <= new:
                logger.info(
                    "Applying v8 migration: creating economy summary tables."
                )
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS league_economy_summary (
                        league TEXT PRIMARY KEY,
                        first_date TEXT NOT NULL,
                        last_date TEXT NOT NULL,
                        total_currency_snapshots INTEGER NOT NULL DEFAULT 0,
                        total_item_snapshots INTEGER NOT NULL DEFAULT 0,
                        is_finalized INTEGER NOT NULL DEFAULT 0,
                        computed_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS league_currency_summary (
                        league TEXT NOT NULL,
                        currency_name TEXT NOT NULL,
                        min_value REAL NOT NULL,
                        max_value REAL NOT NULL,
                        avg_value REAL NOT NULL,
                        start_value REAL,
                        end_value REAL,
                        peak_date TEXT,
                        data_points INTEGER NOT NULL,
                        PRIMARY KEY (league, currency_name)
                    );

                    CREATE TABLE IF NOT EXISTS league_top_items_summary (
                        league TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        base_type TEXT,
                        avg_value REAL NOT NULL,
                        min_value REAL NOT NULL,
                        max_value REAL NOT NULL,
                        data_points INTEGER NOT NULL,
                        rank INTEGER NOT NULL,
                        PRIMARY KEY (league, item_name)
                    );

                    CREATE INDEX IF NOT EXISTS idx_league_top_items_rank
                    ON league_top_items_summary (league, rank);
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
        """Insert a checked item and return its ID. Thread-safe."""
        cursor = self._execute(
            """
            INSERT INTO checked_items
                (game_version, league, item_name, item_base_type, chaos_value)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_version.value, league, item_name, item_base_type, chaos_value),
        )
        return cursor.lastrowid or 0

    def get_checked_items(
        self,
        game_version: Optional[GameVersion] = None,
        league: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return recent checked items. Thread-safe.

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

        rows = self._execute_fetchall(query, tuple(params))
        return [dict(row) for row in rows]

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
        return cursor.lastrowid or 0

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
        self.conn.commit()
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
        stats: Dict[str, int] = {}

        cursor = self.conn.execute("SELECT COUNT(*) FROM checked_items")
        stats["checked_items"] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM sales")
        stats["sales"] = cursor.fetchone()[0]

        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM sales WHERE sold_at IS NOT NULL"
        )
        stats["completed_sales"] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM price_history")
        stats["price_snapshots"] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM price_checks")
        stats["price_checks"] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM price_quotes")
        stats["price_quotes"] = cursor.fetchone()[0]

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

        # nosec B608 - where_sql is constructed from hardcoded clauses, all values use parameterized queries
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
        return list(cursor.fetchall())

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
        """
        Record a currency rate snapshot.

        Args:
            league: League name
            game_version: "poe1" or "poe2"
            divine_to_chaos: Divine orb value in chaos
            exalt_to_chaos: Exalted orb value in chaos (optional)

        Returns:
            The row ID of the inserted record
        """
        cursor = self.conn.execute(
            """
            INSERT INTO currency_rates (league, game_version, divine_to_chaos, exalt_to_chaos)
            VALUES (?, ?, ?, ?)
            """,
            (league, game_version, divine_to_chaos, exalt_to_chaos),
        )
        self.conn.commit()
        return cursor.lastrowid or 0

    def get_latest_currency_rate(
        self, league: str, game_version: str = "poe1"
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent currency rate for a league.

        Args:
            league: League name
            game_version: "poe1" or "poe2"

        Returns:
            Dict with divine_to_chaos, exalt_to_chaos, recorded_at or None
        """
        cursor = self.conn.execute(
            """
            SELECT divine_to_chaos, exalt_to_chaos, recorded_at
            FROM currency_rates
            WHERE league = ? AND game_version = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (league, game_version),
        )
        row = cursor.fetchone()
        if row:
            return {
                "divine_to_chaos": row["divine_to_chaos"],
                "exalt_to_chaos": row["exalt_to_chaos"],
                "recorded_at": self._parse_db_timestamp(row["recorded_at"]),
            }
        return None

    def get_currency_rate_history(
        self, league: str, days: int = 30, game_version: str = "poe1"
    ) -> List[Dict[str, Any]]:
        """
        Get currency rate history for trend analysis.

        Args:
            league: League name
            days: Number of days of history
            game_version: "poe1" or "poe2"

        Returns:
            List of rate records ordered by time descending
        """
        cursor = self.conn.execute(
            """
            SELECT divine_to_chaos, exalt_to_chaos, recorded_at
            FROM currency_rates
            WHERE league = ? AND game_version = ?
              AND recorded_at >= DATE('now', ?)
            ORDER BY recorded_at DESC
            """,
            (league, game_version, f"-{days} days"),
        )
        return [
            {
                "divine_to_chaos": row["divine_to_chaos"],
                "exalt_to_chaos": row["exalt_to_chaos"],
                "recorded_at": self._parse_db_timestamp(row["recorded_at"]),
            }
            for row in cursor.fetchall()
        ]

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
