"""Tests for stash storage service."""
import json
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from core.database import Database
from core.stash_storage import StashStorageService, StoredSnapshot, reset_stash_storage
from data_sources.poe_stash_api import StashSnapshot, StashTab
from core.stash_valuator import ValuationResult, PricedTab, PricedItem, PriceSource


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    db = Database(db_path)
    yield db

    db.close()
    db_path.unlink(missing_ok=True)
    reset_stash_storage()


@pytest.fixture
def storage(temp_db):
    """Create storage service with temp database."""
    return StashStorageService(temp_db)


@pytest.fixture
def sample_snapshot():
    """Create a sample StashSnapshot for testing."""
    tab = StashTab(
        id='tab1',
        name='Currency',
        index=0,
        type='CurrencyStash',
        items=[
            {'typeLine': 'Chaos Orb', 'stackSize': 100, 'x': 0, 'y': 0, 'frameType': 5},
            {'typeLine': 'Divine Orb', 'stackSize': 5, 'x': 1, 'y': 0, 'frameType': 5},
        ]
    )
    return StashSnapshot(
        account_name='TestAccount',
        league='Keepers',
        tabs=[tab],
        total_items=2,
        fetched_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_valuation():
    """Create a sample ValuationResult for testing."""
    items = [
        PricedItem(
            name='',
            type_line='Chaos Orb',
            base_type='Chaos Orb',
            item_class='Currency',
            stack_size=100,
            rarity='Currency',
            unit_price=1.0,
            total_price=100.0,
            price_source=PriceSource.POE_NINJA,
            tab_name='Currency',
        ),
        PricedItem(
            name='',
            type_line='Divine Orb',
            base_type='Divine Orb',
            item_class='Currency',
            stack_size=5,
            rarity='Currency',
            unit_price=200.0,
            total_price=1000.0,
            price_source=PriceSource.POE_NINJA,
            tab_name='Currency',
        ),
    ]
    tab = PricedTab(
        id='tab1',
        name='Currency',
        index=0,
        tab_type='CurrencyStash',
        total_value=1100.0,
        items=items,
    )
    return ValuationResult(
        league='Keepers',
        account_name='TestAccount',
        tabs=[tab],
        total_value=1100.0,
        total_items=2,
        priced_items=2,
    )


class TestStashStorageService:
    """Tests for StashStorageService."""

    def test_save_snapshot_returns_id(self, storage, sample_snapshot, sample_valuation):
        """Test that saving a snapshot returns a valid ID."""
        row_id = storage.save_snapshot(sample_snapshot, sample_valuation)
        assert row_id > 0

    def test_load_latest_snapshot_returns_stored_data(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test loading the latest snapshot."""
        storage.save_snapshot(sample_snapshot, sample_valuation)

        stored = storage.load_latest_snapshot('TestAccount', 'Keepers')

        assert stored is not None
        assert stored.account_name == 'TestAccount'
        assert stored.league == 'Keepers'
        assert stored.total_items == 2
        assert stored.total_chaos_value == 1100.0

    def test_load_latest_returns_none_for_unknown_account(self, storage):
        """Test that loading returns None for unknown account."""
        stored = storage.load_latest_snapshot('UnknownAccount', 'Keepers')
        assert stored is None

    def test_load_latest_returns_most_recent(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test that load_latest returns the most recent snapshot."""
        import time

        # Save first snapshot
        sample_snapshot.fetched_at = datetime.now().isoformat()
        storage.save_snapshot(sample_snapshot, sample_valuation)

        # Small delay to ensure different timestamp
        time.sleep(0.01)

        # Modify and save second snapshot with new timestamp
        sample_snapshot.fetched_at = datetime.now().isoformat()
        sample_valuation.total_value = 2000.0
        storage.save_snapshot(sample_snapshot, sample_valuation)

        # Load should get the second one
        stored = storage.load_latest_snapshot('TestAccount', 'Keepers')
        assert stored.total_chaos_value == 2000.0

    def test_reconstruct_valuation(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test reconstructing a ValuationResult from stored data."""
        storage.save_snapshot(sample_snapshot, sample_valuation)
        stored = storage.load_latest_snapshot('TestAccount', 'Keepers')

        result = storage.reconstruct_valuation(stored)

        assert result is not None
        assert result.total_value == 1100.0
        assert result.total_items == 2
        assert len(result.tabs) == 1
        assert result.tabs[0].name == 'Currency'
        assert len(result.tabs[0].items) == 2

    def test_reconstruct_snapshot(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test reconstructing a StashSnapshot from stored data."""
        storage.save_snapshot(sample_snapshot, sample_valuation)
        stored = storage.load_latest_snapshot('TestAccount', 'Keepers')

        snapshot = storage.reconstruct_snapshot(stored)

        assert snapshot is not None
        assert snapshot.account_name == 'TestAccount'
        assert snapshot.league == 'Keepers'
        assert len(snapshot.tabs) == 1
        assert snapshot.tabs[0].name == 'Currency'

    def test_get_snapshot_history(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test getting snapshot history."""
        import time

        # Save multiple snapshots with different timestamps
        for i in range(5):
            sample_snapshot.fetched_at = datetime.now().isoformat()
            sample_valuation.total_value = float(i * 100)
            storage.save_snapshot(sample_snapshot, sample_valuation)
            time.sleep(0.01)  # Ensure distinct timestamps

        history = storage.get_snapshot_history('TestAccount', 'Keepers', limit=3)

        assert len(history) == 3
        # Should be newest first
        assert history[0].total_chaos_value == 400.0
        assert history[1].total_chaos_value == 300.0
        assert history[2].total_chaos_value == 200.0

    def test_delete_old_snapshots_keeps_recent(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test that delete_old_snapshots keeps the specified count."""
        import time

        # Save 10 snapshots with different timestamps
        for i in range(10):
            sample_snapshot.fetched_at = datetime.now().isoformat()
            sample_valuation.total_value = float(i * 100)
            storage.save_snapshot(sample_snapshot, sample_valuation)
            time.sleep(0.005)  # Small delay for distinct timestamps

        # Delete old, keep 3
        deleted = storage.delete_old_snapshots('TestAccount', 'Keepers', keep_count=3)

        assert deleted == 7

        # Verify only 3 remain
        history = storage.get_snapshot_history('TestAccount', 'Keepers', limit=10)
        assert len(history) == 3

    def test_stored_snapshot_display_total(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test StoredSnapshot.display_total property."""
        storage.save_snapshot(sample_snapshot, sample_valuation)
        stored = storage.load_latest_snapshot('TestAccount', 'Keepers')

        assert stored.display_total == '1,100c'

    def test_different_leagues_isolated(
        self, storage, sample_snapshot, sample_valuation
    ):
        """Test that different leagues have isolated data."""
        # Save to Keepers
        storage.save_snapshot(sample_snapshot, sample_valuation)

        # Modify for Standard
        sample_snapshot.league = 'Standard'
        sample_valuation.league = 'Standard'
        sample_valuation.total_value = 500.0
        storage.save_snapshot(sample_snapshot, sample_valuation)

        # Load Keepers - should get original
        keepers = storage.load_latest_snapshot('TestAccount', 'Keepers')
        assert keepers.total_chaos_value == 1100.0

        # Load Standard - should get modified
        standard = storage.load_latest_snapshot('TestAccount', 'Standard')
        assert standard.total_chaos_value == 500.0
