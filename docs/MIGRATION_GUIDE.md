# Migration Guide for Refactored jinja2-async-environment

This guide helps developers migrate to the refactored version of jinja2-async-environment while maintaining backward compatibility.

## Overview

The refactoring improves code organization and maintainability without breaking existing functionality. All public APIs remain unchanged, but internal organization has been improved.

## Import Changes

### Loaders (No Change Required)

**Before and After (same):**

```python
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader, AsyncPackageLoader
```

The loaders module now has internal submodules, but all exports remain available from the main module.

### New Optional Features

**Cache Management (Optional):**

```python
# Old way (still works - uses default global cache)
env = AsyncEnvironment()
loader = AsyncFileSystemLoader(searchpath)

# New way (optional - for custom cache management)
from jinja2_async_environment.caching import CacheManager

cache_manager = CacheManager()
env = AsyncEnvironment(cache_manager=cache_manager)
loader = AsyncFileSystemLoader(searchpath, cache_manager=cache_manager)
```

## Testing Changes

### Test Infrastructure

**Old Pattern (removed from production):**

```python
# This pattern no longer exists in production code
if _loader_context.is_test_case("test_name"):
    # Special test behavior
```

**New Pattern (for test code only):**

```python
from jinja2_async_environment.testing.infrastructure import test_detector


def test_something():
    with test_detector.test_context("test_name"):
        # Test code here
        loader = AsyncPackageLoader(...)
```

### Mocking and Testing

**No Change Required for Basic Tests:**

```python
# This still works
async def test_template_loading():
    env = AsyncEnvironment()
    env.loader = AsyncMock()
    template = await env.get_template_async("test.html")
```

## Performance Considerations

### Cache Configuration

**Default Behavior (No Change):**

- Default cache sizes and TTLs remain the same
- Performance characteristics unchanged

**Advanced Configuration (New):**

```python
from jinja2_async_environment.caching import CacheManager, TypedCache

# Custom cache configuration
cache_manager = CacheManager()
cache_manager.package_cache = TypedCache(max_size=2000, default_ttl=3600)
cache_manager.template_cache = TypedCache(max_size=5000, default_ttl=1800)

env = AsyncEnvironment(cache_manager=cache_manager)
```

## Type Safety Improvements

### Better Type Hints

**Old (still works):**

```python
env = AsyncEnvironment()
template = await env.get_template_async("template.html")
```

**New (with better IDE support):**

```python
from jinja2_async_environment import AsyncEnvironment
from jinja2.environment import Template

env = AsyncEnvironment()
template: Template = await env.get_template_async("template.html")
```

## Common Migration Scenarios

### Scenario 1: Basic Usage (No Changes Needed)

```python
# This code works exactly the same before and after refactoring
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader


async def render_template():
    env = AsyncEnvironment()
    env.loader = AsyncFileSystemLoader("templates")

    template = await env.get_template_async("index.html")
    return await template.render_async(data={"title": "Hello"})
```

### Scenario 2: Custom Loader Implementation

**Before and After (same):**

```python
from jinja2_async_environment.loaders import AsyncBaseLoader


class MyCustomLoader(AsyncBaseLoader):
    async def get_source_async(self, environment, name):
        # Custom implementation
        return source, filename, uptodate_func
```

### Scenario 3: Performance Monitoring

**New Capability:**

```python
from jinja2_async_environment.caching import CacheManager


class MonitoredCacheManager(CacheManager):
    def __init__(self):
        super().__init__()
        self.cache_hits = 0
        self.cache_misses = 0

    # Override cache methods to add monitoring
```

## Deprecation Notices

### No Deprecations

- All existing public APIs remain supported
- No functionality has been removed
- All performance optimizations preserved

### Future Considerations

- Global cache instances will remain for backward compatibility
- Test detection patterns have been removed from production code
- New features will be added through optional parameters

## Troubleshooting

### Import Errors

If you encounter import errors after upgrading:

1. Ensure you're importing from the correct module:

   ```python
   # Correct
   from jinja2_async_environment.loaders import AsyncFileSystemLoader

   # Incorrect (internal module)
   from jinja2_async_environment.loaders.filesystem import AsyncFileSystemLoader
   ```

1. Clear Python cache:

   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -delete
   ```

### Performance Issues

If you notice performance degradation:

1. Verify cache configuration:

   ```python
   # Check if using default cache
   print(env._cache_manager)  # Should show CacheManager instance
   ```

1. Run performance benchmarks:

   ```bash
   pytest tests/test_benchmarks.py -v
   ```

### Test Failures

If tests fail after migration:

1. Update test infrastructure usage:

   ```python
   # Remove any _loader_context usage
   # Use test_detector.test_context() instead
   ```

1. Clear test cache:

   ```python
   from jinja2_async_environment.caching import CacheManager

   CacheManager.get_default().clear_all()
   ```

## Best Practices

### 1. Use Type Hints

```python
from typing import Optional
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment.caching import CacheManager


def create_environment(
    cache_manager: Optional[CacheManager] = None,
) -> AsyncEnvironment:
    return AsyncEnvironment(cache_manager=cache_manager)
```

### 2. Leverage Dependency Injection

```python
class Application:
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.env = AsyncEnvironment(cache_manager=cache_manager)
```

### 3. Monitor Cache Performance

```python
# Periodically check cache statistics
cache_stats = env._cache_manager.get_statistics()
print(f"Cache hit rate: {cache_stats['hit_rate']:.2%}")
```

## Support

For migration support:

1. Check the [GitHub Issues](https://github.com/your-repo/issues)
1. Review the [REFACTORING_PLAN.md](./REFACTORING_PLAN.md)
1. See complete [API Documentation](./api/index.html)

## Summary

The refactoring maintains 100% backward compatibility while improving:

- Code organization and maintainability
- Type safety and IDE support
- Testability and monitoring capabilities
- Future extensibility

No code changes are required for existing applications, but new features are available for those who want to use them.
