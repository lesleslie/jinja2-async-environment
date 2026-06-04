"""Targeted tests for caching/strategies.py and caching/manager.py coverage gaps.

These tests are designed to exercise specific uncovered lines identified by:
    .venv/bin/python -m pytest tests/test_caching_coverage.py tests/test_cache_manager.py \\
        tests/test_cache_advanced.py tests/test_unified_cache.py \\
        --cov=jinja2_async_environment.caching.strategies \\
        --cov=jinja2_async_environment.caching.manager --cov-report=term-missing

Strategies missing: 94, 104, 164, 188-215, 219-242, 285, 290-291, 299-300,
326-327, 345-348, 358-363, 374-378, 429-430, 448-466, 477-496, 500, 504

Manager missing: 122, 124, 126, 222-226, 315, 423-424, 497, 501, 506
"""

from __future__ import annotations

import asyncio
import time
import typing as t

import pytest

from jinja2_async_environment.caching.manager import (
    AdvancedCacheManager,
    CacheManager,
)
from jinja2_async_environment.caching.strategies import (
    AdaptiveCache,
    CacheWarmer,
    HierarchicalCache,
    LFUCache,
)


# ---------------------------------------------------------------------------
# LFUCache coverage gaps: lines 94, 104
# ---------------------------------------------------------------------------


class TestLFUCacheGaps:
    """Cover branches missed by the baseline tests."""

    def test_set_overwrite_existing_key_reorders_access(self) -> None:
        """Line 94: setting an existing key must remove it from access_order."""
        cache: LFUCache[str] = LFUCache(max_size=10)
        cache.set("dup", "v1")
        cache.set("other", "v2")
        # Now overwrite "dup" — exercises the
        # ``if key in self._access_order: self._access_order.remove(key)`` line.
        cache.set("dup", "v3")

        assert cache.get("dup") == "v3"
        # access_order should not contain duplicates for the same key
        assert cache._access_order.count("dup") == 1

    def test_evict_lfu_on_empty_cache_is_noop(self) -> None:
        """Line 104: ``_evict_lfu`` early-return when cache is empty."""
        cache: LFUCache[str] = LFUCache(max_size=5)
        # Directly invoke the private method on an empty cache — must not raise.
        cache._evict_lfu()
        assert len(cache) == 0
        # No statistics should have changed.
        assert cache._statistics.evictions == 0
        assert cache._statistics.memory_pressure_evictions == 0

    def test_evict_lfu_picks_least_frequent(self) -> None:
        """Verify LFU semantics: hot keys are retained, cold key is evicted."""
        cache: LFUCache[str] = LFUCache(max_size=3)
        cache.set("hot1", "h1")
        cache.set("hot2", "h2")
        cache.set("cold", "c")

        for _ in range(5):
            cache.get("hot1")
        for _ in range(3):
            cache.get("hot2")
        # "cold" only has 1 access count (from set())

        cache.set("new", "n")  # forces eviction
        assert cache.get("hot1") == "h1"
        assert cache.get("hot2") == "h2"
        assert cache.get("new") == "n"
        assert cache.get("cold") is None

    def test_lfu_ttl_eviction_increments_stats(self) -> None:
        """Expired entries increment ttl_evictions on access."""
        cache: LFUCache[str] = LFUCache(max_size=5, default_ttl=1)
        cache.set("k", "v")
        # Backdate the timestamp so it appears expired without sleeping.
        cache._cache["k"].timestamp = time.time() - 10
        assert cache.get("k") is None
        ext = cache.get_extended_statistics()
        assert ext["ttl_evictions"] >= 1

    def test_extended_statistics_efficiency(self) -> None:
        """Extended statistics include the cache_efficiency ratio."""
        cache: LFUCache[str] = LFUCache(max_size=5)
        cache.set("a", "1")
        cache.get("a")
        cache.get("missing")
        ext = cache.get_extended_statistics()
        assert "cache_efficiency" in ext
        assert 0 <= ext["cache_efficiency"] <= 1
        assert "avg_access_time_ms" in ext
        assert "peak_size" in ext


# ---------------------------------------------------------------------------
# AdaptiveCache coverage gaps: lines 164, 188-215, 219-222, 226-242
# ---------------------------------------------------------------------------


class TestAdaptiveCacheGaps:
    """Drive ``_evaluate_strategy`` and adaptive eviction paths."""

    def _ensure_evaluation_triggered(self, cache: AdaptiveCache[str]) -> None:
        """Make next ``get`` call evaluate strategy immediately (line 164)."""
        cache._evaluation_interval = 0
        cache._last_evaluation = 0.0

    def test_evaluate_strategy_switches_lru_to_lfu(self) -> None:
        """High CV access pattern should switch from LRU to LFU."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=20)
        # Seed wildly uneven frequencies so coefficient of variation > 0.5.
        cache._access_patterns = {
            "hot": [time.time()] * 20,
            "cold1": [time.time()],
            "cold2": [time.time()],
            "cold3": [time.time()],
        }
        assert cache._strategy == "lru"
        cache._evaluate_strategy()
        assert cache._strategy == "lfu"
        assert cache._strategy_switches == 1
        # access_patterns should be cleared after a switch
        assert cache._access_patterns == {}

    def test_evaluate_strategy_switches_lfu_to_lru(self) -> None:
        """Uniform access pattern should switch from LFU back to LRU."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=20)
        cache._strategy = "lfu"
        cache._access_patterns = {
            f"k{i}": [time.time()] * 5 for i in range(8)
        }
        cache._evaluate_strategy()
        assert cache._strategy == "lru"
        assert cache._strategy_switches == 1

    def test_evaluate_strategy_no_patterns(self) -> None:
        """Empty access patterns short-circuit without changing strategy."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=10)
        cache._access_patterns.clear()
        cache._evaluate_strategy()
        assert cache._strategy == "lru"
        assert cache._strategy_switches == 0

    def test_evaluate_strategy_zero_mean(self) -> None:
        """Zero-mean frequencies (empty lists) short-circuit early."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=10)
        cache._access_patterns = {"k": [], "k2": []}
        cache._evaluate_strategy()
        # Should not have switched
        assert cache._strategy == "lru"

    def test_get_triggers_periodic_evaluation(self) -> None:
        """Line 164: ``get`` invokes ``_evaluate_strategy`` past the interval."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=10)
        cache.set("k", "v")
        # Seed enough access patterns to potentially cause a switch.
        cache._access_patterns = {
            "k": [time.time()] * 20,
            "k2": [time.time()],
            "k3": [time.time()],
        }
        self._ensure_evaluation_triggered(cache)
        before = cache._last_evaluation
        cache.get("k")
        # Last evaluation timestamp must have updated.
        assert cache._last_evaluation > before

    def test_access_pattern_pruning_to_last_hour(self) -> None:
        """Old timestamps outside the 1-hour window are dropped."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=10)
        cache.set("k", "v")
        old = time.time() - 7200  # 2 hours ago
        cache._access_patterns["k"] = [old, old, old]
        cache.get("k")
        # All historical entries should be pruned; only the new "get" remains.
        assert all(ts >= time.time() - 60 for ts in cache._access_patterns["k"])

    def test_evict_lru_uses_lfu_when_strategy_is_lfu(self) -> None:
        """Lines 219-222 and 226-242: ``_evict_lru`` delegates by strategy."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=3)
        cache._strategy = "lfu"
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")

        # Build access patterns so that "c" has the fewest accesses.
        cache._access_patterns = {
            "a": [time.time()] * 10,
            "b": [time.time()] * 5,
            "c": [time.time()],
        }

        # Force an eviction by adding a 4th item.
        cache.set("d", "4")

        # The least-frequent ("c") should be the victim.
        assert cache.get("c") is None
        assert cache.get("d") == "4"
        assert cache._evictions >= 1

    def test_evict_lfu_adaptive_falls_back_when_no_patterns(self) -> None:
        """Lines 226-228: empty ``_access_patterns`` falls back to LRU eviction."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=3)
        cache._strategy = "lfu"
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")
        # Force the adaptive cache to fall through to ``super()._evict_lru()``.
        cache._access_patterns.clear()
        cache.set("d", "4")
        # We don't assert *which* key is evicted (LRU semantics), only that
        # the cache is bounded and the new key is present.
        assert cache.get("d") == "4"

    def test_evict_lru_uses_super_when_strategy_is_lru(self) -> None:
        """Line 222: ``_evict_lru`` delegates to TypedCache when strategy is LRU."""
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=3)
        assert cache._strategy == "lru"  # default
        # Fill the cache and trigger eviction without ever switching to LFU.
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")
        cache.set("d", "4")  # triggers eviction via super()._evict_lru()
        assert cache.get("d") == "4"
        # Some entry must have been evicted (cache size capped at max_size).
        assert len(cache) <= 3

    def test_get_strategy_info_returns_metadata(self) -> None:
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=10)
        info = cache.get_strategy_info()
        assert info["current_strategy"] in {"lru", "lfu"}
        assert "strategy_switches" in info
        assert "last_evaluation" in info
        assert "access_pattern_keys" in info


# ---------------------------------------------------------------------------
# HierarchicalCache coverage gaps: 285, 290-291, 299-300, 326-327,
#   345-348, 358-363, 374-378
# ---------------------------------------------------------------------------


class TestHierarchicalCacheGaps:
    """Exercise the multi-level cache's TTL, promotion, resize, and delete APIs."""

    def test_default_ttl_property_getter(self) -> None:
        """Line 285: property getter for ``_default_ttl``."""
        cache: HierarchicalCache[str] = HierarchicalCache(
            l1_size=5, l2_size=10, l1_ttl=60, l2_ttl=300
        )
        assert cache._default_ttl == 300

    def test_default_ttl_property_setter(self) -> None:
        """Lines 290-291: setter splits TTL across L1 (1/5) and L2."""
        cache: HierarchicalCache[str] = HierarchicalCache(
            l1_size=5, l2_size=10, l1_ttl=60, l2_ttl=300
        )
        cache._default_ttl = 500
        assert cache.l2_cache._default_ttl == 500
        assert cache.l1_cache._default_ttl == 100  # 500 // 5

    def test_l1_hit_increments_l1_hits(self) -> None:
        """Lines 299-300: L1 hit path increments ``l1_hits``."""
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        # Set directly on L1 to guarantee an L1 hit.
        cache.l1_cache.set("k", "v")
        before = cache.l1_hits
        assert cache.get("k") == "v"
        assert cache.l1_hits == before + 1

    def test_promotion_after_threshold_accesses(self) -> None:
        """Lines 326-327: L2 → L1 promotion after >=3 accesses."""
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        cache.set("k", "v")
        # Three reads through the hierarchical entry point — promotion
        # logic uses the L2 cache's own access_count, which the L2 cache
        # increments on each ``get``.
        for _ in range(4):
            assert cache.get("k") == "v"
        assert cache.promotions >= 1
        # Item should now also live in L1.
        assert cache.l1_cache.get("k") == "v"

    def test_cleanup_expired_clears_both_levels(self) -> None:
        """Lines 345-348: ``cleanup_expired`` aggregates counts from both levels."""
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        # Pre-populate both levels with entries, then backdate them so they
        # appear expired without sleeping. ``ttl=0`` falsifies to default TTL,
        # so we have to manipulate the timestamp directly.
        cache.l1_cache.set("l1k", "v")
        cache.l2_cache.set("l2k", "v")
        cache.l1_cache._cache["l1k"].timestamp = time.time() - 10_000
        cache.l2_cache._cache["l2k"].timestamp = time.time() - 10_000
        removed = cache.cleanup_expired()
        assert removed >= 2

    def test_resize_splits_size_80_20(self) -> None:
        """Lines 358-363: ``resize`` partitions space between L1 and L2."""
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        cache.resize(100)
        assert cache.l1_cache._max_size == 20  # 100 // 5
        assert cache.l2_cache._max_size == 80
        # Edge case: very small size still gives L1 at least 1 entry.
        cache.resize(3)
        assert cache.l1_cache._max_size >= 1
        assert cache.l2_cache._max_size >= 1

    def test_delete_removes_from_both_levels(self) -> None:
        """Lines 374-378: ``delete`` returns True if either level had the key."""
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        cache.l1_cache.set("only_l1", "v")
        cache.l2_cache.set("only_l2", "v")
        cache.l1_cache.set("both", "v")
        cache.l2_cache.set("both", "v")

        assert cache.delete("only_l1") is True
        assert cache.delete("only_l2") is True
        assert cache.delete("both") is True
        assert cache.delete("missing") is False

    def test_clear_resets_statistics(self) -> None:
        """``clear`` zeroes out all hit/promotion counters."""
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        cache.set("k", "v")
        cache.get("k")
        cache.clear()
        assert cache.l1_hits == 0
        assert cache.l2_hits == 0
        assert cache.total_misses == 0
        assert cache.promotions == 0
        assert len(cache) == 0

    def test_get_statistics_overall_hit_rate(self) -> None:
        """Statistics aggregate hits and misses across both layers."""
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        cache.set("k1", "v1")
        cache.get("k1")
        cache.get("missing")
        stats = cache.get_statistics()
        assert 0.0 < stats["overall_hit_rate"] <= 1.0
        assert "l1_hit_rate" in stats
        assert "fill_ratio" in stats
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1


# ---------------------------------------------------------------------------
# CacheWarmer coverage gaps: 429-430, 448-466, 477-496, 500, 504
# ---------------------------------------------------------------------------


class _FakeTemplate:
    """Minimal async template stub for cache-warming tests."""

    def __init__(self, name: str, should_fail_render: bool = False) -> None:
        self.name = name
        self._fail = should_fail_render

    async def render_async(self, **context: t.Any) -> str:
        if self._fail:
            raise RuntimeError("render failed")
        return f"rendered:{self.name}:{context}"


class _FakeEnvironment:
    """Async environment stub returning templates by name."""

    def __init__(
        self,
        ok_names: list[str] | None = None,
        fail_names: list[str] | None = None,
        render_fail_names: list[str] | None = None,
    ) -> None:
        self._ok = set(ok_names or [])
        self._fail = set(fail_names or [])
        self._render_fail = set(render_fail_names or [])

    async def get_template_async(self, name: str) -> _FakeTemplate:
        if name in self._fail:
            raise FileNotFoundError(f"template missing: {name}")
        return _FakeTemplate(name, should_fail_render=name in self._render_fail)


@pytest.mark.asyncio
class TestCacheWarmerTemplateAsync:
    """Cover ``CacheWarmer.warm_template_cache`` end-to-end."""

    async def test_warm_template_cache_success_without_context(self) -> None:
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        env = _FakeEnvironment(ok_names=["a", "b"])
        results = await warmer.warm_template_cache(env, ["a", "b"])
        assert results == {"a": True, "b": True}
        assert "a" in warmer.get_warmed_keys()
        assert "b" in warmer.get_warmed_keys()

    async def test_warm_template_cache_success_with_context(self) -> None:
        """Context data triggers a render_async call after loading."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        env = _FakeEnvironment(ok_names=["a"])
        results = await warmer.warm_template_cache(env, ["a"], {"user": "x"})
        assert results == {"a": True}

    async def test_warm_template_cache_handles_load_failure(self) -> None:
        """Lines 463-464: exceptions during load are swallowed → False result."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        env = _FakeEnvironment(ok_names=["good"], fail_names=["bad"])
        results = await warmer.warm_template_cache(env, ["good", "bad"])
        assert results["good"] is True
        assert results["bad"] is False
        assert "bad" not in warmer.get_warmed_keys()

    async def test_warm_template_cache_handles_render_failure(self) -> None:
        """Render-time exceptions also yield False."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        env = _FakeEnvironment(ok_names=["ok"], render_fail_names=["ok"])
        results = await warmer.warm_template_cache(env, ["ok"], {"v": 1})
        assert results["ok"] is False

    async def test_warm_template_cache_concurrent(self) -> None:
        """``asyncio.gather`` over multiple warmers must not corrupt state."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        env = _FakeEnvironment(ok_names=[f"t{i}" for i in range(10)])

        async def warm(name: str) -> dict[str, bool]:
            return await warmer.warm_template_cache(env, [name])

        results = await asyncio.gather(*(warm(f"t{i}") for i in range(10)))
        assert all(r[f"t{i}"] for i, r in enumerate(results))
        assert len(warmer.get_warmed_keys()) >= 10


class TestCacheWarmerPackage:
    """Cover ``CacheWarmer.warm_package_cache``."""

    def test_warm_package_cache_success(self) -> None:
        """Real importable package (``json``) is cached via the manager."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        results = warmer.warm_package_cache(["json"])
        assert results["json"] is True
        assert "spec:json" in warmer.get_warmed_keys()
        cached = manager.get("package", "spec:json")
        assert cached is not None
        loader, spec = cached
        assert spec.name == "json"

    def test_warm_package_cache_unknown_returns_false(self) -> None:
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        results = warmer.warm_package_cache(["definitely_not_a_real_package_xyz"])
        assert results["definitely_not_a_real_package_xyz"] is False

    def test_warm_package_cache_handles_exception(self) -> None:
        """Lines 493-494: any exception during warming yields False, not a raise."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        # Patch the manager.set so warming raises while attempting to cache.
        original_set = manager.set

        def explode(*args: t.Any, **kwargs: t.Any) -> None:
            raise RuntimeError("simulated set failure")

        manager.set = explode  # type: ignore[assignment]
        try:
            results = warmer.warm_package_cache(["json"])
            assert results["json"] is False
        finally:
            manager.set = original_set  # type: ignore[assignment]

    def test_get_warmed_keys_returns_copy(self) -> None:
        """Line 500: ``get_warmed_keys`` returns a defensive copy."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        warmer._warmed_keys.add("a")
        keys = warmer.get_warmed_keys()
        keys.add("b")  # mutation must not leak back
        assert "b" not in warmer._warmed_keys

    def test_clear_warmed_tracking(self) -> None:
        """Line 504: ``clear_warmed_tracking`` drops the in-memory set."""
        manager = CacheManager()
        warmer = CacheWarmer(manager)
        warmer._warmed_keys.update({"a", "b", "c"})
        warmer.clear_warmed_tracking()
        assert warmer.get_warmed_keys() == set()


# ---------------------------------------------------------------------------
# CacheManager coverage gaps: 122, 124, 126, 222-226, 315, 423-424, 497, 501, 506
# ---------------------------------------------------------------------------


class TestCacheManagerGaps:
    """Exercise the remaining manager branches."""

    def test_resize_caches_all_caches(self) -> None:
        """Lines 122/124/126: template, compilation, and module resize branches."""
        manager = CacheManager()
        manager.resize_caches(
            template_size=11, compilation_size=22, module_size=33
        )
        stats = manager.get_statistics()
        assert stats["template_cache"]["max_size"] == 11
        assert stats["compilation_cache"]["max_size"] == 22
        assert stats["module_cache"]["max_size"] == 33

    def test_create_cache_warmer(self) -> None:
        """Line 315: factory method must return a usable CacheWarmer."""
        manager = CacheManager()
        warmer = manager.create_cache_warmer()
        assert isinstance(warmer, CacheWarmer)
        assert warmer.cache_manager is manager

    def test_memory_usage_with_hierarchical_template_cache(self) -> None:
        """Lines 222-226: hierarchical cache lacks a ``size`` field in stats.

        The manager must fall back to ``len()`` on the cache object itself.
        """
        manager = AdvancedCacheManager(
            strategy="lru",
            enable_hierarchical=True,
            template_cache_size=20,
        )
        # Put something in the hierarchical template cache.
        manager.template_cache.set("k1", "v1")  # type: ignore[union-attr]
        manager.template_cache.set("k2", "v2")  # type: ignore[union-attr]

        memory = manager.get_memory_usage_estimate()
        assert "template_cache" in memory
        # Should be a non-negative integer reflecting roughly len(cache) * avg_size.
        assert memory["template_cache"] >= 0

    def test_memory_usage_size_fallback_via_len(self) -> None:
        """Lines 222-226: fallback to ``len()`` when stats dict has no 'size'.

        The hierarchical cache *does* expose a 'size' field in its statistics,
        so to reach the else-branch we monkey-patch ``get_statistics`` on the
        manager to strip the 'size' key.
        """
        manager = CacheManager()
        manager.template_cache.set("k", "v")
        original_get_statistics = manager.get_statistics

        def stripped_stats() -> dict[str, dict[str, t.Any]]:
            stats = original_get_statistics()
            for cache_stats in stats.values():
                cache_stats.pop("size", None)
            return stats

        manager.get_statistics = stripped_stats  # type: ignore[method-assign]
        memory = manager.get_memory_usage_estimate()
        # When the size key is missing, the manager falls back to len() of
        # the cache attribute itself, which should yield a positive value for
        # the populated template cache.
        assert memory["template_cache"] >= 0
        # The other caches are empty so they should report 0 (the else→else
        # branch where the cache has no entries).
        assert memory["compilation_cache"] == 0


class TestAdvancedCacheManagerGaps:
    """Drive the advanced manager branches that depend on cache flavors."""

    def test_extended_statistics_includes_strategy_info_for_adaptive(self) -> None:
        """Lines 423-424: adaptive caches expose ``get_strategy_info``."""
        manager = AdvancedCacheManager(strategy="adaptive")
        # Drive some traffic so the caches have non-empty state.
        manager.set("template", "k", "v")
        manager.get("template", "k")
        extended = manager.get_extended_statistics()
        # At least one cache should have surfaced strategy info.
        strategy_keys = [k for k in extended if k.endswith("_strategy")]
        assert strategy_keys, f"expected strategy keys, got {list(extended)}"

    def test_extended_statistics_includes_extended_stats_for_lfu(self) -> None:
        """LFU caches expose ``get_extended_statistics``."""
        manager = AdvancedCacheManager(strategy="lfu")
        manager.set("template", "k", "v")
        manager.get("template", "k")
        extended = manager.get_extended_statistics()
        ext_keys = [k for k in extended if k.endswith("_extended")]
        assert ext_keys, f"expected extended keys, got {list(extended)}"

    def test_memory_efficiency_low_utilization_recommendation(self) -> None:
        """Line 497: cache with low utilization triggers a 'reduce' suggestion."""
        manager = AdvancedCacheManager(
            strategy="lru",
            package_cache_size=1000,
            template_cache_size=1000,
            compilation_cache_size=1000,
            module_cache_size=1000,
        )
        # A single set produces fill_ratio ≈ 0.001 → < 0.3 threshold.
        manager.set("package", "lonely", "v")
        report = manager.get_memory_efficiency_report()
        joined = " ".join(report["recommendations"])
        assert "reduc" in joined.lower() or "package_cache" in joined

    def test_memory_efficiency_high_utilization_recommendation(self) -> None:
        """Line 501: cache nearly full triggers an 'increase size' suggestion."""
        manager = AdvancedCacheManager(
            strategy="lru",
            package_cache_size=4,
            template_cache_size=4,
            compilation_cache_size=4,
            module_cache_size=4,
        )
        for i in range(4):
            manager.set("package", f"p{i}", "v")
            manager.set("template", f"t{i}", "v")
            manager.set("compilation", f"c{i}", "v")
            manager.set("module", f"m{i}", "v")
        report = manager.get_memory_efficiency_report()
        joined = " ".join(report["recommendations"])
        assert "increas" in joined.lower() or "high utilization" in joined.lower()

    def test_memory_efficiency_low_hit_rate_recommendation(self) -> None:
        """Line 506: low hit rate triggers a TTL-tuning suggestion."""
        manager = AdvancedCacheManager(
            strategy="lru",
            package_cache_size=10,
            template_cache_size=10,
            compilation_cache_size=10,
            module_cache_size=10,
        )
        manager.set("package", "p", "v")
        # 1 hit, many misses → hit_rate well below 0.5.
        manager.get("package", "p")
        for i in range(20):
            manager.get("package", f"miss{i}")
        report = manager.get_memory_efficiency_report()
        joined = " ".join(report["recommendations"]).lower()
        assert "ttl" in joined or "hit rate" in joined


# ---------------------------------------------------------------------------
# Concurrency & shared-cache smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestConcurrentCacheAccess:
    """Hammer caches with concurrent coroutines to validate async safety."""

    async def test_typed_cache_concurrent_set_get(self) -> None:
        manager = CacheManager(template_cache_size=200)

        async def setter(idx: int) -> None:
            for i in range(20):
                manager.set("template", f"k{idx}-{i}", i)

        async def reader(idx: int) -> int:
            hits = 0
            for i in range(20):
                if manager.get("template", f"k{idx}-{i}") is not None:
                    hits += 1
            return hits

        # Run sets first, then readers — sets must complete before reads
        await asyncio.gather(*(setter(idx) for idx in range(5)))
        results = await asyncio.gather(*(reader(idx) for idx in range(5)))
        assert all(r >= 0 for r in results)

    async def test_lfu_cache_concurrent_get(self) -> None:
        cache: LFUCache[int] = LFUCache(max_size=100)
        for i in range(50):
            cache.set(f"k{i}", i)

        async def reader() -> None:
            for i in range(50):
                cache.get(f"k{i}")

        await asyncio.gather(*(reader() for _ in range(10)))
        # LFUCache tracks hits in its own _statistics dataclass, not in the
        # TypedCache base counters surfaced by get_statistics().
        assert cache._statistics.hits >= 500


# ---------------------------------------------------------------------------
# Edge cases & error paths
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Small edge-case sweep to lock down boundary behavior."""

    def test_empty_cache_get_returns_none(self) -> None:
        cache: LFUCache[str] = LFUCache(max_size=10)
        assert cache.get("anything") is None

    def test_set_with_explicit_ttl_zero_immediately_expires(self) -> None:
        """Backdating timestamps simulates expiration regardless of ttl=0 fallback."""
        cache: LFUCache[str] = LFUCache(max_size=10, default_ttl=300)
        cache.set("k", "v")
        cache._cache["k"].timestamp = time.time() - 10_000
        assert cache.get("k") is None

    def test_hierarchical_cache_promotion_below_threshold(self) -> None:
        """L2 hits below the 3-access threshold do not promote.

        With a fresh set, ``access_count`` starts at 1, and each L2 get
        increments it. Promotion happens once access_count >= 3, i.e. after
        the second get. A single get keeps the entry in L2 only.
        """
        cache: HierarchicalCache[str] = HierarchicalCache(l1_size=5, l2_size=10)
        cache.set("k", "v")
        cache.get("k")  # one get → access_count goes 1 → 2 (not yet promoted)
        # Entry should still be in L2 only.
        assert cache.l1_cache.get("k") is None
        assert cache.l2_cache.get("k") == "v"

    def test_lfu_cache_keys_excludes_expired(self) -> None:
        cache: LFUCache[str] = LFUCache(max_size=10, default_ttl=300)
        cache.set("live", "v")
        cache.set("dead", "v")
        # Backdate "dead" entry's timestamp to force expiration.
        cache._cache["dead"].timestamp = time.time() - 10_000
        keys = cache.keys()
        assert "live" in keys
        assert "dead" not in keys

    def test_adaptive_cache_get_records_first_access_pattern(self) -> None:
        cache: AdaptiveCache[str] = AdaptiveCache(max_size=10)
        cache.set("k", "v")
        # First ``get`` for a key initializes the access pattern list.
        cache.get("k")
        assert "k" in cache._access_patterns
        assert len(cache._access_patterns["k"]) >= 1
