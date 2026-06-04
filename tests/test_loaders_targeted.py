"""Targeted coverage tests for the async loader modules.

Each test in this file targets specific uncovered lines identified in the
coverage report for:

- jinja2_async_environment/loaders/base.py
- jinja2_async_environment/loaders/choice.py
- jinja2_async_environment/loaders/dict.py
- jinja2_async_environment/loaders/filesystem.py
- jinja2_async_environment/loaders/function.py

The goal of this file is to push each of those modules to the coverage
targets called out in the task description:

| Module            | Target |
|-------------------|--------|
| filesystem.py     | 90%+   |
| dict.py           | 95%+   |
| base.py           | 90%+   |
| choice.py         | 100%   |
| function.py       | 100%   |
"""

from __future__ import annotations

import typing as t
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from anyio import Path as AsyncPath
from jinja2.bccache import Bucket
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncBaseLoader,
    AsyncChoiceLoader,
    AsyncDictLoader,
    AsyncFileSystemLoader,
    AsyncFunctionLoader,
    SourceType,
)
from jinja2_async_environment.loaders.filesystem import TemplatePathDataType


# ---------------------------------------------------------------------------
# filesystem.py
# ---------------------------------------------------------------------------


class TestAsyncFileSystemLoaderTargeted:
    """Targeted tests for AsyncFileSystemLoader uncovered lines."""

    def test_init_with_default_encoding_and_followlinks(
        self,
    ) -> None:
        """Constructor stores encoding/followlinks attrs (lines 49-52)."""
        loader = AsyncFileSystemLoader(
            "/tmp", encoding="utf-16", followlinks=True
        )
        assert loader.encoding == "utf-16"
        assert loader.followlinks is True
        assert loader._template_cache == {}

    def test_get_cache_key(self) -> None:
        """The cache key is namespaced with ``fs:`` (line 284)."""
        loader = AsyncFileSystemLoader("/tmp")
        assert loader._get_cache_key("hello.html") == "fs:hello.html"

    @pytest.mark.asyncio
    async def test_get_source_async_continues_after_oserror(
        self, tmp_path: Path
    ) -> None:
        """A path that raises OSError is skipped (lines 99-101)."""
        good = tmp_path / "good.html"
        good.write_text("ok")

        # Build a loader with two paths, the first will raise on stat.
        bad_path = AsyncPath("/__definitely_missing_for_test__")
        loader = AsyncFileSystemLoader([bad_path, AsyncPath(str(tmp_path))])
        env = AsyncEnvironment(loader=loader, enable_async=True)

        source, _filename, _uptodate = await loader.get_source_async(
            env, "good.html"
        )
        assert source == "ok"

    @pytest.mark.asyncio
    async def test_get_source_async_uptodate_returns_false_on_oserror(
        self, tmp_path: Path
    ) -> None:
        """uptodate() returns False when stat raises OSError (lines 94-95)."""
        target = tmp_path / "tpl.html"
        target.write_text("hello")

        loader = AsyncFileSystemLoader(str(tmp_path))
        env = AsyncEnvironment(loader=loader, enable_async=True)
        _, _filename, uptodate = await loader.get_source_async(env, "tpl.html")
        assert uptodate() is True

        # Delete the file so the next stat() raises FileNotFoundError
        # (an OSError subclass) — the uptodate closure should swallow
        # it and return False.
        target.unlink()
        assert uptodate() is False

    @pytest.mark.asyncio
    async def test_get_source_async_unreachable_code_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``_handle_template_not_found`` doesn't raise, line 106 fires."""
        loader = AsyncFileSystemLoader("/no/such/dir")
        env = AsyncEnvironment(loader=loader, enable_async=True)

        def fake_not_found(name: str) -> None:  # pragma: no cover - never runs
            return None

        monkeypatch.setattr(loader, "_handle_template_not_found", fake_not_found)
        with pytest.raises(RuntimeError, match="Unreachable code"):
            await loader.get_source_async(env, "missing.html")

    @pytest.mark.asyncio
    async def test_is_safe_path_rejects_symlink_when_not_following(
        self, tmp_path: Path
    ) -> None:
        """A file that is itself a symlink is unsafe when followlinks=False (line 124)."""
        real = tmp_path / "real.html"
        real.write_text("x")
        link = tmp_path / "link.html"
        link.symlink_to(real)

        loader = AsyncFileSystemLoader(str(tmp_path), followlinks=False)
        is_safe = await loader._is_safe_path(AsyncPath(link))
        assert is_safe is False

    @pytest.mark.asyncio
    async def test_is_safe_path_returns_false_when_path_outside_searchpath(
        self, tmp_path: Path
    ) -> None:
        """A resolved file outside the searchpath returns False (line 137).

        We construct a real file in ``tmp_path.parent`` and a symlink
        inside ``tmp_path`` pointing to it. With ``followlinks=True``,
        the symlink check passes, but the resolved file is outside the
        searchpath, so the final ``return False`` (line 137) fires.
        """
        loader = AsyncFileSystemLoader(str(tmp_path), followlinks=True)
        outside_target = (
            tmp_path.parent / f"__outside_link_target_{id(self)}.html"
        )
        try:
            outside_target.write_text("x")
            inside = tmp_path / "inside.html"
            inside.symlink_to(outside_target)

            result = await loader._is_safe_path(AsyncPath(inside))
            assert result is False
        finally:
            if outside_target.exists() or outside_target.is_symlink():
                outside_target.unlink()

    @pytest.mark.asyncio
    async def test_is_safe_path_returns_false_for_directory(
        self, tmp_path: Path
    ) -> None:
        """A directory, not a file, is unsafe (line 120)."""
        loader = AsyncFileSystemLoader(str(tmp_path))
        # tmp_path is a directory; is_file() returns False.
        result = await loader._is_safe_path(AsyncPath(tmp_path))
        assert result is False

    @pytest.mark.asyncio
    async def test_get_source_async_oserror_during_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An OSError on exists() falls through to the next search path
        (lines 99-101).
        """
        good = tmp_path / "good.html"
        good.write_text("ok")

        loader = AsyncFileSystemLoader(str(tmp_path))
        env = AsyncEnvironment(loader=loader, enable_async=True)

        # Patch AsyncPath.exists so the bad path raises OSError.
        original_exists = AsyncPath.exists

        async def selective_exists(self: t.Any) -> bool:
            # The bad path raises; everything else is normal.
            if str(self) == "/__bad_path__":
                raise OSError("simulated")
            return await original_exists(self)

        monkeypatch.setattr(AsyncPath, "exists", selective_exists)
        # Search the bad path first, then the good one.
        loader.searchpath.insert(0, AsyncPath("/__bad_path__"))
        source, _, _ = await loader.get_source_async(env, "good.html")
        assert source == "ok"

    @pytest.mark.asyncio
    async def test_list_templates_async_skips_missing_searchpath(
        self, tmp_path: Path
    ) -> None:
        """A searchpath that doesn't exist is skipped (line 169)."""
        loader = AsyncFileSystemLoader(
            [AsyncPath("/__nonexistent_searchpath__"), AsyncPath(str(tmp_path))]
        )
        (tmp_path / "a.html").write_text("a")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        templates = await loader.list_templates_async()
        assert templates == ["a.html"]

    @pytest.mark.asyncio
    async def test_is_safe_path_handles_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An OSError during the safety check returns False (lines 139-140)."""
        loader = AsyncFileSystemLoader(str(tmp_path))
        target = AsyncPath(tmp_path / "nope.html")

        # Force ``is_file`` to raise OSError. We patch via type so anyio's
        # AsyncPath.is_file instances get the override.
        original_is_file = AsyncPath.is_file

        async def boom(self: t.Any) -> bool:
            raise OSError("nope")

        monkeypatch.setattr(AsyncPath, "is_file", boom)
        try:
            result = await loader._is_safe_path(target)
            assert result is False
        finally:
            monkeypatch.setattr(AsyncPath, "is_file", original_is_file)

    @pytest.mark.asyncio
    async def test_get_source_async_skips_unsafe_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A search path entry that is unsafe is skipped (line 78)."""
        good = tmp_path / "ok.html"
        good.write_text("ok")

        loader = AsyncFileSystemLoader(str(tmp_path))
        env = AsyncEnvironment(loader=loader, enable_async=True)

        async def always_unsafe(_path: AsyncPath) -> bool:
            return False

        monkeypatch.setattr(loader, "_is_safe_path", always_unsafe)
        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(env, "ok.html")

    @pytest.mark.asyncio
    async def test_list_templates_async_filters_unsafe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unsafe templates are excluded from the listing (line 202)."""
        (tmp_path / "a.html").write_text("a")
        (tmp_path / "b.html").write_text("b")

        loader = AsyncFileSystemLoader(str(tmp_path))
        env = AsyncEnvironment(loader=loader, enable_async=True)

        async def unsafe_only(_path: AsyncPath) -> bool:
            return False

        monkeypatch.setattr(loader, "_is_safe_path", unsafe_only)
        templates = await loader.list_templates_async()
        assert templates == []

    @pytest.mark.asyncio
    async def test_list_templates_in_path_suppresses_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An OSError during rglob is suppressed (lines 168-185)."""
        loader = AsyncFileSystemLoader(str(tmp_path))

        async def fake_exists(self: t.Any) -> bool:
            return True

        async def boom(self: t.Any, *_args: t.Any) -> t.AsyncIterator[AsyncPath]:
            raise OSError("rglob failed")
            if False:  # pragma: no cover
                yield AsyncPath("/dev/null")

        monkeypatch.setattr(AsyncPath, "exists", fake_exists)
        monkeypatch.setattr(AsyncPath, "rglob", boom)
        templates = await loader.list_templates_async()
        assert templates == []

    @pytest.mark.asyncio
    async def test_walk_directory_methods(
        self, tmp_path: Path
    ) -> None:
        """Walk helpers yield the directory contents (lines 234-273)."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "f.html").write_text("x")
        loader = AsyncFileSystemLoader(str(tmp_path))

        # _should_recurse_into_directory: True for real dir, False for symlink
        assert await loader._should_recurse_into_directory(AsyncPath(sub)) is True
        link = tmp_path / "lnk"
        link.symlink_to(sub)
        assert await loader._should_recurse_into_directory(AsyncPath(link)) is False
        # but with followlinks=True the symlink directory is recursable
        loader2 = AsyncFileSystemLoader(str(tmp_path), followlinks=True)
        assert await loader2._should_recurse_into_directory(AsyncPath(link)) is True

        # _walk_directory yields items and recurses into subdirectories.
        walked: list[AsyncPath] = []
        async for item in loader._walk_directory(AsyncPath(tmp_path)):
            walked.append(item)
        names = sorted(p.name for p in walked)
        assert "sub" in names
        assert "f.html" in names

        # _walk_subdirectory delegates to _walk_directory.
        sub_walked: list[AsyncPath] = []
        async for item in loader._walk_subdirectory(AsyncPath(sub)):
            sub_walked.append(item)
        assert any(p.name == "f.html" for p in sub_walked)

    @pytest.mark.asyncio
    async def test_walk_directory_skips_missing(
        self, tmp_path: Path
    ) -> None:
        """Non-existent directory is skipped silently (lines 234-235)."""
        loader = AsyncFileSystemLoader(str(tmp_path))
        results: list[AsyncPath] = []
        async for item in loader._walk_directory(AsyncPath(tmp_path / "missing")):
            results.append(item)
        assert results == []

    @pytest.mark.asyncio
    async def test_walk_directory_handles_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Permission errors are caught (lines 246-248)."""
        loader = AsyncFileSystemLoader(str(tmp_path))

        async def boom(self: t.Any = None) -> t.AsyncIterator[AsyncPath]:
            raise PermissionError("denied")
            if False:  # pragma: no cover
                yield AsyncPath("/dev/null")

        monkeypatch.setattr(AsyncPath, "iterdir", boom)
        results: list[AsyncPath] = []
        async for item in loader._walk_directory(AsyncPath(tmp_path)):
            results.append(item)
        assert results == []

    @pytest.mark.asyncio
    async def test_process_template_path_returns_excluded(
        self, tmp_path: Path
    ) -> None:
        """_process_template_path returns (None, False) when unsafe (line 202)."""
        loader = AsyncFileSystemLoader(str(tmp_path))
        result = await loader._process_template_path(
            AsyncPath("/nope"), AsyncPath("/also_nope")
        )
        assert isinstance(result, TemplatePathDataType)
        assert result.template_name is None
        assert result.should_include is False


# ---------------------------------------------------------------------------
# dict.py
# ---------------------------------------------------------------------------


class TestAsyncDictLoaderTargeted:
    """Targeted tests for AsyncDictLoader uncovered lines."""

    def test_init_uses_virtual_path_when_searchpath_is_none(self) -> None:
        """No explicit searchpath -> the virtual default path is used (line 39)."""
        loader = AsyncDictLoader({"a.html": "A"})
        assert len(loader.searchpath) == 1
        assert str(loader.searchpath[0]) == "/virtual_dict_path"
        assert loader.mapping == {"a.html": "A"}

    def test_init_uses_explicit_searchpath(self) -> None:
        """Explicit searchpath overrides the virtual default."""
        loader = AsyncDictLoader({"a.html": "A"}, "/my/path")
        assert len(loader.searchpath) == 1
        assert str(loader.searchpath[0]) == "/my/path"

    def test_init_copies_mapping(self) -> None:
        """The mapping is copied so callers can't mutate loader state."""
        original = {"a": "A"}
        loader = AsyncDictLoader(original)
        original["b"] = "B"
        assert "b" not in loader.mapping

    def test_add_template(self) -> None:
        """add_template stores new templates (line 109)."""
        loader = AsyncDictLoader({})
        loader.add_template("x.html", "X")
        assert loader.mapping == {"x.html": "X"}

    def test_remove_template(self) -> None:
        """remove_template deletes templates (line 120)."""
        loader = AsyncDictLoader({"a": "A", "b": "B"})
        loader.remove_template("a")
        assert loader.mapping == {"b": "B"}
        with pytest.raises(KeyError):
            loader.remove_template("missing")

    def test_update_mapping(self) -> None:
        """update_mapping merges new keys (line 128)."""
        loader = AsyncDictLoader({"a": "A"})
        loader.update_mapping({"b": "B", "c": "C"})
        assert loader.mapping == {"a": "A", "b": "B", "c": "C"}

    def test_clear_templates(self) -> None:
        """clear_templates empties the mapping (line 132)."""
        loader = AsyncDictLoader({"a": "A", "b": "B"})
        loader.clear_templates()
        assert loader.mapping == {}

    def test_has_template(self) -> None:
        """has_template reports membership (line 143)."""
        loader = AsyncDictLoader({"a": "A"})
        assert loader.has_template("a") is True
        assert loader.has_template("missing") is False

    @pytest.mark.asyncio
    async def test_get_source_async_uses_cache_manager(self) -> None:
        """When a cache_manager is present, the result is cached (line 79/87)."""
        from jinja2_async_environment.caching.manager import CacheManager

        loader = AsyncDictLoader({"a.html": "source"}, "/p")
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        env.enable_async = True

        # First call populates the cache, second call should hit it.
        src1, _, _ = await loader.get_source_async(env, "a.html")
        assert src1 == "source"
        src2, _, _ = await loader.get_source_async(env, "a.html")
        assert src2 == "source"

    @pytest.mark.asyncio
    async def test_uptodate_returns_false_when_template_removed(self) -> None:
        """uptodate() returns False when the template is removed (line 79)."""
        loader = AsyncDictLoader({"a.html": "A"}, "/p")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        _, _, uptodate = await loader.get_source_async(env, "a.html")
        assert uptodate() is True
        del loader.mapping["a.html"]
        assert uptodate() is False


# ---------------------------------------------------------------------------
# base.py
# ---------------------------------------------------------------------------


class _CountingLoader(AsyncBaseLoader):
    """Minimal subclass used to exercise AsyncBaseLoader directly."""

    def __init__(self, searchpath: t.Any = "/x") -> None:
        super().__init__(searchpath)
        self._sources: dict[str, SourceType] = {}
        self._list_result: list[str] | None = None
        self._list_raises: Exception | None = None

    def register(
        self, name: str, source: str = "src", filename: str | None = None
    ) -> None:
        self._sources[name] = (source, filename, lambda: True)

    def set_list_result(self, items: list[str]) -> None:
        self._list_result = items

    def set_list_raises(self, exc: Exception) -> None:
        self._list_raises = exc

    async def get_source_async(
        self, environment: AsyncEnvironment, name: str
    ) -> SourceType:
        if name not in self._sources:
            raise TemplateNotFound(name)
        return self._sources[name]

    async def list_templates_async(self) -> list[str]:
        if self._list_raises is not None:
            raise self._list_raises
        assert self._list_result is not None
        return list(self._list_result)


class TestAsyncBaseLoaderTargeted:
    """Targeted tests for AsyncBaseLoader uncovered lines."""

    def test_init_invalid_searchpath_type_raises_typeerror(self) -> None:
        """A non-string, non-Path, non-sequence value raises TypeError (line 201)."""
        # ``int`` is iterable? No, list(123) raises TypeError, so the
        # generic message branch fires. The validation branch (line 201)
        # only fires when the top-level value is iterable but contains
        # invalid items.
        with pytest.raises(TypeError, match="searchpath must be"):
            AsyncBaseLoader(123)  # type: ignore[arg-type]

        # Iterable with invalid item: line 201 (validation) is reached.
        with pytest.raises(TypeError, match="searchpath must be"):
            AsyncBaseLoader([123])  # type: ignore[list-item]

    def test_init_empty_sequence_raises_valueerror(self) -> None:
        """An empty sequence raises ValueError (line 178)."""
        with pytest.raises(ValueError, match="searchpath cannot be empty"):
            AsyncBaseLoader([])

    def test_init_reraises_valueerror(self) -> None:
        """A ValueError from the empty-sequence check is re-raised (line 185)."""
        # The empty sequence raises ValueError which is re-raised
        # unmodified on line 185.
        with pytest.raises(ValueError, match="searchpath cannot be empty"):
            AsyncBaseLoader([])

    def test_init_empty_string_path_raises(self) -> None:
        """An empty string path raises ValueError (line 223)."""
        with pytest.raises(ValueError, match="Empty string paths are not allowed"):
            AsyncBaseLoader("")

    @pytest.mark.asyncio
    async def test_load_async_rejects_empty_name(self) -> None:
        """An empty template name raises TemplateNotFound (line 380)."""
        loader = _CountingLoader()
        env = AsyncEnvironment(loader=loader, enable_async=True)
        with pytest.raises(TemplateNotFound, match="cannot be empty"):
            await loader.load_async(env, "")
        with pytest.raises(TemplateNotFound, match="cannot be empty"):
            await loader.load_async(env, "   ")

    @pytest.mark.asyncio
    async def test_load_async_wraps_non_template_not_found(self) -> None:
        """A non-TemplateNotFound error is wrapped (lines 385-388)."""
        loader = _CountingLoader()

        async def boom(*_args: t.Any, **_kwargs: t.Any) -> t.Any:
            raise RuntimeError("nope")

        loader.get_source_async = boom  # type: ignore[method-assign]
        env = AsyncEnvironment(loader=loader, enable_async=True)
        with pytest.raises(TemplateNotFound, match="Failed to get template source"):
            await loader.load_async(env, "x.html")

    @pytest.mark.asyncio
    async def test_load_async_propagates_template_not_found(self) -> None:
        """A TemplateNotFound from get_source_async is re-raised (line 387)."""
        loader = _CountingLoader()

        async def raise_tnf(*_args: t.Any, **_kwargs: t.Any) -> t.Any:
            raise TemplateNotFound("original.html")

        loader.get_source_async = raise_tnf  # type: ignore[method-assign]
        env = AsyncEnvironment(loader=loader, enable_async=True)
        with pytest.raises(TemplateNotFound, match="original.html"):
            await loader.load_async(env, "x.html")

    @pytest.mark.asyncio
    async def test_load_async_normalizes_bytes_to_str(self) -> None:
        """Bytes source is decoded to str for compilation."""
        loader = _CountingLoader()
        loader.register("b.html", source=b"bytes content")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        # Should not raise; bytes are decoded to str.
        template = await loader.load_async(env, "b.html")
        assert template is not None

    @pytest.mark.asyncio
    async def test_load_async_handles_invalid_utf8(self) -> None:
        """Invalid UTF-8 bytes raise TemplateNotFound (lines 393-394)."""
        loader = _CountingLoader()
        loader.register("bad.html", source=b"\xff\xfe invalid utf-8")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        with pytest.raises(TemplateNotFound, match="invalid UTF-8 encoding"):
            await loader.load_async(env, "bad.html")

    @pytest.mark.asyncio
    async def test_load_async_with_bytecode_cache_miss(self) -> None:
        """First call compiles and stores in the bytecode cache (line 418)."""
        loader = _CountingLoader()
        loader.register("a.html", source="hello")

        bcc = MagicMock()
        bucket = MagicMock(spec=Bucket)
        bucket.code = None
        bcc.get_bucket = MagicMock(return_value=bucket)

        env = AsyncEnvironment(loader=loader, enable_async=True)
        env.bytecode_cache = bcc

        template = await loader.load_async(env, "a.html")
        assert template is not None
        # After load, bucket.code should have been assigned a real code object.
        assert bucket.code is not None
        bcc.get_bucket.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_async_with_bytecode_cache_hit(self) -> None:
        """Cached bucket.code is returned without recompiling."""
        loader = _CountingLoader()
        loader.register("a.html", source="hello")

        bcc = MagicMock()
        env = AsyncEnvironment(loader=loader, enable_async=True)
        # Pre-compute a real code object.
        cached_code = env.compile("hello", "a.html", None)
        bucket = MagicMock(spec=Bucket)
        bucket.code = cached_code
        bcc.get_bucket = MagicMock(return_value=bucket)

        env.bytecode_cache = bcc
        # Replace env.compile with a Mock to assert it isn't called.
        env.compile = MagicMock(return_value=cached_code)  # type: ignore[method-assign]

        template = await loader.load_async(env, "a.html")
        assert template is not None
        # bucket.code still equals the cached code; not overwritten.
        assert bucket.code is cached_code
        # env.compile was NOT called because the cache hit returned a code.
        env.compile.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_async_bytecode_cache_falls_back_on_error(self) -> None:
        """If the bytecode cache raises, fall back to direct compilation (461-463)."""
        loader = _CountingLoader()
        loader.register("a.html", source="hello")

        bcc = MagicMock()
        bcc.get_bucket = MagicMock(side_effect=RuntimeError("cache down"))

        env = AsyncEnvironment(loader=loader, enable_async=True)
        env.bytecode_cache = bcc

        # Replace env.compile with a Mock so we can assert it was called.
        cached_code = env.compile("hello", "a.html", None)
        env.compile = MagicMock(return_value=cached_code)  # type: ignore[method-assign]

        template = await loader.load_async(env, "a.html")
        assert template is not None
        # env.compile was called for the fallback.
        env.compile.assert_called()

    def test_handle_template_not_found_raises(self) -> None:
        """_handle_template_not_found raises TemplateNotFound (lines 488-490)."""
        loader = _CountingLoader()
        with pytest.raises(TemplateNotFound, match="x.html"):
            loader._handle_template_not_found("x.html")

    def test_get_cache_manager_returns_attribute(self) -> None:
        """_get_cache_manager returns the env's cache_manager (line 476)."""
        from jinja2_async_environment.caching.manager import CacheManager

        loader = _CountingLoader()
        env = AsyncEnvironment(loader=loader, cache_manager=CacheManager())
        assert loader._get_cache_manager(env) is not None

    def test_get_cache_manager_returns_none_when_absent(self) -> None:
        """Missing cache_manager returns None."""
        loader = _CountingLoader()
        env = MagicMock(spec=AsyncEnvironment)
        # Remove cache_manager attribute so getattr falls back to None.
        del env.cache_manager
        assert loader._get_cache_manager(env) is None

    def test_initialize_calls_perform(self) -> None:
        """_ensure_initialized only runs _perform_initialization once."""
        loader = _CountingLoader()
        assert loader._initialized is False
        loader._ensure_initialized()
        assert loader._initialized is True

    def test_initialize_propagates_exceptions(self) -> None:
        """Exceptions during init reset _initialized and re-raise."""

        class _BadInit(AsyncBaseLoader):
            def _perform_initialization(self) -> None:
                raise RuntimeError("init boom")

        loader = _BadInit("/x")
        with pytest.raises(RuntimeError, match="init boom"):
            loader._ensure_initialized()
        assert loader._initialized is False

    def test_initialize_idempotent_with_lock(self) -> None:
        """Re-entering initialization is safe."""
        import threading

        loader = _CountingLoader()
        loader._ensure_initialized()
        loader._ensure_initialized()
        assert loader._initialized is True
        # The init_lock is a threading.RLock after the first call.
        assert type(loader._init_lock) is type(threading.RLock())


# ---------------------------------------------------------------------------
# choice.py
# ---------------------------------------------------------------------------


class TestAsyncChoiceLoaderTargeted:
    """Targeted tests for AsyncChoiceLoader uncovered lines (target: 100%)."""

    def test_init_default_searchpath_is_empty(self) -> None:
        """Default searchpath uses the empty default (line 38).

        AsyncChoiceLoader doesn't override the empty-searchpath check,
        so we use a valid searchpath and check the loaders list is
        still empty.
        """
        loader = AsyncChoiceLoader([], searchpath="/tmp")
        assert str(loader.searchpath[0]) == "/tmp"
        assert loader.loaders == []

    def test_init_default_searchpath_raises_valueerror(self) -> None:
        """When searchpath is None, ``searchpath = []`` runs then super raises."""
        # This exercises the ``searchpath = []`` line on line 38.
        # The base class then raises ValueError because empty.
        with pytest.raises(ValueError, match="searchpath cannot be empty"):
            AsyncChoiceLoader([])

    def test_init_preserves_explicit_searchpath(self) -> None:
        """Explicit searchpath is preserved."""
        loader = AsyncChoiceLoader([], searchpath=["/tmp"])
        assert len(loader.searchpath) == 1
        assert str(loader.searchpath[0]) == "/tmp"

    @pytest.mark.asyncio
    async def test_get_source_async_uses_unreachable_code_branch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If _handle_template_not_found doesn't raise, line 76 fires."""
        loader = AsyncChoiceLoader([AsyncDictLoader({}, "/d")], searchpath="/x")
        env = AsyncEnvironment(loader=loader, enable_async=True)

        def fake_not_found(name: str) -> None:  # pragma: no cover - unreachable
            return None

        monkeypatch.setattr(loader, "_handle_template_not_found", fake_not_found)
        with pytest.raises(RuntimeError, match="Unreachable code"):
            await loader.get_source_async(env, "missing.html")

    def test_add_loader_appends(self) -> None:
        """add_loader appends to the loader list (line 108)."""
        loader = AsyncChoiceLoader([], searchpath="/tmp")
        loader.add_loader("a")
        loader.add_loader("b")
        assert loader.loaders == ["a", "b"]

    def test_insert_loader(self) -> None:
        """insert_loader inserts at the given index (line 117)."""
        loader = AsyncChoiceLoader([], searchpath="/tmp")
        loader.add_loader("a")
        loader.add_loader("c")
        loader.insert_loader(1, "b")
        assert loader.loaders == ["a", "b", "c"]

    def test_remove_loader(self) -> None:
        """remove_loader removes a loader (line 128)."""
        loader = AsyncChoiceLoader([], searchpath="/tmp")
        loader.add_loader("a")
        loader.add_loader("b")
        loader.remove_loader("a")
        assert loader.loaders == ["b"]
        with pytest.raises(ValueError):
            loader.remove_loader("missing")

    def test_clear_loaders(self) -> None:
        """clear_loaders empties the loader list (line 132)."""
        loader = AsyncChoiceLoader([], searchpath="/tmp")
        loader.add_loader("a")
        loader.clear_loaders()
        assert loader.loaders == []

    def test_get_loaders_returns_copy(self) -> None:
        """get_loaders returns a copy, not the internal list (line 148)."""
        loader = AsyncChoiceLoader(["a"], searchpath="/tmp")
        copy = loader.get_loaders()
        assert copy == ["a"]
        assert copy is not loader.loaders


# ---------------------------------------------------------------------------
# function.py
# ---------------------------------------------------------------------------


class TestAsyncFunctionLoaderTargeted:
    """Targeted tests for AsyncFunctionLoader uncovered lines (target: 100%)."""

    def test_init_default_searchpath_is_empty(self) -> None:
        """Default searchpath uses the empty default (line 48)."""
        loader = AsyncFunctionLoader(lambda _n: None, searchpath="/x")
        assert str(loader.searchpath[0]) == "/x"
        assert loader.load_func is not None
        assert loader.is_async_func is False

    def test_init_default_searchpath_raises_valueerror(self) -> None:
        """When searchpath is None, ``searchpath = []`` runs then super raises."""
        # Exercises the ``searchpath = []`` line on line 48; the
        # base class then raises ValueError because empty.
        with pytest.raises(ValueError, match="searchpath cannot be empty"):
            AsyncFunctionLoader(lambda n: None)

    @pytest.mark.asyncio
    async def test_async_function_call_path_when_not_awaitable(self) -> None:
        """Force ``_call_async_load_function`` to take the non-awaitable branch (line 118).

        We construct a regular (sync) loader, then flip ``is_async_func``
        to True so the async-call path is taken even though
        ``self.load_func(name)`` returns a plain string.
        """

        def sync_fn(name: str) -> str:
            return "plain"

        loader = AsyncFunctionLoader(sync_fn, searchpath="/x")
        # Override the auto-detected flag.
        loader.is_async_func = True
        env = AsyncEnvironment(loader=loader, enable_async=True)
        source, filename, _ = await loader.get_source_async(env, "x.html")
        assert source == "plain"
        assert filename == "x.html"

    def test_init_with_async_function_detects_async(self) -> None:
        """Async functions are detected via inspect.iscoroutinefunction (line 55)."""

        async def async_loader(name: str) -> str | None:
            return None

        loader = AsyncFunctionLoader(async_loader, searchpath="/x")
        assert loader.is_async_func is True

    @pytest.mark.asyncio
    async def test_async_loader_returning_non_awaitable(self) -> None:
        """Async function that returns a string (the else branch line 118)."""

        async def load_func(name: str) -> str:
            return "direct-string"

        loader = AsyncFunctionLoader(load_func, searchpath="/x")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        source, filename, uptodate = await loader.get_source_async(env, "x.html")
        assert source == "direct-string"
        assert filename == "x.html"

    @pytest.mark.asyncio
    async def test_async_loader_with_tuple_result(self) -> None:
        """Async loaders can return 3-tuples (lines 174-187)."""

        async def load_func(name: str) -> tuple[str, str, t.Callable[[], bool]] | None:
            if name == "ok":
                return ("source", "filename.html", lambda: True)
            return None

        loader = AsyncFunctionLoader(load_func, searchpath="/x")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        source, filename, uptodate = await loader.get_source_async(env, "ok")
        assert source == "source"
        assert filename == "filename.html"
        assert callable(uptodate)
        assert uptodate() is True

    @pytest.mark.asyncio
    async def test_async_loader_with_tuple_none_uptodate(self) -> None:
        """A tuple with ``None`` uptodate is accepted (line 181)."""

        async def load_func(name: str) -> tuple[str, None, None] | None:
            if name == "ok":
                return ("source", None, None)
            return None

        loader = AsyncFunctionLoader(load_func, searchpath="/x")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        source, filename, uptodate = await loader.get_source_async(env, "ok")
        assert source == "source"
        assert filename is None
        assert uptodate is None

    @pytest.mark.asyncio
    async def test_sync_loader_with_tuple_result(self) -> None:
        """Sync loaders can also return 3-tuples."""

        def load_func(name: str) -> tuple[str, None, t.Callable[[], bool]] | None:
            if name == "ok":
                return ("source", None, lambda: True)
            return None

        loader = AsyncFunctionLoader(load_func, searchpath="/x")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        source, filename, uptodate = await loader.get_source_async(env, "ok")
        assert source == "source"
        assert filename is None
        assert uptodate() is True

    @pytest.mark.asyncio
    async def test_sync_loader_string_uptodate_checks_for_changes(self) -> None:
        """Sync string loaders use _check_sync_template_update (lines 202-214)."""
        sources = {"x.html": "v1"}

        def load_func(name: str) -> str | None:
            return sources.get(name)

        loader = AsyncFunctionLoader(load_func, searchpath="/x")
        env = AsyncEnvironment(loader=loader, enable_async=True)
        _, _, uptodate = await loader.get_source_async(env, "x.html")
        assert uptodate() is True
        # Modify the source; uptodate should now return False.
        sources["x.html"] = "v2"
        assert uptodate() is False

    @pytest.mark.asyncio
    async def test_update_function_after_construction(self) -> None:
        """update_function replaces the function and re-detects async (line 256)."""

        def sync_fn(name: str) -> str | None:
            return "sync"

        async def async_fn(name: str) -> str | None:
            return "async"

        loader = AsyncFunctionLoader(sync_fn, searchpath="/x")
        assert loader.is_async_func is False
        loader.update_function(async_fn)
        assert loader.load_func is async_fn
        assert loader.is_async_func is True
        loader.update_function(sync_fn)
        assert loader.is_async_func is False

    @pytest.mark.asyncio
    async def test_list_templates_async_raises(self) -> None:
        """Function loaders cannot list templates (line 245)."""
        loader = AsyncFunctionLoader(lambda n: None, searchpath="/x")
        with pytest.raises(
            TypeError, match="this loader cannot iterate over all templates"
        ):
            await loader.list_templates_async()
