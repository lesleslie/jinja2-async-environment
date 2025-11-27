"""Tests for the AsyncChoiceLoader to improve test coverage."""

from unittest.mock import AsyncMock

import pytest
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncChoiceLoader,
)


class MockLoader:
    """Mock loader that implements the AsyncLoaderProtocol."""

    def __init__(self, templates=None, should_raise=False, raise_exception=None):
        self.templates = templates or {}
        self.should_raise = should_raise
        self.raise_exception = raise_exception

    async def get_source_async(self, environment, name):
        if self.should_raise:
            if self.raise_exception:
                raise self.raise_exception
            else:
                raise TemplateNotFound(name)
        if name in self.templates:
            return self.templates[name], f"mock_path/{name}", lambda: True
        raise TemplateNotFound(name)

    async def list_templates_async(self):
        if self.should_raise and self.raise_exception:
            raise self.raise_exception
        return list(self.templates.keys())


class TestAsyncChoiceLoader:
    """Test the AsyncChoiceLoader class to improve coverage."""

    async def test_initialization(self):
        """Test initialization with different parameters."""
        loader1 = AsyncChoiceLoader([], searchpath=["/tmp"])
        assert loader1.loaders == []

        mock_loader = AsyncMock()
        loader2 = AsyncChoiceLoader([mock_loader], searchpath=["/tmp"])
        assert len(loader2.loaders) == 1

    async def test_get_source_async_success(self):
        """Test getting source successfully from first loader."""
        success_loader = MockLoader({"template.html": "content"})
        loader = AsyncChoiceLoader([success_loader], searchpath=["/tmp"])

        env = AsyncEnvironment(loader=loader, enable_async=True)
        result = await loader.get_source_async(env, "template.html")
        assert result[0] == "content"

    async def test_get_source_async_fallback(self):
        """Test fallback to second loader when first fails."""
        failing_loader = MockLoader(should_raise=True)
        success_loader = MockLoader({"template.html": "content"})
        loader = AsyncChoiceLoader(
            [failing_loader, success_loader], searchpath=["/tmp"]
        )

        env = AsyncEnvironment(loader=loader, enable_async=True)
        result = await loader.get_source_async(env, "template.html")
        assert result[0] == "content"

    async def test_get_source_async_template_not_found(self):
        """Test when no loader can find the template."""
        failing_loader1 = MockLoader(should_raise=True)
        failing_loader2 = MockLoader(should_raise=True)
        loader = AsyncChoiceLoader(
            [failing_loader1, failing_loader2], searchpath=["/tmp"]
        )

        env = AsyncEnvironment(loader=loader, enable_async=True)
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(env, "nonexistent.html")

    async def test_get_source_async_with_general_exception(self):
        """Test fallback when loader raises a general exception."""
        error_loader = MockLoader(
            should_raise=True, raise_exception=OSError("file error")
        )
        success_loader = MockLoader({"template.html": "content"})
        loader = AsyncChoiceLoader([error_loader, success_loader], searchpath=["/tmp"])

        env = AsyncEnvironment(loader=loader, enable_async=True)
        result = await loader.get_source_async(env, "template.html")
        assert result[0] == "content"

    async def test_list_templates_async(self):
        """Test listing templates from multiple loaders."""
        loader1 = MockLoader({"a.html": "content1", "b.html": "content2"})
        loader2 = MockLoader({"c.html": "content3"})
        choice_loader = AsyncChoiceLoader([loader1, loader2], searchpath=["/tmp"])

        templates = await choice_loader.list_templates_async()
        assert "a.html" in templates
        assert "b.html" in templates
        assert "c.html" in templates
        assert len(templates) == 3

    async def test_list_templates_async_with_not_implemented(self):
        """Test listing templates when some loaders don't support it."""
        loader1 = MockLoader({"a.html": "content1"})
        # Create a mock that raises NotImplementedError
        mock_loader = AsyncMock()
        mock_loader.list_templates_async.side_effect = NotImplementedError()

        choice_loader = AsyncChoiceLoader([loader1, mock_loader], searchpath=["/tmp"])
        templates = await choice_loader.list_templates_async()
        assert "a.html" in templates

    async def test_list_templates_async_with_general_exception(self):
        """Test listing templates when a loader raises a general exception."""
        loader1 = MockLoader({"a.html": "content1"})
        # Create a mock that raises a general exception
        mock_loader = AsyncMock()
        mock_loader.list_templates_async.side_effect = RuntimeError("Unexpected error")

        choice_loader = AsyncChoiceLoader([loader1, mock_loader], searchpath=["/tmp"])
        templates = await choice_loader.list_templates_async()
        assert "a.html" in templates

    async def test_loader_management_methods(self):
        """Test the loader management methods."""
        choice_loader = AsyncChoiceLoader([], searchpath=["/tmp"])

        # Test add_loader
        mock_loader = AsyncMock()
        choice_loader.add_loader(mock_loader)
        assert choice_loader.get_loader_count() == 1

        # Test insert_loader
        mock_loader2 = AsyncMock()
        choice_loader.insert_loader(0, mock_loader2)
        assert choice_loader.get_loader_count() == 2
        assert choice_loader.loaders[0] is mock_loader2

        # Test get_loaders (should return a copy)
        loaders_copy = choice_loader.get_loaders()
        assert loaders_copy == choice_loader.loaders
        assert loaders_copy is not choice_loader.loaders  # Should be a copy

        # Test remove_loader
        choice_loader.remove_loader(mock_loader2)
        assert choice_loader.get_loader_count() == 1

        # Test clear_loaders
        choice_loader.clear_loaders()
        assert choice_loader.get_loader_count() == 0
