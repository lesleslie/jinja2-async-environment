# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `jinja2-async-environment`, an async-first template engine that extends Jinja2 with comprehensive asynchronous support. It provides non-blocking template operations for high-performance web applications using FastAPI, Starlette, AIOHTTP, and similar async frameworks.

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
# Primary package manager
uv sync              # Install dependencies from uv.lock
uv add <package>     # Add new dependency
uv add --dev <package>  # Add development dependency
uv lock              # Update lock file
```

### Code Quality & Linting
```bash
# Run all pre-commit hooks (comprehensive quality checks)
pre-commit run --all-files

# Individual tools
ruff format          # Code formatting
ruff check          # Linting
pyright             # Type checking
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

# Run with coverage (configured with 42% minimum)
pytest --cov=jinja2_async_environment

# Run tests with verbose output
pytest -v

# Run specific test markers
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m benchmark      # Benchmark tests only

# Run realistic performance tests
pytest tests/test_realistic_optimization.py

# Run tests in parallel (if pytest-xdist is available)
pytest -n auto
```

### Performance Analysis
```bash
# Run baseline benchmarks (located in tests/)
pytest tests/test_benchmarks.py -v

# Performance comparison tests
pytest tests/test_optimization_comparison.py
```

## Architecture Overview

### Core Components

**AsyncEnvironment** (`environment.py`): Main async template environment that extends Jinja2's Environment with async-aware compilation and rendering. Key method: `_async_yield_from()` - optimized for 300x performance improvement.

**Async Loaders** (`loaders.py`): Five loader types for different template sources:
- `AsyncFileSystemLoader` - filesystem templates using anyio.Path
- `AsyncPackageLoader` - Python package templates
- `AsyncDictLoader` - in-memory dictionary templates
- `AsyncFunctionLoader` - custom function-based loading
- `AsyncChoiceLoader` - tries multiple loaders sequentially

**AsyncSandboxedEnvironment**: Secure template execution for untrusted content with restricted access to Python internals.

**Async Caching** (`bccache.py`): Redis-backed bytecode caching for compiled templates with `AsyncRedisBytecodeCache`.

**Async Compiler** (`compiler.py`): `AsyncCodeGenerator` extends Jinja2's compiler with async-aware code generation and template rendering.

### Key Design Patterns

- **Async-First**: All operations are non-blocking by default
- **Protocol-Based**: Uses modern Python typing protocols for loader interfaces
- **Performance-Optimized**: Critical path optimization in `_async_yield_from` eliminates exception handling overhead
- **Drop-in Replacement**: Familiar API for existing Jinja2 users
- **Type Safe**: Comprehensive type annotations with Pyright validation

### Performance Considerations

The `_async_yield_from()` method in `AsyncEnvironment` was recently optimized from exception-based type detection to direct `hasattr()` checking, achieving 300x performance improvement (347ms → ~1ms). This is critical for all async template rendering operations.

### Testing Strategy

Tests are organized by component with comprehensive coverage:
- Core functionality tests for each loader and environment type
- Performance benchmarks with baseline tracking in `tests/BENCHMARK_BASELINE.md`
- Security tests for sandboxed environments
- End-to-end integration tests with real async frameworks

The test suite uses `asyncio_mode = "auto"` and requires AsyncMock for async operations (not MagicMock).

### Development Notes

- **Python Version**: Minimum Python 3.13+ required
- **Package Manager**: Uses UV for dependency management (faster than pip/poetry)
- **Type Checking**: Strict type checking with Pyright - all new code must be fully typed
- **Code Quality**: Pre-commit hooks enforce comprehensive quality checks:
  - Code formatting (Ruff)
  - Linting and style (Ruff, Vulture, Refurb)
  - Security analysis (Bandit, detect-secrets)
  - Type checking (Pyright)
  - Dependency analysis (Creosote)
  - Complexity analysis (Complexipy)
- **Performance**: Performance regressions tracked via benchmark tests in `tests/` directory
- **Async Patterns**: Test suite uses `asyncio_mode = "auto"` - use AsyncMock, not MagicMock for async operations
- **Documentation**: Comprehensive performance baselines in `tests/BENCHMARK_BASELINE.md`

## Task Completion Requirements

**MANDATORY: Before marking any task as complete, AI assistants MUST:**

1. **Run crackerjack verification**: Execute `python -m crackerjack -t --ai-agent` to run all quality checks and tests with AI-optimized output
2. **Fix any issues found**: Address all formatting, linting, type checking, and test failures
3. **Re-run verification**: Ensure crackerjack passes completely (all hooks pass, all tests pass)
4. **Document verification**: Mention that crackerjack verification was completed successfully

**Why this is critical:**
- Ensures all code meets project quality standards
- Prevents broken code from being committed
- Maintains consistency with project development workflow
- Catches issues early before they become problems

**Never skip crackerjack verification** - it's the project's standard quality gate.

## File Organization

### Source Structure
```
jinja2_async_environment/
├── __init__.py           # Public API exports
├── environment.py        # AsyncEnvironment, AsyncSandboxedEnvironment
├── loaders.py           # All async loader implementations
├── compiler.py          # AsyncCodeGenerator, async-aware compilation
└── bccache.py           # AsyncRedisBytecodeCache for performance
```

### Test Structure
```
tests/
├── BENCHMARK_BASELINE.md    # Performance baseline tracking
├── OPTIMIZATION_RESULTS.md  # Optimization analysis results
├── PERFORMANCE_SUMMARY.md   # Performance summary reports
├── test_environment.py      # Core environment tests
├── test_*_loader.py         # Loader-specific tests
├── test_benchmarks.py       # Performance benchmarks
├── test_realistic_optimization.py  # Real-world performance tests
└── test_*.py               # Component-specific test files
```

## Important Implementation Details

### Critical Performance Method
The `_async_yield_from()` method in `AsyncEnvironment` (environment.py:86) is the performance-critical path that was optimized from exception-based type detection to direct `hasattr()` checking, achieving 300x performance improvement. Any changes to this method require careful performance testing.

### Loader Interface
All async loaders implement the `AsyncLoaderProtocol` defined in loaders.py:29. When creating new loaders, follow this protocol and support both sync and async uptodate functions.

### Redis Caching
The `AsyncRedisBytecodeCache` provides significant performance improvements for compiled templates. Always test caching functionality when modifying compilation or template loading logic.

### Template Compilation
The `AsyncCodeGenerator` in `compiler.py` extends Jinja2's compiler with async-aware code generation. The `_compile()` method in `AsyncEnvironment` includes special handling for async syntax and yield statements to ensure proper async template rendering.
