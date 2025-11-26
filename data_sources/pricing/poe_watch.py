"""
poe.watch API client for Path of Exile pricing data.
Provides historical data, enchantments, and corruptions.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Optional, Dict, List, Any
from data_sources.base_api import BaseAPIClient
import logging

logger = logging.getLogger(__name__)


class PoeWatchAPI(BaseAPIClient):
    """
    Client for poe.watch pricing API.

    Provides access to:
    - Item prices with historical data
    - Enchantment pricing (lab enchants)
    - Corruption pricing (vaal implicits)
    - Low confidence flagging
    - Search functionality
    """

    def __init__(self, league: str = "Standard"):
        """
        Initialize poe.watch API client.

        Args:
            league: League name (e.g., "Standard", "Keepers")
        """
        super().__init__(
            base_url="https://api.poe.watch",
            rate_limit=0.5,  # ~1 request per 2 seconds (conservative)
            cache_ttl=3600,  # Cache for 1 hour
            user_agent="PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)",
        )

        self.league = league
        self._item_cache: Dict[str, Any] = {}  # Name -> item data cache
        self._category_cache: Optional[List[Dict]] = None
        self.request_count = 0  # Track number of API requests

        logger.info(f"Initialized PoeWatchAPI for league: {league}")

    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from endpoint and params."""
        league = params.get('league', '') if params else ''
        category = params.get('category', '') if params else ''
        item_id = params.get('id', '') if params else ''
        query = params.get('q', '') if params else ''
        return f"{endpoint}:{league}:{category}:{item_id}:{query}"

    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Any:
        """Override get to track request count."""
        self.request_count += 1
        logger.info(f"[poe.watch] API Request #{self.request_count}: {endpoint} (params: {params})")
        return super().get(endpoint, params=params, **kwargs)

    def get_leagues(self) -> List[Dict[str, str]]:
        """
        Get available leagues.

        Returns:
            List of league dicts with 'name', 'start_date', 'end_date'
        """
        return self.get("leagues")

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get available item categories.

        Returns:
            List of category dicts with 'id', 'name', 'display', 'groups'
        """
        if self._category_cache is None:
            self._category_cache = self.get("categories")
        return self._category_cache

    def get_items_by_category(
        self,
        category: str,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Get items by category with optional filters.

        Args:
            category: Category name (currency, armour, weapon, gem, etc.)
            **filters: Optional filters:
                - lowConfidence (bool)
                - linkCount (int, 0-6)
                - gemLevel (int)
                - gemCorrupted (bool)
                - gemQuality (int)
                - itemLevel (int)

        Returns:
            List of item data dicts
        """
        params = {
            'league': self.league,
            'category': category,
            **filters
        }

        return self.get("get", params=params)

    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for items by name.

        Args:
            query: Item name or partial name

        Returns:
            List of matching items
        """
        params = {'league': self.league, 'q': query}
        return self.get("search", params=params)

    def get_item_history(self, item_id: int) -> List[Dict[str, Any]]:
        """
        Get price history for a specific item.

        Args:
            item_id: Item ID from get_items_by_category or search_items

        Returns:
            List of historical price points with 'mean', 'date', 'id'
        """
        params = {'league': self.league, 'id': item_id}
        return self.get("history", params=params)

    def get_enchants(self, item_id: int) -> List[Dict[str, Any]]:
        """
        Get lab enchantment prices for an item (typically helmets/boots).

        Args:
            item_id: Item ID

        Returns:
            List of enchant dicts with 'name', 'value', 'lowConfidence'
        """
        params = {'league': self.league, 'id': item_id}
        try:
            return self.get("enchants", params=params)
        except Exception as e:
            logger.warning(f"Failed to get enchants for item {item_id}: {e}")
            return []

    def get_corruptions(self, item_id: int) -> List[Dict[str, Any]]:
        """
        Get corruption implicit prices for an item.

        Args:
            item_id: Item ID

        Returns:
            List of corruption dicts with 'name', 'mean'
        """
        params = {'league': self.league, 'id': item_id}
        try:
            return self.get("corruptions", params=params)
        except Exception as e:
            logger.warning(f"Failed to get corruptions for item {item_id}: {e}")
            return []

    def get_compact_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all item data for current league in one request.

        Returns:
            Dict with 'items' key containing list of all items
        """
        params = {'league': self.league}
        return self.get("compact", params=params)

    def get_status(self) -> Dict[str, Any]:
        """
        Get API status and data freshness.

        Returns:
            Dict with 'changeID', 'requestedStashes', 'computedStashes'
        """
        return self.get("status")

    def load_all_prices(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all price data for current league using compact endpoint.

        Returns:
            Dict organized by category with item data:
            {
                'currency': {item_name_lower: item_data},
                'unique': {item_name_lower: item_data},
                ...
            }
        """
        cache: Dict[str, Dict[str, Any]] = {}

        try:
            logger.info(f"Loading compact data for {self.league}...")
            compact = self.get_compact_data()
            items = compact.get('items', [])

            logger.info(f"Loaded {len(items)} items from poe.watch")

            # Organize by category
            for item in items:
                category = item.get('category', 'unknown')

                if category not in cache:
                    cache[category] = {}

                # Use name as key (lowercase for matching)
                name_key = item.get('name', '').lower()
                if name_key:
                    cache[category][name_key] = item

            # Log summary
            for category, items_dict in cache.items():
                logger.debug(f"  {category}: {len(items_dict)} items")

        except Exception as e:
            logger.error(f"Failed to load compact data: {e}")

        return cache

    def find_item_price(
        self,
        item_name: str,
        base_type: Optional[str] = None,
        rarity: Optional[str] = None,
        gem_level: Optional[int] = None,
        gem_quality: Optional[int] = None,
        corrupted: Optional[bool] = None,
        links: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find price for an item with optional filtering.

        Args:
            item_name: Name of the item
            base_type: Base type (for uniques)
            rarity: Item rarity (UNIQUE, RARE, GEM, etc.)
            gem_level: Gem level filter
            gem_quality: Gem quality filter
            corrupted: Corruption status
            links: Number of links

        Returns:
            Item data dict or None if not found
        """
        logger.info(f"[poe.watch] find_item_price called for '{item_name}' (rarity={rarity}, links={links})")

        # Try exact search first
        try:
            results = self.search_items(item_name)
            if not results:
                return None

            # Filter results
            candidates = results

            # Filter by gem properties if applicable
            if rarity and rarity.upper() == "GEM":
                if gem_level is not None:
                    candidates = [
                        item for item in candidates
                        if item.get('gemLevel') == gem_level
                    ]

                if gem_quality is not None:
                    candidates = [
                        item for item in candidates
                        if item.get('gemQuality') == gem_quality
                    ]

                if corrupted is not None:
                    candidates = [
                        item for item in candidates
                        if item.get('gemIsCorrupted') == corrupted
                    ]

            # Filter by links
            if links is not None:
                candidates = [
                    item for item in candidates
                    if item.get('linkCount') == links
                ]

            # Return best match (highest mean price if multiple)
            if candidates:
                best = max(
                    candidates,
                    key=lambda x: float(x.get('mean', 0) or 0)
                )
                logger.info(f"[poe.watch] Found match for '{item_name}': {best.get('mean')}c (daily: {best.get('daily')})")
                return best

            # Fallback to first result if no filters matched
            if results:
                logger.info(f"[poe.watch] Using first result for '{item_name}': {results[0].get('mean')}c")
                return results[0]

            logger.info(f"[poe.watch] No results found for '{item_name}'")
            return None

        except Exception as e:
            logger.warning(f"[poe.watch] Failed to find price for {item_name}: {e}")
            return None

    def get_item_with_confidence(
        self,
        item_name: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Find item price and include confidence assessment.

        Returns:
            Item data with additional 'confidence' field:
            - 'high': lowConfidence=False and daily > 10
            - 'medium': lowConfidence=False but daily <= 10
            - 'low': lowConfidence=True
        """
        item = self.find_item_price(item_name, **kwargs)

        if not item:
            return None

        # Add confidence assessment
        low_conf = item.get('lowConfidence', False)
        daily = item.get('daily', 0)

        if low_conf:
            confidence = 'low'
        elif daily > 10:
            confidence = 'high'
        else:
            confidence = 'medium'

        item['confidence'] = confidence

        return item


# Testing
if __name__ == "__main__":
    # Test the API
    api = PoeWatchAPI(league="Standard")

    try:
        print("Testing poe.watch API...")
        print("=" * 60)

        # Test leagues
        print("\n1. Testing leagues endpoint...")
        leagues = api.get_leagues()
        print(f"   Found {len(leagues)} leagues")
        current = [league for league in leagues if league['end_date'].startswith('0001')]
        print(f"   Current leagues: {[league['name'] for league in current[:3]]}")

        # Test categories
        print("\n2. Testing categories endpoint...")
        categories = api.get_categories()
        print(f"   Found {len(categories)} categories")
        print(f"   Categories: {', '.join([c['name'] for c in categories[:5]])}")

        # Test currency prices
        print("\n3. Testing currency prices...")
        currency = api.get_items_by_category("currency")
        print(f"   Found {len(currency)} currency items")

        divine = next((c for c in currency if c['name'] == 'Divine Orb'), None)
        if divine:
            print(f"   Divine Orb: {divine['mean']:.1f} chaos")
            print(f"   Daily listings: {divine['daily']}")
            print(f"   Low confidence: {divine['lowConfidence']}")

        # Test search
        print("\n4. Testing item search...")
        results = api.search_items("Headhunter")
        if results:
            item = results[0]
            print(f"   Found: {item['name']}")
            print(f"   Price: {item['mean']:.1f} chaos")
            print(f"   Item ID: {item['id']}")

        # Test with confidence
        print("\n5. Testing confidence assessment...")
        item_with_conf = api.get_item_with_confidence("Divine Orb")
        if item_with_conf:
            print(f"   Item: {item_with_conf['name']}")
            print(f"   Price: {item_with_conf['mean']:.1f} chaos")
            print(f"   Confidence: {item_with_conf['confidence']}")

        # Test status
        print("\n6. Testing API status...")
        status = api.get_status()
        print(f"   Change ID: {status['changeID']}")
        print(f"   Success rate: {status['computedStashes']}/{status['requestedStashes']}")

        print("\n7. Cache statistics...")
        print(f"   Cache size: {api.get_cache_size()} entries")

        print("\n" + "=" * 60)
        print("[OK] All tests passed!")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        api.close()
