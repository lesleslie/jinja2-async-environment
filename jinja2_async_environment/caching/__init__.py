"""Caching infrastructure for jinja2-async-environment.

This module provides type-safe, high-performance caching solutions with
dependency injection support and proper memory management.
"""

import typing as t

# Import core caching classes
# Import the existing bytecode cache
from ..bccache import AsyncBytecodeCache
from .manager import AdvancedCacheManager, CacheManager, CompilationCache
from .strategies import AdaptiveCache, CacheWarmer, HierarchicalCache, LFUCache
from .typed import TypedCache
from .unified import UnifiedCache

# Re-export compilation cache from compiler
_compilation_cache: t.Any = None
try:
    from ..compiler import _compilation_cache
except ImportError:
    # Handle case where compiler hasn't been refactored yet
    from .manager import CompilationCache

    _compilation_cache = None  # type: ignore

__all__ = [
    "CacheManager",
    "AdvancedCacheManager",
    "TypedCache",
    "UnifiedCache",
    "LFUCache",
    "AdaptiveCache",
    "HierarchicalCache",
    "CacheWarmer",
    "AsyncBytecodeCache",
    "CompilationCache",
    "_compilation_cache",
]

__version__ = "2.0.0"
