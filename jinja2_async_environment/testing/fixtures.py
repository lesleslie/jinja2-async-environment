"""Testing fixtures for jinja2-async-environment."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from .context import TestContext, clear_test_context, set_test_name

# Aliases for backward compatibility
LoaderContext = TestContext


class UnifiedCache:
    """Unified cache for backward compatibility."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def clear_all(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = value


# Global unified cache instance
_unified_cache = UnifiedCache()


def _clear_expired_cache() -> None:
    """Clear expired cache entries (backward compatibility)."""
    pass


@contextmanager
def isolated_test_context(test_name: str) -> Generator[None]:
    """Context manager for isolated test execution with proper cleanup."""
    import gc

    # Set test context
    set_test_name(test_name)

    # Force garbage collection to clear any lingering references
    gc.collect()

    try:
        yield
    finally:
        # Always cleanup after test
        clear_test_context()
        # Force garbage collection after test
        gc.collect()


# Backward compatibility exports
_loader_context = None
set_test_context = set_test_name


__all__ = [
    "isolated_test_context",
    "LoaderContext",
    "TestContext",
    "UnifiedCache",
    "_loader_context",
    "_unified_cache",
    "_clear_expired_cache",
    "set_test_context",
    "clear_test_context",
]
