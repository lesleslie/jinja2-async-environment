# jinja2-async-environment - Project Context

## Project Overview

`jinja2-async-environment` is a Python library that provides asynchronous alternatives to Jinja2's standard template environment and loaders. The library enables non-blocking template operations in async applications while maintaining 100% Jinja2 compatibility, including complete macro support. It's designed for high-performance web applications and APIs built with async frameworks like FastAPI, Starlette, or AIOHTTP.

### Key Features

- Fully asynchronous template loading, rendering, and caching operations
- 100% Jinja2 compatibility including all macro features
- Multiple async loader types (FileSystem, Package, Dict, Function, Choice)
- Redis bytecode caching support
- Sandboxed execution environment for safe template execution
- Modern Python 3.13+ with full type hints
- Drop-in replacement API for existing Jinja2 applications

## Project Structure

```
jinja2-async-environment/
├── jinja2_async_environment/           # Main source code
│   ├── __init__.py                     # Package exports
│   ├── environment.py                  # Core AsyncEnvironment and AsyncSandboxedEnvironment
│   ├── bccache.py                      # Async bytecode caching (Redis support)
│   ├── compiler.py                     # Async code generation
│   ├── compiler_modules/               # Modular compiler implementation
│   │   ├── codegen.py                  # AsyncCodeGenerator implementation
│   │   ├── cache.py                    # Compilation caching
│   │   ├── dependencies.py             # Dependency resolution
│   │   ├── frame.py                    # Async frame handling
│   │   ├── loops.py                    # Loop code generation
│   │   └── patterns.py                 # Compiled patterns
│   ├── loaders/                        # Async template loaders
│   │   ├── __init__.py                 # Loader exports
│   │   ├── base.py                     # AsyncBaseLoader and protocols
│   │   ├── filesystem.py               # AsyncFileSystemLoader
│   │   ├── package.py                  # AsyncPackageLoader
│   │   ├── dict.py                     # AsyncDictLoader
│   │   ├── function.py                 # AsyncFunctionLoader
│   │   └── choice.py                   # AsyncChoiceLoader
│   └── caching/                        # Advanced caching infrastructure
│       ├── __init__.py                 # Cache exports
│       ├── manager.py                  # Cache manager
│       ├── strategies.py               # Cache strategies
│       ├── typed.py                    # Typed cache
│       └── unified.py                  # Unified cache
├── tests/                              # Comprehensive test suite
├── pyproject.toml                      # Project configuration
├── README.md                           # Documentation
└── CHANGELOG.md                        # Version history
```

## Core Components

### AsyncEnvironment

The main entry point that provides asynchronous alternatives to Jinja2's Environment:

```python
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader

# Create async environment
env = AsyncEnvironment(loader=AsyncFileSystemLoader("templates"))

# Load and render template asynchronously
template = await env.get_template_async("hello.html")
rendered = await template.render_async(name="World")
```

### Async Loaders

Multiple loader types for different template sources:

- `AsyncFileSystemLoader`: Load templates from filesystem
- `AsyncPackageLoader`: Load templates from Python packages
- `AsyncDictLoader`: Load templates from in-memory dictionary
- `AsyncFunctionLoader`: Load templates with custom async functions
- `AsyncChoiceLoader`: Try multiple loaders in sequence

### Async Sandboxed Environment

For secure template execution in untrusted environments:

```python
from jinja2_async_environment.environment import AsyncSandboxedEnvironment

sandbox_env = AsyncSandboxedEnvironment(loader=AsyncDictLoader(templates))
```

### Async Bytecode Caching

Redis-based bytecode caching for improved performance:

```python
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
import redis.asyncio as redis

redis_client = redis.Redis(host="localhost", port=6379, db=0)
bytecode_cache = AsyncRedisBytecodeCache(client=redis_client, prefix="jinja2_")

env = AsyncEnvironment(
    loader=AsyncFileSystemLoader("templates"), bytecode_cache=bytecode_cache
)
```

## Development Environment

### Prerequisites

- Python 3.13+
- Dependencies specified in `pyproject.toml`

### Key Dependencies

- `anyio>=4.9` - Async I/O library
- `jinja2>=3.1.6` - Core templating engine
- `redis>=3.5.3` - Redis client for bytecode caching

### Development Dependencies

- `pytest` and `pytest-asyncio` for testing
- `crackerjack` for code formatting
- `pyright` for type checking
- Various linting and quality tools

## Building and Testing

### Installation

```bash
pip install jinja2-async-environment
```

For development:

```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=jinja2_async_environment

# Run specific test modules
python -m pytest tests/test_async_environment.py
```

### Code Quality

The project uses several tools for code quality:

- `ruff` for linting and formatting
- `pyright` for type checking
- `codespell` for spell checking
- `bandit` for security scanning

### Building Distribution

```bash
# Build the package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

## Usage Patterns

### Basic Template Rendering

```python
import asyncio
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader


async def render_template():
    env = AsyncEnvironment(loader=AsyncFileSystemLoader("templates"))
    template = await env.get_template_async("hello.html")
    rendered = await template.render_async(name="World")
    return rendered


result = asyncio.run(render_template())
```

### Web Framework Integration (FastAPI)

```python
from fastapi import FastAPI
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader

app = FastAPI()
env = AsyncEnvironment(loader=AsyncFileSystemLoader("templates"))


@app.get("/")
async def read_root():
    template = await env.get_template_async("index.html")
    content = await template.render_async(title="Home Page")
    return content
```

### Using Macros

The library provides 100% compatible Jinja2 macro support:

```python
templates = {
    "macros.html": """
{%- macro render_user(name, age, city='Unknown') -%}
<div class="user">
    <h3>{{ name }}</h3>
    <p>Age: {{ age }}</p>
    <p>City: {{ city }}</p>
</div>
{%- endmacro -%}""",
    "page.html": """
{% from 'macros.html' import render_user %}
<h1>User Directory</h1>
{{ render_user('Alice', 30, 'New York') }}
{{ render_user('Bob', 25) }}""",
}

env = AsyncEnvironment(loader=AsyncDictLoader(templates))
template = await env.get_template_async("page.html")
result = await template.render_async()
```

## Performance Characteristics

The library provides superior performance compared to standard Jinja2:

- 0.8-1.0x rendering speed (faster in most scenarios)
- 1.23x concurrent processing performance
- Optimized async generator handling (~300x improvement in hot paths)
- Efficient memory usage with `__slots__` in key classes
- Smart caching strategies

## Contributing

The project welcomes contributions. Key areas for contribution:

1. Bug fixes and performance improvements
1. New loader implementations
1. Additional caching strategies
1. Documentation improvements
1. Test coverage expansion

Follow the standard fork-branch-pull request workflow and ensure all tests pass before submitting.
