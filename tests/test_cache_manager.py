"""Tests for CacheManager to improve test coverage."""

import pytest
from jinja2_async_environment.caching.manager import (
    AdvancedCacheManager,
    CacheManager,
    TypedCache,
)


class TestCacheManager:
    """Test the CacheManager class to improve coverage."""

    def test_initialization(self):
        """Test CacheManager initialization with custom parameters."""
        manager = CacheManager(
            package_cache_size=100,
            template_cache_size=200,
            compilation_cache_size=300,
            module_cache_size=50,
            default_ttl=60,
        )

        assert isinstance(manager.package_cache, TypedCache)
        assert isinstance(manager.template_cache, TypedCache)
        assert isinstance(manager.compilation_cache, TypedCache)
        assert isinstance(manager.module_cache, TypedCache)

        # Check cache sizes
        pkg_stats = manager.package_cache.get_statistics()
        assert pkg_stats["max_size"] == 100

        tmpl_stats = manager.template_cache.get_statistics()
        assert tmpl_stats["max_size"] == 200

        comp_stats = manager.compilation_cache.get_statistics()
        assert comp_stats["max_size"] == 300

        mod_stats = manager.module_cache.get_statistics()
        assert mod_stats["max_size"] == 50

    def test_clear_all(self):
        """Test clearing all caches."""
        manager = CacheManager()

        # Add some entries to caches
        manager.package_cache.set("test_pkg", "value")
        manager.template_cache.set("test_template", "value")
        manager.compilation_cache.set("test_comp", "value")
        manager.module_cache.set("test_mod", "value")

        # Verify entries exist
        assert manager.package_cache.get("test_pkg") == "value"
        assert manager.template_cache.get("test_template") == "value"
        assert manager.compilation_cache.get("test_comp") == "value"
        assert manager.module_cache.get("test_mod") == "value"

        # Clear all
        manager.clear_all()

        # Verify entries are gone
        assert manager.package_cache.get("test_pkg") is None
        assert manager.template_cache.get("test_template") is None
        assert manager.compilation_cache.get("test_comp") is None
        assert manager.module_cache.get("test_mod") is None

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        manager = CacheManager()

        # Add entries with short TTL
        manager.package_cache.set("exp_pkg", "value", ttl=0)  # Expired immediately
        manager.template_cache.set(
            "exp_template", "value", ttl=0
        )  # Expired immediately
        manager.compilation_cache.set("exp_comp", "value", ttl=0)  # Expired immediately
        manager.module_cache.set("exp_mod", "value", ttl=0)  # Expired immediately

        # Check cleanup returns counts
        cleanup_results = manager.cleanup_expired()
        assert isinstance(cleanup_results, dict)
        assert "package_cache" in cleanup_results
        assert "template_cache" in cleanup_results
        assert "compilation_cache" in cleanup_results
        assert "module_cache" in cleanup_results

    def test_get_statistics(self):
        """Test getting statistics for all caches."""
        manager = CacheManager()

        stats = manager.get_statistics()
        assert isinstance(stats, dict)
        assert "package_cache" in stats
        assert "template_cache" in stats
        assert "compilation_cache" in stats
        assert "module_cache" in stats

        # Verify each cache has statistics
        for cache_name, cache_stats in stats.items():
            assert "size" in cache_stats
            assert "max_size" in cache_stats
            assert "fill_ratio" in cache_stats
            assert "hit_rate" in cache_stats

    def test_resize_caches(self):
        """Test resizing caches."""
        manager = CacheManager()

        initial_stats = manager.get_statistics()
        initial_size = initial_stats["package_cache"]["max_size"]

        # Resize package cache
        manager.resize_caches(package_size=initial_size // 2)
        new_stats = manager.get_statistics()
        new_size = new_stats["package_cache"]["max_size"]

        assert new_size == initial_size // 2

    def test_get_default(self):
        """Test getting default manager instance."""
        manager1 = CacheManager.get_default()
        manager2 = CacheManager.get_default()

        # Should return the same instance
        assert manager1 is manager2

        # Test setting a new default
        new_manager = CacheManager()
        CacheManager.set_default(new_manager)
        assert CacheManager.get_default() is new_manager

    def test_create_scoped_manager(self):
        """Test creating a scoped manager with different TTL settings."""
        original_manager = CacheManager()

        scoped_manager = original_manager.create_scoped_manager(
            package_ttl=100, template_ttl=200, compilation_ttl=300, module_ttl=400
        )

        # Verify it's a different instance
        assert original_manager is not scoped_manager

        # Verify TTLs are different
        original_pkg_ttl = original_manager.package_cache._default_ttl
        scoped_pkg_ttl = scoped_manager.package_cache._default_ttl
        assert scoped_pkg_ttl != original_pkg_ttl  # Different from default

    def test_get_memory_usage_estimate(self):
        """Test memory usage estimation."""
        manager = CacheManager()

        # Add some entries
        manager.package_cache.set("pkg1", "value1" * 10)
        manager.template_cache.set("tmpl1", "value2" * 10)

        memory_usage = manager.get_memory_usage_estimate()
        assert isinstance(memory_usage, dict)
        assert "package_cache" in memory_usage
        assert "template_cache" in memory_usage
        assert "compilation_cache" in memory_usage
        assert "module_cache" in memory_usage

        # Should be positive values
        for usage in memory_usage.values():
            assert usage >= 0

    def test_get_set_delete(self):
        """Test get, set, and delete operations for different cache types."""
        manager = CacheManager()

        # Test setting values
        manager.set("package", "pkg_key", "pkg_value")
        manager.set("template", "tmpl_key", "tmpl_value")
        manager.set("compilation", "comp_key", "comp_value")
        manager.set("module", "mod_key", "mod_value")

        # Test getting values
        assert manager.get("package", "pkg_key") == "pkg_value"
        assert manager.get("template", "tmpl_key") == "tmpl_value"
        assert manager.get("compilation", "comp_key") == "comp_value"
        assert manager.get("module", "mod_key") == "mod_value"

        # Test deleting values
        assert manager.delete("package", "pkg_key") is True
        assert manager.get("package", "pkg_key") is None

        # Test deleting non-existent key
        assert manager.delete("package", "non_existent") is False

        # Test invalid cache type
        with pytest.raises(ValueError):
            manager.set("invalid_type", "key", "value")

        with pytest.raises(ValueError):
            manager.get("invalid_type", "key")

        with pytest.raises(ValueError):
            manager.delete("invalid_type", "key")

    def test_repr(self):
        """Test string representation."""
        manager = CacheManager()
        repr_str = repr(manager)
        assert "CacheManager" in repr_str
        assert "total_entries" in repr_str
        assert "caches=4" in repr_str


class TestAdvancedCacheManager:
    """Test the AdvancedCacheManager class."""

    @pytest.mark.parametrize("strategy", ["lru", "lfu", "adaptive"])
    def test_initialization_with_strategies(self, strategy):
        """Test AdvancedCacheManager initialization with different strategies."""
        manager = AdvancedCacheManager(strategy=strategy)
        assert manager._strategy == strategy

        # Test hierarchical cache
        hierarchical_manager = AdvancedCacheManager(
            strategy=strategy, enable_hierarchical=True
        )
        assert hierarchical_manager._enable_hierarchical is True

    def test_extended_statistics(self):
        """Test extended statistics method."""
        manager = AdvancedCacheManager()
        extended_stats = manager.get_extended_statistics()

        assert "strategy" in extended_stats
        assert "hierarchical_enabled" in extended_stats
        assert "base_stats" in extended_stats

    def test_optimize_caches(self):
        """Test cache optimization."""
        manager = AdvancedCacheManager(strategy="adaptive")
        results = manager.optimize_caches()

        assert isinstance(results, dict)
        assert "cleanup" in results

    def test_memory_efficiency_report(self):
        """Test memory efficiency report."""
        manager = AdvancedCacheManager()
        report = manager.get_memory_efficiency_report()

        assert isinstance(report, dict)
        assert "total_memory_bytes" in report
        assert "total_entries" in report
        assert "avg_memory_per_entry" in report
        assert "memory_by_cache" in report
        assert "cache_utilization" in report
        assert "recommendations" in report
