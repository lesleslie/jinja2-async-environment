"""Base classes and protocols for async template loaders."""

import typing as t
from abc import abstractmethod

from anyio import Path as AsyncPath
from jinja2.loaders import BaseLoader
from jinja2.utils import internalcode

if t.TYPE_CHECKING:
    from jinja2 import Template

    from ..environment import AsyncEnvironment

# Type alias for source data
SourceType = tuple[str | bytes, str | None, t.Callable[[], bool] | None]


class AsyncLoaderProtocol(t.Protocol):
    """Protocol defining the interface for async template loaders.

    This protocol ensures all async loaders implement the required methods
    for loading templates asynchronously while maintaining compatibility
    with Jinja2's loader interface.
    """

    async def get_source_async(
        self, environment: "AsyncEnvironment", name: str
    ) -> SourceType | None:
        """Get template source asynchronously.

        Args:
            environment: The async environment instance
            name: Template name to load

        Returns:
            Tuple of (source, filename, uptodate_func) or None if not found

        Raises:
            TemplateNotFound: If template cannot be found
        """
        ...

    async def list_templates_async(self) -> list[str]:
        """List all available templates asynchronously.

        Returns:
            List of template names

        Raises:
            TypeError: If listing is not supported by this loader
        """
        ...

    async def load_async(
        self,
        environment: "AsyncEnvironment",
        name: str,
        env_globals: dict[str, t.Any] | None = None,
    ) -> "Template":
        """Load template asynchronously.

        Args:
            environment: The async environment instance
            name: Template name to load
            env_globals: Global variables for the template

        Returns:
            Compiled Template object

        Raises:
            TemplateNotFound: If template cannot be found
        """
        ...


class AsyncBaseLoader(BaseLoader):
    """Base class for async template loaders with memory optimization.

    This class provides the foundation for all async loaders, implementing
    common functionality while using __slots__ for memory efficiency.

    Features:
    - Thread-safe lazy initialization
    - Memory-optimized with __slots__
    - Robust error handling and resource management
    - Compatible with Jinja2's loader interface
    - Support for async template operations

    Thread Safety:
    The loader implements thread-safe initialization using RLock to ensure
    that multiple concurrent calls to _ensure_initialized() are handled safely.
    """

    __slots__ = ("searchpath", "_initialized", "_init_lock")

    searchpath: list[AsyncPath]
    _initialized: bool
    _init_lock: t.Any | None

    def __init__(self, searchpath: AsyncPath | str | t.Sequence[AsyncPath | str]):
        """Initialize the async loader.

        Args:
            searchpath: Path or sequence of paths to search for templates

        Raises:
            TypeError: If searchpath is not a valid type
            ValueError: If searchpath is empty or contains invalid paths
        """
        # Validate and normalize searchpath
        searchpath_list: list[t.Any] = []
        if isinstance(searchpath, str) or hasattr(
            searchpath, "parts"
        ):  # AsyncPath check
            searchpath_list = [searchpath]
        else:
            # Try to treat as sequence
            try:
                searchpath_list = list(searchpath)  # type: ignore
                if not searchpath_list:
                    raise ValueError("searchpath cannot be empty")

                # Validate each path in the sequence
                for i, path in enumerate(searchpath_list):
                    if not (isinstance(path, str) or hasattr(path, "parts")):
                        raise TypeError(
                            f"searchpath item {i} must be a string or AsyncPath, got {type(path)}"
                        )
            except (TypeError, ValueError) as e:
                if isinstance(e, ValueError):
                    raise
                raise TypeError(
                    "searchpath must be a string, AsyncPath, or sequence of strings/AsyncPaths"
                ) from e

        # Convert to AsyncPath objects for consistency and validate
        self.searchpath: list[AsyncPath] = []
        for path in searchpath_list:
            if isinstance(path, str):
                if not path.strip():
                    raise ValueError("Empty string paths are not allowed")
                self.searchpath.append(AsyncPath(path))
            elif hasattr(path, "parts"):
                # Already an AsyncPath-like object, convert to ensure type safety
                self.searchpath.append(AsyncPath(str(path)))
            else:
                # Fallback: convert to string then AsyncPath
                self.searchpath.append(AsyncPath(str(path)))

        self._initialized = False
        self._init_lock = None  # Will be created on first use

    def _ensure_initialized(self) -> None:
        """Ensure the loader is properly initialized.

        This method provides thread-safe lazy initialization. Subclasses
        should override _perform_initialization() instead of this method.

        Thread Safety:
        Uses a reentrant lock (RLock) to ensure thread-safe initialization
        even when called from multiple threads concurrently.

        Raises:
            RuntimeError: If initialization fails
        """
        if not self._initialized:
            # Thread-safe initialization check
            import threading

            if not hasattr(self, "_init_lock") or self._init_lock is None:
                self._init_lock = threading.RLock()

            with self._init_lock:
                if not self._initialized:
                    try:
                        self._perform_initialization()
                        self._initialized = True
                    except Exception:
                        # Ensure we don't leave loader in partially initialized state
                        self._initialized = False
                        # Re-raise the original exception to maintain test compatibility
                        raise

    def _perform_initialization(self) -> None:
        """Perform the actual initialization work.

        This method should be overridden by subclasses that need
        custom initialization logic. It is called within a thread-safe
        context by _ensure_initialized().

        Subclasses should implement their initialization logic here
        rather than overriding _ensure_initialized() directly.

        Raises:
            Exception: Any initialization-specific exceptions
        """
        pass

    @abstractmethod
    async def get_source_async(
        self, environment: "AsyncEnvironment", name: str
    ) -> SourceType:
        """Get template source asynchronously.

        Must be implemented by subclasses.

        Args:
            environment: The async environment instance
            name: Template name to load

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If template cannot be found
        """
        raise NotImplementedError("Subclasses must implement get_source_async")

    async def list_templates_async(self) -> list[str]:
        """List all available templates asynchronously.

        Default implementation raises TypeError. Override in subclasses
        that support template listing.

        Returns:
            List of template names

        Raises:
            TypeError: If listing is not supported by this loader
        """
        raise TypeError("this loader cannot iterate over all templates")

    @internalcode
    async def load_async(
        self,
        environment: "AsyncEnvironment",
        name: str,
        env_globals: dict[str, t.Any] | None = None,
    ) -> "Template":
        """Load template asynchronously using get_source_async.

        This method orchestrates the complete template loading process:
        1. Get template source via get_source_async()
        2. Handle bytecode caching if available
        3. Compile template if not cached
        4. Create and return Template instance

        Args:
            environment: The async environment instance
            name: Template name to load
            env_globals: Global variables for the template (optional)

        Returns:
            Compiled Template object ready for rendering

        Raises:
            TemplateNotFound: If template cannot be found
            RuntimeError: If compilation or loading fails
        """
        if env_globals is None:
            env_globals = {}

        # Import TemplateNotFound here to avoid circular imports
        from jinja2.exceptions import TemplateNotFound

        # Validate inputs
        if not name or not name.strip():
            raise TemplateNotFound("Template name cannot be empty")

        # Get template source
        try:
            source, path, uptodate = await self.get_source_async(environment, name)
        except Exception as e:
            if isinstance(e, TemplateNotFound):
                raise
            from jinja2.exceptions import TemplateNotFound as TNF

            raise TNF(f"Failed to get template source: {e}") from e

        # Normalize source to string
        try:
            source_str = source.decode("utf-8") if isinstance(source, bytes) else source
        except UnicodeDecodeError as e:
            from jinja2.exceptions import TemplateNotFound as TNF

            raise TNF(f"Template {name} contains invalid UTF-8 encoding: {e}") from e

        # Handle bytecode cache if available
        bcc = environment.bytecode_cache
        if bcc is not None:
            try:
                bucket = bcc.get_bucket(environment, name, path)  # type: ignore

                # Create checksum for bytecode caching
                import hashlib

                hashlib.sha256(source_str.encode("utf-8")).hexdigest()

                # Try to get existing bytecode
                code = bucket.code

                if code is None:
                    # Compile template
                    code = environment.compile(source_str, name, path)
                    bucket.code = code
            except Exception:
                # Fallback to direct compilation if cache fails
                code = environment.compile(source_str, name, path)
        else:
            # No cache, compile directly
            code = environment.compile(source_str, name, path)

        # Create template instance
        template = environment.template_class.from_code(
            environment,
            code,
            env_globals,
            uptodate,
        )

        return template

    def _get_cache_manager(self, environment: "AsyncEnvironment") -> t.Any:
        """Get the cache manager from the environment.

        Args:
            environment: The async environment instance

        Returns:
            The cache manager instance
        """
        return getattr(environment, "cache_manager", None)

    @internalcode
    def _handle_template_not_found(self, name: str) -> None:
        """Helper method to raise TemplateNotFound with consistent messaging.

        Args:
            name: Template name that was not found

        Raises:
            TemplateNotFound: Always raised with appropriate message
        """
        from jinja2.exceptions import TemplateNotFound

        raise TemplateNotFound(name)
