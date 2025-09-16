"""Tests for GitHub issue #6 fixes.

This module contains tests for the tuple unpacking and join filter fixes
reported in GitHub issue #6.
"""

import pytest
from anyio import Path
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


@pytest.mark.asyncio
async def test_tuple_unpacking_in_for_loop():
    """Test tuple unpacking in for loops works correctly."""
    loader = AsyncDictLoader(
        {
            "tuple_test": """
        {%- for key, value in items -%}
        {{ key }}: {{ value }}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("tuple_test")
    result = await template.render_async(items=[("a", 1), ("b", 2), ("c", 3)])

    expected = "a: 1\n        b: 2\n        c: 3"
    assert result.strip() == expected.strip()


@pytest.mark.asyncio
async def test_triple_tuple_unpacking():
    """Test triple tuple unpacking in for loops."""
    loader = AsyncDictLoader(
        {
            "triple_test": """
        {%- for x, y, z in coords -%}
        ({{ x }}, {{ y }}, {{ z }})
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("triple_test")
    result = await template.render_async(coords=[(1, 2, 3), (4, 5, 6)])

    expected = "(1, 2, 3)\n        (4, 5, 6)"
    assert result.strip() == expected.strip()


@pytest.mark.asyncio
async def test_join_filter_with_set_variable():
    """Test join filter with variables set in template."""
    loader = AsyncDictLoader(
        {
            "join_test": """
        {%- set items = ['a', 'b', 'c'] -%}
        {{ items | join(", ") }}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("join_test")
    result = await template.render_async()

    assert result.strip() == "a, b, c"


@pytest.mark.asyncio
async def test_join_filter_with_passed_variables():
    """Test join filter with variables passed to template."""
    loader = AsyncDictLoader(
        {
            "join_var_test": """
        {{ items | join(", ") }}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("join_var_test")
    result = await template.render_async(items=["x", "y", "z"])

    assert result.strip() == "x, y, z"


@pytest.mark.asyncio
async def test_combined_tuple_unpacking_and_join():
    """Test tuple unpacking combined with join filter."""
    loader = AsyncDictLoader(
        {
            "combined_test": """
        {%- for name, values in data -%}
        {{ name }}: {{ values | join(", ") }}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("combined_test")
    result = await template.render_async(
        data=[("fruits", ["apple", "banana"]), ("colors", ["red", "blue"])]
    )

    expected = "fruits: apple, banana\n        colors: red, blue"
    assert result.strip() == expected.strip()


@pytest.mark.asyncio
async def test_dictionary_items_tuple_unpacking():
    """Test tuple unpacking with dictionary items."""
    loader = AsyncDictLoader(
        {
            "dict_test": """
        {%- for key, value in data.items() -%}
        {{ key }}={{ value }}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("dict_test")
    result = await template.render_async(data={"name": "John", "age": 30})

    # Dictionary order might vary, so check both possibilities
    assert result.strip() in ["name=John\n        age=30", "age=30\n        name=John"]


@pytest.mark.asyncio
async def test_nested_tuple_unpacking():
    """Test nested tuple unpacking."""
    loader = AsyncDictLoader(
        {
            "nested_test": """
        {%- for name, (age, city) in users -%}
        {{ name }} ({{ age }}) from {{ city }}
        {% endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("nested_test")
    result = await template.render_async(
        users=[("Alice", (25, "NYC")), ("Bob", (30, "LA"))]
    )

    expected = "Alice (25) from NYC\n        Bob (30) from LA"
    assert result.strip() == expected.strip()


@pytest.mark.asyncio
async def test_for_loop_with_else_clause():
    """Test tuple unpacking in for loops with else clause."""
    loader = AsyncDictLoader(
        {
            "else_test": """
        {%- for key, value in items -%}
        {{ key }}: {{ value }}
        {%- else -%}
        No items
        {%- endfor -%}
        """
        },
        searchpath=Path("."),
    )

    env = AsyncEnvironment(loader=loader, enable_async=True)
    template = await env.get_template_async("else_test")

    # Test with items
    result = await template.render_async(items=[("a", 1)])
    assert result.strip() == "a: 1"

    # Test without items (else clause)
    result = await template.render_async(items=[])
    assert result.strip() == "No items"
