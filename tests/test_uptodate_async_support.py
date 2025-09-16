"""Tests for up-to-date async support features."""

import pytest
from anyio import Path
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


@pytest.mark.asyncio
async def test_loop_index_variable():
    """Test that loop.index variables work correctly in async for loops."""
    loader = AsyncDictLoader(
        {
            "loop_index_test": """
        {%- for item in items -%}
        Item {{ loop.index }}: {{ item }}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("loop_index_test")
    result = await template.render_async(items=["apple", "banana", "cherry"])

    expected = "Item 1: apple\n        Item 2: banana\n        Item 3: cherry"
    assert result.strip() == expected.strip()


@pytest.mark.asyncio
async def test_loop_index0_variable():
    """Test that loop.index0 variables work correctly in async for loops."""
    loader = AsyncDictLoader(
        {
            "loop_index0_test": """
        {%- for item in items -%}
        Item {{ loop.index0 }}: {{ item }}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("loop_index0_test")
    result = await template.render_async(items=["apple", "banana", "cherry"])

    expected = "Item 0: apple\n        Item 1: banana\n        Item 2: cherry"
    assert result.strip() == expected.strip()


@pytest.mark.asyncio
async def test_loop_first_last_variables():
    """Test that loop.first and loop.last variables work correctly."""
    loader = AsyncDictLoader(
        {
            "loop_first_last_test": """
        {%- for item in items -%}
        {%- if loop.first -%}First: {%- endif -%}
        {{ item }}
        {%- if loop.last -%}Last{%- endif -%}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("loop_first_last_test")
    result = await template.render_async(items=["apple", "banana", "cherry"])

    expected = "First:applebananacherryLast"
    assert result.strip() == expected.strip()


@pytest.mark.asyncio
async def test_loop_variables_with_tuple_unpacking():
    """Test that loop variables work with tuple unpacking."""
    loader = AsyncDictLoader(
        {
            "loop_tuple_test": """
        {%- for key, value in items -%}
        {{ loop.index }}. {{ key }}: {{ value }}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("loop_tuple_test")
    result = await template.render_async(items=[("a", 1), ("b", 2), ("c", 3)])

    expected = "1. a: 1\n        2. b: 2\n        3. c: 3"
    assert result.strip() == expected.strip()
