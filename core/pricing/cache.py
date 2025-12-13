"""
Item Price Cache - LRU cache for recently checked items.

Provides fast lookup for repeated price checks within a session,
avoiding redundant API calls and database queries.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _normalize_item_text_cached(item_text: str) -> str:
    """
    Normalize item text for consistent cache keys (cached).

    Removes whitespace variations and normalizes line endings.
    Uses lru_cache for repeated lookups of the same item text.
    """
    # Strip and normalize line endings
    text = item_text.strip()
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove excessive whitespace within lines
    lines = [' '.join(line.split()) for line in text.split('\n')]

    # Join back with single newlines
    return '\n'.join(lines)


@dataclass
class CacheEntry:
    """A cached price check result."""
    results: List[Dict[str, Any]]
    timestamp: float
    item_hash: str
    item_name: str = ""


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def total_requests(self) -> int:
        """Total number of cache requests."""
        return self.hits + self.misses

    def reset(self) -> None:
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0


class ItemPriceCache:
    """
    LRU cache for item price check results.

    Features:
    - LRU eviction when max size is reached
    - TTL-based expiration for freshness
    - Thread-safe operations
    - Performance statistics
    - Normalized item text hashing for consistent keys

    Usage:
        cache = ItemPriceCache(max_size=500, ttl_seconds=300)

        # Check cache before expensive lookup
        cached = cache.get(item_text)
        if cached is not None:
            return cached

        # Perform lookup and cache result
        results = price_service.check_item(item_text)
        cache.put(item_text, results)
    """

    DEFAULT_MAX_SIZE = 500
    DEFAULT_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ):
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of entries to store.
            ttl_seconds: Time-to-live for entries in seconds.
        """
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = CacheStats()

    @property
    def stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    @property
    def size(self) -> int:
        """Current number of entries in cache."""
        with self._lock:
            return len(self._cache)

    @property
    def max_size(self) -> int:
        """Maximum cache size."""
        return self._max_size

    @property
    def ttl_seconds(self) -> float:
        """Entry TTL in seconds."""
        return self._ttl_seconds

    @ttl_seconds.setter
    def ttl_seconds(self, value: float) -> None:
        """Set entry TTL."""
        self._ttl_seconds = max(10.0, value)  # Minimum 10 seconds

    def _normalize_item_text(self, item_text: str) -> str:
        """
        Normalize item text for consistent cache keys.

        Delegates to module-level cached function for performance.
        """
        return _normalize_item_text_cached(item_text)

    def _hash_item(self, item_text: str) -> str:
        """Generate hash key for item text."""
        normalized = self._normalize_item_text(item_text)
        # MD5 used only for cache key generation, not security
        return hashlib.md5(normalized.encode('utf-8'), usedforsecurity=False).hexdigest()

    def _extract_item_name(self, item_text: str) -> str:
        """Extract item name from text for logging/debugging."""
        lines = item_text.strip().split('\n')
        # Skip rarity line if present
        for line in lines:
            if not line.startswith('Rarity:') and line.strip():
                return line.strip()[:50]  # First 50 chars
        return "Unknown"

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if an entry has expired."""
        age = time.time() - entry.timestamp
        return age > self._ttl_seconds

    def get(self, item_text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached results for item text.

        Args:
            item_text: Raw item text from clipboard.

        Returns:
            Cached results list, or None if not found/expired.
        """
        item_hash = self._hash_item(item_text)

        with self._lock:
            if item_hash not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[item_hash]

            # Check expiration
            if self._is_expired(entry):
                del self._cache[item_hash]
                self._stats.misses += 1
                self._stats.expirations += 1
                logger.debug(f"Cache entry expired for '{entry.item_name}'")
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(item_hash)
            self._stats.hits += 1

            logger.debug(
                f"Cache hit for '{entry.item_name}' "
                f"(age: {time.time() - entry.timestamp:.1f}s)"
            )
            return entry.results

    def put(
        self,
        item_text: str,
        results: List[Dict[str, Any]],
    ) -> None:
        """
        Store results in cache.

        Args:
            item_text: Raw item text from clipboard.
            results: Price check results to cache.
        """
        item_hash = self._hash_item(item_text)
        item_name = self._extract_item_name(item_text)

        with self._lock:
            # Update existing or add new
            if item_hash in self._cache:
                # Update existing entry
                self._cache[item_hash] = CacheEntry(
                    results=results,
                    timestamp=time.time(),
                    item_hash=item_hash,
                    item_name=item_name,
                )
                self._cache.move_to_end(item_hash)
            else:
                # Evict LRU if at capacity
                while len(self._cache) >= self._max_size:
                    oldest_key, oldest_entry = self._cache.popitem(last=False)
                    self._stats.evictions += 1
                    logger.debug(f"Evicted LRU entry '{oldest_entry.item_name}'")

                # Add new entry
                self._cache[item_hash] = CacheEntry(
                    results=results,
                    timestamp=time.time(),
                    item_hash=item_hash,
                    item_name=item_name,
                )

            logger.debug(f"Cached results for '{item_name}'")

    def invalidate(self, item_text: str) -> bool:
        """
        Remove a specific item from cache.

        Args:
            item_text: Raw item text to invalidate.

        Returns:
            True if item was in cache and removed.
        """
        item_hash = self._hash_item(item_text)

        with self._lock:
            if item_hash in self._cache:
                del self._cache[item_hash]
                return True
            return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} cache entries")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats.expirations += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)

    def get_recent_items(self, limit: int = 10) -> List[str]:
        """
        Get names of recently cached items.

        Args:
            limit: Maximum number of items to return.

        Returns:
            List of item names (most recent first).
        """
        with self._lock:
            items = list(self._cache.values())
            items.reverse()  # Most recent first
            return [entry.item_name for entry in items[:limit]]


# Global cache instance
_item_price_cache: Optional[ItemPriceCache] = None


def get_item_price_cache(
    max_size: int = ItemPriceCache.DEFAULT_MAX_SIZE,
    ttl_seconds: float = ItemPriceCache.DEFAULT_TTL_SECONDS,
) -> ItemPriceCache:
    """
    Get or create the global item price cache.

    Args:
        max_size: Maximum entries (only used on first call).
        ttl_seconds: Entry TTL (only used on first call).

    Returns:
        The global cache instance.
    """
    global _item_price_cache

    if _item_price_cache is None:
        _item_price_cache = ItemPriceCache(
            max_size=max_size,
            ttl_seconds=ttl_seconds,
        )
        logger.info(
            f"Created item price cache (max_size={max_size}, "
            f"ttl={ttl_seconds}s)"
        )

    return _item_price_cache


def clear_item_price_cache() -> None:
    """Clear and reset the global cache."""
    if _item_price_cache is not None:
        _item_price_cache.clear()
        _item_price_cache.stats.reset()
