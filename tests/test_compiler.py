from unittest.mock import MagicMock

import pytest
from jinja2 import nodes
from jinja2.compiler import CompilerExit
from jinja2_async_environment.compiler import AsyncCodeGenerator, AsyncFrame


class TestAsyncFrame:
    """Tests for the AsyncFrame class."""

    @pytest.fixture
    def frame(self) -> AsyncFrame:
        """Create a basic AsyncFrame for testing."""
        eval_ctx = MagicMock()
        frame = AsyncFrame(eval_ctx)

        # Set attributes after initialization
        frame.block_frame = None
        frame.require_output_check = True
        frame.has_known_extends = False
        frame.toplevel = True
        frame.rootlevel = True
        frame.buffer = None

        return frame

    def test_copy(self, frame: AsyncFrame) -> None:
        """Test the copy method."""
        # Set some attributes on the frame
        frame.block_frame = None
        frame.block_counters = {"block1": 1, "block2": 2}
        frame.block_frame_id = 42
        frame.require_output_check = True
        frame.has_known_extends = False
        frame.toplevel = True
        frame.rootlevel = True
        frame.buffer = None

        # Create a copy
        copied = frame.copy()

        # Verify the attributes are copied correctly
        assert copied is not frame
        assert copied.block_frame is frame.block_frame
        assert copied.block_counters == frame.block_counters
        assert copied.block_frame_id == frame.block_frame_id
        assert copied.require_output_check == frame.require_output_check
        assert copied.has_known_extends == frame.has_known_extends
        assert copied.toplevel == frame.toplevel
        assert copied.rootlevel == frame.rootlevel
        assert copied.buffer == frame.buffer


class TestAsyncCodeGenerator:
    """Tests for the AsyncCodeGenerator class."""

    @pytest.fixture
    def environment(self) -> MagicMock:
        """Create a mock environment."""
        env = MagicMock()
        env.is_async = True
        return env

    @pytest.fixture
    def stream(self) -> MagicMock:
        """Create a mock stream."""
        return MagicMock()

    @pytest.fixture
    def code_generator(
        self, environment: MagicMock, stream: MagicMock
    ) -> AsyncCodeGenerator:
        """Create an AsyncCodeGenerator for testing."""
        return AsyncCodeGenerator(environment, "test_name", "test_filename", stream)

    @pytest.fixture
    def async_frame(self) -> AsyncFrame:
        """Create an AsyncFrame for testing."""
        eval_ctx = MagicMock()
        frame = AsyncFrame(eval_ctx)

        # Set attributes after initialization
        frame.block_frame = None
        frame.require_output_check = True
        frame.has_known_extends = False
        frame.toplevel = True
        frame.rootlevel = False
        frame.buffer = None

        return frame

    def test_visit_block_has_known_extends(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Block when has_known_extends is True."""
        # Setup
        code_generator.has_known_extends = True
        block_node = nodes.Block("test_block", [], False, False)

        # Call method
        code_generator.visit_Block(block_node, async_frame)

        # No assertions needed - just verify it doesn't raise exceptions

    def test_visit_block_normal(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Block in normal case."""
        # Setup
        code_generator.has_known_extends = False
        code_generator.extends_so_far = 0
        code_generator.environment.is_async = True
        code_generator.derive_context = MagicMock()
        code_generator.writeline = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()
        code_generator.get_context_ref = MagicMock(return_value="context")
        code_generator.choose_async = MagicMock(return_value="async ")

        block_node = nodes.Block("test_block", [], False, False)

        # Call method
        code_generator.visit_Block(block_node, async_frame)

        # Verify the correct methods were called
        code_generator.choose_async.assert_called_once()
        # Writeline should be called for the async for block
        assert code_generator.writeline.call_count >= 1

    def test_visit_extends_exit_on_no_output_check(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Extends raises CompilerExit when require_output_check is False."""
        # Setup
        async_frame.require_output_check = False
        extends_node = nodes.Extends(MagicMock())

        # Test
        with pytest.raises(CompilerExit):
            code_generator.visit_Extends(extends_node, async_frame)

    def test_visit_extends_fail_on_non_toplevel(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Extends fails when not in toplevel scope."""
        # Setup
        async_frame.toplevel = False
        extends_node = nodes.Extends(MagicMock())
        code_generator.fail = MagicMock()

        # Call method
        code_generator.visit_Extends(extends_node, async_frame)

        # Verify fail was called
        code_generator.fail.assert_called_once()

    def test_visit_extends_multiple_times(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Extends when extends_so_far > 0."""
        # Setup
        code_generator.extends_so_far = 1
        code_generator.has_known_extends = False
        code_generator.writeline = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()

        extends_node = nodes.Extends(MagicMock())

        # Call method
        code_generator.visit_Extends(extends_node, async_frame)

        # Verify conditional block was written
        code_generator.writeline.assert_any_call("if parent_template is not None:")
        code_generator.writeline.assert_any_call(
            'raise TemplateRuntimeError("extended multiple times")'
        )

    def test_visit_extends_with_known_extends(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Extends when has_known_extends is True."""
        # Setup
        code_generator.extends_so_far = 1
        code_generator.has_known_extends = True
        code_generator.writeline = MagicMock()

        extends_node = nodes.Extends(MagicMock())

        # Test
        with pytest.raises(CompilerExit):
            code_generator.visit_Extends(extends_node, async_frame)

        # Verify error message was written
        code_generator.writeline.assert_any_call(
            'raise TemplateRuntimeError("extended multiple times")'
        )

    def test_visit_extends_normal(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Extends in normal case."""
        # Setup
        code_generator.extends_so_far = 0
        code_generator.has_known_extends = False
        code_generator.writeline = MagicMock()
        code_generator.write = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()
        code_generator.visit = MagicMock()

        extends_node = nodes.Extends(MagicMock())

        # Call method
        code_generator.visit_Extends(extends_node, async_frame)

        # Verify the correct methods were called
        code_generator.writeline.assert_any_call(
            "parent_template = await environment.get_template_async(",
            extends_node,
        )
        code_generator.visit.assert_called_once_with(extends_node.template, async_frame)
        assert code_generator.extends_so_far == 1

    def test_visit_extends_set_has_known_extends(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Extends sets has_known_extends when frame.rootlevel is True."""
        # Setup
        code_generator.extends_so_far = 0
        code_generator.has_known_extends = False
        code_generator.writeline = MagicMock()
        code_generator.write = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()
        code_generator.visit = MagicMock()

        async_frame.rootlevel = True
        extends_node = nodes.Extends(MagicMock())

        # Call method
        code_generator.visit_Extends(extends_node, async_frame)

        # Verify has_known_extends was set
        assert code_generator.has_known_extends

    def test_visit_include_ignore_missing(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Include with ignore_missing=True."""
        # Setup
        code_generator.writeline = MagicMock()
        code_generator.write = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()
        code_generator.visit = MagicMock()
        code_generator.simple_write = MagicMock()

        include_node = nodes.Include(MagicMock(), False, True)

        # Call method
        code_generator.visit_Include(include_node, async_frame)

        # Verify try/except block was generated
        code_generator.writeline.assert_any_call("try:")
        code_generator.writeline.assert_any_call("except TemplateNotFound:")

    def test_visit_include_with_context(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Include with with_context=True."""
        # Setup
        code_generator.writeline = MagicMock()
        code_generator.write = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()
        code_generator.visit = MagicMock()
        code_generator.simple_write = MagicMock()
        code_generator.dump_local_context = MagicMock(return_value="local_context")

        include_node = nodes.Include(MagicMock(), True, False)

        # Call method
        code_generator.visit_Include(include_node, async_frame)

        # Verify correct async for loop was generated
        code_generator.writeline.assert_any_call(
            "async for event in template.root_render_func("
            "template.new_context(context.get_all(), True,"
            " local_context)):"
        )

    def test_visit_include_without_context(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test visit_Include with with_context=False."""
        # Setup
        code_generator.writeline = MagicMock()
        code_generator.write = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()
        code_generator.visit = MagicMock()
        code_generator.simple_write = MagicMock()

        include_node = nodes.Include(MagicMock(), False, False)

        # Call method
        code_generator.visit_Include(include_node, async_frame)

        # Verify correct async for loop was generated
        code_generator.writeline.assert_any_call(
            "async for event in (await template._get_default_module_async())"
            "._body_stream:"
        )

    def test_import_common(
        self, code_generator: AsyncCodeGenerator, async_frame: AsyncFrame
    ) -> None:
        """Test _import_common method."""
        # Setup
        code_generator.writeline = MagicMock()
        code_generator.write = MagicMock()
        code_generator.indent = MagicMock()
        code_generator.outdent = MagicMock()
        code_generator.visit = MagicMock()

        import_node = nodes.Import(MagicMock(), MagicMock(), True)

        # Call method
        code_generator._import_common(import_node, async_frame)

        # Verify try/except block was generated
        code_generator.writeline.assert_any_call("try:")
        code_generator.writeline.assert_any_call("except TemplateNotFound:")
        code_generator.visit.assert_called_with(import_node.template, async_frame)
