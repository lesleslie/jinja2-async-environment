"""Async dictionary template loader implementation."""

import typing as t

from jinja2.utils import internalcode

from .base import AsyncBaseLoader, SourceType

if t.TYPE_CHECKING:
    from ..environment import AsyncEnvironment


class AsyncDictLoader(AsyncBaseLoader):
    """Async dictionary template loader with memory optimization.

    This loader stores templates in memory as a dictionary, useful for
    testing and applications that generate templates dynamically.
    """

    __slots__ = ("mapping",)

    def __init__(
        self,
        mapping: dict[str, str],
        searchpath: t.Any = None,  # For backward compatibility
    ) -> None:
        """Initialize the dictionary loader.

        Args:
            mapping: Dictionary mapping template names to template source
            searchpath: Path or sequence of paths for compatibility
        """
        # Call parent with provided searchpath
        if searchpath is not None:
            super().__init__(searchpath)
        else:
            # Call parent with empty searchpath for backward compatibility
            super().__init__([])
        self.mapping = dict(mapping)  # Create a copy for safety

    @internalcode
    async def get_source_async(
        self, environment: "AsyncEnvironment", name: str
    ) -> SourceType:
        """Get template source from dictionary asynchronously with caching.

        Args:
            environment: The async environment instance
            name: Template name to load

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If template is not in the mapping
        """
        self._ensure_initialized()

        # Try to get from cache first
        cache_manager = self._get_cache_manager(environment)
        cache_key = f"dict:{name}"

        if cache_manager:
            cached_source = cache_manager.get("template", cache_key)
            if cached_source is not None:
                return cached_source

        if name not in self.mapping:
            self._handle_template_not_found(name)

        source = self.mapping[name]

        # For dictionary loader, we use None as filename and create an uptodate function
        # that checks if the template still exists and has the same content
        def uptodate() -> bool:
            # Check if template still exists
            if name not in self.mapping:
                return False
            # Check if content is the same
            current_content = self.mapping[name]
            return current_content == source

        source_data = (source, None, uptodate)

        # Cache the result
        if cache_manager:
            cache_manager.set("template", cache_key, source_data)

        return source_data

    @internalcode
    async def list_templates_async(self) -> list[str]:
        """List all templates in the mapping asynchronously.

        Returns:
            Sorted list of template names
        """
        self._ensure_initialized()
        return sorted(self.mapping.keys())

    def add_template(self, name: str, source: str) -> None:
        """Add a new template to the mapping.

        Args:
            name: Template name
            source: Template source code
        """
        self.mapping[name] = source

    def remove_template(self, name: str) -> None:
        """Remove a template from the mapping.

        Args:
            name: Template name to remove

        Raises:
            KeyError: If template is not in the mapping
        """
        del self.mapping[name]

    def update_mapping(self, mapping: dict[str, str]) -> None:
        """Update the template mapping.

        Args:
            mapping: New mapping to merge with existing templates
        """
        self.mapping.update(mapping)

    def clear_templates(self) -> None:
        """Clear all templates from the mapping."""
        self.mapping.clear()

    def has_template(self, name: str) -> bool:
        """Check if a template exists in the mapping.

        Args:
            name: Template name to check

        Returns:
            True if template exists, False otherwise
        """
        return name in self.mapping
