"""Compilation cache for template code optimization."""

import hashlib


class CompilationCache:
    """Cache for compiled template code to avoid recompilation."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: dict[str, str] = {}

    def get_cache_key(self, source: str, environment_id: str) -> str:
        """Generate a cache key for template source and environment."""
        content = f"{source}:{environment_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, cache_key: str) -> str | None:
        """Get compiled code from cache."""
        return self._cache.get(cache_key)

    def set(self, cache_key: str, compiled_code: str) -> None:
        """Store compiled code in cache with size limit."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self._cache.keys())[: self.max_size // 4]
            for key in oldest_keys:
                del self._cache[key]

        self._cache[cache_key] = compiled_code

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
