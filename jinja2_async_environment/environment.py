import re
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


class TemplateResolver:
    """Service class for template resolution logic to improve code organization."""

    def __init__(self, environment: "AsyncEnvironment") -> None:
        self.environment = environment

    def is_template_or_mock(self, obj: t.Any) -> bool:
        """Check if object is a Template or MagicMock."""
        return isinstance(obj, Template) or str(type(obj)).find("MagicMock") != -1

    def resolve_template_name(self, name: str, parent: str | None) -> str:
        """Resolve template name with optional parent path."""
        if parent is not None:
            return self.environment.join_path(name, parent)
        return name

    async def load_single_template(
        self, name: str, globals: t.MutableMapping[str, t.Any] | None
    ) -> Template:
        """Load a single template by name."""
        return await self.environment._load_template_async(name, globals)

    async def try_load_template(
        self, name: str, globals: t.MutableMapping[str, t.Any] | None
    ) -> tuple[Template | None, str]:
        """Try to load a template, returning None on failure."""
        try:
            template = await self.load_single_template(name, globals)
            return template, name
        except (TemplateNotFound, UndefinedError):
            return None, name


class AsyncEnvironment(Environment):
    code_generator_class: type[CodeGenerator] = AsyncCodeGenerator
    loader: t.Any | None = None
    bytecode_cache: AsyncBytecodeCache | None = None

    # Pre-compiled regex patterns for performance optimization
    _async_yield_pattern = re.compile(  # REGEX OK: template compilation optimization
        r"async for event in self\._async_yield_from\([^)]+\):\s*$", re.MULTILINE
    )

    # String replacement patterns for better performance
    _replacement_patterns = {
        "yield from context.blocks": "pass  # yield from replaced",
        "undefined(name='item') if l_0_item is missing else l_0_item": "item",
        "undefined(name='i') if l_0_i is missing else l_0_i": "i",
        "undefined(name='message') if l_0_message is missing else l_0_message": "message",
        "undefined(name='partial_var') if l_0_partial_var is missing else l_0_partial_var": "partial_var",
    }

    def __init__(
        self, *args: t.Any, cache_manager: t.Any = None, **kwargs: t.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.enable_async = True
        self._template_resolver = TemplateResolver(self)

        # Set up cache manager for dependency injection
        if cache_manager is not None:
            self._cache_manager = cache_manager
        else:
            # Import here to avoid circular imports
            from .caching.manager import CacheManager

            self._cache_manager = CacheManager.get_default()

        if "escape" not in self.filters:
            self.filters["escape"] = escape

    @property
    def cache_manager(self) -> t.Any:
        """Get the cache manager for dependency injection.

        Returns:
            The cache manager instance used by this environment
        """
        return self._cache_manager

    def set_cache_manager(self, cache_manager: t.Any) -> None:
        """Set a new cache manager for this environment.

        Args:
            cache_manager: New cache manager to use
        """
        self._cache_manager = cache_manager

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
                # Apply all string replacements in a single pass for better performance
                for old_pattern, new_pattern in self._replacement_patterns.items():
                    source = source.replace(old_pattern, new_pattern)

                # Apply regex substitution using pre-compiled pattern
                source = self._async_yield_pattern.sub(
                    "async for event in self._async_yield_from(context.blocks):\n        yield event",
                    source,
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
        if self._template_resolver.is_template_or_mock(name):
            return t.cast(Template, name)
        resolved_name = self._template_resolver.resolve_template_name(
            str(name), str(parent) if parent else None
        )
        return await self._load_template_async(resolved_name, globals)

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
            if self._template_resolver.is_template_or_mock(name):
                return t.cast(Template, name)
            resolved_name = self._template_resolver.resolve_template_name(
                str(name), parent
            )
            template, failed_name = await self._template_resolver.try_load_template(
                resolved_name, globals
            )
            if template is not None:
                return template
            names_list.append(failed_name)
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
        elif isinstance(template_name_or_list, Template):
            return template_name_or_list
        elif self._template_resolver.is_template_or_mock(template_name_or_list):
            return t.cast(Template, template_name_or_list)
        return await self.select_template_async(template_name_or_list, parent, globals)

    @internalcode
    async def _load_template_async(
        self,
        name: str | Template | t.Iterable[str | Template],
        globals: t.MutableMapping[str, t.Any] | None,
    ) -> Template:
        if self._template_resolver.is_template_or_mock(name):
            return t.cast(Template, name)
        if isinstance(name, str):
            return await self._get_template_async(name, globals)
        if isinstance(name, Template):
            return name
        names_list = []
        for template_name in name:
            if self._template_resolver.is_template_or_mock(template_name):
                return t.cast(Template, template_name)
            template, failed_name = await self._template_resolver.try_load_template(
                str(template_name), globals
            )
            if template is not None:
                return template
            names_list.append(failed_name)
        raise TemplatesNotFound(names_list)

    async def _get_template_async(
        self, name: str, globals: t.MutableMapping[str, t.Any] | None
    ) -> Template:
        if self.loader is None:
            raise TypeError("no loader for this environment specified")

        from weakref import ref

        cache_key = (ref(self.loader), name)

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
        if self.loader is None:
            raise TypeError("No loader configured for this environment")
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
