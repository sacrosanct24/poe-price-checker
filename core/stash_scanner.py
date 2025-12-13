"""
Stash scanner for Path of Exile.

Fetches stash tabs via OAuth API and scans for valuable items.
"""

import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from core.constants import API_TIMEOUT_STASH
from core.poe_oauth import PoeOAuthClient


@dataclass
class StashItem:
    """Represents an item found in a stash tab."""

    name: str
    type_line: str
    rarity: str
    stash_tab_name: str
    stash_tab_index: int
    position_x: int
    position_y: int
    ilvl: int
    identified: bool
    corrupted: bool
    icon: str

    # Price info (filled by scanner)
    chaos_value: float = 0.0
    divine_value: float = 0.0
    confidence: str = "unknown"

    def __str__(self) -> str:
        name = self.name or self.type_line
        return f"{name} @ Tab '{self.stash_tab_name}' ({self.position_x}, {self.position_y})"


@dataclass
class StashTab:
    """Represents a stash tab."""

    name: str
    index: int
    tab_type: str
    items: List[StashItem]
    total_value_chaos: float = 0.0
    total_value_divine: float = 0.0


class StashScanner:
    """
    Scans Path of Exile stash tabs for valuable items.

    Uses OAuth to access private stash tabs.
    """

    # PoE API endpoints
    STASH_TABS_URL = "https://www.pathofexile.com/character-window/get-stash-tabs"
    STASH_ITEMS_URL = "https://www.pathofexile.com/character-window/get-stash-items"

    def __init__(
        self,
        oauth_client: PoeOAuthClient,
        league: str = "Standard",
        realm: str = "pc",
    ) -> None:
        """
        Initialize stash scanner.

        Args:
            oauth_client: Authenticated OAuth client
            league: League name (e.g., "Standard", "Hardcore", "Crucible")
            realm: Realm (usually "pc")
        """
        self.oauth = oauth_client
        self.league = league
        self.realm = realm

        self.logger = logging.getLogger("stash_scanner")

        # Get account name
        self.account_name: Optional[str] = None
        self._fetch_account_name()

    def _fetch_account_name(self) -> None:
        """Fetch the account name from PoE API."""
        token = self.oauth.get_access_token()
        if not token:
            raise ValueError(
                "Not authenticated - call oauth.authenticate() first")

        headers = {
            'Authorization': f'Bearer {token}',
        }

        try:
            # Get profile to extract account name
            response = requests.get(
                "https://www.pathofexile.com/api/profile",
                headers=headers,
                timeout=API_TIMEOUT_STASH,
            )
            response.raise_for_status()

            data = response.json()
            self.account_name = data.get('name')

            if not self.account_name:
                raise ValueError("Could not determine account name")

            self.logger.info("Account name: %s", self.account_name)

        except requests.RequestException as e:
            self.logger.error("Failed to fetch account name: %s", e)
            raise

    def get_stash_tabs(self) -> List[Dict[str, Any]]:
        """
        Fetch list of all stash tabs for the account.

        Returns:
            List of stash tab metadata
        """
        token = self.oauth.get_access_token()
        if not token:
            raise ValueError("Not authenticated")

        self.logger.info("Fetching stash tabs for league '%s'", self.league)

        headers = {
            'Authorization': f'Bearer {token}',
        }

        params = {
            'league': self.league,
            'realm': self.realm,
            'accountName': self.account_name,
            'tabs': 1,  # Include tab metadata
        }

        try:
            response = requests.get(
                self.STASH_TABS_URL,
                headers=headers,
                params=params,
                timeout=API_TIMEOUT_STASH,
            )
            response.raise_for_status()

            data = response.json()
            tabs: List[Dict[str, Any]] = data.get('tabs', [])

            self.logger.info("Found %d stash tabs", len(tabs))

            return tabs

        except requests.RequestException as e:
            self.logger.error("Failed to fetch stash tabs: %s", e)
            raise

    def get_stash_items(self, tab_index: int) -> List[Dict[str, Any]]:
        """
        Fetch items from a specific stash tab.

        Args:
            tab_index: Index of the stash tab (0-based)

        Returns:
            List of item data
        """
        token = self.oauth.get_access_token()
        if not token:
            raise ValueError("Not authenticated")

        self.logger.info("Fetching items from tab %d", tab_index)

        headers = {
            'Authorization': f'Bearer {token}',
        }

        params = {
            'league': self.league,
            'realm': self.realm,
            'accountName': self.account_name,
            'tabIndex': tab_index,
            'tabs': 0,  # Don't need tab metadata again
        }

        try:
            response = requests.get(
                self.STASH_ITEMS_URL,
                headers=headers,
                params=params,
                timeout=API_TIMEOUT_STASH,
            )
            response.raise_for_status()

            data = response.json()
            items: List[Dict[str, Any]] = data.get('items', [])

            self.logger.info("Found %d items in tab %d", len(items), tab_index)

            return items

        except requests.RequestException as e:
            self.logger.error(
                "Failed to fetch items from tab %d: %s", tab_index, e)
            raise

    def scan_all_tabs(self) -> List[StashTab]:
        """
        Scan all stash tabs and return structured data.

        Returns:
            List of StashTab objects with items
        """
        self.logger.info("Starting full stash scan")

        # Get all tabs
        tabs_data = self.get_stash_tabs()

        result: List[StashTab] = []

        for tab_data in tabs_data:
            tab_index = tab_data['i']
            tab_name = tab_data.get('n', f"Tab {tab_index}")
            tab_type = tab_data.get('type', 'NormalStash')

            self.logger.info(
                "Scanning tab %d: '%s' (%s)",
                tab_index,
                tab_name,
                tab_type)

            # Get items from this tab
            items_data = self.get_stash_items(tab_index)

            # Parse items
            items: List[StashItem] = []

            for item_data in items_data:
                item = self._parse_item(item_data, tab_name, tab_index)
                if item:
                    items.append(item)

            # Create StashTab object
            stash_tab = StashTab(
                name=tab_name,
                index=tab_index,
                tab_type=tab_type,
                items=items,
            )

            result.append(stash_tab)

            self.logger.info(
                "Tab '%s': %d items parsed",
                tab_name,
                len(items),
            )

        self.logger.info("Stash scan complete: %d tabs, %d total items", len(
            result), sum(len(t.items) for t in result))

        return result

    def _parse_item(
        self,
        item_data: Dict[str, Any],
        tab_name: str,
        tab_index: int,
    ) -> Optional[StashItem]:
        """
        Parse raw item data into StashItem object.

        Args:
            item_data: Raw item JSON from API
            tab_name: Name of the stash tab
            tab_index: Index of the stash tab

        Returns:
            StashItem or None if parsing failed
        """
        try:
            # Determine rarity
            frame_type = item_data.get('frameType', 0)
            rarity_map = {
                0: 'NORMAL',
                1: 'MAGIC',
                2: 'RARE',
                3: 'UNIQUE',
                4: 'GEM',
                5: 'CURRENCY',
                6: 'DIVINATION_CARD',
                8: 'PROPHECY',
                9: 'RELIC',
            }
            rarity = rarity_map.get(frame_type, 'UNKNOWN')

            item = StashItem(
                name=item_data.get('name', ''),
                type_line=item_data.get('typeLine', ''),
                rarity=rarity,
                stash_tab_name=tab_name,
                stash_tab_index=tab_index,
                position_x=item_data.get('x', 0),
                position_y=item_data.get('y', 0),
                ilvl=item_data.get('ilvl', 0),
                identified=item_data.get('identified', False),
                corrupted=item_data.get('corrupted', False),
                icon=item_data.get('icon', ''),
            )

            return item

        except Exception as e:
            self.logger.warning("Failed to parse item: %s", e)
            return None

    def filter_valuable_items(
        self,
        stash_tabs: List[StashTab],
        min_chaos_value: float = 10.0,
    ) -> List[Tuple[StashTab, StashItem]]:
        """
        Filter items by minimum chaos value.

        Args:
            stash_tabs: List of stash tabs with items
            min_chaos_value: Minimum chaos value threshold

        Returns:
            List of (tab, item) tuples for valuable items
        """
        valuable: List[Tuple[StashTab, StashItem]] = []

        for tab in stash_tabs:
            for item in tab.items:
                if item.chaos_value >= min_chaos_value:
                    valuable.append((tab, item))

        return valuable

    def scan_and_price(
        self,
        price_service: Any,
        min_chaos_value: float = 10.0,
    ) -> List[Tuple[StashTab, StashItem]]:
        """
        Scan all stash tabs and price check items.

        Args:
            price_service: PriceService instance to use for pricing
            min_chaos_value: Minimum chaos value to report

        Returns:
            List of (tab, item) tuples for valuable items
        """
        self.logger.info("Starting scan and price check")

        # Scan all tabs
        stash_tabs = self.scan_all_tabs()

        # Price check each item
        for tab in stash_tabs:
            tab_total_chaos = 0.0
            tab_total_divine = 0.0

            for item in tab.items:
                # Build item text for parser
                item_text = self._build_item_text(item)

                # Get prices
                try:
                    results = price_service.check_item(item_text)

                    if results:
                        # Take first result (usually poe_ninja)
                        best = results[0]

                        item.chaos_value = float(
                            best.get('chaos_value', 0) or 0)
                        item.divine_value = float(
                            best.get('divine_value', 0) or 0)
                        item.confidence = best.get('source', 'unknown')

                        tab_total_chaos += item.chaos_value
                        tab_total_divine += item.divine_value

                except Exception as e:
                    self.logger.warning("Failed to price item %s: %s", item, e)

            tab.total_value_chaos = tab_total_chaos
            tab.total_value_divine = tab_total_divine

            self.logger.info(
                "Tab '%s': %.1fc (%.2fd) total",
                tab.name,
                tab_total_chaos,
                tab_total_divine,
            )

        # Filter valuable items
        valuable = self.filter_valuable_items(stash_tabs, min_chaos_value)

        self.logger.info(
            "Found %d valuable items (>= %.1fc)",
            len(valuable),
            min_chaos_value)

        return valuable

    def _build_item_text(self, item: StashItem) -> str:
        """
        Build pseudo-item text for parser.

        Since we don't have full item text from API, we construct
        a minimal version for the parser.

        Args:
            item: StashItem to convert

        Returns:
            Item text string
        """
        lines: List[str] = []

        # Rarity line
        lines.append(f"Rarity: {item.rarity}")

        # Name and type
        if item.name:
            lines.append(item.name)
        if item.type_line:
            lines.append(item.type_line)

        # Separator
        lines.append("--------")

        # Item level
        lines.append(f"Item Level: {item.ilvl}")

        # Corrupted
        if item.corrupted:
            lines.append("Corrupted")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test stash scanner
    import sys
    logging.basicConfig(level=logging.INFO)

    from core.poe_oauth import PoeOAuthClient

    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"

    oauth = PoeOAuthClient(CLIENT_ID, CLIENT_SECRET)

    if not oauth.is_authenticated():
        print("Need to authenticate first...")
        if not oauth.authenticate():
            print("Authentication failed")
            sys.exit(1)

    scanner = StashScanner(oauth, league="Standard")

    # Scan all tabs
    tabs = scanner.scan_all_tabs()

    print(f"\nFound {len(tabs)} stash tabs:")
    for tab in tabs:
        print(f"  - {tab.name}: {len(tab.items)} items")
