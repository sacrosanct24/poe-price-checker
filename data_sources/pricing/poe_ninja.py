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
        Fetch list of current trade leagues from the official PoE trade API.

        Returns:
            List of league dicts with 'name' and 'displayName', e.g.:
            [
                {"name": "Standard", "displayName": "Standard"},
                {"name": "Hardcore", "displayName": "Hardcore"},
                {"name": "Keepers", "displayName": "Keepers of the Trove"},
                {"name": "Hardcore Keepers", "displayName": "Hardcore Keepers of the Trove"},
                ...
            ]

        We:
          - Restrict to PC realm.
          - Deduplicate by league id.
        """
        import requests

        url = "https://www.pathofexile.com/api/trade/data/leagues"
        headers = {
            "User-Agent": "PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            result = data.get("result", [])
            # Deduplicate by league id, and restrict to PC realm
            id_to_text: dict[str, str] = {}

            for entry in result:
                # Typical shape: {"id": "Standard", "text": "Standard", "realm": "pc", ...}
                if entry.get("realm") != "pc":
                    continue

                league_id = entry.get("id")
                text = entry.get("text") or league_id
                if not league_id:
                    continue

                # First one wins; ignore duplicates from same realm
                if league_id not in id_to_text:
                    id_to_text[league_id] = text

            leagues: List[Dict[str, str]] = [
                {"name": league_id, "displayName": text}
                for league_id, text in id_to_text.items()
            ]

            if leagues:
                logger.info(
                    "Fetched %d leagues from trade API (pc realm): %s",
                    len(leagues),
                    ", ".join(l["name"] for l in leagues),
                )
                return leagues

        except Exception as e:
            logger.warning(f"Failed to fetch leagues from trade API: {e}")

        # Fallback: at least keep the permanent leagues usable
        logger.info("Falling back to static league list (Standard/Hardcore)")
        return [
            {"name": "Standard", "displayName": "Standard"},
            {"name": "Hardcore", "displayName": "Hardcore"},
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

    def _get_item_overview(self, item_type: str) -> dict | None:
        """
        Shared helper for poe.ninja itemoverview endpoints (PoE1 only).
        """
        try:
            data = self.get(
                "itemoverview",
                params={
                    "league": self.league,
                    "type": item_type,
                    "language": "en",
                },
            )
            return data if isinstance(data, dict) else None
        except Exception as e:
            logger.warning(f"Failed to fetch itemoverview for {item_type}: {e}")
            return None

    def get_skill_gem_overview(self) -> dict | None:
        """
        Return poe.ninja SkillGem overview for the current league.

        Contains lines with: name, gemLevel, gemQuality, corrupted, chaosValue, etc.
        """
        return self._get_item_overview("SkillGem")

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
                    data = self._get_item_overview(item_type)

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
    def _find_from_overview_by_name(self, overview_type: str, item_name: str) -> dict | None:
        """
        Look up a poe.ninja itemoverview entry by name.

        overview_type examples:
            - "DivinationCard"
            - "Fragment"
            - "Essence"
            - "Fossil"
            - "Scarab"
            - "Oil"
            - "Incubator"
            - "Vial"
        """
        overview = self._get_item_overview(overview_type)
        if not overview:
            return None

        lines = overview.get("lines", [])
        if not lines:
            return None

        def norm(s: str | None) -> str:
            return (s or "").strip().lower()

        key = norm(item_name)
        if not key:
            return None

        # Exact name match first
        for line in lines:
            if norm(line.get("name")) == key:
                return line

        # Fallback: loose substring match
        for line in lines:
            n = norm(line.get("name"))
            if key in n or n in key:
                return line

        return None

    def find_item_price(
            self,
            item_name: str,
            base_type: str | None,
            rarity: str | None = None,
            gem_level: int | None = None,
            gem_quality: int | None = None,
            corrupted: bool | None = None,
    ) -> dict | None:
        """
        Main item price resolver.

        - Currency is handled separately in GUI via get_currency_overview()
        - Here we handle:
            * Skill gems (SkillGem overview)
            * Unique items (armour, weapon, accessory, flask, jewel)
            * Divination cards, fragments, etc. via itemoverview
        """
        rarity_upper = (rarity or "").upper()
        name = (item_name or "").strip()

        # ---------- Skill gems ----------
        if rarity_upper == "GEM":
            return self._find_gem_price(
                name=name,
                gem_level=gem_level,
                gem_quality=gem_quality,
                corrupted=corrupted,
            )

        # ---------- Divination cards ----------
        # Your parser shows "DIVINATION" as rarity in the tree
        if rarity_upper in ("DIVINATION", "DIVINATION CARD"):
            return self._find_from_overview_by_name("DivinationCard", name)

        # (Optional future: add fragment / essence etc here)
        # if rarity_upper == "FRAGMENT":
        #     return self._find_from_overview_by_name("Fragment", name)

        # ---------- Uniques ----------
        if rarity_upper == "UNIQUE":
            search_key = item_name.lower()
            if base_type:
                search_key = f"{item_name.lower()} {base_type.lower()}"

            for item_type in ["UniqueWeapon", "UniqueArmour", "UniqueAccessory", "UniqueFlask", "UniqueJewel"]:
                try:
                    data = self._get_item_overview(item_type)

                    for item in data.get("lines", []):
                        item_key = item['name'].lower()
                        if item.get("baseType"):
                            item_key = f"{item['name'].lower()} {item['baseType'].lower()}"

                        if search_key == item_key or item_name.lower() in item_key:
                            return item

                except Exception as e:
                    logger.debug(f"Search in {item_type} failed: {e}")

        return None

    def _find_gem_price(
        self,
        name: str,
        gem_level: int | None,
        gem_quality: int | None,
        corrupted: bool | None,
    ) -> dict | None:
        """Find price for a skill gem (including Awakened, alt-quality)."""
        overview = self.get_skill_gem_overview()
        if not overview:
            return None

        lines = overview.get("lines", [])
        if not lines:
            return None

        def norm(s: str | None) -> str:
            return (s or "").strip().lower()

        name_key = norm(name)
        if not name_key:
            return None

        # Step 1: exact name match
        candidates = [ln for ln in lines if norm(ln.get("name")) == name_key]
        if not candidates:
            return None

        # Step 2: filter by corruption if we know it
        if corrupted is not None:
            filtered = [ln for ln in candidates if bool(ln.get("corrupted")) == corrupted]
            if filtered:
                candidates = filtered

        # Step 3: filter by gem level, if known
        if gem_level is not None:
            filtered = [ln for ln in candidates if ln.get("gemLevel") == gem_level]
            if filtered:
                candidates = filtered

        # Step 4: filter by gem quality, if known
        if gem_quality is not None:
            filtered = [ln for ln in candidates if ln.get("gemQuality") == gem_quality]
            if filtered:
                candidates = filtered

        # Step 5: pick the highest chaosValue as a fallback
        best = max(
            candidates,
            key=lambda ln: float(ln.get("chaosValue") or 0.0),
        )
        return best


# Testing
if __name__ == "__main__":
    # Test the API
    api = PoeNinjaAPI(league="Standard")

    try:
        # Test league detection
        current_league = api.detect_current_league()
        print(f"Current league: {current_league}")

        # Test divine orb price
        currency_data = api.get_currency_overview()
        divine_data = next((item for item in currency_data.get("lines", [])
                            if "divine" in item.get("currencyTypeName", "").lower()), None)
        if divine_data:
            print(f"Divine Orb: {divine_data.get('chaosEquivalent', 'N/A')} chaos")

        # Test unique item
        shavs = api.find_item_price("Shavronne's Wrappings", base_type="Occultist's Vestment", rarity="UNIQUE")
        if shavs:
            print(f"Shavronne's Wrappings: {shavs.get('chaosValue', 'N/A')} chaos")

        print(f"\nCache size: {api.get_cache_size()} entries")

    finally:
        api.close()