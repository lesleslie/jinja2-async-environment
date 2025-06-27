"""Tests for macro parameter resolution functionality."""

import pytest
from anyio import Path as AsyncPath
from jinja2_async_environment import AsyncDictLoader, AsyncEnvironment


class TestMacroParameters:
    """Test proper macro parameter resolution."""

    @pytest.fixture
    def env(self) -> AsyncEnvironment:
        """Create AsyncEnvironment for parameter testing."""
        return AsyncEnvironment(
            loader=AsyncDictLoader({}, AsyncPath(".")), enable_async=True
        )

    @pytest.mark.asyncio
    async def test_simple_parameter_resolution(self, env: AsyncEnvironment) -> None:
        """Test that macro parameters are correctly resolved."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro greet(name) -%}
Hello {{ name }}!
{%- endmacro -%}

{{ greet('Alice') }}"""
            },
            searchpath=AsyncPath("."),
        )
        env.loader = loader

        template = await env.get_template_async("test.html")
        result = await template.render_async()

        # This should pass once parameter resolution is fixed
        assert result.strip() == "Hello Alice!"

    @pytest.mark.asyncio
    async def test_multiple_parameters(self, env: AsyncEnvironment) -> None:
        """Test macro with multiple parameters."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro format_user(name, age, city) -%}
{{ name }} is {{ age }} years old and lives in {{ city }}
{%- endmacro -%}

{{ format_user('Bob', 25, 'NYC') }}"""
            },
            searchpath=AsyncPath("."),
        )
        env.loader = loader

        template = await env.get_template_async("test.html")
        result = await template.render_async()

        expected = "Bob is 25 years old and lives in NYC"
        assert result.strip() == expected

    @pytest.mark.asyncio
    async def test_parameter_with_default_values(self, env: AsyncEnvironment) -> None:
        """Test macro parameters with default values (has current limitation)."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro greet(name, greeting='Hello') -%}
{{ greeting }} {{ name }}!
{%- endmacro -%}

{{ greet('Alice') }}
{{ greet('Bob', 'Hi') }}"""
            },
            searchpath=AsyncPath("."),
        )
        env.loader = loader

        template = await env.get_template_async("test.html")
        result = await template.render_async()

        lines = [line.strip() for line in result.strip().split("\n") if line.strip()]
        # Default parameters now work correctly!
        assert "Hello Alice!" in lines
        # Explicit parameters work correctly
        assert "Hi Bob!" in lines

    @pytest.mark.asyncio
    async def test_parameter_vs_context_priority(self, env: AsyncEnvironment) -> None:
        """Test that macro parameters take priority over context variables."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro test_priority(name) -%}
{{ name }}
{%- endmacro -%}

{{ test_priority('Parameter') }}"""
            },
            searchpath=AsyncPath("."),
        )
        env.loader = loader

        template = await env.get_template_async("test.html")
        # Render with a context variable that has the same name
        result = await template.render_async(name="Context")

        # The macro parameter should take priority over context
        assert result.strip() == "Parameter"

    @pytest.mark.asyncio
    async def test_nested_macro_parameters(self, env: AsyncEnvironment) -> None:
        """Test parameter resolution in nested macro calls."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro outer(name) -%}
Outer: {{ name }}
{%- endmacro -%}

{%- macro inner(name) -%}
Inner: {{ name }}, {{ outer('OuterParam') }}
{%- endmacro -%}

{{ inner('InnerParam') }}"""
            },
            searchpath=AsyncPath("."),
        )
        env.loader = loader

        template = await env.get_template_async("test.html")
        result = await template.render_async()

        # Should contain both parameter values correctly
        assert "Inner: InnerParam" in result
        assert "Outer: OuterParam" in result

    @pytest.mark.asyncio
    async def test_macro_parameter_types(self, env: AsyncEnvironment) -> None:
        """Test different parameter types (string, number, boolean)."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro test_types(text, number, flag) -%}
Text: {{ text }}, Number: {{ number }}, Flag: {{ flag }}
{%- endmacro -%}

{{ test_types('hello', 42, true) }}"""
            },
            searchpath=AsyncPath("."),
        )
        env.loader = loader

        template = await env.get_template_async("test.html")
        result = await template.render_async()

        expected = "Text: hello, Number: 42, Flag: True"
        assert result.strip() == expected


class TestMacroParameterCurrentBehavior:
    """Test current (broken) behavior for comparison."""

    @pytest.mark.asyncio
    async def test_parameter_resolution_now_works(self) -> None:
        """Test that basic parameter resolution now works correctly."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro greet(name) -%}
Hello {{ name }}!
{%- endmacro -%}

{{ greet('Alice') }}"""
            },
            searchpath=AsyncPath("."),
        )
        env = AsyncEnvironment(loader=loader, enable_async=True)

        template = await env.get_template_async("test.html")
        result = await template.render_async()

        # Parameter resolution now works correctly
        assert result.strip() == "Hello Alice!"

    @pytest.mark.asyncio
    async def test_default_parameter_now_works(self) -> None:
        """Verify that default parameter values now work correctly."""
        loader = AsyncDictLoader(
            mapping={
                "test.html": """
{%- macro greet(name, greeting='Hello') -%}
{{ greeting }} {{ name }}!
{%- endmacro -%}

{{ greet('Alice') }}"""
            },
            searchpath=AsyncPath("."),
        )
        env = AsyncEnvironment(loader=loader, enable_async=True)

        template = await env.get_template_async("test.html")
        result = await template.render_async()

        # Default parameters now work correctly!
        assert result.strip() == "Hello Alice!"
