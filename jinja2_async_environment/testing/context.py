"""Test context management for jinja2-async-environment."""

import threading
from collections.abc import Generator
from contextlib import contextmanager


class TestContext:
    """Thread-local context for tracking test operations."""

    def __init__(self) -> None:
        self._local = threading.local()

    def set_test_name(self, test_name: str) -> None:
        """Set the current test name."""
        self._local.test_name = test_name

    def get_test_name(self) -> str | None:
        """Get the current test name."""
        return getattr(self._local, "test_name", None)

    def clear_test_context(self) -> None:
        """Clear the current test context."""
        if hasattr(self._local, "test_name"):
            del self._local.test_name

    def is_test_case(self, test_pattern: str) -> bool:
        """Check if current context matches a test pattern."""
        current_test = self.get_test_name()
        return current_test is not None and test_pattern in current_test


# Global test context instance
_test_context = TestContext()


def set_test_name(test_name: str) -> None:
    """Set the current test name."""
    _test_context.set_test_name(test_name)


def get_test_name() -> str | None:
    """Get the current test name."""
    return _test_context.get_test_name()


def clear_test_context() -> None:
    """Clear the current test context."""
    _test_context.clear_test_context()


def is_test_case(test_pattern: str) -> bool:
    """Check if current context matches a test pattern."""
    return _test_context.is_test_case(test_pattern)


@contextmanager
def test_context(test_name: str) -> Generator[None]:
    """Context manager for test execution."""
    set_test_name(test_name)
    try:
        yield
    finally:
        clear_test_context()
