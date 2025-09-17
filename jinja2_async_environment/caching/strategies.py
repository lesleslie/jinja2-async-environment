"""Advanced cache strategies and eviction policies."""

import time
import typing as t
from dataclasses import dataclass
from threading import RLock

from .typed import CacheEntry, TypedCache

T = t.TypeVar("T")


@dataclass
class CacheStatistics:
    """Extended cache statistics for monitoring and optimization."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_pressure_evictions: int = 0
    ttl_evictions: int = 0
    avg_access_time: float = 0.0
    peak_size: int = 0
    cache_efficiency: float = 0.0


class LFUCache(TypedCache[T]):
    """Least Frequently Used cache with advanced statistics."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        super().__init__(max_size, default_ttl)
        self._access_counts: dict[str, int] = {}
        self._statistics = CacheStatistics()

    def get(self, key: str) -> T | None:
        with self._lock:
            start_time = time.time()

            if key not in self._cache:
                self._statistics.misses += 1
                return None

            entry = self._cache[key]
            current_time = time.time()

            # Check TTL
            if current_time - entry.timestamp > entry.ttl:
                del self._cache[key]
                self._access_counts.pop(key, None)
                if key in self._access_order:
                    self._access_order.remove(key)
                self._statistics.misses += 1
                self._statistics.ttl_evictions += 1
                return None

            # Update LFU tracking
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
            entry.access_count += 1
            entry.last_access = current_time

            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            self._statistics.hits += 1
            access_time = time.time() - start_time
            self._update_avg_access_time(access_time)

            return entry.value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        with self._lock:
            current_time = time.time()

            # Evict if needed
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lfu()

            # Create entry
            entry = CacheEntry(
                value=value,
                timestamp=current_time,
                ttl=ttl or self._default_ttl,
                access_count=1,
                last_access=current_time,
            )

            self._cache[key] = entry
            self._access_counts[key] = 1

            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            # Update statistics
            if len(self._cache) > self._statistics.peak_size:
                self._statistics.peak_size = len(self._cache)

    def _evict_lfu(self) -> None:
        """Evict least frequently used entries."""
        if not self._cache:
            return

        # Find LFU key
        lfu_key = min(self._access_counts.keys(), key=lambda k: self._access_counts[k])

        # Remove from all structures
        self._cache.pop(lfu_key, None)
        self._access_counts.pop(lfu_key, None)
        if lfu_key in self._access_order:
            self._access_order.remove(lfu_key)

        self._statistics.evictions += 1
        self._statistics.memory_pressure_evictions += 1

    def _update_avg_access_time(self, access_time: float) -> None:
        """Update running average of access times."""
        total_accesses = self._statistics.hits + self._statistics.misses
        if total_accesses == 1:
            self._statistics.avg_access_time = access_time
        else:
            # Exponential moving average
            alpha = 0.1
            self._statistics.avg_access_time = (
                alpha * access_time + (1 - alpha) * self._statistics.avg_access_time
            )

    def get_extended_statistics(self) -> dict[str, t.Any]:
        """Get extended statistics for monitoring."""
        base_stats = self.get_statistics()

        total_requests = self._statistics.hits + self._statistics.misses
        self._statistics.cache_efficiency = (
            self._statistics.hits / total_requests if total_requests > 0 else 0.0
        )

        return base_stats | {
            "access_counts": self._access_counts.copy(),
            "avg_access_time_ms": self._statistics.avg_access_time * 1000,
            "peak_size": self._statistics.peak_size,
            "cache_efficiency": self._statistics.cache_efficiency,
            "ttl_evictions": self._statistics.ttl_evictions,
            "memory_pressure_evictions": self._statistics.memory_pressure_evictions,
        }


class AdaptiveCache(TypedCache[T]):
    """Adaptive cache that switches between LRU and LFU based on access patterns."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        super().__init__(max_size, default_ttl)
        self._access_patterns: dict[str, list[float]] = {}
        self._strategy: str = "lru"  # "lru" or "lfu"
        self._strategy_switches = 0
        self._last_evaluation = time.time()
        self._evaluation_interval = 300  # 5 minutes

    def get(self, key: str) -> T | None:
        with self._lock:
            # Periodically evaluate and potentially switch strategy
            if time.time() - self._last_evaluation > self._evaluation_interval:
                self._evaluate_strategy()

            # Track access pattern
            current_time = time.time()
            if key not in self._access_patterns:
                self._access_patterns[key] = []
            self._access_patterns[key].append(current_time)

            # Keep only recent accesses (last hour)
            cutoff_time = current_time - 3600
            self._access_patterns[key] = [
                t for t in self._access_patterns[key] if t > cutoff_time
            ]

            return super().get(key)

    def _evaluate_strategy(self) -> None:
        """Evaluate access patterns and potentially switch strategy."""
        self._last_evaluation = time.time()

        if not self._access_patterns:
            return

        # Calculate access frequency distribution
        frequencies = [len(accesses) for accesses in self._access_patterns.values()]

        if not frequencies:
            return

        # Calculate coefficient of variation
        mean_freq = sum(frequencies) / len(frequencies)
        if mean_freq == 0:
            return

        variance = sum((f - mean_freq) ** 2 for f in frequencies) / len(frequencies)
        std_dev = variance**0.5
        cv = std_dev / mean_freq

        # Switch strategy based on access pattern uniformity
        # High CV (> 0.5) suggests some items are accessed much more frequently → LFU
        # Low CV (< 0.3) suggests relatively uniform access → LRU
        old_strategy = self._strategy
        if cv > 0.5 and self._strategy == "lru":
            self._strategy = "lfu"
            self._strategy_switches += 1
        elif cv < 0.3 and self._strategy == "lfu":
            self._strategy = "lru"
            self._strategy_switches += 1

        if old_strategy != self._strategy:
            # Clear old tracking data when switching
            self._access_patterns.clear()

    def _evict_lru(self) -> None:
        """Evict using current strategy."""
        if self._strategy == "lfu":
            self._evict_lfu_adaptive()
        else:
            super()._evict_lru()

    def _evict_lfu_adaptive(self) -> None:
        """Evict least frequently used entry."""
        if not self._access_patterns:
            super()._evict_lru()
            return

        # Find key with lowest access frequency
        lfu_key = min(
            self._access_patterns.keys(),
            key=lambda k: len(self._access_patterns.get(k, [])),
        )

        if lfu_key in self._cache:
            del self._cache[lfu_key]
            if lfu_key in self._access_order:
                self._access_order.remove(lfu_key)
            self._evictions += 1

        self._access_patterns.pop(lfu_key, None)

    def get_strategy_info(self) -> dict[str, t.Any]:
        """Get information about current strategy and switches."""
        return {
            "current_strategy": self._strategy,
            "strategy_switches": self._strategy_switches,
            "last_evaluation": self._last_evaluation,
            "access_pattern_keys": len(self._access_patterns),
        }


class HierarchicalCache[T]:
    """Multi-level cache with different strategies per level."""

    def __init__(
        self,
        l1_size: int = 100,
        l2_size: int = 1000,
        l1_ttl: int = 60,
        l2_ttl: int = 300,
    ):
        """Initialize hierarchical cache.

        Args:
            l1_size: Size of L1 (fastest) cache
            l2_size: Size of L2 (larger) cache
            l1_ttl: TTL for L1 cache entries
            l2_ttl: TTL for L2 cache entries
        """
        self.l1_cache = TypedCache[T](max_size=l1_size, default_ttl=l1_ttl)
        self.l2_cache = LFUCache[T](max_size=l2_size, default_ttl=l2_ttl)
        self._lock = RLock()

        # Statistics
        self.l1_hits = 0
        self.l2_hits = 0
        self.total_misses = 0
        self.promotions = 0  # L2 → L1 promotions

    @property
    def _default_ttl(self) -> int:
        """Get the default TTL for this cache."""
        return self.l2_cache._default_ttl

    @_default_ttl.setter
    def _default_ttl(self, value: int) -> None:
        """Set the default TTL for this cache."""
        self.l1_cache._default_ttl = value // 5  # L1 TTL is 1/5 of L2
        self.l2_cache._default_ttl = value

    def get(self, key: str) -> T | None:
        """Get value from hierarchical cache."""
        with self._lock:
            # Try L1 first
            value = self.l1_cache.get(key)
            if value is not None:
                self.l1_hits += 1
                return value

            # Try L2
            value = self.l2_cache.get(key)
            if value is not None:
                self.l2_hits += 1
                # Promote frequently accessed items to L1
                self._consider_promotion(key, value)
                return value

            # Miss in both levels
            self.total_misses += 1
            return None

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Set value in hierarchical cache."""
        with self._lock:
            # Always start in L2, promote to L1 based on access patterns
            self.l2_cache.set(key, value, ttl)

    def _consider_promotion(self, key: str, value: T) -> None:
        """Consider promoting item from L2 to L1."""
        # Get access count from L2
        l2_entry = self.l2_cache._cache.get(key)
        if l2_entry and l2_entry.access_count >= 3:  # Promote after 3 accesses
            # Promote to L1
            self.l1_cache.set(key, value, l2_entry.ttl)
            self.promotions += 1

    def clear(self) -> None:
        """Clear all cache levels."""
        with self._lock:
            self.l1_cache.clear()
            self.l2_cache.clear()
            self.l1_hits = 0
            self.l2_hits = 0
            self.total_misses = 0
            self.promotions = 0

    def cleanup_expired(self) -> int:
        """Clean up expired entries from both cache levels.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            l1_expired = self.l1_cache.cleanup_expired()
            l2_expired = self.l2_cache.cleanup_expired()
            return l1_expired + l2_expired

    def resize(self, new_max_size: int) -> None:
        """Resize the cache maximum size.

        For hierarchical cache, we split the size between L1 and L2.

        Args:
            new_max_size: New maximum size for the cache
        """
        with self._lock:
            # Split size between L1 and L2 (80% to L2, 20% to L1)
            l1_size = max(1, new_max_size // 5)
            l2_size = new_max_size - l1_size
            self.l1_cache.resize(l1_size)
            self.l2_cache.resize(l2_size)

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            # Try to delete from both caches
            l1_deleted = self.l1_cache.delete(key)
            l2_deleted = self.l2_cache.delete(key)
            return l1_deleted or l2_deleted

    def get_statistics(self) -> dict[str, t.Any]:
        """Get comprehensive statistics for all cache levels."""
        total_requests = self.l1_hits + self.l2_hits + self.total_misses

        return {
            "l1_cache": self.l1_cache.get_statistics(),
            "l2_cache": self.l2_cache.get_extended_statistics(),
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "total_misses": self.total_misses,
            "promotions": self.promotions,
            "overall_hit_rate": (
                (self.l1_hits + self.l2_hits) / total_requests
                if total_requests > 0
                else 0.0
            ),
            "l1_hit_rate": (
                self.l1_hits / total_requests if total_requests > 0 else 0.0
            ),
            "size": len(self.l1_cache) + len(self.l2_cache),
            "max_size": self.l1_cache._max_size + self.l2_cache._max_size,
            "hits": self.l1_hits + self.l2_hits,
            "misses": self.total_misses,
            "evictions": self.l1_cache._evictions + self.l2_cache._evictions,
            "hit_rate": (
                (self.l1_hits + self.l2_hits) / total_requests
                if total_requests > 0
                else 0.0
            ),
            "fill_ratio": (
                (len(self.l1_cache) + len(self.l2_cache))
                / (self.l1_cache._max_size + self.l2_cache._max_size)
            ),
        }

    def __len__(self) -> int:
        """Get total number of entries across all cache levels."""
        return len(self.l1_cache) + len(self.l2_cache)


class CacheWarmer:
    """Utility for warming caches with commonly used templates."""

    def __init__(self, cache_manager: t.Any):
        """Initialize cache warmer.

        Args:
            cache_manager: Cache manager to warm
        """
        self.cache_manager = cache_manager
        self._warmed_keys: set[str] = set()

    async def warm_template_cache(
        self,
        environment: t.Any,
        template_names: list[str],
        context_data: dict[str, t.Any] | None = None,
    ) -> dict[str, bool]:
        """Warm template cache by pre-loading common templates.

        Args:
            environment: AsyncEnvironment instance
            template_names: List of template names to warm
            context_data: Optional context data for compilation

        Returns:
            Dictionary mapping template names to success status
        """
        results = {}
        context_data = context_data or {}

        for template_name in template_names:
            try:
                # Pre-load template to warm the cache
                template = await environment.get_template_async(template_name)

                # Also warm compilation cache if context provided
                if context_data:
                    await template.render_async(**context_data)

                self._warmed_keys.add(template_name)
                results[template_name] = True

            except Exception:
                results[template_name] = False

        return results

    def warm_package_cache(self, package_names: list[str]) -> dict[str, bool]:
        """Warm package cache by pre-loading package specs.

        Args:
            package_names: List of package names to warm

        Returns:
            Dictionary mapping package names to success status
        """
        results = {}

        for package_name in package_names:
            try:
                import importlib.util

                spec = importlib.util.find_spec(package_name)
                if spec and spec.loader:
                    # Cache the package spec
                    cache_key = f"spec:{package_name}"
                    self.cache_manager.set("package", cache_key, (spec.loader, spec))
                    self._warmed_keys.add(cache_key)
                    results[package_name] = True
                else:
                    results[package_name] = False

            except Exception:
                results[package_name] = False

        return results

    def get_warmed_keys(self) -> set[str]:
        """Get set of keys that have been warmed."""
        return self._warmed_keys.copy()

    def clear_warmed_tracking(self) -> None:
        """Clear the tracking of warmed keys."""
        self._warmed_keys.clear()
