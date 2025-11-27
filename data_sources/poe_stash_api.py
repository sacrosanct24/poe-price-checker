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
from typing import Any, Dict, List, Optional

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

    # Rate limiting
    REQUEST_DELAY = 0.5  # seconds between requests (be nice to GGG servers)

    def __init__(self, poesessid: str, user_agent: str = "PoEPriceChecker/1.0"):
        """
        Initialize the client.

        Args:
            poesessid: Your POESESSID cookie value from pathofexile.com
            user_agent: User-Agent header (required by GGG)
        """
        self.session = requests.Session()
        self.session.cookies.set("POESESSID", poesessid, domain=".pathofexile.com")
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json",
        })
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to the API."""
        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logger.error("Access denied - POESESSID may be invalid or expired")
            elif response.status_code == 429:
                logger.error("Rate limited - too many requests")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

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
        return self._get(self.CHARACTERS_URL)

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
        return result.get("tabs", [])

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

    def fetch_all_stashes(
        self,
        account_name: str,
        league: str,
        max_tabs: Optional[int] = None,
        progress_callback: Optional[callable] = None,
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

            if progress_callback:
                progress_callback(i + 1, total_tabs)

            logger.debug(f"Fetching tab {i}: {tab_name} ({tab_type})")

            try:
                tab_data = self.get_stash_tab_items(account_name, league, i)
                items = tab_data.get("items", [])
            except Exception as e:
                logger.warning(f"Failed to fetch tab {i} ({tab_name}): {e}")
                items = []

            tab = StashTab(
                id=tab_id,
                name=tab_name,
                index=i,
                type=tab_type,
                items=items,
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


def get_available_leagues() -> List[str]:
    """
    Get list of active leagues.

    Returns common league names - actual availability depends on season.
    """
    return [
        "Standard",
        "Hardcore",
        "Phrecia",  # Current league (update as needed)
        "Hardcore Phrecia",
    ]


# Testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 3:
        print("Usage: python poe_stash_api.py <POESESSID> <account_name> [league]")
        print("\nTo get your POESESSID:")
        print("1. Log into pathofexile.com")
        print("2. Press F12 -> Application -> Cookies")
        print("3. Copy the POESESSID value")
        sys.exit(1)

    poesessid = sys.argv[1]
    account_name = sys.argv[2]
    league = sys.argv[3] if len(sys.argv) > 3 else "Standard"

    print(f"\nConnecting to PoE API...")
    client = PoEStashClient(poesessid)

    print(f"Verifying session...")
    if not client.verify_session():
        print("ERROR: Invalid POESESSID - session verification failed")
        sys.exit(1)

    print(f"Session valid! Fetching stashes...")

    # Fetch first 5 tabs as a test
    snapshot = client.fetch_all_stashes(
        account_name,
        league,
        max_tabs=5,
        progress_callback=lambda cur, tot: print(f"  Tab {cur}/{tot}...")
    )

    print(f"\n=== Stash Summary ===")
    print(f"Account: {snapshot.account_name}")
    print(f"League: {snapshot.league}")
    print(f"Total Items: {snapshot.total_items}")
    print(f"\nTabs:")
    for tab in snapshot.tabs:
        print(f"  [{tab.index}] {tab.name} ({tab.type}): {tab.item_count} items")
