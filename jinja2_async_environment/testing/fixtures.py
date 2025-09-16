"""Test fixtures and utilities for jinja2-async-environment testing."""

import typing as t

CacheManager: t.Any = None
AsyncEnvironment: t.Any = None

try:
    from ..caching import CacheManager
except ImportError:
    # Fallback during refactoring
    pass

try:
    from ..environment import AsyncEnvironment
except ImportError:
    # Fallback during refactoring
    pass


def create_test_cache_manager(
    smaller_caches: bool = True, short_ttl: bool = True
) -> CacheManager:
    """Create a cache manager optimized for testing.

    Args:
        smaller_caches: Use smaller cache sizes for testing
        short_ttl: Use shorter TTL values for testing

    Returns:
        CacheManager configured for testing
    """
    if smaller_caches:
        # Smaller caches for faster tests
        package_size = 50
        template_size = 100
        compilation_size = 200
        module_size = 20
    else:
        # Standard sizes
        package_size = 500
        template_size = 1000
        compilation_size = 2000
        module_size = 200

    if short_ttl:
        # Short TTL for testing cache expiration
        default_ttl = 5
    else:
        # Standard TTL
        default_ttl = 300

    return CacheManager(
        package_cache_size=package_size,
        template_cache_size=template_size,
        compilation_cache_size=compilation_size,
        module_cache_size=module_size,
        default_ttl=default_ttl,
    )


def create_test_environment(
    cache_manager: "CacheManager | None" = None, **kwargs: t.Any
) -> AsyncEnvironment:
    """Create an AsyncEnvironment configured for testing.

    Args:
        cache_manager: Cache manager to use (creates test one if None)
        **kwargs: Additional arguments for AsyncEnvironment

    Returns:
        AsyncEnvironment configured for testing
    """
    if cache_manager is None:
        cache_manager = create_test_cache_manager()

    # Set testing-friendly defaults
    test_defaults = {
        "cache_size": 100,  # Smaller cache for tests
        "auto_reload": True,  # Enable auto-reload for test changes
    }

    # Merge with provided kwargs
    test_defaults.update(kwargs)

    # Add cache manager if the environment supports it
    # Note: This will be implemented in Phase 2
    return AsyncEnvironment(**test_defaults)


def clear_all_test_caches() -> None:
    """Clear all caches that might be used during testing.

    This is useful for ensuring test isolation.
    """
    # Clear default cache manager
    default_manager = CacheManager.get_default()
    default_manager.clear_all()

    # Clear any global unified cache if it exists
    try:
        from ..loaders import _unified_cache

        _unified_cache.clear_all()
    except (ImportError, AttributeError):
        pass


def get_cache_statistics() -> dict[str, t.Any]:
    """Get cache statistics for test verification.

    Returns:
        Dictionary with cache statistics
    """
    try:
        default_manager = CacheManager.get_default()
        return default_manager.get_statistics()
    except Exception:
        return {"error": "Could not retrieve cache statistics"}


# Type alias for the base class
if t.TYPE_CHECKING:
    _BaseClass = CacheManager if CacheManager is not None else object
else:
    _BaseClass = CacheManager if CacheManager is not None else object


class TestCacheManager(_BaseClass):  # type: ignore
    """Cache manager with additional testing utilities."""

    def __init__(self, *args: t.Any, **kwargs: t.Any):
        """Initialize test cache manager with test-friendly defaults."""
        # Override defaults for testing
        test_kwargs = {
            "package_cache_size": 50,
            "template_cache_size": 100,
            "compilation_cache_size": 200,
            "module_cache_size": 20,
            "default_ttl": 5,
        }
        test_kwargs.update(kwargs)
        super().__init__(*args, **test_kwargs)

        # Track operations for testing
        self._operation_log: list[str] = []

    def get(self, cache_type: str, key: str) -> t.Any:
        """Get with operation logging."""
        self._operation_log.append(f"get:{cache_type}:{key}")
        return super().get(cache_type, key)

    def set(
        self, cache_type: str, key: str, value: t.Any, ttl: int | None = None
    ) -> None:
        """Set with operation logging."""
        self._operation_log.append(f"set:{cache_type}:{key}")
        super().set(cache_type, key, value, ttl)

    def get_operation_log(self) -> list[str]:
        """Get log of cache operations for test verification."""
        return list(self._operation_log)

    def clear_operation_log(self) -> None:
        """Clear the operation log."""
        self._operation_log.clear()
