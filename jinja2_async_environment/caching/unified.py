"""Unified cache implementation for backward compatibility.

This module provides the UnifiedCache class that maintains compatibility
with the existing cache interface while leveraging the new type-safe
caching infrastructure.
"""

import typing as t
from threading import RLock

from .typed import TypedCache


class UnifiedCache:
    """Unified cache system for backward compatibility.

    This cache maintains the existing API while internally using
    the new type-safe cache infrastructure. It will be gradually
    phased out in favor of the CacheManager approach.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """Initialize the unified cache.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        # Internal type-safe caches - using Any for backward compatibility
        template_ttl = default_ttl * 6
        import_ttl = default_ttl * 12

        self._caches: dict[str, TypedCache[t.Any]] = {
            "package_import": TypedCache(max_size=200)
            if import_ttl == 300
            else TypedCache(max_size=200, default_ttl=import_ttl),
            "package_spec": TypedCache(max_size=500)
            if template_ttl == 300
            else TypedCache(max_size=500, default_ttl=template_ttl),
            "template_root": TypedCache(max_size=1000)
            if template_ttl == 300
            else TypedCache(max_size=1000, default_ttl=template_ttl),
        }

        self._default_ttl = default_ttl
        self._lock = RLock()

    def get(self, cache_type: str, key: t.Any, default: t.Any = None) -> t.Any:
        """Get a value from the specified cache.

        Args:
            cache_type: Type of cache ("package_import", "package_spec", "template_root")
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        with self._lock:
            if cache_type not in self._caches:
                return default

            # Convert key to string for internal cache
            str_key = str(key) if not isinstance(key, str) else key

            value = self._caches[cache_type].get(str_key)
            return value if value is not None else default

    def set(
        self, cache_type: str, key: t.Any, value: t.Any, ttl: int | None = None
    ) -> None:
        """Store a value in the specified cache.

        Args:
            cache_type: Type of cache
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            if cache_type not in self._caches:
                # Dynamically create cache for unknown types
                cache_params = {"max_size": 1000}
                if ttl is not None or self._default_ttl != 300:
                    cache_params["default_ttl"] = ttl or self._default_ttl
                self._caches[cache_type] = TypedCache(**cache_params)

            # Convert key to string for internal cache
            str_key = str(key) if not isinstance(key, str) else key

            self._caches[cache_type].set(str_key, value, ttl or None)

    def clear(self, cache_type: str | None = None) -> None:
        """Clear cache entries.

        Args:
            cache_type: Specific cache to clear (None for all caches)
        """
        with self._lock:
            if cache_type is None:
                # Clear all caches
                for cache in self._caches.values():
                    cache.clear()
            elif cache_type in self._caches:
                self._caches[cache_type].clear()

    def clear_all(self) -> None:
        """Clear all cache entries."""
        self.clear()

    def cleanup_expired(self) -> None:
        """Remove expired entries from all caches."""
        with self._lock:
            for cache in self._caches.values():
                cache.cleanup_expired()

    def get_statistics(self) -> dict[str, dict[str, t.Any]]:
        """Get statistics for all caches.

        Returns:
            Dictionary with statistics for each cache type
        """
        with self._lock:
            stats = {}
            for cache_type, cache in self._caches.items():
                stats[cache_type] = cache.get_statistics()
            return stats

    def _is_valid(self, cache_type: str, key: t.Any) -> bool:
        """Check if a cache entry is valid (exists and not expired).

        Args:
            cache_type: Type of cache
            key: Cache key

        Returns:
            True if entry is valid, False otherwise
        """
        with self._lock:
            if cache_type not in self._caches:
                return False

            str_key = str(key) if not isinstance(key, str) else key
            return self._caches[cache_type].contains(str_key)

    def resize_cache(self, cache_type: str, new_size: int) -> None:
        """Resize a specific cache.

        Args:
            cache_type: Type of cache to resize
            new_size: New maximum size
        """
        with self._lock:
            if cache_type in self._caches:
                self._caches[cache_type].resize(new_size)

    def get_cache_types(self) -> list[str]:
        """Get list of available cache types.

        Returns:
            List of cache type names
        """
        with self._lock:
            return list(self._caches.keys())

    def contains(self, cache_type: str, key: t.Any) -> bool:
        """Check if a key exists in the specified cache.

        Args:
            cache_type: Type of cache
            key: Cache key

        Returns:
            True if key exists and is valid, False otherwise
        """
        return self._is_valid(cache_type, key)

    def __len__(self) -> int:
        """Get total number of entries across all caches."""
        with self._lock:
            return sum(len(cache) for cache in self._caches.values())

    def __repr__(self) -> str:
        """String representation of unified cache."""
        with self._lock:
            total_entries = len(self)
            return f"UnifiedCache(types={len(self._caches)}, entries={total_entries})"


# Backward compatibility function
# def _clear_expired_cache() -> None:
#     """Clear expired cache entries (backward compatibility function)."""
#     # This will be connected to the global unified cache instance
#     # when it's available through the loader context
#     pass
