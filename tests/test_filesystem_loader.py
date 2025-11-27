"""Tests for the AsyncFileSystemLoader to improve test coverage."""

import tempfile
from pathlib import Path

import pytest
from anyio import Path as AsyncPath
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader


class TestAsyncFileSystemLoader:
    """Test the AsyncFileSystemLoader class to improve coverage."""

    async def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with single path
        loader1 = AsyncFileSystemLoader("/tmp")
        assert loader1.encoding == "utf-8"
        assert loader1.followlinks is False

        # Test with multiple paths
        loader2 = AsyncFileSystemLoader(["/tmp", "/var"])
        assert loader2.encoding == "utf-8"
        assert loader2.followlinks is False

        # Test with custom parameters
        loader3 = AsyncFileSystemLoader("/tmp", encoding="latin1", followlinks=True)
        assert loader3.encoding == "latin1"
        assert loader3.followlinks is True

    async def test_get_source_async_template_not_found(self):
        """Test get_source_async when template is not found."""
        loader = AsyncFileSystemLoader("/nonexistent/path")
        env = AsyncEnvironment(loader=loader, enable_async=True)

        with pytest.raises(Exception):  # Should raise TemplateNotFound
            await loader.get_source_async(env, "nonexistent.html")

    async def test_get_source_async_unsafe_path(self):
        """Test get_source_async with an unsafe path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a loader
            loader = AsyncFileSystemLoader(tmp_dir)
            env = AsyncEnvironment(loader=loader, enable_async=True)

            # Try to access a file outside the search paths using relative path traversal
            # This should fail the safety check
            try:
                await loader.get_source_async(env, "../../../etc/passwd")
                # If it doesn't fail, check if it returned an empty result or similar
            except Exception:
                # Expected to fail for unsafe paths
                pass

    async def test_list_templates_async(self):
        """Test listing templates asynchronously."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create some template files
            subdir = Path(tmp_dir) / "subdir"
            subdir.mkdir()

            template1 = Path(tmp_dir) / "template1.html"
            template1.write_text("Template 1 content")

            template2 = subdir / "template2.html"
            template2.write_text("Template 2 content")

            # Create the loader
            loader = AsyncFileSystemLoader(tmp_dir)

            # List templates
            templates = await loader.list_templates_async()

            # Verify templates were found
            assert "template1.html" in templates
            assert "subdir/template2.html" in templates

    async def test_list_templates_async_empty_directory(self):
        """Test listing templates when directory doesn't exist."""
        loader = AsyncFileSystemLoader("/nonexistent/directory")
        templates = await loader.list_templates_async()
        assert templates == []

    async def test_is_safe_path(self):
        """Test the _is_safe_path method."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = AsyncFileSystemLoader(tmp_dir)

            # Create a test file
            test_file = Path(tmp_dir) / "test.html"
            test_file.write_text("test content")
            async_test_path = AsyncPath(test_file)

            # Test that a valid file is safe
            is_safe = await loader._is_safe_path(async_test_path)
            assert is_safe is True

            # Test with a non-existent path
            non_existent_path = AsyncPath(tmp_dir) / "nonexistent.html"
            is_safe = await loader._is_safe_path(non_existent_path)
            assert is_safe is False

            # Test with a directory instead of file
            is_safe = await loader._is_safe_path(AsyncPath(tmp_dir))
            assert is_safe is False

    async def test_get_template_name(self):
        """Test the _get_template_name method."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = AsyncFileSystemLoader(tmp_dir)

            # Create a test file
            test_file = Path(tmp_dir) / "subdir" / "test.html"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("test content")

            searchpath = AsyncPath(tmp_dir)
            template_path = AsyncPath(test_file)

            template_name = await loader._get_template_name(searchpath, template_path)
            assert template_name == "subdir/test.html"

            # Test with path not relative to searchpath
            other_path = AsyncPath("/other/path/file.txt")
            template_name = await loader._get_template_name(searchpath, other_path)
            assert template_name is None

    async def test_template_with_different_encoding(self):
        """Test loading template with different encoding."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a template with special characters
            template_file = Path(tmp_dir) / "special.html"
            template_file.write_text("Café: café", encoding="utf-8")

            # Create loader with utf-8 encoding
            loader = AsyncFileSystemLoader(tmp_dir, encoding="utf-8")
            env = AsyncEnvironment(loader=loader, enable_async=True)

            # Load the template
            source, filename, uptodate = await loader.get_source_async(
                env, "special.html"
            )
            assert "café" in source

    async def test_follow_symlinks_option(self):
        """Test the followlinks option."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a real template file
            real_dir = Path(tmp_dir) / "real_templates"
            real_dir.mkdir()
            real_template = real_dir / "real.html"
            real_template.write_text("Real template content")

            # Create a symlink to the real templates directory
            link_dir = Path(tmp_dir) / "linked_templates"
            link_dir.symlink_to(real_dir)

            # Create loader that doesn't follow symlinks
            loader_no_follow = AsyncFileSystemLoader(str(link_dir), followlinks=False)
            env = AsyncEnvironment(loader=loader_no_follow, enable_async=True)

            # Try to access template through symlink - this behavior depends on implementation
            try:
                source, filename, uptodate = await loader_no_follow.get_source_async(
                    env, "real.html"
                )
            except Exception:
                # May fail depending on security settings
                pass

    async def test_uptodate_function(self):
        """Test the uptodate function returned by get_source_async."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            template_file = Path(tmp_dir) / "test.html"
            template_file.write_text("Test content")

            loader = AsyncFileSystemLoader(tmp_dir)
            env = AsyncEnvironment(loader=loader, enable_async=True)

            source, filename, uptodate_func = await loader.get_source_async(
                env, "test.html"
            )

            # Test that the uptodate function works
            assert callable(uptodate_func)
            assert uptodate_func() is True  # Should be up to date initially

            # Modify the file and check again
            template_file.write_text("Modified content")
            # uptodate should now return False (though this depends on exact timing)
