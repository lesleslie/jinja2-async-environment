"""Async template loaders for jinja2-async-environment.

This module provides async-compatible template loaders that maintain
100% backward compatibility with the original API while offering
improved performance and maintainability through modular design.
"""

# Import all loader classes from their respective modules

from .base import AsyncBaseLoader, AsyncLoaderProtocol, SourceType
from .choice import AsyncChoiceLoader
from .dict import AsyncDictLoader
from .filesystem import AsyncFileSystemLoader
from .function import AsyncFunctionLoader

# Import exception classes from package module
from .package import AsyncPackageLoader, LoaderNotFound, PackageSpecNotFound

# For backward compatibility, also import any existing exceptions and utilities
# from the original loaders module that we need to preserve
try:
    # Import from original module if it still exists during transition
    from ..loaders_old import (
        LoaderContext as _OldLoaderContext,
    )
    from ..loaders_old import (
        TestContext as _OldTestContext,
    )
    from ..loaders_old import (
        UnifiedCache as _OldUnifiedCache,
    )
    from ..loaders_old import (
        _clear_expired_cache as _old_clear_expired_cache,
    )
    from ..loaders_old import (
        _loader_context as _old_loader_context,
    )
    from ..loaders_old import (
        _unified_cache as _old_unified_cache,
    )
    from ..loaders_old import (
        clear_test_context as _old_clear_test_context,
    )
    from ..loaders_old import (
        set_test_context as _old_set_test_context,
    )

    # Assign to the expected names
    LoaderContext = _OldLoaderContext
    TestContext = _OldTestContext
    UnifiedCache = _OldUnifiedCache
    _clear_expired_cache = _old_clear_expired_cache
    _loader_context = _old_loader_context
    _unified_cache = _old_unified_cache
    clear_test_context = _old_clear_test_context
    set_test_context = _old_set_test_context
except ImportError:
    pass

# Public API - maintain exact same exports as original module
__all__ = [
    # Main loader classes
    "AsyncBaseLoader",
    "AsyncLoaderProtocol",
    "AsyncFileSystemLoader",
    "AsyncDictLoader",
    "AsyncFunctionLoader",
    "AsyncPackageLoader",
    "AsyncChoiceLoader",
    # Types
    "SourceType",
    # Backward compatibility (will be moved to testing module in later phases)
    "LoaderContext",
    "TestContext",
    "UnifiedCache",
    "set_test_context",
    "clear_test_context",
    "_loader_context",
    "_unified_cache",
    "_clear_expired_cache",
    # Exception classes
    "PackageSpecNotFound",
    "LoaderNotFound",
]

# Version information
__version__ = "2.0.0-refactored"
