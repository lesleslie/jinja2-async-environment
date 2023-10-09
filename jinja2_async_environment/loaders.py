import importlib.util
import typing as t
import zipimport
from collections import abc
from contextlib import suppress
from importlib import import_module

from aiopath import AsyncPath
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import internalcode
from .environment import AsyncEnvironment


class PackageSpecNotFound(TemplateNotFound):
    """Raised if a package spec not found."""


class LoaderNotFound(TemplateNotFound):
    """Raised if a loader is not found."""


class AsyncBaseLoader:
    has_source_access = True

    def __init__(self, searchpath: AsyncPath | t.Sequence[AsyncPath]) -> None:
        self.searchpath = searchpath
        if not isinstance(searchpath, abc.Iterable):
            self.searchpath = [searchpath]

    async def get_source(self, template: AsyncPath) -> t.Any:
        if not self.has_source_access:
            raise RuntimeError(
                f"{type(self).__name__} cannot provide access to the source"
            )
        raise TemplateNotFound(template.name)

    async def list_templates(self) -> list[str] | t.NoReturn:
        raise TypeError("this loader cannot iterate over all templates")

    @internalcode
    async def load(
        self,
        environment: "AsyncEnvironment",
        name: str,
        env_globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> "Template":
        if env_globals is None:
            env_globals = {}
        code: t.Any = None
        bucket: t.Any = None
        source, path, uptodate = await self.get_source(AsyncPath(name))
        bcc = environment.bytecode_cache
        if bcc:
            bucket = await bcc.get_bucket(environment, name, path, source)
            code = bucket.code
        if not code:
            code = environment.compile(source, name, path.name)  # type: ignore
        if bcc and not bucket.code:
            bucket.code = code
            await bcc.set_bucket(bucket)
        return environment.template_class.from_code(
            environment, code, env_globals, uptodate
        )


class FileSystemLoader(AsyncBaseLoader):
    def __init__(
        self,
        searchpath: AsyncPath | t.Sequence[AsyncPath],
        encoding: str = "utf-8",
        followlinks: bool = False,
    ) -> None:
        super().__init__(searchpath)
        self.encoding = encoding
        self.followlinks = followlinks

    async def get_source(self, template: AsyncPath) -> t.Any:
        # split_template_path(template)
        for searchpath in self.searchpath:  # type: ignore
            path = searchpath / template
            if await path.is_file():
                break
        else:
            raise TemplateNotFound(template.name)
        try:
            resp = await path.read_text()
        except FileNotFoundError:
            raise TemplateNotFound(path.name)
        mtime = (await path.stat()).st_mtime

        async def uptodate() -> bool:
            try:
                return (await path.stat()).st_mtime == mtime
            except OSError:
                return False

        return resp, path, uptodate

    async def list_templates(self) -> list[str]:
        found = set()
        for searchpath in self.searchpath:  # type: ignore
            found.update([path.name async for path in searchpath.rglob("*.html")])
        return sorted(found)


class PackageLoader(AsyncBaseLoader):
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
        # Make sure the package exists. This also makes namespace
        # packages work, otherwise get_loader returns None.
        import_module(package_name)
        spec = importlib.util.find_spec(package_name)
        if not spec:
            raise PackageSpecNotFound("An import spec was not found for the package")
        loader = spec.loader
        if not loader:
            raise LoaderNotFound("A loader was not found for the package")
        self._loader = loader
        self._archive = None
        template_root = None
        if isinstance(loader, zipimport.zipimporter):
            self._archive = loader.archive
            pkgdir = next(iter(spec.submodule_search_locations))  # type: ignore
            template_root = AsyncPath(pkgdir) / package_path
        else:
            roots = []
            # One element for regular packages, multiple for namespace
            # packages, or None for single module file.
            if spec.submodule_search_locations:
                roots.extend([AsyncPath(s) for s in spec.submodule_search_locations])
            # A single module file, use the parent directory instead.
            elif spec.origin is not None:
                roots.append(AsyncPath(spec.origin))
            for root in roots:
                path = root / package_path
                if path.is_dir():
                    template_root = root
                    break

        if not template_root:
            raise ValueError(
                f"The {package_name!r} package was not installed in a"
                " way that PackageLoader understands"
            )

        self._template_root = template_root

    async def get_source(self, template: AsyncPath) -> t.Any:
        path = self._template_root / template
        # up_to_date: t.Optional[t.Callable[[], bool]] | None
        if self._archive:
            if not await path.is_file():
                raise TemplateNotFound(path.name)
            source = await path.read_bytes()
            mtime = (await path.stat()).st_mtime

            async def up_to_date() -> bool:
                return await path.is_file() and (await path.stat()).st_mtime == mtime

        else:
            # Package is a zip file.
            try:
                source = self._loader.get_data(str(path))  # type: ignore
            except OSError as e:
                raise TemplateNotFound(path.name) from e
            up_to_date = None  # type: ignore
        return source.decode(self.encoding), path, up_to_date  # type: ignore

    async def list_templates(self) -> t.Any:
        results: list[AsyncPath] = []

        if self._archive is None:
            # Package is a directory.
            paths = self._template_root.rglob("*.html")
            results.extend([p async for p in paths])
        else:
            if not hasattr(self._loader, "_files"):
                raise TypeError(
                    "This zip import does not have the required"
                    " metadata to list templates"
                )
            # Package is a zip file.
            prefix = self._template_root.name
            for name in self._loader._files.keys():  # type: ignore
                # Find names under the templates directory that aren't directories.
                if name.startswith(prefix) and (await AsyncPath(name).is_file()):
                    results.append(name)
        results.sort()
        return results


class DictLoader(AsyncBaseLoader):
    def __init__(
        self,
        mapping: t.Mapping[str, str],
        searchpath: AsyncPath | t.Sequence[AsyncPath],
    ) -> None:
        super().__init__(searchpath)
        self.mapping = mapping

    async def get_source(self, template: AsyncPath) -> t.Any:
        if template.name in self.mapping:
            source = self.mapping[template.name]
            return source, None, lambda: source == self.mapping.get(template.name)
        raise TemplateNotFound(template.name)

    async def list_templates(self) -> list[str]:
        return sorted(self.mapping)


class FunctionLoader(AsyncBaseLoader):
    def __init__(
        self,
        load_func: t.Callable[[AsyncPath], t.Any],
        searchpath: AsyncPath | t.Sequence[AsyncPath],
    ) -> None:
        super().__init__(searchpath)
        self.load_func = load_func

    async def get_source(self, template: str | AsyncPath) -> t.Any:
        path = AsyncPath(template)
        source = self.load_func(path)
        if source is None:
            raise TemplateNotFound(path.name)
        if isinstance(source, str):
            return source, path, True
        return source


class ChoiceLoader(AsyncBaseLoader):
    loaders: list[AsyncBaseLoader] = []

    def __init__(
        self,
        loaders: list[AsyncBaseLoader],
        searchpath: AsyncPath | t.Sequence[AsyncPath],
    ) -> None:
        super().__init__(searchpath)
        self.loaders = loaders

    async def get_source(self, template: AsyncPath) -> t.Any:
        for loader in self.loaders:
            with suppress(TemplateNotFound):
                return await loader.get_source(template)
        raise TemplateNotFound(template.name)

    async def list_templates(self) -> t.Any:
        found = set()
        for loader in self.loaders:
            found.update(await loader.list_templates())
        return sorted(found)
