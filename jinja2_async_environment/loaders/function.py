# mypy: disable-error-code="return-value"
"""Async function template loader implementation."""

import inspect
import typing as t
from typing import Any

from anyio import Path as AsyncPath
from jinja2.utils import internalcode

from .base import AsyncBaseLoader, SourceType

if t.TYPE_CHECKING:
    from ..environment import AsyncEnvironment

# Type alias for loader functions
LoaderFunction = t.Callable[[str], str | None]
AsyncLoaderFunction = t.Callable[[str], t.Awaitable[str | tuple[Any, ...] | None]]


class AsyncFunctionLoader(AsyncBaseLoader):
    """Async function-based template loader with memory optimization.

    This loader uses a callable function to load templates, allowing for
    custom template retrieval logic such as loading from databases,
    remote services, or other dynamic sources.
    """

    __slots__ = ("load_func", "is_async_func")

    load_func: LoaderFunction | AsyncLoaderFunction
    is_async_func: bool

    def __init__(
        self,
        load_func: LoaderFunction | AsyncLoaderFunction,
        searchpath: AsyncPath | str | t.Sequence[AsyncPath | str] | None = None,
    ) -> None:
        """Initialize the function loader.

        Args:
            load_func: Function that takes a template name and returns
                      template source or None if not found. Can be sync or async.
            searchpath: Path or sequence of paths for compatibility (not used)
        """
        # Call parent with provided searchpath or empty list
        if searchpath is None:
            searchpath = []
        super().__init__(searchpath)
        self.load_func = load_func

        # Detect if the function is async
        import inspect

        self.is_async_func = inspect.iscoroutinefunction(load_func)

    @internalcode
    async def get_source_async(
        self, environment: "AsyncEnvironment", name: str
    ) -> SourceType:
        """Get template source using the loader function asynchronously.

        Args:
            environment: The async environment instance
            name: Template name to load

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If template cannot be loaded by the function
        """
        self._ensure_initialized()

        # Call the loader function (async or sync)
        result = await self._call_load_function(name)

        # Handle None result (this should raise TemplateNotFound)
        if result is None:
            self._handle_template_not_found(name)
            # This line should never be reached, but mypy needs it for type checking
            raise RuntimeError(
                "Template not found handler should have raised exception"
            )

        # At this point, result is guaranteed to be not None
        assert result is not None

        return self._process_load_result(result, name)

    async def _call_load_function(self, name: str) -> t.Any:
        """Call the loader function (async or sync).

        Args:
            name: Template name to load

        Returns:
            Result from the loader function
        """
        if self.is_async_func:
            result = await self._call_async_load_function(name)
            return result
        return self._call_sync_load_function(name)

    async def _call_async_load_function(
        self, name: str
    ) -> str | tuple[Any, ...] | None:
        """Call the async loader function and await result."""
        # Call async function and await result
        initial_result = self.load_func(name)

        # Check if result is awaitable and await it if needed
        import inspect

        if inspect.isawaitable(initial_result):
            result: str | tuple[Any, ...] | None = await initial_result
        else:
            result = initial_result

        # Keep awaiting until we get a non-awaitable result
        while inspect.isawaitable(result):
            awaited_result: str | tuple[Any, ...] | None = await result
            result = awaited_result

        # At this point, result should be str | None | tuple[Any, ...]
        return result

    def _call_sync_load_function(self, name: str) -> str | tuple[Any, ...] | None:
        """Call the sync loader function."""
        # Call sync function directly
        result = self.load_func(name)
        # Ensure we're not returning an awaitable for sync calls
        if inspect.isawaitable(result):
            raise RuntimeError("Sync loader function returned an awaitable")
        # Type assertion: at this point result cannot be awaitable
        return t.cast(str | tuple[Any, ...] | None, result)

    def _process_load_result(
        self, result: str | tuple[Any, ...], name: str
    ) -> SourceType:
        """Process the result from the loader function.

        Args:
            result: Result from the loader function
            name: Template name

        Returns:
            SourceType tuple (source, filename, uptodate_func)
        """
        # Handle different return types from the load function
        if isinstance(result, tuple) and len(result) == 3:
            return self._process_tuple_result(result)
        elif isinstance(result, str):
            return self._process_string_result(result, name)
        else:
            # Unexpected return type
            raise TypeError(f"Unexpected source type: {type(result)}")

    def _process_tuple_result(self, result: tuple[Any, ...]) -> SourceType:
        """Process tuple result from loader function.

        Args:
            result: 3-element tuple (source, filename, uptodate_func)

        Returns:
            SourceType tuple
        """
        # load_func returned a full SourceType tuple
        source_val: str | bytes = result[0]
        filename_val: str | None = result[1]
        # Check if the third element is callable or None
        uptodate_candidate = result[2]
        uptodate_val: t.Callable[[], bool] | None = (
            t.cast(t.Callable[[], bool], uptodate_candidate)
            if callable(uptodate_candidate) or uptodate_candidate is None
            else None
        )
        # Ensure types match SourceType definition
        source_typed: str | bytes = source_val
        filename_typed: str | None = filename_val
        uptodate_typed: t.Callable[[], bool] | None = uptodate_val
        return source_typed, filename_typed, uptodate_typed

    def _process_string_result(self, source: str, name: str) -> SourceType:
        """Process string result from loader function.

        Args:
            source: Template source
            name: Template name

        Returns:
            SourceType tuple
        """

        # For function loader, we use the template name as filename
        # and create an uptodate function that re-checks the loader
        def uptodate() -> bool:
            try:
                if self.is_async_func:
                    # Can't call async function from sync context
                    # Always return False to force reload
                    return False
                else:
                    return self._check_sync_template_update(name, source)
            except Exception:
                return False

        uptodate_func: t.Callable[[], bool] | None = uptodate
        return source, name, uptodate_func

    def _check_sync_template_update(self, name: str, source: str) -> bool:
        """Check if a sync template has been updated.

        Args:
            name: Template name
            source: Current template source

        Returns:
            True if template hasn't changed, False otherwise
        """
        current_result = self.load_func(name)
        if current_result is None:
            return False
        if isinstance(current_result, tuple) and len(current_result) == 3:
            current_source = current_result[0]
        else:
            current_source = current_result
        return current_source == source

    @internalcode
    async def list_templates_async(self) -> list[str]:
        """List templates (not supported by function loader).

        Returns:
            Empty list (function loaders cannot enumerate templates)

        Raises:
            TypeError: Always raised as function loaders cannot list templates
        """
        raise TypeError("this loader cannot iterate over all templates")

    def update_function(self, load_func: LoaderFunction | AsyncLoaderFunction) -> None:
        """Update the loader function.

        Args:
            load_func: New loader function to use
        """
        import inspect

        self.load_func = load_func
        self.is_async_func = inspect.iscoroutinefunction(load_func)
