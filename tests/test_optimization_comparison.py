"""Performance comparison benchmark for async_yield_from optimization.

This test demonstrates the before/after performance improvement.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from pytest_benchmark.fixture import BenchmarkFixture
from jinja2_async_environment.environment import AsyncEnvironment


class TestAsyncYieldFromOptimization:
    """Compare old vs new async_yield_from implementation."""

    def old_async_yield_from_implementation(
        self, generator_func: Any
    ) -> AsyncGenerator[Any]:
        """The old implementation using try/except (slow)."""

        async def _old_async_yield_from(generator_func: Any) -> AsyncGenerator[Any]:
            try:
                async for event in generator_func:
                    yield event
            except TypeError:
                for event in generator_func:
                    yield event

        return _old_async_yield_from(generator_func)

    @pytest.mark.benchmark
    def test_benchmark_old_async_yield_from(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark the old (slow) implementation."""
        AsyncEnvironment()

        def sync_generator():
            for i in range(10):
                yield f"Item {i}"

        async def test_old_implementation():
            return [
                item
                async for item in self.old_async_yield_from_implementation(
                    sync_generator()
                )
            ]

        def run_old_implementation():
            return asyncio.run(test_old_implementation())

        result = benchmark(run_old_implementation)
        assert len(result) == 10

    @pytest.mark.benchmark
    def test_benchmark_new_async_yield_from(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark the new (fast) implementation."""
        env = AsyncEnvironment()

        def sync_generator():
            for i in range(10):
                yield f"Item {i}"

        async def test_new_implementation():
            return [item async for item in env._async_yield_from(sync_generator())]

        def run_new_implementation():
            return asyncio.run(test_new_implementation())

        result = benchmark(run_new_implementation)
        assert len(result) == 10

    @pytest.mark.benchmark
    def test_benchmark_async_generator_performance(
        self, benchmark: BenchmarkFixture
    ) -> None:
        """Test performance with async generators (should be similar for both)."""
        env = AsyncEnvironment()

        async def async_generator():
            for i in range(10):
                yield f"Async Item {i}"

        async def test_async_generator():
            return [item async for item in env._async_yield_from(async_generator())]

        def run_async_generator_test():
            return asyncio.run(test_async_generator())

        result = benchmark(run_async_generator_test)
        assert len(result) == 10

    @pytest.mark.benchmark
    def test_benchmark_type_detection_overhead(
        self, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark just the type detection part."""

        def sync_generator():
            for i in range(10):
                yield f"Item {i}"

        generator = sync_generator()

        def test_hasattr_check():
            return hasattr(generator, "__aiter__")

        result = benchmark(test_hasattr_check)
        assert result is False  # Sync generators don't have __aiter__

    @pytest.mark.benchmark
    def test_benchmark_exception_overhead(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark the exception handling overhead."""

        def sync_generator():
            for i in range(10):
                yield f"Item {i}"

        generator = sync_generator()

        def test_exception_handling() -> bool:
            try:
                # This will fail for sync generators
                iter(generator).__next__  # Simulate the check
                return True
            except (TypeError, AttributeError):
                return False

        result = benchmark(test_exception_handling)
        assert result is True  # Sync generators do have __next__
