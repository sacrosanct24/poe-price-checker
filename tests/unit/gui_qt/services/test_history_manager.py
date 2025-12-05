"""
Tests for gui_qt.services.history_manager - HistoryManager service.
"""

import pytest
import threading
from datetime import datetime
from unittest.mock import MagicMock, patch

from gui_qt.services.history_manager import HistoryManager, get_history_manager
from core.history import HistoryEntry


def make_entry(
    item_name: str = "Test Item",
    item_text: str = "Test",
    best_price: float = 10.0,
    results_count: int = 1,
) -> HistoryEntry:
    """Helper to create HistoryEntry with timestamp."""
    return HistoryEntry(
        timestamp=datetime.now().isoformat(),
        item_name=item_name,
        item_text=item_text,
        best_price=best_price,
        results_count=results_count,
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset HistoryManager singleton before and after each test."""
    HistoryManager.reset_for_testing()
    yield
    HistoryManager.reset_for_testing()


class TestHistoryManagerSingleton:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """HistoryManager should return the same instance on multiple calls."""
        manager1 = HistoryManager()
        manager2 = HistoryManager()
        assert manager1 is manager2

    def test_get_history_manager_returns_singleton(self):
        """get_history_manager() should return the singleton instance."""
        manager1 = get_history_manager()
        manager2 = get_history_manager()
        assert manager1 is manager2

    def test_reset_for_testing_clears_singleton(self):
        """reset_for_testing should clear the singleton and allow new instances."""
        manager1 = HistoryManager()
        manager1.add_entry_direct(make_entry(item_name="Test Item", best_price=100.0))
        assert manager1.count == 1

        HistoryManager.reset_for_testing()

        manager2 = HistoryManager()
        assert manager2.count == 0
        # Should be a new instance after reset
        assert manager1 is not manager2

    def test_thread_safety(self):
        """Test that multiple threads can safely access HistoryManager."""
        results = []
        errors = []

        def create_and_add():
            try:
                manager = HistoryManager()
                entry = make_entry(
                    item_name=f"Item-{threading.current_thread().name}",
                    best_price=10.0,
                )
                manager.add_entry_direct(entry)
                results.append(manager)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_and_add, name=f"T{i}") for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors occurred: {errors}"
        # All threads should get the same singleton
        assert all(r is results[0] for r in results)


class TestHistoryManagerBasicOperations:
    """Tests for basic history operations."""

    def test_add_entry_direct(self):
        """Test adding a pre-created HistoryEntry."""
        manager = HistoryManager()
        entry = make_entry(item_name="Test Item", best_price=100.0, results_count=5)
        manager.add_entry_direct(entry)

        assert manager.count == 1
        entries = manager.get_entries()
        assert len(entries) == 1
        assert entries[0].item_name == "Test Item"
        assert entries[0].best_price == 100.0

    def test_add_entry_creates_history_entry(self):
        """Test add_entry creates a HistoryEntry from price check data."""
        manager = HistoryManager()

        # Create mock parsed item
        parsed_item = MagicMock()
        parsed_item.name = "Tabula Rasa"
        parsed_item.rarity = "unique"
        parsed_item.item_class = "Body Armour"

        results = [
            {"chaos_value": 50.0, "source": "poe.ninja"},
            {"chaos_value": 55.0, "source": "poe.watch"},
        ]

        entry = manager.add_entry("Rarity: Unique\nTabula Rasa", parsed_item, results)

        assert manager.count == 1
        assert entry.item_name == "Tabula Rasa"
        assert entry.best_price == 55.0  # Max from results (from_price_check uses max)
        assert entry.results_count == 2

    def test_get_entries_returns_list(self):
        """Test get_entries returns a list copy."""
        manager = HistoryManager()

        for i in range(3):
            manager.add_entry_direct(make_entry(item_name=f"Item {i}", best_price=i * 10.0))

        entries = manager.get_entries()
        assert isinstance(entries, list)
        assert len(entries) == 3

        # Modifying returned list should not affect internal storage
        entries.pop()
        assert manager.count == 3

    def test_get_entries_reversed(self):
        """Test get_entries_reversed returns newest first."""
        manager = HistoryManager()

        for i in range(3):
            manager.add_entry_direct(make_entry(item_name=f"Item {i}", best_price=i * 10.0))

        entries = manager.get_entries_reversed()
        assert entries[0].item_name == "Item 2"
        assert entries[2].item_name == "Item 0"

    def test_get_latest(self):
        """Test get_latest returns N most recent entries."""
        manager = HistoryManager()

        for i in range(5):
            manager.add_entry_direct(make_entry(item_name=f"Item {i}", best_price=i * 10.0))

        latest = manager.get_latest(2)
        assert len(latest) == 2
        assert latest[0].item_name == "Item 3"
        assert latest[1].item_name == "Item 4"

    def test_get_latest_more_than_available(self):
        """Test get_latest when requesting more than available."""
        manager = HistoryManager()
        manager.add_entry_direct(make_entry(item_name="Single Item", best_price=10.0))

        latest = manager.get_latest(5)
        assert len(latest) == 1

    def test_clear(self):
        """Test clearing history."""
        manager = HistoryManager()

        for i in range(3):
            manager.add_entry_direct(make_entry(item_name=f"Item {i}", best_price=10.0))

        assert manager.count == 3
        cleared_count = manager.clear()
        assert cleared_count == 3
        assert manager.count == 0
        assert manager.is_empty()

    def test_is_empty(self):
        """Test is_empty check."""
        manager = HistoryManager()
        assert manager.is_empty()

        manager.add_entry_direct(make_entry(item_name="Item", best_price=10.0))
        assert not manager.is_empty()


class TestHistoryManagerBoundedStorage:
    """Tests for bounded history storage."""

    def test_max_entries_property(self):
        """Test max_entries property."""
        manager = HistoryManager(max_entries=50)
        assert manager.max_entries == 50

    def test_bounded_storage_evicts_oldest(self):
        """Test that oldest entries are evicted when limit is reached."""
        # Create manager with small limit
        HistoryManager.reset_for_testing()
        manager = HistoryManager(max_entries=3)

        for i in range(5):
            manager.add_entry_direct(make_entry(item_name=f"Item {i}", best_price=i * 10.0))

        assert manager.count == 3
        entries = manager.get_entries()
        # Should have items 2, 3, 4 (oldest evicted)
        assert entries[0].item_name == "Item 2"
        assert entries[2].item_name == "Item 4"


class TestHistoryManagerSearch:
    """Tests for search and filter operations."""

    def test_search_by_name(self):
        """Test searching history by item name."""
        manager = HistoryManager()

        manager.add_entry_direct(make_entry(item_name="Tabula Rasa", best_price=50.0))
        manager.add_entry_direct(make_entry(item_name="Headhunter", best_price=5000.0))
        manager.add_entry_direct(make_entry(item_name="Tabula Simple Robe", best_price=1.0))

        results = manager.search("tabula")
        assert len(results) == 2
        assert all("tabula" in r.item_name.lower() for r in results)

    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        manager = HistoryManager()

        manager.add_entry_direct(make_entry(item_name="HEADHUNTER", best_price=5000.0))

        results = manager.search("headhunter")
        assert len(results) == 1

        results = manager.search("HeAdHuNtEr")
        assert len(results) == 1

    def test_filter_by_price_min(self):
        """Test filtering by minimum price."""
        manager = HistoryManager()

        for price in [10.0, 50.0, 100.0, 500.0]:
            manager.add_entry_direct(make_entry(item_name=f"Item-{price}", best_price=price))

        results = manager.filter_by_price(min_price=100)
        assert len(results) == 2
        assert all(r.best_price >= 100 for r in results)

    def test_filter_by_price_max(self):
        """Test filtering by maximum price."""
        manager = HistoryManager()

        for price in [10.0, 50.0, 100.0, 500.0]:
            manager.add_entry_direct(make_entry(item_name=f"Item-{price}", best_price=price))

        results = manager.filter_by_price(max_price=50)
        assert len(results) == 2
        assert all(r.best_price <= 50 for r in results)

    def test_filter_by_price_range(self):
        """Test filtering by price range."""
        manager = HistoryManager()

        for price in [10.0, 50.0, 100.0, 500.0]:
            manager.add_entry_direct(make_entry(item_name=f"Item-{price}", best_price=price))

        results = manager.filter_by_price(min_price=50, max_price=200)
        assert len(results) == 2
        assert all(50 <= r.best_price <= 200 for r in results)


class TestHistoryManagerCallbacks:
    """Tests for callback system."""

    def test_register_callback(self):
        """Test registering a change callback."""
        manager = HistoryManager()
        callback_count = [0]

        def on_change():
            callback_count[0] += 1

        manager.register_callback(on_change)
        manager.add_entry_direct(make_entry(item_name="Item", best_price=10.0))

        assert callback_count[0] == 1

    def test_callback_on_add_entry(self):
        """Test callback is called on add_entry."""
        manager = HistoryManager()
        callback_called = [False]

        def on_change():
            callback_called[0] = True

        manager.register_callback(on_change)

        parsed_item = MagicMock()
        parsed_item.name = "Test"
        manager.add_entry("Test", parsed_item, [{"chaos_value": 10}])

        assert callback_called[0]

    def test_callback_on_clear(self):
        """Test callback is called on clear."""
        manager = HistoryManager()
        callback_called = [False]

        manager.add_entry_direct(make_entry(item_name="Item", best_price=10.0))

        def on_change():
            callback_called[0] = True

        manager.register_callback(on_change)
        manager.clear()

        assert callback_called[0]

    def test_unregister_callback(self):
        """Test unregistering a callback."""
        manager = HistoryManager()
        callback_count = [0]

        def on_change():
            callback_count[0] += 1

        manager.register_callback(on_change)
        manager.add_entry_direct(make_entry(item_name="Item 1", best_price=10.0))
        assert callback_count[0] == 1

        manager.unregister_callback(on_change)
        manager.add_entry_direct(make_entry(item_name="Item 2", best_price=20.0))
        assert callback_count[0] == 1  # Not incremented

    def test_callback_error_does_not_break_other_callbacks(self):
        """Test that a failing callback doesn't prevent other callbacks."""
        manager = HistoryManager()
        callback2_called = [False]

        def failing_callback():
            raise ValueError("Callback error")

        def working_callback():
            callback2_called[0] = True

        manager.register_callback(failing_callback)
        manager.register_callback(working_callback)

        # Should not raise, and second callback should still be called
        manager.add_entry_direct(make_entry(item_name="Item", best_price=10.0))

        assert callback2_called[0]


class TestHistoryManagerStatistics:
    """Tests for statistics generation."""

    def test_get_statistics_empty(self):
        """Test statistics for empty history."""
        manager = HistoryManager()
        stats = manager.get_statistics()

        assert stats["count"] == 0
        assert stats["total_results"] == 0
        assert stats["avg_price"] == 0.0
        assert stats["max_price"] == 0.0
        assert stats["min_price"] == 0.0

    def test_get_statistics_with_data(self):
        """Test statistics calculation with data."""
        manager = HistoryManager()

        manager.add_entry_direct(make_entry(item_name="Item 1", best_price=100.0, results_count=3))
        manager.add_entry_direct(make_entry(item_name="Item 2", best_price=200.0, results_count=2))
        manager.add_entry_direct(make_entry(item_name="Item 3", best_price=300.0, results_count=5))

        stats = manager.get_statistics()

        assert stats["count"] == 3
        assert stats["total_results"] == 10
        assert stats["avg_price"] == 200.0  # (100+200+300)/3
        assert stats["max_price"] == 300.0
        assert stats["min_price"] == 100.0

    def test_statistics_ignores_zero_price_for_avg(self):
        """Test that zero prices are excluded from average calculation."""
        manager = HistoryManager()

        manager.add_entry_direct(make_entry(item_name="Item 1", best_price=100.0, results_count=1))
        manager.add_entry_direct(make_entry(item_name="Item 2", best_price=0.0, results_count=1))
        manager.add_entry_direct(make_entry(item_name="Item 3", best_price=200.0, results_count=1))

        stats = manager.get_statistics()

        # Zero price should be excluded from avg
        assert stats["avg_price"] == 150.0  # (100+200)/2, not (100+0+200)/3
