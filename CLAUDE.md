# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `jinja2-async-environment`, an async-first template engine that extends Jinja2 with comprehensive asynchronous support. It provides non-blocking template operations for high-performance web applications using FastAPI, Starlette, AIOHTTP, and similar async frameworks.

**Key Design Goals:**

- 100% Jinja2 compatibility (including full macro support in sync mode)
- Performance-first architecture with comprehensive benchmarking
- Type-safe async operations with Protocol-based interfaces
- Drop-in replacement for standard Jinja2 in async applications

## Development Commands

### Initial Setup

```bash
# Install dependencies (first time setup)
uv sync              # Install dependencies from uv.lock

# Activate virtual environment if needed
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
```

### Package Management

```bash
# Primary package manager (UV - faster than pip/poetry)
uv sync              # Install dependencies from uv.lock
uv add <package>     # Add new dependency
uv add --dev <package>  # Add development dependency
uv lock              # Update lock file
```

### Code Quality & Linting

```bash
# MANDATORY: Run before marking any task complete
python -m crackerjack -t --ai-agent  # AI-optimized quality checks and tests

# Alternative crackerjack modes
python -m crackerjack -i              # Interactive development mode
python -m crackerjack --update-docs   # Update documentation standards

# Individual tools (if needed)
ruff format          # Code formatting (line length 88)
ruff check          # Linting (Python 3.13+)
pyright             # Type checking (strict mode)
refurb .            # Code improvement suggestions
bandit -r .         # Security analysis
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_environment.py

# Run single test
pytest tests/test_environment.py::test_specific_function

# Run with coverage (minimum 42% required)
pytest --cov=jinja2_async_environment

# Run tests with verbose output
pytest -v

# Run specific test markers
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m benchmark      # Benchmark tests (disables parallel execution)

# Run performance tests
pytest tests/test_realistic_optimization.py
pytest tests/test_benchmarks.py -v

# Run tests in parallel (except benchmarks)
pytest -n auto

# Run coverage-focused tests
pytest tests/test_compiler_uncovered.py tests/test_environment_uncovered.py tests/test_compiler_advanced_coverage.py

# Skip known failing macro tests
pytest --ignore=tests/test_macro_parameters.py --ignore=tests/test_macros.py
```

### Performance Analysis

```bash
# Run baseline benchmarks
pytest tests/test_benchmarks.py -v

# Performance comparison tests
pytest tests/test_optimization_comparison.py

# Check benchmark documentation
cat tests/BENCHMARK_BASELINE.md      # Baseline metrics
cat tests/OPTIMIZATION_RESULTS.md    # Optimization analysis
cat tests/PERFORMANCE_SUMMARY.md     # Executive summary
```

## Architecture Overview

### Core Components

**AsyncEnvironment** (`environment.py:50`): Main async template environment extending Jinja2's Environment. Integrates with dependency injection via `CacheManager` and includes `TemplateResolver` service class for improved organization.

**Modular Loader System** (`jinja2_async_environment/loaders/`): Refactored from monolithic 920 LOC file into focused modules:

- `loaders/base.py`: `AsyncLoaderProtocol` and `AsyncBaseLoader`
- `loaders/filesystem.py`: `AsyncFileSystemLoader` - filesystem templates using anyio.Path
- `loaders/package.py`: `AsyncPackageLoader` - Python package templates with optimized caching
- `loaders/dict.py`: `AsyncDictLoader` - in-memory dictionary templates
- `loaders/function.py`: `AsyncFunctionLoader` - custom function-based loading
- `loaders/choice.py`: `AsyncChoiceLoader` - tries multiple loaders sequentially

**Modular Compiler System** (`jinja2_async_environment/compiler_modules/`): Refactored for better organization:

- `compiler_modules/codegen.py`: `AsyncCodeGenerator` main class
- `compiler_modules/patterns.py`: `CompiledPatterns` for regex optimizations
- `compiler_modules/cache.py`: `CompilationCache` with SHA-256 hashing
- `compiler_modules/dependencies.py`: `DependencyResolver` for filter/test management
- `compiler_modules/frame.py`: `AsyncFrame` for async-aware frames
- `compiler_modules/loops.py`: `LoopCodeGenerator` for complex loop handling

**Advanced Caching Infrastructure** (`jinja2_async_environment/caching/`): New comprehensive caching system:

- `caching/manager.py`: `CacheManager` with dependency injection support
- `caching/typed.py`: `TypedCache[T]` with generics and TTL management
- `caching/strategies.py`: Advanced cache strategies (LFU, Adaptive, Hierarchical)
- `caching/unified.py`: Unified cache for backward compatibility

**AsyncSandboxedEnvironment**: Secure template execution for untrusted content.

**AsyncRedisBytecodeCache** (`bccache.py`): Distributed caching for compiled templates with Redis backend.

### Architectural Patterns

**Dependency Injection Pattern**: The system now uses `CacheManager` for dependency injection:

```python
# Create environment with custom cache manager
from jinja2_async_environment.caching.manager import CacheManager, AdvancedCacheManager

# Basic cache manager
cache_manager = CacheManager(template_cache_size=2000, default_ttl=600)
env = AsyncEnvironment(loader=loader, cache_manager=cache_manager)

# Advanced cache manager with strategies
advanced_manager = AdvancedCacheManager(
    strategy="adaptive",  # or "lru", "lfu", "hierarchical"
    enable_hierarchical=True,
)
env = AsyncEnvironment(loader=loader, cache_manager=advanced_manager)
```

**Service Layer Pattern**: Complex logic is extracted into service classes:

- `TemplateResolver` (environment.py:17): Handles template name resolution and loading strategies
- `DependencyResolver` (compiler_modules/dependencies.py): Manages filter and test dependencies
- `LoopCodeGenerator` (compiler_modules/loops.py): Handles complex for-loop code generation
- `CacheWarmer` (caching/strategies.py:369): Preloads commonly used templates

**Type-Safe Generic Caching**: All caches use generic types for better type safety:

```python
from jinja2_async_environment.caching import TypedCache

# Type-safe cache declarations
PackageSpecCache = TypedCache[tuple[t.Any, t.Any]]
TemplateRootCache = TypedCache[AsyncPath | None]
CompilationCache = TypedCache[str]
```

### Critical Implementation Details

**Performance-Critical Paths:**

- `AsyncEnvironment._async_yield_from()` (environment.py:118) - Uses `hasattr()` instead of exceptions for 300x performance improvement
- Template compilation via `AsyncCodeGenerator.compile_with_cache()` with SHA-256 hashing
- Package loading with aggressive caching: 45ms → 52μs (860x faster)
- Pre-compiled regex patterns for 1,180-1,223x compilation speedup

**Modular Architecture (Recent Major Refactoring):**

- **Loader System**: Split 920 LOC monolithic file into 6 focused modules with backward compatibility via re-exports
- **Compiler System**: Extracted utility classes (`DependencyResolver`, `LoopCodeGenerator`, `CompiledPatterns`) from complex single file
- **Cache Management**: New dependency injection system with `CacheManager` supporting multiple strategies
- **Memory Optimization**: All classes use `__slots__` and lazy initialization patterns

**Advanced Cache Strategies:**

- **LFU Cache** (caching/strategies.py:27): Least Frequently Used with detailed statistics
- **Adaptive Cache** (caching/strategies.py:150): Switches between LRU/LFU based on access patterns
- **Hierarchical Cache** (caching/strategies.py:257): Multi-level L1/L2 caching with promotion logic
- **Cache Warming** (caching/strategies.py:369): Preloads commonly used templates and packages

**Key Methods (Updated Locations):**

- `AsyncCodeGenerator.visit_For()` (compiler_modules/codegen.py:289): Handles single variables and tuple unpacking via helper methods
- `AsyncCodeGenerator.visit_Filter()` (compiler_modules/codegen.py:455): Manages filter dependencies and async execution
- `AsyncCodeGenerator.visit_Assign()` (compiler_modules/codegen.py:534): Tracks `{% set %}` variable assignments
- `AsyncCodeGenerator.visit_Macro()` (compiler_modules/codegen.py:448): Delegates to base for sync compatibility

**Memory Optimization:**

- All loader and cache classes use `__slots__` for reduced memory footprint
- Lazy loading with initialization tracking (`_initialized` attribute)
- Automated cache expiration and cleanup with TTL management
- Memory usage estimation and monitoring via `CacheManager.get_memory_usage_estimate()`

### Testing Architecture

**Coverage Status:**

- Overall: **85%** coverage
- `bccache.py`: 100% ✅
- `environment.py`: 93% ✅
- `compiler_modules/codegen.py`: 87% ✅
- `loaders/`: 78% average (improved from context system)

**Test Organization:**

- Unit tests for each component with proper isolation
- Performance benchmarks with baseline tracking
- Coverage-focused test files for uncovered methods
- GitHub issue regression tests (e.g., test_github_issue_6.py)
- Integration tests for modular architecture

**Testing Requirements:**

- Use AsyncMock for async operations (not MagicMock)
- Performance tests disable parallel execution
- `asyncio_mode = "auto"` in pytest configuration
- **Test Isolation**: Always clear cache managers between tests to prevent state leakage
- **Cache Testing**: Use `CacheManager.create_scoped_manager()` for isolated test environments

## Development Workflow

### Task Completion Protocol

**MANDATORY: Before marking any task complete:**

1. Run `python -m crackerjack -t --ai-agent`
1. Fix all issues (formatting, linting, type checking, tests)
1. Re-run crackerjack until all checks pass
1. Document successful verification

This is the project's standard quality gate - never skip it.

### Code Style Requirements

- **Python Version**: 3.13+ required
- **Line Length**: 88 characters (Ruff)
- **Type Annotations**: Required for all new code (Pyright strict)
- **Complexity Limit**: McCabe complexity ≤ 13
- **Import Style**: Follow existing patterns in each file

### Performance Testing Protocol

When modifying performance-critical code:

1. Run benchmarks before changes: `pytest tests/test_benchmarks.py -v`
1. Make changes
1. Run benchmarks after changes
1. Compare results against `tests/BENCHMARK_BASELINE.md`
1. Document any improvements/regressions

## Known Limitations

**Macro Support**: Macros work 100% in sync mode. Full async macro support would require Jinja2 runtime changes. 13 macro-related tests fail due to async/await incompatibility.

**Template Complexity**: `visit_For()` method handles complex scenarios through helper methods to manage complexity.

**Coverage Gaps**: Focus improvement efforts on edge cases in the modular loader system.

## Recent Major Refactoring (2024)

**Comprehensive Module Restructuring:**

- **Phase 1**: Split monolithic `loaders.py` (920 LOC) into focused modules in `loaders/` directory
- **Phase 2**: Extracted compiler utilities into `compiler_modules/` with better separation of concerns
- **Phase 3**: Implemented dependency injection with `CacheManager` and advanced caching strategies
- **Phase 4**: Added memory optimization with `__slots__` and lazy initialization patterns
- **Phase 5**: Created comprehensive caching infrastructure with multiple strategies

**Performance Improvements (Latest Results):**

- `_async_yield_from()` method: 300x improvement (347ms → ~1ms)
- Template compilation: 1,180-1,223x faster with pre-compiled regex and caching
- Package loader creation: 860x faster (45ms → 52μs) with import caching
- Memory usage: Significant reduction via `__slots__` and lazy loading

**Architecture Improvements:**

- **Modular Design**: Clear separation of concerns with focused modules
- **Type Safety**: Generic caches with proper type annotations
- **Dependency Injection**: `CacheManager` pattern for testable, configurable caching
- **Advanced Strategies**: LFU, Adaptive, and Hierarchical caching options
- **Monitoring**: Comprehensive cache statistics and memory usage tracking

**GitHub Issue #6 Fix:**

- Fixed tuple unpacking in for loops
- Implemented proper join filter generation
- Added comprehensive regression tests

## Quick Reference

### File Locations (Updated Post-Refactoring)

- Source code: `jinja2_async_environment/`
- Loaders: `jinja2_async_environment/loaders/` (6 focused modules)
- Compiler: `jinja2_async_environment/compiler_modules/` (6 focused modules)
- Caching: `jinja2_async_environment/caching/` (4 comprehensive modules)
- Tests: `tests/`
- Performance docs: `tests/BENCHMARK_*.md`
- Coverage tests: `tests/test_*_uncovered.py`

### Common Tasks

- **Add new loader**: Implement `AsyncLoaderProtocol` in `loaders/` directory
- **Add cache strategy**: Extend classes in `caching/strategies.py`
- **Fix type errors**: Run `pyright` and check strict mode compliance
- **Improve coverage**: Focus on edge cases in modular components
- **Performance work**: Always benchmark before/after changes

### Development Tips

- **Modular Development**: Each module has focused responsibility - loaders handle loading, compiler handles compilation, caching handles performance
- **Cache Management**: Use `CacheManager` for dependency injection in new code
- **Type Safety**: Use generic `TypedCache[T]` for new cache implementations
- **Performance Work**: Always benchmark before/after changes, use cache warming for production
- **Memory Optimization**: Use `__slots__` for new classes, consider lazy initialization patterns
- **Testing**: Use scoped cache managers for test isolation, clear caches between test runs

### Cache Strategy Selection Guide

- **LRU (default)**: General purpose, good for most use cases
- **LFU**: When some templates are accessed much more frequently than others
- **Adaptive**: Automatically switches between LRU/LFU based on access patterns
- **Hierarchical**: When you need both fast access (L1) and large capacity (L2)
