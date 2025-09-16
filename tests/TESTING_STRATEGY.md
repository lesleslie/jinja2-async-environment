# Testing Strategy for Refactored jinja2-async-environment

## Overview

This document outlines the comprehensive testing strategy to ensure the refactoring maintains all existing functionality, performance characteristics, and adds new test coverage for improved code quality.

## Testing Principles

1. **No Regression**: All existing tests must continue to pass
1. **Performance Preservation**: All benchmarks must remain within 5% of baseline
1. **Coverage Improvement**: Increase from 84% to 90%+ coverage
1. **Type Safety**: Full pyright strict mode compliance
1. **Backward Compatibility**: Extensive compatibility testing

## Test Organization

### Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_loaders/       # Loader-specific tests
│   ├── test_caching/       # Cache implementation tests
│   ├── test_compiler/      # Compiler component tests
│   └── test_environment.py # Environment tests
├── integration/            # Integration tests
│   ├── test_compatibility.py
│   ├── test_imports.py
│   └── test_workflows.py
├── performance/            # Performance tests
│   ├── test_benchmarks.py
│   ├── test_regression.py
│   └── baselines.json
├── fixtures/               # Shared test fixtures
│   ├── templates/
│   └── conftest.py
└── quality/               # Code quality tests
    ├── test_typing.py
    ├── test_documentation.py
    └── test_architecture.py
```

## Phase-by-Phase Testing Strategy

### Phase 1: Architectural Restructuring Tests

#### 1.1 Import Compatibility Tests

```python
# tests/integration/test_imports.py
"""Ensure all imports work with both old and new structures"""

import pytest


def test_backward_compatible_imports():
    """All existing imports must continue to work"""
    # Old style imports should work
    from jinja2_async_environment import AsyncEnvironment
    from jinja2_async_environment.loaders import (
        AsyncFileSystemLoader,
        AsyncPackageLoader,
        AsyncDictLoader,
        AsyncFunctionLoader,
        AsyncChoiceLoader,
    )

    # Verify all classes are importable
    assert AsyncEnvironment
    assert AsyncFileSystemLoader
    assert AsyncPackageLoader


def test_new_module_structure():
    """New internal modules should be properly organized"""
    # These should work but are internal
    from jinja2_async_environment.loaders.filesystem import AsyncFileSystemLoader
    from jinja2_async_environment.loaders.package import AsyncPackageLoader
    from jinja2_async_environment.caching.unified import UnifiedCache

    # But public API should use main module
    from jinja2_async_environment.loaders import AsyncFileSystemLoader as PublicLoader

    assert PublicLoader is AsyncFileSystemLoader


@pytest.mark.parametrize(
    "import_style",
    [
        "from jinja2_async_environment import *",
        "import jinja2_async_environment as j2async",
        "from jinja2_async_environment.loaders import *",
    ],
)
def test_import_styles(import_style):
    """Various import styles should work"""
    exec(import_style)
```

#### 1.2 Functionality Preservation Tests

```python
# tests/unit/test_loaders/test_preservation.py
"""Ensure refactored loaders maintain exact functionality"""

import pytest
from pathlib import Path


@pytest.fixture
def legacy_loader_behavior():
    """Capture behavior of loaders before refactoring"""
    return {
        "filesystem": {
            "search_paths": ["/path1", "/path2"],
            "expected_templates": ["base.html", "index.html"],
        },
        "package": {"package_name": "myapp", "cache_behavior": "aggressive"},
    }


async def test_filesystem_loader_compatibility(legacy_loader_behavior):
    """Filesystem loader must behave identically"""
    from jinja2_async_environment.loaders import AsyncFileSystemLoader

    loader = AsyncFileSystemLoader(legacy_loader_behavior["filesystem"]["search_paths"])

    # Test all methods maintain same behavior
    templates = await loader.list_templates_async()
    assert set(templates) == set(
        legacy_loader_behavior["filesystem"]["expected_templates"]
    )
```

### Phase 2: Global State Elimination Tests

#### 2.1 Dependency Injection Tests

```python
# tests/unit/test_caching/test_dependency_injection.py
"""Test cache manager dependency injection"""

import pytest
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment.caching import CacheManager


def test_default_cache_manager():
    """Environment should use default cache if none provided"""
    env1 = AsyncEnvironment()
    env2 = AsyncEnvironment()

    # Should share default cache manager
    assert env1._cache_manager is env2._cache_manager


def test_custom_cache_manager():
    """Environment should use provided cache manager"""
    custom_cache = CacheManager()
    env = AsyncEnvironment(cache_manager=custom_cache)

    assert env._cache_manager is custom_cache


def test_cache_isolation():
    """Different cache managers should be isolated"""
    cache1 = CacheManager()
    cache2 = CacheManager()

    env1 = AsyncEnvironment(cache_manager=cache1)
    env2 = AsyncEnvironment(cache_manager=cache2)

    # Add to cache1
    cache1.template_cache.set("test", "value1")

    # Should not appear in cache2
    assert cache2.template_cache.get("test") is None


@pytest.mark.asyncio
async def test_loader_cache_integration():
    """Loaders should use environment's cache manager"""
    from jinja2_async_environment.loaders import AsyncPackageLoader

    custom_cache = CacheManager()
    loader = AsyncPackageLoader("mypackage", "templates", cache_manager=custom_cache)

    # Verify loader uses provided cache
    assert loader._cache_manager is custom_cache
```

#### 2.2 State Isolation Tests

```python
# tests/integration/test_state_isolation.py
"""Ensure no global state pollution between instances"""

import asyncio
import pytest


@pytest.mark.asyncio
async def test_concurrent_environment_isolation():
    """Multiple environments should not interfere"""
    from jinja2_async_environment import AsyncEnvironment
    from jinja2_async_environment.loaders import AsyncDictLoader

    async def create_and_render(env_id: int):
        env = AsyncEnvironment()
        env.loader = AsyncDictLoader(
            {"test.html": f"Environment {env_id}: {{{{ value }}}}"}
        )

        template = await env.get_template_async("test.html")
        return await template.render_async(value=env_id)

    # Run concurrently
    results = await asyncio.gather(
        create_and_render(1), create_and_render(2), create_and_render(3)
    )

    assert results == ["Environment 1: 1", "Environment 2: 2", "Environment 3: 3"]
```

### Phase 3: Type Safety Tests

#### 3.1 Type Checking Tests

```python
# tests/quality/test_typing.py
"""Ensure type safety with pyright"""

import subprocess
import json


def test_pyright_strict_mode():
    """All code should pass pyright strict mode"""
    result = subprocess.run(["pyright", "--outputjson"], capture_output=True, text=True)

    output = json.loads(result.stdout)

    # Should have no errors in strict mode
    assert output["summary"]["errorCount"] == 0


def test_no_any_in_public_api():
    """Public API should not expose Any types"""
    import ast
    import inspect
    from pathlib import Path

    # Parse all public modules
    for py_file in Path("jinja2_async_environment").glob("**/*.py"):
        if "__pycache__" in str(py_file):
            continue

        with open(py_file) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check public methods don't return Any
                if not node.name.startswith("_"):
                    # Verify return annotation exists and isn't Any
                    assert node.returns is not None, (
                        f"{py_file}:{node.name} missing return type"
                    )
```

#### 3.2 Generic Cache Tests

```python
# tests/unit/test_caching/test_typed_cache.py
"""Test type-safe generic cache implementation"""

import pytest
from jinja2_async_environment.caching import TypedCache


def test_typed_cache_type_safety():
    """Cache should maintain type safety"""
    from pathlib import Path

    # String cache
    string_cache: TypedCache[str] = TypedCache()
    string_cache.set("key", "value")
    result = string_cache.get("key")
    assert isinstance(result, str)

    # Path cache
    path_cache: TypedCache[Path] = TypedCache()
    path_cache.set("key", Path("/tmp"))
    result = path_cache.get("key")
    assert isinstance(result, Path)


def test_cache_ttl_expiration():
    """Cache should respect TTL"""
    import time

    cache: TypedCache[str] = TypedCache(default_ttl=1)
    cache.set("key", "value")

    # Should exist immediately
    assert cache.get("key") == "value"

    # Should expire after TTL
    time.sleep(1.1)
    assert cache.get("key") is None


def test_cache_lru_eviction():
    """Cache should evict LRU entries when full"""
    cache: TypedCache[int] = TypedCache(max_size=3)

    # Fill cache
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    # Access 'a' to make it recently used
    cache.get("a")

    # Add new item - should evict 'b' (least recently used)
    cache.set("d", 4)

    assert cache.get("a") == 1  # Still exists
    assert cache.get("b") is None  # Evicted
    assert cache.get("c") == 3  # Still exists
    assert cache.get("d") == 4  # New item
```

### Phase 4: Test Infrastructure Separation Tests

#### 4.1 Production Code Cleanliness

```python
# tests/quality/test_architecture.py
"""Ensure test code is properly separated"""

import ast
from pathlib import Path


def test_no_test_detection_in_production():
    """Production code should not contain test detection"""
    test_patterns = ["_loader_context", "is_test_case", "test_context", "TestContext"]

    for py_file in Path("jinja2_async_environment").glob("**/*.py"):
        if "testing" in str(py_file):  # Skip testing module
            continue

        with open(py_file) as f:
            content = f.read()

        for pattern in test_patterns:
            assert pattern not in content, f"{pattern} found in {py_file}"


def test_testing_module_isolation():
    """Testing module should not be imported by production code"""
    production_files = list(Path("jinja2_async_environment").glob("**/*.py"))
    production_files = [f for f in production_files if "testing" not in str(f)]

    for py_file in production_files:
        with open(py_file) as f:
            content = f.read()

        assert "from .testing" not in content
        assert "from jinja2_async_environment.testing" not in content
```

### Phase 5: Documentation Tests

#### 5.1 Docstring Coverage Tests

```python
# tests/quality/test_documentation.py
"""Test documentation quality and coverage"""

import ast
import inspect
from pathlib import Path


def test_public_api_docstrings():
    """All public API methods must have docstrings"""
    missing_docstrings = []

    for py_file in Path("jinja2_async_environment").glob("**/*.py"):
        with open(py_file) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):  # Public
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        missing_docstrings.append(f"{py_file}:{node.name}")

    assert not missing_docstrings, f"Missing docstrings: {missing_docstrings}"


def test_docstring_quality():
    """Docstrings should follow standards"""
    from jinja2_async_environment import AsyncEnvironment

    # Check a key method
    method = AsyncEnvironment.get_template_async
    doc = inspect.getdoc(method)

    # Should have sections
    assert "Args:" in doc or "Parameters:" in doc
    assert "Returns:" in doc
    assert "Example:" in doc or "Examples:" in doc
```

### Phase 6: Performance Tests

#### 6.1 Regression Tests

```python
# tests/performance/test_regression.py
"""Ensure performance is maintained"""

import pytest
import json
from pathlib import Path

# Load baseline metrics
BASELINE_FILE = Path(__file__).parent / "baselines.json"
with open(BASELINE_FILE) as f:
    BASELINES = json.load(f)


@pytest.mark.benchmark
def test_compilation_performance_maintained(benchmark):
    """Template compilation should not regress"""
    from jinja2_async_environment import AsyncEnvironment

    env = AsyncEnvironment()
    source = "{{ name }} - {{ items|length }}"

    result = benchmark(env.compile, source)

    baseline = BASELINES["compilation"]["simple"]
    assert benchmark.stats["mean"] < baseline * 1.05  # 5% tolerance


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_loader_performance_maintained(benchmark):
    """Loader creation should not regress"""
    from jinja2_async_environment.loaders import AsyncPackageLoader

    def create_loader():
        return AsyncPackageLoader("mypackage", "templates")

    result = benchmark(create_loader)

    baseline = BASELINES["loader"]["package_creation"]
    assert benchmark.stats["mean"] < baseline * 1.05


class TestCachePerformance:
    """Cache operations should maintain performance"""

    @pytest.mark.benchmark
    def test_cache_get_performance(self, benchmark):
        from jinja2_async_environment.caching import TypedCache

        cache = TypedCache[str]()
        cache.set("test", "value")

        result = benchmark(cache.get, "test")

        baseline = BASELINES["cache"]["get"]
        assert benchmark.stats["mean"] < baseline * 1.05

    @pytest.mark.benchmark
    def test_cache_set_performance(self, benchmark):
        from jinja2_async_environment.caching import TypedCache

        cache = TypedCache[str]()

        result = benchmark(cache.set, "test", "value")

        baseline = BASELINES["cache"]["set"]
        assert benchmark.stats["mean"] < baseline * 1.05
```

#### 6.2 Performance Monitoring

```python
# tests/performance/test_monitoring.py
"""Monitor performance trends"""

import json
import pytest
from datetime import datetime
from pathlib import Path


class PerformanceRecorder:
    """Record performance metrics for trend analysis"""

    def __init__(self):
        self.history_file = Path("performance_history.json")
        self.load_history()

    def load_history(self):
        if self.history_file.exists():
            with open(self.history_file) as f:
                self.history = json.load(f)
        else:
            self.history = []

    def record(self, test_name: str, metrics: dict):
        """Record test metrics"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "metrics": metrics,
        }
        self.history.append(entry)

    def save(self):
        """Save history to file"""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def check_trend(self, test_name: str, window: int = 10):
        """Check if performance is degrading"""
        relevant = [e for e in self.history if e["test"] == test_name]
        recent = relevant[-window:]

        if len(recent) < window:
            return True  # Not enough data

        # Check if trending upward (bad)
        means = [e["metrics"]["mean"] for e in recent]
        first_half = sum(means[: window // 2]) / (window // 2)
        second_half = sum(means[window // 2 :]) / (window // 2)

        # Alert if degrading by more than 10%
        return second_half <= first_half * 1.1


@pytest.fixture
def performance_recorder():
    return PerformanceRecorder()


def test_performance_trend(performance_recorder):
    """Check performance trends"""
    degrading = []

    for test in ["compilation", "loader_creation", "cache_operations"]:
        if not performance_recorder.check_trend(test):
            degrading.append(test)

    assert not degrading, f"Performance degrading for: {degrading}"
```

## Test Execution Strategy

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=jinja2_async_environment

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v

  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run performance tests
        run: |
          pytest tests/performance/ --benchmark-only

      - name: Check regression
        run: |
          python scripts/check_performance_regression.py

  quality-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Type checking
        run: |
          pyright --strict

      - name: Architecture tests
        run: |
          pytest tests/quality/ -v
```

### Local Development Testing

```bash
# Quick test during development
pytest tests/unit/ -x  # Stop on first failure

# Full test suite
pytest

# Performance testing
pytest tests/performance/ --benchmark-only

# Type checking
pyright --strict

# Coverage report
pytest --cov=jinja2_async_environment --cov-report=html
```

## Test Data Management

### Template Fixtures

```
tests/fixtures/templates/
├── simple/
│   ├── base.html
│   ├── index.html
│   └── error.html
├── complex/
│   ├── layout.html
│   ├── macros.html
│   └── inheritance.html
└── async/
    ├── async_filters.html
    ├── async_loops.html
    └── async_blocks.html
```

### Performance Baselines

```json
{
  "compilation": {
    "simple": 20000,
    "complex": 60000
  },
  "loader": {
    "filesystem_creation": 1000,
    "package_creation": 50000,
    "dict_creation": 3000
  },
  "cache": {
    "get": 1000,
    "set": 2000,
    "eviction": 5000
  }
}
```

## Success Criteria

1. **All existing tests pass**: 329 tests must continue passing
1. **Coverage increases**: From 84% to 90%+
1. **Performance maintained**: All benchmarks within 5% of baseline
1. **Type safety**: Zero errors in pyright strict mode
1. **Documentation**: 100% docstring coverage for public API
1. **Architecture**: Clean separation of concerns verified

## Risk Mitigation

### Test Flakiness

- Use deterministic test data
- Mock time-dependent operations
- Clear caches between tests
- Use proper async test fixtures

### Performance Variance

- Run benchmarks multiple times
- Use statistical analysis
- Account for system load
- Set reasonable tolerances

### Compatibility Testing

- Test all Python versions
- Test all import patterns
- Test upgrade scenarios
- Test rollback procedures
