"""Tests for RankingsPopulationWorker."""

import pytest
from unittest.mock import MagicMock, patch

from gui_qt.workers.rankings_worker import RankingsPopulationWorker

# Patch paths - imports are lazy (inside _execute), so patch at source
PATCH_POE_NINJA_API = "data_sources.pricing.poe_ninja.PoeNinjaAPI"
PATCH_PRICE_RANKING_CACHE = "core.price_rankings.PriceRankingCache"
PATCH_TOP20_CALCULATOR = "core.price_rankings.Top20Calculator"
PATCH_PRICE_RANKING_HISTORY = "core.price_rankings.PriceRankingHistory"


@pytest.fixture
def worker():
    """Create RankingsPopulationWorker instance."""
    return RankingsPopulationWorker()


@pytest.fixture
def mock_poe_ninja_api():
    """Create mock PoeNinjaAPI."""
    api = MagicMock()
    api.detect_current_league.return_value = "Affliction"
    return api


@pytest.fixture
def mock_cache():
    """Create mock PriceRankingCache."""
    cache = MagicMock()
    cache.is_cache_valid.return_value = False
    cache.get_cache_age_days.return_value = 1.5
    return cache


@pytest.fixture
def mock_calculator():
    """Create mock Top20Calculator."""
    calculator = MagicMock()
    calculator.refresh_all.return_value = {
        "currency": MagicMock(),
        "fragments": MagicMock(),
        "divination_cards": MagicMock(),
    }
    return calculator


@pytest.fixture
def mock_history():
    """Create mock PriceRankingHistory."""
    history = MagicMock()
    return history


class TestRankingsWorkerInitialization:
    """Tests for RankingsPopulationWorker initialization."""

    def test_init_with_no_parent(self):
        """Worker can be initialized without parent."""
        worker = RankingsPopulationWorker()

        assert worker is not None
        assert worker._league is None
        assert not worker.is_cancelled

    def test_init_with_parent(self):
        """Worker can be initialized with parent."""
        from PyQt6.QtCore import QObject

        parent = QObject()
        worker = RankingsPopulationWorker(parent)

        assert worker.parent() is parent

    def test_inherits_base_thread_worker(self):
        """RankingsPopulationWorker inherits from BaseThreadWorker."""
        from gui_qt.workers.base_worker import BaseThreadWorker

        worker = RankingsPopulationWorker()
        assert isinstance(worker, BaseThreadWorker)


class TestRankingsWorkerLeagueProperty:
    """Tests for league property."""

    def test_league_initially_none(self, worker):
        """League is None before execution."""
        assert worker.league is None
        assert worker._league is None

    def test_league_getter(self, worker):
        """League getter returns internal value."""
        worker._league = "Crucible"
        assert worker.league == "Crucible"


class TestRankingsWorkerExecution:
    """Tests for RankingsPopulationWorker execution."""

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_execute_with_valid_cache(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Execute returns 0 when cache is valid."""
        # Set up mocks
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Affliction"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = True
        mock_cache.get_cache_age_days.return_value = 0.5
        mock_cache_class.return_value = mock_cache

        # Execute
        result = worker._execute()

        # Should return 0 without refreshing
        assert result == 0
        assert worker.league == "Affliction"
        mock_cache.is_cache_valid.assert_called_once()
        mock_calc_class.assert_not_called()

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_execute_with_invalid_cache(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Execute refreshes when cache is invalid."""
        # Set up mocks
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Affliction"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_rankings = {
            "currency": MagicMock(),
            "fragments": MagicMock(),
            "divination_cards": MagicMock(),
        }
        mock_calculator.refresh_all.return_value = mock_rankings
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        # Execute
        result = worker._execute()

        # Should refresh and return count
        assert result == 3
        assert worker.league == "Affliction"
        mock_calculator.refresh_all.assert_called_once_with(force=False)
        mock_history.save_all_snapshots.assert_called_once_with(
            mock_rankings, "Affliction"
        )
        mock_history.close.assert_called_once()

    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_execute_detects_league(self, mock_api_class, mock_cache_class, worker):
        """Execute detects current league."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Crucible"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = True
        mock_cache.get_cache_age_days.return_value = 0.5
        mock_cache_class.return_value = mock_cache

        worker._execute()

        assert worker.league == "Crucible"
        mock_api.detect_current_league.assert_called_once()


class TestRankingsWorkerSignals:
    """Tests for RankingsPopulationWorker signal emission.

    Tests call run() directly to test signal emission without starting real threads.
    This avoids segfaults in headless CI environments.
    """

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_result_signal_on_success(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker, qtbot
    ):
        """result signal emitted with count on success."""
        # Set up valid cache
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test League"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = True
        mock_cache.get_cache_age_days.return_value = 0.5
        mock_cache_class.return_value = mock_cache

        with qtbot.waitSignal(worker.result, timeout=1000) as blocker:
            worker.run()

        assert blocker.args[0] == 0

    @patch(PATCH_POE_NINJA_API)
    def test_error_signal_on_exception(self, mock_api_class, worker, qtbot):
        """error signal emitted when execution fails."""
        mock_api = MagicMock()
        mock_api.detect_current_league.side_effect = Exception("API error")
        mock_api_class.return_value = mock_api

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, traceback = blocker.args
        assert "API error" in error_msg

    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_status_signals_emitted(
        self, mock_api_class, mock_cache_class, worker, qtbot
    ):
        """status signals emitted during execution."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test League"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = True
        mock_cache.get_cache_age_days.return_value = 1.2
        mock_cache_class.return_value = mock_cache

        status_messages = []
        worker.status.connect(lambda msg: status_messages.append(msg))

        with qtbot.waitSignal(worker.result, timeout=1000):
            worker.run()

        # Should have status messages
        assert len(status_messages) > 0
        assert any("Checking" in msg for msg in status_messages)


class TestRankingsWorkerCancellation:
    """Tests for RankingsPopulationWorker cancellation."""

    @patch(PATCH_POE_NINJA_API)
    def test_cancel_before_execution(self, mock_api_class, worker):
        """Worker doesn't execute if cancelled before start."""
        worker.cancel()

        worker.run()

        # Should not detect league if cancelled
        mock_api_class.assert_not_called()

    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_cancel_after_league_detection(
        self, mock_api_class, mock_cache_class, worker
    ):
        """Worker checks cancellation after league detection."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test League"
        mock_api_class.return_value = mock_api

        # Cancel after league detection
        def cancel_after_detect():
            worker.cancel()

        mock_api.detect_current_league.side_effect = lambda: (
            cancel_after_detect() or "Test League"
        )

        result = worker._execute()

        # Should return early
        assert result == 0
        mock_cache_class.assert_not_called()

    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_cancel_after_cache_check(
        self, mock_api_class, mock_cache_class, mock_calc_class, worker
    ):
        """Worker checks cancellation after cache check."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test League"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        # Cancel after cache check
        worker._cancelled = False
        worker._execute()

        # Then cancel before refresh
        worker._cancelled = True
        mock_calculator = MagicMock()
        mock_rankings = {"currency": MagicMock()}
        mock_calculator.refresh_all.return_value = mock_rankings
        mock_calc_class.return_value = mock_calculator

        result = worker._execute()

        # Should still complete refresh but might return early after
        assert isinstance(result, int)


class TestRankingsWorkerStatusUpdates:
    """Tests for status update messages."""

    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_status_checking_cache(self, mock_api_class, mock_cache_class, worker):
        """Status message when checking cache."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = True
        mock_cache.get_cache_age_days.return_value = 0.5
        mock_cache_class.return_value = mock_cache

        status_messages = []
        worker.status.connect(lambda msg: status_messages.append(msg))

        worker._execute()

        assert any("Checking price rankings cache" in msg for msg in status_messages)

    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_status_cache_valid(self, mock_api_class, mock_cache_class, worker):
        """Status message when cache is valid."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = True
        mock_cache.get_cache_age_days.return_value = 0.8
        mock_cache_class.return_value = mock_cache

        status_messages = []
        worker.status.connect(lambda msg: status_messages.append(msg))

        worker._execute()

        assert any("valid" in msg for msg in status_messages)

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_status_fetching_rankings(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Status message when fetching rankings."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Affliction"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_calculator.refresh_all.return_value = {}
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        status_messages = []
        worker.status.connect(lambda msg: status_messages.append(msg))

        worker._execute()

        assert any("Fetching Top 20" in msg for msg in status_messages)
        assert any("Affliction" in msg for msg in status_messages)

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_status_saving_database(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Status message when saving to database."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_calculator.refresh_all.return_value = {"currency": MagicMock()}
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        status_messages = []
        worker.status.connect(lambda msg: status_messages.append(msg))

        worker._execute()

        assert any("Saving rankings to database" in msg for msg in status_messages)

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_status_populated_count(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Status message shows populated count."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_rankings = {
            "currency": MagicMock(),
            "fragments": MagicMock(),
            "divination_cards": MagicMock(),
        }
        mock_calculator.refresh_all.return_value = mock_rankings
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        status_messages = []
        worker.status.connect(lambda msg: status_messages.append(msg))

        worker._execute()

        assert any("Populated 3 categories" in msg for msg in status_messages)


class TestRankingsWorkerErrorHandling:
    """Tests for error handling.

    Tests call run() directly to test error signal emission without starting real threads.
    """

    @patch(PATCH_POE_NINJA_API)
    def test_api_exception(self, mock_api_class, worker, qtbot):
        """Handles API exception gracefully."""
        mock_api = MagicMock()
        mock_api.detect_current_league.side_effect = RuntimeError("Network error")
        mock_api_class.return_value = mock_api

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, _ = blocker.args
        assert "Network error" in error_msg

    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_cache_exception(self, mock_api_class, mock_cache_class, worker, qtbot):
        """Handles cache exception gracefully."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache_class.side_effect = IOError("Cache file error")

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, _ = blocker.args
        assert "Cache file error" in error_msg

    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_calculator_exception(
        self, mock_api_class, mock_cache_class, mock_calc_class, worker, qtbot
    ):
        """Handles calculator exception gracefully."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_calculator.refresh_all.side_effect = ValueError("Calculation failed")
        mock_calc_class.return_value = mock_calculator

        with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
            worker.run()

        error_msg, _ = blocker.args
        assert "Calculation failed" in error_msg


class TestRankingsWorkerReturnValues:
    """Tests for different return value scenarios."""

    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_returns_zero_for_valid_cache(
        self, mock_api_class, mock_cache_class, worker
    ):
        """Returns 0 when cache is valid."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = True
        mock_cache.get_cache_age_days.return_value = 0.5
        mock_cache_class.return_value = mock_cache

        result = worker._execute()

        assert result == 0

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_returns_count_for_populated(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Returns count of populated categories."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_rankings = {
            "cat1": MagicMock(),
            "cat2": MagicMock(),
            "cat3": MagicMock(),
            "cat4": MagicMock(),
            "cat5": MagicMock(),
        }
        mock_calculator.refresh_all.return_value = mock_rankings
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        result = worker._execute()

        assert result == 5

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_returns_zero_for_empty_rankings(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Returns 0 when no categories populated."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_calculator.refresh_all.return_value = {}
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        result = worker._execute()

        assert result == 0


class TestRankingsWorkerHistoryDatabase:
    """Tests for database history operations."""

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_saves_to_history_database(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Saves rankings to history database."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Affliction"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_rankings = {"currency": MagicMock()}
        mock_calculator.refresh_all.return_value = mock_rankings
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        worker._execute()

        mock_history.save_all_snapshots.assert_called_once_with(
            mock_rankings, "Affliction"
        )

    @patch(PATCH_PRICE_RANKING_HISTORY)
    @patch(PATCH_TOP20_CALCULATOR)
    @patch(PATCH_PRICE_RANKING_CACHE)
    @patch(PATCH_POE_NINJA_API)
    def test_closes_history_database(
        self, mock_api_class, mock_cache_class, mock_calc_class, mock_hist_class, worker
    ):
        """Closes history database connection."""
        mock_api = MagicMock()
        mock_api.detect_current_league.return_value = "Test"
        mock_api_class.return_value = mock_api

        mock_cache = MagicMock()
        mock_cache.is_cache_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        mock_calculator = MagicMock()
        mock_calculator.refresh_all.return_value = {}
        mock_calc_class.return_value = mock_calculator

        mock_history = MagicMock()
        mock_hist_class.return_value = mock_history

        worker._execute()

        mock_history.close.assert_called_once()
