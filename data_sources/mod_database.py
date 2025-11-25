"""
Mod Database Manager

Stores Path of Exile mod/affix data in a local SQLite database.
Data is fetched from the PoE Wiki Cargo API and cached locally.
"""
from __future__ import annotations

import json
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
        name TEXT NOT NULL,
        stat_text TEXT,
        domain INTEGER,
        generation_type INTEGER,
        mod_group TEXT,
        required_level INTEGER,
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
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema if needed."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()
        logger.info(f"Initialized mod database at {self.db_path}")

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
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO mods (
                        id, name, stat_text, domain, generation_type,
                        mod_group, required_level,
                        stat1_id, stat1_min, stat1_max,
                        stat2_id, stat2_min, stat2_max,
                        tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mod.get('id'),
                        mod.get('name'),
                        mod.get('stat text') or mod.get('stat_text'),
                        mod.get('domain'),
                        mod.get('generation type') or mod.get('generation_type'),
                        mod.get('mod group') or mod.get('mod_group'),
                        mod.get('required level') or mod.get('required_level'),
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
        query = "SELECT * FROM mods WHERE stat_text LIKE ?"
        params = [stat_text_pattern]

        if generation_type is not None:
            query += " AND generation_type = ?"
            params.append(generation_type)

        query += " ORDER BY stat1_max DESC"

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
        mods = self.find_mods_by_stat_text(stat_text_pattern, generation_type)

        if not mods:
            return []

        # Sort by max value (highest first = T1)
        mods_sorted = sorted(
            mods,
            key=lambda m: (m.get('stat1_max') or 0),
            reverse=True
        )

        # Assign tier numbers
        tiers = []
        for tier_num, mod in enumerate(mods_sorted[:10], start=1):  # Top 10 tiers
            min_val = mod.get('stat1_min')
            max_val = mod.get('stat1_max')
            if min_val is not None and max_val is not None:
                tiers.append((tier_num, min_val, max_val))

        return tiers

    def get_mod_count(self) -> int:
        """Get total number of mods in database."""
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM mods")
        return cursor.fetchone()['count']

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
