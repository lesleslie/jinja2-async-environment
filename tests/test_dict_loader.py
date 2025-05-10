import typing as t

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


class TestAsyncDictLoader:
    @pytest.fixture
    def template_dict(self) -> dict[str, str]:
        return {
            "index.html": "<h1>Hello, {{ name }}!</h1>",
            "base.html": "<!DOCTYPE html><html><body>{% block content %}{% endblock %}</body></html>",
            "child.html": "{% extends 'base.html' %}{% block content %}<p>{{ message }}</p>{% endblock %}",
        }

    @pytest.fixture
    def loader(self, template_dict: dict[str, str]) -> AsyncDictLoader:
        return AsyncDictLoader(template_dict, AsyncPath("/templates"))

    @pytest.fixture
    def environment(self, loader: AsyncDictLoader) -> AsyncEnvironment:
        env = AsyncEnvironment(loader=loader)
        env.enable_async = True
        return env

    def test_init(self, template_dict: dict[str, str]) -> None:
        loader = AsyncDictLoader(template_dict, AsyncPath("/templates"))
        assert loader.mapping == template_dict
        assert len(loader.searchpath) == 1
        assert loader.searchpath[0] == AsyncPath("/templates")

    @pytest.mark.asyncio
    async def test_get_source_async_existing_template(
        self, loader: AsyncDictLoader
    ) -> None:
        source, filename, uptodate = await loader.get_source_async("index.html")
        assert source == "<h1>Hello, {{ name }}!</h1>"
        assert filename is None
        assert callable(uptodate)
        assert uptodate()

    @pytest.mark.asyncio
    async def test_get_source_async_nonexistent_template(
        self, loader: AsyncDictLoader
    ) -> None:
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async("nonexistent.html")

    @pytest.mark.asyncio
    async def test_get_source_async_with_path_object(
        self, loader: AsyncDictLoader
    ) -> None:
        source, filename, uptodate = await loader.get_source_async(
            AsyncPath("index.html")
        )
        assert source == "<h1>Hello, {{ name }}!</h1>"
        assert filename is None
        assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_list_templates_async(self, loader: AsyncDictLoader) -> None:
        templates = await loader.list_templates_async()
        assert isinstance(templates, list)
        assert set(templates) == {"index.html", "base.html", "child.html"}
        assert templates == sorted(templates)

    @pytest.mark.asyncio
    async def test_load_async(
        self, loader: AsyncDictLoader, environment: AsyncEnvironment
    ) -> None:
        template = await loader.load_async(environment, "index.html")
        assert isinstance(template, Template)

        globals_dict: dict[str, t.Any] = {"name": "World"}
        template_with_globals = await loader.load_async(
            environment, "index.html", globals_dict
        )
        assert isinstance(template_with_globals, Template)
        assert template_with_globals.globals.get("name") == "World"

    @pytest.mark.asyncio
    async def test_uptodate_function(
        self, loader: AsyncDictLoader, template_dict: dict[str, str]
    ) -> None:
        _, _, uptodate = await loader.get_source_async("index.html")
        assert uptodate()

        original_template = template_dict["index.html"]
        template_dict["index.html"] = "<h1>Modified template</h1>"
        assert not uptodate()

        template_dict["index.html"] = original_template
        assert uptodate()
