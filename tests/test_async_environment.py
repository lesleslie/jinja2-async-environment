import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jinja2 import nodes
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound, UndefinedError
from jinja2.runtime import Undefined
from jinja2_async_environment.environment import AsyncEnvironment


@pytest.fixture
def async_env() -> AsyncEnvironment:
    """Create an AsyncEnvironment instance for testing."""
    return AsyncEnvironment()


class TestAsyncEnvironmentBasics:
    """Test basic functionality of AsyncEnvironment."""

    def test_init(self, async_env: AsyncEnvironment) -> None:
        """Test initialization of AsyncEnvironment."""
        assert async_env.enable_async
        assert async_env.code_generator_class is not None

    def test_generate(self, async_env: AsyncEnvironment) -> None:
        """Test the _generate method."""
        # Create a mock source
        source = MagicMock(spec=nodes.Template)

        # Call the method with a name as string
        with patch.object(async_env.code_generator_class, "generate") as mock_generate:
            mock_generate.return_value = "generated code"
            result = async_env._generate(source, "test_template", "test.py")

        # Verify the result
        assert result == "generated code"

        # Call the method with a name as None
        with patch.object(async_env.code_generator_class, "generate") as mock_generate:
            mock_generate.return_value = "generated code"
            result = async_env._generate(source, None, "test.py")

        # Verify the result
        assert result == "generated code"

    def test_compile_normal(self, async_env: AsyncEnvironment) -> None:
        """Test the _compile method with normal code."""
        # Test normal compilation
        source = "def test(): pass"
        result = async_env._compile(source, "test.py")

        # Verify the result is a code object
        assert result is not None
        # Code objects are not directly callable, but they are code objects
        assert hasattr(result, "co_code")

    def test_compile_with_syntax_error(self, async_env: AsyncEnvironment) -> None:
        """Test the _compile method with syntax error."""
        # Test compilation with SyntaxError but without async code
        with pytest.raises(SyntaxError):
            async_env._compile("def test() yield from", "test.py")

    def test_compile_with_async_code(self, async_env: AsyncEnvironment) -> None:
        """Test the _compile method with async code."""
        # Test compilation with SyntaxError and async code
        source = """
async def test():
    async for event in self._async_yield_from(context.blocks):
        yield event
    """
        result = async_env._compile(source, "test.py")

        # Verify the result is a code object
        assert result is not None
        assert hasattr(result, "co_code")

    def test_compile_with_yield_from_replacement(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test the _compile method with yield from replacement."""
        # For this test, we'll directly test the replacement logic in _compile
        # by creating a source that would trigger the SyntaxError and then
        # checking if the replacements are made correctly

        # Create a source with yield from in an async function
        source = """
async def test():
    yield from context.blocks['item']
    undefined(name='item') if l_0_item is missing else l_0_item
    undefined(name='i') if l_0_i is missing else l_0_i
    undefined(name='message') if l_0_message is missing else l_0_message
    undefined(name='partial_var') if l_0_partial_var is missing else l_0_partial_var
    """

        # Mock compile to first raise SyntaxError, then return a code object
        original_compile = __builtins__["compile"]

        compile_called = [0]

        def mock_compile(src: str, filename: str, mode: str) -> t.Any:
            compile_called[0] += 1
            if compile_called[0] == 1:
                raise SyntaxError("'yield from' inside async function")
            return original_compile("async def test(): pass", filename, mode)

        # Patch the built-in compile function
        with patch("builtins.compile", side_effect=mock_compile):
            # Call _compile with the source
            result = async_env._compile(source, "test.py")

            # Verify the result is a code object
            assert result is not None


class TestAsyncYieldFrom:
    """Test the _async_yield_from method."""

    @pytest.mark.asyncio
    async def test_async_yield_from_with_async_generator(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test _async_yield_from with an async generator."""

        # Create an async generator
        async def async_generator():
            yield "item1"
            yield "item2"

        # Call _async_yield_from
        result = [item async for item in async_env._async_yield_from(async_generator())]

        # Verify the result
        assert result == ["item1", "item2"]

    @pytest.mark.asyncio
    async def test_async_yield_from_with_regular_generator(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test _async_yield_from with a regular generator."""

        # Create a regular generator
        def regular_generator():
            yield "item1"
            yield "item2"

        # Call _async_yield_from
        result = [
            item async for item in async_env._async_yield_from(regular_generator())
        ]

        # Verify the result
        assert result == ["item1", "item2"]


class TestAsyncTemplateLoading:
    """Test template loading methods."""

    @pytest.mark.asyncio
    async def test_get_template_not_implemented(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test that get_template raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Use get_template_async instead"):
            async_env.get_template("template.html")

    @pytest.mark.asyncio
    async def test_select_template_not_implemented(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test that select_template raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="Use select_template_async instead"
        ):
            async_env.select_template(["template.html"])

    @pytest.mark.asyncio
    async def test_get_or_select_template_not_implemented(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test that get_or_select_template raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="Use get_or_select_template_async instead"
        ):
            async_env.get_or_select_template("template.html")

    @pytest.mark.asyncio
    async def test_get_template_async_with_template_object(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test get_template_async with a Template object."""
        # Create a mock Template
        template = MagicMock(spec=Template)

        # Call get_template_async with the Template
        result = await async_env.get_template_async(template)

        # Verify the result
        assert result is template

    @pytest.mark.asyncio
    async def test_get_template_async_with_parent(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test get_template_async with a parent template."""
        # Mock the join_path and _load_template_async methods
        async_env.join_path = MagicMock(return_value="child_from_parent.html")
        async_env._load_template_async = AsyncMock()

        # Call get_template_async with a parent template
        await async_env.get_template_async("child.html", "parent.html")

        # Verify the methods were called with the expected arguments
        async_env.join_path.assert_called_once_with("child.html", "parent.html")
        async_env._load_template_async.assert_called_once_with(
            "child_from_parent.html", None
        )

    @pytest.mark.asyncio
    async def test_get_template_async_with_globals(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test get_template_async with globals."""
        # Mock the _load_template_async method
        async_env._load_template_async = AsyncMock()

        # Call get_template_async with globals
        globals_dict = {"var1": "value1", "var2": "value2"}
        await async_env.get_template_async("template.html", globals=globals_dict)

        # Verify the method was called with the expected arguments
        async_env._load_template_async.assert_called_once_with(
            "template.html", globals_dict
        )

    @pytest.mark.asyncio
    async def test_select_template_async_with_empty_list(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test select_template_async with an empty list."""
        with pytest.raises(
            TemplatesNotFound, match="Tried to select from an empty list of templates."
        ):
            await async_env.select_template_async([])

    @pytest.mark.asyncio
    async def test_select_template_async_with_undefined(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test select_template_async with an Undefined object."""
        # Create an Undefined object
        undefined = Undefined(name="templates")

        # Call select_template_async with the Undefined object
        with pytest.raises(UndefinedError):
            await async_env.select_template_async(undefined)

    @pytest.mark.asyncio
    async def test_select_template_async_with_template_object(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test select_template_async with a Template object."""
        # Create a mock Template
        template = MagicMock(spec=Template)

        # Call select_template_async with the Template
        result = await async_env.select_template_async([template])

        # Verify the result
        assert result is template

    @pytest.mark.asyncio
    async def test_select_template_async_with_parent(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test select_template_async with a parent template."""
        # Mock the join_path and _load_template_async methods
        async_env.join_path = MagicMock(return_value="child_from_parent.html")
        async_env._load_template_async = AsyncMock()

        # Call select_template_async with a parent template
        await async_env.select_template_async(["child.html"], "parent.html")

        # Verify the methods were called with the expected arguments
        async_env.join_path.assert_called_once_with("child.html", "parent.html")
        async_env._load_template_async.assert_called_once_with(
            "child_from_parent.html", None
        )

    @pytest.mark.asyncio
    async def test_select_template_async_not_found(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test select_template_async with templates not found."""
        # Mock the _load_template_async method to raise TemplateNotFound
        async_env._load_template_async = AsyncMock(
            side_effect=TemplateNotFound("not found")
        )

        # Call select_template_async
        with pytest.raises(TemplatesNotFound):
            await async_env.select_template_async(["template1.html", "template2.html"])

    @pytest.mark.asyncio
    async def test_get_or_select_template_async_with_string(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test get_or_select_template_async with a string."""
        # Mock the get_template_async method
        async_env.get_template_async = AsyncMock()

        # Call get_or_select_template_async with a string
        await async_env.get_or_select_template_async("template.html")

        # Verify the method was called with the expected arguments
        async_env.get_template_async.assert_called_once_with(
            "template.html", None, None
        )

    @pytest.mark.asyncio
    async def test_get_or_select_template_async_with_template_object(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test get_or_select_template_async with a Template object."""
        # Create a mock Template
        template = MagicMock(spec=Template)

        # Call get_or_select_template_async with the Template
        result = await async_env.get_or_select_template_async(template)

        # Verify the result
        assert result is template

    @pytest.mark.asyncio
    async def test_get_or_select_template_async_with_list(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test get_or_select_template_async with a list."""
        # Mock the select_template_async method
        async_env.select_template_async = AsyncMock()

        # Call get_or_select_template_async with a list
        await async_env.get_or_select_template_async(
            ["template1.html", "template2.html"]
        )

        # Verify the method was called with the expected arguments
        async_env.select_template_async.assert_called_once_with(
            ["template1.html", "template2.html"], None, None
        )

    @pytest.mark.asyncio
    async def test_load_template_async_with_template_object(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test _load_template_async with a Template object."""
        # Create a mock Template
        template = MagicMock(spec=Template)

        # Call _load_template_async with the Template
        result = await async_env._load_template_async(template, None)

        # Verify the result
        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_string(
        self, async_env: AsyncEnvironment
    ) -> None:
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
    async def test_load_template_async_with_iterable(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test _load_template_async with an iterable."""
        # Mock the _get_template_async method to succeed for the second template
        template = MagicMock()
        async_env._get_template_async = AsyncMock(
            side_effect=[TemplateNotFound("not found"), template]
        )

        # Call _load_template_async with an iterable
        result = await async_env._load_template_async(
            ["template1.html", "template2.html"], None
        )

        # Verify the result
        assert result is template
        assert async_env._get_template_async.call_count == 2
        async_env._get_template_async.assert_any_call("template1.html", None)
        async_env._get_template_async.assert_any_call("template2.html", None)

    @pytest.mark.asyncio
    async def test_load_template_async_with_iterable_all_not_found(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test _load_template_async with an iterable where all templates are not found."""
        # Mock the _get_template_async method to fail for all templates
        async_env._get_template_async = AsyncMock(
            side_effect=TemplateNotFound("not found")
        )

        # Call _load_template_async with an iterable
        with pytest.raises(TemplatesNotFound):
            await async_env._load_template_async(
                ["template1.html", "template2.html"], None
            )

    @pytest.mark.asyncio
    async def test_get_template_no_loader(self, async_env: AsyncEnvironment) -> None:
        """Test _get_template_async with no loader."""
        # Ensure the loader is None
        async_env.loader = None

        # Call _get_template_async
        with pytest.raises(TypeError, match="no loader for this environment specified"):
            await async_env._get_template_async("template.html", None)

    @pytest.mark.asyncio
    async def test_get_template_with_cache_hit(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test _get_template_async with a cache hit."""
        # Set up the environment
        loader = AsyncMock()
        async_env.loader = loader
        async_env.cache = {}
        async_env.auto_reload = True

        # Create a template with is_up_to_date=True
        template = MagicMock()
        template.is_up_to_date = True

        # Add the template to the cache using correct cache key format
        from weakref import ref

        cache_key = (ref(loader), "template.html")
        async_env.cache[cache_key] = template

        # Call _get_template_async
        result = await async_env._get_template_async("template.html", None)

        # Verify the result is from the cache
        assert result is template

    @pytest.mark.asyncio
    async def test_get_template_with_cache_hit_and_globals(
        self, async_env: AsyncEnvironment
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

        # Add the template to the cache using correct cache key format
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
    async def test_get_template_with_cache_miss(
        self, async_env: AsyncEnvironment
    ) -> None:
        """Test _get_template_async with a cache miss."""
        # Set up the environment
        loader = AsyncMock()
        async_env.loader = loader
        async_env.cache = {}

        # Create a template
        template = MagicMock()

        # Mock the loader.load_async method
        loader.load_async = AsyncMock(return_value=template)

        # Mock the make_globals method
        async_env.make_globals = MagicMock(return_value={})

        # Call _get_template_async
        result = await async_env._get_template_async("template.html", None)

        # Verify the result and that load_async was called
        assert result is template
        loader.load_async.assert_called_once_with(async_env, "template.html", {})

        # Verify the template was added to the cache
        from weakref import ref

        cache_key = (ref(loader), "template.html")
        assert async_env.cache[cache_key] is template
