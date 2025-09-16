# Backward Compatibility Tests

## API Compatibility Tests

```python
import pytest
from jinja2_async_environment.environment import (
    AsyncEnvironment,
    AsyncSandboxedEnvironment,
)
from jinja2_async_environment.loaders import (
    AsyncBaseLoader,
    AsyncFileSystemLoader,
    AsyncDictLoader,
    AsyncFunctionLoader,
    AsyncPackageLoader,
    AsyncChoiceLoader,
)


class TestAPICompatibility:
    """Test backward compatibility of public APIs."""

    def test_environment_constructor_compatibility(self):
        """Test AsyncEnvironment constructor maintains backward compatibility."""
        # Test with no arguments
        env1 = AsyncEnvironment()
        assert env1 is not None

        # Test with typical arguments
        env2 = AsyncEnvironment(autoescape=True, trim_blocks=True)
        assert env2 is not None
        assert env2.autoescape is True
        assert env2.trim_blocks is True

        # Test with bytecode_cache
        from jinja2_async_environment.bccache import AsyncBytecodeCache

        bytecode_cache = AsyncBytecodeCache()
        env3 = AsyncEnvironment(bytecode_cache=bytecode_cache)
        assert env3 is not None
        assert env3.bytecode_cache is not None

    def test_sandboxed_environment_constructor_compatibility(self):
        """Test AsyncSandboxedEnvironment constructor maintains backward compatibility."""
        # Test with no arguments
        env1 = AsyncSandboxedEnvironment()
        assert env1 is not None

        # Test with typical arguments
        env2 = AsyncSandboxedEnvironment(autoescape=True, trim_blocks=True)
        assert env2 is not None
        assert env2.autoescape is True
        assert env2.trim_blocks is True

    def test_loader_constructor_compatibility(self):
        """Test loader constructors maintain backward compatibility."""
        # Test AsyncFileSystemLoader
        loader1 = AsyncFileSystemLoader("/tmp/templates")
        assert loader1 is not None

        loader2 = AsyncFileSystemLoader(["/tmp/templates1", "/tmp/templates2"])
        assert loader2 is not None

        # Test AsyncDictLoader
        templates = {"template.html": "<h1>Test</h1>"}
        loader3 = AsyncDictLoader(templates)
        assert loader3 is not None

        # Test AsyncFunctionLoader
        def load_func(name):
            return None

        loader4 = AsyncFunctionLoader(load_func)
        assert loader4 is not None

        # Test AsyncChoiceLoader
        loader5 = AsyncChoiceLoader([loader1, loader3])
        assert loader5 is not None

    def test_environment_method_signature_compatibility(self):
        """Test that environment method signatures haven't changed."""
        env = AsyncEnvironment()

        # These methods should exist and be callable
        assert hasattr(env, "get_template_async")
        assert hasattr(env, "select_template_async")
        assert hasattr(env, "get_or_select_template_async")

        # These methods should raise NotImplementedError (backward compatibility)
        assert hasattr(env, "get_template")
        assert hasattr(env, "select_template")
        assert hasattr(env, "get_or_select_template")

        with pytest.raises(NotImplementedError):
            env.get_template("template.html")

        with pytest.raises(NotImplementedError):
            env.select_template(["template1.html", "template2.html"])

        with pytest.raises(NotImplementedError):
            env.get_or_select_template("template.html")

    def test_loader_method_signature_compatibility(self):
        """Test that loader method signatures maintain backward compatibility."""
        # Test AsyncBaseLoader
        loader = AsyncBaseLoader("/tmp/templates")
        assert hasattr(loader, "get_source_async")
        assert hasattr(loader, "list_templates_async")
        assert hasattr(loader, "load_async")
```

## Import Compatibility Tests

```python
class TestImportCompatibility:
    """Test that import paths maintain backward compatibility."""

    def test_main_module_imports(self):
        """Test that main module imports work as expected."""
        # These should all work
        from jinja2_async_environment import AsyncEnvironment
        from jinja2_async_environment import AsyncSandboxedEnvironment
        from jinja2_async_environment import bccache

        assert AsyncEnvironment is not None
        assert AsyncSandboxedEnvironment is not None
        assert bccache is not None

    def test_loader_imports(self):
        """Test that loader imports work as expected."""
        # These should all work
        from jinja2_async_environment.loaders import (
            AsyncBaseLoader,
            AsyncFileSystemLoader,
            AsyncDictLoader,
            AsyncFunctionLoader,
            AsyncPackageLoader,
            AsyncChoiceLoader,
        )

        assert AsyncBaseLoader is not None
        assert AsyncFileSystemLoader is not None
        assert AsyncDictLoader is not None
        assert AsyncFunctionLoader is not None
        assert AsyncPackageLoader is not None
        assert AsyncChoiceLoader is not None

    def test_backward_compatible_imports(self):
        """Test imports that should continue to work for backward compatibility."""
        # Test that old import patterns still work
        import jinja2_async_environment
        from jinja2_async_environment import environment
        from jinja2_async_environment import loaders

        assert jinja2_async_environment.AsyncEnvironment is not None
        assert environment.AsyncEnvironment is not None
        assert loaders.AsyncFileSystemLoader is not None

    def test_submodule_imports(self):
        """Test that submodule imports work correctly."""
        # Test compiler imports
        from jinja2_async_environment import compiler
        from jinja2_async_environment.compiler import AsyncCodeGenerator

        assert compiler is not None
        assert AsyncCodeGenerator is not None

        # Test bccache imports
        from jinja2_async_environment import bccache
        from jinja2_async_environment.bccache import AsyncBytecodeCache

        assert bccache is not None
        assert AsyncBytecodeCache is not None
```

## Behavior Compatibility Tests

```python
import pytest
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


class TestBehaviorCompatibility:
    """Test that behavior remains consistent with previous versions."""

    def test_template_rendering_output_compatibility(self):
        """Test that template rendering output matches expected format."""
        templates = {
            "simple.html": "<h1>Hello {{ name }}!</h1>",
            "loop.html": """
<ul>
{% for item in items %}
    <li>{{ loop.index }}: {{ item }}</li>
{% endfor %}
</ul>
            """,
            "condition.html": """
{% if condition %}
<p>Condition is true</p>
{% else %}
<p>Condition is false</p>
{% endif %}
            """,
        }

        env = AsyncEnvironment(loader=AsyncDictLoader(templates), enable_async=True)

        # Test simple template
        template1 = asyncio.run(env.get_template_async("simple.html"))
        result1 = asyncio.run(template1.render_async(name="World"))
        assert result1 == "<h1>Hello World!</h1>"

        # Test loop template
        template2 = asyncio.run(env.get_template_async("loop.html"))
        result2 = asyncio.run(
            template2.render_async(items=["apple", "banana", "cherry"])
        )
        assert "<li>1: apple</li>" in result2
        assert "<li>2: banana</li>" in result2
        assert "<li>3: cherry</li>" in result2

        # Test condition template
        template3 = asyncio.run(env.get_template_async("condition.html"))
        result3_true = asyncio.run(template3.render_async(condition=True))
        assert "Condition is true" in result3_true

        result3_false = asyncio.run(template3.render_async(condition=False))
        assert "Condition is false" in result3_false

    def test_error_message_compatibility(self):
        """Test that error messages remain consistent."""
        env = AsyncEnvironment()

        # Test template not found error message format
        try:
            asyncio.run(env.get_template_async("nonexistent.html"))
        except Exception as e:
            error_message = str(e)
            # Should mention the template name
            assert "nonexistent.html" in error_message

    def test_cache_behavior_compatibility(self):
        """Test that caching behavior remains consistent."""
        templates = {"template.html": "<h1>Cache Test: {{ value }}</h1>"}

        env = AsyncEnvironment(loader=AsyncDictLoader(templates), enable_async=True)

        # Render template first time
        template1 = asyncio.run(env.get_template_async("template.html"))
        result1 = asyncio.run(template1.render_async(value="first"))

        # Render template second time (should use cache)
        template2 = asyncio.run(env.get_template_async("template.html"))
        result2 = asyncio.run(template2.render_async(value="second"))

        # Both should be the same template instance (cached)
        assert template1 is template2

        # But results should be different based on context
        assert "first" in result1
        assert "second" in result2

    def test_performance_characteristics_compatibility(self):
        """Test that performance characteristics remain within expected bounds."""
        import time

        templates = {"simple.html": "<h1>Hello {{ name }}!</h1>"}

        env = AsyncEnvironment(loader=AsyncDictLoader(templates), enable_async=True)

        # Time multiple template loads
        start_time = time.time()
        for _ in range(100):
            asyncio.run(env.get_template_async("simple.html"))
        end_time = time.time()

        # Should complete in reasonable time (this is a very loose check)
        assert (end_time - start_time) < 5.0  # Less than 5 seconds for 100 loads

    def test_macro_compatibility(self):
        """Test that macro functionality remains compatible."""
        templates = {
            "macros.html": """
{% macro render_item(name, value) -%}
<div class="item">
    <span class="name">{{ name }}</span>
    <span class="value">{{ value }}</span>
</div>
{%- endmacro %}
            """,
            "template.html": """
{% from "macros.html" import render_item %}
<h1>Items</h1>
{{ render_item("Item 1", "Value 1") }}
{{ render_item("Item 2", "Value 2") }}
            """,
        }

        env = AsyncEnvironment(loader=AsyncDictLoader(templates), enable_async=True)

        template = asyncio.run(env.get_template_async("template.html"))
        result = asyncio.run(template.render_async())

        # Should render macros correctly
        assert "Item 1" in result
        assert "Value 1" in result
        assert "Item 2" in result
        assert "Value 2" in result
        assert 'class="item"' in result
        assert 'class="name"' in result
        assert 'class="value"' in result
```

## Deprecation Warning Tests

```python
import warnings
import pytest
from jinja2_async_environment.environment import AsyncEnvironment


class TestDeprecationWarnings:
    """Test that deprecation warnings are properly issued."""

    def test_deprecated_method_warnings(self):
        """Test that deprecated methods issue warnings."""
        env = AsyncEnvironment()

        # Methods that should warn about deprecation
        with pytest.warns(DeprecationWarning):
            # This is a placeholder - actual deprecated methods would be tested here
            pass

    def test_deprecated_parameter_warnings(self):
        """Test that deprecated parameters issue warnings."""
        with pytest.warns(DeprecationWarning):
            # This is a placeholder - actual deprecated parameters would be tested here
            pass

    def test_future_deprecation_warnings(self):
        """Test warnings for features that will be deprecated."""
        # This is a placeholder - features scheduled for future deprecation would be tested here
        pass
```
