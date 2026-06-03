"""Targeted coverage tests for AsyncFunctionLoader.

Covers the specific uncovered lines in
``jinja2_async_environment/loaders/function.py``:

- Line 128: ``while isinstance(result, t.Awaitable)`` loop body
- Line 139: ``RuntimeError`` when a sync loader returns an awaitable
- Line 207: ``return False`` in the async uptodate branch
- Lines 210-211: ``except Exception: return False`` in uptodate
- Line 228: ``_check_sync_template_update`` with ``None`` result
- Line 230: ``_check_sync_template_update`` with a non-tuple (string) result
- Line 245: ``list_templates_async`` always raises ``TypeError``
- Lines 253-256: ``update_function`` swaps both ``load_func`` and
  ``is_async_func``.
"""

import typing as t

import pytest
from anyio import Path as AsyncPath
from jinja2_async_environment.caching.manager import CacheManager
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncFunctionLoader


class TestFunctionLoaderCoverage:
    """Tests for previously-uncovered lines in function.py."""

    # ------------------------------------------------------------------
    # Line 128: the while-isinstance-Awaitable loop in
    # _call_async_load_function. We craft an async loader that returns
    # another coroutine so that awaiting the outer coroutine resolves to
    # an awaitable, forcing the while-loop body to fire.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_loader_returning_awaitable_triggers_while_loop(
        self,
    ) -> None:
        async def inner() -> str:
            return "<h1>loop body</h1>"

        async def load_func(name: str) -> t.Awaitable[str | None]:
            # ``inner()`` is a coroutine object — awaiting ``load_func``
            # yields another coroutine, exercising the while-loop path.
            return inner()

        loader = AsyncFunctionLoader(load_func, AsyncPath("/templates"))
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        env.enable_async = True

        source, filename, uptodate = await loader.get_source_async(
            env, "loop.html"
        )
        assert source == "<h1>loop body</h1>"
        assert filename == "loop.html"
        assert callable(uptodate)
        # Async loader's uptodate always returns False.
        assert uptodate() is False

    # ------------------------------------------------------------------
    # Lines 207, 210-211: async uptodate path + exception swallowing
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_uptodate_branch_and_exception_swallower(self) -> None:
        # 1) Async uptodate branch: returns False unconditionally when
        # the loader's load_func returned a string.
        async def async_string_loader(name: str) -> str | None:
            return "static"

        loader = AsyncFunctionLoader(
            async_string_loader, AsyncPath("/templates")
        )
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        env.enable_async = True

        _, _, uptodate = await loader.get_source_async(env, "x.html")
        assert uptodate() is False

        # 2) Exception path: a sync loader that returns a string on
        # the first call (so get_source_async succeeds) but raises on
        # subsequent calls — the uptodate() wrapper must swallow the
        # exception and return False (lines 210-211).
        class _BoomAfterFirst:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, name: str) -> str:
                self.calls += 1
                if self.calls == 1:
                    return "first-call-source"
                raise RuntimeError("uptodate exploded")

        boom_later = _BoomAfterFirst()
        loader2 = AsyncFunctionLoader(boom_later, AsyncPath("/templates"))
        env2 = AsyncEnvironment(loader=loader2, cache_manager=CacheManager())
        env2.enable_async = True

        _, _, uptodate2 = await loader2.get_source_async(env2, "x.html")
        # The second invocation of load_func raises, and uptodate
        # should swallow it.
        assert uptodate2() is False

    # ------------------------------------------------------------------
    # Lines 228, 230: _check_sync_template_update with None and with a
    # plain string (non-tuple) result.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_check_sync_template_update_paths(self) -> None:
        # Sync loader that returns a different string the first time
        # (else branch, line 232), ``None`` the second time (line 228),
        # and a 3-tuple the third time (line 230 tuple branch).
        class _Toggle:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(
                self, name: str
            ) -> str | tuple[str, None, t.Callable[[], bool]] | None:
                self.calls += 1
                if self.calls == 1:
                    return "different-source"  # else branch
                if self.calls == 2:
                    return None  # line 228
                # Line 230: tuple branch with a different source.
                return ("another-source", None, lambda: True)

        toggle = _Toggle()
        loader = AsyncFunctionLoader(toggle, AsyncPath("/templates"))
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        env.enable_async = True

        # Force the loader to register a string-returning load_func.
        _, _, uptodate = await loader.get_source_async(env, "x.html")
        # First call: loader returns a non-tuple string (else branch).
        assert uptodate() is False
        # Second call: loader returns None (line 228).
        assert uptodate() is False
        # Third call: loader returns a 3-tuple (line 230).
        assert uptodate() is False

    # ------------------------------------------------------------------
    # Line 139: sync loader that returns an awaitable must raise
    # RuntimeError.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_sync_loader_returning_awaitable_raises(self) -> None:
        async def async_inner(name: str) -> str:
            return "nope"

        def bad_sync_loader(name: str) -> t.Awaitable[str]:
            # Pretend to be sync but actually returns a coroutine.
            coro = async_inner(name)
            # Attach a close callback so the never-awaited warning
            # doesn't fire when the RuntimeError short-circuits.
            coro.close()
            return coro

        loader = AsyncFunctionLoader(bad_sync_loader, AsyncPath("/templates"))
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        env.enable_async = True

        with pytest.raises(RuntimeError, match="awaitable"):
            await loader.get_source_async(env, "x.html")

    # ------------------------------------------------------------------
    # Line 245: list_templates_async always raises TypeError.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_list_templates_async_always_raises(self) -> None:
        def load_func(name: str) -> str | None:
            return None

        loader = AsyncFunctionLoader(load_func, AsyncPath("/templates"))
        with pytest.raises(
            TypeError, match="this loader cannot iterate over all templates"
        ):
            await loader.list_templates_async()

    # ------------------------------------------------------------------
    # Lines 253-256: update_function swaps load_func and re-detects
    # is_async_func.
    # ------------------------------------------------------------------
    def test_update_function_swaps_sync_and_async(self) -> None:
        def sync_func(name: str) -> str | None:
            return "sync"

        async def async_func(name: str) -> str | None:
            return "async"

        # Start as sync.
        loader = AsyncFunctionLoader(sync_func, AsyncPath("/templates"))
        assert loader.is_async_func is False
        assert loader.load_func is sync_func

        # Swap in an async function — is_async_func must flip to True.
        loader.update_function(async_func)
        assert loader.load_func is async_func
        assert loader.is_async_func is True

        # Swap back to a sync function — is_async_func must flip back.
        loader.update_function(sync_func)
        assert loader.load_func is sync_func
        assert loader.is_async_func is False

    # ------------------------------------------------------------------
    # Bonus: full get_source_async round-trip with a freshly-updated
    # async function, to make sure update_function doesn't leave the
    # loader in a broken state.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_update_function_then_load(self) -> None:
        def sync_func(name: str) -> str | None:
            return None

        async def async_func(name: str) -> str | None:
            return "after-update"

        loader = AsyncFunctionLoader(sync_func, AsyncPath("/templates"))
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        env.enable_async = True

        loader.update_function(async_func)

        source, filename, uptodate = await loader.get_source_async(
            env, "x.html"
        )
        assert source == "after-update"
        assert filename == "x.html"
        # Async loader uptodate always returns False (line 207).
        assert uptodate() is False

    # ------------------------------------------------------------------
    # Line 82: dead code after _handle_template_not_found always raises.
    # We mock _handle_template_not_found to return normally so the
    # post-call RuntimeError line is executed.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_handle_template_not_found_passthrough_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def load_func(name: str) -> str | None:
            return None

        # Replace the helper so it no longer raises — the RuntimeError
        # fallback in get_source_async will fire.
        def fake_not_found(name: str) -> None:
            return None

        loader = AsyncFunctionLoader(load_func, AsyncPath("/templates"))
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        env.enable_async = True

        monkeypatch.setattr(
            loader, "_handle_template_not_found", fake_not_found
        )

        with pytest.raises(
            RuntimeError,
            match="Template not found handler should have raised",
        ):
            await loader.get_source_async(env, "missing.html")
