"""
gui_qt.services.history_manager - Manages price check session history.

Provides bounded history storage with persistence callbacks and filtering.
Extracted from main_window.py to reduce complexity.

Usage:
    manager = HistoryManager(max_entries=100)
    manager.add_entry(item_text, parsed_item, results)

    entries = manager.get_entries()
    manager.clear()
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Callable, Deque, Dict, List, Optional, Any, TYPE_CHECKING

from core.constants import HISTORY_MAX_ENTRIES
from core.history import HistoryEntry

if TYPE_CHECKING:
    from core.item_parser import ParsedItem

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manages price check session history with bounded storage.

    Features:
    - Bounded deque to prevent unbounded memory growth
    - Thread-safe singleton pattern
    - Optional persistence callbacks
    - Filtering and search capabilities

    Signals/Slots:
        None - this is a pure service class. Use callbacks for notifications.
    """

    _instance: Optional['HistoryManager'] = None
    _lock: threading.Lock = threading.Lock()
    _history: Deque[HistoryEntry]
    _max_entries: int
    _on_change_callbacks: List[Callable[[], None]]

    def __new__(cls, max_entries: int = HISTORY_MAX_ENTRIES) -> 'HistoryManager':
        """Singleton pattern with thread-safe double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._history = deque(maxlen=max_entries)  # type: ignore[attr-defined]
                    instance._max_entries = max_entries  # type: ignore[attr-defined]
                    instance._on_change_callbacks = []  # type: ignore[attr-defined]
                    cls._instance = instance
        return cls._instance

    @property
    def max_entries(self) -> int:
        """Get the maximum number of history entries."""
        return self._max_entries

    @property
    def count(self) -> int:
        """Get the current number of history entries."""
        return len(self._history)

    def add_entry(
        self,
        item_text: str,
        parsed_item: "ParsedItem",
        results: List[Dict[str, Any]],
    ) -> HistoryEntry:
        """
        Add a new history entry from a price check result.

        Args:
            item_text: Raw item text that was checked.
            parsed_item: The parsed item object.
            results: List of price results from the check.

        Returns:
            The created HistoryEntry.
        """
        entry = HistoryEntry.from_price_check(item_text, parsed_item, results)
        self._history.append(entry)
        self._notify_change()
        logger.debug(f"Added history entry: {entry.item_name} ({self.count}/{self.max_entries})")
        return entry

    def add_entry_direct(self, entry: HistoryEntry) -> None:
        """
        Add a pre-created history entry.

        Args:
            entry: The HistoryEntry to add.
        """
        self._history.append(entry)
        self._notify_change()

    def get_entries(self) -> List[HistoryEntry]:
        """
        Get all history entries as a list (newest last).

        Returns:
            List of HistoryEntry objects.
        """
        return list(self._history)

    def get_entries_reversed(self) -> List[HistoryEntry]:
        """
        Get all history entries in reverse order (newest first).

        Returns:
            List of HistoryEntry objects, most recent first.
        """
        return list(reversed(self._history))

    def get_latest(self, n: int = 1) -> List[HistoryEntry]:
        """
        Get the N most recent entries.

        Args:
            n: Number of entries to return.

        Returns:
            List of up to N most recent HistoryEntry objects.
        """
        entries = list(self._history)
        return entries[-n:] if len(entries) >= n else entries

    def search(self, query: str) -> List[HistoryEntry]:
        """
        Search history entries by item name (case-insensitive).

        Args:
            query: Search string to match against item names.

        Returns:
            List of matching HistoryEntry objects.
        """
        query_lower = query.lower()
        return [
            entry for entry in self._history
            if query_lower in entry.item_name.lower()
        ]

    def filter_by_price(
        self,
        min_price: float = 0,
        max_price: Optional[float] = None,
    ) -> List[HistoryEntry]:
        """
        Filter history entries by price range.

        Args:
            min_price: Minimum chaos value.
            max_price: Maximum chaos value (None for no limit).

        Returns:
            List of matching HistoryEntry objects.
        """
        return [
            entry for entry in self._history
            if entry.best_price >= min_price
            and (max_price is None or entry.best_price <= max_price)
        ]

    def clear(self) -> int:
        """
        Clear all history entries.

        Returns:
            Number of entries that were cleared.
        """
        count = len(self._history)
        self._history.clear()
        self._notify_change()
        logger.info(f"Cleared {count} history entries")
        return count

    def is_empty(self) -> bool:
        """Check if history is empty."""
        return len(self._history) == 0

    def register_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be notified when history changes.

        Args:
            callback: Function to call when history is modified.
        """
        if callback not in self._on_change_callbacks:
            self._on_change_callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """
        Unregister a previously registered callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._on_change_callbacks:
            self._on_change_callbacks.remove(callback)

    def _notify_change(self) -> None:
        """Notify all registered callbacks of a change."""
        for callback in self._on_change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"History change callback error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the history.

        Returns:
            Dictionary with history statistics.
        """
        if not self._history:
            return {
                "count": 0,
                "max_entries": self._max_entries,
                "total_results": 0,
                "avg_price": 0.0,
                "max_price": 0.0,
                "min_price": 0.0,
            }

        prices = [e.best_price for e in self._history if e.best_price > 0]
        total_results = sum(e.results_count for e in self._history)

        return {
            "count": len(self._history),
            "max_entries": self._max_entries,
            "total_results": total_results,
            "avg_price": sum(prices) / len(prices) if prices else 0.0,
            "max_price": max(prices) if prices else 0.0,
            "min_price": min(prices) if prices else 0.0,
        }

    @classmethod
    def reset_for_testing(cls) -> None:
        """
        Reset the singleton instance for test isolation.

        Call this in test fixtures to ensure tests don't affect each other.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance._history.clear()
                cls._instance._on_change_callbacks.clear()
            cls._instance = None
        logger.debug("HistoryManager reset for testing")


# Module-level singleton accessor
_history_manager: Optional[HistoryManager] = None


def get_history_manager(max_entries: int = HISTORY_MAX_ENTRIES) -> HistoryManager:
    """
    Get the global history manager instance.

    Args:
        max_entries: Maximum entries (only used on first call).

    Returns:
        The singleton HistoryManager instance.
    """
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager(max_entries)
    return _history_manager
