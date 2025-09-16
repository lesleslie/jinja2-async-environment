"""Async compiler components for jinja2-async-environment.

This package contains the async-aware compiler components split from the
original monolithic compiler module for better maintainability.
"""

# Export main classes for backward compatibility
from .cache import CompilationCache
from .codegen import AsyncCodeGenerator
from .dependencies import DependencyResolver
from .frame import AsyncFrame
from .loops import LoopCodeGenerator
from .patterns import CompiledPatterns

__all__ = [
    "AsyncCodeGenerator",
    "CompiledPatterns",
    "CompilationCache",
    "DependencyResolver",
    "LoopCodeGenerator",
    "AsyncFrame",
]

# Global compilation cache instance for backward compatibility
_compilation_cache = CompilationCache()
