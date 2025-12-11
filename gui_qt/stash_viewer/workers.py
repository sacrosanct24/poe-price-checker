"""
Background workers for stash viewer.
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core.stash_valuator import StashValuator
from data_sources.poe_stash_api import PoEStashClient

logger = logging.getLogger(__name__)


class FetchWorker(QThread):
    """Background worker for fetching and valuating stash."""

    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(object, object)  # (ValuationResult, StashSnapshot)
    error = pyqtSignal(str)
    rate_limited = pyqtSignal(int, int)  # wait_seconds, attempt

    def __init__(
        self,
        poesessid: str,
        account_name: str,
        league: str,
        max_tabs: Optional[int] = None,
    ):
        super().__init__()
        self.poesessid = poesessid
        self.account_name = account_name
        self.league = league
        self.max_tabs = max_tabs

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

            # Valuate
            def val_progress(cur, total, name):
                self.progress.emit(cur, total, f"Pricing {name}...")

            result = valuator.valuate_snapshot(snapshot, progress_callback=val_progress)

            # Emit both result and snapshot for storage
            self.finished.emit(result, snapshot)

        except Exception as e:
            logger.exception("Stash fetch failed")
            self.error.emit(str(e))
