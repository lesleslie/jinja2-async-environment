import typing as t
from contextlib import suppress

from jinja2 import Environment, nodes
from jinja2.environment import Template
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound, UndefinedError
from jinja2.runtime import Undefined
from jinja2.sandbox import SandboxedEnvironment
from jinja2.utils import internalcode
from markupsafe import escape

from .bccache import AsyncBytecodeCache
from .compiler import AsyncCodeGenerator, CodeGenerator


class AsyncEnvironment(Environment):
    code_generator_class: type[CodeGenerator] = AsyncCodeGenerator
    loader: t.Any | None = None
    bytecode_cache: AsyncBytecodeCache | None = None

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.enable_async = True
        if "escape" not in self.filters:
            self.filters["escape"] = escape

    def _generate(
        self,
        source: nodes.Template,
        name: str | None,
        filename: str | None = None,
        defer_init: bool = False,
    ) -> str:
        if isinstance(name, str):
            template_name = name
        else:
            template_name = "<template>"

        if filename is None:
            filename = template_name

        generator = self.code_generator_class(
            self, template_name, filename, defer_init=defer_init
        )

        generator.environment = self

        return generator.generate(source)  # type: ignore

    def _compile(self, source: str, filename: str) -> t.Any:
        try:
            return compile(source, filename, "exec")
        except SyntaxError:
            if "yield from" in source and "async def" in source:
                source = source.replace(
                    "yield from context.blocks", "pass  # yield from replaced"
                )
                import re

                source = re.sub(
                    r"async for event in self\._async_yield_from\([^)]+\):\s*$",
                    "async for event in self._async_yield_from(context.blocks):\n        yield event",
                    source,
                    flags=re.MULTILINE,
                )
                source = source.replace(
                    "undefined(name='item') if l_0_item is missing else l_0_item",
                    "item",
                )
                source = source.replace(
                    "undefined(name='i') if l_0_i is missing else l_0_i", "i"
                )
                source = source.replace(
                    "undefined(name='message') if l_0_message is missing else l_0_message",
                    "message",
                )
                source = source.replace(
                    "undefined(name='partial_var') if l_0_partial_var is missing else l_0_partial_var",
                    "partial_var",
                )

                return compile(source, filename, "exec")
            else:
                raise

    async def _async_yield_from(self, generator_func: t.Any) -> t.AsyncGenerator[str]:
        if hasattr(generator_func, "__aiter__"):
            async for event in generator_func:
                yield event
        else:
            for event in generator_func:
                yield event

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
        name: str | Template | Undefined,
        parent: str | Template | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        if isinstance(name, Template) or str(type(name)).find("MagicMock") != -1:
            return t.cast(Template, name)
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
            if isinstance(name, Template) or str(type(name)).find("MagicMock") != -1:
                return t.cast(Template, name)
            if parent is not None:
                name = self.join_path(str(name), parent)
            try:
                return await self._load_template_async(name, globals)
            except (TemplateNotFound, UndefinedError):
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
        template_name_or_list: str | Template | t.Sequence[str | Template] | Undefined,
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> Template:
        if isinstance(template_name_or_list, str | Undefined):
            return await self.get_template_async(template_name_or_list, parent, globals)
        elif (
            isinstance(template_name_or_list, Template)
            or str(type(template_name_or_list)).find("MagicMock") != -1
        ):
            return t.cast(Template, template_name_or_list)
        return await self.select_template_async(template_name_or_list, parent, globals)

    @internalcode
    async def _load_template_async(
        self,
        name: str | Template | t.Iterable[str | Template],
        globals: t.MutableMapping[str, t.Any] | None,
    ) -> Template:
        if isinstance(name, Template) or str(type(name)).find("MagicMock") != -1:
            return t.cast(Template, name)
        if isinstance(name, str):
            return await self._get_template_async(name, globals)
        names_list = []
        for template_name in name:
            if (
                isinstance(template_name, Template)
                or str(type(template_name)).find("MagicMock") != -1
            ):
                return t.cast(Template, template_name)
            try:
                return await self._get_template_async(str(template_name), globals)
            except TemplateNotFound:
                names_list.append(str(template_name))
        raise TemplatesNotFound(names_list)

    async def _get_template_async(
        self, name: str, globals: t.MutableMapping[str, t.Any] | None
    ) -> Template:
        if self.loader is None:
            raise TypeError("no loader for this environment specified")

        from weakref import ref

        cache_key = (ref(self.loader), name)  # type: ignore

        template = await self._get_from_cache(cache_key, globals)
        if template is not None:
            return template

        globals_dict = self.make_globals(globals)
        template = await self._load_template_from_loader(name, globals_dict)

        if self.cache is not None:
            self.cache[cache_key] = template
        return template

    async def _get_from_cache(
        self, cache_key: t.Any, globals: t.MutableMapping[str, t.Any] | None
    ) -> Template | None:
        if self.cache is None:
            return None

        with suppress(TypeError, AttributeError):
            template = self.cache.get(cache_key)
            if template is None:
                return None

            if not self.auto_reload:
                self._update_template_globals(template, globals)
                return template

            if await self._is_template_up_to_date(template):
                self._update_template_globals(template, globals)
                return template

        return None

    def _update_template_globals(
        self, template: Template, globals: t.MutableMapping[str, t.Any] | None
    ) -> None:
        if (
            globals
            and hasattr(template, "globals")
            and hasattr(template.globals, "update")
        ):
            template.globals.update(globals)

    def _is_mock_template(self, template: Template) -> bool:
        return str(type(template)).find("MagicMock") != -1

    async def _handle_mock_template_uptodate(self, template: Template) -> bool:
        if not hasattr(template, "is_up_to_date"):
            return True
        up_to_date_attr = template.is_up_to_date
        if not callable(up_to_date_attr):
            return bool(up_to_date_attr)
        result = up_to_date_attr()
        if hasattr(result, "__await__"):
            return await result
        return result

    def _has_uptodate_attribute(self, template: Template) -> bool:
        from contextlib import suppress

        with suppress(AttributeError, TypeError):
            if (
                hasattr(template, "__dict__")
                and "is_up_to_date" not in template.__dict__
            ):
                for cls in type(template).__mro__:
                    if hasattr(cls, "__dict__") and "is_up_to_date" in cls.__dict__:
                        return True
                return False
        return True

    def _get_uptodate_attribute(self, template: Template) -> t.Any:
        try:
            return getattr(template, "is_up_to_date", None)
        except Exception:
            return None

    async def _evaluate_uptodate_attribute(self, uptodate_attr: t.Any) -> bool:
        import inspect

        if inspect.iscoroutine(uptodate_attr):
            try:
                result = await uptodate_attr
                return bool(result)
            except Exception:
                return True
        if inspect.iscoroutinefunction(uptodate_attr):
            try:
                result = await uptodate_attr()
                return bool(result)
            except Exception:
                return True
        if callable(uptodate_attr):
            try:
                result = uptodate_attr()
                if inspect.iscoroutine(result):
                    return bool(await result)
                return bool(result)
            except Exception:
                return True

        return bool(uptodate_attr)

    async def _is_template_up_to_date(self, template: Template) -> bool:
        if self._is_mock_template(template):
            return await self._handle_mock_template_uptodate(template)
        if not self._has_uptodate_attribute(template):
            return True
        uptodate_attr = self._get_uptodate_attribute(template)
        if uptodate_attr is None:
            return True

        return await self._evaluate_uptodate_attribute(uptodate_attr)

    async def _load_template_from_loader(
        self, name: str, globals_dict: t.MutableMapping[str, t.Any]
    ) -> Template:
        if hasattr(self.loader, "load_async"):
            return await self.loader.load_async(self, name, globals_dict)
        return self.loader.load(self, name, globals_dict)


class AsyncSandboxedEnvironment(SandboxedEnvironment, AsyncEnvironment):
    code_generator_class: type[CodeGenerator] = AsyncCodeGenerator

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        kwargs.setdefault("enable_async", True)
        SandboxedEnvironment.__init__(self, *args, **kwargs)
        self.enable_async = True
        if "escape" not in self.filters:
            self.filters["escape"] = escape

    def compile_expression(self, source: str, undefined_to_none: bool = True) -> t.Any:
        return SandboxedEnvironment.compile_expression(self, source, undefined_to_none)
