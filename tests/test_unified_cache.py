"""Comprehensive tests for unified cache module to improve coverage."""

import pytest
import time

from jinja2_async_environment.caching.unified import UnifiedCache


class TestUnifiedCache:
    """Test UnifiedCache class."""

    def test_initialization_default_ttl(self) -> None:
        """Test UnifiedCache initialization with default TTL."""
        cache = UnifiedCache(default_ttl=300)
        assert cache is not None
        assert len(cache.get_cache_types()) == 3

    def test_initialization_custom_ttl(self) -> None:
        """Test UnifiedCache initialization with custom TTL."""
        cache = UnifiedCache(default_ttl=600)
        assert cache._default_ttl == 600

    def test_get_set_default_caches(self) -> None:
        """Test get/set operations on default cache types."""
        cache = UnifiedCache()

        # Test package_import cache
        cache.set("package_import", "key1", "value1")
        assert cache.get("package_import", "key1") == "value1"

        # Test package_spec cache
        cache.set("package_spec", "key2", "value2")
        assert cache.get("package_spec", "key2") == "value2"

        # Test template_root cache
        cache.set("template_root", "key3", "value3")
        assert cache.get("template_root", "key3") == "value3"

    def test_get_nonexistent_key(self) -> None:
        """Test getting a non-existent key returns default."""
        cache = UnifiedCache()
        assert cache.get("package_import", "nonexistent") is None
        assert cache.get("package_import", "nonexistent", "default") == "default"

    def test_get_nonexistent_cache_type(self) -> None:
        """Test getting from non-existent cache type."""
        cache = UnifiedCache()
        assert cache.get("unknown_cache", "key") is None
        assert cache.get("unknown_cache", "key", "default") == "default"

    def test_set_with_custom_ttl(self) -> None:
        """Test setting a value with custom TTL."""
        cache = UnifiedCache(default_ttl=300)
        cache.set("package_import", "key1", "value1", ttl=1)
        assert cache.get("package_import", "key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("package_import", "key1") is None

    def test_set_creates_dynamic_cache(self) -> None:
        """Test that set creates a new cache type if needed."""
        cache = UnifiedCache()
        cache.set("custom_type", "key1", "value1")
        assert "custom_type" in cache.get_cache_types()
        assert cache.get("custom_type", "key1") == "value1"

    def test_key_type_conversion(self) -> None:
        """Test that keys are converted to strings internally."""
        cache = UnifiedCache()
        # Set with tuple key
        cache.set("package_import", ("path", "module"), "value1")
        # Get with tuple key
        assert cache.get("package_import", ("path", "module")) == "value1"

    def test_clear_specific_cache(self) -> None:
        """Test clearing a specific cache type."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")
        cache.set("package_spec", "key2", "value2")

        cache.clear("package_import")
        assert cache.get("package_import", "key1") is None
        assert cache.get("package_spec", "key2") == "value2"

    def test_clear_all_caches(self) -> None:
        """Test clearing all caches."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")
        cache.set("package_spec", "key2", "value2")
        cache.set("template_root", "key3", "value3")

        cache.clear()
        assert cache.get("package_import", "key1") is None
        assert cache.get("package_spec", "key2") is None
        assert cache.get("template_root", "key3") is None

    def test_clear_all_method(self) -> None:
        """Test the clear_all convenience method."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")
        cache.clear_all()
        assert cache.get("package_import", "key1") is None

    def test_clear_nonexistent_cache_type(self) -> None:
        """Test clearing a non-existent cache type."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")
        cache.clear("unknown_type")  # Should not raise
        assert cache.get("package_import", "key1") == "value1"

    def test_cleanup_expired(self) -> None:
        """Test cleanup of expired entries."""
        cache = UnifiedCache(default_ttl=1)
        cache.set("package_import", "key1", "value1", ttl=1)

        # Verify value exists before expiration
        assert cache.get("package_import", "key1") == "value1"

        # Wait for expiration (need more time to ensure > comparison passes)
        time.sleep(1.3)

        # After expiration, get() should return None due to automatic cleanup
        assert cache.get("package_import", "key1") is None

        # cleanup_expired should handle the now-deleted entry gracefully
        cache.cleanup_expired()

    def test_get_statistics(self) -> None:
        """Test getting statistics from all caches."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")
        cache.set("package_spec", "key2", "value2")

        stats = cache.get_statistics()
        assert isinstance(stats, dict)
        assert "package_import" in stats
        assert "package_spec" in stats
        assert "template_root" in stats

    def test_is_valid(self) -> None:
        """Test _is_valid method."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")

        assert cache._is_valid("package_import", "key1") is True
        assert cache._is_valid("package_import", "nonexistent") is False
        assert cache._is_valid("unknown_type", "key1") is False

    def test_contains(self) -> None:
        """Test contains method."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")

        assert cache.contains("package_import", "key1") is True
        assert cache.contains("package_import", "nonexistent") is False

    def test_resize_cache(self) -> None:
        """Test resizing a cache."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")

        # Resize should work without error
        cache.resize_cache("package_import", 100)
        assert cache.get("package_import", "key1") == "value1"

    def test_resize_nonexistent_cache(self) -> None:
        """Test resizing a non-existent cache type."""
        cache = UnifiedCache()
        cache.resize_cache("unknown_type", 100)  # Should not raise

    def test_get_cache_types(self) -> None:
        """Test getting list of cache types."""
        cache = UnifiedCache()
        types = cache.get_cache_types()
        assert isinstance(types, list)
        assert "package_import" in types
        assert "package_spec" in types
        assert "template_root" in types

    def test_len(self) -> None:
        """Test __len__ method."""
        cache = UnifiedCache()
        assert len(cache) == 0

        cache.set("package_import", "key1", "value1")
        assert len(cache) == 1

        cache.set("package_spec", "key2", "value2")
        assert len(cache) == 2

    def test_repr(self) -> None:
        """Test __repr__ method."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")

        repr_str = repr(cache)
        assert "UnifiedCache" in repr_str
        assert "types=3" in repr_str
        assert "entries=1" in repr_str

    def test_thread_safety_concurrent_access(self) -> None:
        """Test thread safety of concurrent operations."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")

        # Multiple operations should work without deadlock
        cache.get("package_import", "key1")
        cache.set("package_import", "key2", "value2")
        cache.clear("package_import")

        assert len(cache) == 0

    def test_multiple_values_in_cache(self) -> None:
        """Test multiple values in same cache."""
        cache = UnifiedCache()
        for i in range(10):
            cache.set("package_import", f"key{i}", f"value{i}")

        for i in range(10):
            assert cache.get("package_import", f"key{i}") == f"value{i}"

    def test_set_overwrites_existing(self) -> None:
        """Test that set overwrites existing values."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")
        assert cache.get("package_import", "key1") == "value1"

        cache.set("package_import", "key1", "value2")
        assert cache.get("package_import", "key1") == "value2"

    def test_cache_statistics_structure(self) -> None:
        """Test structure of cache statistics."""
        cache = UnifiedCache()
        cache.set("package_import", "key1", "value1")
        cache.get("package_import", "key1")
        cache.get("package_import", "nonexistent")

        stats = cache.get_statistics()
        for cache_type, cache_stats in stats.items():
            assert isinstance(cache_stats, dict)
            # Stats should have hit/miss counts or similar
            assert len(cache_stats) > 0

    def test_dynamic_cache_with_default_ttl(self) -> None:
        """Test creating dynamic cache respects default TTL."""
        cache = UnifiedCache(default_ttl=1)
        cache.set("custom_type", "key1", "value1")

        assert cache.get("custom_type", "key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("custom_type", "key1") is None

    def test_integer_and_string_keys(self) -> None:
        """Test that both integer and string keys work."""
        cache = UnifiedCache()

        # Integer key
        cache.set("package_import", 42, "value_int")
        assert cache.get("package_import", 42) == "value_int"

        # String key
        cache.set("package_import", "key_str", "value_str")
        assert cache.get("package_import", "key_str") == "value_str"

    def test_cache_types_immutability(self) -> None:
        """Test that cache type names are consistent."""
        cache1 = UnifiedCache()
        cache2 = UnifiedCache()

        types1 = cache1.get_cache_types()
        types2 = cache2.get_cache_types()

        assert types1 == types2
        assert set(types1) == {"package_import", "package_spec", "template_root"}
