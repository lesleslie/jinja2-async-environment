"""Async function template loader implementation."""

import typing as t

from anyio import Path as AsyncPath
from jinja2.utils import internalcode

from .base import AsyncBaseLoader, SourceType

if t.TYPE_CHECKING:
    from ..environment import AsyncEnvironment

# Type alias for loader functions
LoaderFunction = t.Callable[[str], str | None]
AsyncLoaderFunction = t.Callable[[str], t.Awaitable[str | None]]


class AsyncFunctionLoader(AsyncBaseLoader):
    """Async function-based template loader with memory optimization.

    This loader uses a callable function to load templates, allowing for
    custom template retrieval logic such as loading from databases,
    remote services, or other dynamic sources.
    """

    __slots__ = ("load_func", "is_async_func")

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
        result: str | None | t.Awaitable[str | None] = None
        if self.is_async_func:
            import inspect

            coro = self.load_func(name)
            if inspect.isawaitable(coro):
                result = await coro
            else:
                result = coro
        else:
            result = self.load_func(name)

        # Handle None result (this should raise TemplateNotFound)
        if result is None:
            self._handle_template_not_found(name)
            # This line should never be reached, but mypy needs it for type checking
            raise RuntimeError(
                "Template not found handler should have raised exception"
            )

        # At this point, result is guaranteed to be not None
        assert result is not None

        # Handle different return types from the load function
        if isinstance(result, tuple) and len(result) == 3:
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
        elif isinstance(result, str):
            # load_func returned just the source string
            source = result

            # For function loader, we use the template name as filename
            # and create an uptodate function that re-checks the loader
            def uptodate() -> bool:
                try:
                    if self.is_async_func:
                        # Can't call async function from sync context
                        # Always return False to force reload
                        return False
                    else:
                        current_result = self.load_func(name)
                        if current_result is None:
                            return False
                        if (
                            isinstance(current_result, tuple)
                            and len(current_result) == 3
                        ):
                            current_source = current_result[0]
                        else:
                            current_source = current_result
                        return current_source == source
                except Exception:
                    return False

            uptodate_func: t.Callable[[], bool] | None = uptodate
            return source, name, uptodate_func
        else:
            # Unexpected return type
            raise TypeError(f"Unexpected source type: {type(result)}")

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
