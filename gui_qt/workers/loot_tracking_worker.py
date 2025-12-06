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

    Uses poe.ninja price data to value items found in stash diff.

    Signals:
        result(List[Dict]): Emitted with priced items on success.
        error(str, str): Emitted on failure.
        status(str): Emitted with progress updates.
    """

    def __init__(
        self,
        items: List[Dict[str, Any]],
        league: str,
        ninja_api: Optional[Any] = None,
        parent: Optional[Any] = None,
    ):
        """
        Initialize the valuation worker.

        Args:
            items: List of items to price (from StashDiff.added_items).
            league: League for pricing lookup.
            ninja_api: Optional poe.ninja API client.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._items = items
        self._league = league
        self._ninja_api = ninja_api

    def _execute(self) -> List[Dict[str, Any]]:
        """
        Price all items.

        Returns:
            List of items with chaos_value and divine_value added.
        """
        self.emit_status(f"Pricing {len(self._items)} items...")

        priced_items = []
        for i, item in enumerate(self._items):
            if self.is_cancelled:
                raise InterruptedError("Valuation cancelled")

            if i % 10 == 0:
                self.emit_status(f"Pricing item {i + 1}/{len(self._items)}...")

            # Add pricing (TODO: integrate with actual price service)
            priced_item = item.copy()
            priced_item["chaos_value"] = self._lookup_price(item)
            priced_item["divine_value"] = 0.0  # TODO: divine conversion
            priced_items.append(priced_item)

        self.emit_status(f"Priced {len(priced_items)} items")
        return priced_items

    def _lookup_price(self, item: Dict[str, Any]) -> float:
        """
        Look up price for an item.

        Args:
            item: Raw item data.

        Returns:
            Chaos value estimate.
        """
        # TODO: Implement actual price lookup
        # For now, return 0 - will be integrated with price service
        return 0.0
