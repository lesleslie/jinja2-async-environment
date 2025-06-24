from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jinja2 import nodes
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound, UndefinedError
from jinja2.runtime import Undefined
from jinja2_async_environment.environment import AsyncEnvironment


@pytest.fixture
def async_env() -> AsyncEnvironment:
    """Create an AsyncEnvironment instance for testing."""
    return AsyncEnvironment()


def test_async_environment_init() -> None:
    """Test initialization of AsyncEnvironment."""
    env = AsyncEnvironment()

    assert env.enable_async
    assert env.code_generator_class is not None


def test_generate(async_env: AsyncEnvironment) -> None:
    """Test the _generate method."""
    # Create a mock source
    source = MagicMock(spec=nodes.Template)

    # Call the method
    with patch.object(async_env.code_generator_class, "generate") as mock_generate:
        mock_generate.return_value = "generated code"
        result = async_env._generate(source, "test_template", "test.py")

    # Verify the result
    assert result == "generated code"


def test_compile(async_env: AsyncEnvironment) -> None:
    """Test the _compile method."""
    # Test normal compilation
    source = "def test(): pass"
    result = async_env._compile(source, "test.py")

    # Verify the result is a code object
    assert result is not None

    # Test compilation with SyntaxError but without async code
    with pytest.raises(SyntaxError):
        async_env._compile("def test() yield from", "test.py")

    # Test compilation with SyntaxError and async code
    source = """
async def test():
    yield from context.blocks
    """
    result = async_env._compile(source, "test.py")

    # Verify the result is a code object
    assert result is not None


@pytest.mark.asyncio
async def test_async_yield_from(async_env: AsyncEnvironment) -> None:
    """Test the _async_yield_from method."""

    # Test with an async generator
    async def async_generator():
        yield "item1"
        yield "item2"

    result = [item async for item in async_env._async_yield_from(async_generator())]

    assert result == ["item1", "item2"]

    # Test with a regular generator
    def regular_generator():
        yield "item1"
        yield "item2"

    result = [item async for item in async_env._async_yield_from(regular_generator())]

    assert result == ["item1", "item2"]


@pytest.mark.asyncio
async def test_get_template_async(async_env: AsyncEnvironment) -> None:
    """Test the get_template_async method."""
    # Mock the _load_template_async method
    template = MagicMock()
    async_env._load_template_async = AsyncMock(return_value=template)

    # Test with a template instance
    result = await async_env.get_template_async(template)
    assert result is template

    # Test with a template name
    result = await async_env.get_template_async("template.html")
    assert result is template

    # Test with a parent template
    result = await async_env.get_template_async("template.html", parent="parent.html")
    assert result is template


@pytest.mark.asyncio
async def test_select_template_async(async_env: AsyncEnvironment) -> None:
    """Test the select_template_async method."""
    # Mock the _load_template_async method
    template = MagicMock()
    async_env._load_template_async = AsyncMock(return_value=template)

    # Test with a list of template names
    result = await async_env.select_template_async(["template1.html", "template2.html"])
    assert result is template

    # Test with an empty list
    with pytest.raises(TemplatesNotFound):
        await async_env.select_template_async([])

    # Test with an Undefined object
    undefined = Undefined(name="templates")
    with pytest.raises(UndefinedError):
        await async_env.select_template_async(undefined)

    # Test with a template instance in the list
    result = await async_env.select_template_async([template])
    assert result is template

    # Test with a parent template
    result = await async_env.select_template_async(
        ["template1.html"], parent="parent.html"
    )
    assert result is template

    # Test with all templates not found
    async_env._load_template_async = AsyncMock(
        side_effect=TemplateNotFound("not found")
    )
    with pytest.raises(TemplatesNotFound):
        await async_env.select_template_async(["template1.html", "template2.html"])


@pytest.mark.asyncio
async def test_get_or_select_template_async(async_env: AsyncEnvironment) -> None:
    """Test the get_or_select_template_async method."""
    # Mock the get_template_async and select_template_async methods
    template = MagicMock()
    async_env.get_template_async = AsyncMock(return_value=template)
    async_env.select_template_async = AsyncMock(return_value=template)

    # Test with a string
    result = await async_env.get_or_select_template_async("template.html")
    assert result is template
    async_env.get_template_async.assert_called_once()

    # Test with a template instance
    async_env.get_template_async.reset_mock()
    result = await async_env.get_or_select_template_async(template)
    assert result is template
    async_env.get_template_async.assert_not_called()

    # Test with a list
    async_env.get_template_async.reset_mock()
    result = await async_env.get_or_select_template_async(
        ["template1.html", "template2.html"]
    )
    assert result is template
    async_env.select_template_async.assert_called_once()


@pytest.mark.asyncio
async def test_load_template_async(async_env: AsyncEnvironment) -> None:
    """Test the _load_template_async method."""
    # Mock the _get_template_async method
    template = MagicMock()
    async_env._get_template_async = AsyncMock(return_value=template)

    # Test with a template instance
    result = await async_env._load_template_async(template, None)
    assert result is template

    # Test with a template name
    result = await async_env._load_template_async("template.html", None)
    assert result is template

    # Test with a list of template names (first one found)
    async_env._get_template_async = AsyncMock(return_value=template)
    result = await async_env._load_template_async(
        ["template1.html", "template2.html"], None
    )
    assert result is template

    # Test with a list of template names (first one not found)
    async_env._get_template_async = AsyncMock(
        side_effect=[TemplateNotFound("not found"), template]
    )
    result = await async_env._load_template_async(
        ["template1.html", "template2.html"], None
    )
    assert result is template

    # Test with a list of template names (all not found)
    async_env._get_template_async = AsyncMock(side_effect=TemplateNotFound("not found"))
    with pytest.raises(TemplatesNotFound):
        await async_env._load_template_async(["template1.html", "template2.html"], None)


@pytest.mark.asyncio
async def test_get_template_async_with_cache(async_env: AsyncEnvironment) -> None:
    """Test the _get_template_async method with cache."""
    # Mock the loader
    loader = MagicMock()
    template = MagicMock()
    template.is_up_to_date = True

    # Set up the environment
    async_env.loader = loader
    async_env.cache = {}

    # Mock the loader.load_async method
    loader.load_async = AsyncMock(return_value=template)

    # Call the method
    result = await async_env._get_template_async("template.html", None)

    # Verify the result
    assert result is template

    # Call again to test cache
    result = await async_env._get_template_async("template.html", None)

    # Verify the result and that load_async was only called once
    assert result is template
    assert loader.load_async.call_count == 1

    # Test with an async is_up_to_date method
    template.is_up_to_date = AsyncMock(return_value=True)

    # Clear the cache and call again
    async_env.cache = {}
    result = await async_env._get_template_async("template.html", None)

    # Verify the result
    assert result is template

    # Call again to test cache with async is_up_to_date
    result = await async_env._get_template_async("template.html", None)

    # Verify the result and that is_up_to_date was called
    assert result is template
    assert template.is_up_to_date.call_count == 1
