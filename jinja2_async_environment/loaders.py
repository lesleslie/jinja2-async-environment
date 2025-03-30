import importlib.util
import typing as t
import zipimport
from contextlib import suppress
from importlib import import_module
from pathlib import Path

from anyio import Path as AsyncPath
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound
from jinja2.loaders import BaseLoader
from jinja2.utils import internalcode

from .environment import AsyncEnvironment


class PackageSpecNotFound(TemplateNotFound): ...


class LoaderNotFound(TemplateNotFound): ...


SourceType = tuple[
    str | bytes, str | None, t.Callable[[], bool | t.Awaitable[bool]] | None
]


class AsyncLoaderProtocol(t.Protocol):
    async def get_source_async(
        self, template: str | AsyncPath
    ) -> SourceType | None: ...

    async def list_templates_async(self) -> list[str]: ...

    async def load_async(
        self,
        environment: AsyncEnvironment,
        name: str,
        env_globals: dict[str, t.Any] | None = None,
    ) -> Template: ...


class AsyncBaseLoader(BaseLoader):
    has_source_access: bool = True
    searchpath: list[AsyncPath]

    def __init__(self, searchpath: AsyncPath | t.Sequence[AsyncPath]) -> None:
        if isinstance(searchpath, AsyncPath):
            self.searchpath = [searchpath]
        elif isinstance(searchpath, (list, tuple)):
            self.searchpath = list(searchpath)
        else:
            raise TypeError(
                "searchpath must be an AsyncPath or a sequence of AsyncPath objects"
            )

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        template_path: AsyncPath = (
            AsyncPath(template) if isinstance(template, str) else template
        )
        raise TemplateNotFound(template_path.name)

    async def list_templates_async(self) -> list[str]:
        raise TypeError("this loader cannot iterate over all templates")

    @internalcode
    async def load_async(
        self,
        environment: AsyncEnvironment,
        name: str,
        env_globals: dict[str, t.Any] | None = None,
    ) -> Template:
        if env_globals is None:
            env_globals = {}
        source, path, uptodate = await self.get_source_async(name)
        source_str = source.decode("utf-8") if isinstance(source, bytes) else source
        bcc = environment.bytecode_cache
        bucket = None
        if bcc:
            bucket = await bcc.get_bucket_async(environment, name, path, source_str)
            code = bucket.code
        else:
            code = None
        if not code:
            if path is None:
                code = environment.compile(source_str, name)
            else:
                code = environment.compile(source_str, name, path)
        if bcc and bucket is not None and (not bucket.code):
            bucket.code = code
            await bcc.set_bucket_async(bucket)
        return environment.template_class.from_code(
            environment,
            code,
            env_globals,
            t.cast(t.Optional[t.Callable[[], bool]], uptodate),
        )


class AsyncFileSystemLoader(AsyncBaseLoader):
    encoding: str
    followlinks: bool

    def __init__(
        self,
        searchpath: AsyncPath | t.Sequence[AsyncPath],
        encoding: str = "utf-8",
        followlinks: bool = False,
    ) -> None:
        super().__init__(searchpath)
        self.encoding = encoding
        self.followlinks = followlinks

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        template_path: AsyncPath = (
            AsyncPath(template) if isinstance(template, str) else template
        )
        path: AsyncPath | None = None
        for sp in self.searchpath:
            candidate = sp / template_path
            if await candidate.is_file():
                path = candidate
                break
        if path is None:
            raise TemplateNotFound(template_path.name)
        try:
            resp = await path.read_bytes()
        except FileNotFoundError:
            raise TemplateNotFound(path.name)
        mtime = (await path.stat()).st_mtime

        async def _uptodate() -> bool:
            try:
                return (await path.stat()).st_mtime == mtime
            except OSError:
                return False

        return (
            resp.decode(self.encoding),
            str(path),
            _uptodate,
        )

    async def list_templates_async(self) -> list[str]:
        results: set[str] = set()
        for sp in self.searchpath:
            results.update({str(p) async for p in sp.rglob("*.html")})
        return sorted(results)


class AsyncPackageLoader(AsyncBaseLoader):
    package_path: AsyncPath
    package_name: str
    encoding: str
    _loader: t.Any
    _archive: str | None
    _template_root: AsyncPath

    def __init__(
        self,
        package_name: str,
        searchpath: AsyncPath | t.Sequence[AsyncPath],
        package_path: AsyncPath = AsyncPath("templates"),
        encoding: str = "utf-8",
    ) -> None:
        super().__init__(searchpath)
        self.package_path = package_path
        self.package_name = package_name
        self.encoding = encoding
        import_module(package_name)
        spec = importlib.util.find_spec(package_name)
        if not spec:
            raise PackageSpecNotFound("An import spec was not found for the package")
        loader = spec.loader
        if not loader:
            raise LoaderNotFound("A loader was not found for the package")
        self._loader = loader
        self._archive = None
        template_root: AsyncPath | None = None
        if isinstance(loader, zipimport.zipimporter):
            self._archive = loader.archive
            pkg_locations = spec.submodule_search_locations or []
            if pkg_locations:
                pkgdir = next(iter(pkg_locations))
                template_root = AsyncPath(pkgdir) / package_path
        else:
            roots: list[Path] = []
            if spec.submodule_search_locations:
                roots.extend([Path(s) for s in spec.submodule_search_locations])
            elif spec.origin is not None:
                roots.append(Path(spec.origin))
            for root in roots:
                candidate = root / package_path
                if candidate.is_dir():
                    template_root = AsyncPath(root)
                    break
        if not template_root:
            raise ValueError(
                f"The {package_name!r} package was not installed in a way that PackageLoader understands"
            )
        self._template_root = template_root

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        template_path: AsyncPath = (
            AsyncPath(template) if isinstance(template, str) else template
        )
        path = self._template_root / template_path
        if self._archive:
            if not await path.is_file():
                raise TemplateNotFound(path.name)
            source_bytes = await path.read_bytes()
            mtime = (await path.stat()).st_mtime

            async def _uptodate() -> bool:
                return await path.is_file() and (await path.stat()).st_mtime == mtime

            return (source_bytes.decode(self.encoding), str(path), _uptodate)
        else:
            try:
                source_bytes = self._loader.get_data(str(path))
            except OSError as exc:
                raise TemplateNotFound(path.name) from exc
            uptodate: t.Any = None
            return (source_bytes.decode(self.encoding), str(path), uptodate)

    async def list_templates_async(self) -> list[str]:
        results: list[str] = []
        if self._archive is None:
            paths = self._template_root.rglob("*.html")
            results.extend([str(p) async for p in paths])
        else:
            if not hasattr(self._loader, "_files"):
                raise TypeError(
                    "This zip import does not have the required metadata to list templates"
                )
            prefix = self._template_root.name
            for name in self._loader._files.keys():
                if name.startswith(prefix) and await AsyncPath(name).is_file():
                    results.append(name)
        results.sort()
        return results


class AsyncDictLoader(AsyncBaseLoader):
    mapping: t.Mapping[str, str]

    def __init__(
        self,
        mapping: t.Mapping[str, str],
        searchpath: AsyncPath | t.Sequence[AsyncPath],
    ) -> None:
        super().__init__(searchpath)
        self.mapping = mapping

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        template_name: str = (
            template.name if isinstance(template, AsyncPath) else template
        )
        if template_name in self.mapping:
            source = self.mapping[template_name]
            return (source, None, lambda: source == self.mapping.get(template_name))
        raise TemplateNotFound(template_name)

    async def list_templates_async(self) -> list[str]:
        return sorted(list(self.mapping))


class AsyncFunctionLoader(AsyncBaseLoader):
    load_func: t.Callable[
        [str | AsyncPath], t.Awaitable[SourceType] | SourceType | None
    ]

    def __init__(
        self,
        load_func: t.Callable[
            [str | AsyncPath], t.Awaitable[SourceType] | SourceType | None
        ],
        searchpath: AsyncPath | t.Sequence[AsyncPath],
    ) -> None:
        super().__init__(searchpath)
        self.load_func = load_func

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        result = self.load_func(template)
        if result is None:
            template_name: str = (
                template.name if isinstance(template, AsyncPath) else template
            )
            raise TemplateNotFound(template_name)
        if isinstance(result, tuple):
            return result
        if hasattr(result, "__await__"):
            awaited_result = await result
            return awaited_result
        if isinstance(result, str):
            template_str = str(template)
            return (result, template_str, lambda: True)
        raise TypeError(f"Unexpected source type: {type(result)}")


class AsyncChoiceLoader(AsyncBaseLoader):
    loaders: list[AsyncBaseLoader]

    def __init__(
        self,
        loaders: list[AsyncBaseLoader],
        searchpath: AsyncPath | t.Sequence[AsyncPath],
    ) -> None:
        super().__init__(searchpath)
        self.loaders = loaders

    async def get_source_async(self, template: str | AsyncPath) -> SourceType:
        for loader in self.loaders:
            with suppress(TemplateNotFound):
                return await loader.get_source_async(template)
        template_name: str = (
            template.name if isinstance(template, AsyncPath) else template
        )
        raise TemplateNotFound(template_name)

    async def list_templates_async(self) -> list[str]:
        found: set[str] = set()
        for loader in self.loaders:
            found.update(await loader.list_templates_async())
        return sorted(found)
