"""Async compiler module with backward compatibility exports.

This module provides backward compatibility by re-exporting all classes
from the new modular compiler structure.
"""

# Import all classes from the new modular structure
from jinja2.compiler import CodeGenerator

from .compiler_modules.cache import CompilationCache
from .compiler_modules.codegen import AsyncCodeGenerator, _compilation_cache
from .compiler_modules.dependencies import DependencyResolver
from .compiler_modules.frame import AsyncFrame
from .compiler_modules.loops import LoopCodeGenerator
from .compiler_modules.patterns import CompiledPatterns

# Export all classes for backward compatibility
__all__ = [
    "CompiledPatterns",
    "CompilationCache",
    "DependencyResolver",
    "LoopCodeGenerator",
    "AsyncFrame",
    "AsyncCodeGenerator",
    "CodeGenerator",
    "_compilation_cache",
]
