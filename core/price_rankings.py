"""
Top 20 Price Rankings with local caching.

Provides cached top 20 items by median price for various categories:
- Currency
- Uniques (by slot: weapons, armour, accessories, flasks, jewels)
- Fragments
- Divination Cards
- Essences, Fossils, Scarabs, Oils, Incubators, Vials

Cache is stored locally and only refreshed after 5 days.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache expiry in days
CACHE_EXPIRY_DAYS = 5


@dataclass
class RankedItem:
    """A single ranked item with price information."""
    rank: int
    name: str
    chaos_value: float
    divine_value: Optional[float] = None
    base_type: Optional[str] = None
    icon: Optional[str] = None

    # For uniques, track the item type
    item_class: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RankedItem":
        """Create from dictionary."""
        return cls(
            rank=data.get("rank", 0),
            name=data.get("name", ""),
            chaos_value=data.get("chaos_value", 0.0),
            divine_value=data.get("divine_value"),
            base_type=data.get("base_type"),
            icon=data.get("icon"),
            item_class=data.get("item_class"),
        )


@dataclass
class CategoryRanking:
    """Rankings for a single category."""
    category: str
    display_name: str
    items: List[RankedItem] = field(default_factory=list)
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "display_name": self.display_name,
            "items": [item.to_dict() for item in self.items],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CategoryRanking":
        """Create from dictionary."""
        return cls(
            category=data.get("category", ""),
            display_name=data.get("display_name", ""),
            items=[RankedItem.from_dict(item) for item in data.get("items", [])],
            updated_at=data.get("updated_at"),
        )


class PriceRankingCache:
    """
    Manages cached price rankings with file-based storage.

    Rankings are stored in JSON format and refreshed after 5 days.
    """

    # Category definitions with display names
    CATEGORIES = {
        # Currency
        "currency": "Currency",

        # Uniques by slot
        "unique_weapons": "Unique Weapons",
        "unique_armour": "Unique Armour",
        "unique_accessories": "Unique Accessories",
        "unique_flasks": "Unique Flasks",
        "unique_jewels": "Unique Jewels",

        # Other item types
        "fragments": "Fragments",
        "divination_cards": "Divination Cards",
        "essences": "Essences",
        "fossils": "Fossils",
        "scarabs": "Scarabs",
        "oils": "Oils",
        "incubators": "Incubators",
        "vials": "Vials",
    }

    # Map categories to poe.ninja API types
    CATEGORY_TO_API_TYPE = {
        "currency": "Currency",
        "unique_weapons": "UniqueWeapon",
        "unique_armour": "UniqueArmour",
        "unique_accessories": "UniqueAccessory",
        "unique_flasks": "UniqueFlask",
        "unique_jewels": "UniqueJewel",
        "fragments": "Fragment",
        "divination_cards": "DivinationCard",
        "essences": "Essence",
        "fossils": "Fossil",
        "scarabs": "Scarab",
        "oils": "Oil",
        "incubators": "Incubator",
        "vials": "Vial",
    }

    # Equipment slots for unique items
    EQUIPMENT_SLOTS = {
        # Armour slots
        "helmet": ("UniqueArmour", "Helmet"),
        "body_armour": ("UniqueArmour", "Body Armour"),
        "gloves": ("UniqueArmour", "Gloves"),
        "boots": ("UniqueArmour", "Boots"),
        "shield": ("UniqueArmour", "Shield"),
        "quiver": ("UniqueArmour", "Quiver"),
        # Accessory slots
        "amulet": ("UniqueAccessory", "Amulet"),
        "ring": ("UniqueAccessory", "Ring"),
        "belt": ("UniqueAccessory", "Belt"),
        # Weapon slots (grouped)
        "one_handed_weapon": ("UniqueWeapon", ["One Handed Sword", "One Handed Axe", "One Handed Mace", "Claw", "Dagger", "Wand"]),
        "two_handed_weapon": ("UniqueWeapon", ["Two Handed Sword", "Two Handed Axe", "Two Handed Mace", "Staff", "Bow"]),
        # Individual weapon types
        "sword": ("UniqueWeapon", ["One Handed Sword", "Two Handed Sword"]),
        "axe": ("UniqueWeapon", ["One Handed Axe", "Two Handed Axe"]),
        "mace": ("UniqueWeapon", ["One Handed Mace", "Two Handed Mace"]),
        "bow": ("UniqueWeapon", "Bow"),
        "staff": ("UniqueWeapon", "Staff"),
        "wand": ("UniqueWeapon", "Wand"),
        "claw": ("UniqueWeapon", "Claw"),
        "dagger": ("UniqueWeapon", "Dagger"),
    }

    SLOT_DISPLAY_NAMES = {
        "helmet": "Helmets",
        "body_armour": "Body Armours",
        "gloves": "Gloves",
        "boots": "Boots",
        "shield": "Shields",
        "quiver": "Quivers",
        "amulet": "Amulets",
        "ring": "Rings",
        "belt": "Belts",
        "one_handed_weapon": "One-Handed Weapons",
        "two_handed_weapon": "Two-Handed Weapons",
        "sword": "Swords",
        "axe": "Axes",
        "mace": "Maces",
        "bow": "Bows",
        "staff": "Staves",
        "wand": "Wands",
        "claw": "Claws",
        "dagger": "Daggers",
    }

    def __init__(self, cache_dir: Optional[Path] = None, league: str = "Standard"):
        """
        Initialize the price ranking cache.

        Args:
            cache_dir: Directory for cache files. Defaults to ~/.poe_price_checker/
            league: League name for pricing data
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".poe_price_checker"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.league = league
        self._cache_file = self.cache_dir / f"price_rankings_{league.lower().replace(' ', '_')}.json"

        # In-memory cache
        self._rankings: Dict[str, CategoryRanking] = {}
        self._cache_metadata: Dict[str, Any] = {}

        # Load existing cache
        self._load_cache()

        logger.info(f"PriceRankingCache initialized for league: {league}")

    def _load_cache(self) -> None:
        """Load rankings from cache file."""
        if not self._cache_file.exists():
            logger.info("No cache file found, will fetch fresh data")
            return

        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._cache_metadata = data.get("metadata", {})

            for cat_data in data.get("rankings", []):
                ranking = CategoryRanking.from_dict(cat_data)
                self._rankings[ranking.category] = ranking

            logger.info(f"Loaded {len(self._rankings)} category rankings from cache")

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self._rankings = {}
            self._cache_metadata = {}

    def _save_cache(self) -> None:
        """Save rankings to cache file."""
        try:
            data = {
                "metadata": {
                    "league": self.league,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "version": 1,
                },
                "rankings": [ranking.to_dict() for ranking in self._rankings.values()],
            }

            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self._rankings)} category rankings to cache")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def is_cache_valid(self, category: Optional[str] = None) -> bool:
        """
        Check if cache is still valid (not expired).

        Args:
            category: Specific category to check, or None for overall cache

        Returns:
            True if cache is valid and not expired
        """
        if category:
            ranking = self._rankings.get(category)
            if not ranking or not ranking.updated_at:
                return False
            updated_at = ranking.updated_at
        else:
            updated_at = self._cache_metadata.get("last_updated")
            if not updated_at:
                return False

        try:
            updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            expiry = updated_dt + timedelta(days=CACHE_EXPIRY_DAYS)
            return datetime.now(timezone.utc) < expiry
        except (ValueError, AttributeError):
            return False

    def get_cache_age_days(self) -> Optional[float]:
        """Get the age of the cache in days."""
        updated_at = self._cache_metadata.get("last_updated")
        if not updated_at:
            return None

        try:
            updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - updated_dt
            return age.total_seconds() / 86400  # Convert to days
        except (ValueError, AttributeError):
            return None

    def get_ranking(self, category: str) -> Optional[CategoryRanking]:
        """
        Get cached ranking for a category.

        Args:
            category: Category key (e.g., "currency", "unique_weapons")

        Returns:
            CategoryRanking if cached, None otherwise
        """
        return self._rankings.get(category)

    def get_all_rankings(self) -> Dict[str, CategoryRanking]:
        """Get all cached rankings."""
        return self._rankings.copy()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._rankings = {}
        self._cache_metadata = {}
        if self._cache_file.exists():
            self._cache_file.unlink()
        logger.info("Cache cleared")


class Top20Calculator:
    """
    Calculates top 20 items by price for each category.

    Uses PoE Ninja API to fetch current prices and ranks items.
    """

    def __init__(self, cache: PriceRankingCache, poe_ninja_api: Any = None):
        """
        Initialize the calculator.

        Args:
            cache: PriceRankingCache instance for storage
            poe_ninja_api: Optional PoeNinjaAPI instance (created if not provided)
        """
        self.cache = cache
        self._api = poe_ninja_api

    @property
    def api(self):
        """Lazy-load PoE Ninja API."""
        if self._api is None:
            from data_sources.pricing.poe_ninja import PoeNinjaAPI
            self._api = PoeNinjaAPI(league=self.cache.league)
        return self._api

    def refresh_all(self, force: bool = False) -> Dict[str, CategoryRanking]:
        """
        Refresh all category rankings.

        Args:
            force: If True, refresh even if cache is valid

        Returns:
            Dict of category -> CategoryRanking
        """
        if not force and self.cache.is_cache_valid():
            age = self.cache.get_cache_age_days()
            logger.info(f"Cache is valid ({age:.1f} days old), skipping refresh")
            return self.cache.get_all_rankings()

        logger.info("Refreshing all price rankings...")

        # Get divine rate for conversions
        divine_rate = self.api.ensure_divine_rate()

        # Refresh each category
        for category in PriceRankingCache.CATEGORIES:
            try:
                self._refresh_category(category, divine_rate)
            except Exception as e:
                logger.error(f"Failed to refresh {category}: {e}")

        # Save to file
        self.cache._save_cache()

        return self.cache.get_all_rankings()

    def refresh_category(self, category: str, force: bool = False) -> Optional[CategoryRanking]:
        """
        Refresh a single category ranking.

        Args:
            category: Category key to refresh
            force: If True, refresh even if cache is valid

        Returns:
            CategoryRanking if successful
        """
        if not force and self.cache.is_cache_valid(category):
            return self.cache.get_ranking(category)

        divine_rate = self.api.ensure_divine_rate()
        ranking = self._refresh_category(category, divine_rate)
        self.cache._save_cache()
        return ranking

    def _refresh_category(self, category: str, divine_rate: float) -> Optional[CategoryRanking]:
        """
        Internal method to refresh a category.

        Args:
            category: Category key
            divine_rate: Current divine/chaos rate for conversions

        Returns:
            CategoryRanking if successful
        """
        api_type = PriceRankingCache.CATEGORY_TO_API_TYPE.get(category)
        display_name = PriceRankingCache.CATEGORIES.get(category, category)

        if not api_type:
            logger.warning(f"Unknown category: {category}")
            return None

        logger.info(f"Fetching top 20 for {display_name}...")

        try:
            if category == "currency":
                items = self._fetch_currency_top20(divine_rate)
            else:
                items = self._fetch_item_top20(api_type, divine_rate)

            ranking = CategoryRanking(
                category=category,
                display_name=display_name,
                items=items,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            self.cache._rankings[category] = ranking
            logger.info(f"Got {len(items)} items for {display_name}")
            return ranking

        except Exception as e:
            logger.error(f"Failed to fetch {category}: {e}")
            return None

    def _fetch_currency_top20(self, divine_rate: float) -> List[RankedItem]:
        """Fetch top 20 currency items."""
        data = self.api.get_currency_overview()
        lines = data.get("lines", [])

        # Sort by chaos equivalent value
        sorted_items = sorted(
            lines,
            key=lambda x: float(x.get("chaosEquivalent") or x.get("chaosValue") or 0),
            reverse=True
        )

        items = []
        for i, item in enumerate(sorted_items[:20], start=1):
            chaos_value = float(item.get("chaosEquivalent") or item.get("chaosValue") or 0)
            items.append(RankedItem(
                rank=i,
                name=item.get("currencyTypeName", "Unknown"),
                chaos_value=chaos_value,
                divine_value=chaos_value / divine_rate if divine_rate > 0 else None,
                icon=item.get("icon"),
            ))

        return items

    def _fetch_item_top20(self, api_type: str, divine_rate: float) -> List[RankedItem]:
        """Fetch top 20 items for a given API type."""
        data = self.api._get_item_overview(api_type)
        if not data:
            return []

        lines = data.get("lines", [])

        # Sort by chaos value
        sorted_items = sorted(
            lines,
            key=lambda x: float(x.get("chaosValue") or 0),
            reverse=True
        )

        items = []
        for i, item in enumerate(sorted_items[:20], start=1):
            chaos_value = float(item.get("chaosValue") or 0)
            items.append(RankedItem(
                rank=i,
                name=item.get("name", "Unknown"),
                chaos_value=chaos_value,
                divine_value=chaos_value / divine_rate if divine_rate > 0 else None,
                base_type=item.get("baseType"),
                icon=item.get("icon"),
                item_class=item.get("itemClass"),
            ))

        return items

    def refresh_slot(self, slot: str, force: bool = False) -> Optional[CategoryRanking]:
        """
        Refresh top 20 for a specific equipment slot.

        Args:
            slot: Slot key (e.g., "helmet", "body_armour", "sword")
            force: If True, refresh even if cache is valid

        Returns:
            CategoryRanking if successful
        """
        slot_key = f"slot_{slot}"

        if not force and self.cache.is_cache_valid(slot_key):
            return self.cache.get_ranking(slot_key)

        divine_rate = self.api.ensure_divine_rate()
        ranking = self._refresh_slot(slot, divine_rate)

        if ranking:
            self.cache._save_cache()

        return ranking

    def _refresh_slot(self, slot: str, divine_rate: float) -> Optional[CategoryRanking]:
        """
        Internal method to refresh a slot ranking.

        Args:
            slot: Slot key
            divine_rate: Current divine/chaos rate

        Returns:
            CategoryRanking if successful
        """
        slot_config = PriceRankingCache.EQUIPMENT_SLOTS.get(slot)
        if not slot_config:
            logger.warning(f"Unknown slot: {slot}")
            return None

        api_type, item_types = slot_config
        display_name = PriceRankingCache.SLOT_DISPLAY_NAMES.get(slot, slot.title())

        logger.info(f"Fetching top 20 for {display_name}...")

        try:
            items = self._fetch_slot_top20(api_type, item_types, divine_rate)

            slot_key = f"slot_{slot}"
            ranking = CategoryRanking(
                category=slot_key,
                display_name=display_name,
                items=items,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            self.cache._rankings[slot_key] = ranking
            logger.info(f"Got {len(items)} items for {display_name}")
            return ranking

        except Exception as e:
            logger.error(f"Failed to fetch slot {slot}: {e}")
            return None

    def _fetch_slot_top20(
        self,
        api_type: str,
        item_types: str | List[str],
        divine_rate: float,
    ) -> List[RankedItem]:
        """
        Fetch top 20 items filtered by equipment slot (itemType).

        Args:
            api_type: API category (e.g., "UniqueArmour", "UniqueWeapon")
            item_types: Single itemType string or list of itemType strings to filter
            divine_rate: Current divine/chaos rate

        Returns:
            List of top 20 RankedItems
        """
        data = self.api._get_item_overview(api_type)
        if not data:
            return []

        lines = data.get("lines", [])

        # Normalize item_types to a list
        if isinstance(item_types, str):
            type_filter = [item_types]
        else:
            type_filter = item_types

        # Filter by itemType
        filtered = [
            item for item in lines
            if item.get("itemType") in type_filter
        ]

        # Sort by chaos value
        sorted_items = sorted(
            filtered,
            key=lambda x: float(x.get("chaosValue") or 0),
            reverse=True
        )

        items = []
        for i, item in enumerate(sorted_items[:20], start=1):
            chaos_value = float(item.get("chaosValue") or 0)
            items.append(RankedItem(
                rank=i,
                name=item.get("name", "Unknown"),
                chaos_value=chaos_value,
                divine_value=chaos_value / divine_rate if divine_rate > 0 else None,
                base_type=item.get("baseType"),
                icon=item.get("icon"),
                item_class=item.get("itemClass"),
            ))

        return items

    def refresh_all_slots(self, force: bool = False) -> Dict[str, CategoryRanking]:
        """
        Refresh top 20 for all equipment slots.

        Args:
            force: If True, refresh even if cache is valid

        Returns:
            Dict of slot_key -> CategoryRanking
        """
        divine_rate = self.api.ensure_divine_rate()
        results = {}

        for slot in PriceRankingCache.EQUIPMENT_SLOTS:
            ranking = self._refresh_slot(slot, divine_rate)
            if ranking:
                results[ranking.category] = ranking

        self.cache._save_cache()
        return results


# Category groupings for filtering
UNIQUE_CATEGORIES = ["unique_weapons", "unique_armour", "unique_accessories", "unique_flasks", "unique_jewels"]
EQUIPMENT_CATEGORIES = UNIQUE_CATEGORIES  # Aliases for clarity
CONSUMABLE_CATEGORIES = ["currency", "fragments", "essences", "fossils", "scarabs", "oils", "incubators", "vials"]
CARD_CATEGORIES = ["divination_cards"]


def get_rankings_by_group(
    group: str,
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Dict[str, CategoryRanking]:
    """
    Get rankings for a group of categories.

    Args:
        group: One of "uniques", "equipment", "consumables", "cards", or "all"
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        Dict of category -> CategoryRanking for the specified group
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)

    group_lower = group.lower()

    if group_lower in ("uniques", "equipment"):
        categories = UNIQUE_CATEGORIES
    elif group_lower == "consumables":
        categories = CONSUMABLE_CATEGORIES
    elif group_lower == "cards":
        categories = CARD_CATEGORIES
    elif group_lower == "all":
        return calculator.refresh_all(force=force_refresh)
    else:
        logger.warning(f"Unknown group: {group}, returning all")
        return calculator.refresh_all(force=force_refresh)

    # Refresh only the specified categories
    for category in categories:
        calculator.refresh_category(category, force=force_refresh)

    # Return only the requested categories
    all_rankings = cache.get_all_rankings()
    return {k: v for k, v in all_rankings.items() if k in categories}


def get_top20_rankings(
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Dict[str, CategoryRanking]:
    """
    Convenience function to get top 20 rankings for all categories.

    Args:
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        Dict of category -> CategoryRanking
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_all(force=force_refresh)


def get_top20_for_category(
    category: str,
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Optional[CategoryRanking]:
    """
    Convenience function to get top 20 for a specific category.

    Args:
        category: Category key (e.g., "currency", "unique_weapons")
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        CategoryRanking if successful
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_category(category, force=force_refresh)


def get_top20_for_slot(
    slot: str,
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Optional[CategoryRanking]:
    """
    Convenience function to get top 20 for a specific equipment slot.

    Args:
        slot: Slot key (e.g., "helmet", "body_armour", "sword")
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        CategoryRanking if successful
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_slot(slot, force=force_refresh)


def get_all_slot_rankings(
    league: str = "Standard",
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> Dict[str, CategoryRanking]:
    """
    Convenience function to get top 20 for all equipment slots.

    Args:
        league: League name
        force_refresh: If True, refresh even if cache is valid
        cache_dir: Optional cache directory

    Returns:
        Dict of slot_key -> CategoryRanking
    """
    cache = PriceRankingCache(cache_dir=cache_dir, league=league)
    calculator = Top20Calculator(cache)
    return calculator.refresh_all_slots(force=force_refresh)


# =============================================================================
# Historical Database Storage
# =============================================================================

class PriceRankingHistory:
    """
    SQLite-based historical storage for price rankings.

    Stores daily snapshots for trend analysis and historical queries.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize historical storage.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.poe_price_checker/price_rankings.db
        """
        import sqlite3

        if db_path is None:
            db_path = Path.home() / ".poe_price_checker" / "price_rankings.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path

        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

        logger.info(f"PriceRankingHistory initialized: {db_path}")

    def _initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS ranking_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league TEXT NOT NULL,
                category TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(league, category, snapshot_date)
            );

            CREATE TABLE IF NOT EXISTS ranked_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL REFERENCES ranking_snapshots(id) ON DELETE CASCADE,
                rank INTEGER NOT NULL,
                name TEXT NOT NULL,
                chaos_value REAL NOT NULL,
                divine_value REAL,
                base_type TEXT,
                item_class TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_league_date
                ON ranking_snapshots(league, snapshot_date);

            CREATE INDEX IF NOT EXISTS idx_items_snapshot
                ON ranked_items(snapshot_id);

            CREATE INDEX IF NOT EXISTS idx_items_name
                ON ranked_items(name);
        """)
        self.conn.commit()

    def save_snapshot(self, ranking: CategoryRanking, league: str) -> int:
        """
        Save a ranking snapshot to the database.

        Args:
            ranking: CategoryRanking to save
            league: League name

        Returns:
            Snapshot ID
        """
        today = datetime.now(timezone.utc).date().isoformat()

        cursor = self.conn.cursor()

        # Insert or replace snapshot
        cursor.execute("""
            INSERT OR REPLACE INTO ranking_snapshots (league, category, snapshot_date)
            VALUES (?, ?, ?)
        """, (league, ranking.category, today))

        snapshot_id = cursor.lastrowid

        # Delete old items for this snapshot (in case of replace)
        cursor.execute("DELETE FROM ranked_items WHERE snapshot_id = ?", (snapshot_id,))

        # Insert new items
        for item in ranking.items:
            cursor.execute("""
                INSERT INTO ranked_items (snapshot_id, rank, name, chaos_value, divine_value, base_type, item_class)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (snapshot_id, item.rank, item.name, item.chaos_value, item.divine_value, item.base_type, item.item_class))

        self.conn.commit()
        logger.debug(f"Saved snapshot for {ranking.category} ({league}): {len(ranking.items)} items")
        return snapshot_id

    def save_all_snapshots(self, rankings: Dict[str, CategoryRanking], league: str) -> None:
        """Save all rankings as snapshots."""
        for ranking in rankings.values():
            self.save_snapshot(ranking, league)
        logger.info(f"Saved {len(rankings)} category snapshots for {league}")

    def get_item_history(
        self,
        item_name: str,
        league: str,
        days: int = 30,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get price history for a specific item.

        Args:
            item_name: Item name to look up
            league: League name
            days: Number of days of history
            category: Optional category filter

        Returns:
            List of {date, rank, chaos_value, divine_value}
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

        query = """
            SELECT s.snapshot_date, s.category, i.rank, i.chaos_value, i.divine_value
            FROM ranked_items i
            JOIN ranking_snapshots s ON i.snapshot_id = s.id
            WHERE i.name = ? AND s.league = ? AND s.snapshot_date >= ?
        """
        params: List[Any] = [item_name, league, cutoff]

        if category:
            query += " AND s.category = ?"
            params.append(category)

        query += " ORDER BY s.snapshot_date DESC"

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_trending_items(
        self,
        league: str,
        category: str,
        days: int = 7,
        min_change_percent: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """
        Find items with significant price changes.

        Args:
            league: League name
            category: Category to analyze
            days: Days to compare (compares today vs N days ago)
            min_change_percent: Minimum % change to include

        Returns:
            List of {name, old_price, new_price, change_percent, trend}
        """
        today = datetime.now(timezone.utc).date().isoformat()
        past = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

        # Get current prices
        cursor = self.conn.execute("""
            SELECT i.name, i.chaos_value as new_price
            FROM ranked_items i
            JOIN ranking_snapshots s ON i.snapshot_id = s.id
            WHERE s.league = ? AND s.category = ? AND s.snapshot_date = ?
        """, (league, category, today))
        current_prices = {row["name"]: row["new_price"] for row in cursor.fetchall()}

        # Get past prices
        cursor = self.conn.execute("""
            SELECT i.name, i.chaos_value as old_price
            FROM ranked_items i
            JOIN ranking_snapshots s ON i.snapshot_id = s.id
            WHERE s.league = ? AND s.category = ? AND s.snapshot_date = ?
        """, (league, category, past))
        past_prices = {row["name"]: row["old_price"] for row in cursor.fetchall()}

        # Calculate changes
        trending = []
        for name, new_price in current_prices.items():
            old_price = past_prices.get(name)
            if old_price and old_price > 0:
                change = ((new_price - old_price) / old_price) * 100
                if abs(change) >= min_change_percent:
                    trending.append({
                        "name": name,
                        "old_price": old_price,
                        "new_price": new_price,
                        "change_percent": round(change, 1),
                        "trend": "up" if change > 0 else "down",
                    })

        # Sort by absolute change
        trending.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
        return trending

    def get_snapshot_dates(self, league: str, category: Optional[str] = None) -> List[str]:
        """Get all snapshot dates for a league."""
        query = "SELECT DISTINCT snapshot_date FROM ranking_snapshots WHERE league = ?"
        params: List[Any] = [league]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY snapshot_date DESC"

        cursor = self.conn.execute(query, params)
        return [row[0] for row in cursor.fetchall()]

    def get_category_snapshot(
        self,
        league: str,
        category: str,
        date: Optional[str] = None,
    ) -> Optional[CategoryRanking]:
        """
        Get a historical snapshot for a category.

        Args:
            league: League name
            category: Category key
            date: Snapshot date (YYYY-MM-DD). Defaults to latest.

        Returns:
            CategoryRanking if found
        """
        if date is None:
            # Get latest snapshot
            cursor = self.conn.execute("""
                SELECT id, snapshot_date FROM ranking_snapshots
                WHERE league = ? AND category = ?
                ORDER BY snapshot_date DESC LIMIT 1
            """, (league, category))
        else:
            cursor = self.conn.execute("""
                SELECT id, snapshot_date FROM ranking_snapshots
                WHERE league = ? AND category = ? AND snapshot_date = ?
            """, (league, category, date))

        row = cursor.fetchone()
        if not row:
            return None

        snapshot_id = row["id"]

        # Get items
        cursor = self.conn.execute("""
            SELECT rank, name, chaos_value, divine_value, base_type, item_class
            FROM ranked_items WHERE snapshot_id = ?
            ORDER BY rank
        """, (snapshot_id,))

        items = [
            RankedItem(
                rank=r["rank"],
                name=r["name"],
                chaos_value=r["chaos_value"],
                divine_value=r["divine_value"],
                base_type=r["base_type"],
                item_class=r["item_class"],
            )
            for r in cursor.fetchall()
        ]

        display_name = PriceRankingCache.CATEGORIES.get(category, category)
        return CategoryRanking(
            category=category,
            display_name=display_name,
            items=items,
            updated_at=row["snapshot_date"],
        )

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()


# =============================================================================
# CLI Interface
# =============================================================================

def print_ranking(ranking: CategoryRanking, limit: int = 20, show_divine: bool = True) -> None:
    """Pretty-print a category ranking."""
    print(f"\n{'='*60}")
    print(f" {ranking.display_name}")
    print(f"{'='*60}")

    for item in ranking.items[:limit]:
        divine_str = ""
        if show_divine and item.divine_value:
            divine_str = f" ({item.divine_value:.2f} div)"

        base_str = ""
        if item.base_type:
            base_str = f" [{item.base_type}]"

        print(f"  {item.rank:2}. {item.name}{base_str}: {item.chaos_value:,.0f}c{divine_str}")


def print_trending(trending: List[Dict[str, Any]], category: str) -> None:
    """Pretty-print trending items."""
    print(f"\n{'='*60}")
    print(f" Trending: {category}")
    print(f"{'='*60}")

    if not trending:
        print("  No significant price changes found.")
        return

    for item in trending:
        arrow = "↑" if item["trend"] == "up" else "↓"
        # Could add ANSI colors here
        print(f"  {arrow} {item['name']}: {item['old_price']:,.0f}c → {item['new_price']:,.0f}c ({item['change_percent']:+.1f}%)")


def cli_main() -> None:
    """Command-line interface for price rankings."""
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE Price Rankings - View top 20 items by category",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m core.price_rankings                    # Show all categories
  python -m core.price_rankings -c currency        # Show currency only
  python -m core.price_rankings -g uniques         # Show all unique categories
  python -m core.price_rankings -s helmet          # Show top 20 unique helmets
  python -m core.price_rankings -s body_armour    # Show top 20 unique body armours
  python -m core.price_rankings --slots            # Show all equipment slots
  python -m core.price_rankings --refresh          # Force refresh from API
  python -m core.price_rankings --trending         # Show trending items
  python -m core.price_rankings --history "Divine Orb"  # Show item history
        """
    )

    parser.add_argument("-l", "--league", help="League name (auto-detects current temp league)")
    parser.add_argument("-c", "--category", help="Specific category to show",
                       choices=list(PriceRankingCache.CATEGORIES.keys()))
    parser.add_argument("-s", "--slot", help="Equipment slot to show (e.g., helmet, body_armour, sword)",
                       choices=list(PriceRankingCache.EQUIPMENT_SLOTS.keys()))
    parser.add_argument("--slots", action="store_true", help="Show all equipment slot rankings")
    parser.add_argument("-g", "--group", help="Category group",
                       choices=["uniques", "consumables", "cards", "all"])
    parser.add_argument("-n", "--limit", type=int, default=20, help="Number of items to show (default: 20)")
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--save", action="store_true", help="Save snapshot to database")
    parser.add_argument("--trending", action="store_true", help="Show trending items (price changes)")
    parser.add_argument("--history", metavar="ITEM", help="Show price history for an item")
    parser.add_argument("--days", type=int, default=7, help="Days for trending/history (default: 7)")
    parser.add_argument("--list-categories", action="store_true", help="List available categories")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress info messages")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    # List categories and exit
    if args.list_categories:
        print("\nAvailable categories:")
        for key, name in PriceRankingCache.CATEGORIES.items():
            print(f"  {key:20} - {name}")
        print("\nCategory groups:")
        print("  uniques     - All unique item categories")
        print("  consumables - Currency, fragments, scarabs, etc.")
        print("  cards       - Divination cards")
        print("  all         - All categories")
        print("\nEquipment slots (for unique items):")
        for key, name in PriceRankingCache.SLOT_DISPLAY_NAMES.items():
            print(f"  {key:20} - {name}")
        return

    # Detect league
    if args.league:
        league = args.league
    else:
        from data_sources.pricing.poe_ninja import PoeNinjaAPI
        api = PoeNinjaAPI()
        league = api.detect_current_league()
        print(f"Using league: {league}")

    # Initialize cache
    cache = PriceRankingCache(league=league)
    calculator = Top20Calculator(cache)

    # Handle item history
    if args.history:
        history_db = PriceRankingHistory()
        history = history_db.get_item_history(args.history, league, days=args.days, category=args.category)

        print(f"\n{'='*60}")
        print(f" Price History: {args.history}")
        print(f"{'='*60}")

        if not history:
            print("  No history found. Run with --save to store snapshots.")
        else:
            for entry in history:
                divine_str = f" ({entry['divine_value']:.2f} div)" if entry.get('divine_value') else ""
                print(f"  {entry['snapshot_date']}: #{entry['rank']} - {entry['chaos_value']:,.0f}c{divine_str}")

        history_db.close()
        return

    # Handle trending
    if args.trending:
        # Need to refresh first to ensure we have current data
        rankings = calculator.refresh_all(force=args.refresh)

        history_db = PriceRankingHistory()

        # Save current snapshot
        if args.save or True:  # Always save for trending
            history_db.save_all_snapshots(rankings, league)

        categories_to_check = [args.category] if args.category else list(PriceRankingCache.CATEGORIES.keys())

        for cat in categories_to_check:
            trending = history_db.get_trending_items(league, cat, days=args.days)
            if trending:
                print_trending(trending, PriceRankingCache.CATEGORIES.get(cat, cat))

        history_db.close()
        return

    # Fetch rankings
    if args.slot:
        # Single equipment slot
        ranking = calculator.refresh_slot(args.slot, force=args.refresh)
        if ranking:
            print_ranking(ranking, limit=args.limit)
            if args.save:
                history_db = PriceRankingHistory()
                history_db.save_snapshot(ranking, league)
                history_db.close()
                print("\nSnapshot saved to database.")
    elif args.slots:
        # All equipment slots
        rankings = calculator.refresh_all_slots(force=args.refresh)
        for ranking in rankings.values():
            print_ranking(ranking, limit=args.limit)
        if args.save:
            history_db = PriceRankingHistory()
            history_db.save_all_snapshots(rankings, league)
            history_db.close()
            print("\nSnapshots saved to database.")
    elif args.category:
        ranking = calculator.refresh_category(args.category, force=args.refresh)
        if ranking:
            print_ranking(ranking, limit=args.limit)
            if args.save:
                history_db = PriceRankingHistory()
                history_db.save_snapshot(ranking, league)
                history_db.close()
                print("\nSnapshot saved to database.")
    elif args.group:
        rankings = get_rankings_by_group(args.group, league=league, force_refresh=args.refresh)
        for ranking in rankings.values():
            print_ranking(ranking, limit=args.limit)
        if args.save:
            history_db = PriceRankingHistory()
            history_db.save_all_snapshots(rankings, league)
            history_db.close()
            print("\nSnapshots saved to database.")
    else:
        rankings = calculator.refresh_all(force=args.refresh)
        for ranking in rankings.values():
            print_ranking(ranking, limit=args.limit)
        if args.save:
            history_db = PriceRankingHistory()
            history_db.save_all_snapshots(rankings, league)
            history_db.close()
            print("\nSnapshots saved to database.")

    # Show cache status
    age = cache.get_cache_age_days()
    if age is not None:
        print(f"\nCache age: {age:.1f} days (refreshes after {CACHE_EXPIRY_DAYS} days)")


if __name__ == "__main__":
    cli_main()
