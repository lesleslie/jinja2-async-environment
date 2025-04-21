# jinja2-async-environment

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)


## Asynchronous Jinja2 environment and loaders

`jinja2-async-environment` provides asynchronous alternatives to Jinja2's standard template environment and loaders, enabling non-blocking template operations in async applications. This library is ideal for high-performance web applications and APIs built with async frameworks like FastAPI, Starlette, FastBlocks, or AIOHTTP.

## Features

- **Fully Asynchronous Operations**: Load templates, render content, and cache results without blocking your application
- **Multiple Loader Types**:
  - `AsyncFileSystemLoader`: Load templates from the filesystem asynchronously
  - `AsyncPackageLoader`: Load templates from Python packages
  - `AsyncChoiceLoader`: Try multiple loaders in sequence
- **Redis Bytecode Caching**: Improve performance with async Redis bytecode caching
- **Modern Python**: Leverages `asyncio` with type hints compatible with Python 3.13+
- **Drop-in Replacement**: Familiar API for Jinja2 users with async alternatives
- **Type Safety**: Fully typed with modern Python typing protocols

## Installation

```
pip install jinja2-async-environment
```

## Requirements

- Python 3.13 or higher
- Jinja2
- aiopath
- redis (for bytecode caching)

## Usage

### Basic Template Rendering

```python
import asyncio
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader

async def render_template():
    # Create an async environment with a filesystem loader
    env = AsyncEnvironment(
        loader=AsyncFileSystemLoader('templates')
    )

    # Load and render a template asynchronously
    template = await env.get_template_async('hello.html')
    rendered = await template.render_async(name='World')

    return rendered

# Run the async function
if __name__ == "__main__":
    result = asyncio.run(render_template())
    print(result)
```

### Web Framework Integration (FastAPI Example)

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader

app = FastAPI()

# Initialize the async environment once at startup
env = AsyncEnvironment(
    loader=AsyncFileSystemLoader('templates'),
    autoescape=True
)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    template = await env.get_template_async("index.html")
    content = await template.render_async(
        request=request,
        title="Home Page"
    )
    return content
```

### Using Different Loaders

```python
from jinja2_async_environment.loaders import (
    AsyncFileSystemLoader,
    AsyncPackageLoader,
    AsyncChoiceLoader
)

# Load templates from filesystem
fs_loader = AsyncFileSystemLoader('templates')

# Load templates from a Python package
package_loader = AsyncPackageLoader('your_package', 'templates')

# Create a loader that tries multiple sources
choice_loader = AsyncChoiceLoader([
    fs_loader,  # First try the filesystem
    package_loader  # Then try the package
])

# Create environment with the choice loader
env = AsyncEnvironment(loader=choice_loader)
```

### With Bytecode Caching

```python
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
import redis.asyncio as redis

async def setup_environment():
    # Create a Redis client
    redis_client = redis.Redis(host="localhost", port=6379, db=0)

    # Set up bytecode caching for better performance
    bytecode_cache = AsyncRedisBytecodeCache(redis_client, prefix="jinja2_")

    # Create environment with caching
    env = AsyncEnvironment(
        loader=AsyncFileSystemLoader('templates'),
        bytecode_cache=bytecode_cache
    )

    return env
```

### Running Tests

```
pip install pytest pytest-asyncio pytest-cov
python -m pytest
```

For test coverage reporting:

```
python -m pytest --cov=jinja2_async_environment
```

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

BSD-3-Clause
