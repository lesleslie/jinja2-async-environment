"""Async filesystem template loader implementation."""

import typing as t
from collections import namedtuple
from contextlib import suppress

from anyio import Path as AsyncPath
from jinja2.utils import internalcode

from .base import AsyncBaseLoader, SourceType

# Define TemplatePathData type for better type checking
TemplatePathData = namedtuple("TemplatePathData", ["template_name", "should_include"])


class TemplatePathDataType(t.NamedTuple):
    """Type definition for template path data."""

    template_name: str | None
    should_include: bool


if t.TYPE_CHECKING:
    from ..environment import AsyncEnvironment


class AsyncFileSystemLoader(AsyncBaseLoader):
    """Async filesystem template loader with memory optimization.

    This loader searches for templates in the filesystem asynchronously,
    supporting multiple search paths and proper file watching for
    template updates.
    """

    __slots__ = ("encoding", "followlinks", "_template_cache")

    def __init__(
        self,
        searchpath: AsyncPath | str | t.Sequence[AsyncPath | str],
        encoding: str = "utf-8",
        followlinks: bool = False,
    ) -> None:
        """Initialize the filesystem loader.

        Args:
            searchpath: Path or sequence of paths to search for templates
            encoding: File encoding to use when reading templates
            followlinks: Whether to follow symbolic links
        """
        super().__init__(searchpath)
        self.encoding = encoding
        self.followlinks = followlinks
        self._template_cache: dict[str, tuple[float, str]] = {}

    @internalcode
    async def get_source_async(
        self, environment: "AsyncEnvironment", name: str
    ) -> SourceType:
        """Get template source from filesystem asynchronously.

        Args:
            environment: The async environment instance
            name: Template name to load

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If template file cannot be found
        """
        self._ensure_initialized()

        for searchpath in self.searchpath:
            template_path = searchpath / name

            try:
                if await template_path.exists():
                    if not await self._is_safe_path(template_path):
                        continue

                    # Read the template file
                    source = await template_path.read_text(encoding=self.encoding)
                    filename = str(template_path.resolve())

                    # Get the modification time for uptodate check
                    stat_result = await template_path.stat()
                    mtime = stat_result.st_mtime

                    # Create uptodate function
                    def uptodate() -> bool:
                        try:
                            from pathlib import Path

                            return Path(filename).stat().st_mtime == mtime
                        except OSError:
                            return False

                    return source, filename, uptodate

            except OSError:
                # Continue to next search path
                continue

        # Template not found in any search path
        self._handle_template_not_found(name)
        # This line should never be reached, but added for type checker
        raise RuntimeError("Unreachable code")

    async def _is_safe_path(self, template_path: AsyncPath) -> bool:
        """Check if the template path is safe to access.

        Args:
            template_path: Path to check

        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Check if it's a file
            if not await template_path.is_file():
                return False

            # If not following links, check for symlinks
            if not self.followlinks and await template_path.is_symlink():
                return False

            # Check that the resolved path is within search paths
            resolved_path = await template_path.resolve()

            for searchpath in self.searchpath:
                resolved_searchpath = await searchpath.resolve()
                try:
                    resolved_path.relative_to(str(resolved_searchpath))
                    return True
                except ValueError:
                    continue

            return False

        except OSError:
            return False

    @internalcode
    async def list_templates_async(self) -> list[str]:
        """List all templates in the search paths asynchronously.

        Returns:
            Sorted list of template names
        """
        self._ensure_initialized()

        found_templates = set()

        for searchpath in self.searchpath:
            templates = await self._list_templates_in_path(searchpath)
            found_templates.update(templates)

        return sorted(found_templates)

    async def _list_templates_in_path(self, searchpath: AsyncPath) -> set[str]:
        """List templates in a single search path.

        Args:
            searchpath: Search path to list templates from

        Returns:
            Set of template names found in this path
        """
        if not await searchpath.exists():
            return set()

        found_templates = set()
        with suppress(OSError):
            # Use rglob to find all files recursively
            async for template_path in searchpath.rglob("*"):
                if await template_path.is_file():
                    template_data = await self._process_template_path(
                        searchpath, template_path
                    )
                    if (
                        template_data.should_include
                        and template_data.template_name is not None
                    ):
                        found_templates.add(template_data.template_name)

        return found_templates

    async def _process_template_path(
        self, searchpath: AsyncPath, template_path: AsyncPath
    ) -> TemplatePathDataType:
        """Process a template path to determine if it should be included.

        Args:
            searchpath: Search path
            template_path: Template path to process

        Returns:
            Named tuple with template name and whether it should be included
        """
        template_name = await self._get_template_name(searchpath, template_path)
        if template_name and await self._is_safe_path(template_path):
            return TemplatePathDataType(template_name, True)
        return TemplatePathDataType(None, False)

    async def _get_template_name(
        self, searchpath: AsyncPath, template_path: AsyncPath
    ) -> str | None:
        """Get template name from template path.

        Args:
            searchpath: Search path
            template_path: Full path to template

        Returns:
            Template name or None if path is not relative to searchpath
        """
        try:
            relative_path = template_path.relative_to(str(searchpath))
            return str(relative_path).replace("\\", "/")
        except ValueError:
            # Path is not relative to searchpath
            return None

    async def _walk_directory(
        self, directory: AsyncPath
    ) -> t.AsyncGenerator[AsyncPath]:
        """Async generator to walk directory tree.

        Args:
            directory: Directory to walk

        Yields:
            AsyncPath objects for each file/directory found
        """
        if not await directory.exists():
            return

        try:
            async for item in directory.iterdir():
                yield item

                # Check if we should recurse into this directory
                if await self._should_recurse_into_directory(item):
                    async for subitem in self._walk_subdirectory(item):
                        yield subitem

        except (OSError, PermissionError):
            # Skip directories we can't access
            return

    async def _should_recurse_into_directory(self, item: AsyncPath) -> bool:
        """Check if we should recurse into a directory.

        Args:
            item: Directory to check

        Returns:
            True if we should recurse, False otherwise
        """
        return await item.is_dir() and (self.followlinks or not await item.is_symlink())

    async def _walk_subdirectory(
        self, directory: AsyncPath
    ) -> t.AsyncGenerator[AsyncPath]:
        """Async generator to walk subdirectory tree.

        Args:
            directory: Subdirectory to walk

        Yields:
            AsyncPath objects for each file/directory found
        """
        async for subitem in self._walk_directory(directory):
            yield subitem

    def _get_cache_key(self, name: str) -> str:
        """Generate cache key for template.

        Args:
            name: Template name

        Returns:
            Cache key string
        """
        return f"fs:{name}"
