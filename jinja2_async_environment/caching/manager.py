"""Cache manager for dependency injection and centralized cache control."""

import typing as t
from contextlib import suppress
from types import ModuleType

from anyio import Path as AsyncPath

from .strategies import AdaptiveCache, CacheWarmer, HierarchicalCache, LFUCache
from .typed import TypedCache

# Specialized type aliases for different cache types
PackageSpecCache = TypedCache[tuple[t.Any, t.Any]]
TemplateRootCache = TypedCache[AsyncPath | None]
CompilationCache = TypedCache[str]
ModuleCache = TypedCache[ModuleType]

# Type alias for template cache that can be either TypedCache or HierarchicalCache
TemplateCache = TypedCache[AsyncPath | None] | HierarchicalCache[AsyncPath | None]


class CacheManager:
    """Centralized cache management with dependency injection support.

    This manager provides type-safe caches for different use cases while
    allowing dependency injection and proper resource management.
    """

    _default_instance: "CacheManager | None" = None

    def __init__(
        self,
        package_cache_size: int = 500,
        template_cache_size: int = 1000,
        compilation_cache_size: int = 2000,
        module_cache_size: int = 200,
        default_ttl: int = 300,
    ):
        """Initialize the cache manager.

        Args:
            package_cache_size: Maximum size for package spec cache
            template_cache_size: Maximum size for template root cache
            compilation_cache_size: Maximum size for compilation cache
            module_cache_size: Maximum size for module import cache
            default_ttl: Default TTL for all caches in seconds
        """
        # Initialize type-safe caches
        self.package_cache: PackageSpecCache = TypedCache(
            max_size=package_cache_size,
            default_ttl=default_ttl * 6,  # Package specs change rarely
        )

        self.template_cache: TemplateCache = TypedCache(
            max_size=template_cache_size,
            default_ttl=default_ttl * 6,  # Template roots change rarely
        )

        self.compilation_cache: CompilationCache = TypedCache(
            max_size=compilation_cache_size,
            default_ttl=default_ttl * 2,  # Compiled templates may change
        )

        self.module_cache: ModuleCache = TypedCache(
            max_size=module_cache_size,
            default_ttl=default_ttl * 12,  # Modules change very rarely
        )

        self._default_ttl = default_ttl

    def clear_all(self) -> None:
        """Clear all caches."""
        self.package_cache.clear()
        self.template_cache.clear()
        self.compilation_cache.clear()
        self.module_cache.clear()

    def cleanup_expired(self) -> dict[str, int]:
        """Clean up expired entries from all caches.

        Returns:
            Dictionary with count of expired entries per cache
        """
        return {
            "package_cache": self.package_cache.cleanup_expired(),
            "template_cache": self.template_cache.cleanup_expired(),
            "compilation_cache": self.compilation_cache.cleanup_expired(),
            "module_cache": self.module_cache.cleanup_expired(),
        }

    def get_statistics(self) -> dict[str, dict[str, t.Any]]:
        """Get statistics for all caches.

        Returns:
            Dictionary with statistics for each cache
        """
        return {
            "package_cache": self.package_cache.get_statistics(),
            "template_cache": self.template_cache.get_statistics(),
            "compilation_cache": self.compilation_cache.get_statistics(),
            "module_cache": self.module_cache.get_statistics(),
        }

    def resize_caches(
        self,
        package_size: int | None = None,
        template_size: int | None = None,
        compilation_size: int | None = None,
        module_size: int | None = None,
    ) -> None:
        """Resize cache maximum sizes.

        Args:
            package_size: New size for package cache (None to keep current)
            template_size: New size for template cache (None to keep current)
            compilation_size: New size for compilation cache (None to keep current)
            module_size: New size for module cache (None to keep current)
        """
        if package_size is not None:
            self.package_cache.resize(package_size)
        if template_size is not None:
            self.template_cache.resize(template_size)
        if compilation_size is not None:
            self.compilation_cache.resize(compilation_size)
        if module_size is not None:
            self.module_cache.resize(module_size)

    @classmethod
    def get_default(cls) -> "CacheManager":
        """Get the default global cache manager instance.

        This provides backward compatibility while allowing dependency injection.

        Returns:
            Default cache manager instance
        """
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def set_default(cls, manager: "CacheManager") -> None:
        """Set a new default cache manager instance.

        Args:
            manager: New cache manager to use as default
        """
        cls._default_instance = manager

    def create_scoped_manager(
        self,
        package_ttl: int | None = None,
        template_ttl: int | None = None,
        compilation_ttl: int | None = None,
        module_ttl: int | None = None,
    ) -> "CacheManager":
        """Create a new cache manager with different TTL settings.

        Useful for creating isolated cache environments for testing
        or different application contexts.

        Args:
            package_ttl: TTL for package cache (None to use default)
            template_ttl: TTL for template cache (None to use default)
            compilation_ttl: TTL for compilation cache (None to use default)
            module_ttl: TTL for module cache (None to use default)

        Returns:
            New cache manager with specified TTL settings
        """
        # Use current cache sizes for the scoped manager
        stats = self.get_statistics()

        manager = CacheManager(
            package_cache_size=stats["package_cache"]["max_size"],
            template_cache_size=stats["template_cache"]["max_size"],
            compilation_cache_size=stats["compilation_cache"]["max_size"],
            module_cache_size=stats["module_cache"]["max_size"],
            default_ttl=self._default_ttl,
        )

        # Override specific TTLs if provided
        if package_ttl is not None:
            manager.package_cache._default_ttl = package_ttl
        if template_ttl is not None:
            manager.template_cache._default_ttl = template_ttl
        if compilation_ttl is not None:
            manager.compilation_cache._default_ttl = compilation_ttl
        if module_ttl is not None:
            manager.module_cache._default_ttl = module_ttl

        return manager

    def get_memory_usage_estimate(self) -> dict[str, int]:
        """Get rough memory usage estimates for all caches.

        Returns:
            Dictionary with estimated memory usage per cache in bytes
        """
        # Rough estimates based on typical object sizes
        AVERAGE_SIZES = {
            "package_spec": 200,  # Loader + spec objects
            "template_root": 100,  # Path objects
            "compilation": 5000,  # Compiled template code
            "module": 1000,  # Module objects
        }

        stats = self.get_statistics()

        memory_usage = {}
        for cache_name in (
            "package_cache",
            "template_cache",
            "compilation_cache",
            "module_cache",
        ):
            cache_stats = stats.get(cache_name, {})
            if "size" in cache_stats:
                size = cache_stats["size"]
            else:
                # Handle hierarchical cache which might not have direct size
                size_obj = getattr(self, cache_name, None)
                if size_obj and hasattr(size_obj, "__len__"):
                    size = len(size_obj)
                else:
                    size = 0

            avg_size = AVERAGE_SIZES.get(cache_name.replace("_cache", ""), 100)
            memory_usage[cache_name] = size * avg_size

        return memory_usage

    def get(self, cache_type: str, key: str) -> t.Any:
        """Get value from specified cache.

        Args:
            cache_type: Type of cache ('package', 'template', 'compilation', 'module')
            key: Cache key

        Returns:
            Cached value or None if not found

        Raises:
            ValueError: If cache_type is not recognized
        """
        cache_map = {
            "package": self.package_cache,
            "template": self.template_cache,
            "compilation": self.compilation_cache,
            "module": self.module_cache,
        }

        if cache_type not in cache_map:
            raise ValueError(f"Unknown cache type: {cache_type}")

        return cache_map[cache_type].get(key)

    def set(
        self, cache_type: str, key: str, value: t.Any, ttl: int | None = None
    ) -> None:
        """Set value in specified cache.

        Args:
            cache_type: Type of cache ('package', 'template', 'compilation', 'module')
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (uses cache default if None)

        Raises:
            ValueError: If cache_type is not recognized
        """
        cache_map = {
            "package": self.package_cache,
            "template": self.template_cache,
            "compilation": self.compilation_cache,
            "module": self.module_cache,
        }

        if cache_type not in cache_map:
            raise ValueError(f"Unknown cache type: {cache_type}")

        cache_map[cache_type].set(key, value, ttl)

    def delete(self, cache_type: str, key: str) -> bool:
        """Delete value from specified cache.

        Args:
            cache_type: Type of cache ('package', 'template', 'compilation', 'module')
            key: Cache key

        Returns:
            True if key was deleted, False if not found

        Raises:
            ValueError: If cache_type is not recognized
        """
        cache_map = {
            "package": self.package_cache,
            "template": self.template_cache,
            "compilation": self.compilation_cache,
            "module": self.module_cache,
        }

        if cache_type not in cache_map:
            raise ValueError(f"Unknown cache type: {cache_type}")

        return cache_map[cache_type].delete(key)

    def create_cache_warmer(self) -> CacheWarmer:
        """Create a cache warmer for this cache manager.

        Returns:
            CacheWarmer instance for preloading caches
        """
        return CacheWarmer(self)

    def __repr__(self) -> str:
        """String representation of cache manager."""
        stats = self.get_statistics()
        total_size = sum(cache["size"] for cache in stats.values())
        return f"CacheManager(total_entries={total_size}, caches=4)"


class AdvancedCacheManager(CacheManager):
    """Enhanced cache manager with advanced strategies and monitoring."""

    # Override template_cache type to accommodate HierarchicalCache
    template_cache: "TemplateCache"

    def __init__(
        self,
        strategy: str = "adaptive",  # "lru", "lfu", "adaptive", "hierarchical"
        package_cache_size: int = 500,
        template_cache_size: int = 1000,
        compilation_cache_size: int = 2000,
        module_cache_size: int = 200,
        default_ttl: int = 300,
        enable_hierarchical: bool = False,
        l1_cache_size: int = 100,
    ):
        """Initialize advanced cache manager.

        Args:
            strategy: Cache strategy to use ("lru", "lfu", "adaptive", "hierarchical")
            package_cache_size: Size for package cache
            template_cache_size: Size for template cache
            compilation_cache_size: Size for compilation cache
            module_cache_size: Size for module cache
            default_ttl: Default TTL in seconds
            enable_hierarchical: Enable hierarchical caching for templates
            l1_cache_size: L1 cache size for hierarchical mode
        """
        # Don't call super().__init__() - we'll create our own caches
        self._strategy = strategy
        self._enable_hierarchical = enable_hierarchical
        self._default_ttl = default_ttl

        # Create caches based on strategy
        self._create_caches(
            strategy,
            package_cache_size,
            template_cache_size,
            compilation_cache_size,
            module_cache_size,
            default_ttl,
            l1_cache_size,
        )

    def _create_caches(
        self,
        strategy: str,
        package_size: int,
        template_size: int,
        compilation_size: int,
        module_size: int,
        ttl: int,
        l1_size: int,
    ) -> None:
        """Create caches with specified strategy."""
        cache_factory: dict[str, t.Callable[[int, int], TypedCache[t.Any]]] = {
            "lru": lambda size, ttl: TypedCache(max_size=size, default_ttl=ttl),
            "lfu": lambda size, ttl: LFUCache(max_size=size, default_ttl=ttl),
            "adaptive": lambda size, ttl: AdaptiveCache(max_size=size, default_ttl=ttl),
        }

        factory = cache_factory.get(strategy, cache_factory["lru"])

        # Create standard caches
        self.package_cache = factory(package_size, ttl * 6)
        self.compilation_cache = factory(compilation_size, ttl * 2)
        self.module_cache = factory(module_size, ttl * 12)

        # Create template cache (potentially hierarchical)
        if self._enable_hierarchical:
            self.template_cache = HierarchicalCache(
                l1_size=l1_size, l2_size=template_size, l1_ttl=ttl, l2_ttl=ttl * 6
            )
        else:
            self.template_cache = factory(template_size, ttl * 6)

    def get_extended_statistics(self) -> dict[str, t.Any]:
        """Get extended statistics for all caches."""
        stats = self.get_statistics()

        # Add strategy-specific statistics
        extended_stats: dict[str, t.Any] = {
            "strategy": self._strategy,
            "hierarchical_enabled": self._enable_hierarchical,
            "base_stats": stats,
        }

        # Get advanced statistics from caches that support it
        for cache_name, cache in (
            ("package_cache", self.package_cache),
            ("template_cache", self.template_cache),
            ("compilation_cache", self.compilation_cache),
            ("module_cache", self.module_cache),
        ):
            # Only call methods on objects that actually have them
            # Use getattr with default to avoid type checking issues
            get_extended_stats = getattr(cache, "get_extended_statistics", None)
            if callable(get_extended_stats):
                with suppress(Exception):
                    extended_stats[f"{cache_name}_extended"] = get_extended_stats()

            get_strategy_info = getattr(cache, "get_strategy_info", None)
            if callable(get_strategy_info):
                with suppress(Exception):
                    extended_stats[f"{cache_name}_strategy"] = get_strategy_info()

        return extended_stats

    def optimize_caches(self) -> dict[str, t.Any]:
        """Perform cache optimization and return results.

        Returns:
            Dictionary with optimization results
        """
        results: dict[str, t.Any] = {}

        # Cleanup expired entries
        cleanup_results = self.cleanup_expired()
        results["cleanup"] = cleanup_results

        # Trigger strategy evaluation for adaptive caches
        for cache_name, cache in (
            ("package_cache", self.package_cache),
            ("template_cache", self.template_cache),
            ("compilation_cache", self.compilation_cache),
            ("module_cache", self.module_cache),
        ):
            if isinstance(cache, AdaptiveCache) and hasattr(
                cache, "_evaluate_strategy"
            ):
                old_strategy = getattr(cache, "_strategy", "unknown")
                cache._evaluate_strategy()
                new_strategy = getattr(cache, "_strategy", "unknown")
                results[f"{cache_name}_strategy_change"] = {
                    "old": old_strategy,
                    "new": new_strategy,
                    "changed": old_strategy != new_strategy,
                }

        return results

    def get_memory_efficiency_report(self) -> dict[str, t.Any]:
        """Generate detailed memory efficiency report."""
        stats = self.get_extended_statistics()
        memory_usage = self.get_memory_usage_estimate()

        total_memory = sum(memory_usage.values())
        total_entries = sum(cache["size"] for cache in stats["base_stats"].values())

        # Calculate efficiency metrics
        efficiency_report: dict[str, t.Any] = {
            "total_memory_bytes": total_memory,
            "total_entries": total_entries,
            "avg_memory_per_entry": total_memory / total_entries
            if total_entries > 0
            else 0,
            "memory_by_cache": memory_usage,
            "cache_utilization": {},
            "recommendations": [],
        }

        # Calculate utilization per cache
        for cache_name, cache_stats in stats["base_stats"].items():
            utilization = cache_stats["fill_ratio"]
            efficiency_report["cache_utilization"][cache_name] = {
                "fill_ratio": utilization,
                "hit_rate": cache_stats["hit_rate"],
                "efficiency_score": utilization * cache_stats["hit_rate"],
            }

            # Generate recommendations
            if utilization < 0.3 and cache_stats["size"] > 0:
                efficiency_report["recommendations"].append(
                    f"Consider reducing {cache_name} size (low utilization: {utilization:.1%})"
                )
            elif utilization > 0.9:
                efficiency_report["recommendations"].append(
                    f"Consider increasing {cache_name} size (high utilization: {utilization:.1%})"
                )

            if cache_stats["hit_rate"] < 0.5 and cache_stats["size"] > 0:
                efficiency_report["recommendations"].append(
                    f"Consider tuning {cache_name} TTL (low hit rate: {cache_stats['hit_rate']:.1%})"
                )

        return efficiency_report
