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
            user_agent="PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)",
        )

        self.league = league
        # 0.0 = "unknown until we ask poe.ninja"
        self.divine_chaos_rate: float = 0.0

        # Indexed currency data for O(1) lookups (built on first fetch)
        self._currency_index: Dict[str, Dict[str, Any]] = {}

        # Divine rate cache with expiry (1 hour)
        self._divine_rate_expiry: float = 0.0

        logger.info(f"Initialized PoeNinjaAPI for league: {league}")

    def refresh_divine_rate_from_currency(self) -> float:
        """
        Fetch poe.ninja currencyoverview and derive chaos_per_divine from
        the Divine Orb entry.

        Sets self.divine_chaos_rate and returns it.
        """
        try:
            data = self.get_currency_overview()
        except Exception as exc:
            logger.warning("Failed to fetch currency overview for divine rate: %s", exc)
            self.divine_chaos_rate = 0.0
            return 0.0

        lines = data.get("lines") or []
        for line in lines:
            name = (line.get("currencyTypeName") or "").strip().lower()
            if name == "divine orb":
                chaos_raw: Any = (
                        line.get("chaosEquivalent")
                        or line.get("chaosValue")
                        or 0.0
                )
                try:
                    chaos_equiv = float(chaos_raw)
                except (TypeError, ValueError):
                    chaos_equiv = 0.0

                self.divine_chaos_rate = chaos_equiv
                logger.info(
                    "poe.ninja divine_chaos_rate set to %.2f chaos per divine (league=%s)",
                    self.divine_chaos_rate,
                    self.league,
                )
                return self.divine_chaos_rate

        logger.warning(
            "Divine Orb not found in poe.ninja currencyoverview for league %s; "
            "leaving divine_chaos_rate=0.0",
            self.league,
        )
        self.divine_chaos_rate = 0.0
        return 0.0

    def ensure_divine_rate(self) -> float:
        """
        Return a sane chaos-per-divine rate, using cached value if valid.

        Uses time-based caching (1 hour) to avoid repeated API calls.
        """
        import time

        # Check if cached rate is still valid (within 1 hour)
        now = time.time()
        if now < self._divine_rate_expiry:
            try:
                rate = float(self.divine_chaos_rate)
                if rate > 10.0:  # Anything <= 10c/div is bogus
                    return rate
            except (TypeError, ValueError):
                pass

        # Cache miss or invalid - refresh from API
        rate = self.refresh_divine_rate_from_currency()

        # Set expiry for 1 hour
        if rate > 10.0:
            self._divine_rate_expiry = now + 3600  # 1 hour cache

        return rate

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
                    ", ".join(league["name"] for league in leagues),
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
        temp_leagues = [league for league in leagues if league['name'] not in ['Standard', 'Hardcore']]

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

        # Build indexed lookup for O(1) currency price queries
        self._currency_index.clear()
        for item in data.get("lines", []):
            name = (item.get("currencyTypeName") or "").strip().lower()
            if name:
                self._currency_index[name] = item
                # Update divine/chaos conversion rate
                if name == "divine orb":
                    self.divine_chaos_rate = item.get("chaosEquivalent", 1.0)
                    logger.info(f"Divine Orb = {self.divine_chaos_rate:.1f} chaos")

        logger.debug(f"Built currency index with {len(self._currency_index)} entries")
        return data

    def get_currency_price(self, currency_name: str) -> tuple[float, str]:
        """
        Get price for a currency item using O(1) indexed lookup.

        Args:
            currency_name: Name of currency (e.g., "Divine Orb", "Exalted Orb")

        Returns:
            Tuple of (chaos_value, source_info) or (0.0, "not found")
        """
        key = (currency_name or "").strip().lower()
        if not key:
            return 0.0, "empty name"

        # Chaos Orb is the reference currency - always 1.0c
        # poe.ninja doesn't list it since everything is priced relative to chaos
        if key == "chaos orb":
            return 1.0, "poe.ninja currency (reference)"

        # Ensure index is populated
        if not self._currency_index:
            try:
                self.get_currency_overview()
            except Exception as exc:
                logger.warning("Failed to fetch currency overview: %s", exc)
                return 0.0, "fetch error"

        # O(1) lookup
        item = self._currency_index.get(key)
        if item:
            chaos_raw = item.get("chaosEquivalent") or item.get("chaosValue") or 0.0
            try:
                return float(chaos_raw), "poe.ninja currency"
            except (TypeError, ValueError):
                return 0.0, "parse error"

        return 0.0, "not found"

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

        - Currency is handled separately in GUI via currencyoverview()
        - Here we handle:
            * Skill gems (SkillGem overview)
            * Unique items (armour, weapon, accessory, flask, jewel, maps)
            * Divination cards, fragments, etc. via itemoverview + heuristics
        """
        rarity_upper = (rarity or "").upper()
        name = (item_name or "").strip()
        lower_name = name.lower()

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

        # ---------- Fragments ----------
        # If your parser marks them as FRAGMENT, we can use the Fragment overview directly.
        if rarity_upper == "FRAGMENT":
            hit = self._find_from_overview_by_name("Fragment", name)
            if hit:
                return hit

        # ---------- Maps (unique & possibly non-unique) ----------
        # Vaal Temple Map showed up as rarity=UNIQUE in your logs.
        # If it's a map-like base, use the UniqueMap / Map overviews.
        if rarity_upper in ("MAP", "UNIQUE") and "map" in (base_type or name).lower():
            # Try unique maps first
            hit = self._find_from_overview_by_name("UniqueMap", name)
            if hit:
                return hit
            # Fallback: generic Map overview if poe.ninja exposes that
            hit = self._find_from_overview_by_name("Map", name)
            if hit:
                return hit

        # ---------- Other itemoverview-based misc with name heuristics ----------
        # These rely on simple substring checks in the item name, then the
        # corresponding poe.ninja overview.
        if "scarab" in lower_name:
            hit = self._find_from_overview_by_name("Scarab", name)
            if hit:
                return hit

        if "essence" in lower_name:
            hit = self._find_from_overview_by_name("Essence", name)
            if hit:
                return hit

        if "fossil" in lower_name:
            hit = self._find_from_overview_by_name("Fossil", name)
            if hit:
                return hit

        if "oil" in lower_name:
            hit = self._find_from_overview_by_name("Oil", name)
            if hit:
                return hit

        if "incubator" in lower_name:
            hit = self._find_from_overview_by_name("Incubator", name)
            if hit:
                return hit

        if "vial" in lower_name:
            hit = self._find_from_overview_by_name("Vial", name)
            if hit:
                return hit

        # ---------- Uniques (non-map) ----------
        if rarity_upper == "UNIQUE":
            search_key = item_name.lower()
            if base_type:
                search_key = f"{item_name.lower()} {base_type.lower()}"

            for item_type in ["UniqueWeapon", "UniqueArmour", "UniqueAccessory", "UniqueFlask", "UniqueJewel"]:
                try:
                    data = self._get_item_overview(item_type)
                    if not data:
                        continue

                    for item in data.get("lines", []):
                        item_key = item['name'].lower()
                        if item.get("baseType"):
                            item_key = f"{item['name'].lower()} {item['baseType'].lower()}"

                        if search_key == item_key or item_name.lower() in item_key:
                            return item

                except Exception as e:
                    logger.debug(f"Search in {item_type} failed: {e}")

        # Rares and other categories we don't explicitly know how to map
        # will fall through here.
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
