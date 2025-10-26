# Project Overview

This project, `jinja2-async-environment`, is a Python library that provides an asynchronous version of the popular Jinja2 templating engine. It's designed for use in asynchronous web frameworks like FastAPI, Starlette, and AIOHTTP. The key features include:

- **Fully Asynchronous:** All template operations (loading, rendering, caching) are non-blocking.
- **Jinja2 Compatibility:** It aims for 100% compatibility with Jinja2, including macros, inheritance, and filters.
- **Performance:** The library is optimized for performance, with benchmarks showing it can be faster than the standard Jinja2 in some scenarios.
- **Async Loaders:** It provides asynchronous versions of Jinja2's template loaders, such as `AsyncFileSystemLoader`, `AsyncPackageLoader`, and `AsyncDictLoader`.
- **Bytecode Caching:** Supports asynchronous bytecode caching with Redis to improve performance.
- **Sandboxed Execution:** Includes an `AsyncSandboxedEnvironment` for safely rendering untrusted templates.

The project is built using modern Python features (Python 3.13+) and is fully type-hinted.

# Building and Running

The project uses `hatchling` for building and `pytest` for testing.

## Installation

To install the package for use in another project:

```bash
pip install jinja2-async-environment
```

For development, you can install it in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

## Running Tests

Tests are run using `pytest`. The configuration in `pyproject.toml` specifies the test paths and options. To run the tests:

```bash
pytest
```

The tests include unit tests, integration tests, and benchmarks. The test coverage is configured to fail if it drops below 69%.

# Development Conventions

- **Code Style:** The project follows the `crackerjack` code style, which is enforced by the `ruff` linter.
- **Linting:** `ruff` is used for linting and formatting. The configuration is in `pyproject.toml`.
- **Type Checking:** `pyright` is used for static type checking in "strict" mode.
- **Testing:** `pytest` is the testing framework. Tests are located in the `tests/` directory. New features should be accompanied by comprehensive tests.
- **Contributions:** The `README.md` file outlines the contribution process, which includes forking the repository, creating a feature branch, adding tests, and submitting a pull request.
