import typing as t
from weakref import ref

from jinja2 import Environment
from jinja2.environment import Template
from jinja2.utils import internalcode
from .compiler import AsyncCodeGenerator


class AsyncEnvironment(Environment):
    code_generator_class = AsyncCodeGenerator
    loader: t.Optional[t.Any] = None
    bytecode_cache: t.Optional[t.Any] = None

    @internalcode
    async def get_template(
        self,
        name: str,
        parent: t.Optional[str] = None,
        env_globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> "Template":
        if isinstance(name, Template):
            return name
        if parent is not None:
            name = self.join_path(name, parent)
        return await self._load_template(name, env_globals)

    @internalcode
    async def _load_template(
        self, name: str, env_globals: t.Optional[t.MutableMapping[str, t.Any]]
    ) -> "Template":
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (ref(self.loader), name)
        if self.cache is not None:
            template = self.cache.get(cache_key)
            if template and (not self.auto_reload or template.is_up_to_date):
                if env_globals:
                    template.globals.update(env_globals)
                return template
        template = await self.loader.load(self, name, self.make_globals(env_globals))
        if self.cache is not None:
            self.cache[cache_key] = template
        return template
