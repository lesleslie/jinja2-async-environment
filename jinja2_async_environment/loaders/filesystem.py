"""Async filesystem template loader implementation."""

import typing as t

from anyio import Path as AsyncPath
from jinja2.utils import internalcode

from .base import AsyncBaseLoader, SourceType

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
                            import os

                            return os.path.getmtime(filename) == mtime
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
            if not await searchpath.exists():
                continue

            try:
                # Use rglob to find all files recursively
                async for template_path in searchpath.rglob("*"):
                    if await template_path.is_file():
                        # Get relative path from search path
                        try:
                            relative_path = template_path.relative_to(str(searchpath))
                            template_name = str(relative_path).replace("\\", "/")

                            # Only include if it's a safe path
                            if await self._is_safe_path(template_path):
                                found_templates.add(template_name)

                        except ValueError:
                            # Path is not relative to searchpath
                            continue

            except OSError:
                # Skip this search path if it can't be accessed
                continue

        return sorted(found_templates)

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

                if await item.is_dir() and (
                    self.followlinks or not await item.is_symlink()
                ):
                    async for subitem in self._walk_directory(item):
                        yield subitem

        except (OSError, PermissionError):
            # Skip directories we can't access
            return

    def _get_cache_key(self, name: str) -> str:
        """Generate cache key for template.

        Args:
            name: Template name

        Returns:
            Cache key string
        """
        return f"fs:{name}"
