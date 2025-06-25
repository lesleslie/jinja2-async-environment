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
  - `AsyncDictLoader`: Load templates from a dictionary in memory
  - `AsyncFunctionLoader`: Load templates using custom async functions
  - `AsyncChoiceLoader`: Try multiple loaders in sequence
- **Redis Bytecode Caching**: Improve performance with async Redis bytecode caching
- **Sandboxed Execution**: `AsyncSandboxedEnvironment` for safe template execution in untrusted environments
- **Modern Python**: Leverages `asyncio` with type hints compatible with Python 3.13+
- **Drop-in Replacement**: Familiar API for Jinja2 users with async alternatives
- **Type Safety**: Fully typed with modern Python typing protocols

## Installation

```
pip install jinja2-async-environment
```

## Requirements

- Python 3.13 or higher
- Jinja2 3.1.6+
- anyio 4.9+
- redis 6.2+ (for bytecode caching)

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

    # Render the template with context variables
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
    # Get and render template asynchronously
    template = await env.get_template_async("index.html")

    # Render with context variables
    content = await template.render_async(
        request=request,
        title='Home Page'
    )

    return content
```

### Web Framework Integration (Starlette Example)

```python
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader

# Initialize the async environment once at startup
env = AsyncEnvironment(
    loader=AsyncFileSystemLoader('templates'),
    autoescape=True
)

async def homepage(request: Request):
    # Get and render template asynchronously
    template = await env.get_template_async("index.html")

    # Render with context variables
    content = await template.render_async(
        request=request,
        title='Starlette Home Page'
    )

    return HTMLResponse(content)

# Define routes
routes = [
    Route('/', endpoint=homepage)
]

# Create Starlette application
app = Starlette(routes=routes)
```

### Using Different Loaders

```python
from jinja2_async_environment.loaders import (
    AsyncFileSystemLoader,
    AsyncPackageLoader,
    AsyncDictLoader,
    AsyncFunctionLoader,
    AsyncChoiceLoader
)

# Load templates from filesystem
fs_loader = AsyncFileSystemLoader('templates')

# Load templates from a Python package
package_loader = AsyncPackageLoader('your_package', 'templates')

# Load templates from a dictionary
templates_dict = {
    'hello.html': '<h1>Hello {{ name }}!</h1>',
    'goodbye.html': '<p>Goodbye {{ name }}.</p>'
}
dict_loader = AsyncDictLoader(templates_dict, '/virtual')

# Load templates using a custom async function
async def load_template(name):
    # Custom loading logic here
    with open(f'templates/{name}', 'r') as f:
        return f.read(), f'templates/{name}', lambda: True

function_loader = AsyncFunctionLoader(load_template, 'templates')

# Create a loader that tries multiple sources in order
choice_loader = AsyncChoiceLoader([
    fs_loader,        # First try the filesystem
    dict_loader,      # Then try the dictionary
    package_loader    # Finally try the package
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
    bytecode_cache = AsyncRedisBytecodeCache(client=redis_client, prefix="jinja2_")

    # Create environment with caching
    env = AsyncEnvironment(
        loader=AsyncFileSystemLoader('templates'),
        bytecode_cache=bytecode_cache
    )

    return env

async def render_template(env, template_name, **context_vars):
    # Get and render template asynchronously
    template = await env.get_template_async(template_name)

    # Render with context variables
    return await template.render_async(**context_vars)
```

### Sandboxed Template Execution

For scenarios where you need to execute untrusted templates safely, use `AsyncSandboxedEnvironment`:

```python
import asyncio
from jinja2.exceptions import SecurityError
from jinja2_async_environment.environment import AsyncSandboxedEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader

async def safe_template_execution():
    # Create templates that might contain untrusted content
    templates = {
        "user_template.html": "Hello {{ name }}! Your score is {{ score + 10 }}.",
        "unsafe_template.html": "{{ ''.__class__.__mro__[1].__subclasses__() }}"  # This will be blocked
    }

    # Create a sandboxed environment
    sandbox_env = AsyncSandboxedEnvironment(
        loader=AsyncDictLoader(templates, "/sandbox")
    )

    # Safe template execution
    safe_template = await sandbox_env.get_template_async("user_template.html")
    result = await safe_template.render_async(name="Alice", score=85)
    print(result)  # Output: Hello Alice! Your score is 95.

    # Unsafe template execution will raise SecurityError
    try:
        unsafe_template = await sandbox_env.get_template_async("unsafe_template.html")
        await unsafe_template.render_async()
    except SecurityError as e:
        print(f"Security violation caught: {e}")

# Run the example
asyncio.run(safe_template_execution())
```

The sandboxed environment provides protection against:
- Access to Python internals and dangerous built-ins
- File system access attempts
- Import statements and module access
- Execution of arbitrary Python code

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
