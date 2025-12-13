"""
Background workers for loot tracking operations.

Handles stash fetching and diff computation in background threads
to avoid blocking the UI during API calls.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from gui_qt.workers.base_worker import BaseThreadWorker

if TYPE_CHECKING:
    from data_sources.poe_stash_api import StashSnapshot
    from core.stash_diff_engine import StashDiff

logger = logging.getLogger(__name__)


class StashSnapshotWorker(BaseThreadWorker):
    """
    Worker that fetches a stash snapshot in the background.

    Signals:
        result(StashSnapshot): Emitted with snapshot on success.
        error(str, str): Emitted with (message, traceback) on failure.
        status(str): Emitted with progress updates.

    Usage:
        worker = StashSnapshotWorker(
            poesessid="...",
            account_name="TestAccount",
            league="Settlers",
        )
        worker.result.connect(self._on_snapshot_ready)
        worker.error.connect(self._on_snapshot_error)
        worker.start()
    """

    def __init__(
        self,
        poesessid: str,
        account_name: str,
        league: str,
        tracked_tabs: Optional[List[str]] = None,
        max_tabs: int = 50,
        parent: Optional[Any] = None,
    ):
        """
        Initialize the snapshot worker.

        Args:
            poesessid: Session cookie for PoE API.
            account_name: PoE account name.
            league: League to fetch stash from.
            tracked_tabs: Optional list of tab names to fetch.
            max_tabs: Maximum tabs to fetch (default 50).
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._poesessid = poesessid
        self._account_name = account_name
        self._league = league
        self._tracked_tabs = tracked_tabs
        self._max_tabs = max_tabs

    def _execute(self) -> "StashSnapshot":
        """
        Fetch stash snapshot.

        Returns:
            StashSnapshot with all tab data.

        Raises:
            ValueError: If session is invalid or API fails.
        """
        from data_sources.poe_stash_api import PoEStashClient

        self.emit_status("Connecting to PoE API...")

        if self.is_cancelled:
            raise InterruptedError("Snapshot cancelled")

        # Create client with rate limit callback
        def rate_limit_callback(wait_seconds: int, attempt: int):
            self.emit_status(f"Rate limited, waiting {wait_seconds}s (attempt {attempt})...")

        client = PoEStashClient(
            self._poesessid,
            rate_limit_callback=rate_limit_callback,
        )

        # Verify session
        if not client.verify_session():
            raise ValueError("Invalid POESESSID - session verification failed")

        if self.is_cancelled:
            raise InterruptedError("Snapshot cancelled")

        # Progress callback
        def progress_callback(current: int, total: int):
            self.emit_status(f"Fetching tab {current}/{total}...")
            # Check cancellation during fetch
            if self.is_cancelled:
                raise InterruptedError("Snapshot cancelled")

        # Fetch stash
        self.emit_status("Fetching stash tabs...")
        snapshot = client.fetch_all_stashes(
            account_name=self._account_name,
            league=self._league,
            max_tabs=self._max_tabs,
            progress_callback=progress_callback,
        )

        self.emit_status(f"Fetched {snapshot.total_items} items from {len(snapshot.tabs)} tabs")
        return snapshot


class StashDiffWorker(BaseThreadWorker):
    """
    Worker that computes the diff between two stash snapshots.

    Signals:
        result(StashDiff): Emitted with diff result on success.
        error(str, str): Emitted with (message, traceback) on failure.
        status(str): Emitted with progress updates.

    Usage:
        worker = StashDiffWorker(
            before_snapshot=before,
            after_snapshot=after,
        )
        worker.result.connect(self._on_diff_ready)
        worker.start()
    """

    def __init__(
        self,
        before_snapshot: "StashSnapshot",
        after_snapshot: "StashSnapshot",
        tracked_tabs: Optional[List[str]] = None,
        parent: Optional[Any] = None,
    ):
        """
        Initialize the diff worker.

        Args:
            before_snapshot: Stash state before map run.
            after_snapshot: Stash state after map run.
            tracked_tabs: Optional list of tab names to compare.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._before_snapshot = before_snapshot
        self._after_snapshot = after_snapshot
        self._tracked_tabs = tracked_tabs

    def _execute(self) -> "StashDiff":
        """
        Compute stash diff.

        Returns:
            StashDiff with added/removed/changed items.
        """
        from core.stash_diff_engine import StashDiffEngine

        self.emit_status("Computing stash diff...")

        if self.is_cancelled:
            raise InterruptedError("Diff cancelled")

        engine = StashDiffEngine(tracked_tabs=self._tracked_tabs)
        engine.set_before_snapshot(self._before_snapshot)

        if self.is_cancelled:
            raise InterruptedError("Diff cancelled")

        diff = engine.compute_diff(self._after_snapshot)

        self.emit_status(f"Diff complete: {diff.get_summary()}")
        return diff


class LootValuationWorker(BaseThreadWorker):
    """
    Worker that prices a list of items in the background.

    Uses the price service to value items found in stash diff.
    Requires a price_service to function - will raise an error if not provided.

    Signals:
        result(List[Dict]): Emitted with priced items on success.
        error(str, str): Emitted on failure.
        status(str): Emitted with progress updates.
    """

    def __init__(
        self,
        items: List[Dict[str, Any]],
        league: str,
        price_service: Optional[Any] = None,
        divine_ratio: float = 180.0,
        parent: Optional[Any] = None,
    ):
        """
        Initialize the valuation worker.

        Args:
            items: List of items to price (from StashDiff.added_items).
            league: League for pricing lookup.
            price_service: Price service for item valuation (required).
            divine_ratio: Chaos per divine for conversion (default 180).
            parent: Optional parent QObject.

        Raises:
            ValueError: If price_service is not provided.
        """
        super().__init__(parent)
        if price_service is None:
            raise ValueError(
                "LootValuationWorker requires a price_service. "
                "Loot tracking valuation is disabled without a configured price service."
            )
        self._items = items
        self._league = league
        self._price_service = price_service
        self._divine_ratio = divine_ratio

    def _execute(self) -> List[Dict[str, Any]]:
        """
        Price all items.

        Returns:
            List of items with chaos_value and divine_value added.
        """
        self.emit_status(f"Pricing {len(self._items)} items...")

        priced_items = []
        total_chaos = 0.0

        for i, item in enumerate(self._items):
            if self.is_cancelled:
                raise InterruptedError("Valuation cancelled")

            if i % 10 == 0:
                self.emit_status(f"Pricing item {i + 1}/{len(self._items)}...")

            priced_item = item.copy()
            chaos_value = self._lookup_price(item)
            priced_item["chaos_value"] = chaos_value
            priced_item["divine_value"] = chaos_value / self._divine_ratio if self._divine_ratio > 0 else 0.0
            priced_item["priced"] = chaos_value > 0
            priced_items.append(priced_item)
            total_chaos += chaos_value

        priced_count = sum(1 for p in priced_items if p.get("priced", False))
        self.emit_status(
            f"Priced {priced_count}/{len(priced_items)} items, "
            f"total value: {total_chaos:.0f}c"
        )
        return priced_items

    def _lookup_price(self, item: Dict[str, Any]) -> float:
        """
        Look up price for an item using the price service.

        Args:
            item: Raw item data from stash API.

        Returns:
            Chaos value estimate, or 0.0 if not found.
        """
        try:
            # Convert stash item to text format for price lookup
            item_text = self._item_to_text(item)
            if not item_text:
                return 0.0

            # Use price service to check item
            results = self._price_service.check_item(item_text)
            if results:
                # Return the first result's chaos value
                return float(results[0].get("chaos_value", 0.0))
            return 0.0
        except Exception as e:
            logger.debug(f"Price lookup failed for {item.get('typeLine', 'unknown')}: {e}")
            return 0.0

    def _item_to_text(self, item: Dict[str, Any]) -> str:
        """
        Convert a stash API item to text format for price lookup.

        Args:
            item: Raw item data from stash API.

        Returns:
            Item text in clipboard format, or empty string if conversion fails.
        """
        lines = []

        # Rarity mapping (frameType in API)
        rarity_map = {0: "Normal", 1: "Magic", 2: "Rare", 3: "Unique", 4: "Gem", 5: "Currency"}
        frame_type = item.get("frameType", 0)
        rarity = rarity_map.get(frame_type, "Normal")
        lines.append(f"Rarity: {rarity}")

        # Item name and base type
        name = item.get("name", "")
        base_type = item.get("typeLine", "")
        if name:
            lines.append(name)
        if base_type:
            lines.append(base_type)

        # Item level
        ilvl = item.get("ilvl")
        if ilvl:
            lines.append(f"Item Level: {ilvl}")

        # Stack size for currency/stackables
        stack_size = item.get("stackSize", 1)
        if stack_size > 1:
            lines.append(f"Stack Size: {stack_size}")

        # Sockets
        sockets = item.get("sockets", [])
        if sockets:
            groups = {}
            for s in sockets:
                g = s.get("group", 0)
                c = s.get("sColour", "R")
                groups.setdefault(g, []).append(c)
            socket_str = " ".join("-".join(g) for g in groups.values())
            lines.append(f"Sockets: {socket_str}")

        # Implicit mods
        for mod in item.get("implicitMods", []):
            lines.append(mod)

        # Explicit mods
        for mod in item.get("explicitMods", []):
            lines.append(mod)

        # Crafted mods
        for mod in item.get("craftedMods", []):
            lines.append(f"{mod} (crafted)")

        return "\n".join(lines)
