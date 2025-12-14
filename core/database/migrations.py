"""
Database migration runner for schema versioning.

Handles database schema initialization and migration between versions.
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from threading import RLock
from typing import Iterator

from core.database.schema import (
    SCHEMA_VERSION,
    CREATE_SCHEMA_SQL,
    MIGRATION_V3_SQL,
    MIGRATION_V4_CURRENCY_RATES_SQL,
    MIGRATION_V5_SQL,
    MIGRATION_V6_SQL,
    MIGRATION_V7_SQL,
    MIGRATION_V8_SQL,
    MIGRATION_V9_SQL,
    MIGRATION_V10_SQL,
    MIGRATION_V11_SQL,
    MIGRATION_V12_SQL,
    ALLOWED_MIGRATION_COLUMNS,
)

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Handles database schema initialization and migrations.

    Responsible for:
    - Creating schema for fresh databases
    - Migrating existing databases to new schema versions
    - Tracking schema version
    """

    def __init__(self, conn: sqlite3.Connection, lock: RLock):
        """
        Initialize the migration runner.

        Args:
            conn: SQLite connection to migrate
            lock: Thread lock for safe execution
        """
        self._conn = conn
        self._lock = lock

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Provide a transaction scope with thread safety."""
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception as exc:
                self._conn.rollback()
                logger.error(f"Migration transaction failed: {exc}")
                raise

    def initialize_schema(self) -> None:
        """Create tables if they don't exist or run migrations."""
        current_version = self.get_schema_version()

        if current_version == 0:
            logger.info("No schema detected - creating schema.")
            self._create_schema()
            self._set_schema_version(SCHEMA_VERSION)
        elif current_version < SCHEMA_VERSION:
            logger.info(
                f"Migrating schema from v{current_version} to v{SCHEMA_VERSION}"
            )
            self.migrate_schema(current_version, SCHEMA_VERSION)
        else:
            logger.debug(f"Schema v{current_version} is up-to-date.")

    def get_schema_version(self) -> int:
        """Return the schema version stored in the DB."""
        try:
            cursor = self._conn.execute(
                "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.OperationalError:
            # No schema_version table yet
            return 0

    def _set_schema_version(self, version: int) -> None:
        """Record the schema version."""
        self._conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (version,),
        )
        self._conn.commit()

    def _create_schema(self) -> None:
        """Create all necessary tables for a fresh database."""
        logger.info("Creating database schema...")

        with self._transaction() as conn:
            conn.executescript(CREATE_SCHEMA_SQL)

    def migrate_schema(self, old: int, new: int) -> None:
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
        v11 -> v12:
            - Add `price_alerts` for price monitoring and notifications.
            - Tracks item alerts with above/below thresholds and cooldowns.

        Args:
            old: Current schema version
            new: Target schema version
        """
        logger.info(f"Starting schema migration v{old} -> v{new}")

        with self._transaction() as conn:
            if old < 2 <= new:
                self._migrate_v2(conn)

            if old < 3 <= new:
                self._migrate_v3(conn)

            if old < 4 <= new:
                self._migrate_v4(conn)

            if old < 5 <= new:
                self._migrate_v5(conn)

            if old < 6 <= new:
                self._migrate_v6(conn)

            if old < 7 <= new:
                self._migrate_v7(conn)

            if old < 8 <= new:
                self._migrate_v8(conn)

            if old < 9 <= new:
                self._migrate_v9(conn)

            if old < 10 <= new:
                self._migrate_v10(conn)

            if old < 11 <= new:
                self._migrate_v11(conn)

            if old < 12 <= new:
                self._migrate_v12(conn)

        self._set_schema_version(new)
        logger.info(f"Schema migration complete. Now at v{new}.")

    def _migrate_v2(self, conn: sqlite3.Connection) -> None:
        """v1 -> v2: Add `source` column to `sales`."""
        logger.info("Applying v2 migration: adding `source` column to `sales`.")
        try:
            conn.execute("ALTER TABLE sales ADD COLUMN source TEXT;")
        except sqlite3.OperationalError as exc:
            # Column might already exist if created via a previous schema
            logger.warning(
                "ALTER TABLE sales ADD COLUMN source failed (possibly already exists): %s",
                exc,
            )

    def _migrate_v3(self, conn: sqlite3.Connection) -> None:
        """v2 -> v3: Create price_checks and price_quotes tables."""
        logger.info(
            "Applying v3 migration: creating price_checks and price_quotes tables."
        )
        conn.executescript(MIGRATION_V3_SQL)

    def _migrate_v4(self, conn: sqlite3.Connection) -> None:
        """v3 -> v4: Add analytics columns and currency_rates table."""
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

    def _migrate_v5(self, conn: sqlite3.Connection) -> None:
        """v4 -> v5: Create loot tracking tables."""
        logger.info("Applying v5 migration: creating loot tracking tables.")
        conn.executescript(MIGRATION_V5_SQL)

    def _migrate_v6(self, conn: sqlite3.Connection) -> None:
        """v5 -> v6: Create stash_snapshots table."""
        logger.info("Applying v6 migration: creating stash_snapshots table.")
        conn.executescript(MIGRATION_V6_SQL)

    def _migrate_v7(self, conn: sqlite3.Connection) -> None:
        """v6 -> v7: Create league economy history tables."""
        logger.info("Applying v7 migration: creating league economy history tables.")
        conn.executescript(MIGRATION_V7_SQL)

    def _migrate_v8(self, conn: sqlite3.Connection) -> None:
        """v7 -> v8: Create economy summary tables."""
        logger.info("Applying v8 migration: creating economy summary tables.")
        conn.executescript(MIGRATION_V8_SQL)

    def _migrate_v9(self, conn: sqlite3.Connection) -> None:
        """v8 -> v9: Create upgrade_advice_cache table."""
        logger.info("Applying v9 migration: creating upgrade_advice_cache table.")
        conn.executescript(MIGRATION_V9_SQL)

    def _migrate_v10(self, conn: sqlite3.Connection) -> None:
        """v9 -> v10: Create upgrade_advice_history table."""
        logger.info("Applying v10 migration: creating upgrade_advice_history table.")
        conn.executescript(MIGRATION_V10_SQL)

    def _migrate_v11(self, conn: sqlite3.Connection) -> None:
        """v10 -> v11: Create verdict_statistics table."""
        logger.info("Applying v11 migration: creating verdict_statistics table.")
        conn.executescript(MIGRATION_V11_SQL)

    def _migrate_v12(self, conn: sqlite3.Connection) -> None:
        """v11 -> v12: Create price_alerts table."""
        logger.info("Applying v12 migration: creating price_alerts table.")
        conn.executescript(MIGRATION_V12_SQL)
