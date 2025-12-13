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
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, cast

from core.game_version import GameVersion

from core.database.migrations import MigrationRunner
from core.database.repositories.checked_items_repository import CheckedItemsRepository
from core.database.repositories.currency_repository import CurrencyRepository
from core.database.repositories.plugin_repository import PluginRepository
from core.database.repositories.price_repository import PriceRepository
from core.database.repositories.sales_repository import SalesRepository
from core.database.repositories.stats_repository import StatsRepository
from core.database.repositories.upgrade_advice_repository import UpgradeAdviceRepository
from core.database.repositories.verdict_repository import VerdictRepository

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

        # Initialize or migrate schema using MigrationRunner
        self._migration_runner = MigrationRunner(self.conn, self._lock)
        self._migration_runner.initialize_schema()

        # Initialize repositories
        self._checked_items_repo = CheckedItemsRepository(self.conn, self._lock)
        self._currency_repo = CurrencyRepository(self.conn, self._lock)
        self._plugin_repo = PluginRepository(self.conn, self._lock)
        self._price_repo = PriceRepository(self.conn, self._lock)
        self._sales_repo = SalesRepository(self.conn, self._lock)
        self._stats_repo = StatsRepository(self.conn, self._lock)
        self._upgrade_advice_repo = UpgradeAdviceRepository(self.conn, self._lock)
        self._verdict_repo = VerdictRepository(self.conn, self._lock)

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
    # Price History + Price Checks / Quotes (delegated to PriceRepository)
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
        """Insert a price history snapshot and return its ID."""
        return self._price_repo.add_price_snapshot(
            game_version, league, item_name, chaos_value, item_base_type, divine_value
        )

    def create_price_check(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        item_base_type: Optional[str],
        source: Optional[str] = None,
        query_hash: Optional[str] = None,
    ) -> int:
        """Insert a new price_checks row and return its ID."""
        return self._price_repo.create_price_check(
            game_version, league, item_name, item_base_type, source, query_hash
        )

    def add_price_quotes_batch(
        self,
        price_check_id: int,
        quotes: List[Dict[str, Any]],
    ) -> None:
        """Insert a batch of raw price quotes for a given price_check_id."""
        return self._price_repo.add_price_quotes_batch(price_check_id, quotes)

    def get_price_stats_for_check(self, price_check_id: int) -> Dict[str, Any]:
        """Compute robust statistics for all price_quotes belonging to a price_check_id."""
        return self._price_repo.get_price_stats_for_check(price_check_id)

    def get_latest_price_stats_for_item(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        days: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """Get robust price stats for the most recent price_check for a given item."""
        return self._price_repo.get_latest_price_stats_for_item(
            game_version, league, item_name, days
        )

    def get_price_history(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        days: int,
    ) -> List[Dict[str, Any]]:
        """Return price snapshots within the last N days, ordered ascending."""
        return self._price_repo.get_price_history(game_version, league, item_name, days)

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
    # Upgrade Advice Cache (delegated to UpgradeAdviceRepository)
    # ----------------------------------------------------------------------

    def save_upgrade_advice(
        self,
        profile_name: str,
        slot: str,
        item_hash: str,
        advice_text: str,
        ai_model: Optional[str] = None,
    ) -> None:
        """Save or update upgrade advice for a profile/slot."""
        return self._upgrade_advice_repo.save_upgrade_advice(
            profile_name, slot, item_hash, advice_text, ai_model
        )

    def get_upgrade_advice(
        self,
        profile_name: str,
        slot: str,
        item_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get cached upgrade advice for a profile/slot."""
        return self._upgrade_advice_repo.get_upgrade_advice(profile_name, slot, item_hash)

    def get_all_upgrade_advice(
        self,
        profile_name: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Get all cached upgrade advice for a profile."""
        return self._upgrade_advice_repo.get_all_upgrade_advice(profile_name)

    def clear_upgrade_advice(
        self,
        profile_name: Optional[str] = None,
        slot: Optional[str] = None,
    ) -> int:
        """Clear cached upgrade advice."""
        return self._upgrade_advice_repo.clear_upgrade_advice(profile_name, slot)

    # ----------------------------------------------------------------------
    # Upgrade Advice History (delegated to UpgradeAdviceRepository)
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
        """Save upgrade advice to history, keeping last 5 per profile+slot."""
        return self._upgrade_advice_repo.save_upgrade_advice_history(
            profile_name, slot, item_hash, advice_text, ai_model,
            ai_provider, include_stash, stash_candidates_count
        )

    def get_upgrade_advice_history(
        self,
        profile_name: str,
        slot: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get upgrade advice history for a profile+slot."""
        return self._upgrade_advice_repo.get_upgrade_advice_history(profile_name, slot, limit)

    def get_latest_advice_from_history(
        self,
        profile_name: str,
        slot: str,
        item_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent advice from history for a slot."""
        return self._upgrade_advice_repo.get_latest_advice_from_history(
            profile_name, slot, item_hash
        )

    def get_all_slots_latest_history(
        self,
        profile_name: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Get the latest history entry for all slots of a profile."""
        return self._upgrade_advice_repo.get_all_slots_latest_history(profile_name)

    def clear_upgrade_advice_history(
        self,
        profile_name: Optional[str] = None,
        slot: Optional[str] = None,
    ) -> int:
        """Clear upgrade advice history."""
        return self._upgrade_advice_repo.clear_upgrade_advice_history(profile_name, slot)

    # ----------------------------------------------------------------------
    # Verdict Statistics Persistence (delegated to VerdictRepository)
    # ----------------------------------------------------------------------

    def save_verdict_statistics(
        self,
        league: str,
        game_version: str,
        session_date: str,
        stats: Dict[str, Any],
    ) -> int:
        """Save or update verdict statistics for a session."""
        return self._verdict_repo.save_verdict_statistics(
            league, game_version, session_date, stats
        )

    def get_verdict_statistics(
        self,
        league: str,
        game_version: str = "poe1",
        session_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get verdict statistics for a specific session."""
        return self._verdict_repo.get_verdict_statistics(league, game_version, session_date)

    def get_verdict_statistics_history(
        self,
        league: str,
        game_version: str = "poe1",
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get verdict statistics history for a league."""
        return self._verdict_repo.get_verdict_statistics_history(league, game_version, days)

    def get_verdict_statistics_summary(
        self,
        league: str,
        game_version: str = "poe1",
    ) -> Dict[str, Any]:
        """Get aggregated verdict statistics for a league."""
        return self._verdict_repo.get_verdict_statistics_summary(league, game_version)

    def clear_verdict_statistics(
        self,
        league: Optional[str] = None,
        game_version: Optional[str] = None,
    ) -> int:
        """Clear verdict statistics."""
        return self._verdict_repo.clear_verdict_statistics(league, game_version)

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
