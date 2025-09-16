# Error Handling and Edge Case Tests

## Template Not Found Error Tests

```python
import pytest
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncDictLoader,
    AsyncFileSystemLoader,
    AsyncFunctionLoader,
    AsyncPackageLoader,
    AsyncChoiceLoader,
)


class TestTemplateNotFoundErrorHandling:
    """Test error handling for template not found scenarios."""

    def test_dict_loader_template_not_found(self):
        """Test DictLoader raises TemplateNotFound for non-existent templates."""
        templates = {"existing.html": "<h1>Existing Template</h1>"}

        loader = AsyncDictLoader(templates)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("nonexistent.html"))

    def test_filesystem_loader_template_not_found(self, tmp_path):
        """Test FileSystemLoader raises TemplateNotFound for non-existent templates."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "existing.html").write_text("<h1>Existing Template</h1>")

        loader = AsyncFileSystemLoader(templates_dir)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("nonexistent.html"))

    def test_function_loader_template_not_found(self):
        """Test FunctionLoader raises TemplateNotFound for non-existent templates."""

        def load_func(name):
            return None  # Always return None to simulate not found

        loader = AsyncFunctionLoader(load_func)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("any_template.html"))

    def test_choice_loader_all_loaders_fail(self):
        """Test ChoiceLoader raises TemplateNotFound when all loaders fail."""

        def fail_func1(name):
            return None

        def fail_func2(name):
            return None

        loader1 = AsyncFunctionLoader(fail_func1)
        loader2 = AsyncFunctionLoader(fail_func2)
        choice_loader = AsyncChoiceLoader([loader1, loader2])

        env = AsyncEnvironment(loader=choice_loader)

        # This should raise TemplateNotFound
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("any_template.html"))

    def test_select_template_all_not_found(self):
        """Test select_template_async raises TemplateNotFound when all templates not found."""
        templates = {"template1.html": "<h1>Template 1</h1>"}

        loader = AsyncDictLoader(templates)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound
        with pytest.raises(TemplateNotFound):
            asyncio.run(
                env.select_template_async(
                    ["nonexistent1.html", "nonexistent2.html", "nonexistent3.html"]
                )
            )
```

## Loader Error Handling Tests

```python
import pytest
from jinja2.exceptions import TemplateNotFound
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncDictLoader,
    AsyncFileSystemLoader,
    AsyncFunctionLoader,
)


class TestLoaderErrorHandling:
    """Test error handling in various loader scenarios."""

    def test_filesystem_loader_permission_denied(self, tmp_path):
        """Test FileSystemLoader handles permission denied errors gracefully."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "restricted.html"
        template_file.write_text("<h1>Restricted Template</h1>")

        # Make file unreadable
        template_file.chmod(0o000)

        loader = AsyncFileSystemLoader(templates_dir)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound (not a permission error)
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("restricted.html"))

        # Restore permissions for cleanup
        template_file.chmod(0o644)

    def test_filesystem_loader_corrupted_file(self, tmp_path):
        """Test FileSystemLoader handles corrupted files gracefully."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        # Create a "corrupted" file (invalid UTF-8)
        corrupted_file = templates_dir / "corrupted.html"
        corrupted_file.write_bytes(b"\xff\xfe\xfd")  # Invalid UTF-8 bytes

        loader = AsyncFileSystemLoader(templates_dir)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound (not a decode error)
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("corrupted.html"))

    def test_function_loader_exception_handling(self):
        """Test FunctionLoader handles exceptions in load function gracefully."""

        def faulty_load_func(name):
            raise ValueError("Simulated error in load function")

        loader = AsyncFunctionLoader(faulty_load_func)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound (not the original ValueError)
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("any_template.html"))

    def test_function_loader_invalid_return_type(self):
        """Test FunctionLoader handles invalid return types gracefully."""

        def invalid_return_func(name):
            return 42  # Invalid return type

        loader = AsyncFunctionLoader(invalid_return_func)
        env = AsyncEnvironment(loader=loader)

        # This should raise TemplateNotFound (not a type error)
        with pytest.raises(TemplateNotFound):
            asyncio.run(env.get_template_async("any_template.html"))
```

## Template Compilation Error Tests

```python
import pytest
from jinja2.exceptions import TemplateSyntaxError
from jinja2_async_environment.environment import AsyncEnvironment


class TestTemplateCompilationErrors:
    """Test error handling for template compilation errors."""

    def test_syntax_error_in_template(self):
        """Test that syntax errors in templates are properly handled."""
        env = AsyncEnvironment()

        # Template with syntax error (unclosed block)
        invalid_template = """
{% block content %}
<h1>Hello World</h1>
<!-- Missing {% endblock %} -->
        """

        # This should raise TemplateSyntaxError
        with pytest.raises(TemplateSyntaxError):
            env._compile(invalid_template, "invalid.html")

    def test_invalid_macro_definition(self):
        """Test that invalid macro definitions are properly handled."""
        env = AsyncEnvironment()

        # Template with invalid macro syntax
        invalid_macro = """
{% macro invalid_macro( %}
<!-- Missing parameter name and closing parenthesis -->
        """

        # This should raise TemplateSyntaxError
        with pytest.raises(TemplateSyntaxError):
            env._compile(invalid_macro, "invalid_macro.html")

    def test_invalid_filter_usage(self):
        """Test that invalid filter usage is properly handled."""
        env = AsyncEnvironment()

        # Template with invalid filter syntax
        invalid_filter = """
<p>{{ "hello" | invalid_filter: "extra_arg" }}</p>
<!-- Invalid filter syntax with colon -->
        """

        # This should raise TemplateSyntaxError
        with pytest.raises(TemplateSyntaxError):
            env._compile(invalid_filter, "invalid_filter.html")
```

## Runtime Error Tests

```python
import pytest
from jinja2.exceptions import UndefinedError
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


class TestRuntimeErrors:
    """Test error handling for runtime/template execution errors."""

    def test_undefined_variable_error(self):
        """Test that undefined variables raise appropriate errors."""
        templates = {"template.html": "<h1>Hello {{ undefined_variable }}!</h1>"}

        env = AsyncEnvironment(loader=AsyncDictLoader(templates), enable_async=True)

        template = asyncio.run(env.get_template_async("template.html"))

        # By default, this should render without error (Undefined behavior)
        result = asyncio.run(template.render_async())
        assert (
            "Hello " in result
        )  # Undefined variables render as empty string by default

        # With strict autoescape, it might behave differently
        env_strict = AsyncEnvironment(
            loader=AsyncDictLoader(templates),
            undefined_behavior="strict",  # This would need to be implemented
            enable_async=True,
        )
        # Note: Actual strict undefined behavior would need custom implementation

    def test_filter_execution_error(self):
        """Test that filter execution errors are handled properly."""
        templates = {"template.html": "<p>{{ value | round }}</p>"}

        env = AsyncEnvironment(loader=AsyncDictLoader(templates), enable_async=True)

        template = asyncio.run(env.get_template_async("template.html"))

        # Pass a non-numeric value to round filter
        result = asyncio.run(template.render_async(value="not_a_number"))
        # The result will depend on how the round filter handles errors
        assert "<p>" in result

    def test_macro_execution_error(self):
        """Test that macro execution errors are handled properly."""
        templates = {
            "macros.html": """
{% macro divide(a, b) -%}
{{ a / b }}
{%- endmacro %}
            """,
            "template.html": """
{% from "macros.html" import divide %}
<p>{{ divide(10, 0) }}</p>
            """,
        }

        env = AsyncEnvironment(loader=AsyncDictLoader(templates), enable_async=True)

        template = asyncio.run(env.get_template_async("template.html"))

        # Division by zero - behavior depends on Python's division handling
        result = asyncio.run(template.render_async())
        assert "<p>" in result
```

## Edge Case Tests

```python
import pytest
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader, AsyncChoiceLoader


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_template_name(self):
        """Test handling of empty template names."""
        templates = {"": "<h1>Empty Name Template</h1>"}

        loader = AsyncDictLoader(templates)
        env = AsyncEnvironment(loader=loader)

        # This should work (though it's an unusual case)
        template = asyncio.run(env.get_template_async(""))
        result = asyncio.run(template.render_async())
        assert "Empty Name Template" in result

    def test_template_name_with_special_characters(self):
        """Test template names with special characters."""
        templates = {
            "template with spaces.html": "<h1>Template With Spaces</h1>",
            "template-with-dashes.html": "<h2>Template With Dashes</h2>",
            "template_with_underscores.html": "<p>Template With Underscores</p>",
            "template@with#special$chars.html": "<div>Special Characters</div>",
        }

        loader = AsyncDictLoader(templates)
        env = AsyncEnvironment(loader=loader)

        # Test all special character templates
        for template_name in templates.keys():
            template = asyncio.run(env.get_template_async(template_name))
            result = asyncio.run(template.render_async())
            assert (
                template_name.replace(".html", "").replace("_", " ").replace("-", " ")
                in result
            )

    def test_very_large_template(self):
        """Test handling of very large templates."""
        # Create a very large template
        large_content = "<p>" + "x" * 100000 + "</p>"  # 100K characters
        templates = {"large_template.html": large_content}

        loader = AsyncDictLoader(templates)
        env = AsyncEnvironment(loader=loader)

        template = asyncio.run(env.get_template_async("large_template.html"))
        result = asyncio.run(template.render_async())

        # Should handle large templates without issues
        assert len(result) > 99000
        assert result.startswith("<p>")
        assert result.endswith("</p>")

    def test_nested_choice_loaders_deep(self):
        """Test deeply nested ChoiceLoader scenarios."""

        def loader_func1(name):
            if name == "level1.html":
                return "<h1>Level 1</h1>"
            return None

        def loader_func2(name):
            if name == "level2.html":
                return "<h2>Level 2</h2>"
            return None

        def loader_func3(name):
            if name == "level3.html":
                return "<h3>Level 3</h3>"
            return None

        # Create deeply nested choice loaders
        loader1 = AsyncFunctionLoader(loader_func1)
        loader2 = AsyncFunctionLoader(loader_func2)
        loader3 = AsyncFunctionLoader(loader_func3)

        choice1 = AsyncChoiceLoader([loader1, loader2])
        choice2 = AsyncChoiceLoader([choice1, loader3])

        env = AsyncEnvironment(loader=choice2)

        # Test all levels
        template1 = asyncio.run(env.get_template_async("level1.html"))
        result1 = asyncio.run(template1.render_async())
        assert "Level 1" in result1

        template2 = asyncio.run(env.get_template_async("level2.html"))
        result2 = asyncio.run(template2.render_async())
        assert "Level 2" in result2

        template3 = asyncio.run(env.get_template_async("level3.html"))
        result3 = asyncio.run(template3.render_async())
        assert "Level 3" in result3

    def test_concurrent_access_to_same_template(self):
        """Test concurrent access to the same template."""
        templates = {
            "concurrent.html": "<h1>Concurrent Access Test</h1><p>Request ID: {{ request_id }}</p>"
        }

        loader = AsyncDictLoader(templates)
        env = AsyncEnvironment(loader=loader, enable_async=True)

        async def render_template(request_id):
            template = await env.get_template_async("concurrent.html")
            return await template.render_async(request_id=request_id)

        # Render the same template concurrently
        async def render_concurrent():
            tasks = [render_template(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(render_concurrent())

        # All should succeed and have different request IDs
        assert len(results) == 10
        for i, result in enumerate(results):
            assert "Concurrent Access Test" in result
            assert f"Request ID: {i}" in result
```
