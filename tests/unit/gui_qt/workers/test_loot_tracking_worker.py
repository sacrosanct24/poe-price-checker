"""Tests for gui_qt/workers/loot_tracking_worker.py - Loot tracking background workers."""

import pytest
from unittest.mock import MagicMock, patch

from gui_qt.workers.loot_tracking_worker import (
    StashSnapshotWorker,
    StashDiffWorker,
    LootValuationWorker,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_snapshot():
    """Create a mock stash snapshot."""
    snapshot = MagicMock()
    snapshot.tabs = [
        MagicMock(name="Currency"),
        MagicMock(name="Divination"),
    ]
    snapshot.total_items = 150
    return snapshot


@pytest.fixture
def mock_diff():
    """Create a mock stash diff."""
    diff = MagicMock()
    diff.added_items = [
        {"name": "Exalted Orb", "stack_size": 1},
        {"name": "Chaos Orb", "stack_size": 10},
    ]
    diff.removed_items = []
    diff.get_summary.return_value = "2 items added, 0 removed"
    return diff


# =============================================================================
# StashSnapshotWorker Tests
# =============================================================================


class TestStashSnapshotWorkerInit:
    """Tests for StashSnapshotWorker initialization."""

    def test_init_stores_parameters(self):
        """Should store all initialization parameters."""
        worker = StashSnapshotWorker(
            poesessid="test_session",
            account_name="TestAccount",
            league="Settlers",
            tracked_tabs=["Currency", "Maps"],
            max_tabs=30,
        )

        assert worker._poesessid == "test_session"
        assert worker._account_name == "TestAccount"
        assert worker._league == "Settlers"
        assert worker._tracked_tabs == ["Currency", "Maps"]
        assert worker._max_tabs == 30

    def test_init_default_max_tabs(self):
        """Should use default max_tabs of 50."""
        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )

        assert worker._max_tabs == 50

    def test_init_tracked_tabs_optional(self):
        """Should allow None for tracked_tabs."""
        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )

        assert worker._tracked_tabs is None


class TestStashSnapshotWorkerExecute:
    """Tests for StashSnapshotWorker._execute()."""

    @patch('data_sources.poe_stash_api.PoEStashClient')
    def test_execute_creates_client_with_poesessid(self, mock_client_cls):
        """Should create PoEStashClient with correct session."""
        mock_client = MagicMock()
        mock_client.verify_session.return_value = True
        mock_snapshot = MagicMock()
        mock_snapshot.tabs = []
        mock_snapshot.total_items = 0
        mock_client.fetch_all_stashes.return_value = mock_snapshot
        mock_client_cls.return_value = mock_client

        worker = StashSnapshotWorker(
            poesessid="my_session",
            account_name="Account",
            league="League",
        )

        worker._execute()

        mock_client_cls.assert_called_once()
        call_args = mock_client_cls.call_args
        assert call_args[0][0] == "my_session"

    @patch('data_sources.poe_stash_api.PoEStashClient')
    def test_execute_verifies_session(self, mock_client_cls):
        """Should verify session before fetching."""
        mock_client = MagicMock()
        mock_client.verify_session.return_value = True
        mock_snapshot = MagicMock()
        mock_snapshot.tabs = []
        mock_snapshot.total_items = 0
        mock_client.fetch_all_stashes.return_value = mock_snapshot
        mock_client_cls.return_value = mock_client

        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )

        worker._execute()

        mock_client.verify_session.assert_called_once()

    @patch('data_sources.poe_stash_api.PoEStashClient')
    def test_execute_raises_on_invalid_session(self, mock_client_cls):
        """Should raise ValueError on invalid session."""
        mock_client = MagicMock()
        mock_client.verify_session.return_value = False
        mock_client_cls.return_value = mock_client

        worker = StashSnapshotWorker(
            poesessid="bad_session",
            account_name="Test",
            league="Test",
        )

        with pytest.raises(ValueError, match="Invalid POESESSID"):
            worker._execute()

    @patch('data_sources.poe_stash_api.PoEStashClient')
    def test_execute_fetches_stashes(self, mock_client_cls):
        """Should fetch stashes with correct parameters."""
        mock_client = MagicMock()
        mock_client.verify_session.return_value = True
        mock_snapshot = MagicMock()
        mock_snapshot.tabs = []
        mock_snapshot.total_items = 0
        mock_client.fetch_all_stashes.return_value = mock_snapshot
        mock_client_cls.return_value = mock_client

        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="MyAccount",
            league="Settlers",
            max_tabs=25,
        )

        worker._execute()

        mock_client.fetch_all_stashes.assert_called_once()
        call_kwargs = mock_client.fetch_all_stashes.call_args[1]
        assert call_kwargs["account_name"] == "MyAccount"
        assert call_kwargs["league"] == "Settlers"
        assert call_kwargs["max_tabs"] == 25

    @patch('data_sources.poe_stash_api.PoEStashClient')
    def test_execute_returns_snapshot(self, mock_client_cls, mock_snapshot):
        """Should return snapshot from client."""
        mock_client = MagicMock()
        mock_client.verify_session.return_value = True
        mock_client.fetch_all_stashes.return_value = mock_snapshot
        mock_client_cls.return_value = mock_client

        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )

        result = worker._execute()

        assert result is mock_snapshot

    @patch('data_sources.poe_stash_api.PoEStashClient')
    def test_execute_emits_status_updates(self, mock_client_cls, mock_snapshot):
        """Should emit status updates during execution."""
        mock_client = MagicMock()
        mock_client.verify_session.return_value = True
        mock_client.fetch_all_stashes.return_value = mock_snapshot
        mock_client_cls.return_value = mock_client

        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )

        status_updates = []
        worker.status.connect(lambda msg: status_updates.append(msg))

        worker._execute()

        # Should have at least connecting and final status
        assert len(status_updates) >= 2
        assert any("Connecting" in s for s in status_updates)

    @patch('data_sources.poe_stash_api.PoEStashClient')
    def test_execute_checks_cancellation(self, mock_client_cls):
        """Should check cancellation and raise if cancelled."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )
        worker._cancelled = True

        with pytest.raises(InterruptedError, match="cancelled"):
            worker._execute()


# =============================================================================
# StashDiffWorker Tests
# =============================================================================


class TestStashDiffWorkerInit:
    """Tests for StashDiffWorker initialization."""

    def test_init_stores_snapshots(self, mock_snapshot):
        """Should store before and after snapshots."""
        before = MagicMock()
        after = mock_snapshot

        worker = StashDiffWorker(
            before_snapshot=before,
            after_snapshot=after,
        )

        assert worker._before_snapshot is before
        assert worker._after_snapshot is after

    def test_init_stores_tracked_tabs(self, mock_snapshot):
        """Should store tracked tabs."""
        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=mock_snapshot,
            tracked_tabs=["Currency", "Maps"],
        )

        assert worker._tracked_tabs == ["Currency", "Maps"]


class TestStashDiffWorkerExecute:
    """Tests for StashDiffWorker._execute()."""

    @patch('core.stash_diff_engine.StashDiffEngine')
    def test_execute_creates_engine(self, mock_engine_cls, mock_snapshot, mock_diff):
        """Should create StashDiffEngine."""
        mock_engine = MagicMock()
        mock_engine.compute_diff.return_value = mock_diff
        mock_engine_cls.return_value = mock_engine

        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=mock_snapshot,
            tracked_tabs=["Currency"],
        )

        worker._execute()

        mock_engine_cls.assert_called_once_with(tracked_tabs=["Currency"])

    @patch('core.stash_diff_engine.StashDiffEngine')
    def test_execute_sets_before_snapshot(self, mock_engine_cls, mock_snapshot, mock_diff):
        """Should set before snapshot on engine."""
        mock_engine = MagicMock()
        mock_engine.compute_diff.return_value = mock_diff
        mock_engine_cls.return_value = mock_engine

        before = MagicMock()
        worker = StashDiffWorker(
            before_snapshot=before,
            after_snapshot=mock_snapshot,
        )

        worker._execute()

        mock_engine.set_before_snapshot.assert_called_once_with(before)

    @patch('core.stash_diff_engine.StashDiffEngine')
    def test_execute_computes_diff(self, mock_engine_cls, mock_snapshot, mock_diff):
        """Should compute diff with after snapshot."""
        mock_engine = MagicMock()
        mock_engine.compute_diff.return_value = mock_diff
        mock_engine_cls.return_value = mock_engine

        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=mock_snapshot,
        )

        worker._execute()

        mock_engine.compute_diff.assert_called_once_with(mock_snapshot)

    @patch('core.stash_diff_engine.StashDiffEngine')
    def test_execute_returns_diff(self, mock_engine_cls, mock_snapshot, mock_diff):
        """Should return diff result."""
        mock_engine = MagicMock()
        mock_engine.compute_diff.return_value = mock_diff
        mock_engine_cls.return_value = mock_engine

        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=mock_snapshot,
        )

        result = worker._execute()

        assert result is mock_diff

    @patch('core.stash_diff_engine.StashDiffEngine')
    def test_execute_emits_status(self, mock_engine_cls, mock_snapshot, mock_diff):
        """Should emit status updates."""
        mock_engine = MagicMock()
        mock_engine.compute_diff.return_value = mock_diff
        mock_engine_cls.return_value = mock_engine

        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=mock_snapshot,
        )

        status_updates = []
        worker.status.connect(lambda msg: status_updates.append(msg))

        worker._execute()

        assert len(status_updates) >= 1
        assert any("diff" in s.lower() for s in status_updates)

    @patch('core.stash_diff_engine.StashDiffEngine')
    def test_execute_checks_cancellation(self, mock_engine_cls, mock_snapshot):
        """Should raise if cancelled."""
        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=mock_snapshot,
        )
        worker._cancelled = True

        with pytest.raises(InterruptedError, match="cancelled"):
            worker._execute()


# =============================================================================
# LootValuationWorker Tests
# =============================================================================


@pytest.fixture
def mock_price_service():
    """Create a mock price service for testing."""
    service = MagicMock()
    service.check_item.return_value = [{"chaos_value": 100.0}]
    return service


class TestLootValuationWorkerInit:
    """Tests for LootValuationWorker initialization."""

    def test_init_stores_items(self, mock_price_service):
        """Should store items list."""
        items = [{"name": "Item1"}, {"name": "Item2"}]

        worker = LootValuationWorker(
            items=items,
            league="Test",
            price_service=mock_price_service,
        )

        assert worker._items == items

    def test_init_stores_league(self, mock_price_service):
        """Should store league."""
        worker = LootValuationWorker(
            items=[],
            league="Settlers",
            price_service=mock_price_service,
        )

        assert worker._league == "Settlers"

    def test_init_stores_price_service(self, mock_price_service):
        """Should store price service."""
        worker = LootValuationWorker(
            items=[],
            league="Test",
            price_service=mock_price_service,
        )

        assert worker._price_service is mock_price_service

    def test_init_requires_price_service(self):
        """Should raise ValueError when price_service is None."""
        with pytest.raises(ValueError, match="requires a price_service"):
            LootValuationWorker(
                items=[],
                league="Test",
                price_service=None,
            )


class TestLootValuationWorkerExecute:
    """Tests for LootValuationWorker._execute()."""

    def test_execute_returns_priced_items(self, mock_price_service):
        """Should return items with price fields added."""
        items = [
            {"typeLine": "Exalted Orb", "stackSize": 1, "frameType": 5},
            {"typeLine": "Chaos Orb", "stackSize": 10, "frameType": 5},
        ]

        worker = LootValuationWorker(items=items, league="Test", price_service=mock_price_service)
        result = worker._execute()

        assert len(result) == 2
        for item in result:
            assert "chaos_value" in item
            assert "divine_value" in item

    def test_execute_preserves_original_item_data(self, mock_price_service):
        """Should preserve original item fields."""
        items = [
            {"typeLine": "Test Item", "stackSize": 5, "frameType": 2},
        ]

        worker = LootValuationWorker(items=items, league="Test", price_service=mock_price_service)
        result = worker._execute()

        assert result[0]["typeLine"] == "Test Item"
        assert result[0]["stackSize"] == 5
        assert result[0]["frameType"] == 2

    def test_execute_does_not_modify_original(self, mock_price_service):
        """Should not modify original items list."""
        items = [{"typeLine": "Test", "frameType": 0}]
        original_item = items[0].copy()

        worker = LootValuationWorker(items=items, league="Test", price_service=mock_price_service)
        worker._execute()

        assert items[0] == original_item
        assert "chaos_value" not in items[0]

    def test_execute_emits_status_updates(self, mock_price_service):
        """Should emit status during pricing."""
        items = [{"typeLine": f"Item{i}", "frameType": 0} for i in range(15)]

        worker = LootValuationWorker(items=items, league="Test", price_service=mock_price_service)

        status_updates = []
        worker.status.connect(lambda msg: status_updates.append(msg))

        worker._execute()

        # Should have status updates for batch progress
        assert len(status_updates) >= 2

    def test_execute_checks_cancellation(self, mock_price_service):
        """Should check cancellation during iteration."""
        items = [{"typeLine": f"Item{i}", "frameType": 0} for i in range(100)]

        worker = LootValuationWorker(items=items, league="Test", price_service=mock_price_service)
        worker._cancelled = True

        with pytest.raises(InterruptedError, match="cancelled"):
            worker._execute()

    def test_execute_empty_items(self, mock_price_service):
        """Should handle empty items list."""
        worker = LootValuationWorker(items=[], league="Test", price_service=mock_price_service)
        result = worker._execute()

        assert result == []


class TestLootValuationWorkerLookupPrice:
    """Tests for LootValuationWorker._lookup_price()."""

    def test_lookup_price_returns_float(self, mock_price_service):
        """Should return a float value."""
        worker = LootValuationWorker(items=[], league="Test", price_service=mock_price_service)
        result = worker._lookup_price({"typeLine": "Exalted Orb", "frameType": 5})

        assert isinstance(result, float)

    def test_lookup_price_uses_price_service(self, mock_price_service):
        """Should use price service to get value."""
        mock_price_service.check_item.return_value = [{"chaos_value": 150.0}]
        worker = LootValuationWorker(items=[], league="Test", price_service=mock_price_service)
        result = worker._lookup_price({"typeLine": "Exalted Orb", "frameType": 5})

        assert result == 150.0
        mock_price_service.check_item.assert_called_once()

    def test_lookup_price_returns_zero_on_no_results(self, mock_price_service):
        """Should return 0.0 when price service returns empty results."""
        mock_price_service.check_item.return_value = []
        worker = LootValuationWorker(items=[], league="Test", price_service=mock_price_service)
        result = worker._lookup_price({"typeLine": "Unknown Item", "frameType": 0})

        assert result == 0.0

    def test_lookup_price_returns_zero_on_exception(self, mock_price_service):
        """Should return 0.0 on price service exception."""
        mock_price_service.check_item.side_effect = Exception("API error")
        worker = LootValuationWorker(items=[], league="Test", price_service=mock_price_service)
        result = worker._lookup_price({"typeLine": "Test", "frameType": 0})

        assert result == 0.0


# =============================================================================
# Integration-Style Tests
# =============================================================================


class TestWorkerSignals:
    """Tests for worker signal behavior."""

    def test_snapshot_worker_has_required_signals(self):
        """Should have result, error, and status signals."""
        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )

        assert hasattr(worker, 'result')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'status')

    def test_diff_worker_has_required_signals(self):
        """Should have result, error, and status signals."""
        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=MagicMock(),
        )

        assert hasattr(worker, 'result')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'status')

    def test_valuation_worker_has_required_signals(self, mock_price_service):
        """Should have result, error, and status signals."""
        worker = LootValuationWorker(items=[], league="Test", price_service=mock_price_service)

        assert hasattr(worker, 'result')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'status')


class TestWorkerCancellation:
    """Tests for worker cancellation behavior."""

    def test_snapshot_worker_cancel(self):
        """Should set cancelled flag."""
        worker = StashSnapshotWorker(
            poesessid="test",
            account_name="Test",
            league="Test",
        )

        worker.cancel()

        assert worker.is_cancelled

    def test_diff_worker_cancel(self):
        """Should set cancelled flag."""
        worker = StashDiffWorker(
            before_snapshot=MagicMock(),
            after_snapshot=MagicMock(),
        )

        worker.cancel()

        assert worker.is_cancelled

    def test_valuation_worker_cancel(self, mock_price_service):
        """Should set cancelled flag."""
        worker = LootValuationWorker(items=[], league="Test", price_service=mock_price_service)

        worker.cancel()

        assert worker.is_cancelled
