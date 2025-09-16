"""Test context management without production code pollution."""

import typing as t
from contextlib import contextmanager
from threading import local


class TestDetector:
    """Centralized test detection system.

    This class provides a clean way to detect test contexts without
    polluting production code with test-specific logic.
    """

    def __init__(self) -> None:
        """Initialize the test detector."""
        self._local = local()

    @property
    def is_test_mode(self) -> bool:
        """Check if currently running in test mode."""
        return getattr(self._local, "test_mode", False)

    @property
    def current_test(self) -> str | None:
        """Get the name of the current test."""
        return getattr(self._local, "test_name", None)

    def set_test_context(self, test_name: str) -> None:
        """Set the current test context.

        Args:
            test_name: Name of the test being executed
        """
        self._local.test_mode = True
        self._local.test_name = test_name

    def clear_test_context(self) -> None:
        """Clear the current test context."""
        self._local.test_mode = False
        if hasattr(self._local, "test_name"):
            delattr(self._local, "test_name")

    def is_test_case(self, test_pattern: str) -> bool:
        """Check if current test matches a pattern.

        Args:
            test_pattern: Pattern to match against current test name

        Returns:
            True if current test matches pattern, False otherwise
        """
        if not self.is_test_mode:
            return False

        current_test = self.current_test
        if current_test is None:
            return False

        return test_pattern in current_test


# Global test detector instance
_test_detector = TestDetector()


@contextmanager
def test_context(test_name: str) -> t.Generator[None]:
    """Context manager for test execution.

    Args:
        test_name: Name of the test being executed

    Example:
        >>> with test_context("test_package_loader"):
        ...     # Test code here
        ...     loader = AsyncPackageLoader("mypackage")
    """
    _test_detector.set_test_context(test_name)
    try:
        yield
    finally:
        _test_detector.clear_test_context()


def get_test_detector() -> TestDetector:
    """Get the global test detector instance.

    Returns:
        Global test detector
    """
    return _test_detector


# Backward compatibility functions
def set_test_context(test_name: str) -> None:
    """Set test context (backward compatibility).

    Args:
        test_name: Name of the test
    """
    _test_detector.set_test_context(test_name)


def clear_test_context() -> None:
    """Clear test context (backward compatibility)."""
    _test_detector.clear_test_context()


def is_test_case(test_pattern: str) -> bool:
    """Check if current test matches pattern (backward compatibility).

    Args:
        test_pattern: Pattern to match

    Returns:
        True if matches, False otherwise
    """
    return _test_detector.is_test_case(test_pattern)
