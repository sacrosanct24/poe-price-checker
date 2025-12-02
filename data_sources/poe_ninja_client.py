"""
poe.ninja API Client.

Provides pricing data for bulk items:
- Currency (chaos, divine, exalted, etc.)
- Unique items (weapons, armour, accessories, jewels, flasks)
- Maps, fragments, scarabs
- Skill gems, divination cards

Reference: https://poe.ninja/api/data

Cache is used heavily since poe.ninja updates hourly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

from data_sources.base_api import BaseAPIClient

logger = logging.getLogger(__name__)


@dataclass
class NinjaPrice:
    """Price data from poe.ninja."""
    name: str
    chaos_value: float
    divine_value: float = 0.0
    base_type: str = ""
    variant: str = ""
    links: int = 0
    item_class: str = ""
    icon: str = ""
    stack_size: int = 1
    details_id: str = ""

    @property
    def display_price(self) -> str:
        """Format price for display."""
        if self.chaos_value >= 100:
            return f"{self.chaos_value:.0f}c"
        elif self.chaos_value >= 1:
            return f"{self.chaos_value:.1f}c"
        else:
            return f"{self.chaos_value:.2f}c"


@dataclass
class NinjaPriceDatabase:
    """In-memory database of poe.ninja prices."""
    league: str
    currency: Dict[str, NinjaPrice] = field(default_factory=dict)
    fragments: Dict[str, NinjaPrice] = field(default_factory=dict)
    uniques: Dict[str, NinjaPrice] = field(default_factory=dict)
    unique_maps: Dict[str, NinjaPrice] = field(default_factory=dict)
    maps: Dict[str, NinjaPrice] = field(default_factory=dict)
    scarabs: Dict[str, NinjaPrice] = field(default_factory=dict)
    skill_gems: Dict[str, NinjaPrice] = field(default_factory=dict)
    div_cards: Dict[str, NinjaPrice] = field(default_factory=dict)
    essences: Dict[str, NinjaPrice] = field(default_factory=dict)
    oils: Dict[str, NinjaPrice] = field(default_factory=dict)
    fossils: Dict[str, NinjaPrice] = field(default_factory=dict)
    resonators: Dict[str, NinjaPrice] = field(default_factory=dict)
    incubators: Dict[str, NinjaPrice] = field(default_factory=dict)
    beasts: Dict[str, NinjaPrice] = field(default_factory=dict)

    def get_price(self, name: str, item_class: str = "") -> Optional[NinjaPrice]:
        """
        Look up price by name.

        Args:
            name: Item name
            item_class: Optional item class for disambiguation

        Returns:
            NinjaPrice if found
        """
        # Normalize name
        name_lower = name.lower()

        # Check by item class first if provided
        if item_class:
            class_map = {
                "currency": self.currency,
                "fragment": self.fragments,
                "map": self.maps,
                "unique": self.uniques,
                "divination card": self.div_cards,
                "skill gem": self.skill_gems,
                "scarab": self.scarabs,
                "essence": self.essences,
                "oil": self.oils,
                "fossil": self.fossils,
                "resonator": self.resonators,
            }
            if item_class.lower() in class_map:
                db = class_map[item_class.lower()]
                if name_lower in db:
                    return db[name_lower]

        # Search all databases
        for db in [
            self.currency, self.fragments, self.uniques,
            self.unique_maps, self.maps, self.scarabs,
            self.skill_gems, self.div_cards, self.essences,
            self.oils, self.fossils, self.resonators,
            self.incubators, self.beasts
        ]:
            if name_lower in db:
                return db[name_lower]

        return None

    def get_all_prices(self) -> Dict[str, NinjaPrice]:
        """Get all prices merged into one dict."""
        merged = {}
        for db in [
            self.currency, self.fragments, self.uniques,
            self.unique_maps, self.maps, self.scarabs,
            self.skill_gems, self.div_cards, self.essences,
            self.oils, self.fossils, self.resonators,
            self.incubators, self.beasts
        ]:
            merged.update(db)
        return merged


class PoeNinjaClient(BaseAPIClient):
    """
    Client for poe.ninja API.

    Provides bulk item pricing data.
    """

    # API endpoints
    CURRENCY_URL = "currencyoverview"
    ITEM_URL = "itemoverview"

    # Item types for currency endpoint
    CURRENCY_TYPES = ["Currency", "Fragment"]

    # Item types for item endpoint
    ITEM_TYPES = [
        "UniqueWeapon", "UniqueArmour", "UniqueAccessory",
        "UniqueFlask", "UniqueJewel", "UniqueMap",
        "Map", "Scarab", "SkillGem", "DivinationCard",
        "Essence", "Oil", "Fossil", "Resonator",
        "Incubator", "Beast"
    ]

    def __init__(
        self,
        rate_limit: float = 2.0,  # 2 req/sec is safe for poe.ninja
        cache_ttl: int = 1800,    # 30 min cache (updates hourly)
    ):
        super().__init__(
            base_url="https://poe.ninja/api/data",
            rate_limit=rate_limit,
            cache_ttl=cache_ttl,
            user_agent="PoEPriceChecker/1.0 (stash-valuation)",
        )

    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for requests."""
        param_str = ""
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"poeninja:{endpoint}:{param_str}"

    def get_currency_prices(
        self,
        league: str,
        currency_type: str = "Currency"
    ) -> List[NinjaPrice]:
        """
        Get currency prices.

        Args:
            league: League name (e.g., "Phrecia")
            currency_type: "Currency" or "Fragment"

        Returns:
            List of NinjaPrice objects
        """
        params = {
            "league": league,
            "type": currency_type,
        }

        try:
            data = self.get(self.CURRENCY_URL, params=params)
            lines = data.get("lines", [])

            prices = []
            for line in lines:
                name = line.get("currencyTypeName", "")
                price = NinjaPrice(
                    name=name,
                    chaos_value=line.get("chaosEquivalent", 0),
                    icon=line.get("icon", ""),
                    item_class=currency_type.lower(),
                    details_id=line.get("detailsId", ""),
                )
                prices.append(price)

            logger.info(f"Fetched {len(prices)} {currency_type} prices for {league}")
            return prices

        except Exception as e:
            logger.error(f"Failed to fetch {currency_type} prices: {e}")
            return []

    def get_item_prices(
        self,
        league: str,
        item_type: str
    ) -> List[NinjaPrice]:
        """
        Get item prices.

        Args:
            league: League name
            item_type: Item type (e.g., "UniqueWeapon", "DivinationCard")

        Returns:
            List of NinjaPrice objects
        """
        params = {
            "league": league,
            "type": item_type,
        }

        try:
            data = self.get(self.ITEM_URL, params=params)
            lines = data.get("lines", [])

            prices = []
            for line in lines:
                name = line.get("name", "")
                base_type = line.get("baseType", "")

                # Handle variants (e.g., corrupted, different rolls)
                variant = line.get("variant", "")
                links = line.get("links", 0)

                price = NinjaPrice(
                    name=name,
                    chaos_value=line.get("chaosValue", 0),
                    divine_value=line.get("divineValue", 0),
                    base_type=base_type,
                    variant=variant,
                    links=links,
                    icon=line.get("icon", ""),
                    item_class=item_type,
                    details_id=line.get("detailsId", ""),
                )
                prices.append(price)

            logger.info(f"Fetched {len(prices)} {item_type} prices for {league}")
            return prices

        except Exception as e:
            logger.error(f"Failed to fetch {item_type} prices: {e}")
            return []

    def build_price_database(
        self,
        league: str,
        item_types: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> NinjaPriceDatabase:
        """
        Build complete price database for a league.

        Args:
            league: League name
            item_types: Specific types to fetch (None = all)
            progress_callback: Optional callback(current, total, type_name)

        Returns:
            NinjaPriceDatabase with all prices
        """
        db = NinjaPriceDatabase(league=league)

        # Determine what to fetch
        currency_types = self.CURRENCY_TYPES
        types_to_fetch = item_types or self.ITEM_TYPES

        total_types = len(currency_types) + len(types_to_fetch)
        current = 0

        # Fetch currency
        for ctype in currency_types:
            current += 1
            if progress_callback:
                progress_callback(current, total_types, ctype)

            prices = self.get_currency_prices(league, ctype)

            # Store by lowercase name
            target = db.currency if ctype == "Currency" else db.fragments
            for p in prices:
                target[p.name.lower()] = p

        # Fetch items
        type_to_db = {
            "UniqueWeapon": db.uniques,
            "UniqueArmour": db.uniques,
            "UniqueAccessory": db.uniques,
            "UniqueFlask": db.uniques,
            "UniqueJewel": db.uniques,
            "UniqueMap": db.unique_maps,
            "Map": db.maps,
            "Scarab": db.scarabs,
            "SkillGem": db.skill_gems,
            "DivinationCard": db.div_cards,
            "Essence": db.essences,
            "Oil": db.oils,
            "Fossil": db.fossils,
            "Resonator": db.resonators,
            "Incubator": db.incubators,
            "Beast": db.beasts,
        }

        for itype in types_to_fetch:
            current += 1
            if progress_callback:
                progress_callback(current, total_types, itype)

            prices = self.get_item_prices(league, itype)

            target = type_to_db.get(itype, db.uniques)
            for p in prices:
                # For uniques, use name + base for key to handle variants
                if itype.startswith("Unique") and p.base_type:
                    key = f"{p.name.lower()} {p.base_type.lower()}"
                else:
                    key = p.name.lower()

                # Handle link variants - prefer 6-link prices
                if key in target and target[key].links > p.links:
                    continue

                target[key] = p

        logger.info(f"Built price database with {sum(len(getattr(db, attr)) for attr in dir(db) if isinstance(getattr(db, attr), dict))} items")
        return db

    def get_divine_chaos_rate(self, league: str) -> float:
        """
        Get divine orb to chaos ratio.

        Args:
            league: League name

        Returns:
            Chaos value of 1 Divine Orb
        """
        prices = self.get_currency_prices(league, "Currency")
        for p in prices:
            if p.name.lower() == "divine orb":
                return p.chaos_value
        return 1.0  # Fallback


# Thread-safe singleton pattern for convenience functions
import threading

_client: Optional[PoeNinjaClient] = None
_price_db: Optional[NinjaPriceDatabase] = None
_client_lock = threading.Lock()
_price_db_lock = threading.Lock()


def get_ninja_client() -> PoeNinjaClient:
    """Get or create singleton client. Thread-safe."""
    global _client
    if _client is None:
        with _client_lock:
            # Double-check locking pattern
            if _client is None:
                _client = PoeNinjaClient()
    return _client


def get_ninja_price(name: str, league: str = "Phrecia") -> Optional[NinjaPrice]:
    """
    Quick lookup for an item price. Thread-safe.

    Args:
        name: Item name
        league: League name

    Returns:
        NinjaPrice if found
    """
    global _price_db
    client = get_ninja_client()

    # Fast path: if DB is ready for this league, read under lock briefly
    with _price_db_lock:
        db = _price_db
        if db is not None and db.league == league:
            return db.get_price(name)

    # Slow path: build outside the lock to avoid long critical section/deadlocks
    new_db = client.build_price_database(league)

    # Publish the new DB with a short lock; double-check in case another thread already did
    with _price_db_lock:
        if _price_db is None or _price_db.league != league:
            _price_db = new_db
        # Use the most recent DB (ours or the one set by another thread)
        return _price_db.get_price(name)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    league = sys.argv[1] if len(sys.argv) > 1 else "Phrecia"

    print(f"\n=== poe.ninja Price Check ({league}) ===\n")

    client = PoeNinjaClient()

    # Quick divine rate check
    divine_rate = client.get_divine_chaos_rate(league)
    print(f"Divine Orb: {divine_rate:.0f}c\n")

    # Build full database
    def progress(cur, total, name):
        print(f"  [{cur}/{total}] Fetching {name}...")

    print("Building price database...")
    db = client.build_price_database(league, progress_callback=progress)

    print(f"\n=== Sample Prices ===")

    # Check some common items
    test_items = [
        "Chaos Orb", "Divine Orb", "Exalted Orb",
        "Mageblood", "Headhunter", "The Doctor",
        "Awakened Multistrike Support",
    ]

    for item in test_items:
        price = db.get_price(item)
        if price:
            print(f"  {item}: {price.display_price}")
        else:
            print(f"  {item}: Not found")
