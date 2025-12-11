"""
Background workers for stash viewer.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core.stash_valuator import PricedItem, StashValuator, ValuationResult
from data_sources.poe_stash_api import PoEStashClient

logger = logging.getLogger(__name__)


class FetchWorker(QThread):
    """Background worker for fetching and valuating stash."""

    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(object, object)  # (ValuationResult, StashSnapshot)
    error = pyqtSignal(str)
    rate_limited = pyqtSignal(int, int)  # wait_seconds, attempt

    # New signal for incremental item updates
    items_batch = pyqtSignal(str, list, int, int)  # tab_name, items, processed, total

    def __init__(
        self,
        poesessid: str,
        account_name: str,
        league: str,
        max_tabs: Optional[int] = None,
        incremental: bool = True,
        batch_size: int = 50,
    ):
        super().__init__()
        self.poesessid = poesessid
        self.account_name = account_name
        self.league = league
        self.max_tabs = max_tabs
        self.incremental = incremental
        self.batch_size = batch_size

    def run(self):
        """Fetch and valuate stash in background."""
        try:
            valuator = StashValuator()

            # Load prices
            self.progress.emit(0, 0, "Loading prices from poe.ninja...")

            def price_progress(cur, total, name):
                self.progress.emit(cur, total, f"Loading {name}...")

            valuator.load_prices(self.league, progress_callback=price_progress)

            # Connect to PoE
            self.progress.emit(0, 0, "Connecting to Path of Exile...")

            def rate_limit_callback(wait_seconds: int, attempt: int):
                """Called when rate limited - emit signal to update UI."""
                self.rate_limited.emit(wait_seconds, attempt)

            client = PoEStashClient(
                self.poesessid,
                rate_limit_callback=rate_limit_callback,
            )

            if not client.verify_session():
                self.error.emit("Invalid POESESSID - session verification failed")
                return

            # Fetch stash
            def stash_progress(cur, total):
                self.progress.emit(cur, total, f"Fetching tab {cur}/{total}...")

            snapshot = client.fetch_all_stashes(
                self.account_name,
                self.league,
                max_tabs=self.max_tabs,
                progress_callback=stash_progress,
            )

            # Valuate with incremental updates if enabled
            if self.incremental:
                result = self._valuate_incremental(valuator, snapshot)
            else:
                # Original behavior
                def val_progress(cur, total, name):
                    self.progress.emit(cur, total, f"Pricing {name}...")

                result = valuator.valuate_snapshot(snapshot, progress_callback=val_progress)

            # Emit both result and snapshot for storage
            self.finished.emit(result, snapshot)

        except Exception as e:
            logger.exception("Stash fetch failed")
            self.error.emit(str(e))

    def _valuate_incremental(self, valuator: StashValuator, snapshot) -> ValuationResult:
        """Valuate snapshot with incremental batch updates."""
        from core.stash_valuator import PriceSource

        result = ValuationResult(
            league=snapshot.league,
            account_name=snapshot.account_name,
        )

        total_tabs = len(snapshot.tabs)

        for i, tab in enumerate(snapshot.tabs):
            self.progress.emit(i + 1, total_tabs, f"Pricing {tab.name}...")

            # Create batch callback for this tab
            def on_batch(items: List[PricedItem], processed: int, total: int, tab_name=tab.name):
                self.items_batch.emit(tab_name, items, processed, total)

            # Use incremental valuation if tab has many items
            if len(tab.items) > self.batch_size:
                priced_tab = valuator.valuate_tab_incremental(
                    tab,
                    batch_size=self.batch_size,
                    on_batch=on_batch,
                )
            else:
                # Small tab - use regular method
                priced_tab = valuator.valuate_tab(tab)

            result.tabs.append(priced_tab)
            result.total_value += priced_tab.total_value
            result.total_items += len(priced_tab.items)
            result.priced_items += sum(
                1 for item in priced_tab.items if item.price_source != PriceSource.UNKNOWN
            )
            result.unpriced_items += sum(
                1 for item in priced_tab.items if item.price_source == PriceSource.UNKNOWN
            )

            # Handle children (nested tabs)
            for child in tab.children:
                child_priced = valuator.valuate_tab(child)
                result.tabs.append(child_priced)
                result.total_value += child_priced.total_value
                result.total_items += len(child_priced.items)

        # Sort tabs by value
        result.tabs.sort(key=lambda x: x.total_value, reverse=True)

        logger.info(
            f"Valuated {result.total_items} items across {len(result.tabs)} tabs. "
            f"Total: {result.display_total}"
        )

        return result
