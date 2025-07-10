# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `jinja2-async-environment`, an async-first template engine that extends Jinja2 with comprehensive asynchronous support. It provides non-blocking template operations for high-performance web applications using FastAPI, Starlette, AIOHTTP, and similar async frameworks.

## Development Commands

### Package Management
```bash
# Primary package manager
pdm install          # Install dependencies
pdm add <package>    # Add new dependency
pdm lock             # Update lock file

# Alternative (UV also supported)
uv sync              # Install from uv.lock
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

# Run with coverage
pytest --cov=jinja2_async_environment

# Run benchmarks only
pytest -m benchmark tests/test_benchmarks.py

# Run realistic performance tests
pytest tests/test_realistic_optimization.py
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

- Minimum Python 3.13+ required
- Uses PDM for dependency management (UV also supported)
- Strict type checking with Pyright - all new code must be fully typed
- Pre-commit hooks enforce comprehensive code quality (formatting, linting, security, performance)
- Performance regressions are tracked via benchmark tests in `tests/` directory

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
