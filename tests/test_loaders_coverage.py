import typing as t
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncChoiceLoader,
    AsyncDictLoader,
    AsyncFileSystemLoader,
    AsyncFunctionLoader,
    AsyncPackageLoader,
    PackageSpecNotFound,
)


class MockStorage:
    """Mock storage for testing."""

    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    async def write(self, path: str, content: bytes) -> None:
        """Write content to a path."""
        self._files[path] = content

    async def read(self, path: str) -> bytes:
        """Read content from a path."""
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[path]

    async def exists(self, path: str) -> bool:
        """Check if a path exists."""
        return path in self._files


@pytest.fixture
async def mock_storage() -> AsyncIterator[MockStorage]:
    """Create a mock storage for testing."""
    storage = MockStorage()
    yield storage


@pytest.mark.asyncio
async def test_async_filesystem_loader_string_path_initialization() -> None:
    """Test that AsyncFileSystemLoader accepts string paths (Issue #3)."""
    # Test single string path
    loader1 = AsyncFileSystemLoader("templates")
    assert len(loader1.searchpath) == 1
    assert isinstance(loader1.searchpath[0], AsyncPath)
    assert str(loader1.searchpath[0]) == "templates"

    # Test sequence of string paths
    loader2 = AsyncFileSystemLoader(["templates", "other_templates"])
    assert len(loader2.searchpath) == 2
    assert all(isinstance(p, AsyncPath) for p in loader2.searchpath)
    assert str(loader2.searchpath[0]) == "templates"
    assert str(loader2.searchpath[1]) == "other_templates"

    # Test mixed string and AsyncPath objects
    loader3 = AsyncFileSystemLoader(["templates", AsyncPath("async_templates")])
    assert len(loader3.searchpath) == 2
    assert all(isinstance(p, AsyncPath) for p in loader3.searchpath)
    assert str(loader3.searchpath[0]) == "templates"
    assert str(loader3.searchpath[1]) == "async_templates"

    # Test invalid type should raise TypeError with helpful message
    with pytest.raises(TypeError, match="searchpath must be.*AsyncPath.*string"):
        AsyncFileSystemLoader(123)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_async_filesystem_loader_error_handling() -> None:
    """Test error handling in AsyncFileSystemLoader."""
    # Test with a non-existent directory
    loader = AsyncFileSystemLoader(AsyncPath("/non_existent_dir"))

    # Test get_source_async with a non-existent template
    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(AsyncEnvironment(), "non_existent.html")


@pytest.mark.asyncio
async def test_async_package_loader_error_handling() -> None:
    """Test error handling in AsyncPackageLoader."""
    # Test with a non-existent package
    with pytest.raises(PackageSpecNotFound):
        AsyncPackageLoader("non_existent_package", "templates")

    # Test with a valid package but non-existent template
    loader = AsyncPackageLoader("jinja2_async_environment", "tests")

    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(AsyncEnvironment(), "non_existent.html")


@pytest.mark.asyncio
async def test_async_choice_loader_error_handling() -> None:
    """Test error handling in AsyncChoiceLoader."""
    # Create loaders that will all fail
    loader1 = AsyncDictLoader({}, AsyncPath("/dict"))
    loader2 = AsyncFunctionLoader(
        lambda _: t.cast(t.Any, TemplateNotFound("not found")), AsyncPath("/func")
    )

    # Create a choice loader with these loaders
    choice_loader = AsyncChoiceLoader([loader1, loader2], AsyncPath("/choice"))

    # Test get_source_async with a non-existent template
    with pytest.raises(TemplateNotFound):
        await choice_loader.get_source_async(AsyncEnvironment(), "non_existent.html")


@pytest.mark.asyncio
async def test_async_function_loader_error_handling() -> None:
    """Test error handling in AsyncFunctionLoader."""

    # Create a function that raises TemplateNotFound
    async def load_func(template: str | AsyncPath) -> t.Any:
        raise TemplateNotFound(str(template))

    loader = AsyncFunctionLoader(load_func, AsyncPath("/func"))

    # Test get_source_async with a template that will raise TemplateNotFound
    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(AsyncEnvironment(), "non_existent.html")


@pytest.mark.asyncio
async def test_async_dict_loader_error_handling() -> None:
    """Test error handling in AsyncDictLoader."""
    # Create an empty dictionary loader
    loader = AsyncDictLoader({}, AsyncPath("/dict"))

    # Test get_source_async with a non-existent template
    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(AsyncEnvironment(), "non_existent.html")


@pytest.mark.asyncio
async def test_async_filesystem_loader_with_encoding() -> None:
    """Test AsyncFileSystemLoader with different encodings."""
    with (
        patch("anyio.Path.is_file") as mock_is_file,
        patch("anyio.Path.read_bytes") as mock_read_bytes,
        patch("anyio.Path.stat") as mock_stat,
    ):
        # Mock the file exists and content
        mock_is_file.return_value = True
        mock_read_bytes.return_value = "template content".encode("latin1")
        mock_stat.return_value.st_mtime = 123456789.0

        # Create a loader with a specific encoding
        loader = AsyncFileSystemLoader(AsyncPath("/templates"), encoding="latin1")

        # Test get_source_async
        source, _unused_name, _ = await loader.get_source_async(
            AsyncEnvironment(), "template.html"
        )

        # Verify the encoding was used
        mock_read_bytes.assert_called_once()
        assert source == "template content"


@pytest.mark.asyncio
async def test_async_package_loader_with_encoding() -> None:
    """Test AsyncPackageLoader with different encodings."""
    # Create a loader with a specific encoding - just test that it initializes properly
    loader = AsyncPackageLoader("jinja2_async_environment", "tests", encoding="latin1")

    # Verify the encoding was set
    assert loader.encoding == "latin1"

    # Test that it raises TemplateNotFound for non-existent templates
    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(AsyncEnvironment(), "non_existent.html")


@pytest.mark.asyncio
async def test_async_choice_loader_with_multiple_loaders() -> None:
    """Test AsyncChoiceLoader with multiple loaders."""
    # Create a dict loader with one template
    dict_loader = AsyncDictLoader(
        {"template1.html": "dict content"}, AsyncPath("/dict")
    )

    # Create a function loader with another template
    async def load_func(template: str | AsyncPath) -> t.Any:
        template_str = str(template)
        if template_str == "template2.html":
            return "function content", template_str, lambda: True
        raise TemplateNotFound(template_str)

    func_loader = AsyncFunctionLoader(load_func, AsyncPath("/func"))

    # Create a choice loader with these loaders
    choice_loader = AsyncChoiceLoader([dict_loader, func_loader], AsyncPath("/choice"))

    # Test get_source_async with templates from both loaders
    source1, _unused_name1, _ = await choice_loader.get_source_async(
        AsyncEnvironment(), "template1.html"
    )
    assert source1 == "dict content"

    source2, _unused_name2, _ = await choice_loader.get_source_async(
        AsyncEnvironment(), "template2.html"
    )
    assert source2 == "function content"


@pytest.mark.asyncio
async def test_async_function_loader_with_uptodate() -> None:
    """Test AsyncFunctionLoader with an uptodate function."""

    # Create a function that returns a source with an uptodate function
    async def load_func(template: str | AsyncPath) -> t.Any:
        template_str = str(template)
        if template_str == "template.html":
            return "content", template_str, bool
        raise TemplateNotFound(template_str)

    loader = AsyncFunctionLoader(load_func, AsyncPath("/func"))

    # Test get_source_async
    source, _unused_name, uptodate = await loader.get_source_async(
        AsyncEnvironment(), "template.html"
    )

    # Verify the source and uptodate function
    assert source == "content"
    assert uptodate() is False


@pytest.mark.asyncio
async def test_async_dict_loader_with_prefix() -> None:
    """Test AsyncDictLoader with a prefix."""
    # Create a dict loader with a prefix
    loader = AsyncDictLoader(
        {"prefix/template.html": "content with prefix"}, AsyncPath("/dict")
    )

    # Test get_source_async with the prefixed template
    source, _unused_name, _ = await loader.get_source_async(
        AsyncEnvironment(), "prefix/template.html"
    )

    # Verify the source
    assert source == "content with prefix"


@pytest.mark.asyncio
async def test_async_filesystem_loader_list_templates() -> None:
    """Test AsyncFileSystemLoader's list_templates_async method with directory structure."""
    with (
        patch("anyio.Path.rglob") as mock_rglob,
        patch("anyio.Path.is_file") as mock_is_file,
    ):
        # Create a mock for the rglob method to return a list of paths
        mock_paths = [
            AsyncPath("/templates/template1.html"),
            AsyncPath("/templates/subdir/template2.html"),
            AsyncPath("/templates/subdir/nested/template3.html"),
        ]

        # Setup the mock to return an async iterator
        async def mock_async_iter():
            for path in mock_paths:
                yield path

        mock_rglob.return_value = mock_async_iter()
        mock_is_file.return_value = True

        # Create a loader with the mock searchpath
        loader = AsyncFileSystemLoader(AsyncPath("/templates"))

        # Test list_templates_async
        templates = await loader.list_templates_async()

        # Verify the templates list contains the expected relative paths
        assert "template1.html" in templates
        assert "subdir/template2.html" in templates
        assert "subdir/nested/template3.html" in templates
        assert len(templates) == 3
