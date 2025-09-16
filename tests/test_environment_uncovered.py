"""Tests for uncovered methods in environment.py to improve coverage."""

from unittest.mock import MagicMock

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplatesNotFound
from jinja2_async_environment.environment import (
    AsyncEnvironment,
    AsyncSandboxedEnvironment,
)
from jinja2_async_environment.loaders import AsyncDictLoader


class TestAsyncEnvironment:
    """Test AsyncEnvironment methods that are not covered."""

    def test_init_with_existing_escape_filter(self):
        """Test AsyncEnvironment initialization when escape filter already exists."""
        # Create environment with escape filter already in filters
        env = AsyncEnvironment()
        original_escape = env.filters["escape"]

        # Re-initialize to test the path where escape filter already exists
        env.__init__()

        # The escape filter should remain the same (not overwritten)
        assert env.filters["escape"] == original_escape

    def test_init_without_escape_filter(self):
        """Test AsyncEnvironment initialization without escape filter."""
        # Create environment without escape filter
        env = AsyncEnvironment()

        # Remove escape filter to test the path where it doesn't exist
        if "escape" in env.filters:
            del env.filters["escape"]

        # Re-initialize to test the path where escape filter doesn't exist
        env.__init__()

        # The escape filter should be added
        assert "escape" in env.filters

    @pytest.mark.asyncio
    async def test_select_template_async_with_template_object(self):
        """Test select_template_async with Template object."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Get a template object first
        template = await env.get_template_async("test.html")

        # Test select_template_async with Template object
        result = await env.select_template_async([template])
        assert result is template

    @pytest.mark.asyncio
    async def test_select_template_async_with_magicmock(self):
        """Test select_template_async with MagicMock object."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Create a MagicMock that looks like a Template
        mock_template = MagicMock()
        mock_template.__class__.__name__ = "MagicMock"

        # Test select_template_async with MagicMock
        result = await env.select_template_async([mock_template])
        assert result is mock_template

    @pytest.mark.asyncio
    async def test_select_template_async_with_template_not_found(self):
        """Test select_template_async when templates are not found."""
        loader = AsyncDictLoader({}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Test select_template_async with non-existent templates
        with pytest.raises(TemplatesNotFound):
            await env.select_template_async(["nonexistent1.html", "nonexistent2.html"])

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_coroutine(self):
        """Test _evaluate_uptodate_attribute with coroutine."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Create a coroutine that returns True
        async def coroutine_uptodate():
            return True

        # Test with coroutine
        result = await env._evaluate_uptodate_attribute(coroutine_uptodate())
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_coroutine_exception(self):
        """Test _evaluate_uptodate_attribute with coroutine that raises exception."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Create a coroutine that raises an exception
        async def failing_coroutine():
            raise ValueError("Test error")

        # Test with failing coroutine - should return True on exception
        result = await env._evaluate_uptodate_attribute(failing_coroutine())
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_coroutine_function(self):
        """Test _evaluate_uptodate_attribute with coroutine function."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Create a coroutine function
        async def async_uptodate():
            return False

        # Test with coroutine function
        result = await env._evaluate_uptodate_attribute(async_uptodate)
        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_coroutine_function_exception(self):
        """Test _evaluate_uptodate_attribute with coroutine function that raises exception."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Create a coroutine function that raises an exception
        async def failing_async_uptodate():
            raise RuntimeError("Test error")

        # Test with failing coroutine function - should return True on exception
        result = await env._evaluate_uptodate_attribute(failing_async_uptodate)
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_callable(self):
        """Test _evaluate_uptodate_attribute with regular callable."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Create a regular callable
        def sync_uptodate():
            return True

        # Test with callable
        result = await env._evaluate_uptodate_attribute(sync_uptodate)
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_callable_exception(self):
        """Test _evaluate_uptodate_attribute with callable that raises exception."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Create a callable that raises an exception
        def failing_sync_uptodate():
            raise ValueError("Test error")

        # Test with failing callable - should return True on exception
        result = await env._evaluate_uptodate_attribute(failing_sync_uptodate)
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_truthy_value(self):
        """Test _evaluate_uptodate_attribute with truthy value."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Test with truthy value
        result = await env._evaluate_uptodate_attribute("truthy")
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_uptodate_attribute_with_falsy_value(self):
        """Test _evaluate_uptodate_attribute with falsy value."""
        loader = AsyncDictLoader({"test.html": "Hello {{ name }}!"}, AsyncPath("."))
        env = AsyncEnvironment(loader=loader)

        # Test with falsy value
        result = await env._evaluate_uptodate_attribute("")
        assert result is False


class TestAsyncSandboxedEnvironment:
    """Test AsyncSandboxedEnvironment methods that are not covered."""

    def test_init_with_existing_escape_filter(self):
        """Test AsyncSandboxedEnvironment initialization when escape filter already exists."""
        # Create environment with escape filter already in filters
        env = AsyncSandboxedEnvironment()
        original_escape = env.filters["escape"]

        # Re-initialize to test the path where escape filter already exists
        env.__init__()

        # The escape filter should remain the same (not overwritten)
        assert env.filters["escape"] == original_escape

    def test_init_without_escape_filter(self):
        """Test AsyncSandboxedEnvironment initialization without escape filter."""
        # Create environment without escape filter
        env = AsyncSandboxedEnvironment()

        # Remove escape filter to test the path where it doesn't exist
        if "escape" in env.filters:
            del env.filters["escape"]

        # Re-initialize to test the path where escape filter doesn't exist
        env.__init__()

        # The escape filter should be added
        assert "escape" in env.filters
