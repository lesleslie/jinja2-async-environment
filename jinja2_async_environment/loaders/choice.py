"""Async choice template loader implementation."""

import typing as t

from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import internalcode

from .base import AsyncBaseLoader, AsyncLoaderProtocol, SourceType

if t.TYPE_CHECKING:
    from ..environment import AsyncEnvironment


class AsyncChoiceLoader(AsyncBaseLoader):
    """Async choice template loader with memory optimization.

    This loader tries multiple loaders in sequence until one successfully
    loads the requested template. Useful for fallback scenarios and
    template inheritance chains.
    """

    __slots__ = ("loaders",)

    def __init__(
        self,
        loaders: t.Sequence[AsyncLoaderProtocol],
        searchpath: AsyncPath | str | t.Sequence[AsyncPath | str] | None = None,
    ) -> None:
        """Initialize the choice loader.

        Args:
            loaders: Sequence of loaders to try in order
            searchpath: Path or sequence of paths for compatibility (not used)
        """
        # Call parent with provided searchpath or empty list
        if searchpath is None:
            searchpath = []
        super().__init__(searchpath)
        self.loaders = list(loaders)  # Create a copy for safety

    @internalcode
    async def get_source_async(
        self, environment: "AsyncEnvironment", name: str
    ) -> SourceType:
        """Get template source by trying loaders in sequence asynchronously.

        Args:
            environment: The async environment instance
            name: Template name to load

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If no loader can find the template
        """
        self._ensure_initialized()

        for loader in self.loaders:
            try:
                result = await loader.get_source_async(environment, name)
                if result is not None:
                    return result
            except TemplateNotFound:
                # Try the next loader
                continue
            except Exception:
                # For other exceptions, continue to next loader
                # but log the error if debugging is enabled
                continue

        # No loader could find the template
        self._handle_template_not_found(name)
        # This line should never be reached, but added for type checker
        raise RuntimeError("Unreachable code")

    @internalcode
    async def list_templates_async(self) -> list[str]:
        """List all templates from all loaders asynchronously.

        Returns:
            Sorted list of unique template names from all loaders
        """
        self._ensure_initialized()

        found_templates = set()

        for loader in self.loaders:
            try:
                templates = await loader.list_templates_async()
                found_templates.update(templates)
            except (TypeError, NotImplementedError):
                # Some loaders don't support listing, skip them
                continue
            except Exception:
                # Log error if debugging is enabled, but continue
                continue

        return sorted(found_templates)

    def add_loader(self, loader: AsyncLoaderProtocol) -> None:
        """Add a loader to the end of the sequence.

        Args:
            loader: Loader to add
        """
        self.loaders.append(loader)

    def insert_loader(self, index: int, loader: AsyncLoaderProtocol) -> None:
        """Insert a loader at the specified position.

        Args:
            index: Position to insert at
            loader: Loader to insert
        """
        self.loaders.insert(index, loader)

    def remove_loader(self, loader: AsyncLoaderProtocol) -> None:
        """Remove a loader from the sequence.

        Args:
            loader: Loader to remove

        Raises:
            ValueError: If loader is not in the sequence
        """
        self.loaders.remove(loader)

    def clear_loaders(self) -> None:
        """Remove all loaders from the sequence."""
        self.loaders.clear()

    def get_loader_count(self) -> int:
        """Get the number of loaders in the sequence.

        Returns:
            Number of loaders
        """
        return len(self.loaders)

    def get_loaders(self) -> list[AsyncLoaderProtocol]:
        """Get a copy of the loader sequence.

        Returns:
            Copy of the loader list
        """
        return self.loaders.copy()
