"""
Path of Exile Stash API Client.

Accesses user's stash tabs via POESESSID cookie authentication.
This allows pricing of all items in a user's stash.

SECURITY NOTE: POESESSID is a sensitive credential that grants full
account access. Only use locally - never send to third-party servers.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, cast

import requests

logger = logging.getLogger(__name__)


@dataclass
class StashTab:
    """Represents a stash tab."""
    id: str
    name: str
    index: int
    type: str  # "NormalStash", "CurrencyStash", "MapStash", etc.
    items: List[Dict[str, Any]] = field(default_factory=list)

    # Folder info
    folder: Optional[str] = None
    children: List["StashTab"] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.items)


@dataclass
class StashSnapshot:
    """A snapshot of all stash tabs at a point in time."""
    account_name: str
    league: str
    tabs: List[StashTab] = field(default_factory=list)
    total_items: int = 0
    fetched_at: str = ""

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Get all items from all tabs."""
        items = []
        for tab in self.tabs:
            items.extend(tab.items)
            for child in tab.children:
                items.extend(child.items)
        return items


class PoEStashClient:
    """
    Client for accessing Path of Exile stash data via POESESSID.

    Usage:
        client = PoEStashClient("your_poesessid_here")
        snapshot = client.fetch_all_stashes("YourAccount", "Phrecia")

        for tab in snapshot.tabs:
            print(f"{tab.name}: {tab.item_count} items")
    """

    # API endpoints
    BASE_URL = "https://www.pathofexile.com"
    STASH_URL = "/character-window/get-stash-items"
    CHARACTERS_URL = "/character-window/get-characters"
    ITEMS_URL = "/character-window/get-items"

    # Rate limiting - GGG rate limits are strict, need 1.5s+ between requests
    REQUEST_DELAY = 1.5  # seconds between requests (be nice to GGG servers)
    RATE_LIMIT_WAIT = 60  # seconds to wait when rate limited (429 response)

    def __init__(
        self,
        poesessid: str,
        user_agent: str = "PoEPriceChecker/1.0",
        rate_limit_callback: Optional[Callable[[int, int], Any]] = None,
    ):
        """
        Initialize the client.

        Args:
            poesessid: Your POESESSID cookie value from pathofexile.com
            user_agent: User-Agent header (required by GGG)
            rate_limit_callback: Optional callback(wait_seconds, attempt) called when rate limited
        """
        self.session = requests.Session()
        self.session.cookies.set("POESESSID", poesessid, domain=".pathofexile.com")
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json",
        })
        self._last_request_time = 0.0
        self._rate_limit_callback = rate_limit_callback

    def _rate_limit(self) -> None:
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Make a GET request to the API with rate limit handling.

        When a 429 rate limit response is received, waits RATE_LIMIT_WAIT seconds
        (default 60s) before retrying. This allows large stash pulls to complete
        even when rate limited.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            max_retries: Maximum retry attempts for 429 errors

        Returns:
            Response JSON data
        """
        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())
            except requests.exceptions.HTTPError:
                if response.status_code == 403:
                    logger.error("Access denied - POESESSID may be invalid or expired")
                    raise
                elif response.status_code == 429:
                    if attempt < max_retries:
                        # Wait fixed duration on rate limit
                        wait_time = self.RATE_LIMIT_WAIT
                        logger.warning(
                            f"Rate limited (429). Waiting {wait_time}s before retry "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        # Notify caller about rate limit wait
                        if self._rate_limit_callback:
                            self._rate_limit_callback(wait_time, attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            "Rate limited - max retries exceeded after "
                            f"{max_retries} attempts with {self.RATE_LIMIT_WAIT}s waits."
                        )
                        raise
                else:
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise

        # Should not reach here, but just in case
        raise requests.exceptions.RequestException("Max retries exceeded")

    def verify_session(self) -> bool:
        """
        Verify that the POESESSID is valid.

        Returns:
            True if session is valid
        """
        try:
            chars = self._get(self.CHARACTERS_URL)
            # If we get character data, session is valid
            return isinstance(chars, list)
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
            return False

    def get_characters(self) -> List[Dict[str, Any]]:
        """Get list of characters on the account."""
        result = self._get(self.CHARACTERS_URL)
        # API returns dict with 'characters' key or a list directly
        if isinstance(result, dict):
            return cast(List[Dict[str, Any]], result.get("characters", []))
        return cast(List[Dict[str, Any]], result)

    def get_stash_tabs(
        self,
        account_name: str,
        league: str
    ) -> List[Dict[str, Any]]:
        """
        Get list of stash tabs (metadata only, no items).

        Args:
            account_name: PoE account name
            league: League name (e.g., "Standard", "Phrecia")

        Returns:
            List of tab metadata
        """
        params = {
            "accountName": account_name,
            "league": league,
            "tabs": 1,
            "tabIndex": 0,
        }

        result = self._get(self.STASH_URL, params)
        return cast(List[Dict[str, Any]], result.get("tabs", []))

    def get_stash_tab_items(
        self,
        account_name: str,
        league: str,
        tab_index: int
    ) -> Dict[str, Any]:
        """
        Get items from a specific stash tab.

        Args:
            account_name: PoE account name
            league: League name
            tab_index: Tab index (0-based)

        Returns:
            Dict with 'items' list and tab metadata
        """
        params = {
            "accountName": account_name,
            "league": league,
            "tabs": 0,  # Don't need tab list again
            "tabIndex": tab_index,
        }

        return self._get(self.STASH_URL, params)

    def get_stash_tab_by_id(
        self,
        account_name: str,
        league: str,
        stash_id: str,
        substash_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get items from a stash tab using its ID (for substash access).

        This uses the newer stash endpoint format that supports substash_id
        for accessing nested tabs like UniqueStash categories.

        Args:
            account_name: PoE account name
            league: League name
            stash_id: The stash tab's public ID
            substash_id: Optional substash ID for nested tabs

        Returns:
            Dict with stash data including items
        """
        # Try the character-window endpoint with stashId parameter
        # This is an alternative to the tabIndex approach
        params = {
            "accountName": account_name,
            "league": league,
            "tabs": 0,
            "stashId": stash_id,
        }

        if substash_id:
            params["substashId"] = substash_id

        try:
            return self._get(self.STASH_URL, params)
        except Exception as e:
            logger.debug(f"get_stash_tab_by_id failed for {stash_id}/{substash_id}: {e}")
            return {"items": []}

    def fetch_all_stashes(
        self,
        account_name: str,
        league: str,
        max_tabs: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], Any]] = None,
    ) -> StashSnapshot:
        """
        Fetch all stash tabs and their items.

        Args:
            account_name: PoE account name
            league: League name
            max_tabs: Maximum tabs to fetch (None for all)
            progress_callback: Optional callback(current, total) for progress

        Returns:
            StashSnapshot with all tabs and items
        """
        from datetime import datetime

        # First, get tab list
        logger.info(f"Fetching stash tabs for {account_name} in {league}...")
        tabs_meta = self.get_stash_tabs(account_name, league)

        total_tabs = len(tabs_meta)
        if max_tabs:
            total_tabs = min(total_tabs, max_tabs)

        logger.info(f"Found {len(tabs_meta)} tabs, fetching {total_tabs}...")

        tabs = []
        total_items = 0

        for i, tab_meta in enumerate(tabs_meta[:total_tabs]):
            tab_name = tab_meta.get("n", f"Tab {i}")
            tab_type = tab_meta.get("type", "NormalStash")
            tab_id = tab_meta.get("id", str(i))
            children_meta = tab_meta.get("children", [])

            if progress_callback:
                progress_callback(i + 1, total_tabs)

            logger.debug(f"Fetching tab {i}: {tab_name} ({tab_type})")

            try:
                tab_data = self.get_stash_tab_items(account_name, league, i)
                items = tab_data.get("items", [])
            except Exception as e:
                logger.warning(f"Failed to fetch tab {i} ({tab_name}): {e}")
                items = []

            # Create child tabs for tabs with children (like UniqueStash, FolderStash)
            children: List[StashTab] = []
            if children_meta:
                logger.debug(f"  Tab has {len(children_meta)} sub-tabs")

                # Specialized stash tabs (UniqueStash, MapStash, etc.) store ALL items
                # in the parent tab. The "children" are just organizational categories.
                #
                # NOTE: UniqueStash has known API limitations - GGG's API doesn't fully
                # support the "tab-in-tab" structure. Items may not be returned reliably.
                # See: https://github.com/viktorgullmark/exilence/issues/246
                #
                # For specialized tabs, we DON'T distribute items to children because:
                # 1. UniqueStash API is unreliable for item placement data
                # 2. The x/y coordinates don't map to category indices
                # 3. Creating empty children tabs is confusing for users
                #
                # Instead, we keep all items in the parent tab.
                specialized_types = {
                    "UniqueStash", "MapStash", "FragmentStash", "DivinationCardStash",
                    "EssenceStash", "DelveStash", "BlightStash", "MetamorphStash",
                    "DeliriumStash", "GemStash", "FlaskStash",
                }

                if tab_type in specialized_types:
                    # For specialized tabs, the parent tab fetch often returns items.
                    # But for UniqueStash specifically, items may not be returned.
                    # Try fetching substabs if parent has no items.

                    if tab_type == "UniqueStash" and len(items) == 0:
                        # UniqueStash returned no items - try fetching each substab
                        logger.info(
                            f"  UniqueStash '{tab_name}' returned 0 items, "
                            f"attempting substab fetch for {len(children_meta)} categories..."
                        )

                        substab_items = []
                        for child_meta in children_meta:
                            child_id = child_meta.get("id")
                            child_name = child_meta.get("n", "Unknown")

                            if child_id:
                                # Try fetching by substash ID
                                try:
                                    child_data = self.get_stash_tab_by_id(
                                        account_name, league, tab_id, child_id
                                    )
                                    child_items = child_data.get("items", [])
                                    if child_items:
                                        logger.info(
                                            f"    -> Substab '{child_name}' ({child_id}): "
                                            f"{len(child_items)} items!"
                                        )
                                        substab_items.extend(child_items)
                                    else:
                                        logger.debug(
                                            f"    -> Substab '{child_name}': no items"
                                        )
                                except Exception as e:
                                    logger.debug(
                                        f"    -> Substab '{child_name}' fetch failed: {e}"
                                    )

                        if substab_items:
                            logger.info(
                                f"  UniqueStash substab fetch succeeded! "
                                f"Found {len(substab_items)} items total."
                            )
                            items = substab_items
                        else:
                            logger.warning(
                                f"  UniqueStash '{tab_name}': substab fetch returned no items. "
                                f"This is a known GGG API limitation."
                            )
                    else:
                        logger.debug(
                            f"  Specialized tab ({tab_type}): {len(items)} items in parent, "
                            f"ignoring {len(children_meta)} category children"
                        )

                    # Don't create children - all items stay in the parent tab.

                else:
                    # For FolderStash, children are separate fetchable tabs
                    for j, child_meta in enumerate(children_meta):
                        child_name = child_meta.get("n", f"{tab_name} ({j})")
                        child_type = child_meta.get("type", tab_type)
                        child_id = child_meta.get("id", f"{tab_id}_{j}")
                        child_index = child_meta.get("i", j)

                        # Fetch items from child tab using its index
                        try:
                            child_data = self.get_stash_tab_items(
                                account_name, league, child_index
                            )
                            child_items = child_data.get("items", [])
                        except Exception as e:
                            logger.warning(
                                f"Failed to fetch sub-tab {child_index} ({child_name}): {e}"
                            )
                            child_items = []

                        child_tab = StashTab(
                            id=child_id,
                            name=child_name,
                            index=child_index,
                            type=child_type,
                            items=child_items,
                            folder=tab_name,
                        )
                        children.append(child_tab)
                        total_items += len(child_items)
                        logger.debug(f"    -> Sub-tab '{child_name}': {len(child_items)} items")

            tab = StashTab(
                id=tab_id,
                name=tab_name,
                index=i,
                type=tab_type,
                items=items,
                children=children,
            )

            tabs.append(tab)
            total_items += len(items)

            logger.debug(f"  -> {len(items)} items")

        snapshot = StashSnapshot(
            account_name=account_name,
            league=league,
            tabs=tabs,
            total_items=total_items,
            fetched_at=datetime.now().isoformat(),
        )

        logger.info(f"Fetched {total_items} items from {len(tabs)} tabs")
        return snapshot


def get_available_leagues(include_standard: bool = False) -> List[str]:
    """
    Get list of active leagues.

    Args:
        include_standard: If True, include Standard/Hardcore leagues

    Returns:
        List of league names, current league first
    """
    # Current league first
    leagues = [
        "Keepers",  # Current league (update as needed)
        "Hardcore Keepers",
    ]

    if include_standard:
        leagues.extend([
            "Standard",
            "Hardcore",
        ])

    return leagues


# Testing
if __name__ == "__main__":
    import sys

    # Configure logging to show our module's logs
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s: %(message)s"
    )
    # Also enable our module's logger
    logger.setLevel(logging.DEBUG)

    def print_usage():
        print("Usage: python poe_stash_api.py <POESESSID> <account_name> [league] [--unique-test]")
        print("\nModes:")
        print("  Default:       Fetch first 5 stash tabs")
        print("  --unique-test: Test UniqueStash substab fetching specifically")
        print("\nTo get your POESESSID:")
        print("1. Log into pathofexile.com")
        print("2. Press F12 -> Application -> Cookies")
        print("3. Copy the POESESSID value")
        print("\nRate Limiting:")
        print("  - 1.5s delay between requests (GGG's servers)")
        print("  - 60s wait on 429 rate limit errors")

    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    poesessid = sys.argv[1]
    account_name = sys.argv[2]
    league = "Standard"
    unique_test = False

    # Parse optional args
    for arg in sys.argv[3:]:
        if arg == "--unique-test":
            unique_test = True
        else:
            league = arg

    # Rate limit callback for user feedback
    def on_rate_limit(wait_seconds: int, attempt: int):
        print(f"\n⚠️  Rate limited! Waiting {wait_seconds}s (attempt {attempt})...")
        print("   This is normal - GGG limits API requests.")

    print(f"\n{'='*60}")
    print("PoE Stash API Test")
    print(f"{'='*60}")
    print(f"Account: {account_name}")
    print(f"League:  {league}")
    print(f"Mode:    {'UniqueStash Test' if unique_test else 'General Test'}")
    print(f"{'='*60}\n")

    print("Connecting to PoE API...")
    client = PoEStashClient(poesessid, rate_limit_callback=on_rate_limit)

    print("Verifying session (1 request)...")
    if not client.verify_session():
        print("❌ ERROR: Invalid POESESSID - session verification failed")
        sys.exit(1)

    print("✅ Session valid!\n")

    if unique_test:
        # Dedicated UniqueStash test
        print("="*60)
        print("UNIQUE STASH TAB TEST")
        print("="*60)
        print("\nStep 1: Fetching tab list (1 request)...")

        tabs_meta = client.get_stash_tabs(account_name, league)
        print(f"Found {len(tabs_meta)} tabs total.\n")

        # Find UniqueStash tabs
        unique_tabs = [
            (i, t) for i, t in enumerate(tabs_meta)
            if t.get("type") == "UniqueStash"
        ]

        if not unique_tabs:
            print("❌ No UniqueStash tab found in this league.")
            print("\nAvailable tab types:")
            for i, t in enumerate(tabs_meta[:10]):
                print(f"  [{i}] {t.get('n', 'Unknown')} ({t.get('type', 'Unknown')})")
            sys.exit(1)

        print(f"Found {len(unique_tabs)} UniqueStash tab(s):\n")

        for tab_index, tab_meta in unique_tabs:
            tab_name = tab_meta.get("n", "Unique Collection")
            tab_id = tab_meta.get("id", "unknown")
            children = tab_meta.get("children", [])

            print(f"Tab [{tab_index}]: {tab_name}")
            print(f"  ID: {tab_id}")
            print(f"  Children/Categories: {len(children)}")

            # Step 2: Try normal fetch
            print(f"\nStep 2: Normal fetch via tabIndex={tab_index} (1 request)...")
            try:
                tab_data = client.get_stash_tab_items(account_name, league, tab_index)
                items = tab_data.get("items", [])
                print(f"  Result: {len(items)} items")

                if items:
                    print("  ✅ Normal fetch WORKS! Sample items:")
                    for item in items[:5]:
                        name = item.get("name") or item.get("typeLine", "Unknown")
                        print(f"      - {name}")
                else:
                    print("  ⚠️  Normal fetch returned 0 items")
            except Exception as e:
                print(f"  ❌ Normal fetch failed: {e}")
                items = []

            # Step 3: Try substash fetch if normal failed
            if not items and children:
                print(f"\nStep 3: Trying substash fetch ({len(children)} substabs)...")
                print("  Note: Each substab = 1 API request with 1.5s delay\n")

                total_substab_items = 0
                for j, child in enumerate(children):
                    child_id = child.get("id")
                    child_name = child.get("n", f"Category {j}")

                    print(f"  [{j+1}/{len(children)}] Fetching '{child_name}'...", end=" ", flush=True)

                    if child_id:
                        try:
                            child_data = client.get_stash_tab_by_id(
                                account_name, league, tab_id, child_id
                            )
                            child_items = child_data.get("items", [])
                            total_substab_items += len(child_items)

                            if child_items:
                                print(f"✅ {len(child_items)} items!")
                                for item in child_items[:2]:
                                    name = item.get("name") or item.get("typeLine", "Unknown")
                                    print(f"        - {name}")
                            else:
                                print("0 items")
                        except Exception as e:
                            print(f"❌ Error: {e}")
                    else:
                        print("⚠️  No child ID available")

                print(f"\n  Substab fetch complete: {total_substab_items} items total")

                if total_substab_items > 0:
                    print("\n✅ SUCCESS! Substab fetching WORKS for UniqueStash!")
                else:
                    print("\n❌ Substab fetch returned 0 items.")
                    print("   This confirms the GGG API limitation.")
                    print("   Items in UniqueStash cannot be retrieved via API.")

            elif items:
                print("\n✅ UniqueStash items fetched successfully via normal method!")

            print()

    else:
        # General test - fetch first 5 tabs
        print("Fetching first 5 stash tabs...")
        print("(This will make ~6 API requests with 1.5s delays)\n")

        snapshot = client.fetch_all_stashes(
            account_name,
            league,
            max_tabs=5,
            progress_callback=lambda cur, tot: print(f"  Tab {cur}/{tot}...")
        )

        print(f"\n{'='*60}")
        print("STASH SUMMARY")
        print(f"{'='*60}")
        print(f"Account:     {snapshot.account_name}")
        print(f"League:      {snapshot.league}")
        print(f"Total Items: {snapshot.total_items}")
        print(f"\nTabs:")
        for tab in snapshot.tabs:
            status = ""
            if tab.type == "UniqueStash" and tab.item_count == 0:
                status = " ⚠️  (known API limitation)"
            print(f"  [{tab.index}] {tab.name} ({tab.type}): {tab.item_count} items{status}")

    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}")
