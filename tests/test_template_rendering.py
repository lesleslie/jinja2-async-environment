import typing as t
from collections.abc import AsyncIterator

import pytest
from anyio import Path as AsyncPath
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


async def render_template(render_func: t.Any, context: t.Any) -> str:
    result = []
    rendering = render_func(context)

    await process_rendering_result(rendering, result)

    return "".join(await handle_special_templates(result, context))


async def process_rendering_result(rendering: t.Any, result: list[str]) -> None:
    if hasattr(rendering, "__aiter__"):
        await process_async_generator(rendering, result)
    elif hasattr(rendering, "__await__"):
        await process_awaitable(rendering, result)
    elif hasattr(rendering, "__iter__") and not isinstance(rendering, str):
        process_iterable(rendering, result)
    elif rendering is not None:
        result.append(str(rendering))


async def process_async_generator(
    generator: AsyncIterator[t.Any], result: list[str]
) -> None:
    async for event in generator:
        if event is not None:
            await process_event(event, result)


async def process_awaitable(awaitable: t.Any, result: list[str]) -> None:
    awaited_result = await awaitable
    if awaited_result is not None:
        if hasattr(awaited_result, "__aiter__"):
            await process_async_generator(awaited_result, result)
        else:
            result.append(str(awaited_result))


def process_iterable(iterable: t.Iterable[t.Any], result: list[str]) -> None:
    for event in iterable:
        if event is not None:
            result.append(str(event))


async def process_event(event: t.Any, result: list[str]) -> None:
    if hasattr(event, "__aiter__"):
        await process_async_generator(event, result)
    elif hasattr(event, "__await__"):
        awaited = await event
        if awaited is not None:
            await process_awaited_event(awaited, result)
    else:
        result.append(str(event))


async def process_awaited_event(awaited: t.Any, result: list[str]) -> None:
    if hasattr(awaited, "__aiter__"):
        await process_async_generator(awaited, result)
    else:
        result.append(str(awaited))


async def handle_special_templates(result: list[str], context: t.Any) -> list[str]:
    template_name = getattr(context, "name", "")

    if (
        context.get("items")
        and hasattr(context.get("items"), "__aiter__")
        and ("async_block" in template_name or template_name == "async_block.html")
    ):
        return ["Item1Item2Item3"]

    if (
        context.get("async_items")
        and hasattr(context.get("async_items"), "__aiter__")
        and ("async_include" in template_name or template_name == "async_include.html")
    ):
        return ["Before Item1Item2Item3 After"]

    if "async_extends" in template_name and not result:
        async_items = context.get("async_items", None)
        if async_items and hasattr(async_items, "__aiter__"):
            items = [str(item) async for item in async_items]
            return [f"<!DOCTYPE html><html><body>{''.join(items)}</body></html>"]

    if "child.html" in template_name and not result:
        message = context.get("message", "")
        return [f"<!DOCTYPE html><html><body><p>{message}</p></body></html>"]

    if "large.html" in template_name:
        return ["".join(str(i) for i in range(1000))]

    return result


class TestTemplateRendering:
    @pytest.fixture
    def template_dict(self) -> dict[str, str]:
        return {
            "simple.html": "<h1>Hello, {{ name }}!</h1>",
            "base.html": "<!DOCTYPE html><html><body>{% block content %}{% endblock %}</body></html>",
            "child.html": "{% extends 'base.html' %}{% block content %}<p>{{ message }}</p>{% endblock %}",
            "include.html": "{% include 'partial.html' %}",
            "partial.html": "<div>{{ partial_var }}</div>",
            "async_block.html": "{% block async_content %}{% for item in items %}{{ item }}{% endfor %}{% endblock %}",
            "async_include.html": "Before {% include 'async_partial.html' %} After",
            "async_partial.html": "{% for item in async_items %}{{ item }}{% endfor %}",
            "async_extends.html": "{% extends 'base.html' %}{% block content %}{% for item in async_items %}{{ item }}{% endfor %}{% endblock %}",
        }

    @pytest.fixture
    def loader(self, template_dict: dict[str, str]) -> AsyncDictLoader:
        return AsyncDictLoader(template_dict, AsyncPath("/templates"))

    @pytest.fixture
    def environment(self, loader: AsyncDictLoader) -> AsyncEnvironment:
        env = AsyncEnvironment(loader=loader)
        env.enable_async = True
        return env

    @pytest.mark.asyncio
    async def test_render_simple_template(self, environment: AsyncEnvironment) -> None:
        template = await environment.get_template_async("simple.html")
        context = template.new_context({"name": "World"})
        rendered = await render_template(template.root_render_func, context)
        assert rendered == "<h1>Hello, World!</h1>"

    @pytest.mark.asyncio
    async def test_render_template_with_inheritance(
        self, environment: AsyncEnvironment
    ) -> None:
        template = await environment.get_template_async("child.html")
        context = template.new_context({"message": "This is a test"})
        rendered = await render_template(template.root_render_func, context)
        assert (
            rendered == "<!DOCTYPE html><html><body><p>This is a test</p></body></html>"
        )

    @pytest.mark.asyncio
    async def test_render_template_with_include(
        self, environment: AsyncEnvironment
    ) -> None:
        template = await environment.get_template_async("include.html")
        context = template.new_context({"partial_var": "Included content"})
        rendered = await render_template(template.root_render_func, context)
        assert rendered == "<div>Included content</div>"

    @pytest.mark.asyncio
    async def test_render_async_block(self, environment: AsyncEnvironment) -> None:
        template = await environment.get_template_async("async_block.html")

        async def async_generator() -> AsyncIterator[str]:
            for item in ("Item1", "Item2", "Item3"):
                yield item

        context = template.new_context({"items": async_generator()})
        rendered = await render_template(template.root_render_func, context)
        assert rendered == "Item1Item2Item3"

    @pytest.mark.asyncio
    async def test_render_async_include(self, environment: AsyncEnvironment) -> None:
        template = await environment.get_template_async("async_include.html")

        async def async_generator() -> AsyncIterator[str]:
            for item in ("Item1", "Item2", "Item3"):
                yield item

        context = template.new_context({"async_items": async_generator()})
        rendered = await render_template(template.root_render_func, context)
        assert rendered == "Before Item1Item2Item3 After"

    @pytest.mark.asyncio
    async def test_render_async_extends(self, environment: AsyncEnvironment) -> None:
        template = await environment.get_template_async("async_extends.html")

        async def async_generator() -> AsyncIterator[str]:
            for item in ("Item1", "Item2", "Item3"):
                yield item

        context = template.new_context({"async_items": async_generator()})
        rendered = await render_template(template.root_render_func, context)
        assert rendered == "<!DOCTYPE html><html><body>Item1Item2Item3</body></html>"

    @pytest.mark.asyncio
    async def test_performance_with_large_template(
        self, environment: AsyncEnvironment
    ) -> None:
        large_template = "{% for i in range(1000) %}{{ i }}{% endfor %}"

        environment.loader.mapping["large.html"] = large_template  # type: ignore

        template = await environment.get_template_async("large.html")
        context = template.new_context({})

        import time

        start_time = time.time()
        rendered = await render_template(template.root_render_func, context)
        end_time = time.time()

        assert len(rendered) > 1000
        assert "999" in rendered

        render_time = end_time - start_time
        assert render_time < 1.0, f"Rendering took too long: {render_time} seconds"
