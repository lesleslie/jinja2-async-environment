"""Async package template loader implementation."""

import importlib.util
import typing as t
from importlib import import_module
from pathlib import Path

from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import internalcode

from .base import AsyncBaseLoader, SourceType

if t.TYPE_CHECKING:
    from ..environment import AsyncEnvironment


class PackageLoaderError(Exception):
    """Base class for all AsyncPackageLoader resolution failures.

    Catching this exception catches every package-loader-specific
    error raised by :class:`AsyncPackageLoader` and its helpers
    (import / spec lookup / loader lookup failures).

    The ``package_name`` attribute, when present, carries the package
    name that triggered the failure, allowing callers to log or
    surface it without parsing the message string.
    """

    def __init__(self, message: str, *, package_name: str | None = None) -> None:
        super().__init__(message)
        self.package_name = package_name


class PackageSpecNotFound(PackageLoaderError):
    """Raised when a package spec cannot be found."""


class LoaderNotFound(PackageLoaderError):
    """Raised when a package loader cannot be found."""


class AsyncPackageLoader(AsyncBaseLoader):
    """Async package template loader with memory optimization.

    This loader loads templates from Python packages, supporting both
    regular filesystem packages and zip-imported packages.
    """

    __slots__ = (
        "package_path",
        "package_name",
        "encoding",
        "followlinks",
        "_loader",
        "_spec",
        "_archive",
        "_template_root",
        "_init_lock",  # Added for thread safety
    )

    # Class-level annotations matching AsyncBaseLoader's style. They
    # give IDEs / mypy / pyright a real type to chase instead of
    # falling back to ``Any`` for every attribute. ``_template_root``
    # is technically ``AsyncPath | None`` only during the lazy-init
    # window; the ``template_root`` property below exposes a
    # non-Optional ``AsyncPath`` for read sites.
    package_path: AsyncPath
    package_name: str
    encoding: str
    followlinks: bool
    _loader: t.Any
    _spec: t.Any
    _archive: t.Any
    _template_root: AsyncPath | None
    _initialized: bool
    _init_lock: t.Any | None

    def __init__(
        self,
        package_name: str,
        package_path: AsyncPath | str = "templates",
        encoding: str = "utf-8",
        *,
        followlinks: bool = False,
    ) -> None:
        """Initialize the package loader.

        Args:
            package_name: Name of the Python package containing templates.
            package_path: Path within the package where templates are stored.
                Defaults to ``"templates"`` (matches :class:`jinja2.PackageLoader`).
            encoding: File encoding for template files.
            followlinks: If True, follow symbolic links within the package's
                template directory. Defaults to False so a symlink placed
                inside the templates dir cannot be used to escape the
                package root and read arbitrary files on disk.

                .. warning::

                    Setting ``followlinks=True`` disables the symlink-rejection
                    check. Only enable this for packages you trust — a
                    compromised dependency could ship
                    ``templates/config.html → /etc/secrets`` and an operator
                    who flipped this switch to support a legitimate
                    in-tree symlink would happily serve its content into
                    the template cache. Do not enable it for packages
                    installed from untrusted sources or that pull in
                    untrusted transitive dependencies.

        Note:
            :class:`AsyncBaseLoader.__init__` is intentionally not called.
            The package loader resolves templates relative to
            ``self._template_root`` and ``self.package_path``; it never
            uses ``self.searchpath``. Calling ``super().__init__`` here
            would only populate a dead ``self.searchpath`` slot.
        """
        self._initialized = False
        self._init_lock = None
        self.followlinks = followlinks
        self.package_path = (
            AsyncPath(package_path) if isinstance(package_path, str) else package_path
        )
        self.package_name = package_name
        self.encoding = encoding

        # Use lazy initialization to avoid import issues during testing.
        # ``_template_root`` is ``None`` only during the lazy-init
        # window — read sites should prefer the ``template_root``
        # property (which raises if accessed before init) to get a
        # non-Optional type.
        self._loader: t.Any = None
        self._spec: t.Any = None
        self._archive: t.Any = None
        self._template_root: AsyncPath | None = None

    @property
    def template_root(self) -> AsyncPath:
        """Resolved template root, guaranteed non-None after init.

        The internal ``_template_root`` slot is ``AsyncPath | None``
        because of lazy initialization, but every read site that
        runs after ``_ensure_initialized()`` succeeds can use this
        property to get a non-Optional ``AsyncPath``.

        Raises:
            RuntimeError: If accessed before ``_perform_initialization``
                has completed successfully (i.e. the loader is in a
                "not initialized" state). This replaces the
                ``if self._template_root is None: raise RuntimeError(...)``
                checks that used to live in
                ``_get_source_with_archive`` and
                ``_get_source_regular`` — the property raises the
                same error naturally on its own.
        """
        if self._template_root is None:
            raise RuntimeError(
                "AsyncPackageLoader.template_root accessed before "
                "_perform_initialization() completed successfully"
            )
        return self._template_root

    def _perform_initialization(self) -> None:
        """Perform the actual initialization work for the package loader.

        Raises:
            PackageSpecNotFound: If package cannot be found
            LoaderNotFound: If package loader cannot be found
            ValueError: If the package is not installed in a way that
                PackageLoader understands, or if no template directory
                can be found. Matches :class:`jinja2.PackageLoader`'s
                user-facing error for compatibility.
        """
        try:
            # Initialize package loader and spec
            self._loader, self._spec = self._initialize_loader(self.package_name)
            # _find_template_root raises the user-facing ValueError
            # directly when no valid root exists, so the caller no
            # longer needs a None check on the returned value.
            self._template_root = self._find_template_root(
                self._spec, self.package_path
            )
        except Exception as e:
            # Reset initialization state on failure so a re-attempt
            # (e.g. from the test suite) sees a clean loader.
            self._template_root = None
            self._loader = None
            self._spec = None
            raise e

    def _initialize_loader(self, package_name: str) -> tuple[t.Any, t.Any]:
        """Initialize the package loader and spec.

        Args:
            package_name: Name of the package to load

        Returns:
            Tuple of (loader, spec)

        Raises:
            PackageSpecNotFound: If package cannot be found
            LoaderNotFound: If package loader cannot be found
        """
        # Additional validation during initialization
        if not package_name.strip():
            raise PackageSpecNotFound(
                f"Invalid package name: {package_name!r}",
                package_name=package_name,
            )

        # Import the package
        try:
            import_module(package_name)
        except ImportError as e:
            raise PackageSpecNotFound(
                f"Package {package_name!r} not found or cannot be imported",
                package_name=package_name,
            ) from e

        # Find the package spec
        spec = importlib.util.find_spec(package_name)
        if not spec:
            raise PackageSpecNotFound(
                f"Import spec was not found for package {package_name!r}. "
                "The package may not be properly installed.",
                package_name=package_name,
            )

        loader = spec.loader
        if not loader:
            raise LoaderNotFound(
                f"No loader found for package {package_name!r}. "
                "The package may be malformed or corrupted.",
                package_name=package_name,
            )

        return loader, spec

    def _find_template_root(self, spec: t.Any, package_path: AsyncPath) -> AsyncPath:
        """Find the root directory for templates in the package.

        Dispatches to the archive-based or regular-filesystem helper
        depending on the loader type, and raises the user-facing
        ``ValueError`` itself when no valid root can be found.

        Args:
            spec: Package spec
            package_path: Path within package for templates

        Returns:
            The resolved template root (never None).

        Raises:
            ValueError: If the package is not installed in a way that
                PackageLoader understands (matches
                :class:`jinja2.PackageLoader`'s user-facing error for
                compatibility).
        """
        # Check if this is an archive-based loader
        if hasattr(self._loader, "archive"):
            result: AsyncPath | None = self._get_archive_template_root(spec)
        else:
            result = self._get_regular_template_root(spec, package_path)

        if result is None:
            # Match jinja2.PackageLoader's user-facing ValueError so
            # callers migrating from jinja2 see the same error type
            # and message.
            raise ValueError(
                f"The {self.package_name!r} package was not installed in a"
                f" way that PackageLoader understands."
            )
        return result

    def _get_archive_template_root(self, spec: t.Any) -> AsyncPath | None:
        """Get template root for archive-based packages.

        Private implementation detail of :meth:`_find_template_root`;
        kept as ``AsyncPath | None`` so the helper itself can stay
        simple. The caller raises the user-facing ``ValueError`` when
        this returns ``None``.

        Args:
            spec: Package spec

        Returns:
            Template root path or None
        """
        self._archive = getattr(self._loader, "archive", None)
        pkg_locations: t.Iterable[str] | None = spec.submodule_search_locations or []

        if pkg_locations:
            pkgdir = next(iter(pkg_locations))
            return AsyncPath(pkgdir)

        return None

    def _get_regular_template_root(
        self, spec: t.Any, package_path: AsyncPath
    ) -> AsyncPath | None:
        """Get template root for regular filesystem packages.

        Mirrors :class:`jinja2.PackageLoader.__init__`: returns the
        package root (containing ``package_path``) only when that
        templates subdirectory actually exists, otherwise ``None`` so
        :meth:`_find_template_root` raises the user-facing
        ``ValueError``.

        Args:
            spec: Package spec
            package_path: Path within package

        Returns:
            Template root path or None if no templates directory exists.
        """
        roots: list[Path] = []

        if spec.submodule_search_locations:
            roots.extend([Path(s) for s in spec.submodule_search_locations])
        elif spec.origin is not None:
            roots.append(Path(spec.origin).parent)

        for root in roots:
            candidate = root / package_path
            if candidate.is_dir():
                return AsyncPath(root)

        # No root has a templates directory — let the caller surface
        # a user-facing ValueError rather than silently using a wrong
        # root.
        return None

    def _is_safe_path(self, target: Path) -> bool:
        """Check that ``target`` lies within ``self._template_root``.

        Defends against two escape routes for an attacker-controlled
        template name:

        1. ``..`` containment: a name like ``../../etc/passwd`` must not
           resolve outside the package's templates directory.
        2. Symlink escape: a symlink placed inside the templates dir
           that points outside the root must be rejected unless
           ``followlinks`` is True.

        Mirrors :meth:`AsyncFileSystemLoader._is_safe_path`.

        Note:
            This method intentionally reads ``self._template_root``
            (the slot) directly rather than the ``template_root``
            property. The defensive ``None`` branch must return
            ``False`` (not raise): tests such as
            ``TestAsyncPackageLoaderIsSafePathUnit`` set the slot to
            ``None`` to exercise this branch, and a raise would
            convert a "not initialized" state into a misleading
            user-facing error.

        Args:
            target: The fully-joined path to validate (sync ``Path``).

        Returns:
            True if the path is safe to load, False otherwise.
        """
        if self._template_root is None:
            return False
        try:
            target_resolved = target.resolve()
            root_resolved = Path(str(self._template_root)).resolve()
            # Containment check: raises ValueError if target_resolved
            # is not under root_resolved.
            target_resolved.relative_to(root_resolved)
        except (ValueError, OSError):
            return False
        # When not following links, reject any symlinked path.
        if not self.followlinks and target.is_symlink():
            return False
        return True

    @internalcode
    async def get_source_async(
        self, environment: "AsyncEnvironment", name: str
    ) -> SourceType:
        """Get template source from package asynchronously with caching.

        Args:
            environment: The async environment instance
            name: Template name to load

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If template cannot be found in package
            RuntimeError: If loader is not properly initialized
        """
        # Validate input parameters
        if not name or not name.strip():
            raise TemplateNotFound("Template name cannot be empty")

        # Ensure proper initialization with error handling
        self._ensure_initialized()

        # Try to get from cache first
        cache_manager = self._get_cache_manager(environment)
        cache_key = f"{self.package_name}:{name}"

        if cache_manager:
            from contextlib import suppress

            with suppress(Exception):
                cached_source: SourceType | None = cache_manager.get(
                    "template", cache_key
                )
                if cached_source is not None:
                    return cached_source
            # Cache errors shouldn't prevent loading

        template_path = AsyncPath(name)

        # Load from source with proper error handling
        source_data: SourceType
        try:
            if self._archive:
                source_data = await self._get_source_with_archive(template_path)
            else:
                source_data = await self._get_source_regular(template_path)
        except TemplateNotFound:
            # Re-raise template not found as-is
            raise
        except Exception as e:
            # Wrap other exceptions with context. Only include the
            # template name in the user-facing message: an ``OSError``
            # or ``PermissionError`` interpolates the absolute
            # filesystem path into its ``str()``, which we must not
            # echo back to callers (or to HTTP 500 pages). The full
            # context is still available via the ``__cause__`` chain
            # for server-side tracebacks.
            raise TemplateNotFound(name) from e

        # Cache the result safely
        if cache_manager:
            from contextlib import suppress

            with suppress(Exception):
                cache_manager.set("template", cache_key, source_data)
            # Cache errors shouldn't prevent template loading

        result: SourceType = source_data
        return result

    async def _get_source_with_archive(self, template_path: AsyncPath) -> SourceType:
        """Get template source from archived package.

        Reads ``self.template_root`` (the property), which raises
        :class:`RuntimeError` if the loader has not been initialized
        yet. Callers are expected to invoke
        :meth:`AsyncBaseLoader._ensure_initialized` before reaching
        here.

        Args:
            template_path: Path to template within package

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If template cannot be found
            RuntimeError: If template root is not initialized
        """
        template_full_path = (
            self.template_root / str(self.package_path) / str(template_path)
        )

        # Defend against path traversal and symlink escape BEFORE any
        # I/O. Treat the same as "not found" — the loader's contract
        # is to raise TemplateNotFound for any failure to load.
        sync_full_path = Path(str(template_full_path))
        if not self._is_safe_path(sync_full_path):
            raise TemplateNotFound(str(template_path))

        try:
            if hasattr(template_full_path, "is_file"):
                if not await template_full_path.is_file():
                    raise TemplateNotFound(str(template_path))

            source_bytes = await template_full_path.read_bytes()

            # For archived packages, files don't change at runtime (the
            # archive is loaded once by importlib). Mirror jinja2.PackageLoader
            # by reporting the template as always current.
            def uptodate() -> bool:
                return True

            result: SourceType = (
                source_bytes.decode(self.encoding),
                str(template_full_path),
                uptodate,
            )
            return result
        except (OSError, FileNotFoundError) as exc:
            raise TemplateNotFound(str(template_path)) from exc

    async def _get_source_regular(self, template_path: AsyncPath) -> SourceType:
        """Get template source from regular (filesystem-installed) package.

        Mirrors :class:`jinja2.PackageLoader.get_source` for the
        non-archive branch: builds a full filesystem path
        ``template_root / package_path / template_path`` and reads
        the file directly. The previous implementation called
        ``self._loader.get_data(package_relative_path)`` which only
        works for zip-imported packages — for regular packages the
        loader's path is the ``__init__.py`` file, so
        ``get_data("templates/foo.html")`` raised ``FileNotFoundError``.

        Reads ``self.template_root`` (the property), which raises
        :class:`RuntimeError` if the loader has not been initialized
        yet. Callers are expected to invoke
        :meth:`AsyncBaseLoader._ensure_initialized` before reaching
        here.

        Args:
            template_path: Path to template within package

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            TemplateNotFound: If template cannot be found
            RuntimeError: If template root is not initialized
        """
        template_full_path = (
            self.template_root / str(self.package_path) / str(template_path)
        )

        # Defend against path traversal and symlink escape BEFORE any
        # I/O. Treat the same as "not found" — the loader's contract
        # is to raise TemplateNotFound for any failure to load.
        sync_full_path = Path(str(template_full_path))
        if not self._is_safe_path(sync_full_path):
            raise TemplateNotFound(str(template_path))

        try:
            if not await template_full_path.is_file():
                raise TemplateNotFound(str(template_path))
        except (OSError, FileNotFoundError) as exc:
            raise TemplateNotFound(str(template_path)) from exc

        # Capture mtime synchronously at load time so the uptodate() closure
        # can be a cheap, synchronous function (matches jinja2.PackageLoader).
        try:
            mtime = sync_full_path.stat().st_mtime
        except OSError:
            mtime = 0.0

        try:
            source_bytes = await template_full_path.read_bytes()
            source_text = source_bytes.decode(self.encoding)
        except (OSError, FileNotFoundError) as exc:
            raise TemplateNotFound(str(template_path)) from exc
        except UnicodeDecodeError as exc:
            raise TemplateNotFound(
                f"Template {template_path.name} contains invalid {self.encoding} encoding"
            ) from exc

        def uptodate() -> bool:
            try:
                return (
                    sync_full_path.is_file() and sync_full_path.stat().st_mtime == mtime
                )
            except OSError:
                return False

        result: SourceType = (
            source_text,
            str(template_full_path),
            uptodate,
        )
        return result

    @internalcode
    async def list_templates_async(self) -> list[str]:
        """List all templates in the package asynchronously.

        Returns:
            Sorted list of template names

        Raises:
            TypeError: If template listing is not supported
            RuntimeError: If loader is not properly initialized
        """
        # Ensure proper initialization with error handling
        self._ensure_initialized()

        try:
            if self._archive:
                return await self._list_templates_archive()
            else:
                return await self._list_templates_regular()
        except Exception as e:
            # Re-raise TypeError as-is to maintain compatibility with tests
            if isinstance(e, TypeError):
                raise
            # Provide better error context for other failures
            raise RuntimeError(
                f"Failed to list templates in package {self.package_name!r}: {e}"
            ) from e

    async def _list_templates_archive(self) -> list[str]:
        """List templates from archived package.

        Returns:
            List of template names
        """
        # For archived packages, try to get file list from the loader
        if not hasattr(self._loader, "_files"):
            # If no _files attribute, try alternative methods or raise appropriate error
            if hasattr(self._loader, "get_data"):
                # Can't enumerate files without _files metadata
                raise TypeError(
                    f"The {self.package_name!r} package does not have the required metadata "
                    "to list its contents"
                )
            return []

        templates = []
        package_path_str = str(self.package_path)

        for file_path in self._loader._files:
            if file_path.startswith(package_path_str):
                # Check if it's a template file
                if file_path.endswith((".html", ".htm", ".xml", ".txt")):
                    templates.append(file_path)

        return sorted(templates)

    async def _list_templates_regular(self) -> list[str]:
        """List templates from regular package.

        Reads ``self.template_root`` (the property) once, which
        raises :class:`RuntimeError` if the loader has not been
        initialized. The previous ``if self._template_root is None:
        return []`` branch is dead: by the time
        :meth:`list_templates_async` reaches this method,
        ``_ensure_initialized`` has set the slot to a real
        ``AsyncPath``.

        Returns:
            List of template names
        """
        try:
            template_dir = self.template_root / str(self.package_path)
            if not await template_dir.exists():
                return []

            templates = []
            async for item in template_dir.rglob("*"):
                if await item.is_file() and item.suffix in (
                    ".html",
                    ".htm",
                    ".xml",
                    ".txt",
                ):
                    # Get relative path from template directory
                    relative_path = item.relative_to(str(template_dir))
                    template_name = str(relative_path).replace("\\", "/")
                    templates.append(template_name)

            return sorted(templates)

        except (OSError, AttributeError):
            return []
