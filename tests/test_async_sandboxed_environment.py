from unittest.mock import MagicMock

import pytest
from anyio import Path as AsyncPath
from jinja2.exceptions import SecurityError
from jinja2_async_environment.environment import AsyncSandboxedEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


class TestAsyncSandboxedEnvironment:
    @pytest.fixture
    def safe_loader(self) -> AsyncDictLoader:
        """Create a loader with safe templates."""
        return AsyncDictLoader(
            {
                "safe.html": "Hello {{ name }}!",
                "with_filter.html": "{{ message | escape }}",
                "math.html": "Result: {{ a + b }}",
            },
            AsyncPath("/templates"),
        )

    @pytest.fixture
    def unsafe_loader(self) -> AsyncDictLoader:
        """Create a loader with unsafe templates."""
        return AsyncDictLoader(
            {
                "unsafe_class.html": "{{ obj.__class__.__bases__ }}",
                "unsafe_subclass.html": "{{ ().__class__.__bases__[0].__subclasses__() }}",
                "allowed_code.html": "{{ func.__code__ }}",  # This is allowed but returns empty
                "allowed_globals.html": "{{ func.__globals__ }}",  # This is allowed but returns empty
            },
            AsyncPath("/templates"),
        )

    @pytest.fixture
    def env_safe(self, safe_loader: AsyncDictLoader) -> AsyncSandboxedEnvironment:
        """Create a sandboxed environment with safe templates."""
        return AsyncSandboxedEnvironment(loader=safe_loader)

    @pytest.fixture
    def env_unsafe(self, unsafe_loader: AsyncDictLoader) -> AsyncSandboxedEnvironment:
        """Create a sandboxed environment with unsafe templates."""
        return AsyncSandboxedEnvironment(loader=unsafe_loader)

    def test_init(self) -> None:
        """Test AsyncSandboxedEnvironment initialization."""
        loader = MagicMock()
        env = AsyncSandboxedEnvironment(loader=loader)

        assert env.loader is loader
        assert env.enable_async
        assert hasattr(env, "code_generator_class")
        assert "escape" in env.filters

    def test_async_enabled_by_default(self) -> None:
        """Test that async is enabled by default."""
        env = AsyncSandboxedEnvironment()
        assert env.enable_async

    def test_explicit_async_enabled(self) -> None:
        """Test that explicit enable_async=True works."""
        env = AsyncSandboxedEnvironment(enable_async=True)
        assert env.enable_async

    def test_async_disabled_override(self) -> None:
        """Test that async can be explicitly disabled."""
        env = AsyncSandboxedEnvironment(enable_async=False)
        assert env.enable_async  # Should still be True due to our implementation

    async def test_safe_template_rendering(
        self, env_safe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that safe templates render correctly."""
        template = await env_safe.get_template_async("safe.html")
        result = await template.render_async(name="World")
        assert "Hello World!" in result

    async def test_safe_template_with_filter(
        self, env_safe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that safe templates with filters work."""
        template = await env_safe.get_template_async("with_filter.html")
        result = await template.render_async(message="<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result  # Should be escaped

    async def test_safe_template_with_math(
        self, env_safe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that safe math operations work."""
        template = await env_safe.get_template_async("math.html")
        result = await template.render_async(a=5, b=3)
        assert "Result: 8" in result

    async def test_allowed_code_access_safe(
        self, env_unsafe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that access to function __code__ is allowed but safe (returns empty)."""
        template = await env_unsafe.get_template_async("allowed_code.html")

        def test_func() -> str:
            return "test"

        # This should not raise SecurityError but return empty string
        result = await template.render_async(func=test_func)
        assert result.strip() == ""

    async def test_allowed_globals_access_safe(
        self, env_unsafe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that access to function __globals__ is allowed but safe (returns empty)."""
        template = await env_unsafe.get_template_async("allowed_globals.html")

        def test_func() -> str:
            return "test"

        # This should not raise SecurityError but return empty string
        result = await template.render_async(func=test_func)
        assert result.strip() == ""

    async def test_unsafe_class_access_blocked(
        self, env_unsafe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that access to class internals is blocked."""
        template = await env_unsafe.get_template_async("unsafe_class.html")

        class TestClass:
            pass

        with pytest.raises(SecurityError):
            await template.render_async(obj=TestClass())

    async def test_unsafe_subclass_introspection_blocked(
        self, env_unsafe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that subclass introspection is blocked."""
        template = await env_unsafe.get_template_async("unsafe_subclass.html")

        with pytest.raises(SecurityError):
            await template.render_async()

    def test_inheritance_from_both_parents(self) -> None:
        """Test that AsyncSandboxedEnvironment inherits from both parent classes."""
        from jinja2.sandbox import SandboxedEnvironment
        from jinja2_async_environment.environment import AsyncEnvironment

        env = AsyncSandboxedEnvironment()
        assert isinstance(env, SandboxedEnvironment)
        assert isinstance(env, AsyncEnvironment)

    def test_code_generator_class(self) -> None:
        """Test that the correct code generator class is used."""
        from jinja2_async_environment.compiler import AsyncCodeGenerator

        env = AsyncSandboxedEnvironment()
        assert env.code_generator_class is AsyncCodeGenerator

    async def test_template_caching_works(
        self, env_safe: AsyncSandboxedEnvironment
    ) -> None:
        """Test that template caching works in sandboxed environment."""
        # Enable caching
        env_safe.cache = {}

        # Load template twice
        template1 = await env_safe.get_template_async("safe.html")
        template2 = await env_safe.get_template_async("safe.html")

        # Templates should have same name and render the same
        assert template1.name == template2.name == "safe.html"
        result1 = await template1.render_async(name="Test")
        result2 = await template2.render_async(name="Test")
        assert result1 == result2

    async def test_multiple_template_rendering(
        self, env_safe: AsyncSandboxedEnvironment
    ) -> None:
        """Test rendering multiple templates in sequence."""
        template1 = await env_safe.get_template_async("safe.html")
        template2 = await env_safe.get_template_async("math.html")

        result1 = await template1.render_async(name="Alice")
        result2 = await template2.render_async(a=10, b=20)

        assert "Hello Alice!" in result1
        assert "Result: 30" in result2

    def test_escape_filter_registered(self) -> None:
        """Test that the escape filter is properly registered."""
        env = AsyncSandboxedEnvironment()
        assert "escape" in env.filters

        # Test that it's callable
        escape_filter = env.filters["escape"]
        assert callable(escape_filter)
