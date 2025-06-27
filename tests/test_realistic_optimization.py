"""Realistic performance test for async_yield_from optimization.

This test simulates real-world template rendering scenarios.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from pytest_benchmark.fixture import BenchmarkFixture
from jinja2_async_environment.environment import AsyncEnvironment


class TestRealisticOptimization:
    """Test async_yield_from optimization in realistic scenarios."""

    @pytest.mark.benchmark
    def test_benchmark_realistic_template_rendering(
        self, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark realistic template rendering scenario."""
        env = AsyncEnvironment()

        # Simulate template rendering with multiple generator calls
        def large_sync_generator() -> Generator[str]:
            for i in range(1000):  # Larger dataset
                yield f"<li>Item {i}: Content for item {i}</li>"

        async def realistic_template_rendering() -> list[str]:
            # Simulate multiple calls to _async_yield_from like in real templates
            results = []

            # Simulate template blocks, loops, etc.
            for _ in range(10):  # Multiple template sections
                section_content = [
                    item async for item in env._async_yield_from(large_sync_generator())
                ]
                results.extend(section_content)

            return results

        def run_realistic_test() -> list[str]:
            return asyncio.run(realistic_template_rendering())

        result = benchmark(run_realistic_test)
        assert len(result) == 10000  # 10 sections × 1000 items each

    @pytest.mark.benchmark
    def test_benchmark_many_small_generators(self, benchmark: BenchmarkFixture) -> None:
        """Test performance with many small generator calls."""
        env = AsyncEnvironment()

        def small_generator(start: int, count: int) -> Generator[str]:
            for i in range(start, start + count):
                yield f"Item {i}"

        async def many_small_calls() -> list[str]:
            results = []
            # Simulate many small template fragments
            for i in range(100):  # 100 different generators
                fragment = [
                    item
                    async for item in env._async_yield_from(small_generator(i * 10, 10))
                ]
                results.extend(fragment)
            return results

        def run_many_small_test() -> list[str]:
            return asyncio.run(many_small_calls())

        result = benchmark(run_many_small_test)
        assert len(result) == 1000  # 100 generators × 10 items each

    @pytest.mark.benchmark
    def test_benchmark_mixed_generator_types(self, benchmark: BenchmarkFixture) -> None:
        """Test with mixed async and sync generators."""
        env = AsyncEnvironment()

        def sync_generator(prefix: str, count: int) -> Generator[str]:
            for i in range(count):
                yield f"{prefix}-sync-{i}"

        async def async_generator(prefix: str, count: int) -> AsyncGenerator[str]:
            for i in range(count):
                yield f"{prefix}-async-{i}"

        async def mixed_generator_test() -> list[str]:
            results = []

            # Mix of sync and async generators
            for i in range(50):
                # Sync generator
                sync_items = [
                    item
                    async for item in env._async_yield_from(
                        sync_generator(f"sync{i}", 20)
                    )
                ]
                results.extend(sync_items)

                # Async generator
                async_items = [
                    item
                    async for item in env._async_yield_from(
                        async_generator(f"async{i}", 20)
                    )
                ]
                results.extend(async_items)

            return results

        def run_mixed_test() -> list[str]:
            return asyncio.run(mixed_generator_test())

        result = benchmark(run_mixed_test)
        assert len(result) == 2000  # 50 × (20 sync + 20 async)

    @pytest.mark.benchmark
    def test_benchmark_nested_generators(self, benchmark: BenchmarkFixture) -> None:
        """Test performance with nested generator calls."""
        env = AsyncEnvironment()

        def outer_generator() -> Generator[str]:
            for i in range(10):
                yield f"outer-{i}"

        def inner_generator(outer_item: str) -> Generator[str]:
            for j in range(10):
                yield f"{outer_item}-inner-{j}"

        async def nested_generator_test() -> list[str]:
            results = []

            async for outer_item in env._async_yield_from(outer_generator()):
                inner_results = [
                    inner_item
                    async for inner_item in env._async_yield_from(
                        inner_generator(outer_item)
                    )
                ]
                results.extend(inner_results)

            return results

        def run_nested_test() -> list[str]:
            return asyncio.run(nested_generator_test())

        result = benchmark(run_nested_test)
        assert len(result) == 100  # 10 outer × 10 inner

    def old_async_yield_from(self, generator_func: Any) -> AsyncGenerator[Any]:
        """Old implementation for comparison."""

        async def _old_implementation(generator_func: Any) -> AsyncGenerator[Any]:
            try:
                async for event in generator_func:
                    yield event
            except TypeError:
                for event in generator_func:
                    yield event

        return _old_implementation(generator_func)

    @pytest.mark.benchmark
    def test_benchmark_old_vs_new_realistic(self, benchmark: BenchmarkFixture) -> None:
        """Direct comparison of old vs new in realistic scenario."""

        def test_generator() -> Generator[str]:
            for i in range(100):
                yield f"Test item {i}"

        # Test the new implementation
        env = AsyncEnvironment()

        async def test_new_implementation() -> list[str]:
            results = []
            for _ in range(10):  # Multiple calls
                items = [item async for item in env._async_yield_from(test_generator())]
                results.extend(items)
            return results

        def run_new_test() -> list[str]:
            return asyncio.run(test_new_implementation())

        result = benchmark(run_new_test)
        assert len(result) == 1000
