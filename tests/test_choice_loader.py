import typing as t
from unittest.mock import AsyncMock, MagicMock

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncChoiceLoader,
    AsyncDictLoader,
    AsyncFileSystemLoader,
)


class TestAsyncChoiceLoader:
    @pytest.fixture
    def template_dict1(self) -> dict[str, str]:
        return {
            "index.html": "<h1>Hello from dict1</h1>",
            "shared.html": "<p>Shared template from dict1</p>",
        }

    @pytest.fixture
    def template_dict2(self) -> dict[str, str]:
        return {
            "about.html": "<h1>About page from dict2</h1>",
            "shared.html": "<p>Shared template from dict2</p>",
        }

    @pytest.fixture
    def dict_loader1(self, template_dict1: dict[str, str]) -> AsyncDictLoader:
        return AsyncDictLoader(template_dict1, AsyncPath("/templates/dict1"))

    @pytest.fixture
    def dict_loader2(self, template_dict2: dict[str, str]) -> AsyncDictLoader:
        return AsyncDictLoader(template_dict2, AsyncPath("/templates/dict2"))

    @pytest.fixture
    def mock_fs_loader(self) -> AsyncFileSystemLoader:
        loader = MagicMock(spec=AsyncFileSystemLoader)
        loader.get_source_async = AsyncMock(side_effect=TemplateNotFound("not found"))
        loader.list_templates_async = AsyncMock(return_value=["fs_template.html"])
        return loader

    @pytest.fixture
    def choice_loader(
        self,
        dict_loader1: AsyncDictLoader,
        dict_loader2: AsyncDictLoader,
        mock_fs_loader: AsyncFileSystemLoader,
    ) -> AsyncChoiceLoader:
        return AsyncChoiceLoader(
            [dict_loader1, dict_loader2, mock_fs_loader], AsyncPath("/templates")
        )

    @pytest.fixture
    def environment(self, choice_loader: AsyncChoiceLoader) -> AsyncEnvironment:
        env = AsyncEnvironment(loader=choice_loader)
        env.enable_async = True
        return env

    def test_init(
        self,
        dict_loader1: AsyncDictLoader,
        dict_loader2: AsyncDictLoader,
        mock_fs_loader: AsyncFileSystemLoader,
    ) -> None:
        loaders = [dict_loader1, dict_loader2, mock_fs_loader]
        loader = AsyncChoiceLoader(loaders, AsyncPath("/templates"))
        assert loader.loaders == loaders
        assert len(loader.searchpath) == 1
        assert loader.searchpath[0] == AsyncPath("/templates")

    @pytest.mark.asyncio
    async def test_get_source_async_first_loader(
        self, choice_loader: AsyncChoiceLoader
    ) -> None:
        source, _, uptodate = await choice_loader.get_source_async("index.html")
        assert source == "<h1>Hello from dict1</h1>"
        assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_get_source_async_second_loader(
        self, choice_loader: AsyncChoiceLoader
    ) -> None:
        source, _, uptodate = await choice_loader.get_source_async("about.html")
        assert source == "<h1>About page from dict2</h1>"
        assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_get_source_async_shared_template(
        self, choice_loader: AsyncChoiceLoader
    ) -> None:
        source, _, uptodate = await choice_loader.get_source_async("shared.html")
        assert source == "<p>Shared template from dict1</p>"
        assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_get_source_async_nonexistent_template(
        self, choice_loader: AsyncChoiceLoader
    ) -> None:
        with pytest.raises(TemplateNotFound):
            await choice_loader.get_source_async("nonexistent.html")

    @pytest.mark.asyncio
    async def test_get_source_async_with_path_object(
        self, choice_loader: AsyncChoiceLoader
    ) -> None:
        source, _, uptodate = await choice_loader.get_source_async(
            AsyncPath("index.html")
        )
        assert source == "<h1>Hello from dict1</h1>"
        assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_list_templates_async(
        self, choice_loader: AsyncChoiceLoader, mock_fs_loader: AsyncFileSystemLoader
    ) -> None:
        templates = await choice_loader.list_templates_async()
        assert isinstance(templates, list)

        expected_templates = {
            "index.html",
            "about.html",
            "shared.html",
            "fs_template.html",
        }
        assert set(templates) == expected_templates
        assert templates == sorted(templates)

    @pytest.mark.asyncio
    async def test_load_async(
        self, choice_loader: AsyncChoiceLoader, environment: AsyncEnvironment
    ) -> None:
        template = await choice_loader.load_async(environment, "index.html")
        assert isinstance(template, Template)

        globals_dict: dict[str, t.Any] = {"name": "World"}
        template_with_globals = await choice_loader.load_async(
            environment, "index.html", globals_dict
        )
        assert isinstance(template_with_globals, Template)
        assert template_with_globals.globals.get("name") == "World"
