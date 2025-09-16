"""Type-safe cache implementation with generic support."""

import time
import typing as t
from dataclasses import dataclass
from threading import RLock

T = t.TypeVar("T")


@dataclass
class CacheEntry[T]:
    """Cache entry with value, timestamp, and TTL information."""

    value: T
    timestamp: float
    ttl: int
    access_count: int = 0
    last_access: float = 0.0


class TypedCache[T]:
    """Type-safe cache with TTL, LRU eviction, and memory management.

    This cache provides:
    - Type safety through generics
    - TTL-based expiration
    - LRU eviction when cache is full
    - Thread-safe operations
    - Memory usage tracking
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """Initialize the typed cache.

        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default time-to-live in seconds
        """
        self._cache: dict[str, CacheEntry[T]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._access_order: list[str] = []
        self._lock = RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> T | None:
        """Get value from cache with TTL and LRU tracking.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]
            current_time = time.time()

            # Check TTL
            if current_time - entry.timestamp > entry.ttl:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._misses += 1
                return None

            # Update access tracking
            entry.access_count += 1
            entry.last_access = current_time

            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            self._hits += 1
            return entry.value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Store value in cache with automatic eviction.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            current_time = time.time()

            # Check if we need to evict entries
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()

            # Create cache entry
            entry = CacheEntry(
                value=value,
                timestamp=current_time,
                ttl=ttl or self._default_ttl,
                access_count=1,
                last_access=current_time,
            )

            self._cache[key] = entry

            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def _evict_lru(self) -> None:
        """Evict least recently used entries to make space."""
        # Evict 25% of entries to avoid frequent evictions
        evict_count = max(1, self._max_size // 4)

        for _ in range(min(evict_count, len(self._access_order))):
            if self._access_order:
                lru_key = self._access_order.pop(0)
                if lru_key in self._cache:
                    del self._cache[lru_key]
                    self._evictions += 1

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, entry in self._cache.items():
                if current_time - entry.timestamp > entry.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

            return len(expired_keys)

    def get_statistics(self) -> dict[str, t.Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": hit_rate,
                "fill_ratio": len(self._cache) / self._max_size,
            }

    def resize(self, new_max_size: int) -> None:
        """Resize the cache maximum size.

        Args:
            new_max_size: New maximum size for the cache
        """
        with self._lock:
            self._max_size = new_max_size

            # If new size is smaller, evict excess entries
            if new_max_size < len(self._cache):
                excess = len(self._cache) - new_max_size
                for _ in range(excess):
                    if self._access_order:
                        lru_key = self._access_order.pop(0)
                        if lru_key in self._cache:
                            del self._cache[lru_key]
                            self._evictions += 1

    def contains(self, key: str) -> bool:
        """Check if key exists in cache (without updating access).

        Args:
            key: Cache key to check

        Returns:
            True if key exists and not expired, False otherwise
        """
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            current_time = time.time()

            # Check TTL without updating access
            if current_time - entry.timestamp > entry.ttl:
                return False

            return True

    def keys(self) -> list[str]:
        """Get all valid (non-expired) keys.

        Returns:
            List of valid cache keys
        """
        with self._lock:
            current_time = time.time()
            valid_keys = []

            for key, entry in self._cache.items():
                if current_time - entry.timestamp <= entry.ttl:
                    valid_keys.append(key)

            return valid_keys

    def __len__(self) -> int:
        """Get number of entries in cache."""
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Check if key is in cache (supports 'in' operator)."""
        return self.contains(key)
