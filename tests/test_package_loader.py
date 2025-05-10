import typing as t
from unittest.mock import MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncPackageLoader,
    LoaderNotFound,
    PackageSpecNotFound,
)


class TestAsyncPackageLoader:
    @pytest.fixture
    def mock_package_spec(self) -> MagicMock:
        spec = MagicMock()
        spec.submodule_search_locations = ["/path/to/package"]
        return spec

    @pytest.fixture
    def mock_loader(self) -> MagicMock:
        loader = MagicMock()
        loader.get_data = MagicMock(return_value=b"<h1>Template content</h1>")
        return loader

    @pytest.fixture
    def mock_find_spec(
        self, mock_package_spec: MagicMock, mock_loader: MagicMock
    ) -> MagicMock:
        mock_package_spec.loader = mock_loader
        mock_find = MagicMock(return_value=mock_package_spec)
        return mock_find

    @pytest.fixture
    def mock_import_module(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def package_loader(
        self, mock_find_spec: MagicMock, mock_import_module: MagicMock
    ) -> AsyncPackageLoader:
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.submodule_search_locations = ["/path/to/package"]
        mock_find_spec.return_value = mock_spec

        mock_path = AsyncPath("/path/to/package/templates")

        with (
            patch("importlib.util.find_spec", return_value=mock_spec),
            patch("jinja2_async_environment.loaders.import_module", mock_import_module),
            patch("anyio.Path.is_dir", return_value=True),
            patch("anyio.Path.__truediv__", return_value=mock_path),
            patch(
                "pathlib.Path.__truediv__", return_value=MagicMock(is_dir=lambda: True)
            ),
        ):
            loader = AsyncPackageLoader(
                "test_package",
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )
            return loader

    @pytest.fixture
    def environment(self, package_loader: AsyncPackageLoader) -> AsyncEnvironment:
        env = AsyncEnvironment(loader=package_loader)
        env.enable_async = True
        return env

    def test_init_package_not_found(self, mock_import_module: MagicMock) -> None:
        with (
            patch("importlib.util.find_spec", return_value=None),
            patch("jinja2_async_environment.loaders.import_module", mock_import_module),
        ):
            with pytest.raises(PackageSpecNotFound):
                AsyncPackageLoader(
                    "nonexistent_package",
                    AsyncPath("/templates"),
                    package_path=AsyncPath("templates"),
                )

    def test_init_loader_not_found(self, mock_import_module: MagicMock) -> None:
        mock_spec = MagicMock()
        mock_spec.loader = None
        with (
            patch("importlib.util.find_spec", return_value=mock_spec),
            patch("jinja2_async_environment.loaders.import_module", mock_import_module),
        ):
            with pytest.raises(LoaderNotFound):
                AsyncPackageLoader(
                    "package_without_loader",
                    AsyncPath("/templates"),
                    package_path=AsyncPath("templates"),
                )

    def test_init_template_root_not_found(self, mock_import_module: MagicMock) -> None:
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.submodule_search_locations = []
        mock_spec.origin = None
        with (
            patch("importlib.util.find_spec", return_value=mock_spec),
            patch("jinja2_async_environment.loaders.import_module", mock_import_module),
        ):
            with pytest.raises(
                ValueError,
                match="was not installed in a way that PackageLoader understands",
            ):
                AsyncPackageLoader(
                    "package_without_template_root",
                    AsyncPath("/templates"),
                    package_path=AsyncPath("templates"),
                )

    def test_init_success(self, package_loader: AsyncPackageLoader) -> None:
        assert package_loader.package_name == "test_package"
        assert package_loader.package_path == AsyncPath("templates")
        assert package_loader.encoding == "utf-8"
        package_loader._archive = None
        assert package_loader._archive is None
        assert isinstance(package_loader._template_root, AsyncPath)

    @pytest.mark.asyncio
    async def test_get_source_async_not_found(
        self, package_loader: AsyncPackageLoader
    ) -> None:
        with patch.object(
            package_loader._loader, "get_data", side_effect=OSError("File not found")
        ):
            with pytest.raises(TemplateNotFound):
                await package_loader.get_source_async("nonexistent.html")

    @pytest.mark.asyncio
    async def test_get_source_async_success(
        self, package_loader: AsyncPackageLoader
    ) -> None:
        with patch.object(
            package_loader._loader,
            "get_data",
            return_value=b"<h1>Template content</h1>",
        ):
            source, filename, uptodate = await package_loader.get_source_async(
                "template.html"
            )
            assert source == "<h1>Template content</h1>"
            assert filename.endswith("template.html")
            assert uptodate is None

    @pytest.mark.asyncio
    async def test_get_source_async_with_archive(
        self, mock_find_spec: MagicMock, mock_import_module: MagicMock
    ) -> None:
        mock_zipimporter = MagicMock()
        mock_zipimporter.archive = "/path/to/archive.zip"

        mock_spec = MagicMock()
        mock_spec.loader = mock_zipimporter
        mock_spec.submodule_search_locations = ["/path/to/package"]

        mock_path = AsyncPath("/path/to/package/templates")

        with (
            patch("importlib.util.find_spec", return_value=mock_spec),
            patch("jinja2_async_environment.loaders.import_module", mock_import_module),
            patch("anyio.Path.is_file", return_value=True),
            patch("anyio.Path.read_bytes", return_value=b"<h1>Zip template</h1>"),
            patch("anyio.Path.stat", return_value=MagicMock(st_mtime=12345)),
            patch("anyio.Path.__truediv__", return_value=mock_path),
            patch(
                "pathlib.Path.__truediv__", return_value=MagicMock(is_dir=lambda: True)
            ),
            patch("zipimport.zipimporter", return_value=mock_zipimporter),
        ):
            loader = AsyncPackageLoader(
                "test_package",
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )

            source, filename, uptodate = await loader.get_source_async("template.html")
            assert source == "<h1>Zip template</h1>"
            assert filename.endswith("template.html")
            assert callable(uptodate)

            with (
                patch("anyio.Path.is_file", return_value=True),
                patch("anyio.Path.stat", return_value=MagicMock(st_mtime=12345)),
            ):
                assert await t.cast(t.Awaitable[bool], uptodate())

            with (
                patch("anyio.Path.is_file", return_value=True),
                patch("anyio.Path.stat", return_value=MagicMock(st_mtime=54321)),
            ):
                assert not await t.cast(t.Awaitable[bool], uptodate())

            with patch("anyio.Path.is_file", return_value=False):
                assert not await t.cast(t.Awaitable[bool], uptodate())

    @pytest.mark.asyncio
    async def test_list_templates_async_regular(
        self, package_loader: AsyncPackageLoader
    ) -> None:
        with patch("anyio.Path.rglob") as mock_rglob:
            mock_rglob.return_value.__aiter__.return_value = [
                AsyncPath("/path/to/package/templates/template1.html"),
                AsyncPath("/path/to/package/templates/template2.html"),
                AsyncPath("/path/to/package/templates/subdir/template3.html"),
            ]
            templates = await package_loader.list_templates_async()
            assert len(templates) == 3
            assert all(t.endswith(".html") for t in templates)
            assert templates == sorted(templates)

    @pytest.mark.asyncio
    async def test_list_templates_async_zip(
        self, mock_find_spec: MagicMock, mock_import_module: MagicMock
    ) -> None:
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

        with (
            patch("importlib.util.find_spec", return_value=mock_spec),
            patch("jinja2_async_environment.loaders.import_module", mock_import_module),
            patch("anyio.Path.is_file", return_value=True),
            patch.object(AsyncPath, "is_dir", return_value=True),
            patch("anyio.Path.__truediv__", return_value=mock_path),
        ):
            loader = AsyncPackageLoader(
                "test_package",
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
        self, mock_find_spec: MagicMock, mock_import_module: MagicMock
    ) -> None:
        mock_zipimporter = MagicMock()
        mock_zipimporter.archive = "/path/to/archive.zip"

        mock_spec = MagicMock()
        mock_spec.loader = mock_zipimporter
        mock_spec.submodule_search_locations = ["/path/to/package"]

        mock_path = AsyncPath("/path/to/package/templates")

        with (
            patch("importlib.util.find_spec", return_value=mock_spec),
            patch("jinja2_async_environment.loaders.import_module", mock_import_module),
            patch("anyio.Path.is_file", return_value=True),
            patch.object(AsyncPath, "is_dir", return_value=True),
            patch("anyio.Path.__truediv__", return_value=mock_path),
        ):
            loader = AsyncPackageLoader(
                "test_package",
                AsyncPath("/templates"),
                package_path=AsyncPath("templates"),
            )

            with pytest.raises(TypeError, match="does not have the required metadata"):
                await loader.list_templates_async()
