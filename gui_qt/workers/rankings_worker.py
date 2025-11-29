"""
Rankings population worker for background cache updates.
"""

from typing import Optional
import logging

from gui_qt.workers.base_worker import BaseThreadWorker

logger = logging.getLogger(__name__)


class RankingsPopulationWorker(BaseThreadWorker):
    """
    Background worker to populate price rankings on startup.

    Checks if the rankings cache is valid and populates it if needed.
    Emits status updates during the process.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._league: Optional[str] = None

    @property
    def league(self) -> Optional[str]:
        """Get the detected league after execution."""
        return self._league

    def _execute(self) -> int:
        """
        Check and populate rankings if needed.

        Returns:
            Number of categories populated (0 if cache was valid)
        """
        from core.price_rankings import (
            PriceRankingCache,
            Top20Calculator,
            PriceRankingHistory,
        )
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        self.emit_status("Checking price rankings cache...")

        # Detect current league
        api = PoeNinjaAPI()
        league = api.detect_current_league()
        self._league = league

        if self.is_cancelled:
            return 0

        # Check if cache is valid
        cache = PriceRankingCache(league=league)

        if cache.is_cache_valid():
            age = cache.get_cache_age_days()
            self.emit_status(f"Rankings cache valid ({age:.1f} days old)")
            return 0

        if self.is_cancelled:
            return 0

        # Need to populate
        self.emit_status(f"Fetching Top 20 rankings for {league}...")

        calculator = Top20Calculator(cache, poe_ninja_api=api)
        rankings = calculator.refresh_all(force=False)

        if self.is_cancelled:
            return len(rankings)

        # Save to history database
        self.emit_status("Saving rankings to database...")
        history = PriceRankingHistory()
        history.save_all_snapshots(rankings, league)
        history.close()

        self.emit_status(f"Populated {len(rankings)} categories")
        return len(rankings)
