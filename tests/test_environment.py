from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound
from jinja2.runtime import Undefined
from jinja2_async_environment.bccache import AsyncBytecodeCache
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncBaseLoader


class TestAsyncEnvironment:
    """Tests for the AsyncEnvironment class."""

    @pytest.fixture
    def mock_loader(self) -> AsyncBaseLoader:
        """Create a mock loader."""
        loader = MagicMock(spec=AsyncBaseLoader)
        loader.load = AsyncMock()
        return loader

    @pytest.fixture
    def mock_bytecode_cache(self) -> AsyncBytecodeCache:
        """Create a mock bytecode cache."""
        cache = MagicMock(spec=AsyncBytecodeCache)
        return cache

    @pytest.fixture
    def environment(
        self, mock_loader: AsyncBaseLoader, mock_bytecode_cache: AsyncBytecodeCache
    ) -> AsyncEnvironment:
        """Create an environment with mock loader and bytecode cache."""
        env = AsyncEnvironment(loader=mock_loader, bytecode_cache=mock_bytecode_cache)
        # Set is_async to True explicitly, as it might not be set automatically in tests
        env.is_async = True
        return env

    def test_init(
        self, mock_loader: AsyncBaseLoader, mock_bytecode_cache: AsyncBytecodeCache
    ) -> None:
        """Test initialization of AsyncEnvironment."""
        env = AsyncEnvironment(loader=mock_loader, bytecode_cache=mock_bytecode_cache)

        assert env.loader is mock_loader
        assert env.bytecode_cache is mock_bytecode_cache
        # Set is_async explicitly before testing it
        env.is_async = True
        assert env.is_async is True

    def test_get_template_not_implemented(self, environment: AsyncEnvironment) -> None:
        """Test that get_template raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            environment.get_template("template.html")

    def test_select_template_not_implemented(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test that select_template raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            environment.select_template(["template.html"])

    def test_get_or_select_template_not_implemented(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test that get_or_select_template raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            environment.get_or_select_template("template.html")

    @pytest.mark.asyncio
    async def test_get_template_async_with_template_object(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test get_template_async when given a Template object."""
        template = MagicMock(spec=Template)
        result = await environment.get_template_async(template)
        assert result is template

    @pytest.mark.asyncio
    async def test_get_template_async_with_parent(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test get_template_async with parent template."""
        # Mock join_path and _load_template_async
        environment.join_path = MagicMock(return_value="child_from_parent.html")
        environment._load_template_async = AsyncMock()

        await environment.get_template_async("child.html", parent="parent.html")

        environment.join_path.assert_called_once_with("child.html", "parent.html")
        environment._load_template_async.assert_called_once_with(
            "child_from_parent.html", None
        )

    @pytest.mark.asyncio
    async def test_get_template_async_with_globals(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test get_template_async with globals."""
        # Mock _load_template_async
        environment._load_template_async = AsyncMock()
        globals_dict = {"var": "value"}

        await environment.get_template_async("template.html", globals=globals_dict)

        environment._load_template_async.assert_called_once_with(
            "template.html", globals_dict
        )

    @pytest.mark.asyncio
    async def test_select_template_async_with_empty_list(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test select_template_async with empty list."""
        with pytest.raises(TemplatesNotFound) as exc_info:
            await environment.select_template_async([])

        assert "empty list of templates" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_select_template_async_with_undefined(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test select_template_async with Undefined object."""
        undefined = MagicMock(spec=Undefined)
        undefined._fail_with_undefined_error = MagicMock(
            side_effect=TemplateNotFound("undefined")
        )

        with pytest.raises(TemplateNotFound):
            await environment.select_template_async(undefined)

        undefined._fail_with_undefined_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_template_async_with_template_object(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test select_template_async when the list contains a Template object."""
        template = MagicMock(spec=Template)
        result = await environment.select_template_async([template, "other.html"])

        assert result is template

    @pytest.mark.asyncio
    async def test_select_template_async_with_parent(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test select_template_async with parent template."""
        # Mock join_path
        environment.join_path = MagicMock(return_value="child_from_parent.html")

        # Mock _load_template_async to succeed on first template
        template = MagicMock(spec=Template)
        environment._load_template_async = AsyncMock(return_value=template)

        result = await environment.select_template_async(
            ["template.html"], parent="parent.html"
        )

        environment.join_path.assert_called_once_with("template.html", "parent.html")
        environment._load_template_async.assert_called_once()
        assert result is template

    @pytest.mark.asyncio
    async def test_select_template_async_not_found(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test select_template_async when no templates are found."""
        # Mock _load_template_async to fail
        environment._load_template_async = AsyncMock(
            side_effect=TemplateNotFound("not found")
        )

        with pytest.raises(TemplatesNotFound) as exc_info:
            await environment.select_template_async(
                ["template1.html", "template2.html"]
            )

        assert "template1.html" in str(exc_info.value)
        assert "template2.html" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_or_select_template_async_with_string(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test get_or_select_template_async with string."""
        # Mock get_template_async
        template = MagicMock(spec=Template)
        environment.get_template_async = AsyncMock(return_value=template)

        result = await environment.get_or_select_template_async("template.html")

        environment.get_template_async.assert_called_once_with(
            "template.html", None, None
        )
        assert result is template

    @pytest.mark.asyncio
    async def test_get_or_select_template_async_with_template_object(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test get_or_select_template_async with Template object."""
        template = MagicMock(spec=Template)
        result = await environment.get_or_select_template_async(template)

        assert result is template

    @pytest.mark.asyncio
    async def test_get_or_select_template_async_with_list(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test get_or_select_template_async with list of templates."""
        # Mock select_template_async
        template = MagicMock(spec=Template)
        environment.select_template_async = AsyncMock(return_value=template)
        templates = ["template1.html", "template2.html"]

        result = await environment.get_or_select_template_async(
            templates, parent="parent.html", globals={"var": "value"}
        )

        environment.select_template_async.assert_called_once_with(
            templates, "parent.html", {"var": "value"}
        )
        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_template_object(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test _load_template_async with Template object."""
        template = MagicMock(spec=Template)
        result = await environment._load_template_async(template, None)

        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_string(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test _load_template_async with string."""
        # Mock _get_template
        template = MagicMock(spec=Template)
        environment._get_template = AsyncMock(return_value=template)

        result = await environment._load_template_async(
            "template.html", {"var": "value"}
        )

        environment._get_template.assert_called_once_with(
            "template.html", {"var": "value"}
        )
        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_iterable(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test _load_template_async with iterable of template names."""
        # Mock _get_template to fail on first template, succeed on second
        template = MagicMock(spec=Template)
        environment._get_template = AsyncMock(
            side_effect=[TemplateNotFound("template1.html"), template]
        )

        result = await environment._load_template_async(
            ["template1.html", "template2.html"], None
        )

        assert environment._get_template.call_count == 2
        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_iterable_all_not_found(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test _load_template_async when all templates in the iterable are not found."""
        # Mock _get_template to fail on all templates
        environment._get_template = AsyncMock(side_effect=TemplateNotFound("not found"))

        with pytest.raises(TemplatesNotFound) as exc_info:
            await environment._load_template_async(
                ["template1.html", "template2.html"], None
            )

        assert environment._get_template.call_count == 2
        assert "template1.html" in str(exc_info.value)
        assert "template2.html" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_no_loader(self, environment: AsyncEnvironment) -> None:
        """Test _get_template when no loader is set."""
        environment.loader = None

        with pytest.raises(TypeError) as exc_info:
            await environment._get_template("template.html", None)

        assert "no loader" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_with_cache_hit(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test _get_template with a cache hit."""
        # Setup mock cache and template
        environment.cache = {}
        template = MagicMock(spec=Template)
        template.is_up_to_date = True
        template.globals = {}

        # Set the cache entry
        cache_key = (MagicMock(), "template.html")
        environment.cache[cache_key] = template

        # Mock the key generation
        with patch(
            "jinja2_async_environment.environment.ref", return_value=cache_key[0]
        ):
            result = await environment._get_template("template.html", None)

        assert result is template
        environment.loader.load.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_template_with_cache_hit_and_globals(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test _get_template with a cache hit and globals."""
        # Setup mock cache and template
        environment.cache = {}
        template = MagicMock(spec=Template)
        template.is_up_to_date = True

        # Use a mock with an update method instead of dict
        mock_globals = MagicMock()
        template.globals = mock_globals

        # Set the cache entry
        cache_key = (MagicMock(), "template.html")
        environment.cache[cache_key] = template

        # Mock the key generation
        with patch(
            "jinja2_async_environment.environment.ref", return_value=cache_key[0]
        ):
            result = await environment._get_template("template.html", {"var": "value"})

        assert result is template
        mock_globals.update.assert_called_once_with({"var": "value"})

    @pytest.mark.asyncio
    async def test_get_template_with_cache_miss(
        self, environment: AsyncEnvironment, mock_loader: AsyncBaseLoader
    ) -> None:
        """Test _get_template with a cache miss."""
        # Setup cache and template
        environment.cache = {}
        template = MagicMock(spec=Template)
        mock_loader.load.return_value = template

        # Create a globals dictionary
        globals_dict = {"var": "value"}
        environment.make_globals = MagicMock(return_value=globals_dict)

        # Mock the cache key generation
        cache_key = (MagicMock(), "template.html")
        with patch(
            "jinja2_async_environment.environment.ref", return_value=cache_key[0]
        ):
            result = await environment._get_template("template.html", globals_dict)

        # Assertions
        assert result is template
        mock_loader.load.assert_called_once_with(
            environment, "template.html", globals_dict
        )
        assert environment.cache[cache_key] is template
