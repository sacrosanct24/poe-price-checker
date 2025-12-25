"""Orchestrator for ML collection loop."""

from __future__ import annotations

import logging
import signal
import threading
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.database import Database
from data_sources.mod_database import ModDatabase
from ml.collection.lifecycle_tracker import ListingLifecycleTracker
from ml.collection.polling_service import CurrencyConverter, MLPollingService, MLRunStats

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from data_sources.pricing.trade_api import PoeTradeClient


class MLCollectionOrchestrator:
    """
    Main entry point for collection system.

    Methods:
    - start(): Begin collection loop
    - stop(): Graceful shutdown
    - run_once(): Single collection cycle (for testing)
    - get_status(): Current state and stats
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        db: Optional[Database] = None,
        mod_database: Optional[ModDatabase] = None,
        trade_client: Optional["PoeTradeClient"] = None,
        price_converter: Optional[CurrencyConverter] = None,
        logger_override: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger_override or logger
        self.polling_service = MLPollingService(
            config,
            db=db,
            mod_database=mod_database,
            trade_client=trade_client,
            price_converter=price_converter,
            logger_override=self.logger,
        )
        self.lifecycle_tracker = ListingLifecycleTracker(
            self.polling_service.db,
            league=self.polling_service.league,
            game_id=self.polling_service.game_id,
            logger_override=self.logger,
        )

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[Dict[str, Any]] = None
        self._signal_handlers_installed = False

    def start(self) -> None:
        if not self.polling_service.enabled:
            self.logger.info("ML collection disabled; start() ignored")
            return
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._install_signal_handlers()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)

    def run_once(self) -> MLRunStats:
        stats, seen_ids = self.polling_service.poll_once()
        lifecycle_stats = self.lifecycle_tracker.update_listing_states(seen_ids)
        self._last_run = {
            "run_id": stats.run_id,
            "started_at": stats.started_at,
            "completed_at": stats.completed_at,
            "listings_fetched": stats.listings_fetched,
            "listings_new": stats.listings_new,
            "listings_updated": stats.listings_updated,
            "errors": stats.errors,
            "lifecycle_visible": lifecycle_stats.updated_visible,
            "lifecycle_missing": lifecycle_stats.updated_missing,
        }
        return stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "last_run": self._last_run,
            "frequency_minutes": self.polling_service.frequency_minutes,
            "enabled": self.polling_service.enabled,
        }

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                self.logger.exception("Collection cycle failed")
            self._stop_event.wait(self.polling_service.frequency_minutes * 60)

    def _install_signal_handlers(self) -> None:
        if self._signal_handlers_installed:
            return
        if threading.current_thread() is not threading.main_thread():
            return

        def _handler(signum: int, _frame: Any) -> None:
            self.logger.info("Received signal %s; shutting down", signum)
            self.stop()

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
        self._signal_handlers_installed = True
