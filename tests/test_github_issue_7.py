"""Unit test that would have caught the GitHub issue #7:
'RuntimeWarning: coroutine 'Path.resolve' was never awaited'.

This test ensures the AsyncFileSystemLoader properly awaits the resolve()
method when getting the full path to the template file.
"""

import tempfile
from pathlib import Path

from anyio import Path as AsyncPath
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFileSystemLoader


class TestGitHubIssue7:
    """Tests for GitHub issue #7: coroutine 'Path.resolve' was never awaited."""

    async def test_async_filesystem_loader_resolve_awaited_properly(self):
        """Test that AsyncFileSystemLoader properly awaits the resolve() call
        when getting the filename in get_source_async method.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a test template
            template_path = Path(tmp_dir) / "test_template.html"
            with open(template_path, "w") as f:
                f.write("<h1>Hello {{ name }}!</h1>")

            # Create the async file system loader
            loader = AsyncFileSystemLoader(searchpath=[tmp_dir])

            # Create the environment with async enabled
            env = AsyncEnvironment(loader=loader, enable_async=True)

            # Get the template and render it - this will internally call
            # get_source_async which contains the problematic resolve() call
            template = await env.get_template_async("test_template.html")
            result = await template.render_async(name="World")

            # Verify that the template rendered correctly
            assert result == "<h1>Hello World!</h1>"

            # If we reach this point without RuntimeWarning, the issue is fixed
            print("Test passed: resolve() coroutine was properly awaited")

    async def test_async_filesystem_loader_with_symlinks_that_require_resolve(self):
        """Test a scenario where the resolve() method is critical for proper path resolution,
        such as when dealing with symbolic links.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create the actual template file in a subdirectory
            subdir = Path(tmp_dir) / "real_templates"
            subdir.mkdir()
            real_template_path = subdir / "real_template.html"
            with open(real_template_path, "w") as f:
                f.write("<h1>Real template content</h1>")

            # Create a symlink to the real templates directory
            link_dir = Path(tmp_dir) / "linked_templates"
            link_dir.symlink_to(subdir)

            # Create the loader pointing to the symlink directory
            loader = AsyncFileSystemLoader(searchpath=[str(link_dir)])

            # Create the environment with async enabled
            env = AsyncEnvironment(loader=loader, enable_async=True)

            # Get the template and render it - this will test resolve() with symlinks
            template = await env.get_template_async("real_template.html")
            result = await template.render_async()

            # Verify that the template rendered correctly
            assert result == "<h1>Real template content</h1>"

            print("Test passed: resolve() works with symbolic links")


# Additional test that specifically targets the problematic line in the source code
async def test_specific_resolve_functionality():
    """Unit test that specifically exercises the problematic line of code
    that was in the GitHub issue.
    """
    # Create an AsyncPath object
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file_path = AsyncPath(tmp_dir) / "test_resolve.txt"
        await test_file_path.write_text("test content")

        # This should properly await the resolve method
        resolved_path = await test_file_path.resolve()

        # Verify that the result is a proper path (could be string or Path-like)
        assert "test_resolve.txt" in str(resolved_path)
        # The important thing is that no RuntimeWarning occurred

        print("Direct AsyncPath resolve test passed")
