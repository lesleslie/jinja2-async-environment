import typing as t

import pytest
from anyio import Path as AsyncPath
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


async def render_template_simple(template: t.Any, context: dict[str, t.Any]) -> str:
    """Simple helper to render a template."""
    ctx = template.new_context(context)
    rendering = template.root_render_func(ctx)

    # Handle both sync and async results
    if hasattr(rendering, "__aiter__"):
        result = [event async for event in rendering]
    elif hasattr(rendering, "__iter__") and not isinstance(rendering, str):
        result = list(rendering)
    else:
        result = [str(rendering)] if rendering is not None else []

    return "".join(str(item) for item in result)


class TestEscapeFilter:
    @pytest.fixture
    def template_dict(self) -> dict[str, str]:
        return {
            "escape_test.html": "<!DOCTYPE html><html><body>Hello {{ name | escape }}</body></html>",
            "autoescape_test.html": "<!DOCTYPE html><html><body>Hello {{ name }}</body></html>",
            "multiple_escapes.html": "<div>{{ value1 | escape }} and {{ value2 | escape }}</div>",
            "nested_escapes.html": "<div>{{ (value1 + value2) | escape }}</div>",
        }

    @pytest.fixture
    def loader(self, template_dict: dict[str, str]) -> AsyncDictLoader:
        return AsyncDictLoader(template_dict, AsyncPath("/templates"))

    @pytest.fixture
    def environment(self, loader: AsyncDictLoader) -> AsyncEnvironment:
        env = AsyncEnvironment(loader=loader, autoescape=True)
        env.enable_async = True
        return env

    @pytest.mark.asyncio
    async def test_explicit_escape_filter(self, environment: AsyncEnvironment) -> None:
        """Test that the escape filter works when explicitly used."""
        template = await environment.get_template_async("escape_test.html")
        result = await render_template_simple(template, {"name": "<World>"})
        assert result == "<!DOCTYPE html><html><body>Hello &lt;World&gt;</body></html>"

    @pytest.mark.asyncio
    async def test_autoescape(self, environment: AsyncEnvironment) -> None:
        """Test that autoescape works when enabled in the environment."""
        template = await environment.get_template_async("autoescape_test.html")
        result = await render_template_simple(template, {"name": "<World>"})
        assert result == "<!DOCTYPE html><html><body>Hello &lt;World&gt;</body></html>"

    @pytest.mark.asyncio
    async def test_multiple_escapes(self, environment: AsyncEnvironment) -> None:
        """Test that multiple escape filters in the same template work correctly."""
        template = await environment.get_template_async("multiple_escapes.html")
        result = await render_template_simple(
            template, {"value1": "<tag1>", "value2": "<tag2>"}
        )
        assert result == "<div>&lt;tag1&gt; and &lt;tag2&gt;</div>"

    @pytest.mark.asyncio
    async def test_nested_expression_escape(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test that escape filter works with nested expressions."""
        template = await environment.get_template_async("nested_escapes.html")
        result = await render_template_simple(
            template, {"value1": "<hello>", "value2": "<world>"}
        )
        assert result == "<div>&lt;hello&gt;&lt;world&gt;</div>"

    @pytest.mark.asyncio
    async def test_escape_with_non_string_values(
        self, environment: AsyncEnvironment
    ) -> None:
        """Test that escape filter works with non-string values."""
        template = await environment.get_template_async("escape_test.html")
        result = await render_template_simple(template, {"name": 123})
        assert result == "<!DOCTYPE html><html><body>Hello 123</body></html>"
