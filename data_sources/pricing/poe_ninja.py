"""
PoE.ninja API client for Path of Exile 1 pricing data.
Inherits from BaseAPIClient for rate limiting and caching.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Optional, Dict, List, Any
from data_sources.base_api import BaseAPIClient
import logging

logger = logging.getLogger(__name__)


class PoeNinjaAPI(BaseAPIClient):
    """
    Client for poe.ninja economy API (PoE1 only).

    Provides access to:
    - Currency prices
    - Unique item prices
    - Fragments, div cards, essences, etc.
    """

    # API endpoint types
    CURRENCY_TYPES = ["Currency"]
    ITEM_TYPES = [
        "UniqueWeapon",
        "UniqueArmour",
        "UniqueAccessory",
        "UniqueFlask",
        "UniqueJewel",
        "Fragment",
        "DivinationCard",
        "Essence",
        "Fossil",
        "Scarab",
        "Oil",
        "Incubator",
        "Vial"
    ]

    def __init__(self, league: str = "Standard"):
        """
        Initialize poe.ninja API client.

        Args:
            league: League name (e.g., "Standard", "Settlers", "Keepers of the Flame")
        """
        super().__init__(
            base_url="https://poe.ninja/api/data",
            rate_limit=0.33,  # ~1 request per 3 seconds (community standard)
            cache_ttl=3600,  # Cache for 1 hour (prices don't change that fast)
            user_agent="PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)"
        )

        self.league = league
        self.divine_chaos_rate = 1.0  # Will be updated on first price load

        logger.info(f"Initialized PoeNinjaAPI for league: {league}")

    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from endpoint and params"""
        league = params.get('league', '') if params else ''
        type_param = params.get('type', '') if params else ''
        return f"{endpoint}:{league}:{type_param}"

    def get_current_leagues(self) -> List[Dict[str, str]]:
        """
        Fetch list of current leagues from poe.ninja.

        Returns:
            List of league dicts with 'name' and 'displayName'
        """
        try:
            data = self.get("economyleagues")
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to fetch leagues: {e}")
            # Fallback leagues
            return [
                {"name": "Standard", "displayName": "Standard"},
                {"name": "Hardcore", "displayName": "Hardcore"}
            ]

    def detect_current_league(self) -> str:
        """
        Auto-detect the current temp league (non-Standard/Hardcore).

        Returns:
            League name, defaults to "Standard" if no temp league found
        """
        leagues = self.get_current_leagues()

        # Filter out permanent leagues
        temp_leagues = [l for l in leagues if l['name'] not in ['Standard', 'Hardcore']]

        if temp_leagues:
            detected = temp_leagues[0]['name']
            logger.info(f"Detected current league: {detected}")
            return detected

        logger.info("No temp league detected, using Standard")
        return "Standard"

    def get_currency_overview(self) -> Dict[str, Any]:
        """
        Get currency price overview for current league.

        Returns:
            Dict with 'lines' (currency data) and 'currencyDetails'
        """
        data = self.get(
            "currencyoverview",
            params={"league": self.league, "type": "Currency"}
        )

        # Update divine/chaos conversion rate
        for item in data.get("lines", []):
            if item.get("currencyTypeName", "").lower() == "divine orb":
                self.divine_chaos_rate = item.get("chaosEquivalent", 1.0)
                logger.info(f"Divine Orb = {self.divine_chaos_rate:.1f} chaos")
                break

        return data

    def get_item_overview(self, item_type: str) -> Dict[str, Any]:
        """
        Get item price overview for a specific type.

        Args:
            item_type: One of ITEM_TYPES (e.g., "UniqueWeapon", "Fragment")

        Returns:
            Dict with 'lines' (item data)
        """
        if item_type not in self.ITEM_TYPES:
            raise ValueError(f"Invalid item type: {item_type}. Must be one of {self.ITEM_TYPES}")

        return self.get(
            "itemoverview",
            params={"league": self.league, "type": item_type}
        )

    def load_all_prices(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all price data for current league.
        Returns organized cache of all items.

        Returns:
            Dict with keys: 'currency', 'uniques', 'fragments', etc.
            Each value is a dict of {item_name_lower: item_data}
        """
        cache = {
            'currency': {},
            'uniques': {},
            'fragments': {},
            'divination': {},
            'essences': {},
            'fossils': {},
            'scarabs': {},
            'oils': {},
            'incubators': {},
            'vials': {}
        }

        # Load currency
        logger.info("Loading currency data...")
        currency_data = self.get_currency_overview()
        for item in currency_data.get("lines", []):
            key = item.get("currencyTypeName", "").lower()
            cache['currency'][key] = item

        # Load items by category
        category_mapping = {
            'uniques': ["UniqueWeapon", "UniqueArmour", "UniqueAccessory", "UniqueFlask", "UniqueJewel"],
            'fragments': ["Fragment"],
            'divination': ["DivinationCard"],
            'essences': ["Essence"],
            'fossils': ["Fossil"],
            'scarabs': ["Scarab"],
            'oils': ["Oil"],
            'incubators': ["Incubator"],
            'vials': ["Vial"]
        }

        for cache_key, types in category_mapping.items():
            for item_type in types:
                logger.info(f"Loading {item_type}...")
                try:
                    data = self.get_item_overview(item_type)

                    for item in data.get("lines", []):
                        # For uniques, include base type in key
                        if cache_key == 'uniques' and item.get("baseType"):
                            key = f"{item['name'].lower()} {item['baseType'].lower()}"
                        else:
                            key = item.get("name", "").lower()

                        cache[cache_key][key] = item

                except Exception as e:
                    logger.error(f"Failed to load {item_type}: {e}")

        logger.info(f"Loaded all prices for {self.league}")
        return cache

    def find_item_price(
            self,
            item_name: str,
            base_type: Optional[str] = None,
            rarity: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find price for an item by name.

        Args:
            item_name: Item name
            base_type: Base type (for uniques)
            rarity: Item rarity (UNIQUE, CURRENCY, etc.)

        Returns:
            Item data dict with chaosValue, divineValue, etc., or None if not found
        """
        search_key = item_name.lower()

        # Try currency first if no name (base_type only)
        if not item_name and base_type:
            search_key = base_type.lower()

            for cache_type in ['currency', 'fragments', 'essences', 'fossils', 'scarabs', 'oils', 'incubators',
                               'vials']:
                # Need to load this type first
                try:
                    if cache_type == 'currency':
                        data = self.get_currency_overview()
                    else:
                        type_map = {
                            'fragments': 'Fragment',
                            'divination': 'DivinationCard',
                            'essences': 'Essence',
                            'fossils': 'Fossil',
                            'scarabs': 'Scarab',
                            'oils': 'Oil',
                            'incubators': 'Incubator',
                            'vials': 'Vial'
                        }
                        data = self.get_item_overview(type_map[cache_type])

                    for item in data.get("lines", []):
                        item_key = item.get("currencyTypeName", item.get("name", "")).lower()
                        if search_key in item_key or item_key in search_key:
                            return item

                except Exception as e:
                    logger.debug(f"Search in {cache_type} failed: {e}")

        # Try uniques if rarity is UNIQUE
        if rarity == 'UNIQUE':
            search_key = item_name.lower()
            if base_type:
                search_key = f"{item_name.lower()} {base_type.lower()}"

            for item_type in ["UniqueWeapon", "UniqueArmour", "UniqueAccessory", "UniqueFlask", "UniqueJewel"]:
                try:
                    data = self.get_item_overview(item_type)

                    for item in data.get("lines", []):
                        item_key = item['name'].lower()
                        if item.get("baseType"):
                            item_key = f"{item['name'].lower()} {item['baseType'].lower()}"

                        if search_key == item_key or item_name.lower() in item_key:
                            return item

                except Exception as e:
                    logger.debug(f"Search in {item_type} failed: {e}")

        return None


# Testing
if __name__ == "__main__":
    # Test the API
    api = PoeNinjaAPI(league="Standard")

    try:
        # Test league detection
        current_league = api.detect_current_league()
        print(f"Current league: {current_league}")

        # Test divine orb price
        divine_data = api.find_item_price("Divine Orb", rarity="CURRENCY")
        if divine_data:
            print(f"Divine Orb: {divine_data.get('chaosEquivalent', 'N/A')} chaos")

        # Test unique item
        shavs = api.find_item_price("Shavronne's Wrappings", base_type="Occultist's Vestment", rarity="UNIQUE")
        if shavs:
            print(f"Shavronne's Wrappings: {shavs.get('chaosValue', 'N/A')} chaos")

        print(f"\nCache size: {api.get_cache_size()} entries")

    finally:
        api.close()