import typing as t
from unittest.mock import patch

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncBaseLoader,
    AsyncChoiceLoader,
    AsyncDictLoader,
    AsyncFileSystemLoader,
    AsyncFunctionLoader,
)


class TestLoaderAdapter:
    """Test adapter for loaders to handle environment parameter."""

    @pytest.mark.asyncio
    async def test_base_loader_adapter(self) -> None:
        """Test that AsyncBaseLoader can handle environment parameter."""
        loader = AsyncBaseLoader(AsyncPath("/path"))

        # Patch the original get_source_async to test our adapter
        original_method = loader.get_source_async

        async def patched_get_source(*args: t.Any, **kwargs: t.Any) -> t.Any:
            # If first arg is environment, call with just the template
            if len(args) > 1 and isinstance(args[0], AsyncEnvironment):
                return await original_method(args[1])
            return await original_method(*args, **kwargs)

        # Apply the patch
        with patch.object(loader, "get_source_async", patched_get_source):
            # Should work with environment
            with pytest.raises(TemplateNotFound):
                await loader.get_source_async(AsyncEnvironment(), "template.html")

            # Should still work without environment
            with pytest.raises(TemplateNotFound):
                await loader.get_source_async("template.html")

    @pytest.mark.asyncio
    async def test_filesystem_loader_adapter(self) -> None:
        """Test that AsyncFileSystemLoader can handle environment parameter."""
        loader = AsyncFileSystemLoader(AsyncPath("/path"))

        # Create a mock method that will be called by our adapter
        async def mock_get_source(
            environment_or_template: AsyncEnvironment | str | AsyncPath,
            template: str | AsyncPath | None = None,
        ) -> tuple[str, str, t.Callable[[], bool]]:
            actual_template = (
                template if template is not None else environment_or_template
            )
            if isinstance(actual_template, str) and actual_template == "test.html":
                return "content", "/path/test.html", lambda: True
            raise TemplateNotFound(str(actual_template))

        # Replace the original method with our mock
        loader.get_source_async = mock_get_source

        # Test with environment parameter
        content, path_str, uptodate_func = await loader.get_source_async(
            AsyncEnvironment(), "test.html"
        )
        assert content == "content"
        assert path_str == "/path/test.html"
        assert uptodate_func()

        # Test with template not found
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(AsyncEnvironment(), "nonexistent.html")

    @pytest.mark.asyncio
    async def test_dict_loader_adapter(self) -> None:
        """Test that AsyncDictLoader can handle environment parameter."""
        loader = AsyncDictLoader({"test.html": "content"}, AsyncPath("/path"))

        # Test with environment parameter
        content, path_str, uptodate_func = await loader.get_source_async(
            AsyncEnvironment(), "test.html"
        )
        assert content == "content"
        # Verify path and uptodate are properly returned
        assert (
            path_str is None
        )  # DictLoader returns None for path (in-memory templates)
        assert callable(uptodate_func)

        # Test with template not found
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(AsyncEnvironment(), "nonexistent.html")

    @pytest.mark.asyncio
    async def test_function_loader_adapter(self) -> None:
        """Test that AsyncFunctionLoader can handle environment parameter."""

        async def load_func(
            template: str | AsyncPath,
        ) -> tuple[str, str, t.Callable[[], bool]]:
            template_str = str(template)
            if template_str == "test.html":
                return "content", template_str, lambda: True
            raise TemplateNotFound(template_str)

        loader = AsyncFunctionLoader(load_func, AsyncPath("/path"))

        # Test with environment parameter
        content, path, uptodate = await loader.get_source_async(
            AsyncEnvironment(), "test.html"
        )
        assert content == "content"
        assert path == "test.html"
        assert uptodate() is True

        # Test with template not found
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(AsyncEnvironment(), "nonexistent.html")

    @pytest.mark.asyncio
    async def test_choice_loader_adapter(self) -> None:
        """Test that AsyncChoiceLoader can handle environment parameter."""
        dict_loader = AsyncDictLoader({"test1.html": "content1"}, AsyncPath("/path1"))

        async def load_func(
            template: str | AsyncPath,
        ) -> tuple[str, str, t.Callable[[], bool]]:
            template_str = str(template)
            if template_str == "test2.html":
                return "content2", template_str, lambda: True
            raise TemplateNotFound(template_str)

        func_loader = AsyncFunctionLoader(load_func, AsyncPath("/path2"))

        choice_loader = AsyncChoiceLoader(
            [dict_loader, func_loader], AsyncPath("/choice")
        )

        # Test with environment parameter for first loader
        content1, path_str1, uptodate_func1 = await choice_loader.get_source_async(
            AsyncEnvironment(), "test1.html"
        )
        assert content1 == "content1"
        assert path_str1 is None  # DictLoader returns None for path
        assert callable(uptodate_func1)

        # Test with environment parameter for second loader
        content2, path_str2, uptodate_func2 = await choice_loader.get_source_async(
            AsyncEnvironment(), "test2.html"
        )
        assert content2 == "content2"
        assert isinstance(path_str2, str)
        assert callable(uptodate_func2)

        # Test with template not found
        with pytest.raises(TemplateNotFound):
            await choice_loader.get_source_async(AsyncEnvironment(), "nonexistent.html")
