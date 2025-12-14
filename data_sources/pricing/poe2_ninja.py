"""
PoE2.ninja API client for Path of Exile 2 pricing data.
Inherits from BaseAPIClient for rate limiting and caching.

Note: PoE2 uses Exalted Orbs as the base currency (not Chaos).
"""
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests

from core.constants import API_TIMEOUT_DEFAULT
from data_sources.base_api import BaseAPIClient, RateLimitExceeded

logger = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def _normalize_currency_name(name: str) -> str:
    """
    Normalize currency name for cache key lookups.

    Cached to avoid repeated string operations for common currencies.
    """
    return (name or "").strip().lower()


class Poe2NinjaAPI(BaseAPIClient):
    """
    Client for poe2.ninja economy API (PoE2 only).

    Provides access to:
    - Currency prices (in Exalted Orbs, the PoE2 base currency)
    - Unique item prices
    - Skill gems, runes, soul cores, etc.

    Key difference from PoE1: Exalted Orbs are the base currency,
    not Chaos Orbs. Divine Orbs are worth ~70-100 Exalts.
    """

    # API endpoint types for PoE2
    CURRENCY_TYPES = ["Currency"]
    ITEM_TYPES = [
        "UniqueWeapon",
        "UniqueArmour",
        "UniqueAccessory",
        "UniqueFlask",
        "UniqueJewel",
        "SkillGem",
        "Rune",
        "SoulCore",
    ]

    def __init__(self, league: str = "Standard"):
        """
        Initialize poe2.ninja API client.

        Args:
            league: League name (e.g., "Standard", "Fate of the Vaal")
        """
        super().__init__(
            base_url="https://poe2.ninja/api/data",
            rate_limit=0.33,  # ~1 request per 3 seconds (community standard)
            cache_ttl=3600,  # Cache for 1 hour
            user_agent="PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)",
        )

        self.league = league

        # PoE2: Divine rate in Exalted (not Chaos)
        # e.g., 80.0 means 1 Divine = 80 Exalts
        self.divine_exalted_rate: float = 0.0

        # Indexed currency data for O(1) lookups (built on first fetch)
        self._currency_index: Dict[str, Dict[str, Any]] = {}

        # Divine rate cache with expiry (1 hour)
        self._divine_rate_expiry: float = 0.0

        logger.info(f"Initialized Poe2NinjaAPI for league: {league}")

    def refresh_divine_rate_from_currency(self) -> float:
        """
        Fetch poe2.ninja currencyoverview and derive exalts_per_divine from
        the Divine Orb entry.

        Sets self.divine_exalted_rate and returns it.
        """
        try:
            data = self.get_currency_overview()
        except (requests.RequestException, RateLimitExceeded) as exc:
            logger.warning("Failed to fetch currency overview for divine rate: %s", exc)
            self.divine_exalted_rate = 0.0
            return 0.0

        lines = data.get("lines") or []
        for line in lines:
            name = (line.get("currencyTypeName") or "").strip().lower()
            if name == "divine orb":
                # PoE2 uses exaltedValue instead of chaosEquivalent
                exalt_raw: Any = (
                    line.get("exaltedValue")
                    or line.get("chaosEquivalent")  # fallback
                    or 0.0
                )
                try:
                    exalt_equiv = float(exalt_raw)
                except (TypeError, ValueError):
                    exalt_equiv = 0.0

                self.divine_exalted_rate = exalt_equiv
                logger.info(
                    "poe2.ninja divine_exalted_rate set to %.2f exalts per divine (league=%s)",
                    self.divine_exalted_rate,
                    self.league,
                )
                return self.divine_exalted_rate

        logger.warning(
            "Divine Orb not found in poe2.ninja currencyoverview for league %s; "
            "leaving divine_exalted_rate=0.0",
            self.league,
        )
        self.divine_exalted_rate = 0.0
        return 0.0

    def ensure_divine_rate(self) -> float:
        """
        Return a sane exalts-per-divine rate, using cached value if valid.

        Uses time-based caching (1 hour) to avoid repeated API calls.
        """
        import time

        # Check if cached rate is still valid (within 1 hour)
        now = time.time()
        if now < self._divine_rate_expiry:
            try:
                rate = float(self.divine_exalted_rate)
                if rate > 10.0:  # Anything <= 10 exalts/div is bogus
                    return rate
            except (TypeError, ValueError):
                pass  # Invalid cached rate, refresh

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
        return f"poe2:{endpoint}:{league}:{type_param}"

    def get_current_leagues(self) -> List[Dict[str, str]]:
        """
        Fetch list of current PoE2 trade leagues from the official PoE2 trade API.

        Returns:
            List of league dicts with 'name' and 'displayName'
        """
        url = "https://www.pathofexile.com/api/trade2/data/leagues"
        headers = {
            "User-Agent": "PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=API_TIMEOUT_DEFAULT)
            resp.raise_for_status()
            data = resp.json()

            result = data.get("result", [])
            # Deduplicate by league id
            id_to_text: dict[str, str] = {}

            for entry in result:
                league_id = entry.get("id")
                text = entry.get("text") or league_id
                if not league_id:
                    continue

                if league_id not in id_to_text:
                    id_to_text[league_id] = text

            leagues: List[Dict[str, str]] = [
                {"name": league_id, "displayName": text}
                for league_id, text in id_to_text.items()
            ]

            if leagues:
                logger.info(
                    "Fetched %d PoE2 leagues from trade API: %s",
                    len(leagues),
                    ", ".join(league["name"] for league in leagues),
                )
                return leagues

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch PoE2 leagues from trade API: {e}")

        # Fallback
        logger.info("Falling back to static PoE2 league list")
        return [
            {"name": "Standard", "displayName": "Standard"},
        ]

    def detect_current_league(self) -> str:
        """
        Auto-detect the current PoE2 temp league (non-Standard).

        Returns:
            League name, defaults to "Standard" if no temp league found
        """
        leagues = self.get_current_leagues()

        # Filter out permanent leagues
        temp_leagues = [
            league for league in leagues
            if league['name'] not in ['Standard', 'Hardcore']
        ]

        if temp_leagues:
            detected = temp_leagues[0]['name']
            logger.info(f"Detected current PoE2 league: {detected}")
            return detected

        logger.info("No PoE2 temp league detected, using Standard")
        return "Standard"

    def get_currency_overview(self) -> Dict[str, Any]:
        """
        Get currency price overview for current league.

        Returns:
            Dict with 'lines' (currency data) and 'currencyDetails'

        Note: PoE2 prices are in Exalted Orbs, not Chaos.
        """
        data = self.get(
            "currencyoverview",
            params={"league": self.league, "type": "Currency"}
        )

        # Build icon lookup from currencyDetails
        icon_map: Dict[str, str] = {}
        for detail in data.get("currencyDetails", []):
            name = (detail.get("name") or "").strip().lower()
            if name and detail.get("icon"):
                icon_map[name] = detail["icon"]

        # Build indexed lookup for O(1) currency price queries
        self._currency_index.clear()
        for item in data.get("lines", []):
            name = (item.get("currencyTypeName") or "").strip().lower()
            if name:
                self._currency_index[name] = item
                # Inject icon from currencyDetails
                if name in icon_map:
                    item["icon"] = icon_map[name]
                # Update divine/exalted conversion rate
                if name == "divine orb":
                    self.divine_exalted_rate = item.get("exaltedValue", 80.0)
                    logger.info(f"Divine Orb = {self.divine_exalted_rate:.1f} exalts")

        logger.debug(f"Built PoE2 currency index with {len(self._currency_index)} entries")
        return data

    def get_currency_price(self, currency_name: str) -> tuple[float, str]:
        """
        Get price for a currency item using O(1) indexed lookup.

        Args:
            currency_name: Name of currency (e.g., "Divine Orb", "Chaos Orb")

        Returns:
            Tuple of (exalted_value, source_info) or (0.0, "not found")

        Note: PoE2 uses Exalted Orbs as base currency, so Exalted = 1.0
        """
        key = _normalize_currency_name(currency_name)
        if not key:
            return 0.0, "empty name"

        # Exalted Orb is the reference currency in PoE2 - always 1.0
        if key == "exalted orb":
            return 1.0, "poe2.ninja currency (reference)"

        # Ensure index is populated
        if not self._currency_index:
            try:
                self.get_currency_overview()
            except (requests.RequestException, RateLimitExceeded) as exc:
                logger.warning("Failed to fetch currency overview: %s", exc)
                return 0.0, "fetch error"

        # O(1) lookup
        item = self._currency_index.get(key)
        if item:
            # PoE2 uses exaltedValue
            exalt_raw = item.get("exaltedValue") or item.get("chaosEquivalent") or 0.0
            try:
                return float(exalt_raw), "poe2.ninja currency"
            except (TypeError, ValueError):
                return 0.0, "parse error"

        return 0.0, "not found"

    def _get_item_overview(self, item_type: str) -> dict | None:
        """
        Shared helper for poe2.ninja itemoverview endpoints.
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
        except (requests.RequestException, RateLimitExceeded) as e:
            logger.warning(f"Failed to fetch itemoverview for {item_type}: {e}")
            return None

    def get_skill_gem_overview(self) -> dict | None:
        """
        Return poe2.ninja SkillGem overview for the current league.

        Contains lines with: name, gemLevel, gemQuality, exaltedValue, etc.
        """
        return self._get_item_overview("SkillGem")

    def get_rune_overview(self) -> dict | None:
        """
        Return poe2.ninja Rune overview for the current league.

        PoE2-specific item type.
        """
        return self._get_item_overview("Rune")

    def get_soul_core_overview(self) -> dict | None:
        """
        Return poe2.ninja SoulCore overview for the current league.

        PoE2-specific item type.
        """
        return self._get_item_overview("SoulCore")

    def _find_from_overview_by_name(self, overview_type: str, item_name: str) -> dict | None:
        """
        Look up a poe2.ninja itemoverview entry by name.
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
                return dict(line)

        # Fallback: loose substring match
        for line in lines:
            n = norm(line.get("name"))
            if key in n or n in key:
                return dict(line)

        return None

    def find_item_price(
        self,
        item_name: str,
        base_type: str | None = None,
        rarity: str | None = None,
        gem_level: int | None = None,
        gem_quality: int | None = None,
        corrupted: bool | None = None,
    ) -> dict | None:
        """
        Main item price resolver for PoE2.

        Returns dict with 'exaltedValue' (not 'chaosValue' like PoE1).
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

        # ---------- Runes (PoE2-specific) ----------
        if "rune" in lower_name:
            hit = self._find_from_overview_by_name("Rune", name)
            if hit:
                return hit

        # ---------- Soul Cores (PoE2-specific) ----------
        if "soul core" in lower_name or "soulcore" in lower_name:
            hit = self._find_from_overview_by_name("SoulCore", name)
            if hit:
                return hit

        # ---------- Uniques ----------
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
                            return dict(item)

                except (KeyError, TypeError, AttributeError) as e:
                    logger.debug(f"Search in {item_type} failed: {e}")

        return None

    def _find_gem_price(
        self,
        name: str,
        gem_level: int | None,
        gem_quality: int | None,
        corrupted: bool | None,
    ) -> dict | None:
        """Find price for a skill gem."""
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

        # Step 5: pick the highest exaltedValue as a fallback
        best = max(
            candidates,
            key=lambda ln: float(ln.get("exaltedValue") or ln.get("chaosValue") or 0.0),
        )
        return dict(best)


# Testing
if __name__ == "__main__":
    # Test the API
    api = Poe2NinjaAPI(league="Standard")

    try:
        # Test league detection
        current_league = api.detect_current_league()
        print(f"Current PoE2 league: {current_league}")

        # Test divine orb price
        currency_data = api.get_currency_overview()
        divine_data = next((item for item in currency_data.get("lines", [])
                            if "divine" in item.get("currencyTypeName", "").lower()), None)
        if divine_data:
            print(f"Divine Orb: {divine_data.get('exaltedValue', 'N/A')} exalts")

        print(f"\nCache size: {api.get_cache_size()} entries")

    finally:
        api.close()
