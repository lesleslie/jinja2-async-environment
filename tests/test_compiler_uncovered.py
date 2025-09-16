"""Tests for uncovered methods in compiler.py to improve coverage."""

import pytest
from jinja2.environment import Environment
from jinja2.nodes import EvalContext
from jinja2_async_environment.compiler import AsyncCodeGenerator, AsyncFrame


class TestAsyncFrame:
    """Test AsyncFrame methods that are not covered."""

    def test_inspect_with_nodes(self):
        """Test AsyncFrame.inspect with nodes."""
        eval_ctx = EvalContext(Environment(autoescape=True), "template")
        frame = AsyncFrame(eval_ctx)

        # Create a mock node that will trigger the analyze_node path
        class MockNode:
            def __init__(self):
                pass

        # Mock the analyze_node method to avoid complex setup
        original_analyze = frame.symbols.analyze_node

        def mock_analyze(node):
            pass

        frame.symbols.analyze_node = mock_analyze

        # Test inspect method with nodes
        frame.inspect([MockNode()])

        # Restore original method
        frame.symbols.analyze_node = original_analyze

        # The inspect method should execute without error
        assert True

    def test_inspect_without_nodes(self):
        """Test AsyncFrame.inspect without nodes."""
        eval_ctx = EvalContext(Environment(autoescape=True), "template")
        frame = AsyncFrame(eval_ctx)

        # Test inspect method with None
        frame.inspect(None)

        # Should not raise an exception
        assert True

    def test_push_pop_scope(self):
        """Test AsyncFrame push_scope and pop_scope methods."""
        eval_ctx = EvalContext(Environment(autoescape=True), "template")
        frame = AsyncFrame(eval_ctx)

        # Test push and pop scope (currently no-ops)
        frame.push_scope()
        frame.pop_scope()

        # Should not raise an exception
        assert True

    def test_find_break_continue(self):
        """Test AsyncFrame find_break and find_continue methods."""
        eval_ctx = EvalContext(Environment(autoescape=True), "template")
        frame = AsyncFrame(eval_ctx)

        # Test find_break and find_continue
        assert frame.find_break() is False
        assert frame.find_continue() is False

    def test_inner_frame(self):
        """Test AsyncFrame.inner method."""
        eval_ctx = EvalContext(Environment(autoescape=True), "template")
        frame = AsyncFrame(eval_ctx)

        # Test inner frame creation
        inner_frame = frame.inner()

        assert isinstance(inner_frame, AsyncFrame)
        assert inner_frame.parent is frame


class TestAsyncCodeGenerator:
    """Test AsyncCodeGenerator methods that are not covered."""

    def test_func_method(self):
        """Test AsyncCodeGenerator.func method."""
        from jinja2_async_environment.environment import AsyncEnvironment

        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        # Test func method
        result = generator.func("test_function")
        assert result == "def test_function"

    def test_enter_leave_frame(self):
        """Test AsyncCodeGenerator enter_frame and leave_frame methods."""
        from jinja2_async_environment.environment import AsyncEnvironment

        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Test enter and leave frame (currently no-ops)
        generator.enter_frame(frame)
        generator.leave_frame(frame)
        generator.leave_frame(frame, with_python_scope=True)

        # Should not raise an exception
        assert True

    def test_return_buffer_contents(self):
        """Test AsyncCodeGenerator.return_buffer_contents method."""
        from jinja2_async_environment.environment import AsyncEnvironment

        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)
        frame.buffer = "test_buffer"

        # Test return buffer contents
        generator.return_buffer_contents(frame)

        # Check that the correct code was generated
        output = generator.stream.getvalue()
        assert "return ''.join(test_buffer)" in output

    def test_func_code_generator(self):
        """Test AsyncCodeGenerator.func_code_generator method."""
        from jinja2_async_environment.environment import AsyncEnvironment

        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Test with async frame
        frame.is_async = True
        result = generator.func_code_generator(frame)
        assert result == "async def"

        # Test with sync frame
        frame.is_async = False
        result = generator.func_code_generator(frame)
        assert result == "def"

    def test_simple_write(self):
        """Test AsyncCodeGenerator.simple_write method."""
        from jinja2_async_environment.environment import AsyncEnvironment

        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Test simple write
        generator.simple_write("test_value", frame)

        # Check that the correct code was generated
        output = generator.stream.getvalue()
        assert "yield test_value" in output

    @pytest.mark.asyncio
    async def test_visit_async_for_with_recursive(self):
        """Test visit_AsyncFor with recursive loop (should raise NotImplementedError)."""
        from jinja2_async_environment.environment import AsyncEnvironment

        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock node with recursive=True
        class MockNode:
            def __init__(self):
                self.recursive = True
                self.target = type("Target", (), {"name": "item"})()

        node = MockNode()

        # Test that recursive loops raise NotImplementedError
        with pytest.raises(NotImplementedError, match="Recursive loops not supported"):
            generator.visit_AsyncFor(node, frame)
