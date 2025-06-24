import typing as t
from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound, UndefinedError
from jinja2.runtime import Undefined
from jinja2_async_environment.environment import AsyncEnvironment


@pytest.fixture
def async_env() -> AsyncEnvironment:
    """Create an AsyncEnvironment instance for testing."""
    return AsyncEnvironment()


@pytest.mark.asyncio
async def test_async_yield_from_with_generator_function(
    async_env: AsyncEnvironment,
) -> None:
    """Test _async_yield_from with a generator function."""

    # Create a generator function
    def generator_func():
        yield "item1"
        yield "item2"
        yield "item3"

    # Call _async_yield_from with the generator function
    result = [item async for item in async_env._async_yield_from(generator_func())]

    # Verify the result
    assert result == ["item1", "item2", "item3"]


@pytest.mark.asyncio
async def test_async_yield_from_with_async_generator_function(
    async_env: AsyncEnvironment,
) -> None:
    """Test _async_yield_from with an async generator function."""

    # Create an async generator function
    async def async_generator_func():
        yield "async_item1"
        yield "async_item2"
        yield "async_item3"

    # Call _async_yield_from with the async generator function
    result = [
        item async for item in async_env._async_yield_from(async_generator_func())
    ]

    # Verify the result
    assert result == ["async_item1", "async_item2", "async_item3"]


@pytest.mark.asyncio
async def test_async_yield_from_with_type_error(async_env: AsyncEnvironment) -> None:
    """Test _async_yield_from with a non-generator object that raises TypeError."""

    # Create a non-generator object that will raise TypeError when iterated
    class NonGenerator:
        def __iter__(self) -> t.Iterator[str]:
            raise TypeError("Not a generator")

    # Call _async_yield_from with the non-generator object
    result = []
    with pytest.raises(TypeError):
        async for item in async_env._async_yield_from(NonGenerator()):
            result.append(item)


@pytest.mark.asyncio
async def test_get_template_async_with_parent(async_env: AsyncEnvironment) -> None:
    """Test get_template_async with a parent template."""
    # Mock the join_path method
    async_env.join_path = MagicMock(return_value="child_from_parent.html")

    # Mock the _load_template_async method
    template = MagicMock()
    async_env._load_template_async = AsyncMock(return_value=template)

    # Call get_template_async with a parent template
    result = await async_env.get_template_async("child.html", "parent.html")

    # Verify the result
    assert result is template
    async_env.join_path.assert_called_once_with("child.html", "parent.html")
    async_env._load_template_async.assert_called_once_with(
        "child_from_parent.html", None
    )


@pytest.mark.asyncio
async def test_select_template_async_with_undefined(
    async_env: AsyncEnvironment,
) -> None:
    """Test select_template_async with an Undefined object."""
    # Create an Undefined object
    undefined = Undefined(name="templates")

    # Call select_template_async with the Undefined object
    with pytest.raises(UndefinedError):
        await async_env.select_template_async(undefined)


@pytest.mark.asyncio
async def test_select_template_async_with_template_object(
    async_env: AsyncEnvironment,
) -> None:
    """Test select_template_async with a Template object."""
    # Create a Template object
    template = MagicMock()

    # Call select_template_async with the Template object
    result = await async_env.select_template_async([template])

    # Verify the result
    assert result is template


@pytest.mark.asyncio
async def test_select_template_async_with_parent_and_template_not_found(
    async_env: AsyncEnvironment,
) -> None:
    """Test select_template_async with a parent template and TemplateNotFound."""
    # Mock the join_path method
    async_env.join_path = MagicMock(return_value="child_from_parent.html")

    # Mock the _load_template_async method to raise TemplateNotFound
    async_env._load_template_async = AsyncMock(
        side_effect=TemplateNotFound("not found")
    )

    # Call select_template_async with a parent template
    with pytest.raises(TemplatesNotFound):
        await async_env.select_template_async(
            ["child1.html", "child2.html"], "parent.html"
        )

    # Verify the join_path was called for each template
    assert async_env.join_path.call_count == 2
    async_env.join_path.assert_any_call("child1.html", "parent.html")
    async_env.join_path.assert_any_call("child2.html", "parent.html")


@pytest.mark.asyncio
async def test_get_or_select_template_async_with_undefined(
    async_env: AsyncEnvironment,
) -> None:
    """Test get_or_select_template_async with an Undefined object."""
    # Create an Undefined object
    undefined = Undefined(name="template")

    # Mock the get_template_async method
    async_env.get_template_async = AsyncMock()

    # Call get_or_select_template_async with the Undefined object
    await async_env.get_or_select_template_async(undefined)

    # Verify get_template_async was called with the Undefined object
    async_env.get_template_async.assert_called_once_with(undefined, None, None)


@pytest.mark.asyncio
async def test_get_or_select_template_async_with_template_object(
    async_env: AsyncEnvironment,
) -> None:
    """Test get_or_select_template_async with a Template object."""
    # Create a Template object
    template = MagicMock()

    # Call get_or_select_template_async with the Template object
    result = await async_env.get_or_select_template_async(template)

    # Verify the result
    assert result is template


@pytest.mark.asyncio
async def test_get_or_select_template_async_with_sequence(
    async_env: AsyncEnvironment,
) -> None:
    """Test get_or_select_template_async with a sequence of templates."""
    # Create a sequence of templates
    templates = ["template1.html", "template2.html"]

    # Mock the select_template_async method
    template = MagicMock()
    async_env.select_template_async = AsyncMock(return_value=template)

    # Call get_or_select_template_async with the sequence
    result = await async_env.get_or_select_template_async(templates)

    # Verify the result
    assert result is template
    async_env.select_template_async.assert_called_once_with(templates, None, None)


@pytest.mark.asyncio
async def test_load_template_async_with_template_object(
    async_env: AsyncEnvironment,
) -> None:
    """Test _load_template_async with a Template object."""
    # Create a Template object
    template = MagicMock()

    # Call _load_template_async with the Template object
    result = await async_env._load_template_async(template, None)

    # Verify the result
    assert result is template


@pytest.mark.asyncio
async def test_load_template_async_with_string(async_env: AsyncEnvironment) -> None:
    """Test _load_template_async with a string."""
    # Mock the _get_template_async method
    template = MagicMock()
    async_env._get_template_async = AsyncMock(return_value=template)

    # Call _load_template_async with a string
    result = await async_env._load_template_async("template.html", None)

    # Verify the result
    assert result is template
    async_env._get_template_async.assert_called_once_with("template.html", None)


@pytest.mark.asyncio
async def test_load_template_async_with_sequence(async_env: AsyncEnvironment) -> None:
    """Test _load_template_async with a sequence of templates."""
    # Create a sequence of templates
    templates = ["template1.html", "template2.html"]

    # Mock the _get_template_async method to succeed for the second template
    template = MagicMock()
    async_env._get_template_async = AsyncMock(
        side_effect=[TemplateNotFound("not found"), template]
    )

    # Call _load_template_async with the sequence
    result = await async_env._load_template_async(templates, None)

    # Verify the result
    assert result is template
    assert async_env._get_template_async.call_count == 2
    async_env._get_template_async.assert_any_call("template1.html", None)
    async_env._get_template_async.assert_any_call("template2.html", None)


@pytest.mark.asyncio
async def test_load_template_async_with_sequence_all_not_found(
    async_env: AsyncEnvironment,
) -> None:
    """Test _load_template_async with a sequence of templates where all are not found."""
    # Create a sequence of templates
    templates = ["template1.html", "template2.html"]

    # Mock the _get_template_async method to fail for all templates
    async_env._get_template_async = AsyncMock(side_effect=TemplateNotFound("not found"))

    # Call _load_template_async with the sequence
    with pytest.raises(TemplatesNotFound) as excinfo:
        await async_env._load_template_async(templates, None)

    # Verify the exception contains all template names
    assert "template1.html" in str(excinfo.value)
    assert "template2.html" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_template_async_no_loader(async_env: AsyncEnvironment) -> None:
    """Test _get_template_async with no loader."""
    # Ensure the loader is None
    async_env.loader = None

    # Call _get_template_async
    with pytest.raises(TypeError, match="no loader for this environment specified"):
        await async_env._get_template_async("template.html", None)


@pytest.mark.asyncio
async def test_get_template_async_with_cache_hit(async_env: AsyncEnvironment) -> None:
    """Test _get_template_async with a cache hit."""
    # Set up the environment
    loader = AsyncMock()
    async_env.loader = loader
    async_env.cache = {}
    async_env.auto_reload = True

    # Create a template with is_up_to_date=True
    template = MagicMock()
    template.is_up_to_date = True

    # Add the template to the cache
    from weakref import ref

    cache_key = (ref(loader), "template.html")
    async_env.cache[cache_key] = template

    # Call _get_template_async
    result = await async_env._get_template_async("template.html", None)

    # Verify the result is from the cache
    assert result is template


@pytest.mark.asyncio
async def test_get_template_async_with_cache_hit_and_async_is_up_to_date(
    async_env: AsyncEnvironment,
) -> None:
    """Test _get_template_async with a cache hit and async is_up_to_date."""
    # Set up the environment
    loader = AsyncMock()
    async_env.loader = loader
    async_env.cache = {}
    async_env.auto_reload = True

    # Create a template with async is_up_to_date
    template = MagicMock()
    template.is_up_to_date = AsyncMock(return_value=True)

    # Add the template to the cache
    from weakref import ref

    cache_key = (ref(loader), "template.html")
    async_env.cache[cache_key] = template

    # Call _get_template_async
    result = await async_env._get_template_async("template.html", None)

    # Verify the result is from the cache and is_up_to_date was called
    assert result is template
    template.is_up_to_date.assert_called_once()


@pytest.mark.asyncio
async def test_get_template_async_with_cache_hit_and_auto_reload_false(
    async_env: AsyncEnvironment,
) -> None:
    """Test _get_template_async with a cache hit and auto_reload=False."""
    # Set up the environment
    loader = AsyncMock()
    async_env.loader = loader
    async_env.cache = {}
    async_env.auto_reload = False

    # Create a template
    template = MagicMock()

    # Add the template to the cache
    from weakref import ref

    cache_key = (ref(loader), "template.html")
    async_env.cache[cache_key] = template

    # Call _get_template_async
    result = await async_env._get_template_async("template.html", None)

    # Verify the result is from the cache and is_up_to_date was not called
    assert result is template
    assert not hasattr(template, "is_up_to_date") or not template.is_up_to_date.called


@pytest.mark.asyncio
async def test_get_template_async_with_cache_hit_and_globals(
    async_env: AsyncEnvironment,
) -> None:
    """Test _get_template_async with a cache hit and globals."""
    # Set up the environment
    loader = AsyncMock()
    async_env.loader = loader
    async_env.cache = {}
    async_env.auto_reload = True

    # Create a template with is_up_to_date=True
    template = MagicMock()
    template.is_up_to_date = True
    template.globals = {}

    # Add the template to the cache
    from weakref import ref

    cache_key = (ref(loader), "template.html")
    async_env.cache[cache_key] = template

    # Call _get_template_async with globals
    globals_dict = {"var1": "value1", "var2": "value2"}
    result = await async_env._get_template_async("template.html", globals_dict)

    # Verify the result is from the cache and globals were updated
    assert result is template
    assert template.globals == globals_dict


@pytest.mark.asyncio
async def test_get_template_async_with_cache_miss(async_env: AsyncEnvironment) -> None:
    """Test _get_template_async with a cache miss."""
    # Set up the environment
    loader = AsyncMock()
    async_env.loader = loader
    async_env.cache = {}

    # Create a template
    template = MagicMock()

    # Mock the loader.load_async method
    loader.load_async = AsyncMock(return_value=template)

    # Call _get_template_async
    result = await async_env._get_template_async("template.html", None)

    # Verify the result and that load_async was called
    assert result is template
    # The environment adds default globals, so we can't check for an empty dict
    assert loader.load_async.call_count == 1
    args, kwargs = loader.load_async.call_args
    assert args[0] is async_env
    assert args[1] == "template.html"
    assert kwargs is not None  # Use kwargs to satisfy linter

    # Verify the template was added to the cache
    from weakref import ref

    cache_key = (ref(loader), "template.html")
    assert async_env.cache[cache_key] is template


@pytest.mark.asyncio
async def test_get_template_async_with_cache_miss_and_globals(
    async_env: AsyncEnvironment,
) -> None:
    """Test _get_template_async with a cache miss and globals."""
    # Set up the environment
    loader = AsyncMock()
    async_env.loader = loader
    async_env.cache = {}

    # Create a template
    template = MagicMock()

    # Mock the loader.load_async method
    loader.load_async = AsyncMock(return_value=template)

    # Mock the make_globals method
    globals_dict = {"var1": "value1", "var2": "value2"}
    processed_globals = {"var1": "processed1", "var2": "processed2"}
    async_env.make_globals = MagicMock(return_value=processed_globals)

    # Call _get_template_async with globals
    result = await async_env._get_template_async("template.html", globals_dict)

    # Verify the result and that load_async was called with processed globals
    assert result is template
    async_env.make_globals.assert_called_once_with(globals_dict)
    loader.load_async.assert_called_once_with(
        async_env, "template.html", processed_globals
    )
