import typing as t
from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound
from jinja2.runtime import Undefined
from jinja2_async_environment.bccache import AsyncBytecodeCache
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncBaseLoader

GlobalsDict = dict[str, t.Any]  # type alias replacement


class TestAsyncEnvironment:
    @pytest.fixture
    def mock_loader(self) -> AsyncBaseLoader:
        loader = MagicMock(spec=AsyncBaseLoader)
        loader.load = AsyncMock()
        return loader

    @pytest.fixture
    def mock_bytecode_cache(self) -> AsyncBytecodeCache:
        cache = MagicMock(spec=AsyncBytecodeCache)
        return cache

    @pytest.fixture
    def environment(
        self, mock_loader: AsyncBaseLoader, mock_bytecode_cache: AsyncBytecodeCache
    ) -> AsyncEnvironment:
        env = AsyncEnvironment(loader=mock_loader, bytecode_cache=mock_bytecode_cache)
        env.enable_async = True
        return env

    def test_init(
        self, mock_loader: AsyncBaseLoader, mock_bytecode_cache: AsyncBytecodeCache
    ) -> None:
        env = AsyncEnvironment(loader=mock_loader, bytecode_cache=mock_bytecode_cache)
        assert env.loader is mock_loader
        assert env.bytecode_cache is mock_bytecode_cache
        env.enable_async = True
        assert env.enable_async

    def test_get_template_not_implemented(self, environment: AsyncEnvironment) -> None:
        with pytest.raises(NotImplementedError):
            environment.get_template("template.html")

    def test_select_template_not_implemented(
        self, environment: AsyncEnvironment
    ) -> None:
        with pytest.raises(NotImplementedError):
            environment.select_template(["template.html"])

    def test_get_or_select_template_not_implemented(
        self, environment: AsyncEnvironment
    ) -> None:
        with pytest.raises(NotImplementedError):
            environment.get_or_select_template("template.html")

    @pytest.mark.asyncio
    async def test_get_template_async_with_template_object(
        self, environment: AsyncEnvironment
    ) -> None:
        template = MagicMock(spec=Template)
        result = await environment.get_template_async(template)
        assert result is template

    @pytest.mark.asyncio
    async def test_get_template_async_with_parent(
        self, environment: AsyncEnvironment
    ) -> None:
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
        with pytest.raises(TemplatesNotFound) as exc_info:
            await environment.select_template_async([])
        assert "empty list of templates" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_select_template_async_with_undefined(
        self, environment: AsyncEnvironment
    ) -> None:
        undefined = MagicMock(spec=Undefined)
        undefined._fail_with_undefined_error = MagicMock(
            side_effect=TemplateNotFound("undefined")
        )
        with pytest.raises(TemplateNotFound):
            await environment.select_template_async(undefined)  # type: ignore[arg-type]
        undefined._fail_with_undefined_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_template_async_with_template_object(
        self, environment: AsyncEnvironment
    ) -> None:
        template = MagicMock(spec=Template)
        result = await environment.select_template_async([template, "other.html"])
        assert result is template

    @pytest.mark.asyncio
    async def test_select_template_async_with_parent(
        self, environment: AsyncEnvironment
    ) -> None:
        environment.join_path = MagicMock(return_value="child_from_parent.html")
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
        template = MagicMock(spec=Template)
        result = await environment.get_or_select_template_async(template)
        assert result is template

    @pytest.mark.asyncio
    async def test_get_or_select_template_async_with_list(
        self, environment: AsyncEnvironment
    ) -> None:
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
        template = MagicMock(spec=Template)
        result = await environment._load_template_async(template, None)
        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_string(
        self, environment: AsyncEnvironment
    ) -> None:
        template = MagicMock(spec=Template)
        environment._get_template_async = AsyncMock(return_value=template)
        result = await environment._load_template_async(
            "template.html", {"var": "value"}
        )
        environment._get_template_async.assert_called_once_with(
            "template.html", {"var": "value"}
        )
        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_iterable(
        self, environment: AsyncEnvironment
    ) -> None:
        template = MagicMock(spec=Template)
        environment._get_template_async = AsyncMock(
            side_effect=[TemplateNotFound("template1.html"), template]
        )
        result = await environment._load_template_async(
            ["template1.html", "template2.html"], None
        )
        assert environment._get_template_async.call_count == 2
        assert result is template

    @pytest.mark.asyncio
    async def test_load_template_async_with_iterable_all_not_found(
        self, environment: AsyncEnvironment
    ) -> None:
        environment._get_template_async = AsyncMock(
            side_effect=TemplateNotFound("not found")
        )
        with pytest.raises(TemplatesNotFound) as exc_info:
            await environment._load_template_async(
                ["template1.html", "template2.html"], None
            )
        assert environment._get_template_async.call_count == 2
        assert "template1.html" in str(exc_info.value)
        assert "template2.html" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_no_loader(self, environment: AsyncEnvironment) -> None:
        environment.loader = None
        with pytest.raises(TypeError) as exc_info:
            await environment._get_template_async("template.html", None)
        assert "no loader" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_template_with_cache_hit(
        self, environment: AsyncEnvironment
    ) -> None:
        environment.cache = {}
        template = MagicMock(spec=Template)
        template.is_up_to_date = True
        template.globals = {}
        mock_loader = AsyncMock()
        environment.loader = mock_loader
        from weakref import ref

        cache_key = (ref(mock_loader), "template.html")
        environment.cache[cache_key] = template
        result = await environment._get_template_async("template.html", None)
        assert result is template

    @pytest.mark.asyncio
    async def test_get_template_with_cache_hit_and_globals(
        self, environment: AsyncEnvironment
    ) -> None:
        environment.cache = {}
        template = MagicMock(spec=Template)
        template.is_up_to_date = True
        mock_globals = MagicMock()
        template.globals = mock_globals
        mock_loader = AsyncMock()
        environment.loader = mock_loader
        from weakref import ref

        cache_key = (ref(mock_loader), "template.html")
        environment.cache[cache_key] = template
        result = await environment._get_template_async(
            "template.html", {"var": "value"}
        )
        assert result is template
        mock_globals.update.assert_called_once_with({"var": "value"})

    @pytest.mark.asyncio
    async def test_get_template_with_cache_miss(
        self, environment: AsyncEnvironment, mock_loader: AsyncBaseLoader
    ) -> None:
        environment.cache = {}
        template = MagicMock(spec=Template)

        actual_return = None

        async def side_effect(*args: t.Any, **kwargs: t.Any):
            nonlocal actual_return
            actual_return = template
            return template

        mock_loader.load = AsyncMock(side_effect=side_effect)
        mock_loader.load_async = mock_loader.load

        globals_dict: GlobalsDict = {"var": "value"}
        environment.make_globals = MagicMock(return_value=globals_dict)
        from weakref import ref

        cache_key = (ref(mock_loader), "template.html")

        result = await environment._get_template_async("template.html", globals_dict)

        assert result is template

        assert environment.cache[cache_key] is actual_return
        mock_loader.load.assert_called_once_with(
            environment, "template.html", globals_dict
        )
