"""Tests for the AsyncPackageLoader to improve test coverage."""

import pytest
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncPackageLoader
from jinja2_async_environment.loaders.package import PackageSpecNotFound


class TestAsyncPackageLoader:
    """Test the AsyncPackageLoader class to improve coverage."""

    async def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with minimal parameters
        loader1 = AsyncPackageLoader("sys", "templates")
        assert loader1.package_name == "sys"
        assert str(loader1.package_path) == "templates"

        # Test with custom encoding
        loader2 = AsyncPackageLoader("sys", "templates", encoding="latin1")
        assert loader2.encoding == "latin1"

    async def test_perform_initialization_with_empty_package_name(self):
        """Test _perform_initialization with empty package name raises error."""
        loader = AsyncPackageLoader("", "templates")
        with pytest.raises(PackageSpecNotFound):
            loader._perform_initialization()

    async def test_get_source_async_package_not_found(self):
        """Test get_source_async when package doesn't exist."""
        loader = AsyncPackageLoader("nonexistent_package_12345", "templates")
        env = AsyncEnvironment(loader=loader, enable_async=True)

        with pytest.raises(Exception):  # Should raise PackageSpecNotFound or similar
            await loader.get_source_async(env, "template.html")

    async def test_package_with_nonexistent_template(self):
        """Test accessing a non-existent template in a valid package."""
        # Use a real package name that should exist
        loader = AsyncPackageLoader("os", "templates")
        env = AsyncEnvironment(loader=loader, enable_async=True)

        # This should fail because "nonexistent.html" doesn't exist
        with pytest.raises(Exception):  # Should raise TemplateNotFound
            await loader.get_source_async(env, "nonexistent.html")

    async def test_list_templates_async(self):
        """Test listing templates in the package."""
        # Since we can't easily create a test package with templates,
        # we'll test with a package that definitely doesn't have templates
        loader = AsyncPackageLoader("sys", "nonexistent_templates")
        templates = await loader.list_templates_async()
        # Should return empty list since templates dir doesn't exist
        assert templates == []

    async def test_perform_initialization_with_custom_error(self):
        """Test the initialization with custom error scenario."""
        # This test might be hard to trigger without specific test context,
        # but we can at least verify the initialization flow works
        loader = AsyncPackageLoader("os", "templates")

        # Manually trigger initialization
        loader._perform_initialization()

        # Verify the loader was initialized properly
        assert loader._spec is not None
        assert loader._loader is not None
        # Note: _template_root might be None if the templates directory doesn't exist

    async def test_initialize_loader_directly(self):
        """Test the _initialize_loader method directly."""
        loader = AsyncPackageLoader("os", "templates")

        # Test with valid package
        pkg_loader, spec = loader._initialize_loader("os")
        assert pkg_loader is not None
        assert spec is not None

    async def test_initialize_loader_invalid_package(self):
        """Test _initialize_loader with invalid package."""
        loader = AsyncPackageLoader("os", "templates")

        # Test with invalid package name
        with pytest.raises(PackageSpecNotFound):
            loader._initialize_loader("nonexistent_package_12345")

    async def test_initialize_loader_empty_package_name(self):
        """Test _initialize_loader with empty package name."""
        loader = AsyncPackageLoader("os", "templates")

        # Test with empty package name
        with pytest.raises(PackageSpecNotFound):
            loader._initialize_loader("")

    async def test_perform_initialization_error_handling(self):
        """Test error handling in _perform_initialization."""
        loader = AsyncPackageLoader("nonexistent_package_12345", "templates")

        # This should fail initialization
        with pytest.raises(PackageSpecNotFound):
            loader._perform_initialization()

        # Verify that error state was properly reset
        assert loader._template_root is None
        assert loader._loader is None
        assert loader._spec is None
