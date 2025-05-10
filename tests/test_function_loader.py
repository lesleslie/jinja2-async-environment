import typing as t

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFunctionLoader, SourceType


class TestAsyncFunctionLoader:
    @pytest.fixture
    def template_dict(self) -> dict[str, str]:
        return {
            "index.html": "<h1>Hello, {{ name }}!</h1>",
            "base.html": "<!DOCTYPE html><html><body>{% block content %}{% endblock %}</body></html>",
            "child.html": "{% extends 'base.html' %}{% block content %}<p>{{ message }}</p>{% endblock %}",
        }

    @pytest.fixture
    def sync_load_func(
        self, template_dict: dict[str, str]
    ) -> t.Callable[[str | AsyncPath], SourceType | None]:
        def load_func(template: str | AsyncPath) -> SourceType | None:
            template_name = (
                template.name if isinstance(template, AsyncPath) else template
            )
            if template_name in template_dict:
                source = template_dict[template_name]
                return (source, None, lambda: True)
            return None

        return load_func

    @pytest.fixture
    def async_load_func(
        self, template_dict: dict[str, str]
    ) -> t.Callable[[str | AsyncPath], t.Awaitable[SourceType | None]]:
        async def load_func(template: str | AsyncPath) -> SourceType | None:
            template_name = (
                template.name if isinstance(template, AsyncPath) else template
            )
            if template_name in template_dict:
                source = template_dict[template_name]
                return (source, None, lambda: True)
            return None

        return load_func

    @pytest.fixture
    def string_load_func(
        self, template_dict: dict[str, str]
    ) -> t.Callable[[str | AsyncPath], str | None]:
        def load_func(template: str | AsyncPath) -> str | None:
            template_name = (
                template.name if isinstance(template, AsyncPath) else template
            )
            return template_dict.get(template_name)

        return load_func

    @pytest.fixture
    def sync_loader(
        self, sync_load_func: t.Callable[[str | AsyncPath], SourceType | None]
    ) -> AsyncFunctionLoader:
        return AsyncFunctionLoader(sync_load_func, AsyncPath("/templates"))

    @pytest.fixture
    def async_loader(
        self,
        async_load_func: t.Callable[[str | AsyncPath], t.Awaitable[SourceType | None]],
    ) -> AsyncFunctionLoader:
        return AsyncFunctionLoader(async_load_func, AsyncPath("/templates"))

    @pytest.fixture
    def string_loader(
        self, string_load_func: t.Callable[[str | AsyncPath], str | None]
    ) -> AsyncFunctionLoader:
        return AsyncFunctionLoader(string_load_func, AsyncPath("/templates"))

    @pytest.fixture
    def environment(self, sync_loader: AsyncFunctionLoader) -> AsyncEnvironment:
        env = AsyncEnvironment(loader=sync_loader)
        env.enable_async = True
        return env

    def test_init(
        self, sync_load_func: t.Callable[[str | AsyncPath], SourceType | None]
    ) -> None:
        loader = AsyncFunctionLoader(sync_load_func, AsyncPath("/templates"))
        assert loader.load_func == sync_load_func
        assert len(loader.searchpath) == 1
        assert loader.searchpath[0] == AsyncPath("/templates")

    @pytest.mark.asyncio
    async def test_get_source_async_with_sync_function(
        self, sync_loader: AsyncFunctionLoader
    ) -> None:
        source, filename, uptodate = await sync_loader.get_source_async("index.html")
        assert source == "<h1>Hello, {{ name }}!</h1>"
        assert filename is None
        assert callable(uptodate)
        assert uptodate()

    @pytest.mark.asyncio
    async def test_get_source_async_with_async_function(
        self, async_loader: AsyncFunctionLoader
    ) -> None:
        source, filename, uptodate = await async_loader.get_source_async("index.html")
        assert source == "<h1>Hello, {{ name }}!</h1>"
        assert filename is None
        assert callable(uptodate)
        assert uptodate()

    @pytest.mark.asyncio
    async def test_get_source_async_with_string_function(
        self, string_loader: AsyncFunctionLoader
    ) -> None:
        source, filename, uptodate = await string_loader.get_source_async("index.html")
        assert source == "<h1>Hello, {{ name }}!</h1>"
        assert filename == "index.html"
        assert callable(uptodate)
        assert uptodate()

    @pytest.mark.asyncio
    async def test_get_source_async_nonexistent_template(
        self, sync_loader: AsyncFunctionLoader
    ) -> None:
        with pytest.raises(TemplateNotFound):
            await sync_loader.get_source_async("nonexistent.html")

    @pytest.mark.asyncio
    async def test_get_source_async_with_path_object(
        self, sync_loader: AsyncFunctionLoader
    ) -> None:
        source, filename, uptodate = await sync_loader.get_source_async(
            AsyncPath("index.html")
        )
        assert source == "<h1>Hello, {{ name }}!</h1>"
        assert filename is None
        assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_load_async(
        self, sync_loader: AsyncFunctionLoader, environment: AsyncEnvironment
    ) -> None:
        template = await sync_loader.load_async(environment, "index.html")
        assert isinstance(template, Template)

        globals_dict: dict[str, t.Any] = {"name": "World"}
        template_with_globals = await sync_loader.load_async(
            environment, "index.html", globals_dict
        )
        assert isinstance(template_with_globals, Template)
        assert template_with_globals.globals.get("name") == "World"

    @pytest.mark.asyncio
    async def test_invalid_return_type(self) -> None:
        def invalid_load_func(template: str | AsyncPath) -> int:
            return 42

        loader = AsyncFunctionLoader(invalid_load_func, AsyncPath("/templates"))
        with pytest.raises(TypeError, match="Unexpected source type"):
            await loader.get_source_async("index.html")
