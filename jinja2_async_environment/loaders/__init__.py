"""Async template loaders for jinja2-async-environment.

This module provides async-compatible template loaders that maintain
100% backward compatibility with the original API while offering
improved performance and maintainability through modular design.
"""

# Import all loader classes from their respective modules

# Import testing utilities for backward compatibility
from ..testing import fixtures as _testing_fixtures
from .base import AsyncBaseLoader, AsyncLoaderProtocol, SourceType
from .choice import AsyncChoiceLoader
from .dict import AsyncDictLoader
from .filesystem import AsyncFileSystemLoader
from .function import AsyncFunctionLoader
from .package import AsyncPackageLoader, LoaderNotFound, PackageSpecNotFound

# Expose testing utilities for backward compatibility
LoaderContext = _testing_fixtures.LoaderContext
TestContext = _testing_fixtures.TestContext
UnifiedCache = _testing_fixtures.UnifiedCache
_loader_context = _testing_fixtures._loader_context
_unified_cache = _testing_fixtures._unified_cache
_clear_expired_cache = _testing_fixtures._clear_expired_cache
set_test_context = _testing_fixtures.set_test_context
clear_test_context = _testing_fixtures.clear_test_context

# For backward compatibility, also import any existing exceptions and utilities
# from the original loaders module that we need to preserve
# (loaders_old.py has been removed for simplification)

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
    # Exception classes
    "PackageSpecNotFound",
    "LoaderNotFound",
    # Backward compatibility (testing utilities)
    "LoaderContext",
    "TestContext",
    "UnifiedCache",
    "set_test_context",
    "clear_test_context",
    "_loader_context",
    "_unified_cache",
    "_clear_expired_cache",
]

# Version information
__version__ = "2.0.0-refactored"
