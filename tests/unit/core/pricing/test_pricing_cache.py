"""
Tests for core/pricing/cache.py - ItemPriceCache and related classes.
"""
import time
import pytest
from unittest.mock import patch
from core.pricing.cache import (
    CacheEntry,
    CacheStats,
    ItemPriceCache,
    get_item_price_cache,
    clear_item_price_cache,
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_create_cache_entry(self):
        """Can create a CacheEntry with required fields."""
        entry = CacheEntry(
            results=[{"item_name": "Test", "chaos_value": 100}],
            timestamp=time.time(),
            item_hash="abc123",
        )

        assert entry.results == [{"item_name": "Test", "chaos_value": 100}]
        assert entry.item_hash == "abc123"
        assert entry.item_name == ""  # Default

    def test_create_cache_entry_with_name(self):
        """Can create a CacheEntry with item name."""
        entry = CacheEntry(
            results=[],
            timestamp=1234567890.0,
            item_hash="xyz789",
            item_name="Exalted Orb",
        )

        assert entry.item_name == "Exalted Orb"
        assert entry.timestamp == 1234567890.0


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_default_values(self):
        """CacheStats should have zero defaults."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.expirations == 0

    def test_hit_rate_zero_requests(self):
        """hit_rate should return 0.0 when no requests made."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_all_hits(self):
        """hit_rate should return 1.0 when all hits."""
        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 1.0

    def test_hit_rate_all_misses(self):
        """hit_rate should return 0.0 when all misses."""
        stats = CacheStats(hits=0, misses=10)
        assert stats.hit_rate == 0.0

    def test_hit_rate_mixed(self):
        """hit_rate should calculate correctly for mixed results."""
        stats = CacheStats(hits=7, misses=3)
        assert stats.hit_rate == 0.7

    def test_total_requests(self):
        """total_requests should sum hits and misses."""
        stats = CacheStats(hits=15, misses=5)
        assert stats.total_requests == 20

    def test_reset(self):
        """reset should zero all counters."""
        stats = CacheStats(hits=10, misses=5, evictions=3, expirations=2)
        stats.reset()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.expirations == 0


class TestItemPriceCacheCreation:
    """Tests for ItemPriceCache initialization."""

    def test_default_values(self):
        """Cache should use default values when not specified."""
        cache = ItemPriceCache()

        assert cache.max_size == 500
        assert cache.ttl_seconds == 300
        assert cache.size == 0

    def test_custom_values(self):
        """Cache should accept custom configuration."""
        cache = ItemPriceCache(max_size=100, ttl_seconds=60)

        assert cache.max_size == 100
        assert cache.ttl_seconds == 60

    def test_stats_property(self):
        """stats property should return CacheStats instance."""
        cache = ItemPriceCache()

        assert isinstance(cache.stats, CacheStats)
        assert cache.stats.hits == 0

    def test_ttl_setter_enforces_minimum(self):
        """TTL setter should enforce minimum of 10 seconds."""
        cache = ItemPriceCache()

        cache.ttl_seconds = 5  # Below minimum
        assert cache.ttl_seconds == 10.0

        cache.ttl_seconds = 60
        assert cache.ttl_seconds == 60.0


class TestItemPriceCacheOperations:
    """Tests for cache get/put operations."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return ItemPriceCache(max_size=10, ttl_seconds=60)

    def test_get_miss_returns_none(self, cache):
        """get should return None for missing items."""
        result = cache.get("nonexistent item")

        assert result is None
        assert cache.stats.misses == 1

    def test_put_and_get(self, cache):
        """put should store and get should retrieve."""
        item_text = "Rarity: Currency\nExalted Orb"
        results = [{"item_name": "Exalted Orb", "chaos_value": 150}]

        cache.put(item_text, results)
        retrieved = cache.get(item_text)

        assert retrieved == results
        assert cache.stats.hits == 1
        assert cache.size == 1

    def test_put_updates_existing(self, cache):
        """put should update existing entry."""
        item_text = "Rarity: Currency\nChaos Orb"
        old_results = [{"chaos_value": 1}]
        new_results = [{"chaos_value": 2}]

        cache.put(item_text, old_results)
        cache.put(item_text, new_results)

        retrieved = cache.get(item_text)
        assert retrieved == new_results
        assert cache.size == 1  # Still only one entry

    def test_cache_hit_increments_stats(self, cache):
        """Cache hits should increment hit counter."""
        item_text = "Test Item"
        cache.put(item_text, [])

        cache.get(item_text)
        cache.get(item_text)
        cache.get(item_text)

        assert cache.stats.hits == 3

    def test_cache_miss_increments_stats(self, cache):
        """Cache misses should increment miss counter."""
        cache.get("missing1")
        cache.get("missing2")

        assert cache.stats.misses == 2


class TestItemPriceCacheExpiration:
    """Tests for TTL-based expiration."""

    def test_expired_entry_returns_none(self):
        """Expired entries should return None."""
        cache = ItemPriceCache(ttl_seconds=0.1)  # 100ms TTL

        item_text = "Test Item"
        cache.put(item_text, [{"value": 1}])

        # Wait for expiration
        time.sleep(0.15)

        result = cache.get(item_text)
        assert result is None
        assert cache.stats.expirations == 1

    def test_non_expired_entry_returns_value(self):
        """Non-expired entries should return value."""
        cache = ItemPriceCache(ttl_seconds=60)

        item_text = "Test Item"
        results = [{"value": 1}]
        cache.put(item_text, results)

        # Immediate retrieval should succeed
        result = cache.get(item_text)
        assert result == results


class TestItemPriceCacheLRU:
    """Tests for LRU eviction."""

    def test_evicts_lru_when_full(self):
        """Should evict least recently used when at capacity."""
        cache = ItemPriceCache(max_size=3, ttl_seconds=60)

        # Fill cache
        cache.put("item1", [{"v": 1}])
        cache.put("item2", [{"v": 2}])
        cache.put("item3", [{"v": 3}])

        # Add one more - should evict item1
        cache.put("item4", [{"v": 4}])

        assert cache.get("item1") is None  # Evicted
        assert cache.get("item2") is not None
        assert cache.get("item4") is not None
        assert cache.stats.evictions == 1

    def test_access_updates_lru_order(self):
        """Accessing an item should make it most recently used."""
        cache = ItemPriceCache(max_size=3, ttl_seconds=60)

        cache.put("item1", [{"v": 1}])
        cache.put("item2", [{"v": 2}])
        cache.put("item3", [{"v": 3}])

        # Access item1 to make it most recent
        cache.get("item1")

        # Add new item - should evict item2 (now LRU)
        cache.put("item4", [{"v": 4}])

        assert cache.get("item1") is not None  # Still present
        assert cache.get("item2") is None  # Evicted


class TestItemPriceCacheInvalidation:
    """Tests for cache invalidation."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return ItemPriceCache(max_size=10, ttl_seconds=60)

    def test_invalidate_existing_item(self, cache):
        """invalidate should remove existing item."""
        item_text = "Test Item"
        cache.put(item_text, [])

        result = cache.invalidate(item_text)

        assert result is True
        assert cache.get(item_text) is None
        assert cache.size == 0

    def test_invalidate_missing_item(self, cache):
        """invalidate should return False for missing item."""
        result = cache.invalidate("nonexistent")
        assert result is False

    def test_clear_removes_all(self, cache):
        """clear should remove all entries."""
        cache.put("item1", [])
        cache.put("item2", [])
        cache.put("item3", [])

        count = cache.clear()

        assert count == 3
        assert cache.size == 0


class TestItemPriceCacheCleanup:
    """Tests for cleanup_expired method."""

    def test_cleanup_removes_expired(self):
        """cleanup_expired should remove all expired entries."""
        cache = ItemPriceCache(ttl_seconds=0.1)  # 100ms TTL

        cache.put("item1", [])
        cache.put("item2", [])

        time.sleep(0.15)  # Wait for expiration

        # TTL is still 0.1, so items should be expired
        removed = cache.cleanup_expired()

        assert removed == 2
        assert cache.size == 0
        assert cache.stats.expirations == 2

    def test_cleanup_keeps_fresh_items(self):
        """cleanup_expired should keep non-expired items."""
        cache = ItemPriceCache(ttl_seconds=60)

        cache.put("item1", [{"v": 1}])
        cache.put("item2", [{"v": 2}])

        removed = cache.cleanup_expired()

        assert removed == 0
        assert cache.size == 2


class TestItemPriceCacheRecentItems:
    """Tests for get_recent_items method."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return ItemPriceCache(max_size=10, ttl_seconds=60)

    def test_get_recent_items_empty_cache(self, cache):
        """get_recent_items should return empty list for empty cache."""
        result = cache.get_recent_items()
        assert result == []

    def test_get_recent_items_returns_names(self, cache):
        """get_recent_items should return item names."""
        cache.put("Rarity: Currency\nExalted Orb", [])
        cache.put("Rarity: Currency\nDivine Orb", [])

        names = cache.get_recent_items()

        assert len(names) == 2
        # Most recent first
        assert "Divine Orb" in names[0]
        assert "Exalted Orb" in names[1]

    def test_get_recent_items_respects_limit(self, cache):
        """get_recent_items should respect limit parameter."""
        for i in range(5):
            cache.put(f"Item {i}", [])

        names = cache.get_recent_items(limit=3)
        assert len(names) == 3


class TestItemPriceCacheNormalization:
    """Tests for text normalization and hashing."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return ItemPriceCache(max_size=10, ttl_seconds=60)

    def test_whitespace_normalized(self, cache):
        """Different whitespace should produce same cache key."""
        text1 = "Rarity: Currency\nExalted Orb"
        text2 = "Rarity: Currency\r\nExalted Orb"
        text3 = "  Rarity: Currency\n  Exalted Orb  "

        cache.put(text1, [{"source": "text1"}])

        # All should hit the same entry
        assert cache.get(text2) == [{"source": "text1"}]
        assert cache.get(text3) == [{"source": "text1"}]

    def test_extra_spaces_normalized(self, cache):
        """Extra internal spaces should be normalized."""
        text1 = "Rarity: Currency\nName Here"
        text2 = "Rarity:  Currency\nName   Here"

        cache.put(text1, [{"v": 1}])
        assert cache.get(text2) == [{"v": 1}]

    def test_extract_item_name_skips_rarity(self, cache):
        """Item name extraction should skip Rarity line."""
        # This tests _extract_item_name indirectly through get_recent_items
        cache.put("Rarity: Unique\nHeadHunter\nLeather Belt", [])

        names = cache.get_recent_items()
        assert "Headhunter" in names[0] or "HeadHunter" in names[0]


class TestGlobalCacheFunctions:
    """Tests for global cache functions."""

    def test_get_item_price_cache_creates_singleton(self):
        """get_item_price_cache should create/return singleton."""
        # Reset global state for test
        import core.pricing.cache as cache_module
        cache_module._item_price_cache = None

        cache1 = get_item_price_cache()
        cache2 = get_item_price_cache()

        assert cache1 is cache2

    def test_get_item_price_cache_uses_first_call_params(self):
        """First call parameters should be used for creation."""
        import core.pricing.cache as cache_module
        cache_module._item_price_cache = None

        cache = get_item_price_cache(max_size=100, ttl_seconds=120)

        assert cache.max_size == 100
        assert cache.ttl_seconds == 120

        # Reset for other tests
        cache_module._item_price_cache = None

    def test_clear_item_price_cache(self):
        """clear_item_price_cache should clear and reset stats."""
        import core.pricing.cache as cache_module
        cache_module._item_price_cache = None

        cache = get_item_price_cache()
        cache.put("test", [])
        cache.get("test")

        clear_item_price_cache()

        assert cache.size == 0
        assert cache.stats.hits == 0

        # Reset for other tests
        cache_module._item_price_cache = None

    def test_clear_item_price_cache_when_none(self):
        """clear_item_price_cache should handle None cache gracefully."""
        import core.pricing.cache as cache_module
        cache_module._item_price_cache = None

        # Should not raise
        clear_item_price_cache()


class TestItemPriceCacheThreadSafety:
    """Tests for thread safety (basic verification)."""

    def test_concurrent_operations(self):
        """Cache should handle concurrent operations."""
        import threading

        cache = ItemPriceCache(max_size=100, ttl_seconds=60)
        errors = []

        def worker(item_id):
            try:
                for _ in range(50):
                    item_text = f"Item {item_id}"
                    cache.put(item_text, [{"id": item_id}])
                    cache.get(item_text)
                    cache.invalidate(item_text)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
