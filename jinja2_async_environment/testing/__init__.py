"""Testing infrastructure for jinja2-async-environment.

This module provides clean separation of test utilities from production code,
enabling better maintainability and eliminating test pollution in the main
codebase.
"""

from .context import TestDetector, test_context
from .fixtures import create_test_cache_manager, create_test_environment

__all__ = [
    "TestDetector",
    "test_context",
    "create_test_cache_manager",
    "create_test_environment",
]

__version__ = "2.0.0"
