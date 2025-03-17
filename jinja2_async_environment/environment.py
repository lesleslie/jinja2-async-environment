import typing as t
from contextlib import suppress
from weakref import ref

from jinja2 import Environment
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound, UndefinedError
from jinja2.runtime import Undefined
from jinja2.utils import internalcode

from .bccache import AsyncBytecodeCache
from .compiler import AsyncCodeGenerator, CodeGenerator


class AsyncEnvironment(Environment):
    code_generator_class: t.Type[CodeGenerator] = AsyncCodeGenerator
    loader: t.Any | None = None
    bytecode_cache: AsyncBytecodeCache | None = None
    enable_async = True

    @internalcode
    def get_template(
        self,
        name: str | Template,
        parent: str | Template | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        raise NotImplementedError("Use get_template_async instead")

    @internalcode
    async def get_template_async(
        self,
        name: str | Template,
        parent: str | Template | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        if isinstance(name, Template):
            return name
        if parent is not None:
            name = self.join_path(str(name), str(parent))
        return await self._load_template_async(name, globals)

    @internalcode
    def select_template(
        self,
        names: t.Iterable[str | Template],
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        raise NotImplementedError("Use select_template_async instead")

    @internalcode
    async def select_template_async(
        self,
        names: t.Iterable[str | Template],
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        if isinstance(names, Undefined):
            names._fail_with_undefined_error()
        if not names:
            raise TemplatesNotFound(
                message="Tried to select from an empty list of templates."
            )
        names_list = []
        for name in names:
            if isinstance(name, Template):
                return name
            if parent is not None:
                name = self.join_path(str(name), parent)
            with suppress(TemplateNotFound, UndefinedError):
                return await self._load_template_async(name, globals)
            names_list.append(str(name))
        raise TemplatesNotFound(names_list)

    @internalcode
    def get_or_select_template(
        self,
        template_name_or_list: str | Template | t.Sequence[str | Template],
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        raise NotImplementedError("Use get_or_select_template_async instead")

    @internalcode
    async def get_or_select_template_async(
        self,
        template_name_or_list: str | Template | t.Sequence[str | Template],
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        if isinstance(template_name_or_list, (str, Undefined)):
            return await self.get_template_async(template_name_or_list, parent, globals)
        elif isinstance(template_name_or_list, Template):
            return template_name_or_list
        return await self.select_template_async(template_name_or_list, parent, globals)

    @internalcode
    async def _load_template_async(
        self,
        name: str | Template | t.Iterable[str | Template],
        globals: t.MutableMapping[str, t.Any] | None,
    ) -> Template:
        if isinstance(name, Template):
            return name
        if isinstance(name, str):
            return await self._get_template_async(name, globals)
        names_list = []
        for template_name in name:
            if isinstance(template_name, Template):
                return template_name
            with suppress(TemplateNotFound):
                return await self._get_template_async(str(template_name), globals)
            names_list.append(str(template_name))
        raise TemplatesNotFound(names_list)

    async def _get_template_async(
        self, name: str, globals: t.MutableMapping[str, t.Any] | None
    ) -> Template:
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (ref(self.loader), name)
        if self.cache is not None:
            with suppress(TypeError):
                template = self.cache.get(cache_key)
                if template is not None:
                    is_up_to_date = template.is_up_to_date
                    if callable(getattr(is_up_to_date, "__await__", None)):
                        is_up_to_date = await is_up_to_date  # type: ignore
                    if not self.auto_reload or is_up_to_date:
                        if globals:
                            template.globals.update(globals)
                        return template
        template = await self.loader.load_async(self, name, self.make_globals(globals))
        if self.cache is not None:
            self.cache[cache_key] = template
        return template
