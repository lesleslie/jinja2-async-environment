import typing as t
from contextlib import suppress
from weakref import ref

from jinja2 import Environment
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound, UndefinedError
from jinja2.runtime import Undefined
from jinja2.utils import internalcode
from .compiler import AsyncCodeGenerator


class AsyncEnvironment(Environment):
    code_generator_class: t.Any = AsyncCodeGenerator
    loader: t.Optional[t.Any] = None
    bytecode_cache: t.Optional[t.Any] = None

    @internalcode
    @t.override
    async def get_template(  # type: ignore
        self,
        name: str | Template,
        parent: t.Optional[str | Template] = None,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> t.Coroutine[t.Any, t.Any, t.Any]:
        if isinstance(name, Template):
            return name  # type: ignore
        if parent is not None:
            name = self.join_path(name, str(parent))
        return await self._load_template(name, globals)

    @internalcode
    @t.override
    async def select_template(  # type: ignore
        self,
        names: t.Iterable[str | Template],
        parent: t.Optional[str] = None,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> t.Coroutine[t.Any, t.Any, t.Any]:
        if isinstance(names, Undefined):
            names._fail_with_undefined_error()

        if not names:
            raise TemplatesNotFound(
                message="Tried to select from an empty list of templates."
            )

        for name in names:
            if isinstance(name, Template):
                return name  # type: ignore
            if parent is not None:
                name = self.join_path(name, parent)
            with suppress(TemplateNotFound, UndefinedError):
                return await self._load_template(name, globals)
        raise TemplatesNotFound(names)  # type: ignore

    @internalcode
    @t.override
    async def get_or_select_template(  # type: ignore
        self,
        template_name_or_list: str | Template | list[str | Template],
        parent: t.Optional[str] = None,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> t.Coroutine[t.Any, t.Any, t.Any] | Template:
        if isinstance(template_name_or_list, (str, Undefined)):
            return await self.get_template(template_name_or_list, parent, globals)
        elif isinstance(template_name_or_list, Template):
            return template_name_or_list
        return await self.select_template(template_name_or_list, parent, globals)

    @internalcode
    @t.override
    async def _load_template(  # type: ignore
        self, name: str, globals: t.Optional[t.MutableMapping[str, t.Any]]
    ) -> t.Coroutine[t.Any, t.Any, t.Any]:
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (ref(self.loader), name)
        if self.cache is not None:
            template = self.cache.get(cache_key)
            if template and (
                not self.auto_reload or await template.is_up_to_date  # type: ignore
            ):
                if globals:
                    template.globals.update(globals)
                return template  # type: ignore
        template = await self.loader.load(self, name, self.make_globals(globals))
        if self.cache is not None:
            self.cache[cache_key] = template
        return template
