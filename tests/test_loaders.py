import typing as t
from unittest.mock import AsyncMock, MagicMock

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncBaseLoader


class TestAsyncBaseLoader:
    @pytest.fixture
    def loader(self) -> AsyncBaseLoader:
        return AsyncBaseLoader(AsyncPath("/path/to/templates"))

    def test_init_with_single_path(self) -> None:
        path = AsyncPath("/templates")
        loader = AsyncBaseLoader(path)
        searchpath = loader.searchpath
        assert isinstance(searchpath, list | tuple)
        assert len(searchpath) == 1
        assert searchpath[0] == path

    def test_init_with_multiple_paths(self) -> None:
        paths = [AsyncPath("/templates1"), AsyncPath("/templates2")]
        loader = AsyncBaseLoader(paths)
        searchpath = loader.searchpath
        assert isinstance(searchpath, list | tuple)
        assert len(searchpath) == 2
        assert searchpath.copy() == paths

    @pytest.mark.asyncio
    async def test_not_implemented_methods(self, loader: AsyncBaseLoader) -> None:
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(AsyncPath("template.html"))
        with pytest.raises(
            TypeError, match="this loader cannot iterate over all templates"
        ):
            await loader.list_templates_async()

    @pytest.mark.asyncio
    async def test_load(self) -> None:
        loader = AsyncBaseLoader(AsyncPath("/path/to/templates"))
        template_content = "<h1>Hello, {{ name }}!</h1>"
        template_instance = MagicMock(spec=Template)
        env = MagicMock(spec=AsyncEnvironment)
        calls: list[
            tuple[
                AsyncEnvironment,
                str,
                dict[str, t.Any],
                t.Callable[[], bool] | None,
            ]
        ] = []

        def mock_from_code(
            env_arg: AsyncEnvironment,
            code: str,
            globals_arg: dict[str, t.Any],
            uptodate: t.Callable[[], bool] | None = None,
        ) -> Template:
            calls.append((env_arg, code, globals_arg, uptodate))
            return template_instance

        env.bytecode_cache = None
        env.compile.return_value = "compiled_code"
        env.template_class = MagicMock()
        env.template_class.from_code = mock_from_code
        loader.get_source_async = AsyncMock(return_value=(template_content, None, None))
        result = await loader.load_async(env, "template.html")
        assert result is template_instance
        env.compile.assert_called_once_with(template_content, "template.html")
        assert len(calls) == 1
        call_args = calls[0]
        assert call_args[0] == env
        assert call_args[1] == "compiled_code"
        assert call_args[2] == {}

    @pytest.mark.asyncio
    async def test_load_with_bytes(self) -> None:
        loader = AsyncBaseLoader(AsyncPath("/path/to/templates"))
        bytes_content = b"<h1>Hello, {{ name }}!</h1>"
        env = MagicMock(spec=AsyncEnvironment)
        env.make_globals.return_value = {}
        env.bytecode_cache = None
        env.compile.return_value = "compiled_code"
        template_instance = MagicMock(spec=Template)
        env.template_class.from_code.return_value = template_instance
        loader.get_source_async = AsyncMock(return_value=(bytes_content, None, None))
        result = await loader.load_async(env, "template.html")
        env.compile.assert_called_once_with(bytes_content.decode(), "template.html")
        env.template_class.from_code.assert_called_once_with(
            env, "compiled_code", {}, None
        )
        assert result is template_instance
