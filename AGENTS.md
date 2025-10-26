# Repository Guidelines

## Project Structure & Module Organization

`jinja2_async_environment/` contains the async environment, loaders, compiler modules, and caching utilities; review `environment.py` first, then dive into `loaders/`, `compiler_modules/`, and `caching/` when touching specialization. Tests live in `tests/`, mirroring package layout with `test_*.py` files and marker-specific suites. Documentation, changelogs, and benchmarking notes sit in `docs/` and topical `*.md` files at the root. Build artifacts land in `dist/`; avoid editing generated content directly.

## Build, Test & Development Commands

Use UV for dependency management: `uv sync` bootstraps the virtualenv defined by `uv.lock`. Run the holistic quality gate with `python -m crackerjack -t --ai-agent` before sharing changes—it executes lint, type-check, and test bundles. Individual tools remain available: `ruff format` enforces the 88-character formatter, `ruff check` handles linting, and `pyright` runs strict type analysis. Execute `pytest` (or `pytest -m unit` / `pytest -m integration`) for targeted runs; append `--cov=jinja2_async_environment` when asserting coverage locally.

## Coding Style & Naming Conventions

Code targets Python 3.13+ with standard four-space indentation and exhaustive type hints. Follow snake_case for functions, async coroutines, and module names; prefer PascalCase for classes and TypedDicts. Keep async APIs truly non-blocking—wrap sync fallbacks in thread pools when necessary. Let `ruff` autofix trivial issues, and keep imports sorted per the configured isort profile (no blank line before first-party imports).

## Testing Guidelines

Pytest discovers files named `test_*.py` or `*_test.py`; align helper modules under the same patterns when practical. Mark tests with `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.benchmark` to integrate with existing selection flags. The default run enforces coverage via `--cov-fail-under=69`; do not regress this threshold. Prefer async fixtures and the `asyncio` event loop provided by `pytest-asyncio` instead of manual loop management.

## Commit & Pull Request Guidelines

Commits follow a Conventional Commit variant such as `test(config): update 5 files`; keep scopes small and messages in the imperative mood. Reference related issues in the body when applicable and note any benchmarks or coverage deltas. Before opening a PR, confirm `python -m crackerjack -t --ai-agent` passes, describe architectural changes, and attach relevant log excerpts or screenshots for benchmark-affecting work.
