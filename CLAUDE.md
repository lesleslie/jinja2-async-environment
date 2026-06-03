# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

For a shorter, tool-neutral bootstrap document, start with `AGENTS.md`.

## Project Overview

`jinja2-async-environment` is an async-first extension of Jinja2 aimed at preserving Jinja compatibility while making template loading, compilation, and rendering work well in async applications.

Important goals:

- preserve expected Jinja behavior unless a change is explicitly async-specific
- keep async paths genuinely non-blocking
- protect the package's performance-sensitive code paths

## Key Paths

- `jinja2_async_environment/environment.py`: main async environment
- `jinja2_async_environment/loaders/`: async loader implementations
- `jinja2_async_environment/compiler_modules/`: code generation and compiler helpers
- `jinja2_async_environment/caching/`: cache management and strategies
- `tests/`: unit, integration, benchmark, and regression coverage

## Development Commands

### Setup

```bash
uv sync
```

### Standard Quality Gate

```bash
python -m crackerjack -t --ai-agent
```

Run that before considering work complete. For targeted iteration, use:

```bash
ruff format
ruff check
pyright
pytest
pytest -m unit
pytest -m integration
pytest --cov=jinja2_async_environment
```

## Architecture Notes

The package is organized around four concerns:

- environment orchestration
- async loaders
- compiler/codegen helpers
- caching and bytecode support

When making changes:

- prefer extending the modular subsystems instead of rebuilding monolithic logic
- preserve compatibility expectations for sync behavior, macro behavior, and loader contracts
- keep async work non-blocking and isolate any unavoidable sync fallback clearly
- treat performance-sensitive helpers as hot paths and benchmark them when behavior changes

## Performance Guidance

This repo cares about performance as a product feature. Be careful around:

- loader caching behavior
- compiler dependency resolution
- template compilation caches
- async iteration and render hot paths

If a change touches those areas, run focused tests or benchmarks and call out any measurable effect in the result.

## Testing Focus

- environment changes: cover rendering semantics and compatibility behavior
- loader changes: add filesystem/package/dict/function-loader coverage as relevant
- compiler changes: add regression tests for generated output and edge-case templates
- cache changes: verify invalidation, TTL behavior, and isolation between tests

Use `AsyncMock` for async behavior and keep tests isolated from shared cache state.

## Working Rules

- Do not trade correctness for async cleverness.
- Do not introduce blocking I/O into async code paths without explicit isolation.
- Do not change compatibility-sensitive behavior without tests that show the intended delta.
- Keep historical refactor notes and long benchmark narratives in dedicated docs, not here.
