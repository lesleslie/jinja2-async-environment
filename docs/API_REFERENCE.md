# API Reference

## AsyncEnvironment

### Constructor

```python
AsyncEnvironment(
    loader: AsyncBaseLoader | None = None,
    cache_size: int = 400,
    auto_reload: bool = True,
    bytecode_cache: AsyncBytecodeCache | None = None,
    enable_async: bool = True,
    **options: t.Any
) -> None
```

### Key Methods

#### get_template_async

```python
async def get_template_async(
    self,
    name: str | Template | Undefined,
    parent: str | Template | None = None,
    globals: t.MutableMapping[str, t.Any] | None = None
) -> Template
```

#### select_template_async

```python
async def select_template_async(
    self,
    names: t.Iterable[str | Template],
    parent: str | None = None,
    globals: t.MutableMapping[str, t.Any] | None = None
) -> Template
```

#### get_or_select_template_async

```python
async def get_or_select_template_async(
    self,
    template_name_or_list: str | Template | t.Sequence[str | Template] | Undefined,
    parent: str | None = None,
    globals: t.MutableMapping[str, t.Any] | None = None
) -> Template
```

## Loaders

### AsyncBaseLoader

Base class for all async loaders.

#### Constructor

```python
AsyncBaseLoader(searchpath: AsyncPath | str | t.Sequence[AsyncPath | str])
```

#### Key Methods

- `get_source_async(environment: AsyncEnvironment, name: str) -> SourceType`
- `list_templates_async() -> list[str]`
- `load_async(environment: AsyncEnvironment, name: str, env_globals: dict[str, t.Any] | None = None) -> Template`

### AsyncFileSystemLoader

Loads templates from the filesystem asynchronously.

#### Constructor

```python
AsyncFileSystemLoader(
    searchpath: AsyncPath | str | t.Sequence[AsyncPath | str],
    encoding: str = "utf-8",
    followlinks: bool = False
)
```

### AsyncDictLoader

Loads templates from a dictionary in memory.

#### Constructor

```python
AsyncDictLoader(mapping: dict[str, str])
```

#### Additional Methods

- `add_template(name: str, source: str) -> None`
- `remove_template(name: str) -> None`
- `update_mapping(mapping: dict[str, str]) -> None`
- `clear_templates() -> None`
- `has_template(name: str) -> bool`

### AsyncFunctionLoader

Loads templates using a custom async function.

#### Constructor

```python
AsyncFunctionLoader(load_func: LoaderFunction | AsyncLoaderFunction)
```

### AsyncPackageLoader

Loads templates from Python packages.

#### Constructor

```python
AsyncPackageLoader(
    package_name: str,
    package_path: AsyncPath | str = "templates"
)
```

### AsyncChoiceLoader

Tries multiple loaders in sequence until one successfully loads the requested template.

#### Constructor

```python
AsyncChoiceLoader(loaders: t.Sequence[AsyncLoaderProtocol])
```

#### Additional Methods

- `add_loader(loader: AsyncLoaderProtocol) -> None`
- `insert_loader(index: int, loader: AsyncLoaderProtocol) -> None`
- `remove_loader(loader: AsyncLoaderProtocol) -> None`
- `clear_loaders() -> None`
- `get_loader_count() -> int`
- `get_loaders() -> list[AsyncLoaderProtocol]`

## AsyncSandboxedEnvironment

Provides sandboxed template execution for safe handling of untrusted templates.

### Constructor

```python
AsyncSandboxedEnvironment(
    loader: AsyncBaseLoader | None = None,
    cache_size: int = 400,
    auto_reload: bool = True,
    bytecode_cache: AsyncBytecodeCache | None = None,
    enable_async: bool = True,
    **options: t.Any
)
```

## Cache Classes

### AsyncBytecodeCache

Abstract base class for async bytecode caching.

### AsyncRedisBytecodeCache

Redis-based async bytecode caching implementation.

#### Constructor

```python
AsyncRedisBytecodeCache(
    client: redis.Redis,
    prefix: str = "jinja2",
    timeout: int = 300
)
```
