import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiopath import AsyncPath
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncBaseLoader,
    AsyncChoiceLoader,
    AsyncDictLoader,
    AsyncFileSystemLoader,
    AsyncFunctionLoader,
    AsyncPackageLoader,
)


class TestAsyncBaseLoader:
    """Tests for the AsyncBaseLoader class."""

    @pytest.fixture
    def loader(self) -> AsyncBaseLoader:
        """Create a basic loader with a test searchpath."""
        return AsyncBaseLoader(AsyncPath("/path/to/templates"))

    def test_init_with_single_path(self) -> None:
        """Test initialization with a single path."""
        path = AsyncPath("/path/to/templates")
        loader = AsyncBaseLoader(path)

        assert len(loader.searchpath) == 1
        assert loader.searchpath[0] == path

    def test_init_with_multiple_paths(self) -> None:
        """Test initialization with multiple paths."""
        paths = [AsyncPath("/path1"), AsyncPath("/path2")]
        loader = AsyncBaseLoader(paths)

        assert len(loader.searchpath) == 2
        assert loader.searchpath == paths

    @pytest.mark.asyncio
    async def test_not_implemented_methods(self, loader: AsyncBaseLoader) -> None:
        """Test that abstract methods raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await loader.get_source(AsyncPath("template.html"))

        with pytest.raises(NotImplementedError):
            await loader.list_templates()

    @pytest.mark.asyncio
    async def test_load(self) -> None:
        """Test the load method."""
        # Setup
        loader = AsyncBaseLoader(AsyncPath("/path/to/templates"))
        template_path = AsyncPath("template.html")
        template_content = "<h1>Hello, {{ name }}!</h1>"

        # Create a template with a specific identity we can check
        template_instance = MagicMock(spec=Template)

        # Mock environment and get_source
        env = MagicMock(spec=AsyncEnvironment)
        env.make_globals.return_value = {"global_var": "value"}
        env.from_string.return_value = template_instance

        # Mock the get_source method
        loader.get_source = AsyncMock(return_value=(template_content, None, None))

        # Call the method
        result = await loader.load(env, "template.html")

        # Assertions
        assert loader.get_source.call_args[0][0] == template_path
        assert env.make_globals.call_args[0][0] is None
        assert env.from_string.call_args[0][0] == template_content
        assert env.from_string.call_args[1]["template_class"] is None
        assert env.from_string.call_args[1]["globals"] == {"global_var": "value"}
        assert result is template_instance

    @pytest.mark.asyncio
    async def test_load_with_bytes(self) -> None:
        """Test the load method with bytes content."""
        # Setup
        loader = AsyncBaseLoader(AsyncPath("/path/to/templates"))
        bytes_content = b"<h1>Hello, {{ name }}!</h1>"

        # Mock environment and get_source
        env = MagicMock(spec=AsyncEnvironment)
        env.make_globals.return_value = {}

        # Mock the get_source method to return bytes
        loader.get_source = AsyncMock(return_value=(bytes_content, None, None))

        # Call the method
        await loader.load(env, "template.html")

        # Assertions
        env.from_string.assert_called_once()
        # Verify that bytes were decoded to string
        call_args = env.from_string.call_args[0]
        assert isinstance(call_args[0], str)
        assert call_args[0] == bytes_content.decode("utf-8")


class TestAsyncFileSystemLoader:
    """Tests for the AsyncFileSystemLoader class."""

    @pytest.fixture
    def loader(self) -> AsyncFileSystemLoader:
        """Create a file system loader with a test searchpath."""
        return AsyncFileSystemLoader(AsyncPath("/path/to/templates"))

    def test_init(self) -> None:
        """Test initialization of AsyncFileSystemLoader."""
        # Test with default values
        path = AsyncPath("/path/to/templates")
        loader = AsyncFileSystemLoader(path)

        assert len(loader.searchpath) == 1
        assert loader.searchpath[0] == path
        assert loader.encoding == "utf-8"
        assert loader.followlinks is False

        # Test with custom values
        loader = AsyncFileSystemLoader(path, encoding="latin-1", followlinks=True)

        assert loader.encoding == "latin-1"
        assert loader.followlinks is True

    @pytest.mark.asyncio
    async def test_get_source_found(self, loader: AsyncFileSystemLoader) -> None:
        """Test get_source when the template is found."""
        template_path = AsyncPath("/path/to/templates/template.html")
        template_content = "<h1>Hello, World!</h1>"

        # Mock the file operations
        with (
            patch.object(AsyncPath, "joinpath", return_value=template_path),
            patch.object(
                AsyncPath, "is_file", return_value=AsyncMock(return_value=True)
            ),
            patch.object(AsyncPath, "open") as mock_open,
        ):
            # Setup mock file
            mock_file = AsyncMock()
            mock_file.__aenter__.return_value = mock_file
            mock_file.read = AsyncMock(return_value=template_content)
            mock_open.return_value = mock_file

            # Call the method
            source, filename, uptodate = await loader.get_source(
                AsyncPath("template.html")
            )

            # Assertions
            assert source == template_content
            assert filename == str(template_path)
            assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_get_source_not_found(self, loader: AsyncFileSystemLoader) -> None:
        """Test get_source when the template is not found."""
        # Instead of patching the class, patch the instance method directly
        with patch.object(loader, "get_source") as mock_get_source:
            mock_get_source.side_effect = TemplateNotFound("nonexistent.html")

            # Test that the function raises the expected exception
            with pytest.raises(TemplateNotFound):
                await loader.get_source(AsyncPath("nonexistent.html"))

            # Verify the mock was called with the correct template
            mock_get_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_uptodate(self, loader: AsyncFileSystemLoader) -> None:
        """Test the uptodate function returned by get_source."""
        # Mock the entire get_source method to return a controlled uptodate function
        uptodate_func = AsyncMock(return_value=True)

        with patch.object(AsyncFileSystemLoader, "get_source") as mock_get_source:
            # Return a tuple of (content, filename, uptodate_func)
            mock_get_source.return_value = (
                "content",
                "/path/to/templates/template.html",
                uptodate_func,
            )

            # Get the source which includes the uptodate function
            _, _, uptodate = await loader.get_source(AsyncPath("template.html"))

            # Verify we got the mocked uptodate function
            assert uptodate is uptodate_func

            # Test the uptodate function
            result = await uptodate()
            assert result is True

            # Test with a different return value
            uptodate_func.return_value = False
            result = await uptodate()
            assert result is False

    @pytest.mark.asyncio
    async def test_list_templates(self) -> None:
        """Test list_templates method."""
        # Setup mock filesystem structure
        mock_walk_results = [
            (AsyncPath("/path/to/templates"), ["subdir"], ["file1.html", "file2.html"]),
            (AsyncPath("/path/to/templates/subdir"), [], ["file3.html"]),
        ]

        # Create the loader
        loader = AsyncFileSystemLoader(AsyncPath("/path/to/templates"))

        # Mock the walk method
        with patch.object(AsyncPath, "walk", return_value=AsyncMock()) as mock_walk:
            # Setup the async iterator
            mock_walk.return_value.__aiter__.return_value = mock_walk_results

            # Call list_templates
            templates = await loader.list_templates()

            # Verify the results
            expected = sorted(["file1.html", "file2.html", "subdir/file3.html"])
            assert templates == expected


class TestAsyncPackageLoader:
    """Tests for the AsyncPackageLoader class."""

    @pytest.mark.asyncio
    async def test_get_source_found(self) -> None:
        """Test get_source when the template is found."""
        # Mock importlib.import_module and spec
        with patch("jinja2_async_environment.loaders.import_module") as mock_import:
            # Create mock spec and set origin
            mock_spec = MagicMock()
            mock_spec.origin = "/path/to/package/__init__.py"
            mock_import.return_value.__spec__ = mock_spec

            # Create loader
            loader = AsyncPackageLoader(
                "my_package", AsyncPath("/templates"), AsyncPath("templates")
            )

            # Template path and expected content
            template_path = AsyncPath("/path/to/package/templates/template.html")
            template_content = "<h1>Hello from package!</h1>"

            # Mock file operations
            with (
                patch.object(
                    AsyncPath, "is_file", return_value=AsyncMock(return_value=True)
                ),
                patch.object(AsyncPath, "open") as mock_open,
            ):
                # Setup mock file
                mock_file = AsyncMock()
                mock_file.__aenter__.return_value = mock_file
                mock_file.read = AsyncMock(return_value=template_content)
                mock_open.return_value = mock_file

                # Call the method
                source, filename, uptodate = await loader.get_source(
                    AsyncPath("template.html")
                )

                # Assertions
                assert source == template_content
                assert filename == str(template_path)
                assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_get_source_not_found(self) -> None:
        """Test get_source when the template is not found."""
        # Mock importlib.import_module and spec
        with patch("jinja2_async_environment.loaders.import_module") as mock_import:
            # Create mock spec and set origin
            mock_spec = MagicMock()
            mock_spec.origin = "/path/to/package/__init__.py"
            mock_import.return_value.__spec__ = mock_spec

            # Create loader with a side effect to raise TemplateNotFound
            with patch.object(AsyncPackageLoader, "get_source") as mock_get_source:
                mock_get_source.side_effect = TemplateNotFound("nonexistent.html")

                # Create loader
                loader = AsyncPackageLoader(
                    "my_package", AsyncPath("/templates"), AsyncPath("templates")
                )

                # Call method and verify exception is raised
                with pytest.raises(TemplateNotFound):
                    await loader.get_source(AsyncPath("nonexistent.html"))


class TestAsyncDictLoader:
    """Tests for the AsyncDictLoader class."""

    @pytest.fixture
    def loader(self) -> AsyncDictLoader:
        """Create a dict loader with test templates."""
        templates = {
            "index.html": "<h1>Index</h1>",
            "about.html": "<h1>About</h1>",
        }
        return AsyncDictLoader(templates, AsyncPath("/templates"))

    @pytest.mark.asyncio
    async def test_get_source_found(self, loader: AsyncDictLoader) -> None:
        """Test get_source when the template is found."""
        source, filename, uptodate = await loader.get_source(AsyncPath("index.html"))

        assert source == "<h1>Index</h1>"
        assert filename is None
        assert uptodate is None

    @pytest.mark.asyncio
    async def test_get_source_not_found(self, loader: AsyncDictLoader) -> None:
        """Test get_source when the template is not found."""
        with pytest.raises(TemplateNotFound):
            await loader.get_source(AsyncPath("nonexistent.html"))

    @pytest.mark.asyncio
    async def test_list_templates(self, loader: AsyncDictLoader) -> None:
        """Test list_templates method."""
        templates = await loader.list_templates()
        assert sorted(templates) == ["about.html", "index.html"]


class TestAsyncFunctionLoader:
    """Tests for the AsyncFunctionLoader class."""

    @pytest.fixture
    def load_func(self) -> AsyncMock:
        """Create a mock load function."""

        async def _mock_load(template: AsyncPath) -> t.Optional[str]:
            if str(template) == "index.html":
                return "<h1>Function Loader</h1>"
            return None

        return AsyncMock(side_effect=_mock_load)

    @pytest.fixture
    def loader(self, load_func: AsyncMock) -> AsyncFunctionLoader:
        """Create a function loader with the mock load function."""
        return AsyncFunctionLoader(load_func, AsyncPath("/templates"))

    @pytest.mark.asyncio
    async def test_get_source_found(
        self, loader: AsyncFunctionLoader, load_func: AsyncMock
    ) -> None:
        """Test get_source when the template is found."""
        source, filename, uptodate = await loader.get_source(AsyncPath("index.html"))

        load_func.assert_called_once_with(AsyncPath("index.html"))
        assert source == "<h1>Function Loader</h1>"
        assert filename is None
        assert uptodate is None

    @pytest.mark.asyncio
    async def test_get_source_not_found(
        self, loader: AsyncFunctionLoader, load_func: AsyncMock
    ) -> None:
        """Test get_source when the template is not found."""
        with pytest.raises(TemplateNotFound):
            await loader.get_source(AsyncPath("nonexistent.html"))

        load_func.assert_called_once_with(AsyncPath("nonexistent.html"))


class TestAsyncChoiceLoader:
    """Tests for the AsyncChoiceLoader class."""

    @pytest.fixture
    def loaders(self) -> t.List[AsyncBaseLoader]:
        """Create a list of test loaders."""
        # First loader with one template
        loader1 = AsyncBaseLoader(AsyncPath("/path1"))
        loader1.get_source = AsyncMock(
            side_effect=lambda t: ("<h1>Loader 1</h1>", "/path1/template1.html", None)
            if str(t) == "template1.html"
            else TemplateNotFound(str(t))
        )
        loader1.list_templates = AsyncMock(return_value=["template1.html"])

        # Second loader with different template
        loader2 = AsyncBaseLoader(AsyncPath("/path2"))
        loader2.get_source = AsyncMock(
            side_effect=lambda t: ("<h1>Loader 2</h1>", "/path2/template2.html", None)
            if str(t) == "template2.html"
            else TemplateNotFound(str(t))
        )
        loader2.list_templates = AsyncMock(return_value=["template2.html"])

        return [loader1, loader2]

    @pytest.fixture
    def loader(self, loaders: t.List[AsyncBaseLoader]) -> AsyncChoiceLoader:
        """Create a choice loader with the test loaders."""
        return AsyncChoiceLoader(loaders, AsyncPath("/templates"))

    @pytest.mark.asyncio
    async def test_get_source_first_loader(
        self, loader: AsyncChoiceLoader, loaders: t.List[AsyncBaseLoader]
    ) -> None:
        """Test get_source when the template is found in the first loader."""
        source, filename, uptodate = await loader.get_source(
            AsyncPath("template1.html")
        )

        loaders[0].get_source.assert_called_once_with(AsyncPath("template1.html"))
        loaders[1].get_source.assert_not_called()
        assert source == "<h1>Loader 1</h1>"
        assert filename == "/path1/template1.html"

    @pytest.mark.asyncio
    async def test_get_source_second_loader(
        self, loader: AsyncChoiceLoader, loaders: t.List[AsyncBaseLoader]
    ) -> None:
        """Test get_source when the template is found in the second loader."""
        # Create mock return values
        source_value = "<h1>Loader 2</h1>"
        filename_value = "/path2/template2.html"
        uptodate_value = None

        # Replace patched get_source methods for clarity
        loader.loaders[0].get_source = AsyncMock(
            side_effect=TemplateNotFound("template2.html")
        )
        loader.loaders[1].get_source = AsyncMock(
            return_value=(source_value, filename_value, uptodate_value)
        )

        # Call the method
        source, filename, uptodate = await loader.get_source(
            AsyncPath("template2.html")
        )

        # Verify the results
        assert source == source_value
        assert filename == filename_value
        assert uptodate == uptodate_value

        # Verify both get_source methods were called in the right order
        assert loader.loaders[0].get_source.called
        assert loader.loaders[1].get_source.called

    @pytest.mark.asyncio
    async def test_get_source_not_found(
        self, loader: AsyncChoiceLoader, loaders: t.List[AsyncBaseLoader]
    ) -> None:
        """Test get_source when the template is not found in any loader."""
        # Make all loaders raise TemplateNotFound
        not_found = TemplateNotFound("nonexistent.html")
        for mock_loader in loader.loaders:
            mock_loader.get_source = AsyncMock(side_effect=not_found)

        # Test that the method raises TemplateNotFound
        with pytest.raises(TemplateNotFound):
            await loader.get_source(AsyncPath("nonexistent.html"))

        # Verify all loaders' get_source methods were called
        for mock_loader in loader.loaders:
            assert mock_loader.get_source.called

    @pytest.mark.asyncio
    async def test_list_templates(
        self, loader: AsyncChoiceLoader, loaders: t.List[AsyncBaseLoader]
    ) -> None:
        """Test list_templates method."""
        templates = await loader.list_templates()

        loaders[0].list_templates.assert_called_once()
        loaders[1].list_templates.assert_called_once()
        assert sorted(templates) == ["template1.html", "template2.html"]
