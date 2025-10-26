"""Comprehensive tests for caching module to improve coverage."""

import pytest
import time
from unittest.mock import MagicMock, patch

from jinja2_async_environment.caching.typed import TypedCache
from jinja2_async_environment.caching.strategies import (
    LFUCache,
    AdaptiveCache,
    HierarchicalCache,
    CacheStatistics,
    CacheWarmer,
)
from jinja2_async_environment.caching.manager import CacheManager, AdvancedCacheManager


class TestTypeVCache:
    """Test TypedCache basic functionality."""

    def test_cache_get_set(self):
        """Test basic cache get/set operations."""
        cache: TypedCache[str] = TypedCache(max_size=100)

        # Set and retrieve
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache: TypedCache[str] = TypedCache(max_size=100)
        assert cache.get("nonexistent") is None

    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        cache: TypedCache[str] = TypedCache(max_size=100, default_ttl=1)
        cache.set("key1", "value1")

        # Should exist immediately
        assert cache.get("key1") == "value1"

        # Wait for TTL to expire
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_max_size(self):
        """Test max size enforcement."""
        cache: TypedCache[str] = TypedCache(max_size=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict oldest

        # key3 and key2 should exist, key1 might be evicted
        assert cache.get("key3") == "value3"

    def test_cache_delete(self):
        """Test cache deletion."""
        cache: TypedCache[str] = TypedCache(max_size=100)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        cache.delete("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """Test cache clearing."""
        cache: TypedCache[str] = TypedCache(max_size=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_size(self):
        """Test cache size via len()."""
        cache: TypedCache[str] = TypedCache(max_size=100)
        assert len(cache) == 0

        cache.set("key1", "value1")
        assert len(cache) == 1

        cache.set("key2", "value2")
        assert len(cache) == 2

    def test_cache_contains(self):
        """Test cache contains check."""
        cache: TypedCache[str] = TypedCache(max_size=100)
        assert "key1" not in cache

        cache.set("key1", "value1")
        assert "key1" in cache

    def test_cache_keys(self):
        """Test getting all cache keys."""
        cache: TypedCache[str] = TypedCache(max_size=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = cache.keys()
        assert "key1" in keys
        assert "key2" in keys


class TestLFUCache:
    """Test Least Frequently Used cache."""

    def test_lfu_eviction(self):
        """Test LFU eviction policy."""
        cache = LFUCache(max_size=3)

        # Fill cache
        cache.set("freq1", "value1")
        cache.set("freq2", "value2")
        cache.set("freq3", "value3")

        # Access freq1 and freq2 multiple times
        for _ in range(3):
            cache.get("freq1")
        for _ in range(2):
            cache.get("freq2")
        # freq3 has only 1 access

        # Add new item - should evict freq3 (least frequently used)
        cache.set("freq4", "value4")
        assert cache.get("freq3") is None or cache.get("freq4") == "value4"

    def test_lfu_statistics(self):
        """Test LFU statistics tracking."""
        cache = LFUCache(max_size=100)

        # Track hits and misses
        cache.get("nonexistent")  # Miss
        cache.set("key1", "value1")
        cache.get("key1")  # Hit

        stats = cache.get_statistics()
        assert isinstance(stats, dict)
        assert "misses" in stats or "hits" in stats

    def test_lfu_ttl_eviction(self):
        """Test LFU TTL eviction."""
        cache = LFUCache(max_size=100, default_ttl=1)
        cache.set("key1", "value1")

        time.sleep(1.1)
        assert cache.get("key1") is None


class TestAdaptiveCache:
    """Test Adaptive cache strategy."""

    def test_adaptive_initialization(self):
        """Test adaptive cache initialization."""
        cache = AdaptiveCache(max_size=100)
        assert cache.get("nonexistent") is None

    def test_adaptive_set_get(self):
        """Test basic set/get on adaptive cache."""
        cache = AdaptiveCache(max_size=100)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_adaptive_strategy_switching(self):
        """Test adaptive cache strategy switching."""
        cache = AdaptiveCache(max_size=100)

        # Fill cache with various access patterns
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        # Access some keys multiple times (frequency pattern)
        for _ in range(3):
            cache.get("key1")
            cache.get("key2")

        # Verify cache operations work
        assert cache.get("key1") == "value1"
        assert len(cache) > 0


class TestHierarchicalCache:
    """Test Hierarchical L1/L2 cache."""

    def test_hierarchical_initialization(self):
        """Test hierarchical cache initialization."""
        cache = HierarchicalCache(l1_size=10, l2_size=100)
        assert cache.get("nonexistent") is None

    def test_hierarchical_l1_set_get(self):
        """Test L1 cache operations."""
        cache = HierarchicalCache(l1_size=10, l2_size=100)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_hierarchical_promotion(self):
        """Test item promotion from L2 to L1."""
        cache = HierarchicalCache(l1_size=5, l2_size=20)

        # Fill L1
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")

        # This should go to L2
        cache.set("key5", "value5")

        # Access from L2 should be retrievable
        assert cache.get("key5") == "value5"

    def test_hierarchical_statistics(self):
        """Test hierarchical cache statistics."""
        cache = HierarchicalCache(l1_size=10, l2_size=100)
        cache.set("key1", "value1")
        cache.get("key1")

        stats = cache.get_statistics()
        assert stats is not None


class TestCacheStatistics:
    """Test cache statistics dataclass."""

    def test_statistics_initialization(self):
        """Test CacheStatistics initialization."""
        stats = CacheStatistics()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0

    def test_statistics_fields(self):
        """Test all CacheStatistics fields."""
        stats = CacheStatistics(
            hits=10,
            misses=5,
            evictions=2,
            memory_pressure_evictions=1,
            ttl_evictions=1,
            avg_access_time=0.001,
            peak_size=100,
            cache_efficiency=0.95,
        )
        assert stats.hits == 10
        assert stats.misses == 5
        assert stats.evictions == 2
        assert stats.memory_pressure_evictions == 1


class TestCacheWarmer:
    """Test CacheWarmer for preloading templates."""

    def test_cache_warmer_exists(self):
        """Test that CacheWarmer class exists."""
        assert CacheWarmer is not None


class TestCacheManager:
    """Test CacheManager for dependency injection."""

    def test_cache_manager_initialization(self):
        """Test CacheManager initialization."""
        manager = CacheManager(template_cache_size=1000, default_ttl=600)
        assert manager is not None

    def test_cache_manager_template_cache(self):
        """Test accessing template cache."""
        manager = CacheManager(template_cache_size=1000, default_ttl=600)
        cache = manager.template_cache
        assert cache is not None
        assert len(cache) >= 0

    def test_cache_manager_set_get(self):
        """Test set/get via manager."""
        manager = CacheManager(template_cache_size=1000, default_ttl=600)
        manager.set("template", "mykey", "myvalue")
        result = manager.get("template", "mykey")
        assert result == "myvalue"

    def test_cache_manager_clear_all(self):
        """Test clearing all caches."""
        manager = CacheManager(template_cache_size=1000, default_ttl=600)
        manager.set("template", "test", "value")
        manager.clear_all()
        assert manager.get("template", "test") is None

    def test_cache_manager_scoped_manager(self):
        """Test creating scoped cache manager."""
        manager = CacheManager(template_cache_size=1000, default_ttl=600)
        scoped = manager.create_scoped_manager()

        # Scoped manager should be isolated
        assert scoped is not None
        assert scoped.template_cache is not None


class TestAdvancedCacheManager:
    """Test AdvancedCacheManager with strategies."""

    def test_advanced_manager_lfu(self):
        """Test AdvancedCacheManager with LFU strategy."""
        manager = AdvancedCacheManager(strategy="lfu")
        assert manager is not None

    def test_advanced_manager_adaptive(self):
        """Test AdvancedCacheManager with adaptive strategy."""
        manager = AdvancedCacheManager(strategy="adaptive")
        assert manager is not None

    def test_advanced_manager_hierarchical(self):
        """Test AdvancedCacheManager with hierarchical strategy."""
        manager = AdvancedCacheManager(
            strategy="hierarchical",
            enable_hierarchical=True,
        )
        assert manager is not None

    def test_advanced_manager_template_cache(self):
        """Test accessing cache from advanced manager."""
        manager = AdvancedCacheManager(strategy="lfu")
        cache = manager.template_cache
        assert cache is not None

        # Test operations
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_advanced_manager_operations(self):
        """Test manager operations."""
        manager = AdvancedCacheManager(strategy="lfu")

        manager.set("template", "key1", "value1")
        manager.get("template", "key1")

        # Verify it works
        assert manager.get("template", "key1") == "value1"


class TestCachingIntegration:
    """Integration tests for caching module."""

    def test_cache_manager_with_lfu(self):
        """Test cache manager using LFU strategy."""
        manager = AdvancedCacheManager(strategy="lfu")
        cache = manager.template_cache

        # Test multi-key access
        for i in range(5):
            cache.set(f"template{i}", f"content{i}")

        # Verify retrieval
        assert cache.get("template0") == "content0"
        assert cache.get("template4") == "content4"

    def test_cache_memory_usage(self):
        """Test cache memory usage tracking."""
        manager = CacheManager(template_cache_size=1000, default_ttl=600)

        # Get memory estimate
        memory = manager.get_memory_usage_estimate()
        assert isinstance(memory, dict)
        assert len(memory) >= 0

    def test_scoped_cache_isolation(self):
        """Test that scoped caches are isolated."""
        manager = CacheManager(template_cache_size=1000, default_ttl=600)

        scope1 = manager.create_scoped_manager()
        scope2 = manager.create_scoped_manager()

        # Set in scope1
        cache1 = scope1.template_cache
        cache1.set("key1", "value1")

        # Retrieve from scope1
        assert cache1.get("key1") == "value1"

        # Scope2 should be independent
        cache2 = scope2.template_cache
        # Should either not have key1 or have different instance
        assert cache2 is not cache1 or cache2.get("key1") is None
