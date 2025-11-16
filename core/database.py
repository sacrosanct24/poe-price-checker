"""
SQLite database layer for the PoE Price Checker.
Handles all persistence: items, sales, prices, configs, plugins.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from contextlib import contextmanager
from core.game_version import GameVersion

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager with connection pooling and migrations.
    """

    # Current schema version
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = Path.home() / '.poe_price_checker' / 'data.db'

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create connection
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        logger.info(f"Database initialized: {self.db_path}")

        # Initialize schema
        self._initialize_schema()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        try:
            yield self.conn
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def _initialize_schema(self):
        """Create tables if they don't exist"""

        # Check if we need migration
        current_version = self._get_schema_version()

        if current_version == 0:
            # Fresh database
            self._create_schema()
            self._set_schema_version(self.SCHEMA_VERSION)
        elif current_version < self.SCHEMA_VERSION:
            # Migration needed
            logger.info(f"Migrating database from v{current_version} to v{self.SCHEMA_VERSION}")
            self._migrate_schema(current_version, self.SCHEMA_VERSION)

    def _get_schema_version(self) -> int:
        """Get current schema version"""
        try:
            cursor = self.conn.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.OperationalError:
            # Table doesn't exist
            return 0

    def _set_schema_version(self, version: int):
        """Set schema version"""
        self.conn.execute("""
                          CREATE TABLE IF NOT EXISTS schema_version
                          (
                              id
                              INTEGER
                              PRIMARY
                              KEY
                              AUTOINCREMENT,
                              version
                              INTEGER
                              NOT
                              NULL,
                              applied_at
                              TIMESTAMP
                              DEFAULT
                              CURRENT_TIMESTAMP
                          )
                          """)
        self.conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        self.conn.commit()

    def _create_schema(self):
        """Create all tables"""

        logger.info("Creating database schema...")

        with self.transaction():
            # Game configurations
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS game_configs
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  game_version
                                  TEXT
                                  NOT
                                  NULL
                                  UNIQUE,
                                  league
                                  TEXT
                                  NOT
                                  NULL,
                                  last_price_update
                                  TIMESTAMP,
                                  divine_chaos_rate
                                  REAL
                                  DEFAULT
                                  1.0
                              )
                              """)

            # Checked items history
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS checked_items
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  game_version
                                  TEXT
                                  NOT
                                  NULL,
                                  league
                                  TEXT
                                  NOT
                                  NULL,
                                  item_name
                                  TEXT
                                  NOT
                                  NULL,
                                  item_base_type
                                  TEXT,
                                  item_rarity
                                  TEXT,
                                  chaos_value
                                  REAL,
                                  divine_value
                                  REAL,
                                  stack_size
                                  INTEGER
                                  DEFAULT
                                  1,
                                  checked_at
                                  TIMESTAMP
                                  DEFAULT
                                  CURRENT_TIMESTAMP,
                                  raw_data
                                  TEXT
                              )
                              """)

            # Create index on checked_items
            self.conn.execute("""
                              CREATE INDEX IF NOT EXISTS idx_checked_items_name
                                  ON checked_items(item_name, game_version, league)
                              """)

            # Sales tracking
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS sales
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  item_id
                                  INTEGER,
                                  item_name
                                  TEXT
                                  NOT
                                  NULL,
                                  item_base_type
                                  TEXT,
                                  listed_price_chaos
                                  REAL
                                  NOT
                                  NULL,
                                  listed_at
                                  TIMESTAMP
                                  DEFAULT
                                  CURRENT_TIMESTAMP,
                                  sold_at
                                  TIMESTAMP,
                                  actual_price_chaos
                                  REAL,
                                  time_to_sale_hours
                                  REAL,
                                  relisted
                                  BOOLEAN
                                  DEFAULT
                                  0,
                                  notes
                                  TEXT,
                                  FOREIGN
                                  KEY
                              (
                                  item_id
                              ) REFERENCES checked_items
                              (
                                  id
                              ) ON DELETE SET NULL
                                  )
                              """)

            # Meta builds affixes (future)
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS meta_affixes
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  game_version
                                  TEXT
                                  NOT
                                  NULL,
                                  build_name
                                  TEXT,
                                  affix_text
                                  TEXT
                                  NOT
                                  NULL,
                                  priority
                                  INTEGER
                                  DEFAULT
                                  3,
                                  source_pob_url
                                  TEXT,
                                  updated_at
                                  TIMESTAMP
                                  DEFAULT
                                  CURRENT_TIMESTAMP
                              )
                              """)

            # Price history
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS price_history
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  game_version
                                  TEXT
                                  NOT
                                  NULL,
                                  league
                                  TEXT
                                  NOT
                                  NULL,
                                  item_name
                                  TEXT
                                  NOT
                                  NULL,
                                  item_base_type
                                  TEXT,
                                  chaos_value
                                  REAL
                                  NOT
                                  NULL,
                                  divine_value
                                  REAL,
                                  recorded_at
                                  TIMESTAMP
                                  DEFAULT
                                  CURRENT_TIMESTAMP
                              )
                              """)

            # Create index on price_history
            self.conn.execute("""
                              CREATE INDEX IF NOT EXISTS idx_price_history_lookup
                                  ON price_history(item_name, game_version, league, recorded_at DESC)
                              """)

            # Plugin state
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS plugin_state
                              (
                                  plugin_name
                                  TEXT
                                  PRIMARY
                                  KEY,
                                  enabled
                                  BOOLEAN
                                  DEFAULT
                                  1,
                                  config_json
                                  TEXT,
                                  last_run
                                  TIMESTAMP
                              )
                              """)

        logger.info("Database schema created successfully")

    def _migrate_schema(self, from_version: int, to_version: int):
        """Migrate database schema"""
        # Future migrations will go here
        logger.warning(f"No migrations defined for v{from_version} -> v{to_version}")
        self._set_schema_version(to_version)

    # === Checked Items ===

    def add_checked_item(
            self,
            game_version: GameVersion,
            league: str,
            item_name: str,
            item_base_type: Optional[str] = None,
            item_rarity: Optional[str] = None,
            chaos_value: Optional[float] = None,
            divine_value: Optional[float] = None,
            stack_size: int = 1,
            raw_data: Optional[str] = None
    ) -> int:
        """
        Add a checked item to history.

        Returns:
            Item ID
        """
        cursor = self.conn.execute("""
                                   INSERT INTO checked_items
                                   (game_version, league, item_name, item_base_type, item_rarity,
                                    chaos_value, divine_value, stack_size, raw_data)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                   """, (
                                       game_version.value, league, item_name, item_base_type, item_rarity,
                                       chaos_value, divine_value, stack_size, raw_data
                                   ))
        self.conn.commit()

        item_id = cursor.lastrowid
        logger.debug(f"Added checked item: {item_name} (ID: {item_id})")
        return item_id

    def get_checked_items(
            self,
            game_version: Optional[GameVersion] = None,
            league: Optional[str] = None,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recently checked items.

        Args:
            game_version: Filter by game version
            league: Filter by league
            limit: Maximum number of items

        Returns:
            List of item dicts
        """
        query = "SELECT * FROM checked_items WHERE 1=1"
        params = []

        if game_version:
            query += " AND game_version = ?"
            params.append(game_version.value)

        if league:
            query += " AND league = ?"
            params.append(league)

        query += " ORDER BY checked_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # === Sales Tracking ===

    def add_sale(
            self,
            item_name: str,
            listed_price_chaos: float,
            item_base_type: Optional[str] = None,
            item_id: Optional[int] = None
    ) -> int:
        """
        Record a new item listing for sale.

        Returns:
            Sale ID
        """
        cursor = self.conn.execute("""
                                   INSERT INTO sales (item_id, item_name, item_base_type, listed_price_chaos)
                                   VALUES (?, ?, ?, ?)
                                   """, (item_id, item_name, item_base_type, listed_price_chaos))
        self.conn.commit()

        sale_id = cursor.lastrowid
        logger.debug(f"Added sale listing: {item_name} at {listed_price_chaos}c (ID: {sale_id})")
        return sale_id

    def complete_sale(
            self,
            sale_id: int,
            actual_price_chaos: float,
            sold_at: Optional[datetime] = None
    ):
        """Mark a sale as completed"""
        if sold_at is None:
            sold_at = datetime.now()

        # Calculate time to sale
        cursor = self.conn.execute("SELECT listed_at FROM sales WHERE id = ?", (sale_id,))
        row = cursor.fetchone()

        if row:
            listed_at = datetime.fromisoformat(row[0])
            time_to_sale = (sold_at - listed_at).total_seconds() / 3600  # hours

            self.conn.execute("""
                              UPDATE sales
                              SET sold_at            = ?,
                                  actual_price_chaos = ?,
                                  time_to_sale_hours = ?
                              WHERE id = ?
                              """, (sold_at.isoformat(), actual_price_chaos, time_to_sale, sale_id))
            self.conn.commit()

            logger.info(f"Sale completed: ID {sale_id}, sold for {actual_price_chaos}c in {time_to_sale:.1f}h")

    def mark_sale_unsold(self, sale_id: int):
        """Mark a sale as not sold (after timeout)"""
        self.conn.execute("""
                          UPDATE sales
                          SET sold_at = ?,
                              notes   = 'Did not sell'
                          WHERE id = ?
                          """, (datetime.now().isoformat(), sale_id))
        self.conn.commit()
        logger.info(f"Sale marked unsold: ID {sale_id}")

    def get_sales(
            self,
            sold_only: bool = False,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get sales records.

        Args:
            sold_only: Only return completed sales
            limit: Maximum number of records

        Returns:
            List of sale dicts
        """
        query = "SELECT * FROM sales WHERE 1=1"

        if sold_only:
            query += " AND sold_at IS NOT NULL"

        query += " ORDER BY listed_at DESC LIMIT ?"

        cursor = self.conn.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # === Price History ===

    def add_price_snapshot(
            self,
            game_version: GameVersion,
            league: str,
            item_name: str,
            chaos_value: float,
            item_base_type: Optional[str] = None,
            divine_value: Optional[float] = None
    ):
        """Record a price snapshot for historical tracking"""
        self.conn.execute("""
                          INSERT INTO price_history
                          (game_version, league, item_name, item_base_type, chaos_value, divine_value)
                          VALUES (?, ?, ?, ?, ?, ?)
                          """, (game_version.value, league, item_name, item_base_type, chaos_value, divine_value))
        self.conn.commit()

    def get_price_history(
            self,
            item_name: str,
            game_version: GameVersion,
            league: str,
            days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get price history for an item"""
        cursor = self.conn.execute("""
                                   SELECT *
                                   FROM price_history
                                   WHERE item_name = ?
                                     AND game_version = ?
                                     AND league = ?
                                     AND recorded_at >= datetime('now', '-' || ? || ' days')
                                   ORDER BY recorded_at ASC
                                   """, (item_name, game_version.value, league, days))

        return [dict(row) for row in cursor.fetchall()]

    # === Plugin State ===

    def set_plugin_enabled(self, plugin_name: str, enabled: bool):
        """Enable or disable a plugin"""
        self.conn.execute("""
                          INSERT INTO plugin_state (plugin_name, enabled)
                          VALUES (?, ?) ON CONFLICT(plugin_name) DO
                          UPDATE SET enabled = ?
                          """, (plugin_name, enabled, enabled))
        self.conn.commit()

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled"""
        cursor = self.conn.execute(
            "SELECT enabled FROM plugin_state WHERE plugin_name = ?",
            (plugin_name,)
        )
        row = cursor.fetchone()
        return bool(row[0]) if row else False

    def set_plugin_config(self, plugin_name: str, config_json: str):
        """Save plugin configuration"""
        self.conn.execute("""
                          INSERT INTO plugin_state (plugin_name, config_json)
                          VALUES (?, ?) ON CONFLICT(plugin_name) DO
                          UPDATE SET config_json = ?
                          """, (plugin_name, config_json, config_json))
        self.conn.commit()

    def get_plugin_config(self, plugin_name: str) -> Optional[str]:
        """Get plugin configuration"""
        cursor = self.conn.execute(
            "SELECT config_json FROM plugin_state WHERE plugin_name = ?",
            (plugin_name,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # === Utility ===

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        stats = {}

        cursor = self.conn.execute("SELECT COUNT(*) FROM checked_items")
        stats['checked_items'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM sales")
        stats['sales'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM sales WHERE sold_at IS NOT NULL")
        stats['completed_sales'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM price_history")
        stats['price_snapshots'] = cursor.fetchone()[0]

        return stats

    def vacuum(self):
        """Optimize database (reclaim space)"""
        logger.info("Vacuuming database...")
        self.conn.execute("VACUUM")
        logger.info("Database vacuumed")

    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Database connection closed")


# Testing
if __name__ == "__main__":
    print("=== Database Test ===\n")

    # Create test database
    test_db_path = Path("test_poe.db")
    if test_db_path.exists():
        test_db_path.unlink()

    db = Database(test_db_path)

    # Test 1: Add checked items
    print("1. Adding checked items...")
    item_id1 = db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Keepers of the Flame",
        item_name="Shavronne's Wrappings",
        item_base_type="Occultist's Vestment",
        item_rarity="UNIQUE",
        chaos_value=355.2,
        divine_value=1.12
    )
    print(f"   ✓ Added item ID: {item_id1}")

    item_id2 = db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Keepers of the Flame",
        item_name="Divine Orb",
        item_rarity="CURRENCY",
        chaos_value=317.2,
        stack_size=5
    )
    print(f"   ✓ Added item ID: {item_id2}")

    # Test 2: Get checked items
    print("\n2. Retrieving checked items...")
    items = db.get_checked_items(game_version=GameVersion.POE1, limit=10)
    print(f"   ✓ Found {len(items)} items")
    for item in items:
        print(f"     - {item['item_name']}: {item['chaos_value']}c")

    # Test 3: Add sale
    print("\n3. Recording a sale...")
    sale_id = db.add_sale(
        item_name="Shavronne's Wrappings",
        listed_price_chaos=350.0,
        item_id=item_id1
    )
    print(f"   ✓ Sale ID: {sale_id}")

    # Test 4: Complete sale
    print("\n4. Completing sale...")
    db.complete_sale(sale_id, actual_price_chaos=340.0)
    print(f"   ✓ Sale completed")

    # Test 5: Price history
    print("\n5. Adding price snapshots...")
    for i in range(3):
        db.add_price_snapshot(
            game_version=GameVersion.POE1,
            league="Keepers of the Flame",
            item_name="Divine Orb",
            chaos_value=300.0 + i * 10
        )
    print(f"   ✓ Added 3 price snapshots")

    history = db.get_price_history("Divine Orb", GameVersion.POE1, "Keepers of the Flame")
    print(f"   ✓ Retrieved {len(history)} price points")

    # Test 6: Plugin state
    print("\n6. Testing plugin state...")
    db.set_plugin_enabled("price_alert", True)
    db.set_plugin_config("price_alert", '{"threshold": 100}')

    enabled = db.is_plugin_enabled("price_alert")
    config = db.get_plugin_config("price_alert")
    print(f"   ✓ Plugin enabled: {enabled}")
    print(f"   ✓ Plugin config: {config}")

    # Test 7: Stats
    print("\n7. Database statistics...")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Cleanup
    db.close()
    test_db_path.unlink()

    print("\n=== All Tests Passed! ===")