"""Tests for the AsyncPackageLoader to improve test coverage."""

import importlib
import importlib.util
import sys
import tempfile
import typing as t
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.caching.manager import CacheManager
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncPackageLoader
from jinja2_async_environment.loaders.package import (
    LoaderNotFound,
    PackageLoaderError,
    PackageSpecNotFound,
)


@contextmanager
def temporary_package(
    package_name: str,
    templates: dict[str, str] | None = None,
) -> t.Iterator[tuple[Path, str]]:
    """Create a temporary Python package with optional template files.

    Yields the package's namespace directory (the directory containing the
    package) and the package name. The directory is added to sys.path so the
    package can be imported during the test.
    """
    tmp_root = tempfile.mkdtemp(prefix="pkg_loader_test_")

    pkg_dir = Path(tmp_root) / package_name
    pkg_dir.mkdir()

    (pkg_dir / "__init__.py").write_text('"""Test package for AsyncPackageLoader."""\n')

    if templates:
        templates_dir = pkg_dir / "templates"
        templates_dir.mkdir()
        for name, content in templates.items():
            file_path = templates_dir / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    sys.path.insert(0, tmp_root)
    try:
        yield Path(tmp_root), package_name
    finally:
        if package_name in sys.modules:
            del sys.modules[package_name]
        for key in list(sys.modules.keys()):
            if key.startswith(f"{package_name}."):
                del sys.modules[key]
        try:
            sys.path.remove(tmp_root)
        except ValueError:
            pass
        import shutil

        shutil.rmtree(tmp_root, ignore_errors=True)


def _wrap_loader_with_filesystem(loader: t.Any, pkg_dir: Path) -> t.Any:
    """Wrap a package loader so its get_data() reads from a real directory.

    The AsyncPackageLoader's regular-path code calls
    ``self._loader.get_data(template_pkg_path)``, but for a normal
    SourceFileLoader this path is resolved relative to the package's
    __init__.py (which doesn't work for nested paths).  This wrapper
    reads the file directly from the on-disk package directory.

    Pass the *initialized* loader here, or call _ensure_initialized()
    after wrapping.
    """
    if loader is None:
        # Caller hasn't initialized yet; return a no-op stand-in. The real
        # wrapping is set up below after init.
        return None

    class _FileSystemGetDataLoader:
        def __init__(self, real_loader: t.Any) -> None:
            self._real_loader = real_loader

        def __getattr__(self, name: str) -> t.Any:
            return getattr(self._real_loader, name)

        def get_data(self, path: str) -> bytes:
            file_path = pkg_dir / path
            if not file_path.is_file():
                raise FileNotFoundError(path)
            return file_path.read_bytes()

    return _FileSystemGetDataLoader(loader)


class TestAsyncPackageLoader:
    """Test the AsyncPackageLoader class to improve coverage."""

    async def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with minimal parameters
        loader1 = AsyncPackageLoader("sys")
        assert loader1.package_name == "sys"
        assert str(loader1.package_path) == "templates"

        # Test with custom encoding
        loader2 = AsyncPackageLoader("sys", encoding="latin1")
        assert loader2.encoding == "latin1"

        # Test with AsyncPath
        loader3 = AsyncPackageLoader("sys")
        assert loader3.package_name == "sys"
        assert str(loader3.package_path) == "templates"

    async def test_perform_initialization_with_empty_package_name(self):
        """Test _perform_initialization with empty package name raises error."""
        loader = AsyncPackageLoader("")
        with pytest.raises(PackageSpecNotFound):
            loader._perform_initialization()

    async def test_perform_initialization_with_whitespace_package_name(self):
        """Test _initialize_loader rejects whitespace-only package names."""
        loader = AsyncPackageLoader("os")
        with pytest.raises(PackageSpecNotFound):
            loader._initialize_loader("   ")

    async def test_get_source_async_package_not_found(self):
        """Test get_source_async when package doesn't exist."""
        loader = AsyncPackageLoader("nonexistent_package_12345")
        env = AsyncEnvironment(loader=loader, enable_async=True)

        with pytest.raises(Exception):  # Should raise PackageSpecNotFound or similar
            await loader.get_source_async(env, "template.html")

    async def test_package_with_nonexistent_template(self):
        """Test accessing a non-existent template in a valid package."""
        # Use a real package name that should exist
        loader = AsyncPackageLoader("os")
        env = AsyncEnvironment(loader=loader, enable_async=True)

        # This should fail because "nonexistent.html" doesn't exist
        with pytest.raises(Exception):  # Should raise TemplateNotFound
            await loader.get_source_async(env, "nonexistent.html")

    async def test_list_templates_async(self):
        """Test listing templates in the package."""
        # When the package has no templates dir, list_templates_async raises
        # ValueError during initialization (Jinja2-compatible behavior).
        loader = AsyncPackageLoader("sys")
        with pytest.raises(ValueError, match="was not installed"):
            await loader.list_templates_async()

    async def test_perform_initialization_with_custom_error(self):
        """Test the initialization flow raises ValueError for a package with no.

        templates directory (Jinja2-compatible behavior).
        """
        loader = AsyncPackageLoader("os")

        with pytest.raises(ValueError, match="was not installed"):
            loader._perform_initialization()
        # Error state was reset on the way out.
        assert loader._template_root is None
        assert loader._loader is None
        assert loader._spec is None

    async def test_initialize_loader_directly(self):
        """Test the _initialize_loader method directly."""
        loader = AsyncPackageLoader("os")

        # Test with valid package
        pkg_loader, spec = loader._initialize_loader("os")
        assert pkg_loader is not None
        assert spec is not None

    async def test_initialize_loader_invalid_package(self):
        """Test _initialize_loader with invalid package."""
        loader = AsyncPackageLoader("os")

        # Test with invalid package name
        with pytest.raises(PackageSpecNotFound):
            loader._initialize_loader("nonexistent_package_12345")

    async def test_initialize_loader_empty_package_name(self):
        """Test _initialize_loader with empty package name."""
        loader = AsyncPackageLoader("os")

        # Test with empty package name
        with pytest.raises(PackageSpecNotFound):
            loader._initialize_loader("")

    async def test_perform_initialization_error_handling(self):
        """Test error handling in _perform_initialization."""
        loader = AsyncPackageLoader("nonexistent_package_12345")

        # This should fail initialization
        with pytest.raises(PackageSpecNotFound):
            loader._perform_initialization()

        # Verify that error state was properly reset
        assert loader._template_root is None
        assert loader._loader is None
        assert loader._spec is None


class TestAsyncPackageLoaderRealPackage:
    """Test AsyncPackageLoader against a real (temporary) test package with templates."""

    async def test_get_source_with_real_template(self):
        """Load a template from a real (temporary) package."""
        with temporary_package(
            "test_tpl_pkg",
            templates={
                "hello.html": "<h1>Hello, {{ name }}!</h1>",
                "subdir/nested.html": "<p>nested {{ value }}</p>",
            },
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            # Trigger lazy init so _loader is populated, then wrap it
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(loader._loader, root / pkg_name)

            source, filename, uptodate = await loader.get_source_async(
                env, "hello.html"
            )
            assert source == "<h1>Hello, {{ name }}!</h1>"
            assert filename is not None
            assert "hello.html" in filename
            assert callable(uptodate)
            assert uptodate() is True

    async def test_get_source_missing_template_in_real_package(self):
        """Loading a missing template in an existing package should raise TemplateNotFound."""
        with temporary_package(
            "test_tpl_pkg_missing",
            templates={"hello.html": "<h1>Hello</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            with pytest.raises(TemplateNotFound):
                await loader.get_source_async(env, "no_such_template.html")

    async def test_get_source_with_unicode_decode_error(self):
        """Verify invalid encoding raises TemplateNotFound."""
        with temporary_package(
            "test_tpl_pkg_enc",
            templates={"hello.html": "<h1>Hello</h1>"},
        ) as (root, pkg_name):
            # Use ASCII encoding with non-ASCII content; the file is written
            # with raw bytes including a 0xff sequence.
            pkg_dir = root / pkg_name
            (pkg_dir / "templates" / "hello.html").write_bytes(
                b"<h1>Hello \xff World</h1>"
            )
            loader = AsyncPackageLoader(
                pkg_name, encoding="ascii"
            )
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, pkg_dir
            )

            with pytest.raises(TemplateNotFound, match="invalid ascii encoding"):
                await loader.get_source_async(env, "hello.html")

    async def test_get_source_with_latin1_encoding(self):
        """Verify custom encoding is actually used in decode."""
        with temporary_package("test_tpl_pkg_latin1") as (root, pkg_name):
            pkg_dir = root / pkg_name
            (pkg_dir / "templates").mkdir(exist_ok=True)
            (pkg_dir / "templates" / "latin.html").write_bytes(
                b"<p>caf\xe9</p>"
            )

            loader = AsyncPackageLoader(pkg_name, encoding="latin-1")
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, pkg_dir
            )

            source, _, _ = await loader.get_source_async(env, "latin.html")
            assert "café" in source

    async def test_get_source_with_empty_name(self):
        """An empty template name should raise TemplateNotFound."""
        loader = AsyncPackageLoader("os")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(env, "")
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(env, "   ")

    async def test_list_templates_async_finds_files(self):
        """list_templates_async should find html/htm/xml/txt files."""
        with temporary_package(
            "test_tpl_pkg_list",
            templates={
                "a.html": "a",
                "b.htm": "b",
                "c.xml": "c",
                "d.txt": "d",
                "sub/e.html": "e",
                "ignored.bin": "should not be listed",
            },
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_list")
            templates = await loader.list_templates_async()
            assert "a.html" in templates
            assert "b.htm" in templates
            assert "c.xml" in templates
            assert "d.txt" in templates
            # Subdirectory templates should be found
            normalized = [t.replace("\\", "/") for t in templates]
            assert "sub/e.html" in normalized
            # Non-template files should be skipped
            assert "ignored.bin" not in templates

    async def test_list_templates_async_when_dir_missing(self):
        """list_templates_async raises ValueError when the templates dir doesn't exist."""
        loader = AsyncPackageLoader("os")
        with pytest.raises(ValueError, match="was not installed"):
            await loader.list_templates_async()


class TestAsyncPackageLoaderCaching:
    """Test the cache integration paths in get_source_async."""

    async def test_get_source_uses_cache(self):
        """When the cache has the value, get_source_async should return it without.

        re-reading the underlying file.
        """
        with temporary_package(
            "test_tpl_pkg_cache",
            templates={"cached.html": "<h1>cached</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            cache_manager = CacheManager()
            env = AsyncEnvironment(
                loader=loader, cache_manager=cache_manager, enable_async=True
            )
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            # Prime the cache via a real load
            await loader.get_source_async(env, "cached.html")

            # Cache should now contain the entry
            cached_result = cache_manager.get(
                "template", f"{pkg_name}:cached.html"
            )
            assert cached_result is not None
            assert cached_result[0] == "<h1>cached</h1>"

    async def test_get_source_cache_set_called(self):
        """Ensure the cache is populated after a successful load."""
        with temporary_package(
            "test_tpl_pkg_cache_set",
            templates={"hello.html": "<h1>hi</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            cache_manager = CacheManager()
            env = AsyncEnvironment(
                loader=loader, cache_manager=cache_manager, enable_async=True
            )
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            await loader.get_source_async(env, "hello.html")
            cached = cache_manager.get("template", f"{pkg_name}:hello.html")
            assert cached is not None
            assert cached[0] == "<h1>hi</h1>"

    async def test_get_source_cache_set_failure_does_not_break(self):
        """Cache.set errors should be swallowed and the load should still succeed."""
        with temporary_package(
            "test_tpl_pkg_cache_set_fail",
            templates={"ok.html": "<h1>ok</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            # Force a cache.set to raise
            with patch.object(
                CacheManager, "set", side_effect=RuntimeError("boom")
            ):
                # Should still succeed
                source, _, _ = await loader.get_source_async(env, "ok.html")
                assert source == "<h1>ok</h1>"

    async def test_get_source_cache_get_failure_does_not_break(self):
        """Cache.get errors should be swallowed and the load should still succeed."""
        with temporary_package(
            "test_tpl_pkg_cache_get_fail",
            templates={"ok.html": "<h1>ok</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            with patch.object(
                CacheManager, "get", side_effect=RuntimeError("boom")
            ):
                # Should still succeed despite cache.get error
                source, _, _ = await loader.get_source_async(env, "ok.html")
                assert source == "<h1>ok</h1>"


class TestAsyncPackageLoaderArchivePath:
    """Test the archive-based loader path (via mocking)."""

    async def test_archive_loader_with_files(self):
        """Mock an archive-style loader that exposes _files."""
        with temporary_package(
            "test_tpl_pkg_archive",
            templates={"x.html": "<h1>archive</h1>"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_archive")
            loader._ensure_initialized()
            real_loader = loader._loader
            loader._archive = "/fake/path/to/archive.zip"

            class _FakeArchiveLoader:
                archive = "/fake/path/to/archive.zip"
                _files = [
                    "templates/index.html",
                    "templates/about.htm",
                    "templates/data.xml",
                    "templates/notes.txt",
                    "templates/skip.bin",
                ]

                def get_data(self, path):  # pragma: no cover - not called here
                    return b""

            loader._loader = _FakeArchiveLoader()

            templates = await loader.list_templates_async()
            assert "templates/index.html" in templates
            assert "templates/about.htm" in templates
            assert "templates/data.xml" in templates
            assert "templates/notes.txt" in templates
            assert "templates/skip.bin" not in templates

            loader._loader = real_loader
            loader._archive = None

    async def test_archive_loader_without_files_attribute(self):
        """Archive loader with no _files and only get_data should raise TypeError."""
        with temporary_package(
            "test_tpl_pkg_archive_nofiles",
            templates={"x.html": "<h1>archive</h1>"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_archive_nofiles")
            loader._ensure_initialized()
            real_loader = loader._loader

            class _FakeLoaderNoFiles:
                archive = "/fake/path/to/archive.zip"

                def get_data(self, path):  # pragma: no cover - not called here
                    return b""

            loader._loader = _FakeLoaderNoFiles()
            loader._archive = "/fake/path/to/archive.zip"

            with pytest.raises(TypeError):
                await loader.list_templates_async()

            loader._loader = real_loader
            loader._archive = None

    async def test_archive_loader_without_get_data_returns_empty(self):
        """Archive loader with no _files and no get_data should return []."""
        with temporary_package(
            "test_tpl_pkg_archive_nogetdata",
            templates={"x.html": "<h1>archive</h1>"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_archive_nogetdata")
            loader._ensure_initialized()
            real_loader = loader._loader

            class _FakeLoaderNothing:
                archive = "/fake/path/to/archive.zip"

            loader._loader = _FakeLoaderNothing()
            loader._archive = "/fake/path/to/archive.zip"

            templates = await loader.list_templates_async()
            assert templates == []

            loader._loader = real_loader
            loader._archive = None

    async def test_get_source_with_archive(self):
        """The archive branch of get_source_async should successfully load a template."""
        with temporary_package(
            "test_tpl_pkg_archive_load",
            templates={"arc.html": "<h1>archive</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            real_loader = loader._loader
            real_root = loader._template_root

            class _FakeArchiveSource:
                archive = "/fake/archive.zip"

            loader._loader = _FakeArchiveSource()
            loader._archive = "/fake/archive.zip"
            # _template_root is already populated by _ensure_initialized

            source, filename, uptodate = await loader.get_source_async(
                env, "arc.html"
            )
            assert source == "<h1>archive</h1>"
            assert filename is not None
            assert callable(uptodate)
            # Archive uptodate is always True
            assert uptodate() is True

            loader._loader = real_loader
            loader._archive = None
            loader._template_root = real_root

    async def test_get_source_archive_with_missing_file(self):
        """Archive branch should raise TemplateNotFound if the file does not exist."""
        with temporary_package(
            "test_tpl_pkg_archive_missing",
            templates={"exists.html": "<h1>exists</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            real_loader = loader._loader
            real_root = loader._template_root

            class _FakeArchiveSource2:
                archive = "/fake/archive.zip"

            loader._loader = _FakeArchiveSource2()
            loader._archive = "/fake/archive.zip"

            with pytest.raises(TemplateNotFound):
                await loader.get_source_async(env, "missing_in_archive.html")

            loader._loader = real_loader
            loader._archive = None
            loader._template_root = real_root

    async def test_get_source_archive_with_no_template_root(self):
        """Archive branch with no _template_root should raise RuntimeError."""
        with temporary_package(
            "test_tpl_pkg_no_root",
            templates={"a.html": "a"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_no_root")
            AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            saved_root = loader._template_root
            loader._template_root = None
            loader._archive = "/fake/archive.zip"

            with pytest.raises(RuntimeError):
                await loader._get_source_with_archive(AsyncPath("anything.html"))

            loader._template_root = saved_root
            loader._archive = None

    async def test_get_source_regular_with_no_template_root(self):
        """Regular branch with no _template_root should raise RuntimeError."""
        with temporary_package(
            "test_tpl_pkg_no_root2",
            templates={"a.html": "a"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_no_root2")
            loader._ensure_initialized()
            saved_root = loader._template_root
            loader._template_root = None

            with pytest.raises(RuntimeError):
                await loader._get_source_regular(AsyncPath("anything.html"))

            loader._template_root = saved_root

    async def test_get_source_with_get_data_oserror(self):
        """Regular branch should raise TemplateNotFound when get_data raises OSError."""
        with temporary_package(
            "test_tpl_pkg_oserror",
            templates={"present.html": "<h1>present</h1>"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_oserror")
            env = AsyncEnvironment(loader=loader, enable_async=True)
            real_loader = loader._loader

            class _BoomLoader:
                def get_data(self, path):
                    raise FileNotFoundError(f"no such file: {path}")

            loader._loader = _BoomLoader()
            with pytest.raises(TemplateNotFound):
                await loader.get_source_async(env, "missing.html")

            loader._loader = real_loader

    async def test_uptodate_function_returns_false_when_file_removed(self):
        """The uptodate() closure should return False when the underlying file goes away."""
        with temporary_package(
            "test_tpl_pkg_uptodate",
            templates={"will_be_gone.html": "<h1>gone</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            source, _, uptodate = await loader.get_source_async(env, "will_be_gone.html")
            assert source == "<h1>gone</h1>"
            assert uptodate() is True

            # Remove the file and call uptodate again
            (root / pkg_name / "templates" / "will_be_gone.html").unlink()

            assert uptodate() is False

    async def test_uptodate_function_handles_oserror(self):
        """uptodate() should swallow OSError and return False when the file is.

        removed or otherwise inaccessible (matches jinja2.PackageLoader).
        """
        with temporary_package(

            "test_tpl_pkg_uptodate_os",
            templates={"hi.html": "<h1>hi</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            source, _, uptodate = await loader.get_source_async(env, "hi.html")
            assert source == "<h1>hi</h1>"

            # Remove the file — the new uptodate() uses os.path.is_file
            # directly, so deleting the template is the right way to make
            # the sync stat()/is_file() calls raise OSError.
            (root / pkg_name / "templates" / "hi.html").unlink()
            assert uptodate() is False


class TestAsyncPackageLoaderContextValueError:
    """Missing template directory raises the Jinja2-compatible ValueError."""

    async def test_perform_init_raises_valueerror_when_no_templates_dir(self):
        """When a package has no templates subdirectory, _perform_initialization.

        raises ValueError with the same message Jinja2's PackageLoader uses.
        """
        # 'os' is a single-module stdlib package with no 'templates' directory.
        loader = AsyncPackageLoader("os")
        with pytest.raises(ValueError, match="was not installed"):
            loader._perform_initialization()
        # Error state was reset on the way out.
        assert loader._template_root is None
        assert loader._loader is None
        assert loader._spec is None


class TestAsyncPackageLoaderSpecEdgeCases:
    """Edge cases around spec and loader resolution."""

    async def test_initialize_loader_import_error_message(self):
        """A failed import_module should produce a useful PackageSpecNotFound."""
        loader = AsyncPackageLoader("os")
        with pytest.raises(PackageSpecNotFound) as excinfo:
            loader._initialize_loader("definitely_not_a_real_pkg_xyz_123")
        assert "not found" in str(excinfo.value).lower()

    async def test_initialize_loader_with_module_only(self):
        """A module without submodule_search_locations still works for spec.origin path."""
        # The 'sys' module has no submodule_search_locations
        loader = AsyncPackageLoader("os")
        pkg_loader, spec = loader._initialize_loader("sys")
        assert spec.submodule_search_locations is None
        assert spec.origin is not None
        assert pkg_loader is not None

    async def test_initialize_loader_raises_loader_not_found(self):
        """When importlib returns a spec with loader=None, raise LoaderNotFound.

        Real packages always have a loader, so we synthesize one with
        unittest.mock.patch on find_spec. Covers the LoaderNotFound branch
        in _initialize_loader that no other test exercises.

        Also verifies the new ``package_name`` attribute on the exception
        is set to the package that triggered the failure, so callers can
        log it without parsing the message string.
        """

        class _SpecNoLoader:
            loader = None
            submodule_search_locations = None
            origin = None

        loader = AsyncPackageLoader("os")
        # Ensure the module is imported first (the production code calls
        # import_module before find_spec, mirroring jinja2.PackageLoader).
        importlib.import_module("os")
        with patch("importlib.util.find_spec", return_value=_SpecNoLoader()):
            with pytest.raises(LoaderNotFound) as excinfo:
                loader._initialize_loader("os")
        assert "No loader found" in str(excinfo.value)
        assert excinfo.value.package_name == "os"
        # And it's catchable via the common base.
        assert isinstance(excinfo.value, PackageLoaderError)

    async def test_initialize_loader_raises_spec_not_found_with_package_name(self):
        """PackageSpecNotFound should also carry the package_name attribute."""
        loader = AsyncPackageLoader("os")
        with pytest.raises(PackageSpecNotFound) as excinfo:
            loader._initialize_loader("definitely_not_a_real_pkg_xyz_123")
        assert excinfo.value.package_name == "definitely_not_a_real_pkg_xyz_123"
        assert isinstance(excinfo.value, PackageLoaderError)

    async def test_package_loader_error_base_catches_both_subtypes(self):
        """Single ``except`` clause catches both ``LoaderNotFound`` and ``PackageSpecNotFound``.

        This is the main value of the new common base class: callers
        who want to handle any package-loader resolution failure can
        write a single ``except`` clause.
        """
        loader = AsyncPackageLoader("os")

        # Both subtypes must be catchable as PackageLoaderError.
        caught_loader: list[Exception] = []
        caught_spec: list[Exception] = []

        class _SpecNoLoader:
            loader = None
            submodule_search_locations = None
            origin = None

        # First scenario: a spec with no loader -> LoaderNotFound.
        try:
            importlib.import_module("os")  # ensure importable
            with patch(
                "importlib.util.find_spec", return_value=_SpecNoLoader()
            ):
                loader._initialize_loader("os")
        except PackageLoaderError as e:  # single clause for both
            caught_loader.append(e)

        # Second scenario: a missing package -> PackageSpecNotFound.
        try:
            loader._initialize_loader("definitely_not_a_real_pkg_xyz_456")
        except PackageLoaderError as e:  # same clause catches the other type
            caught_spec.append(e)

        assert len(caught_loader) == 1
        assert len(caught_spec) == 1
        # And the caught exceptions are the right subtypes (and both
        # carry the package_name attribute through the common base).
        assert isinstance(caught_loader[0], LoaderNotFound)
        assert caught_loader[0].package_name == "os"
        assert isinstance(caught_spec[0], PackageSpecNotFound)
        assert caught_spec[0].package_name == "definitely_not_a_real_pkg_xyz_456"

    async def test_package_loader_error_default_package_name(self):
        """``PackageLoaderError`` can be raised directly with or without ``package_name``.

        Documents the public API of the new common base class for
        callers who want to raise it outside the package loader itself.
        """
        err_default = PackageLoaderError("boom")

        assert err_default.package_name is None
        assert str(err_default) == "boom"

        err_explicit = PackageLoaderError("boom", package_name="x")
        assert err_explicit.package_name == "x"
        assert str(err_explicit) == "boom"

    async def test_get_regular_template_root_uses_origin(self):
        """_get_regular_template_root should return None when no root has the.

        templates subdirectory (Jinja2-compatible behavior).
        """
        loader = AsyncPackageLoader("os")
        spec = importlib.util.find_spec("sys")
        assert spec is not None
        package_path = AsyncPath("definitely_missing_dir_xyz")
        result = loader._get_regular_template_root(spec, package_path)
        assert result is None

    async def test_get_regular_template_root_uses_search_locations(self):
        """_get_regular_template_root should return None when no search location.

        has the templates subdirectory.
        """
        loader = AsyncPackageLoader("os")

        spec = importlib.util.find_spec("jinja2_async_environment")
        assert spec is not None
        assert spec.submodule_search_locations is not None
        package_path = AsyncPath("definitely_missing_dir_xyz")
        result = loader._get_regular_template_root(spec, package_path)
        assert result is None

    async def test_get_regular_template_root_finds_existing_dir(self):
        """_get_regular_template_root should return the package path when the dir exists."""
        with temporary_package(
            "test_tpl_pkg_root",
            templates={"a.html": "a"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_root")
            loader._ensure_initialized()
            spec = importlib.util.find_spec("test_tpl_pkg_root")
            assert spec is not None
            package_path = AsyncPath("templates")
            result = loader._get_regular_template_root(spec, package_path)
            assert result is not None

    async def test_get_archive_template_root_uses_search_locations(self):
        """_get_archive_template_root should use spec.submodule_search_locations when present."""
        loader = AsyncPackageLoader("os")

        class _ArchiveLoader:
            archive = "/fake.zip"

        loader._loader = _ArchiveLoader()
        spec = importlib.util.find_spec("jinja2_async_environment")
        assert spec is not None
        result = loader._get_archive_template_root(spec)
        assert result is not None
        loader._loader = None

    async def test_get_archive_template_root_returns_none_without_search_locations(self):
        """_get_archive_template_root should return None when no submodule_search_locations."""
        loader = AsyncPackageLoader("os")

        class _ArchiveLoader2:
            archive = "/fake.zip"

        loader._loader = _ArchiveLoader2()
        spec = importlib.util.find_spec("sys")
        assert spec is not None
        assert spec.submodule_search_locations is None
        result = loader._get_archive_template_root(spec)
        assert result is None
        loader._loader = None

    async def test_find_template_root_archive(self):
        """_find_template_root should dispatch to archive path when loader has 'archive' attr."""
        loader = AsyncPackageLoader("os")

        class _ArchiveLoader3:
            archive = "/fake.zip"

        loader._loader = _ArchiveLoader3()
        spec = importlib.util.find_spec("jinja2_async_environment")
        result = loader._find_template_root(spec, AsyncPath("templates"))
        assert result is not None
        loader._loader = None

    async def test_find_template_root_regular(self):
        """_find_template_root should dispatch to regular path when loader has no 'archive'."""
        with temporary_package(
            "test_tpl_pkg_find_root",
            templates={"a.html": "a"},
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_find_root")
            loader._ensure_initialized()
            spec = importlib.util.find_spec("test_tpl_pkg_find_root")
            assert spec is not None
            result = loader._find_template_root(spec, AsyncPath("templates"))
            assert result is not None

    async def test_list_templates_regular_with_no_dir(self):
        """_list_templates_regular: when the package is initialized despite.

        missing templates dir (forced via spec), the listing returns [].
        """
        with temporary_package(
            "test_tpl_pkg_no_dir",
        ):
            loader = AsyncPackageLoader("test_tpl_pkg_no_dir")
            # Force the loader into a "no templates dir" state by manipulating
            # _template_root after _find_template_root returns None.
            # Use a real package so the import succeeds; then point _template_root
            # at a non-existent directory.
            loader._loader, loader._spec = loader._initialize_loader(
                "test_tpl_pkg_no_dir"
            )
            loader._template_root = AsyncPath("/nonexistent/path/that/doesnt/exist")
            loader._archive = None
            templates = await loader._list_templates_regular()
            assert templates == []


class TestAsyncPackageLoaderNoCacheManager:
    """When the env has no cache_manager attribute, code paths should still work."""

    async def test_get_source_without_cache_manager(self):
        """Get_source should still work when env has no cache_manager attribute."""
        with temporary_package(
            "test_tpl_pkg_nocache",
            templates={"hello.html": "<h1>hi</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            # Remove the cache_manager attribute
            saved = env._cache_manager
            delattr(env, "_cache_manager")

            try:
                source, _, _ = await loader.get_source_async(env, "hello.html")
                assert source == "<h1>hi</h1>"
            finally:
                env._cache_manager = saved


class TestAsyncPackageLoaderPathSafety:
    """Defend against path-traversal and symlink-escape attacks.

    A template name is operator-controlled in normal use, but anything
    that accepts template names from external input (e.g. a query
    parameter, a path derived from a URL) is a potential attack
    surface. These tests verify that names which try to escape the
    package's templates directory are rejected with TemplateNotFound,
    not silently loaded.
    """

    async def test_path_traversal_raises_template_not_found(self):
        """A ``..``-laden template name must not escape the templates dir.

        The loader's contract is to raise TemplateNotFound, not to leak
        the target file via a relative path traversal.
        """
        with temporary_package(
            "test_tpl_pkg_traversal",
            templates={"hello.html": "<h1>hi</h1>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            # Try to read the file outside the package via ../
            with pytest.raises(TemplateNotFound):
                await loader.get_source_async(env, "../../../etc/passwd")

    async def test_symlink_escape_raises_template_not_found(self):
        """A symlink escaping the templates dir is rejected by default.

        ``followlinks=False`` is the safe setting; an attacker-controlled
        template name cannot be used to read arbitrary files on disk.

        Also verifies the side effect: the file outside the package is
        NOT read (its mtime is unchanged after the call). Without this
        side-effect assertion, a regression where ``_is_safe_path``
        returns False for ``..`` containment but accepts symlink escape
        could still raise ``TemplateNotFound`` for an unrelated reason
        (e.g., decode failure) and this test would pass.
        """
        with temporary_package(

            "test_tpl_pkg_symlink_escape",
            templates={"hello.html": "<h1>hi</h1>"},
        ) as (root, pkg_name):
            # Create a real file OUTSIDE the package and a symlink
            # INSIDE the templates dir pointing at it.
            outside = root / "secret.txt"
            outside.write_text("SECRET")
            mtime_before = outside.stat().st_mtime

            templates_dir = root / pkg_name / "templates"
            evil_link = templates_dir / "evil.html"
            try:
                evil_link.symlink_to(outside)
            except (OSError, NotImplementedError):
                pytest.skip("symlinks not supported on this platform")

            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            with pytest.raises(TemplateNotFound):
                await loader.get_source_async(env, "evil.html")

            # Side-effect assertion: the outside file was not read.
            # (Read would update atime on some filesystems; mtime is
            # not bumped by reads, so we assert mtime equality.)
            assert outside.stat().st_mtime == mtime_before

    async def test_followlinks_true_allows_legitimate_symlinks(self):
        """Legitimate in-tree symlinks are allowed when ``followlinks=True``.

        A symlink whose target is OUTSIDE the templates dir is still
        rejected; the containment check fires before the symlink check.
        """
        with temporary_package(
            "test_tpl_pkg_followlinks",
            templates={"real.html": "<h1>real</h1>"},
        ) as (root, pkg_name):
            templates_dir = root / pkg_name / "templates"
            inside_target = templates_dir / "real.html"
            alias = templates_dir / "alias.html"
            try:
                alias.symlink_to(inside_target)
            except (OSError, NotImplementedError):
                pytest.skip("symlinks not supported on this platform")

            loader = AsyncPackageLoader(pkg_name, followlinks=True)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            # The symlink resolves to a path still under the templates
            # root, so followlinks=True should let it through.
            source, _, _ = await loader.get_source_async(env, "alias.html")
            assert source == "<h1>real</h1>"

    async def test_safe_path_within_package_works(self):
        """Sanity check: legitimate template names still load.

        No traversal or symlink trickery here; just an ordinary load,
        which is the regression baseline the safety check must not break.
        """
        with temporary_package(

            "test_tpl_pkg_safety_ok",
            templates={
                "hello.html": "<h1>hi</h1>",
                "subdir/nested.html": "<p>nested</p>",
            },
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            # Top-level template
            source, _, _ = await loader.get_source_async(env, "hello.html")
            assert source == "<h1>hi</h1>"

            # Nested template (still inside the package root)
            source, _, _ = await loader.get_source_async(env, "subdir/nested.html")
            assert source == "<p>nested</p>"

    async def test_archive_path_traversal_raises_template_not_found(self):
        """The archive branch's ``_is_safe_path`` invocation rejects ``..`` too.

        Phase 2 added ``_is_safe_path`` at both invocation sites
        (``_get_source_regular`` and ``_get_source_with_archive``), but
        the 4 new path-safety tests only exercise the regular branch.
        This test forces the archive branch by attaching an ``archive``
        attribute to the loader and verifies containment fires there too.
        """
        with temporary_package(
            "test_tpl_pkg_arch_traversal",
            templates={"ok.html": "<p>ok</p>"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            env = AsyncEnvironment(loader=loader, enable_async=True)
            loader._ensure_initialized()
            loader._loader = _wrap_loader_with_filesystem(
                loader._loader, root / pkg_name
            )

            # Force the archive branch: stub an archive attribute on the
            # loader so ``_get_archive_template_root`` is selected.
            loader._archive = "/fake/archive.zip"

            try:
                with pytest.raises(TemplateNotFound):
                    await loader.get_source_async(env, "../../../etc/passwd")
            finally:
                loader._archive = None


class TestAsyncPackageLoaderIsSafePathUnit:
    """Direct unit tests for ``_is_safe_path``.

    These bypass ``get_source_async`` to cover the defensive branches
    that are unreachable through the public API (e.g. the
    ``_template_root is None`` check). They are also faster than the
    full end-to-end path-safety tests above.
    """

    def test_is_safe_path_returns_false_when_template_root_is_none(self) -> None:
        """Defensive: if ``_template_root`` is None, the helper refuses."""
        loader = AsyncPackageLoader("os")
        loader._template_root = None
        assert loader._is_safe_path(Path("/anything")) is False

    def test_is_safe_path_rejects_traversal(self) -> None:
        """``..`` segments that escape the root are rejected."""
        with temporary_package(
            "test_tpl_pkg_is_safe_traversal",
            templates={"x.html": "x"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            loader._ensure_initialized()
            outside_target = root / "outside.html"
            assert loader._is_safe_path(outside_target) is False

    def test_is_safe_path_accepts_in_tree_file(self) -> None:
        """Files inside the templates dir are accepted."""
        with temporary_package(
            "test_tpl_pkg_is_safe_in_tree",
            templates={"in_tree.html": "x"},
        ) as (root, pkg_name):
            loader = AsyncPackageLoader(pkg_name)
            loader._ensure_initialized()
            in_tree = root / pkg_name / "templates" / "in_tree.html"
            assert loader._is_safe_path(in_tree) is True
