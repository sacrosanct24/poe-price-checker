"""
Mod Database Manager

Stores Path of Exile mod/affix data in a local SQLite database.
Data is fetched from the PoE Wiki Cargo API and cached locally.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ModDatabase:
    """
    Manages a local SQLite database of PoE mod/affix data.

    The database stores:
    - Mod definitions with tier ranges
    - Stat IDs and display text
    - Spawn weights and requirements
    - Metadata (league, last update time)
    """

    DEFAULT_DB_PATH = Path("data/mods.db")

    SCHEMA = """
    -- Mod data table
    CREATE TABLE IF NOT EXISTS mods (
        id TEXT PRIMARY KEY,
        name TEXT,
        stat_text TEXT,
        stat_text_raw TEXT,
        domain INTEGER,
        generation_type INTEGER,
        mod_group TEXT,
        required_level INTEGER,
        tier_text TEXT,
        stat1_id TEXT,
        stat1_min INTEGER,
        stat1_max INTEGER,
        stat2_id TEXT,
        stat2_min INTEGER,
        stat2_max INTEGER,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_mods_stat_text ON mods(stat_text);
    CREATE INDEX IF NOT EXISTS idx_mods_stat1_id ON mods(stat1_id);
    CREATE INDEX IF NOT EXISTS idx_mods_generation_type ON mods(generation_type);
    CREATE INDEX IF NOT EXISTS idx_mods_domain ON mods(domain);

    -- Items table (unique items, etc.)
    CREATE TABLE IF NOT EXISTS items (
        name TEXT PRIMARY KEY,
        base_item TEXT,
        item_class TEXT,
        rarity TEXT,
        required_level INTEGER,
        drop_enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Indexes for items
    CREATE INDEX IF NOT EXISTS idx_items_base_item ON items(base_item);
    CREATE INDEX IF NOT EXISTS idx_items_class ON items(item_class);
    CREATE INDEX IF NOT EXISTS idx_items_rarity ON items(rarity);

    -- Metadata table for tracking updates
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the mod database.

        Args:
            db_path: Path to SQLite database file (default: data/mods.db)
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection = self._init_database()

    def _init_database(self) -> sqlite3.Connection:
        """Initialize database schema if needed."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        conn.executescript(self.SCHEMA)
        conn.commit()
        logger.info(f"Initialized mod database at {self.db_path}")
        return conn

    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        cursor = self.conn.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        return row['value'] if row else None

    def set_metadata(self, key: str, value: str) -> None:
        """Set metadata key-value pair."""
        self.conn.execute(
            """
            INSERT INTO metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value)
        )
        self.conn.commit()

    def get_last_update_time(self) -> Optional[datetime]:
        """Get the last database update timestamp."""
        value = self.get_metadata('last_update')
        if value:
            return datetime.fromisoformat(value)
        return None

    def get_current_league(self) -> Optional[str]:
        """Get the league for which data was last fetched."""
        return self.get_metadata('league')

    def should_update(self, current_league: str) -> bool:
        """
        Check if database needs updating.

        Returns True if:
        - Database is empty
        - League has changed
        - Data is older than 7 days
        """
        stored_league = self.get_current_league()
        if not stored_league or stored_league != current_league:
            logger.info(f"League changed: {stored_league} -> {current_league}")
            return True

        last_update = self.get_last_update_time()
        if not last_update:
            logger.info("No update timestamp found")
            return True

        # Check if data is stale (>7 days)
        age_days = (datetime.now() - last_update).days
        if age_days > 7:
            logger.info(f"Data is {age_days} days old, updating")
            return True

        return False

    def insert_mods(self, mods: List[Dict[str, Any]]) -> int:
        """
        Insert or update mod records in bulk.

        Args:
            mods: List of mod dictionaries from Cargo API

        Returns:
            Number of mods inserted/updated
        """
        cursor = self.conn.cursor()
        count = 0

        for mod in mods:
            try:
                # Handle both space-separated (API) and underscore (local) field names
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO mods (
                        id, name, stat_text, stat_text_raw, domain, generation_type,
                        mod_group, required_level, tier_text,
                        stat1_id, stat1_min, stat1_max,
                        stat2_id, stat2_min, stat2_max,
                        tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mod.get('id'),
                        mod.get('name'),
                        mod.get('stat text') or mod.get('stat_text'),
                        mod.get('stat text raw') or mod.get('stat_text_raw'),
                        mod.get('domain'),
                        mod.get('generation type') or mod.get('generation_type'),
                        mod.get('mod groups') or mod.get('mod_group'),
                        mod.get('required level') or mod.get('required_level'),
                        mod.get('tier text') or mod.get('tier_text'),
                        mod.get('stat1 id') or mod.get('stat1_id'),
                        mod.get('stat1 min') or mod.get('stat1_min'),
                        mod.get('stat1 max') or mod.get('stat1_max'),
                        mod.get('stat2 id') or mod.get('stat2_id'),
                        mod.get('stat2 min') or mod.get('stat2_min'),
                        mod.get('stat2 max') or mod.get('stat2_max'),
                        mod.get('tags'),
                    )
                )
                count += 1
            except sqlite3.Error as e:
                logger.warning(f"Failed to insert mod {mod.get('id')}: {e}")
                continue

        self.conn.commit()
        logger.info(f"Inserted/updated {count} mods")
        return count

    def find_mods_by_stat_text(
        self,
        stat_text_pattern: str,
        generation_type: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find mods matching a stat text pattern.

        Args:
            stat_text_pattern: SQL LIKE pattern (e.g., "%maximum Life")
            generation_type: 6=prefix, 7=suffix, None=all

        Returns:
            List of matching mod dictionaries
        """
        # Search in stat_text_raw (plain text) for better pattern matching
        query = "SELECT * FROM mods WHERE (stat_text_raw LIKE ? OR stat_text LIKE ?)"
        params: List[Any] = [stat_text_pattern, stat_text_pattern]

        if generation_type is not None:
            query += " AND generation_type = ?"
            params.append(generation_type)

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_affix_tiers(
        self,
        stat_text_pattern: str,
        generation_type: Optional[int] = None,
    ) -> List[Tuple[int, int, int]]:
        """
        Get tier ranges for an affix (T1, T2, T3, etc.).

        Returns list of (tier_number, min_value, max_value) sorted by tier.

        Args:
            stat_text_pattern: Pattern to match (e.g., "%to maximum Life")
            generation_type: 6=prefix, 7=suffix, None=all

        Returns:
            List of (tier, min, max) tuples, sorted best to worst
        """
        import re

        mods = self.find_mods_by_stat_text(stat_text_pattern, generation_type)

        if not mods:
            return []

        # Extract tier info and value ranges from mods
        tier_data = []
        for mod in mods:
            tier_text = mod.get('tier_text') or ''
            stat_text = mod.get('stat_text_raw') or mod.get('stat_text') or ''

            # Parse tier number from tier_text (e.g., "Tier 1", "Tier 2")
            tier_match = re.search(r'Tier\s*(\d+)', tier_text, re.IGNORECASE)
            tier_num = int(tier_match.group(1)) if tier_match else 99

            # Parse value range from stat_text (e.g., "+(80-89) to maximum Life")
            # Patterns: (min-max), +min, min%
            range_match = re.search(r'\((\d+)-(\d+)\)', stat_text)
            if range_match:
                min_val = int(range_match.group(1))
                max_val = int(range_match.group(2))
            else:
                # Try single value pattern
                single_match = re.search(r'[+\-]?(\d+)', stat_text)
                if single_match:
                    val = int(single_match.group(1))
                    min_val = max_val = val
                else:
                    continue  # Skip if no values found

            tier_data.append((tier_num, min_val, max_val, mod.get('name')))

        if not tier_data:
            return []

        # Sort by tier number (T1 first)
        tier_data.sort(key=lambda x: (x[0], -x[2]))  # Sort by tier, then by max value descending

        # Return unique tiers
        seen_tiers = set()
        result = []
        for tier_num, min_val, max_val, name in tier_data:
            if tier_num not in seen_tiers:
                seen_tiers.add(tier_num)
                result.append((tier_num, min_val, max_val))

        return result

    def get_mod_count(self) -> int:
        """Get total number of mods in database."""
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM mods")
        row = cursor.fetchone()
        return int(row['count']) if row else 0

    # =========================================================================
    # Items table methods
    # =========================================================================

    def insert_items(self, items: List[Dict[str, Any]]) -> int:
        """
        Insert or update item records in bulk.

        Args:
            items: List of item dictionaries from Cargo API

        Returns:
            Number of items inserted/updated
        """
        cursor = self.conn.cursor()
        count = 0

        for item in items:
            try:
                # Handle both space-separated (API) and underscore (local) field names
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO items (
                        name, base_item, item_class, rarity, required_level, drop_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.get('name'),
                        item.get('base item') or item.get('base_item'),
                        item.get('class') or item.get('item_class'),
                        item.get('rarity'),
                        item.get('required level') or item.get('required_level'),
                        item.get('drop enabled') or item.get('drop_enabled', 1),
                    )
                )
                count += 1
            except sqlite3.Error as e:
                logger.warning(f"Failed to insert item {item.get('name')}: {e}")
                continue

        self.conn.commit()
        logger.info(f"Inserted/updated {count} items")
        return count

    def find_unique_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a unique item by its name.

        Args:
            name: Unique item name (e.g., "Headhunter")

        Returns:
            Item dictionary or None if not found
        """
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE name = ? AND rarity = 'Unique'",
            (name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_items_by_base(self, base_item: str) -> List[Dict[str, Any]]:
        """
        Find all items that use a specific base type.

        Args:
            base_item: Base item name (e.g., "Leather Belt")

        Returns:
            List of matching item dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE base_item = ?",
            (base_item,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_unique_items_by_class(self, item_class: str) -> List[Dict[str, Any]]:
        """
        Get all unique items of a specific class.

        Args:
            item_class: Item class (e.g., "Belt", "Helmet", "Body Armour")

        Returns:
            List of unique item dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE item_class = ? AND rarity = 'Unique'",
            (item_class,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_item_count(self) -> int:
        """Get total number of items in database."""
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM items")
        row = cursor.fetchone()
        return int(row['count']) if row else 0

    def get_unique_item_count(self) -> int:
        """Get number of unique items in database."""
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM items WHERE rarity = 'Unique'"
        )
        row = cursor.fetchone()
        return int(row['count']) if row else 0

    def get_items_by_class(self, item_class: str) -> List[Dict[str, Any]]:
        """
        Get all items of a specific class.

        Args:
            item_class: Item class (e.g., "Divination Card", "Skill Gem")

        Returns:
            List of item dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE item_class = ?",
            (item_class,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_divination_cards(self) -> List[Dict[str, Any]]:
        """Get all divination cards."""
        return self.get_items_by_class("Divination Card")

    def get_skill_gems(self) -> List[Dict[str, Any]]:
        """Get all skill gems (active and support)."""
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE item_class IN ('Skill Gem', 'Support Gem')"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_scarabs(self) -> List[Dict[str, Any]]:
        """Get all scarabs."""
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE name LIKE '%Scarab%'"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_currency_items(self) -> List[Dict[str, Any]]:
        """Get all currency items."""
        return self.get_items_by_class("Currency Item")

    def find_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find any item by exact name.

        Args:
            name: Item name (e.g., "House of Mirrors", "Enlighten Support")

        Returns:
            Item dictionary or None if not found
        """
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_items(self, name_pattern: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search items by name pattern.

        Args:
            name_pattern: SQL LIKE pattern (e.g., "%Scarab%", "House of%")
            limit: Maximum results to return

        Returns:
            List of matching item dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE name LIKE ? LIMIT ?",
            (name_pattern, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None  # type: ignore[assignment]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
