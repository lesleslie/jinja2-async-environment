import typing as t
from weakref import ref

from jinja2 import Environment
from jinja2.environment import Template
from jinja2.utils import internalcode
from .compiler import AsyncCodeGenerator


class AsyncEnvironment(Environment):
    code_generator_class: t.Any = AsyncCodeGenerator
    loader: t.Optional[t.Any] = None
    bytecode_cache: t.Optional[t.Any] = None

    @internalcode
    async def get_template(  # type: ignore
        self,
        name: str | Template,
        parent: t.Optional[str | Template] = None,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> t.Any:
        if isinstance(name, Template):
            return name
        if parent is not None:
            name = self.join_path(name, str(parent))
        return await self._load_template(name, globals)

    @internalcode
    async def _load_template(  # type: ignore
        self, name: str, globals: t.Optional[t.MutableMapping[str, t.Any]]
    ) -> t.Any:
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (ref(self.loader), name)
        if self.cache is not None:
            template = self.cache.get(cache_key)
            if template and (not self.auto_reload or template.is_up_to_date):
                if globals:
                    template.globals.update(globals)
                return template
        template = await self.loader.load(self, name, self.make_globals(globals))
        if self.cache is not None:
            self.cache[cache_key] = template
        return template
