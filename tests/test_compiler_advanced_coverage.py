"""Advanced tests for compiler.py uncovered lines to improve coverage."""

from unittest.mock import MagicMock

from jinja2.nodes import EvalContext
from jinja2_async_environment.compiler import AsyncCodeGenerator, AsyncFrame
from jinja2_async_environment.environment import AsyncEnvironment


class TestAsyncCodeGeneratorAdvanced:
    """Test uncovered paths in AsyncCodeGenerator."""

    def test_visit_async_for_with_else_clause(self):
        """Test visit_AsyncFor with else clause (lines 196-200)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock AsyncFor node with else clause
        node = MagicMock()
        node.recursive = False
        node.target = MagicMock()
        node.target.name = "item"
        node.test = None
        node.body = []
        node.else_ = [MagicMock()]  # Has else clause
        node.iter = MagicMock()

        # Test visit_AsyncFor with else clause
        generator.visit_AsyncFor(node, frame)

        # Check that else clause code was generated
        output = generator.stream.getvalue()
        assert "if " in output and "== -1:" in output

    def test_visit_async_for_with_filter_test(self):
        """Test visit_AsyncFor with filter test (lines 177-180, 188-190, 193-194)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock AsyncFor node with test filter
        node = MagicMock()
        node.recursive = False
        node.target = MagicMock()
        node.target.name = "item"
        node.test = MagicMock()  # Has filter test
        node.body = []
        node.else_ = None
        node.iter = MagicMock()

        # Test visit_AsyncFor with filter test
        generator.visit_AsyncFor(node, frame)

        # Check that filter test code was generated
        output = generator.stream.getvalue()
        assert "if " in output and "(" in output and "):" in output

    def test_visit_async_call(self):
        """Test visit_AsyncCall method (lines 202-204)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock AsyncCall node
        node = MagicMock()

        # Mock the visit_Call method
        generator.visit_Call = MagicMock()

        # Test visit_AsyncCall
        generator.visit_AsyncCall(node, frame)

        # Check that "await " was written and visit_Call was called
        output = generator.stream.getvalue()
        assert "await " in output
        generator.visit_Call.assert_called_once_with(node, frame)

    def test_visit_async_filter_block_no_filter(self):
        """Test visit_AsyncFilterBlock with no filter (lines 206-209)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock node without filter
        node = MagicMock()
        del node.filter  # Remove filter attribute

        # Test visit_AsyncFilterBlock - should return early
        generator.visit_AsyncFilterBlock(node, frame)

        # Should not generate any code
        output = generator.stream.getvalue()
        assert output == ""

    def test_visit_async_filter_block_no_body(self):
        """Test visit_AsyncFilterBlock with no body (lines 210-211)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock node with filter but no body
        node = MagicMock()
        node.filter = MagicMock()
        del node.body  # Remove body attribute

        # Test visit_AsyncFilterBlock - should return early
        generator.visit_AsyncFilterBlock(node, frame)

        # Should not generate any code
        output = generator.stream.getvalue()
        assert output == ""

    def test_visit_async_block_no_name(self):
        """Test visit_AsyncBlock with no name (lines 224-227)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock node without name
        node = MagicMock()
        del node.name  # Remove name attribute

        # Test visit_AsyncBlock - should return early
        generator.visit_AsyncBlock(node, frame)

        # Should not generate any code
        output = generator.stream.getvalue()
        assert output == ""

    def test_visit_async_block_no_body(self):
        """Test visit_AsyncBlock with no body (lines 227-228)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock node with name but no body
        node = MagicMock()
        node.name = "test_block"
        del node.body  # Remove body attribute

        # Test visit_AsyncBlock - should return early
        generator.visit_AsyncBlock(node, frame)

        # Should not generate any code
        output = generator.stream.getvalue()
        assert output == ""

    def test_handle_special_names_blocks(self):
        """Test _handle_special_names with 'blocks' (lines 257-259)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        AsyncFrame(eval_ctx)

        # Create a mock Name node with 'blocks'
        node = MagicMock()
        node.name = "blocks"

        # Test _handle_special_names
        result = generator._handle_special_names(node)

        # Should return True and write 'blocks'
        assert result is True
        output = generator.stream.getvalue()
        assert "blocks" in output

    def test_handle_special_names_debug_info(self):
        """Test _handle_special_names with 'debug_info' (lines 257-259)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        AsyncFrame(eval_ctx)

        # Create a mock Name node with 'debug_info'
        node = MagicMock()
        node.name = "debug_info"

        # Test _handle_special_names
        result = generator._handle_special_names(node)

        # Should return True and write 'debug_info'
        assert result is True
        output = generator.stream.getvalue()
        assert "debug_info" in output

    def test_handle_special_names_other(self):
        """Test _handle_special_names with other name (line 260)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        AsyncFrame(eval_ctx)

        # Create a mock Name node with regular name
        node = MagicMock()
        node.name = "regular_name"

        # Test _handle_special_names
        result = generator._handle_special_names(node)

        # Should return False
        assert result is False

    def test_handle_symbol_name_assertion_error(self):
        """Test _handle_symbol_name with AssertionError (lines 271-275)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock Name node
        node = MagicMock()
        node.name = "test_var"
        node.ctx = "load"

        # Mock frame.symbols.ref to raise AssertionError
        frame.symbols.ref = MagicMock(side_effect=AssertionError("Test error"))

        # Test _handle_symbol_name
        generator._handle_symbol_name(node, frame)

        # Should use context.get for load context
        output = generator.stream.getvalue()
        assert "context.get(" in output

    def test_handle_symbol_name_assertion_error_store(self):
        """Test _handle_symbol_name with AssertionError and store context (line 275)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a mock Name node with store context
        node = MagicMock()
        node.name = "test_var"
        node.ctx = "store"

        # Mock frame.symbols.ref to raise AssertionError
        frame.symbols.ref = MagicMock(side_effect=AssertionError("Test error"))

        # Test _handle_symbol_name
        generator._handle_symbol_name(node, frame)

        # Should use context.vars for store context
        output = generator.stream.getvalue()
        assert "context.vars[" in output

    def test_write_filter_special_params_no_func(self):
        """Test _write_filter_special_params with no func (lines 713-714)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        # Test with None function
        generator._write_filter_special_params(None)

        # Should not write anything
        output = generator.stream.getvalue()
        assert output == ""

    def test_write_filter_input_no_node_no_buffer(self):
        """Test _write_filter_input with no node and no buffer (lines 728-731)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)
        frame.buffer = None

        # Create a filter node with no node
        node = MagicMock()
        node.node = None

        # Test _write_filter_input
        generator._write_filter_input(node, frame)

        # Should not write anything
        output = generator.stream.getvalue()
        assert output == ""

    def test_write_buffer_content_volatile(self):
        """Test _write_buffer_content with volatile context (lines 735-739)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        eval_ctx.volatile = True
        frame = AsyncFrame(eval_ctx)
        frame.buffer = "test_buffer"

        # Test _write_buffer_content
        generator._write_buffer_content(frame)

        # Should write volatile buffer content
        output = generator.stream.getvalue()
        assert "Markup(concat(" in output or "concat(" in output

    def test_write_buffer_content_autoescape(self):
        """Test _write_buffer_content with autoescape (lines 740-743)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        eval_ctx.volatile = False
        eval_ctx.autoescape = True
        frame = AsyncFrame(eval_ctx)
        frame.buffer = "test_buffer"

        # Test _write_buffer_content
        generator._write_buffer_content(frame)

        # Should write autoescape buffer content
        output = generator.stream.getvalue()
        assert "Markup(concat(" in output

    def test_write_buffer_content_no_autoescape(self):
        """Test _write_buffer_content without autoescape (lines 742-743)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        eval_ctx.volatile = False
        eval_ctx.autoescape = False
        frame = AsyncFrame(eval_ctx)
        frame.buffer = "test_buffer"

        # Test _write_buffer_content
        generator._write_buffer_content(frame)

        # Should write plain buffer content
        output = generator.stream.getvalue()
        assert "concat(" in output

    def test_write_filter_arguments_with_dynamic_args(self):
        """Test _write_filter_arguments with dynamic args (lines 755-761)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create a filter node with dynamic args
        node = MagicMock()
        node.args = []
        node.kwargs = []
        node.dyn_args = MagicMock()
        node.dyn_kwargs = MagicMock()

        # Mock visit method
        generator.visit = MagicMock()

        # Test _write_filter_arguments
        generator._write_filter_arguments(node, frame)

        # Should write dynamic args and kwargs
        output = generator.stream.getvalue()
        assert ", *" in output
        assert ", **" in output

    def test_visit_assign_with_nsref(self):
        """Test visit_Assign with namespace reference (lines 769-781)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)

        # Create an Assign node with NSRef
        node = MagicMock()
        node.target = MagicMock()
        node.node = MagicMock()

        # Mock NSRef finding
        nsref = MagicMock()
        nsref.name = "ns"
        node.find_all = MagicMock(return_value=[nsref])

        # Mock frame.symbols.ref
        frame.symbols.ref = MagicMock(return_value="l_0_ns")

        # Mock visit methods
        generator.visit = MagicMock()
        generator.newline = MagicMock()
        generator.push_assign_tracking = MagicMock()
        generator.pop_assign_tracking = MagicMock()

        # Test visit_Assign
        generator.visit_Assign(node, frame)

        # Should generate namespace assignment check
        output = generator.stream.getvalue()
        assert "isinstance(" in output and "Namespace" in output

    def test_pop_assign_tracking_no_vars(self):
        """Test pop_assign_tracking with no variables set (lines 803-806)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)
        frame.block_frame = False
        frame.loop_frame = False
        frame.toplevel = False

        # Initialize assign stack with empty set
        generator._assign_stack = [set()]

        # Test pop_assign_tracking
        generator.pop_assign_tracking(frame)

        # Should not write anything
        output = generator.stream.getvalue()
        assert output == ""

    def test_pop_assign_tracking_single_var_loop(self):
        """Test pop_assign_tracking with single variable in loop (lines 812-814)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)
        frame.block_frame = False
        frame.loop_frame = True
        frame.toplevel = False

        # Initialize assign stack with single variable
        generator._assign_stack = [{"test_var"}]

        # Mock frame.symbols.ref
        frame.symbols.ref = MagicMock(return_value="l_0_test_var")

        # Test pop_assign_tracking
        generator.pop_assign_tracking(frame)

        # Should write loop variable assignment
        output = generator.stream.getvalue()
        assert "_loop_vars[" in output

    def test_pop_assign_tracking_single_var_block(self):
        """Test pop_assign_tracking with single variable in block (lines 815-817)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)
        frame.block_frame = True
        frame.loop_frame = False
        frame.toplevel = False

        # Initialize assign stack with single variable
        generator._assign_stack = [{"test_var"}]

        # Mock frame.symbols.ref
        frame.symbols.ref = MagicMock(return_value="l_0_test_var")

        # Test pop_assign_tracking
        generator.pop_assign_tracking(frame)

        # Should write block variable assignment
        output = generator.stream.getvalue()
        assert "_block_vars[" in output

    def test_pop_assign_tracking_multiple_vars_loop(self):
        """Test pop_assign_tracking with multiple variables in loop (lines 820-831)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)
        frame.block_frame = False
        frame.loop_frame = True
        frame.toplevel = False

        # Initialize assign stack with multiple variables
        generator._assign_stack = [{"var1", "var2"}]

        # Mock frame.symbols.ref
        frame.symbols.ref = MagicMock(side_effect=lambda x: f"l_0_{x}")

        # Test pop_assign_tracking
        generator.pop_assign_tracking(frame)

        # Should write loop variable update
        output = generator.stream.getvalue()
        assert "_loop_vars.update({" in output

    def test_pop_assign_tracking_public_names(self):
        """Test pop_assign_tracking with public names (lines 833-838)."""
        env = AsyncEnvironment()
        generator = AsyncCodeGenerator(env, "test", "test.html")

        eval_ctx = EvalContext(env, "test")
        frame = AsyncFrame(eval_ctx)
        frame.block_frame = False
        frame.loop_frame = False
        frame.toplevel = True

        # Initialize assign stack with public and private variables
        generator._assign_stack = [{"public_var", "_private_var"}]

        # Mock frame.symbols.ref
        frame.symbols.ref = MagicMock(side_effect=lambda x: f"l_0_{x}")

        # Test pop_assign_tracking
        generator.pop_assign_tracking(frame)

        # Should write exported vars
        output = generator.stream.getvalue()
        assert (
            "context.exported_vars.add(" in output
            or "context.exported_vars.update(" in output
        )
