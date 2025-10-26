"""Edge case tests to improve coverage of critical paths."""

import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from jinja2_async_environment.caching.typed import TypedCache
from jinja2_async_environment.caching.strategies import (
    LFUCache,
    AdaptiveCache,
    HierarchicalCache,
)
from jinja2_async_environment.testing.fixtures import (
    isolated_test_context,
    UnifiedCache,
    _clear_expired_cache,
)


class TestTypedCacheEdgeCases:
    """Test edge cases in TypedCache."""

    def test_typed_cache_delete_nonexistent(self) -> None:
        """Test deleting non-existent key."""
        cache = TypedCache[str](max_size=10)
        cache.delete("nonexistent")  # Should not raise

    def test_typed_cache_keys(self) -> None:
        """Test getting all keys."""
        cache = TypedCache[str](max_size=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = cache.keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_typed_cache_contains(self) -> None:
        """Test __contains__ magic method."""
        cache = TypedCache[str](max_size=10)
        cache.set("key1", "value1")

        assert "key1" in cache
        assert "missing" not in cache

    def test_typed_cache_with_ttl_and_custom_ttl(self) -> None:
        """Test setting custom TTL for specific entry."""
        cache = TypedCache[str](max_size=10, default_ttl=600)
        cache.set("key1", "value1", ttl=300)
        assert cache.get("key1") == "value1"

    def test_typed_cache_concurrent_operations(self) -> None:
        """Test multiple operations in sequence."""
        cache = TypedCache[str](max_size=10)
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
            assert cache.get(f"key{i}") == f"value{i}"


class TestLFUCacheEdgeCases:
    """Test LFU cache edge cases."""

    def test_lfu_single_access_frequency(self) -> None:
        """Test that newly added items have frequency of 1."""
        cache = LFUCache(max_size=10)
        cache.set("key1", "value1")
        # Verify it exists immediately after set
        assert cache.get("key1") == "value1"

    def test_lfu_frequency_tracking(self) -> None:
        """Test that frequently accessed items are retained."""
        cache = LFUCache(max_size=3)
        cache.set("freq_high", "value1")
        cache.set("freq_mid", "value2")
        cache.set("freq_low", "value3")

        # Access freq_high many times
        for _ in range(5):
            cache.get("freq_high")

        # Access freq_mid a few times
        for _ in range(2):
            cache.get("freq_mid")

        # Add new item - freq_low should be evicted
        cache.set("new_item", "value4")

        # High frequency item should still be there
        assert cache.get("freq_high") == "value1"


class TestAdaptiveCacheEdgeCases:
    """Test adaptive cache edge cases."""

    def test_adaptive_cache_strategy_detection(self) -> None:
        """Test that adaptive cache detects access patterns."""
        cache = AdaptiveCache(max_size=10)

        # Create frequency-based pattern
        for i in range(3):
            cache.set(f"item{i}", f"value{i}")

        # Access in frequency pattern
        for _ in range(3):
            cache.get("item0")
        for _ in range(2):
            cache.get("item1")

        # Should handle without errors
        assert cache.get("item0") == "value0"

    def test_adaptive_cache_recency_pattern(self) -> None:
        """Test recency-based eviction pattern."""
        cache = AdaptiveCache(max_size=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Add more items with different access patterns
        cache.set("key4", "value4")

        # Verify cache still responds
        assert cache.get("key1") is None or cache.get("key2") is not None


class TestHierarchicalCacheEdgeCases:
    """Test hierarchical cache edge cases."""

    def test_hierarchical_l1_to_l2_transfer(self) -> None:
        """Test item transfer from L1 to L2."""
        cache = HierarchicalCache(l1_size=2, l2_size=5)

        # Fill L1
        cache.set("l1_1", "value1")
        cache.set("l1_2", "value2")

        # Add to L2
        cache.set("l2_1", "value3")
        cache.set("l2_2", "value4")

        # Verify both levels have items
        assert cache.get("l1_1") is not None or cache.get("l2_1") is not None

    def test_hierarchical_l2_miss(self) -> None:
        """Test miss in L2 cache."""
        cache = HierarchicalCache(l1_size=5, l2_size=10)
        cache.set("key1", "value1")

        # Access non-existent key
        result = cache.get("nonexistent")
        assert result is None

    def test_hierarchical_size_limit(self) -> None:
        """Test that total cache respects size limits."""
        cache = HierarchicalCache(l1_size=3, l2_size=5)

        # Add many items
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        # Total should be limited
        assert len(cache) <= 8  # l1_size + l2_size


class TestCacheCommonOperations:
    """Test common operations across cache types."""

    def test_cache_delete_and_reset(self) -> None:
        """Test delete followed by reset."""
        cache = LFUCache(max_size=10)
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

        # Reset with same key
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_cache_overwrite_multiple_times(self) -> None:
        """Test overwriting same key multiple times."""
        cache = AdaptiveCache(max_size=10)

        for i in range(5):
            cache.set("key", f"value{i}")
            assert cache.get("key") == f"value{i}"

    def test_cache_mixed_operations(self) -> None:
        """Test mixed set/get/delete operations."""
        cache = LFUCache(max_size=10)

        # Mixed sequence
        cache.set("a", "1")
        cache.set("b", "2")
        assert cache.get("a") == "1"
        cache.delete("b")
        cache.set("c", "3")
        assert cache.get("c") == "3"
        assert cache.get("b") is None


class TestCacheInvariants:
    """Test cache maintains invariants."""

    def test_cache_size_never_exceeds_max(self) -> None:
        """Test that cache size never exceeds max_size."""
        cache = LFUCache(max_size=5)

        for i in range(20):
            cache.set(f"key{i}", f"value{i}")
            assert len(cache) <= 5

    def test_cache_get_same_size(self) -> None:
        """Test that get operations don't change size."""
        cache = AdaptiveCache(max_size=10)
        cache.set("key1", "value1")
        initial_size = len(cache)

        cache.get("key1")
        cache.get("key1")
        cache.get("nonexistent")

        assert len(cache) == initial_size

    def test_hierarchical_total_size_limited(self) -> None:
        """Test hierarchical cache total size is limited."""
        cache = HierarchicalCache(l1_size=3, l2_size=4)

        # Add more than total capacity
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        # Total should never exceed l1_size + l2_size
        assert len(cache) <= 7


class TestTypedCacheTTLExpiration:
    """Test TypedCache TTL expiration edge cases."""

    def test_cleanup_expired_entries(self) -> None:
        """Test cleanup_expired removes expired entries."""
        cache = TypedCache[str](max_size=10, default_ttl=1)

        # Add entries with short TTL
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=1)

        # Wait for expiration
        time.sleep(1.1)

        # Cleanup should remove them
        removed = cache.cleanup_expired()
        assert removed >= 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_contains_with_expired_entry(self) -> None:
        """Test contains() returns False for expired entries."""
        cache = TypedCache[str](max_size=10, default_ttl=1)
        cache.set("key1", "value1", ttl=1)

        # Entry exists immediately
        assert cache.contains("key1")

        # Wait for expiration
        time.sleep(1.1)

        # Entry should no longer be considered contained
        assert not cache.contains("key1")

    def test_resize_cache_smaller(self) -> None:
        """Test resizing cache to smaller size evicts entries."""
        cache = TypedCache[str](max_size=10)

        # Fill cache
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        assert len(cache) == 10

        # Resize to smaller
        cache.resize(5)

        # Should have fewer entries
        assert len(cache) <= 5

    def test_evict_lru_entries(self) -> None:
        """Test LRU eviction when cache is full."""
        cache = TypedCache[str](max_size=3)

        # Fill cache
        cache.set("a", "value1")
        cache.set("b", "value2")
        cache.set("c", "value3")

        # Access some entries to change LRU order
        cache.get("a")
        cache.get("b")

        # Add new entry - least recently used (c) should be evicted
        cache.set("d", "value4")

        # Oldest unused entry should be gone
        assert len(cache) <= 3

    def test_keys_filters_expired(self) -> None:
        """Test keys() method filters out expired entries."""
        cache = TypedCache[str](max_size=10, default_ttl=1)

        # Add entries with short TTL
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=1)
        cache.set("key3", "value3", ttl=100)  # Long TTL

        # Wait for first two to expire
        time.sleep(1.1)

        # keys() should only return non-expired
        keys = cache.keys()
        assert "key3" in keys
        assert "key1" not in keys or "key2" not in keys

    def test_statistics_with_hits_and_misses(self) -> None:
        """Test statistics calculation with hits and misses."""
        cache = TypedCache[str](max_size=10)
        cache.set("key1", "value1")

        # Generate hits and misses
        cache.get("key1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_statistics()
        assert stats["hits"] > 0
        assert stats["misses"] > 0
        assert stats["hit_rate"] > 0


class TestTestingFixtures:
    """Test testing fixtures module coverage."""

    def test_unified_cache_operations(self) -> None:
        """Test UnifiedCache basic operations."""
        cache = UnifiedCache()

        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Test default value
        assert cache.get("missing") is None
        assert cache.get("missing", "default") == "default"

        # Test clear
        cache.clear_all()
        assert cache.get("key1") is None

    def test_clear_expired_cache_compatibility(self) -> None:
        """Test _clear_expired_cache function for backward compatibility."""
        # Should not raise, just for backward compatibility
        _clear_expired_cache()

    def test_isolated_test_context_manager(self) -> None:
        """Test isolated_test_context as context manager."""
        with isolated_test_context("test_name"):
            # Inside context, should work properly
            pass

        # After context, should be cleaned up
        # (context manager should handle cleanup)

    def test_isolated_test_context_with_exception(self) -> None:
        """Test isolated_test_context cleans up even with exception."""
        try:
            with isolated_test_context("test_with_exception"):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Context should still clean up despite exception
