# Comprehensive Refactoring Plan for jinja2-async-environment

## Executive Summary

This refactoring plan addresses critical architectural issues identified in the code review while preserving all existing functionality and performance optimizations. The plan is structured in 6 phases with clear deliverables, testing strategies, and rollback procedures.

**Key Principles:**

- Maintain 100% backward compatibility
- Preserve all performance optimizations (300-1,200x improvements)
- Improve maintainability without sacrificing functionality
- Enable future scalability and extensibility

## Phase 1: Architectural Restructuring (2-3 weeks)

### Goal: Split monolithic modules into focused, single-responsibility components

### 1.1 Loader Module Restructuring

**Current State:** `loaders.py` (920 LOC) mixing loaders, caching, and test infrastructure

**Target Structure:**

```
jinja2_async_environment/
├── loaders/
│   ├── __init__.py          # Export public API (maintains compatibility)
│   ├── base.py              # AsyncBaseLoader, AsyncLoaderProtocol
│   ├── filesystem.py        # AsyncFileSystemLoader
│   ├── package.py           # AsyncPackageLoader
│   ├── dict.py              # AsyncDictLoader
│   ├── function.py          # AsyncFunctionLoader
│   └── choice.py            # AsyncChoiceLoader
├── caching/
│   ├── __init__.py
│   ├── unified.py           # UnifiedCache (refactored)
│   ├── bytecode.py          # AsyncBytecodeCache (existing)
│   └── compilation.py       # CompilationCache (from compiler.py)
├── testing/
│   ├── __init__.py
│   ├── context.py           # LoaderContext, TestContext
│   └── utils.py             # Test-specific utilities
```

**Implementation Steps:**

1. Create new directory structure
1. Move classes to appropriate modules with imports
1. Update `loaders/__init__.py` to re-export all public APIs
1. Ensure backward compatibility with existing imports

**Compatibility Layer:**

```python
# loaders/__init__.py
from .base import AsyncBaseLoader, AsyncLoaderProtocol
from .filesystem import AsyncFileSystemLoader
from .package import AsyncPackageLoader
# ... etc

# Maintain backward compatibility
__all__ = [
    "AsyncBaseLoader",
    "AsyncLoaderProtocol",
    "AsyncFileSystemLoader",
    "AsyncPackageLoader",
    # ... all existing exports
]
```

### 1.2 Compiler Module Optimization

**Current State:** `compiler.py` (1,083 LOC) with mixed concerns

**Target Structure:**

```
jinja2_async_environment/
├── compiler/
│   ├── __init__.py          # AsyncCodeGenerator
│   ├── patterns.py          # CompiledPatterns
│   ├── resolver.py          # DependencyResolver
│   ├── generator.py         # LoopCodeGenerator
│   └── frame.py             # AsyncFrame
```

### 1.3 Testing Strategy

- Create comprehensive test suite before refactoring
- Use git bisect-friendly commits
- Maintain 100% test coverage during refactoring
- Add integration tests for import compatibility

### Deliverables

- [ ] New modular directory structure
- [ ] All tests passing with same coverage (84%+)
- [ ] Performance benchmarks unchanged
- [ ] Migration guide for developers

## Phase 2: Eliminate Global State (2 weeks)

### Goal: Replace global instances with dependency injection

### 2.1 Cache Manager Pattern

**Current Global State:**

```python
# Current (problematic)
_unified_cache = UnifiedCache()
_loader_context = LoaderContext()
_compilation_cache = CompilationCache()
```

**Target Architecture:**

```python
# caching/manager.py
from typing import Protocol, TypeVar, Generic

T = TypeVar("T")


class CacheProtocol(Protocol[T]):
    """Type-safe cache protocol"""

    def get(self, key: str) -> T | None: ...
    def set(self, key: str, value: T, ttl: int | None = None) -> None: ...
    def clear(self) -> None: ...


class CacheManager:
    """Centralized cache management with dependency injection"""

    def __init__(self):
        self.package_cache: CacheProtocol[tuple[Any, Any]] = TypedCache()
        self.template_cache: CacheProtocol[AsyncPath] = TypedCache()
        self.compilation_cache: CacheProtocol[str] = TypedCache()

    @classmethod
    def get_default(cls) -> "CacheManager":
        """Get default instance for backward compatibility"""
        if not hasattr(cls, "_default"):
            cls._default = cls()
        return cls._default
```

### 2.2 Environment Integration

```python
class AsyncEnvironment(Environment):
    def __init__(self, cache_manager: CacheManager | None = None, **kwargs):
        super().__init__(**kwargs)
        self._cache_manager = cache_manager or CacheManager.get_default()
        self._template_resolver = TemplateResolver(self, self._cache_manager)
```

### 2.3 Loader Integration

```python
class AsyncPackageLoader(AsyncBaseLoader):
    def __init__(self, package_name: str, ..., cache_manager: CacheManager | None = None):
        self._cache_manager = cache_manager or CacheManager.get_default()
        # Use instance cache instead of global
        cached_spec = self._cache_manager.package_cache.get(package_name)
```

### Deliverables

- [ ] CacheManager implementation
- [ ] Updated constructors with optional cache_manager parameter
- [ ] Backward compatibility tests
- [ ] Performance verification

## Phase 3: Type Safety Enhancement (1 week)

### Goal: Implement type-safe caching and eliminate Any types

### 3.1 Generic Cache Implementation

```python
# caching/typed.py
from typing import Generic, TypeVar, Dict, Optional
from dataclasses import dataclass
from time import time

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    timestamp: float
    ttl: int


class TypedCache(Generic[T]):
    """Type-safe cache with TTL and LRU eviction"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._access_order: list[str] = []

    def get(self, key: str) -> T | None:
        """Get value with TTL check"""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time() - entry.timestamp > entry.ttl:
            del self._cache[key]
            return None

        # Update LRU order
        self._access_order.remove(key)
        self._access_order.append(key)
        return entry.value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Set value with automatic eviction"""
        if len(self._cache) >= self._max_size:
            self._evict_lru()

        self._cache[key] = CacheEntry(
            value=value, timestamp=time(), ttl=ttl or self._default_ttl
        )

        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def _evict_lru(self) -> None:
        """Evict least recently used entries"""
        to_evict = self._max_size // 4
        for key in self._access_order[:to_evict]:
            del self._cache[key]
        self._access_order = self._access_order[to_evict:]
```

### 3.2 Specialized Cache Types

```python
# caching/specialized.py
from importlib.machinery import ModuleSpec
from types import ModuleType
from anyio import Path as AsyncPath

# Type-specific cache implementations
PackageSpecCache = TypedCache[tuple[Any, ModuleSpec]]
TemplateRootCache = TypedCache[AsyncPath]
CompilationCache = TypedCache[str]
ModuleCache = TypedCache[ModuleType]
```

### Deliverables

- [ ] Generic TypedCache implementation
- [ ] Specialized cache types
- [ ] Migration of existing cache usage
- [ ] Type safety verification with pyright

## Phase 4: Test Infrastructure Separation (1 week)

### Goal: Remove test detection from production code

### 4.1 Test Infrastructure Module

```python
# testing/infrastructure.py
"""Test infrastructure completely separated from production code"""

from contextlib import contextmanager
from typing import Generator


class TestDetector:
    """Centralized test detection without production pollution"""

    def __init__(self):
        self._test_mode = False
        self._test_context = None

    @contextmanager
    def test_context(self, test_name: str) -> Generator[None, None, None]:
        """Context manager for test execution"""
        old_mode = self._test_mode
        old_context = self._test_context

        self._test_mode = True
        self._test_context = test_name
        try:
            yield
        finally:
            self._test_mode = old_mode
            self._test_context = old_context

    def is_test_mode(self) -> bool:
        """Check if running in test mode"""
        return self._test_mode

    def get_test_context(self) -> str | None:
        """Get current test context"""
        return self._test_context


# Global instance for tests only
_test_detector = TestDetector()
```

### 4.2 Production Code Cleanup

**Remove from loaders:**

```python
# OLD (remove this)
if _loader_context.is_test_case("test_init_template_root_not_found"):
    raise ValueError(...)

# NEW (clean production code)
# No test detection in production code
```

**Update tests to use infrastructure:**

```python
# tests/test_loaders.py
from jinja2_async_environment.testing.infrastructure import _test_detector


def test_package_loader():
    with _test_detector.test_context("test_init_template_root_not_found"):
        # Test code here
        pass
```

### Deliverables

- [ ] Separate testing infrastructure module
- [ ] Remove all test detection from production code
- [ ] Update all tests to use new infrastructure
- [ ] Verify no test references in production

## Phase 5: Documentation Overhaul (1 week)

### Goal: Achieve 100% documentation coverage with quality docstrings

### 5.1 Documentation Standards

```python
def method_name(self, param1: str, param2: int | None = None) -> ResultType:
    """One-line summary of what the method does.

    Extended description providing more detail about the method's behavior,
    including any important side effects or considerations.

    Args:
        param1: Description of first parameter
        param2: Description of optional parameter (default: None)

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised

    Example:
        >>> env = AsyncEnvironment()
        >>> result = env.method_name("test", 42)
        >>> print(result)
        ResultType(...)
    """
```

### 5.2 Priority Documentation Targets

**High Priority (Public API):**

1. All AsyncEnvironment methods
1. All loader class methods
1. All protocol methods
1. Cache manager interface

**Medium Priority (Internal):**

1. Compiler utility classes
1. Frame management methods
1. Cache implementations

**Low Priority (Private):**

1. Helper methods
1. Internal utilities

### 5.3 Documentation Generation

```python
# scripts/generate_docs.py
"""Generate documentation coverage report"""

import ast
import sys
from pathlib import Path


def analyze_docstrings(module_path: Path) -> dict:
    """Analyze docstring coverage for a module"""
    # Implementation to analyze and report coverage
    pass


def generate_sphinx_docs():
    """Generate Sphinx documentation"""
    # Auto-generate API documentation
    pass
```

### Deliverables

- [ ] 100% docstring coverage for public API
- [ ] 80%+ docstring coverage overall
- [ ] Generated API documentation
- [ ] Usage examples for all major features

## Phase 6: Performance Regression Prevention (1 week)

### Goal: Ensure refactoring maintains all performance gains

### 6.1 Performance Test Suite

```python
# tests/performance/regression.py
"""Performance regression test suite"""

import pytest
from pathlib import Path

# Baseline performance metrics
PERFORMANCE_BASELINES = {
    "template_compilation": {
        "simple": 20_000,  # nanoseconds
        "complex": 60_000,  # nanoseconds
    },
    "package_loader_creation": {
        "cached": 60_000,  # nanoseconds
        "uncached": 500_000,  # nanoseconds
    },
    "cache_operations": {
        "get": 1_000,  # nanoseconds
        "set": 2_000,  # nanoseconds
    },
}


@pytest.mark.benchmark
def test_compilation_performance(benchmark):
    """Ensure compilation performance is maintained"""
    result = benchmark(compile_template, simple_template)
    assert result < PERFORMANCE_BASELINES["template_compilation"]["simple"]
```

### 6.2 CI/CD Integration

```yaml
# .github/workflows/performance.yml
name: Performance Regression Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run performance tests
        run: |
          pytest tests/performance/ --benchmark-only
          python scripts/compare_benchmarks.py
```

### 6.3 Performance Monitoring

```python
# scripts/performance_monitor.py
"""Monitor performance metrics over time"""

import json
from datetime import datetime
from pathlib import Path


class PerformanceMonitor:
    def __init__(self, baseline_file: Path):
        self.baseline_file = baseline_file
        self.history_file = baseline_file.parent / "performance_history.json"

    def record_metrics(self, metrics: dict) -> None:
        """Record performance metrics with timestamp"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "commit": self._get_git_commit(),
        }
        # Append to history

    def check_regression(self, current: dict) -> list[str]:
        """Check for performance regressions"""
        baseline = self._load_baseline()
        regressions = []

        for key, baseline_value in baseline.items():
            if key in current:
                current_value = current[key]
                if current_value > baseline_value * 1.1:  # 10% threshold
                    regressions.append(
                        f"{key}: {current_value}ns > {baseline_value}ns (baseline)"
                    )

        return regressions
```

### Deliverables

- [ ] Comprehensive performance test suite
- [ ] CI/CD integration for performance tests
- [ ] Performance monitoring dashboard
- [ ] Automated regression detection

## Implementation Timeline

### Week 1-2: Phase 1 (Architectural Restructuring)

- Create new directory structure
- Move loaders to separate modules
- Split compiler components
- Ensure all tests pass

### Week 3-4: Phase 2 (Global State Elimination)

- Implement CacheManager
- Add dependency injection
- Update all components
- Verify backward compatibility

### Week 5: Phase 3 (Type Safety)

- Implement generic caches
- Add type annotations
- Run pyright strict mode
- Fix type errors

### Week 6: Phase 4 (Test Separation)

- Create test infrastructure
- Remove test code from production
- Update all tests
- Verify clean separation

### Week 7: Phase 5 (Documentation)

- Add comprehensive docstrings
- Generate API documentation
- Create usage examples
- Review documentation quality

### Week 8: Phase 6 (Performance)

- Create regression tests
- Set up CI/CD
- Establish baselines
- Monitor performance

## Risk Mitigation

### Backward Compatibility

- All changes maintain existing public API
- Import paths preserved through __init__.py re-exports
- Optional parameters for new features
- Comprehensive compatibility test suite

### Performance Preservation

- Benchmark before and after each change
- Automated regression detection
- Performance-critical paths unchanged
- Optimization strategies documented

### Rollback Strategy

- Git tags at each phase completion
- Feature flags for major changes
- Incremental deployment capability
- Comprehensive test coverage

## Success Metrics

1. **Maintainability**: Reduce average file size from 625 LOC to \<300 LOC
1. **Type Safety**: Eliminate all `Any` types in public APIs
1. **Documentation**: Achieve 100% docstring coverage for public API
1. **Performance**: Maintain all existing performance benchmarks ±5%
1. **Test Quality**: Maintain 84%+ test coverage
1. **Architecture**: Achieve clear separation of concerns

## Conclusion

This refactoring plan addresses all critical issues identified in the code review while preserving the excellent performance characteristics of the jinja2-async-environment package. The phased approach ensures minimal risk and allows for incremental improvements with clear rollback points.

The end result will be a more maintainable, type-safe, and well-documented codebase that retains all existing functionality and performance optimizations while enabling future scalability and extensibility.
