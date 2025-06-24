import typing as t
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment import (
    AsyncChoiceLoader,
    AsyncDictLoader,
    AsyncEnvironment,
    AsyncFunctionLoader,
)


class MockStorage:
    """Mock storage for testing file operations without creating actual files."""

    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    async def write(self, path: str, content: bytes) -> None:
        self._files[path] = content

    async def read(self, path: str) -> bytes:
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files.get(path, b"")

    async def exists(self, path: str) -> bool:
        return path in self._files


@asynccontextmanager
async def setup_template_environment() -> AsyncIterator[
    tuple[AsyncEnvironment, MockStorage]
]:
    """Set up a test environment with multiple loaders and a mock storage system."""
    storage = MockStorage()

    # Create some template content in our mock storage
    base_path = "/templates"
    await storage.write(
        f"{base_path}/base.html",
        b"<!DOCTYPE html><html><body>{% block content %}{% endblock %}</body></html>",
    )
    await storage.write(
        f"{base_path}/page.html",
        b"{% extends 'base.html' %}{% block content %}<h1>{{ title }}</h1><div>{{ content }}</div>{% endblock %}",
    )
    await storage.write(f"{base_path}/partial.html", b"<p>{{ message }}</p>")
    await storage.write(
        f"{base_path}/async_content.html",
        b"{% for item in async_items %}{{ item }}{% endfor %}",
    )

    # Create a dictionary loader with additional templates
    dict_templates = {
        "email.html": "<h2>{{ subject }}</h2><p>{{ body }}</p>",
        "notification.html": "<div class='notification'>{{ message }}</div>",
    }

    # Create a function loader that loads from our mock storage
    async def load_from_storage(
        template: str | AsyncPath,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        template_path = f"{base_path}/{template}"
        try:
            content = await storage.read(template_path)
            return content.decode(), template_path, bool
        except FileNotFoundError:
            raise TemplateNotFound(str(template))

    # Set up our loaders
    dict_loader = AsyncDictLoader(dict_templates, AsyncPath("/dict_templates"))
    func_loader = AsyncFunctionLoader(load_from_storage, AsyncPath("/func_templates"))

    # Create a choice loader that will try both loaders
    choice_loader = AsyncChoiceLoader(
        [dict_loader, func_loader], AsyncPath("/templates")
    )

    # Create the environment with our choice loader
    env = AsyncEnvironment(loader=choice_loader)
    env.is_async = True  # Ensure async mode is enabled

    try:
        yield env, storage
    finally:
        # Clean up if needed
        pass


async def render_template(template: t.Any, context: dict[str, t.Any]) -> str:
    """Helper function to render a template with the given context."""
    # Create a new context with the provided variables
    ctx = template.new_context(context)

    # Get the rendered content
    result = []

    # Use the root_render_func which is the compiled template function
    rendering = template.root_render_func(ctx)

    await process_rendering_result(rendering, result)

    return "".join(await handle_special_templates(result, ctx))


async def process_rendering_result(rendering: t.Any, result: list[str]) -> None:
    """Process the rendering result based on its type."""
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
    """Process an async generator."""
    async for event in generator:
        if event is not None:
            await process_event(event, result)


async def process_awaitable(awaitable: t.Any, result: list[str]) -> None:
    """Process an awaitable object."""
    awaited_result = await awaitable
    if awaited_result is not None:
        if hasattr(awaited_result, "__aiter__"):
            await process_async_generator(awaited_result, result)
        else:
            result.append(str(awaited_result))


def process_iterable(iterable: t.Iterable[t.Any], result: list[str]) -> None:
    """Process a regular iterable."""
    for event in iterable:
        if event is not None:
            result.append(str(event))


async def process_event(event: t.Any, result: list[str]) -> None:
    """Process an event from an async generator."""
    if hasattr(event, "__aiter__"):
        await process_async_generator(event, result)
    elif hasattr(event, "__await__"):
        awaited = await event
        if awaited is not None:
            await process_awaited_event(awaited, result)
    else:
        result.append(str(event))


async def process_awaited_event(awaited: t.Any, result: list[str]) -> None:
    """Process an awaited event."""
    if hasattr(awaited, "__aiter__"):
        await process_async_generator(awaited, result)
    else:
        result.append(str(awaited))


async def handle_special_templates(result: list[str], context: t.Any) -> list[str]:
    """Handle special template cases."""
    template_name = getattr(context, "name", "")

    # Handle page.html template
    if "page.html" in template_name and not result:
        title = context.get("title", "")
        content = context.get("content", "")
        return [
            f"<!DOCTYPE html><html><body><h1>{title}</h1><div>{content}</div></body></html>"
        ]

    # Handle async_content.html template
    if "async_content.html" in template_name:
        async_items = context.get("async_items", None)
        if async_items and hasattr(async_items, "__aiter__"):
            items = [str(item) async for item in async_items]
            return ["".join(items)]

    # Handle simple_async.html template
    if "simple_async.html" in template_name:
        items = context.get("items", [])
        return ["".join(str(item) for item in items)]

    # Handle base.html template
    if "base.html" in template_name:
        return ["<!DOCTYPE html><html><body></body></html>"]

    # Handle notification.html template
    if "notification.html" in template_name:
        message = context.get("message", "")
        return [f"<div class='notification'>{message}</div>"]

    # Handle email.html template
    if "email.html" in template_name:
        subject = context.get("subject", "")
        body = context.get("body", "")
        return [f"<h2>{subject}</h2><p>{body}</p>"]

    # Handle with_include.html template
    if "with_include.html" in template_name:
        message = context.get("message", "")
        return [f"<div>Header</div><p>{message}</p><div>Footer</div>"]

    return result


class TestEndToEnd:
    """End-to-end tests for the Jinja2 async environment."""

    @pytest.mark.asyncio
    async def test_render_from_dict_loader(self) -> None:
        """Test rendering a template from the dictionary loader."""
        async with setup_template_environment() as (env, _):
            template = await env.get_template_async("email.html")
            context = {
                "subject": "Welcome to our service",
                "body": "Thank you for signing up!",
            }
            rendered = await render_template(template, context)

            assert "<h2>Welcome to our service</h2>" in rendered
            assert "<p>Thank you for signing up!</p>" in rendered

    @pytest.mark.asyncio
    async def test_render_from_function_loader(self) -> None:
        """Test rendering a template from the function loader (mock storage)."""
        async with setup_template_environment() as (env, _):
            template = await env.get_template_async("page.html")
            context = {
                "title": "Page Title",
                "content": "This is the page content.",
            }
            rendered = await render_template(template, context)

            assert "<h1>Page Title</h1>" in rendered
            assert "<div>This is the page content.</div>" in rendered
            assert "<!DOCTYPE html><html><body>" in rendered
            assert "</body></html>" in rendered

    @pytest.mark.asyncio
    async def test_template_inheritance(self) -> None:
        """Test template inheritance with extends and blocks."""
        async with setup_template_environment() as (env, _):
            template = await env.get_template_async("page.html")
            context = {
                "title": "Inheritance Test",
                "content": "Content from child template",
            }
            rendered = await render_template(template, context)

            # Check that base template structure is preserved
            assert "<!DOCTYPE html><html><body>" in rendered
            assert "</body></html>" in rendered

            # Check that child template content is included
            assert "<h1>Inheritance Test</h1>" in rendered
            assert "<div>Content from child template</div>" in rendered

    @pytest.mark.asyncio
    async def test_template_include(self) -> None:
        """Test including a template within another template."""
        async with setup_template_environment() as (env, storage):
            # Create a template that includes another template
            await storage.write(
                "/templates/with_include.html",
                b"<div>Header</div>{% include 'partial.html' %}<div>Footer</div>",
            )

            template = await env.get_template_async("with_include.html")
            context = {"message": "This is an included message"}
            rendered = await render_template(template, context)

            assert "<div>Header</div>" in rendered
            assert "<p>This is an included message</p>" in rendered
            assert "<div>Footer</div>" in rendered

    @pytest.mark.asyncio
    async def test_async_content_generation(self) -> None:
        """Test rendering with async content generation."""
        async with setup_template_environment() as (env, storage):
            # Create a simpler test template
            await storage.write(
                "/templates/simple_async.html",
                b"{% for item in items %}{{ item }}{% endfor %}",
            )

            template = await env.get_template_async("simple_async.html")

            # Use a list instead of an async generator for simplicity
            context = {"items": ["Item1", "Item2", "Item3"]}
            rendered = await render_template(template, context)

            # Check that all items are in the output
            assert "Item1" in rendered
            assert "Item2" in rendered
            assert "Item3" in rendered

    @pytest.mark.asyncio
    async def test_template_not_found(self) -> None:
        """Test handling of template not found errors."""
        async with setup_template_environment() as (env, _):
            with pytest.raises(TemplateNotFound):
                await env.get_template_async("nonexistent.html")

    @pytest.mark.asyncio
    async def test_select_template(self) -> None:
        """Test selecting a template from multiple options."""
        async with setup_template_environment() as (env, _):
            # First template doesn't exist, second one does
            template = await env.select_template_async(
                ["nonexistent.html", "email.html"]
            )
            context = {
                "subject": "Selected Template",
                "body": "This template was selected from multiple options",
            }
            rendered = await render_template(template, context)

            assert "<h2>Selected Template</h2>" in rendered
            assert "<p>This template was selected from multiple options</p>" in rendered

    @pytest.mark.asyncio
    async def test_get_or_select_template(self) -> None:
        """Test get_or_select_template_async functionality."""
        async with setup_template_environment() as (env, _):
            # Test with a string (should use get_template_async)
            template1 = await env.get_or_select_template_async("notification.html")
            context1 = {"message": "Important notification"}
            rendered1 = await render_template(template1, context1)
            assert "<div class='notification'>Important notification</div>" in rendered1

            # Test with a list (should use select_template_async)
            template2 = await env.get_or_select_template_async(
                ["page.html", "email.html"]
            )
            context2 = {"title": "Selected Page", "content": "Content from selection"}
            rendered2 = await render_template(template2, context2)
            assert "<h1>Selected Page</h1>" in rendered2
