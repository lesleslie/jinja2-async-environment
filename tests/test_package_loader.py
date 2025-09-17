from contextlib import contextmanager
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncPackageLoader,
    LoaderNotFound,
    PackageSpecNotFound,
)


@contextmanager
def isolated_test_context(test_name: str):
    """Context manager for isolated test execution with proper cleanup."""
    import gc

    # Import test context functions
    from jinja2_async_environment.testing.context import (
        clear_test_context,
        set_test_name,
    )

    # Set test context
    set_test_name(test_name)

    # Force garbage collection to clear any lingering references
    gc.collect()

    try:
        yield
    finally:
        # Always cleanup after test
        clear_test_context()
        # Force garbage collection after test
        gc.collect()

        # Clear environment caches again
        if hasattr(AsyncEnvironment, "_cache_manager"):
            delattr(AsyncEnvironment, "_cache_manager")

        # Force another garbage collection
        gc.collect()


class TestAsyncPackageLoader:
    @pytest.fixture(scope="function")
    def mock_package_spec(self) -> MagicMock:
        """Create a fresh mock package spec for each test."""
        spec = MagicMock()
        spec.submodule_search_locations = ["/path/to/package"]
        return spec

    @pytest.fixture(scope="function")
    def mock_loader(self) -> MagicMock:
        """Create a fresh mock loader for each test."""
        loader = MagicMock()
        loader.get_data = MagicMock(return_value=b"<h1>Template content</h1>")
        return loader

    @pytest.fixture(scope="function")
    def mock_find_spec(
        self, mock_package_spec: MagicMock, mock_loader: MagicMock
    ) -> MagicMock:
        """Create a fresh mock find_spec for each test."""
        mock_package_spec.loader = mock_loader
        mock_find = MagicMock(return_value=mock_package_spec)
        return mock_find

    @pytest.fixture(scope="function")
    def mock_import_module(self) -> MagicMock:
        """Create a fresh mock import_module for each test."""
        return MagicMock()

    @pytest.fixture(scope="function")
    def package_loader_factory(self):
        """Factory for creating isolated package loaders."""

        def create_loader(monkeypatch, mock_content=b"<h1>Template content</h1>"):
            """Create a mocked package loader with isolated state."""
            # Create fresh mocks for this specific loader instance
            mock_loader = MagicMock()
            # Ensure this loader does NOT have archive attribute (regular filesystem loader)
            if hasattr(mock_loader, "archive"):
                delattr(mock_loader, "archive")
            mock_loader.get_data = MagicMock(return_value=mock_content)

            mock_spec = MagicMock()
            mock_spec.loader = mock_loader
            mock_spec.submodule_search_locations = ["/path/to/package"]

            mock_import_module = MagicMock()

            # Use monkeypatch to apply mocks that are scoped to this test
            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module",
                mock_import_module,
            )
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )

            loader = AsyncPackageLoader(
                "test_package",
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )
            return loader

        return create_loader

    @pytest.fixture(scope="function", autouse=False)
    def package_loader(self, request, monkeypatch) -> AsyncPackageLoader:
        """Create a mocked package loader for testing with function-level isolation.

        This fixture is explicitly not autouse to prevent contamination.
        Tests that need different mock configurations should create their own loaders.
        """
        # Only create the loader if explicitly requested by test
        if hasattr(request, "param") and request.param == "skip":
            pytest.skip("Test configured to skip package_loader fixture")

        # Create fresh mocks for this specific test
        mock_loader = MagicMock()
        # Ensure this loader does NOT have archive attribute (regular filesystem loader)
        if hasattr(mock_loader, "archive"):
            delattr(mock_loader, "archive")
        mock_loader.get_data = MagicMock(return_value=b"<h1>Template content</h1>")

        mock_spec = MagicMock()
        mock_spec.loader = mock_loader
        mock_spec.submodule_search_locations = ["/path/to/package"]

        mock_import_module = MagicMock()

        # Use monkeypatch to apply mocks that are scoped to this test
        monkeypatch.setattr(
            "jinja2_async_environment.loaders.package.import_module", mock_import_module
        )
        monkeypatch.setattr(
            "importlib.util.find_spec", MagicMock(return_value=mock_spec)
        )

        loader = AsyncPackageLoader(
            "test_package",
            AsyncPath("/templates"),
            package_path=AsyncPath("templates"),
        )
        return loader

    # Removed shared environment fixture to prevent contamination
    # Tests that need environments should create them inline

    def test_init_package_not_found(
        self, mock_import_module: MagicMock, monkeypatch
    ) -> None:
        # Use monkeypatch for proper isolation
        monkeypatch.setattr("importlib.util.find_spec", MagicMock(return_value=None))
        monkeypatch.setattr(
            "jinja2_async_environment.loaders.package.import_module",
            mock_import_module,
        )

        with pytest.raises(PackageSpecNotFound):
            loader = AsyncPackageLoader(
                "nonexistent_package",
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )
            # Trigger lazy initialization where the error should occur
            loader._ensure_initialized()

    def test_init_loader_not_found(
        self, mock_import_module: MagicMock, monkeypatch
    ) -> None:
        mock_spec = MagicMock()
        mock_spec.loader = None

        # Use monkeypatch for proper isolation
        monkeypatch.setattr(
            "importlib.util.find_spec", MagicMock(return_value=mock_spec)
        )
        monkeypatch.setattr(
            "jinja2_async_environment.loaders.package.import_module",
            mock_import_module,
        )

        with pytest.raises(LoaderNotFound):
            loader = AsyncPackageLoader(
                "package_without_loader",
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )
            # Trigger lazy initialization where the error should occur
            loader._ensure_initialized()

    def test_init_template_root_not_found(
        self, mock_import_module: MagicMock, monkeypatch
    ) -> None:
        with isolated_test_context("test_init_template_root_not_found"):
            mock_spec = MagicMock()
            mock_spec.loader = MagicMock()
            mock_spec.submodule_search_locations = []
            mock_spec.origin = None

            # Use monkeypatch for proper isolation
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )
            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module",
                mock_import_module,
            )

            with pytest.raises(
                ValueError,
                match="was not installed in a way that PackageLoader understands",
            ):
                loader = AsyncPackageLoader(
                    "package_without_template_root",
                    AsyncPath("/templates"),
                    package_path=AsyncPath("templates"),
                )
                # Trigger lazy initialization where the error should occur
                loader._ensure_initialized()

    def test_init_success(self, monkeypatch) -> None:
        with isolated_test_context("test_init_success"):
            # Create a fresh loader for this test with unique package name
            mock_loader = MagicMock()
            if hasattr(mock_loader, "archive"):
                delattr(mock_loader, "archive")
            mock_loader.get_data = MagicMock(return_value=b"<h1>Template content</h1>")

            mock_spec = MagicMock()
            mock_spec.loader = mock_loader
            mock_spec.submodule_search_locations = ["/path/to/package"]

            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module", MagicMock()
            )
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )

            package_loader = AsyncPackageLoader(
                "test_package_init_success",  # Unique package name to avoid cache conflicts
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )

            assert package_loader.package_name == "test_package_init_success"
            assert package_loader.package_path == AsyncPath("templates")
            assert package_loader.encoding == "utf-8"

            # Force initialization to test the lazy loading behavior
            package_loader._ensure_initialized()

            assert package_loader._archive is None
            assert isinstance(package_loader._template_root, AsyncPath)

    @pytest.mark.asyncio
    async def test_get_source_async_not_found(self, monkeypatch) -> None:
        with isolated_test_context("test_get_source_async_not_found"):
            # Create a fresh loader for this test with unique package name
            mock_loader = MagicMock()
            if hasattr(mock_loader, "archive"):
                delattr(mock_loader, "archive")
            mock_loader.get_data = MagicMock(return_value=b"<h1>Template content</h1>")

            mock_spec = MagicMock()
            mock_spec.loader = mock_loader
            mock_spec.submodule_search_locations = ["/path/to/package"]

            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module", MagicMock()
            )
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )

            package_loader = AsyncPackageLoader(
                "test_package_not_found",  # Unique package name to avoid cache conflicts
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )

            # Ensure loader is initialized first
            package_loader._ensure_initialized()

            with patch.object(
                package_loader._loader,
                "get_data",
                side_effect=OSError("File not found"),
            ):
                with pytest.raises(TemplateNotFound):
                    await package_loader.get_source_async(
                        AsyncEnvironment(), "nonexistent.html"
                    )

    @pytest.mark.asyncio
    async def test_get_source_async_success(self, monkeypatch) -> None:
        with isolated_test_context("test_get_source_async_success"):
            # Create a fresh loader for this test with unique package name
            mock_loader = MagicMock()
            if hasattr(mock_loader, "archive"):
                delattr(mock_loader, "archive")
            mock_loader.get_data = MagicMock(return_value=b"<h1>Template content</h1>")

            mock_spec = MagicMock()
            mock_spec.loader = mock_loader
            mock_spec.submodule_search_locations = ["/path/to/package"]

            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module", MagicMock()
            )
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )

            package_loader = AsyncPackageLoader(
                "test_package_success",  # Unique package name to avoid cache conflicts
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )

            # Ensure loader is initialized first
            package_loader._ensure_initialized()

            with patch.object(
                package_loader._loader,
                "get_data",
                return_value=b"<h1>Template content</h1>",
            ):
                source, filename, uptodate = await package_loader.get_source_async(
                    AsyncEnvironment(), "template.html"
                )
                assert source == "<h1>Template content</h1>"
                assert filename.endswith("template.html")
                assert callable(uptodate)

    @pytest.mark.asyncio
    async def test_get_source_async_with_archive(
        self, mock_import_module: MagicMock, monkeypatch
    ) -> None:
        with isolated_test_context("test_get_source_async_with_archive"):
            # Create a mock that properly simulates a zipimporter with archive attribute
            mock_zipimporter = MagicMock()
            mock_zipimporter.archive = "/path/to/archive.zip"

            # Ensure hasattr(mock_zipimporter, "archive") returns True
            type(mock_zipimporter).archive = PropertyMock(
                return_value="/path/to/archive.zip"
            )

            mock_spec = MagicMock()
            mock_spec.loader = mock_zipimporter
            mock_spec.submodule_search_locations = ["/path/to/package"]

            # Use monkeypatch for isolated mocking
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )
            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module",
                mock_import_module,
            )

            with (
                patch(
                    "pathlib.Path.__truediv__",
                    return_value=MagicMock(is_dir=lambda: True),
                ),
                patch("zipimport.zipimporter", return_value=mock_zipimporter),
            ):
                loader = AsyncPackageLoader(
                    "test_package_archive",  # Unique package name to avoid cache conflicts
                    AsyncPath("/templates"),
                    package_path=AsyncPath("templates"),
                )

                # Force initialization to set up archive properly
                loader._ensure_initialized()

                # Manually set the archive to simulate proper archive loader detection
                loader._archive = "/path/to/archive.zip"

                # Mock the _get_source_with_archive method directly to avoid path complexity
                expected_source = (
                    "<h1>Zip template</h1>",
                    "/path/to/package/templates/template.html",
                    lambda: True,
                )

                with patch.object(
                    loader, "_get_source_with_archive", return_value=expected_source
                ) as mock_get_source:
                    source, filename, uptodate = await loader.get_source_async(
                        AsyncEnvironment(), "template.html"
                    )
                    assert source == "<h1>Zip template</h1>"
                    assert filename.endswith("template.html")
                    assert callable(uptodate)
                    assert uptodate() is True

                    # Verify the method was called with the right template path
                    mock_get_source.assert_called_once()
                    call_args = mock_get_source.call_args[0]
                    assert str(call_args[0]) == "template.html"

    @pytest.mark.asyncio
    async def test_list_templates_async_regular(self, monkeypatch) -> None:
        with isolated_test_context("test_list_templates_async_regular"):
            # Create a fresh loader for this test with unique package name
            mock_loader = MagicMock()
            if hasattr(mock_loader, "archive"):
                delattr(mock_loader, "archive")
            mock_loader.get_data = MagicMock(return_value=b"<h1>Template content</h1>")

            mock_spec = MagicMock()
            mock_spec.loader = mock_loader
            mock_spec.submodule_search_locations = ["/path/to/package"]

            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module", MagicMock()
            )
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )

            package_loader = AsyncPackageLoader(
                "test_package_list_regular",  # Unique package name to avoid cache conflicts
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )

            # Ensure loader is initialized
            package_loader._ensure_initialized()

            # Mock the _list_templates_regular method directly to avoid complex path mocking
            expected_templates = [
                "template1.html",
                "template2.html",
                "subdir/template3.html",
            ]

            with patch.object(
                package_loader,
                "_list_templates_regular",
                return_value=expected_templates,
            ) as mock_list:
                templates = await package_loader.list_templates_async()
                assert len(templates) == 3
                assert all(t.endswith(".html") for t in templates)
                assert templates == expected_templates
                mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_templates_async_zip(
        self, mock_import_module: MagicMock, monkeypatch
    ) -> None:
        with isolated_test_context("test_list_templates_async_zip"):
            mock_zipimporter = MagicMock()
            mock_zipimporter.archive = "/path/to/archive.zip"
            mock_zipimporter._files = {
                "templates/template1.html": MagicMock(),
                "templates/template2.html": MagicMock(),
                "templates/subdir/template3.html": MagicMock(),
                "other/file.txt": MagicMock(),
            }

            mock_spec = MagicMock()
            mock_spec.loader = mock_zipimporter
            mock_spec.submodule_search_locations = ["/path/to/package"]

            mock_path = AsyncPath("/path/to/package/templates")

            # Use monkeypatch for isolated mocking
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )
            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module",
                mock_import_module,
            )

            with (
                patch("anyio.Path.is_file", return_value=True),
                patch.object(AsyncPath, "is_dir", return_value=True),
                patch("anyio.Path.__truediv__", return_value=mock_path),
            ):
                loader = AsyncPackageLoader(
                    "test_package_list_zip",  # Unique package name to avoid cache conflicts
                    AsyncPath("/templates"),
                    package_path=AsyncPath("templates"),
                )

                templates = await loader.list_templates_async()
                assert len(templates) == 3
                assert all(t.startswith("templates/") for t in templates)
                assert all(t.endswith(".html") for t in templates)
                assert templates == sorted(templates)

    @pytest.mark.asyncio
    async def test_list_templates_async_zip_no_files(
        self, mock_import_module: MagicMock, monkeypatch
    ) -> None:
        with isolated_test_context("test_list_templates_async_zip_no_files"):
            # Create a mock that properly simulates a zipimporter without _files
            mock_zipimporter = MagicMock()
            mock_zipimporter.archive = "/path/to/archive.zip"
            mock_zipimporter.get_data = MagicMock()

            # Make sure _files attribute doesn't exist by deleting it if it was auto-created
            if hasattr(mock_zipimporter, "_files"):
                delattr(mock_zipimporter, "_files")

            mock_spec = MagicMock()
            mock_spec.loader = mock_zipimporter
            mock_spec.submodule_search_locations = ["/path/to/package"]

            mock_path = AsyncPath("/path/to/package/templates")

            # Use monkeypatch for isolated mocking
            monkeypatch.setattr(
                "importlib.util.find_spec", MagicMock(return_value=mock_spec)
            )
            monkeypatch.setattr(
                "jinja2_async_environment.loaders.package.import_module",
                mock_import_module,
            )

            with (
                patch("anyio.Path.is_file", return_value=True),
                patch.object(AsyncPath, "is_dir", return_value=True),
                patch("anyio.Path.__truediv__", return_value=mock_path),
            ):
                loader = AsyncPackageLoader(
                    "test_package_zip_no_files",  # Unique package name to avoid cache conflicts
                    AsyncPath("/templates"),
                    package_path=AsyncPath("templates"),
                )

                with pytest.raises(
                    TypeError, match="does not have the required metadata"
                ):
                    await loader.list_templates_async()
