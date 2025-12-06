"""
Persistent Stash Storage Service.

Stores stash snapshots and valuation results locally for:
- Instant loading when opening stash viewer (no mandatory refresh)
- Generating diffs between stash updates
- Historical tracking of stash value over time

Storage Design:
- stash_snapshots: Metadata + JSON blobs for efficiency
- One "active" snapshot per account+league combination
- Optional history retention for analytics
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.database import Database
    from data_sources.poe_stash_api import StashSnapshot, StashTab
    from core.stash_valuator import ValuationResult

logger = logging.getLogger(__name__)


@dataclass
class StoredSnapshot:
    """A stored stash snapshot with valuation data."""

    id: int
    account_name: str
    league: str
    game_version: str
    total_items: int
    priced_items: int
    total_chaos_value: float
    fetched_at: datetime

    # Parsed from JSON columns
    snapshot_data: Optional[Dict[str, Any]] = None
    valuation_data: Optional[Dict[str, Any]] = None

    @property
    def display_total(self) -> str:
        """Format total value for display."""
        if self.total_chaos_value >= 1000:
            return f"{self.total_chaos_value:,.0f}c"
        return f"{self.total_chaos_value:.1f}c"


class StashStorageService:
    """
    Service for persisting stash snapshots and valuations.

    Usage:
        storage = StashStorageService(db)

        # Save after fetch
        storage.save_snapshot(snapshot, valuation_result)

        # Load on viewer open
        stored = storage.load_latest_snapshot("account", "league")
        if stored:
            # Reconstruct ValuationResult from stored.valuation_data
            pass
    """

    def __init__(self, db: "Database"):
        """
        Initialize the storage service.

        Args:
            db: Database instance for persistence.
        """
        self._db = db

    def save_snapshot(
        self,
        snapshot: "StashSnapshot",
        valuation: "ValuationResult",
        game_version: str = "poe1",
    ) -> int:
        """
        Save a stash snapshot and its valuation.

        Args:
            snapshot: Raw stash snapshot from API.
            valuation: Valuation result with priced items.
            game_version: "poe1" or "poe2".

        Returns:
            Row ID of saved snapshot.
        """
        # Serialize snapshot to JSON
        snapshot_json = self._serialize_snapshot(snapshot)

        # Serialize valuation to JSON
        valuation_json = self._serialize_valuation(valuation)

        # Insert into database
        cursor = self._db._execute(
            """
            INSERT INTO stash_snapshots (
                account_name, league, game_version,
                total_items, priced_items, total_chaos_value,
                snapshot_json, valuation_json, fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.account_name,
                snapshot.league,
                game_version,
                snapshot.total_items,
                valuation.priced_items,
                valuation.total_value,  # total_value is the field name
                snapshot_json,
                valuation_json,
                snapshot.fetched_at,
            ),
        )

        row_id = cursor.lastrowid or 0
        logger.info(
            f"Saved stash snapshot: {snapshot.account_name}/{snapshot.league} "
            f"({snapshot.total_items} items, {valuation.total_value:.0f}c)"
        )

        return row_id

    def load_latest_snapshot(
        self,
        account_name: str,
        league: str,
    ) -> Optional[StoredSnapshot]:
        """
        Load the most recent snapshot for an account/league.

        Args:
            account_name: PoE account name.
            league: League name.

        Returns:
            StoredSnapshot or None if no snapshot exists.
        """
        row = self._db._execute_fetchone(
            """
            SELECT
                id, account_name, league, game_version,
                total_items, priced_items, total_chaos_value,
                snapshot_json, valuation_json, fetched_at
            FROM stash_snapshots
            WHERE account_name = ? AND league = ?
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (account_name, league),
        )

        if not row:
            return None

        return self._row_to_stored_snapshot(row)

    def get_snapshot_history(
        self,
        account_name: str,
        league: str,
        limit: int = 10,
    ) -> List[StoredSnapshot]:
        """
        Get snapshot history for an account/league.

        Args:
            account_name: PoE account name.
            league: League name.
            limit: Maximum snapshots to return.

        Returns:
            List of StoredSnapshots, newest first.
        """
        rows = self._db._execute_fetchall(
            """
            SELECT
                id, account_name, league, game_version,
                total_items, priced_items, total_chaos_value,
                snapshot_json, valuation_json, fetched_at
            FROM stash_snapshots
            WHERE account_name = ? AND league = ?
            ORDER BY fetched_at DESC
            LIMIT ?
            """,
            (account_name, league, limit),
        )

        return [self._row_to_stored_snapshot(row) for row in rows]

    def delete_old_snapshots(
        self,
        account_name: str,
        league: str,
        keep_count: int = 5,
    ) -> int:
        """
        Delete old snapshots, keeping only the most recent ones.

        Args:
            account_name: PoE account name.
            league: League name.
            keep_count: Number of recent snapshots to keep.

        Returns:
            Number of deleted rows.
        """
        # Get IDs to keep
        rows = self._db._execute_fetchall(
            """
            SELECT id FROM stash_snapshots
            WHERE account_name = ? AND league = ?
            ORDER BY fetched_at DESC
            LIMIT ?
            """,
            (account_name, league, keep_count),
        )

        keep_ids = [row["id"] for row in rows]

        if not keep_ids:
            return 0

        # Delete all others
        placeholders = ",".join("?" * len(keep_ids))
        # nosec B608 - placeholders are constructed from list length, all values parameterized
        cursor = self._db._execute(
            f"""
            DELETE FROM stash_snapshots
            WHERE account_name = ? AND league = ?
              AND id NOT IN ({placeholders})
            """,
            (account_name, league, *keep_ids),
        )

        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"Deleted {deleted} old snapshots for {account_name}/{league}")

        return deleted

    def reconstruct_valuation(
        self,
        stored: StoredSnapshot,
    ) -> Optional["ValuationResult"]:
        """
        Reconstruct a ValuationResult from stored data.

        Args:
            stored: StoredSnapshot with valuation_data.

        Returns:
            ValuationResult or None if reconstruction fails.
        """
        if not stored.valuation_data:
            return None

        try:
            from core.stash_valuator import (
                ValuationResult,
                PricedTab,
                PricedItem,
                PriceSource,
            )

            data = stored.valuation_data

            # Reconstruct tabs
            tabs = []
            for tab_data in data.get("tabs", []):
                # Reconstruct items for this tab
                items = []
                for item_data in tab_data.get("items", []):
                    # Map price source string back to enum
                    source_str = item_data.get("price_source", "")
                    if source_str == "poe_ninja":
                        source = PriceSource.POE_NINJA
                    elif source_str == "poe_prices":
                        source = PriceSource.POE_PRICES
                    else:
                        source = PriceSource.UNKNOWN

                    item = PricedItem(
                        name=item_data.get("name", ""),
                        type_line=item_data.get("type_line", ""),
                        base_type=item_data.get("base_type", ""),
                        item_class=item_data.get("item_class", ""),
                        stack_size=item_data.get("stack_size", 1),
                        ilvl=item_data.get("ilvl", 0),
                        rarity=item_data.get("rarity", "Normal"),
                        identified=item_data.get("identified", True),
                        corrupted=item_data.get("corrupted", False),
                        links=item_data.get("links", 0),
                        sockets=item_data.get("sockets", ""),
                        icon=item_data.get("icon", ""),
                        raw_item=item_data.get("raw_item", {}),
                        unit_price=item_data.get("unit_price", 0.0),
                        total_price=item_data.get("total_price", 0.0),
                        price_source=source,
                        confidence=item_data.get("confidence", ""),
                        price_min=item_data.get("price_min", 0.0),
                        price_max=item_data.get("price_max", 0.0),
                        tab_name=item_data.get("tab_name", ""),
                        tab_index=item_data.get("tab_index", 0),
                        x=item_data.get("x", 0),
                        y=item_data.get("y", 0),
                    )
                    items.append(item)

                tab = PricedTab(
                    id=tab_data.get("id", ""),
                    name=tab_data.get("name", ""),
                    index=tab_data.get("index", 0),
                    tab_type=tab_data.get("tab_type", ""),
                    items=items,
                    total_value=tab_data.get("total_value", 0.0),
                    valuable_count=tab_data.get("valuable_count", 0),
                )
                tabs.append(tab)

            result = ValuationResult(
                league=data.get("league", ""),
                account_name=data.get("account_name", ""),
                tabs=tabs,
                total_value=data.get("total_value", 0.0),
                total_items=data.get("total_items", 0),
                priced_items=data.get("priced_items", 0),
                unpriced_items=data.get("unpriced_items", 0),
                errors=data.get("errors", []),
            )

            return result

        except Exception as e:
            logger.error(f"Failed to reconstruct valuation: {e}")
            return None

    def reconstruct_snapshot(
        self,
        stored: StoredSnapshot,
    ) -> Optional["StashSnapshot"]:
        """
        Reconstruct a StashSnapshot from stored data (for diff engine).

        Args:
            stored: StoredSnapshot with snapshot_data.

        Returns:
            StashSnapshot or None if reconstruction fails.
        """
        if not stored.snapshot_data:
            return None

        try:
            from data_sources.poe_stash_api import StashSnapshot, StashTab

            data = stored.snapshot_data

            # Reconstruct tabs
            tabs = []
            for tab_data in data.get("tabs", []):
                # Reconstruct children
                children = []
                for child_data in tab_data.get("children", []):
                    child = StashTab(
                        id=child_data.get("id", ""),
                        name=child_data.get("name", ""),
                        index=child_data.get("index", 0),
                        type=child_data.get("type", "NormalStash"),
                        items=child_data.get("items", []),
                        folder=child_data.get("folder"),
                    )
                    children.append(child)

                tab = StashTab(
                    id=tab_data.get("id", ""),
                    name=tab_data.get("name", ""),
                    index=tab_data.get("index", 0),
                    type=tab_data.get("type", "NormalStash"),
                    items=tab_data.get("items", []),
                    folder=tab_data.get("folder"),
                    children=children,
                )
                tabs.append(tab)

            snapshot = StashSnapshot(
                account_name=data.get("account_name", ""),
                league=data.get("league", ""),
                tabs=tabs,
                total_items=data.get("total_items", 0),
                fetched_at=data.get("fetched_at", ""),
            )

            return snapshot

        except Exception as e:
            logger.error(f"Failed to reconstruct snapshot: {e}")
            return None

    def _serialize_snapshot(self, snapshot: "StashSnapshot") -> str:
        """Serialize a StashSnapshot to JSON."""
        data = {
            "account_name": snapshot.account_name,
            "league": snapshot.league,
            "total_items": snapshot.total_items,
            "fetched_at": snapshot.fetched_at,
            "tabs": [],
        }

        for tab in snapshot.tabs:
            tab_data = {
                "id": tab.id,
                "name": tab.name,
                "index": tab.index,
                "type": tab.type,
                "items": tab.items,  # Already list of dicts
                "folder": tab.folder,
                "children": [],
            }

            for child in tab.children:
                child_data = {
                    "id": child.id,
                    "name": child.name,
                    "index": child.index,
                    "type": child.type,
                    "items": child.items,
                    "folder": child.folder,
                }
                tab_data["children"].append(child_data)

            data["tabs"].append(tab_data)

        return json.dumps(data)

    def _serialize_valuation(self, valuation: "ValuationResult") -> str:
        """Serialize a ValuationResult to JSON."""
        data = {
            "league": valuation.league,
            "account_name": valuation.account_name,
            "total_value": valuation.total_value,
            "total_items": valuation.total_items,
            "priced_items": valuation.priced_items,
            "unpriced_items": valuation.unpriced_items,
            "errors": valuation.errors,
            "tabs": [],
        }

        for tab in valuation.tabs:
            tab_data = {
                "id": tab.id,
                "name": tab.name,
                "index": tab.index,
                "tab_type": tab.tab_type,
                "total_value": tab.total_value,
                "valuable_count": tab.valuable_count,
                "items": [],
            }

            for item in tab.items:
                item_data = {
                    "name": item.name,
                    "type_line": item.type_line,
                    "base_type": item.base_type,
                    "item_class": item.item_class,
                    "stack_size": item.stack_size,
                    "ilvl": item.ilvl,
                    "rarity": item.rarity,
                    "identified": item.identified,
                    "corrupted": item.corrupted,
                    "links": item.links,
                    "sockets": item.sockets,
                    "icon": item.icon,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "price_source": item.price_source.value if hasattr(item.price_source, 'value') else str(item.price_source),
                    "confidence": item.confidence,
                    "price_min": item.price_min,
                    "price_max": item.price_max,
                    "tab_name": item.tab_name,
                    "tab_index": item.tab_index,
                    "x": item.x,
                    "y": item.y,
                    # Don't store raw_item - it's redundant with snapshot
                }
                tab_data["items"].append(item_data)

            data["tabs"].append(tab_data)

        return json.dumps(data)

    def _row_to_stored_snapshot(self, row) -> StoredSnapshot:
        """Convert a database row to StoredSnapshot."""
        # Parse JSON columns
        snapshot_data = None
        valuation_data = None

        if row["snapshot_json"]:
            try:
                snapshot_data = json.loads(row["snapshot_json"])
            except json.JSONDecodeError:
                pass

        if row["valuation_json"]:
            try:
                valuation_data = json.loads(row["valuation_json"])
            except json.JSONDecodeError:
                pass

        # Parse fetched_at timestamp
        fetched_at = row["fetched_at"]
        if isinstance(fetched_at, str):
            try:
                fetched_at = datetime.fromisoformat(fetched_at)
            except ValueError:
                fetched_at = datetime.now()

        return StoredSnapshot(
            id=row["id"],
            account_name=row["account_name"],
            league=row["league"],
            game_version=row["game_version"],
            total_items=row["total_items"],
            priced_items=row["priced_items"],
            total_chaos_value=row["total_chaos_value"],
            fetched_at=fetched_at,
            snapshot_data=snapshot_data,
            valuation_data=valuation_data,
        )


# Singleton instance
_storage_instance: Optional[StashStorageService] = None


def get_stash_storage(db: "Database") -> StashStorageService:
    """
    Get or create the stash storage service singleton.

    Args:
        db: Database instance.

    Returns:
        StashStorageService instance.
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StashStorageService(db)
    return _storage_instance


def reset_stash_storage() -> None:
    """Reset the singleton (for testing)."""
    global _storage_instance
    _storage_instance = None
